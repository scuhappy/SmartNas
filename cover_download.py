import os
import re
import json
import asyncio
import requests
from urllib.parse import quote
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# 读取配置文件
def load_config():
    """读取cover_config.json配置文件"""
    try:
        with open('cover_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ cover_config.json 文件未找到，使用默认配置")
        return {
            "video_paths": ["/media"],
            "cover_path": "./covers",
            "meta_config": "metadata.json"
        }

# 加载配置
CONFIG = load_config()
BASE_URL = "https://javday.app"

async def search_javday(fanhao: str):
    """使用 Playwright 访问 javday 搜索并解析结果"""
    url = f"{BASE_URL}/search?wd={quote(fanhao)}"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://javday.app/",
                "Connection": "keep-alive",
            },
            ignore_https_errors=True
        )
        page = await context.new_page()

        try:
            print(f"🔍 搜索 {fanhao}: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".videoBox", timeout=15000)
            content = await page.content()

            soup = BeautifulSoup(content, "html.parser")
            for box in soup.select(".videoBox"):
                cover_div = box.select_one(".videoBox-cover")
                cover_url = None
                if cover_div and "style" in cover_div.attrs:
                    m = re.search(r"url\((.*?)\)", cover_div["style"])
                    if m:
                        cover_url = BASE_URL + m.group(1)

                title_span = box.select_one(".videoBox-info .title")
                title = title_span.get_text(strip=True) if title_span else None

                if cover_url and title:
                    results.append({"title": title, "cover": cover_url})

        except Exception as e:
            print(f"❌ 搜索 {fanhao} 失败: {e}")
        finally:
            await browser.close()

    return results

async def download_cover(url, fanhao, filename, save_dir, retries=3):
    """下载封面并以视频文件名命名，支持重试和备用下载"""
    os.makedirs(save_dir, exist_ok=True)
    save_name = os.path.splitext(filename)[0]
    save_path = os.path.join(save_dir, f"{save_name}.jpg")

    # 检查封面是否已存在
    if os.path.exists(save_path):
        print(f"✅ {fanhao} 封面已存在: {save_path}")
        return save_path

    # 尝试使用 Playwright 下载
    for attempt in range(retries):
        try:
            print(f"📥 尝试下载 {fanhao} 封面 (第 {attempt + 1}/{retries}): {url}")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(ignore_https_errors=True)
                page = await context.new_page()
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                if response and response.status == 200:
                    content = await response.body()
                    with open(save_path, "wb") as f:
                        f.write(content)
                    await browser.close()
                    print(f"✅ {fanhao} 封面已保存: {save_path}")
                    return save_path
                else:
                    print(f"⚠ {fanhao} 封面下载失败，状态码: {response.status if response else '无响应'}")
                    await browser.close()
        except Exception as e:
            print(f"❌ {fanhao} 封面下载失败 (第 {attempt + 1}/{retries}): {e}")

    # 备用下载：使用 requests
    print(f"🔄 尝试使用 requests 下载 {fanhao} 封面: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://javday.app/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"✅ {fanhao} 封面已保存 (requests): {save_path}")
        return save_path
    except Exception as e:
        print(f"❌ {fanhao} 封面下载失败 (requests): {e}")
        return None

def extract_fanhao(filename):
    """从文件名中提取番号"""
    match = re.search(r"[A-Z]{2,5}-\d{2,5}", filename, re.I)
    return match.group(0).upper() if match else None

def get_relative_cover_path(cover_path, base_path):
    """计算封面相对于脚本运行目录的路径"""
    try:
        return os.path.relpath(cover_path, os.getcwd()).replace(os.sep, '/')
    except ValueError:
        # 跨分区时，使用绝对路径并规范化
        print(f"⚠ 跨分区路径: {cover_path} (基于 {base_path})")
        return os.path.abspath(cover_path).replace(os.sep, '/')

def extract_actor_name(title):
    """从标题中提取演员名字，取最后一个空格字符后面的内容"""
    if not title:
        return None
    
    # 查找最后一个空格
    last_space_index = title.rfind(' ')
    if last_space_index == -1:
        return None
    
    # 提取最后一个空格后的内容作为演员名字
    actor_name = title[last_space_index + 1:].strip()
    return actor_name if actor_name else None

async def process_videos(folder_path, cover_path, json_file="metadata.json"):
    """递归遍历文件夹及其子文件夹，提取番号，下载封面并保存元数据"""
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    metadata = load_existing_metadata(json_file)
    record_count = 0
    base_path = os.path.abspath(folder_path)

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(video_extensions):
                fanhao = extract_fanhao(filename)
                if not fanhao:
                    print(f"⚠ {filename} 未找到有效番号")
                    continue

                print(f"处理文件: {os.path.join(root, filename)} (番号: {fanhao})")
                # 跳过已存在于 metadata 的番号
                if fanhao in metadata:
                    print(f"✅ {fanhao} 已存在于元数据，跳过")
                    continue

                items = await search_javday(fanhao)
                if not items:
                    print(f"⚠ {fanhao} 没有找到结果")
                    continue

                # 只处理第一个搜索结果
                item = items[0]
                downloaded_cover_path = await download_cover(item["cover"], fanhao, filename, cover_path)
                if downloaded_cover_path:
                    # 封面路径：相对于脚本运行目录
                    relative_cover_path = get_relative_cover_path(downloaded_cover_path, base_path)
                    # 视频路径：绝对路径，规范化斜杠
                    absolute_video_path = os.path.abspath(os.path.join(root, filename)).replace(os.sep, '/')
                    # 提取演员名字
                    actor_name = extract_actor_name(item["title"])
                    metadata[fanhao] = {
                        "title": item["title"],
                        "cover_path": relative_cover_path,
                        "video_file": absolute_video_path,
                        "actor_name": actor_name
                    }
                    record_count += 1

                    # 每 10 条记录写入一次
                    if record_count >= 10:
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=4)
                        print(f"📝 已保存 {record_count} 条元数据至: {json_file}")
                        record_count = 0

    # 保存剩余的元数据
    if record_count > 0:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        print(f"📝 最终保存 {record_count} 条元数据至: {json_file}")

def load_existing_metadata(json_file):
    """加载现有的 metadata.json 文件"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def main():
    """主函数，使用配置文件中的路径"""
    video_paths = CONFIG.get("video_paths", ["/media"])
    cover_path = CONFIG.get("cover_path", "./covers")
    meta_config = CONFIG.get("meta_config", "metadata.json")
    
    # 确保封面目录存在
    os.makedirs(cover_path, exist_ok=True)
    
    print(f"📁 视频路径: {video_paths}")
    print(f"📁 封面保存路径: {cover_path}")
    print(f"📁 元数据文件: {meta_config}")
    
    total_processed = 0
    
    # 处理所有视频路径
    for video_path in video_paths:
        if not os.path.exists(video_path):
            print(f"❌ 视频路径不存在: {video_path}")
            continue
            
        print(f"🔄 开始处理路径: {video_path}")
        await process_videos(video_path, cover_path, meta_config)
        total_processed += 1
    
    print(f"✅ 所有路径处理完成，共处理 {total_processed} 个路径")

if __name__ == "__main__":
    asyncio.run(main())