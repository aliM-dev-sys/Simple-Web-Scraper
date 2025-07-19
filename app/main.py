from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from app.scraper import extract_text_from_url, extract_texts_from_urls
from typing import List

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

class ScrapeBatchRequest(BaseModel):
    urls: List[str]

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        text = await extract_text_from_url(request.url)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/scrape-batch")
async def scrape_batch(request: ScrapeBatchRequest):
    try:
        results = await extract_texts_from_urls(request.urls)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 