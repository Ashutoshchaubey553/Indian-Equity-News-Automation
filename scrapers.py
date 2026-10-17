"""
Scraper Pipeline Module
Asynchronously fetches fresh stock news across multiple verified Indian financial sources:
  1. Google News RSS (India edition covering Moneycontrol, Economic Times, Livemint, Business Standard, etc.)
  2. Yahoo Finance RSS (.NS / .BO feeds)
Extracts headline, publisher source, pub_date, direct link, and clean 1-2 line summary.
"""

import re
import html
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import email.utils
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup

from deduplicator import clean_headline

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]


def format_relative_time(dt: datetime) -> str:
    """Return a human-friendly relative time string (e.g., '2 hours ago', 'Yesterday')."""
    now = datetime.now(timezone.utc)
    # Ensure dt is timezone aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 0:
        return "Just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return dt.strftime("%b %d, %Y")


def clean_summary_text(raw_html: str, title: str, source: str) -> str:
    """
    Cleans raw HTML description or synthesizes a high-context 1-2 line financial summary.
    """
    body_text = ""
    if raw_html:
        soup = BeautifulSoup(raw_html, "html.parser")
        # Remove script and style elements
        for s in soup(["script", "style"]):
            s.decompose()
        body_text = soup.get_text(separator=" ").strip()
        body_text = html.unescape(body_text)
        # Remove publisher tag often appended at end of Google News descriptions
        body_text = re.sub(r'\s*[-|–—]\s*' + re.escape(source) + r'.*$', '', body_text, flags=re.IGNORECASE).strip()
        body_text = re.sub(r'\s+', ' ', body_text).strip()

    # If body text has substantive content beyond repeating the headline
    title_lower = title.lower()
    clean_body_lower = body_text.lower()

    if len(body_text) > 40 and not clean_body_lower.startswith(title_lower):
        sentences = re.split(r'(?<=[.!?])\s+', body_text)
        if sentences:
            summary = " ".join(sentences[:2]).strip()
            if len(summary) > 220:
                summary = summary[:217].rsplit(' ', 1)[0] + "..."
            return summary

    # Otherwise, synthesize a contextual 1-to-2 line financial summary based on headline catalysts
    title_clean = title.strip()
    
    # Financial catalysts detection
    if any(k in title_lower for k in ["q1", "q2", "q3", "q4", "net profit", "results", "quarterly"]):
        action = "Details recent quarterly operational metrics, revenue trajectory, and bottom-line profit performance."
    elif any(k in title_lower for k in ["order", "deal", "contract", "partnership", "agreement"]):
        action = "Covers key commercial contracts, enterprise client wins, and strategic growth developments."
    elif any(k in title_lower for k in ["target", "upgrade", "downgrade", "brokerage", "buy rating", "sell rating"]):
        action = "Analyzes institutional brokerage perspective, fair value assessments, and price target revisions."
    elif any(k in title_lower for k in ["dividend", "buyback", "bonus", "split", "agm"]):
        action = "Outlines corporate action announcements, shareholder reward distributions, and capital allocation."
    elif any(k in title_lower for k in ["rallies", "rally", "surges", "jumps", "soars", "gain", "gains"]):
        action = "Reports intraday market momentum and trading volume surges driven by positive investor sentiment."
    elif any(k in title_lower for k in ["falls", "drops", "slumps", "plunges", "slides", "loss"]):
        action = "Examines selling pressure, sectoral headwinds, and risk factors impacting stock valuation."
    else:
        action = f"Market coverage by {source} providing situational context and corporate tracking for investors."

    return f"{title_clean}. {action}"


