"""
Watchlist and Daily Digest Manager Module
Manages investor watchlist items and compiles executive daily scheduled digests.
Persists watchlist items locally in JSON.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from company_resolver import resolver
from scrapers import pipeline
from deduplicator import deduplicator
from sentiment_analyzer import analyzer
from synthesizer import synthesizer

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
DIGESTS_FILE = os.path.join(DATA_DIR, "digests.json")

DEFAULT_WATCHLIST = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "TATAMOTORS"]


class WatchlistManager:
    """
    Manages user watchlist equities and generates structured daily briefing digests.
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_WATCHLIST, f, indent=2)
        if not os.path.exists(DIGESTS_FILE):
            with open(DIGESTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_watchlist(self) -> List[Dict[str, Any]]:
        """Return full metadata for all symbols in the watchlist."""
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                symbols = json.load(f)
        except Exception:
            symbols = DEFAULT_WATCHLIST

        results = []
        for sym in symbols:
            resolved = resolver.resolve(sym)
            if resolved["success"]:
                results.append(resolved["resolved"])
            else:
                results.append({"symbol": sym, "canonical_name": sym, "nse_ticker": sym})
        return results

    def add_symbol(self, query: str) -> Dict[str, Any]:
        """Add a resolved symbol to the watchlist."""
        res = resolver.resolve(query)
        if not res["success"]:
            return {"success": False, "error": f"Invalid stock: {res.get('error', 'Unknown')}"}

        target_sym = res["resolved"]["symbol"]
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                symbols = json.load(f)
        except Exception:
            symbols = []

        if target_sym not in symbols:
            symbols.append(target_sym)
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(symbols, f, indent=2)

        return {"success": True, "symbol": target_sym, "canonical_name": res["resolved"]["canonical_name"]}

    def remove_symbol(self, symbol: str) -> Dict[str, Any]:
        """Remove a symbol from the watchlist."""
        clean_sym = symbol.strip().upper()
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                symbols = json.load(f)
        except Exception:
            symbols = []

        if clean_sym in symbols:
            symbols.remove(clean_sym)
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(symbols, f, indent=2)
            return {"success": True, "removed": clean_sym}

        return {"success": False, "error": f"Symbol {clean_sym} not in watchlist."}

    async def generate_daily_digest(self) -> Dict[str, Any]:
        """
        Gathers latest news across all watchlist stocks and compiles an executive digest.
        """
        watchlist = self.get_watchlist()
        if not watchlist:
            return {"success": False, "error": "Watchlist is empty."}

        stock_briefs = []
        overall_bullish = 0
        overall_bearish = 0

        for stock in watchlist:
            sym = stock["symbol"]
            raw_arts = await pipeline.fetch_all(stock, days=3)
            # Deduplicate
            dedup_res = deduplicator.deduplicate(raw_arts)
            unique_arts = dedup_res["unique_articles"]

            # Sentiment analyze
            for a in unique_arts:
                a["sentiment"] = analyzer.analyze(a["title"], a.get("summary", ""))

            # Synthesize
            briefing = synthesizer.synthesize(stock, unique_arts)

            bull_pct = briefing["sentiment_breakdown"]["bullish_pct"]
            bear_pct = briefing["sentiment_breakdown"]["bearish_pct"]
            overall_bullish += bull_pct
            overall_bearish += bear_pct

            stock_briefs.append({
                "symbol": sym,
                "name": stock.get("canonical_name", sym),
                "article_count": len(unique_arts),
                "sentiment_tag": "Bullish" if bull_pct > 55 else ("Bearish" if bear_pct > 40 else "Neutral"),
                "bullish_pct": bull_pct,
                "bearish_pct": bear_pct,
                "takeaway": briefing["headline_takeaway"],
                "top_catalyst": briefing["key_catalysts"][0] if briefing["key_catalysts"] else None,
                "investor_watch": briefing["investor_watch"],
                "recent_articles": unique_arts[:3]
            })

        count = len(watchlist)
        avg_bull = round(overall_bullish / count) if count > 0 else 0
        avg_bear = round(overall_bearish / count) if count > 0 else 0

        market_tone = "Bullish" if avg_bull > 50 else ("Cautious / Defensive" if avg_bear > 35 else "Balanced / Rangebound")

        # Format markdown export
        md_lines = [
            f"# Daily Investor Watchlist Digest",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%A, %B %d, %Y - %I:%M %p UTC')}",
            f"**Overall Watchlist Bias:** {market_tone} ({avg_bull}% Bullish vs {avg_bear}% Bearish)",
            f"\n---\n"
        ]

        for s in stock_briefs:
            top_cat = s['top_catalyst']['summary'] if s['top_catalyst'] else 'No major catalyst'
            md_lines.append(f"### {s['name']} ({s['symbol']}) - {s['sentiment_tag']}")
            md_lines.append(f"- **What's Going On:** {s['takeaway']}")
            md_lines.append(f"- **Top Catalyst:** {top_cat}")
            md_lines.append(f"- **Key Watch Item:** {s['investor_watch']}")
            md_lines.append(f"- **Fresh Coverage:** {s['article_count']} verified articles")
            md_lines.append("")

        digest_record = {
            "digest_id": f"DIGEST-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_tone": market_tone,
            "avg_bullish_pct": avg_bull,
            "avg_bearish_pct": avg_bear,
            "stocks_covered": count,
            "stock_briefs": stock_briefs,
            "markdown_export": "\n".join(md_lines)
        }

        # Save to history
        try:
            with open(DIGESTS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
        history.insert(0, digest_record)
        # Keep latest 10 digests
        history = history[:10]
        with open(DIGESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        return {"success": True, "digest": digest_record}

    def get_latest_digest(self) -> Optional[Dict[str, Any]]:
        """Return the most recently generated digest from file."""
        try:
            with open(DIGESTS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                return history[0] if history else None
        except Exception:
            return None


# Global default instance
watchlist_mgr = WatchlistManager()

if __name__ == "__main__":
    async def test():
        print("=== TESTING WATCHLIST MANAGER ===")
        wl = watchlist_mgr.get_watchlist()
        print(f"Current watchlist ({len(wl)} items): {[w['symbol'] for w in wl]}")
        print("Generating sample digest (first 2 stocks)...")
        # Temporarily test with 2 stocks to be fast
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(["TCS", "INFY"], f)
        res = await watchlist_mgr.generate_daily_digest()
        if res["success"]:
            d = res["digest"]
            print(f"Digest generated: {d['digest_id']}, Tone: {d['market_tone']}")
            print(d["markdown_export"][:400] + "...")
        # Restore full watchlist
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_WATCHLIST, f, indent=2)

    asyncio.run(test())
