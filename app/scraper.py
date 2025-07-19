import httpx
from bs4 import BeautifulSoup
import asyncio
from collections import defaultdict
from urllib.parse import urlparse
import time

# Optional: Use readability-lxml for main content extraction
try:
    from readability import Document
    USE_READABILITY = True
except ImportError:
    USE_READABILITY = False

# Concurrency and per-domain limits
MAX_CONCURRENT_SCRAPES = 3  # Adjust as needed
MAX_SCRAPES_PER_DOMAIN = 3  # Adjust as needed
scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
domain_scrape_counts = defaultdict(int)

def get_domain(url):
    return urlparse(url).netloc

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove unwanted elements by tag
    for selector in ["nav", "footer", "header", "aside", "form", "script", "style", "noscript"]:
        for tag in soup.find_all(selector):
            tag.decompose()
    # Remove elements by common class/id keywords
    for cls in ["cookie", "banner", "advert", "ad", "subscribe", "newsletter", "popup"]:
        for tag in soup.find_all(class_=lambda x: x and cls in x.lower()):
            tag.decompose()
        for tag in soup.find_all(id=lambda x: x and cls in x.lower()):
            tag.decompose()
    return str(soup)

def get_visible_text(html: str) -> str:
    # Use readability if available for main content
    if USE_READABILITY:
        try:
            doc = Document(html)
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if len(text) > 100:
                return text
        except Exception:
            pass
    # Fallback: clean and extract all visible text
    cleaned_html = clean_html(html)
    soup = BeautifulSoup(cleaned_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text

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

async def scrape_static(url: str, retries=2, delay=3) -> str:
    for attempt in range(retries + 1):
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 429:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception("429 Too Many Requests (static)")
            response.raise_for_status()
            html = response.text
            return get_visible_text(html)

async def scrape_dynamic(url: str, retries=2, delay=5) -> str:
    from playwright.async_api import async_playwright
    for attempt in range(retries + 1):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            try:
                await page.goto(url, timeout=30000)
                # Wait for main content to load (main, article, or body)
                try:
                    await page.wait_for_selector("main, article, body", timeout=10000)
                except Exception:
                    pass
                text = await page.inner_text('body')
                if "Too Many Requests" in text or "429" in text:
                    if attempt < retries:
                        await browser.close()
                        await asyncio.sleep(delay)
                        continue
                    else:
                        await browser.close()
                        raise Exception("429 Too Many Requests (dynamic)")
                # Detect Cloudflare/anti-bot
                if "Verifying you are human" in text or "needs to review the security of your connection" in text:
                    await browser.close()
                    raise Exception("Blocked by anti-bot (Cloudflare or similar)")
                await browser.close()
                return text
            except Exception as e:
                await browser.close()
                if attempt < retries:
                    await asyncio.sleep(delay)
                    continue
                raise Exception(str(e))

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
