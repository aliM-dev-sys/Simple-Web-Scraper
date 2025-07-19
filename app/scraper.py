import httpx
from bs4 import BeautifulSoup
import asyncio

# Heuristic to detect if a website is dynamic
async def is_dynamic_website(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
        soup = BeautifulSoup(html, "html.parser")
        visible_text = soup.get_text(separator=" ", strip=True)
        # Heuristic 1: Very little visible text
        if len(visible_text) < 100:
            return True
        # Heuristic 2: Large number of script tags
        scripts = soup.find_all("script")
        if len(scripts) > 10:
            return True
        # Heuristic 3: React/Angular/Vue root divs
        if soup.find(id="root") or soup.find(id="app"):
            return True
        return False
    except Exception:
        return True  # If we can't determine, treat as dynamic for safety

def get_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # Get visible text
    text = soup.get_text(separator=" ", strip=True)
    return text

async def extract_text_from_url(url: str) -> str:
    if await is_dynamic_website(url):
        raise Exception("URL is dynamic, skipping.")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
    return get_visible_text(html)

async def extract_texts_from_urls(urls: list) -> list:
    results = []
    for url in urls:
        result = {"url": url}
        try:
            if await is_dynamic_website(url):
                result["error"] = "URL is dynamic, skipping."
            else:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    html = response.text
                result["text"] = get_visible_text(html)
        except Exception as e:
            result["error"] = str(e)
        results.append(result)
    return results 