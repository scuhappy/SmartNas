import os
import re
from urllib.parse import quote
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://javday.app"

async def search_javday(fanhao: str):
    """使用 Playwright 访问 javday 搜索并解析结果"""
    url = f"{BASE_URL}/search?wd={quote(fanhao)}"
    results = []

    async with async_playwright() as p:
        # 启动无头浏览器（可设置为 headless=False 以调试）
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
            # 访问搜索页面并等待页面加载
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # 等待页面内容加载（根据需要调整选择器和超时时间）
            await page.wait_for_selector(".videoBox", timeout=10000)
            content = await page.content()

            # 使用 BeautifulSoup 解析页面
            soup = BeautifulSoup(content, "html.parser")
            for box in soup.select(".videoBox"):
                # 封面
                cover_div = box.select_one(".videoBox-cover")
                cover_url = None
                if cover_div and "style" in cover_div.attrs:
                    m = re.search(r"url\((.*?)\)", cover_div["style"])
                    if m:
                        cover_url = BASE_URL + m.group(1)

                # 标题
                title_span = box.select_one(".videoBox-info .title")
                title = title_span.get_text(strip=True) if title_span else None

                if cover_url and title:
                    results.append({"title": title, "cover": cover_url})

        except Exception as e:
            print(f"❌ 页面加载或解析失败: {e}")
        finally:
            await browser.close()

    return results

async def download_cover(url, fanhao, save_dir="covers"):
    """下载封面（使用 requests 保持与原脚本一致）"""
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{fanhao}.jpg")

    try:
        # 使用 Playwright 下载封面（可选）
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
        print(f"❌ 下载失败: {e}")
        return None

async def main():
    fanhao = 'IPX-922'
    items = await search_javday(fanhao)

    if not items:
        print("⚠ 没有找到结果")
    else:
        for item in items:
            print("番号标题:", item["title"])
            print("封面链接:", item["cover"])

            # 提取番号（确保文件名规范）
            m = re.search(r"[A-Z]{2,5}-\d{2,5}", item["title"], re.I)
            save_name = m.group(0) if m else fanhao
            await download_cover(item["cover"], save_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())