class NewsScraperPipeline:
    """
    Coordinates multi-source scraping for a given stock entity.
    """

    def __init__(self, timeout: float = 7.0):
        self.timeout = timeout

    async def fetch_google_news(self, client: httpx.AsyncClient, query: str, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch and parse Google News RSS for Indian equities."""
        encoded_query = httpx.URL("", params={"q": f"{query} when:{days}d"}).query.decode('utf-8').replace('q=', '')
        # Formulate search URL
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

        articles: List[Dict[str, Any]] = []
        try:
            resp = await client.get(url, headers={"User-Agent": USER_AGENTS[0]})
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                for item in root.findall(".//item"):
                    raw_title = item.findtext("title") or ""
                    link = item.findtext("link") or ""
                    pub_date_str = item.findtext("pubDate") or ""
                    raw_desc = item.findtext("description") or ""

                    # Extract source
                    source_elem = item.find("source")
                    source_name = source_elem.text if source_elem is not None and source_elem.text else ""

                    clean_title, pub_from_title = clean_headline(raw_title)
                    final_source = source_name or pub_from_title or "Google News"

                    # Parse date
                    try:
                        parsed_dt = email.utils.parsedate_to_datetime(pub_date_str)
                    except Exception:
                        parsed_dt = datetime.now(timezone.utc)

                    # Filter by recency
                    if parsed_dt < cutoff_date:
                        continue

                    summary = clean_summary_text(raw_desc, clean_title, final_source)

                    # Create a deterministic id
                    art_id = hashlib.md5(f"{clean_title}_{link}".encode("utf-8")).hexdigest()[:12]

                    articles.append({
                        "id": art_id,
                        "title": clean_title,
                        "source": final_source,
                        "link": link,
                        "published_at": parsed_dt.isoformat(),
                        "timestamp": parsed_dt.timestamp(),
                        "relative_time": format_relative_time(parsed_dt),
                        "summary": summary,
                        "raw_source": "google_news"
                    })
        except Exception as e:
            # Soft failure: log and return whatever succeeded
            print(f"[Scraper] Google News fetch warning: {e}")

        return articles

    async def fetch_yahoo_finance(self, client: httpx.AsyncClient, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch and parse Yahoo Finance RSS for NSE symbol."""
        articles: List[Dict[str, Any]] = []
        # Strip any existing suffixes and append .NS
        clean_sym = re.sub(r'(\.NS|\.BO)$', '', symbol.upper())
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean_sym}.NS"

        try:
            resp = await client.get(url, headers={"User-Agent": USER_AGENTS[1]})
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                for item in root.findall(".//item"):
                    raw_title = item.findtext("title") or ""
                    link = item.findtext("link") or ""
                    pub_date_str = item.findtext("pubDate") or ""
                    raw_desc = item.findtext("description") or ""

                    clean_title, pub_from_title = clean_headline(raw_title)
                    final_source = pub_from_title or "Yahoo Finance"

                    try:
                        parsed_dt = email.utils.parsedate_to_datetime(pub_date_str)
                    except Exception:
                        parsed_dt = datetime.now(timezone.utc)

                    if parsed_dt < cutoff_date:
                        continue

                    summary = clean_summary_text(raw_desc, clean_title, final_source)
                    art_id = hashlib.md5(f"{clean_title}_{link}".encode("utf-8")).hexdigest()[:12]

                    articles.append({
                        "id": art_id,
                        "title": clean_title,
                        "source": final_source,
                        "link": link,
                        "published_at": parsed_dt.isoformat(),
                        "timestamp": parsed_dt.timestamp(),
                        "relative_time": format_relative_time(parsed_dt),
                        "summary": summary,
                        "raw_source": "yahoo_finance"
                    })
        except Exception as e:
            print(f"[Scraper] Yahoo Finance fetch warning: {e}")

        return articles

    async def fetch_all(self, resolved_meta: Dict[str, Any], days: int = 7) -> List[Dict[str, Any]]:
        """
        Coordinates concurrent fetching from at least two sources.
        Guarantees fast retrieval and resilient error handling.
        """
        sym = resolved_meta.get("symbol", "")
        name = resolved_meta.get("canonical_name", sym)

        # Build search query for Google News
        query = f'"{name}" OR "{sym}" stock'

        all_articles: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            # Query Google News and Yahoo Finance simultaneously
            results = await asyncio.gather(
                self.fetch_google_news(client, query, days=days),
                self.fetch_yahoo_finance(client, sym, days=days),
                return_exceptions=True
            )

            for res in results:
                if isinstance(res, list):
                    all_articles.extend(res)

        return all_articles


# Global default instance
pipeline = NewsScraperPipeline()

if __name__ == "__main__":
    async def test():
        print("=== TESTING SCRAPER PIPELINE ===")
        mock_meta = {
            "symbol": "TCS",
            "canonical_name": "Tata Consultancy Services Ltd",
            "nse_ticker": "TCS"
        }
        t0 = datetime.now()
        arts = await pipeline.fetch_all(mock_meta, days=7)
        elapsed = (datetime.now() - t0).total_seconds()
        print(f"Fetched {len(arts)} total articles in {elapsed:.2f}s")
        sources_found = set(a["source"] for a in arts)
        print(f"Distinct sources found ({len(sources_found)}): {list(sources_found)[:5]}")
        for a in arts[:3]:
            print(f"- [{a['source']}] {a['title']} ({a['relative_time']})")
            print(f"  Summary: {a['summary']}")

    asyncio.run(test())
