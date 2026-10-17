"""
Vercel Serverless Function Entry Point
Wraps the FastAPI application via Mangum for AWS Lambda / Vercel Python Runtime.
"""

import sys
import os

# Add the project root to Python path so modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure encoding for serverless environment
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from typing import Optional

from company_resolver import resolver
from scrapers import pipeline
from deduplicator import deduplicator
from sentiment_analyzer import analyzer
from synthesizer import synthesizer
from watchlist_manager import watchlist_mgr

app = FastAPI(
    title="Aura Intel - Stock News Lookup Automation",
    description="High-speed multi-source Indian equity news scraper, deduplicator, sentiment analyzer, and AI briefing generator.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@app.get("/api/health")
async def health_check():
    return {"status": "online", "service": "Aura Intel Stock News Automation", "runtime": "vercel-serverless"}


@app.get("/api/resolve")
async def resolve_input(q: str = Query(..., description="Stock ticker, company name, or alias")):
    """Resolves input query like 'TCS', 'Tata Consultancy', 'TCS.NS' to canonical equity entity."""
    res = resolver.resolve(q)
    return res


@app.get("/api/trending")
async def get_trending():
    """Returns popular Indian equities for quick lookup chips."""
    return [
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "IT"},
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy / Retail"},
        {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Auto"},
        {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG"},
        {"symbol": "ZOMATO", "name": "Zomato Ltd", "sector": "Consumer Tech"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom"}
    ]


@app.get("/api/news")
async def get_stock_news(
    q: str = Query(..., description="Stock name or ticker"),
    days: int = Query(7, ge=1, le=30, description="Recency filter in days"),
    source_filter: Optional[str] = Query(None, description="Optional publisher filter")
):
    """
    Main lookup automation endpoint:
      1. Resolves input query to canonical entity.
      2. Scrapes fresh news from at least two sources concurrently.
      3. Deduplicates overlapping stories.
      4. Analyzes sentiment per article.
      5. Synthesizes executive 'What's going on' overview.
      6. Sorts by recency (newest first).
    """
    # 1. Resolve input
    res_entity = resolver.resolve(q)
    if not res_entity["success"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": res_entity["error"],
                "raw_query": q,
                "suggestions": res_entity.get("suggestions", [])
            }
        )

    resolved_meta = res_entity["resolved"]

    # 2. Scrape across sources
    try:
        raw_articles = await pipeline.fetch_all(resolved_meta, days=days)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to fetch news feeds: {str(e)}",
                "resolved": resolved_meta
            }
        )

    if not raw_articles:
        return {
            "success": True,
            "resolved": resolved_meta,
            "match_type": res_entity.get("match_type"),
            "confidence": res_entity.get("confidence", 1.0),
            "articles": [],
            "stats": {
                "total_fetched": 0,
                "unique_count": 0,
                "duplicates_removed": 0,
                "dedup_percentage": 0.0,
                "distinct_sources": []
            },
            "briefing": synthesizer.synthesize(resolved_meta, []),
            "message": f"No fresh news articles found for {resolved_meta['canonical_name']} in the last {days} days."
        }

    # 3. Deduplicate
    dedup_res = deduplicator.deduplicate(raw_articles)
    unique_articles = dedup_res["unique_articles"]
    stats = dedup_res["stats"]

    # 4. Sentiment Analysis per article
    for art in unique_articles:
        art["sentiment"] = analyzer.analyze(art["title"], art.get("summary", ""))

    # 5. Sort by recency (newest first)
    unique_articles.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # 6. Apply optional source filter if requested
    if source_filter and source_filter.lower() != "all":
        unique_articles = [a for a in unique_articles if source_filter.lower() in a.get("source", "").lower()]

    # 7. Collect distinct source publishers
    distinct_sources = sorted(list(dict.fromkeys(a.get("source", "") for a in unique_articles if a.get("source"))))
    stats["distinct_sources"] = distinct_sources

    # 8. Synthesize AI 'What's going on' overview
    briefing = synthesizer.synthesize(resolved_meta, unique_articles)

    return {
        "success": True,
        "resolved": resolved_meta,
        "match_type": res_entity.get("match_type"),
        "confidence": res_entity.get("confidence", 1.0),
        "articles": unique_articles,
        "stats": stats,
        "briefing": briefing
    }


@app.get("/api/watchlist")
async def get_watchlist():
    """Get all watchlist stocks."""
    return watchlist_mgr.get_watchlist()


@app.post("/api/watchlist")
async def add_to_watchlist(symbol: str = Query(...)):
    """Add stock to watchlist."""
    return watchlist_mgr.add_symbol(symbol)


@app.delete("/api/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove stock from watchlist."""
    return watchlist_mgr.remove_symbol(symbol)


@app.get("/api/digest/latest")
async def get_latest_digest():
    """Retrieve the most recent compiled daily digest."""
    digest = watchlist_mgr.get_latest_digest()
    if not digest:
        return {"has_digest": False, "message": "No digest generated yet."}
    return {"has_digest": True, "digest": digest}


@app.post("/api/digest/generate")
async def generate_digest():
    """Trigger compilation of a fresh daily watchlist digest."""
    res = await watchlist_mgr.generate_daily_digest()
    return res


@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return HTMLResponse("<html><body><h1>Aura Intel API is online</h1></body></html>")


# Mangum handler for Vercel serverless
handler = Mangum(app, lifespan="off")
