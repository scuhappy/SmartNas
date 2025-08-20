import os
import re
import json
import asyncio
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
            }
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_selector(".videoBox", timeout=10000)
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

async def download_cover(url, fanhao, filename, save_dir="covers"):
    """下载封面并以视频文件名命名"""
    os.makedirs(save_dir, exist_ok=True)
    save_name = os.path.splitext(filename)[0]
    save_path = os.path.join(save_dir, f"{save_name}.jpg")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=15000)
            content = await response.body()
            with open(save_path, "wb") as f:
                f.write(content)
            await browser.close()
            print(f"✅ {fanhao} 封面已保存: {save_path}")
            return save_path
    except Exception as e:
        print(f"❌ 下载 {fanhao} 封面失败: {e}")
        return None

def extract_fanhao(filename):
    """从文件名中提取番号"""
    match = re.search(r"[A-Z]{2,5}-\d{2,5}", filename, re.I)
    return match.group(0).upper() if match else None

async def process_videos(folder_path, json_file="metadata.json"):
    """递归遍历文件夹及其子文件夹，提取番号，下载封面并保存元数据"""
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    metadata = {}

    # 递归遍历文件夹
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
                    metadata[fanhao] = {
                        "title": item["title"],
                        "cover_path": cover_path,
                        "video_file": os.path.join(root, filename)
                    }

    # 保存元数据到 JSON 文件
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    print(f"✅ 元数据已保存至: {json_file}")

async def main():
    # 指定视频文件夹路径
    folder_path = "G:\Videos"  # 请替换为你的视频文件夹路径
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹 {folder_path} 不存在")
        return

    await process_videos(folder_path)

if __name__ == "__main__":
    asyncio.run(main())