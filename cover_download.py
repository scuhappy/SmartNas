import os
import re
import json
import asyncio
import requests
from urllib.parse import quote
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

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

async def download_cover(url, fanhao, filename, save_dir="covers", retries=3):
    """下载封面并以视频文件名命名，支持重试和备用下载"""
    os.makedirs(save_dir, exist_ok=True)
    save_name = os.path.splitext(filename)[0]
    save_path = os.path.join(save_dir, f"{save_name}.jpg")

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
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
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

def get_relative_path(path, base_path):
    """计算相对路径，处理跨分区情况"""
    try:
        return os.path.relpath(path, base_path).replace(os.sep, '/')
    except ValueError:
        # 跨分区时，使用绝对路径并规范化
        print(f"⚠ 跨分区路径: {path} (基于 {base_path})")
        return os.path.abspath(path).replace(os.sep, '/')

async def process_videos(folder_path, json_file="metadata.json"):
    """递归遍历文件夹及其子文件夹，提取番号，下载封面并保存元数据"""
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    metadata = {}

    # 使用 folder_path 作为基准路径
    base_path = os.path.abspath(folder_path)

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(video_extensions):
                fanhao = extract_fanhao(filename)
                if not fanhao:
                    print(f"⚠ {filename} 未找到有效番号")
                    continue

                print(f"处理文件: {os.path.join(root, filename)} (番号: {fanhao})")
                items = await search_javday(fanhao)

                if not items:
                    print(f"⚠ {fanhao} 没有找到结果")
                    continue

                # 只处理第一个搜索结果
                item = items[0]
                cover_path = await download_cover(item["cover"], fanhao, filename)
                if cover_path:
                    # 计算相对于 folder_path 的路径
                    relative_cover_path = get_relative_path(cover_path, base_path)
                    relative_video_path = get_relative_path(os.path.join(root, filename), base_path)
                    metadata[fanhao] = {
                        "title": item["title"],
                        "cover_path": relative_cover_path,
                        "video_file": relative_video_path
                    }

    # 保存元数据到 JSON 文件
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    print(f"✅ 元数据已保存至: {json_file}")

async def main():
    # 指定视频文件夹路径
    folder_path = "G:/Videos"  # 请替换为你的视频文件夹路径
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹 {folder_path} 不存在")
        return

    await process_videos(folder_path)

if __name__ == "__main__":
    asyncio.run(main())