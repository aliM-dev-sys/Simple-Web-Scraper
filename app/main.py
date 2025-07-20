from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.scraper import extract_text_from_url, extract_texts_from_urls
from typing import List

app = FastAPI(
    title="Web Scraper API",
    description="Extracts main text content from static and dynamic web pages.",
    version="1.0.0"
)

# Enable CORS for all origins (or restrict as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your n8n server origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    url: str

class ScrapeBatchRequest(BaseModel):
    urls: List[str]

@app.post("/scrape", summary="Scrape a single URL")
async def scrape(request: ScrapeRequest):
    try:
        text = await extract_text_from_url(request.url)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/scrape-batch", summary="Scrape a batch of URLs")
async def scrape_batch(request: ScrapeBatchRequest):
    try:
        results = await extract_texts_from_urls(request.urls)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
