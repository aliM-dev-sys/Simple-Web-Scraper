import httpx
from bs4 import BeautifulSoup
import asyncio
from collections import defaultdict
from urllib.parse import urlparse

# Concurrency and per-domain limits
MAX_CONCURRENT_SCRAPES = 3  # Adjust as needed
MAX_SCRAPES_PER_DOMAIN = 3  # Adjust as needed
scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
domain_scrape_counts = defaultdict(int)

def get_domain(url):
    return urlparse(url).netloc

async def is_dynamic_website(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
        soup = BeautifulSoup(html, "html.parser")
        visible_text = soup.get_text(separator=" ", strip=True)
        if len(visible_text) < 100:
            return True
        scripts = soup.find_all("script")
        if len(scripts) > 10:
            return True
        if soup.find(id="root") or soup.find(id="app"):
            return True
        return False
    except Exception:
        return True

def get_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text

async def scrape_static(url: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
    return get_visible_text(html)

async def scrape_dynamic(url: str) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        text = await page.inner_text('body')
        await browser.close()
        return text

async def extract_text_from_url(url: str) -> str:
    domain = get_domain(url)
    if domain_scrape_counts[domain] >= MAX_SCRAPES_PER_DOMAIN:
        raise Exception(f"Scrape limit reached for domain: {domain}")
    async with scrape_semaphore:
        try:
            # Try static first
            if not await is_dynamic_website(url):
                text = await scrape_static(url)
                domain_scrape_counts[domain] += 1
                return text
            # If dynamic, try Playwright
            text = await scrape_dynamic(url)
            domain_scrape_counts[domain] += 1
            return text
        except Exception as e:
            raise Exception(str(e))

async def extract_texts_from_urls(urls: list) -> list:
    tasks = []
    for url in urls:
        tasks.append(_extract_text_with_result(url))
    return await asyncio.gather(*tasks)

async def _extract_text_with_result(url):
    result = {"url": url}
    try:
        text = await extract_text_from_url(url)
        result["text"] = text
    except Exception as e:
        result["error"] = str(e)
    return result
