# Simple Web Scraper API

This is a FastAPI-based web scraper that extracts only the visible text content from a given URL and returns it as JSON.

## Features
- Accepts a URL via HTTP POST
- Returns only visible text (no images, scripts, or styles)
- Easy to deploy (Docker-ready)

## Usage

### Run Locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

### Run with Docker
```bash
docker build -t webscraper .
docker run -p 5000:5000 webscraper
```

### Example Request
```bash
curl -X POST "http://localhost:5000/scrape" -H "Content-Type: application/json" -d '{"url": "https://example.com"}'
```

### Response
```json
{
  "text": "...visible text content..."
}
``` 