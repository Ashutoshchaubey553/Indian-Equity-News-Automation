"""
Command Line Interface (CLI)
Stock News Lookup Automation Tool
Usage:
  python cli.py TCS
  python cli.py "Tata Consultancy"
  python cli.py TCS.NS
  python cli.py --digest
"""

import sys
import asyncio
import argparse
from datetime import datetime

# Configure Windows console to handle UTF-8 / emojis safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from company_resolver import resolver
from scrapers import pipeline
from deduplicator import deduplicator
from sentiment_analyzer import analyzer
from synthesizer import synthesizer
from watchlist_manager import watchlist_mgr

# ANSI Color codes for clean terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


async def lookup_stock(query: str, days: int = 7, limit: int = 10):
    print(f"\n{BOLD}{CYAN}🔍 Resolving input:{RESET} '{query}'...")
    res = resolver.resolve(query)

    if not res["success"]:
        print(f"\n{RED}❌ Error:{RESET} {res['error']}")
        if "suggestions" in res:
            print(f"\n{YELLOW}Popular Indian Stocks:{RESET}")
            for s in res["suggestions"]:
                print(f"  • {s['symbol']} - {s['name']}")
        return

    meta = res["resolved"]
    match_type = res.get("match_type", "exact")
    print(f"{GREEN}✓ Resolved to:{RESET} {BOLD}{meta['canonical_name']}{RESET} (NSE: {BOLD}{meta['symbol']}{RESET}) [Match: {match_type}]")
    print(f"{DIM}Fetching fresh news from Google News, Yahoo Finance, and Indian financial portals...{RESET}")

    t0 = datetime.now()
    raw_articles = await pipeline.fetch_all(meta, days=days)
    elapsed = (datetime.now() - t0).total_seconds()

    if not raw_articles:
        print(f"\n{YELLOW}⚠️ No fresh news found for {meta['canonical_name']} in the last {days} days.{RESET}")
        print("Try expanding your search query or checking recent corporate filings.")
        return

    # Deduplicate
    dedup = deduplicator.deduplicate(raw_articles)
    unique_articles = dedup["unique_articles"]
    stats = dedup["stats"]

    # Sentiment analysis
    for art in unique_articles:
        art["sentiment"] = analyzer.analyze(art["title"], art.get("summary", ""))

    # Sort by recency (newest first)
    unique_articles.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # Executive "What's going on" briefing
    briefing = synthesizer.synthesize(meta, unique_articles)

    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}📈 AI EXECUTIVE BRIEFING: {meta['canonical_name']} ({meta['symbol']}){RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"{CYAN}Speed & Coverage:{RESET} Fetched {stats['total_fetched']} reports from multiple outlets in {elapsed:.2f}s")
    print(f"{CYAN}Deduplication:{RESET} Consolidated {stats['duplicates_removed']} duplicate stories ({stats['dedup_percentage']}% duplicate rate)")

    s_break = briefing["sentiment_breakdown"]
    print(f"{CYAN}Market Sentiment:{RESET} {GREEN}▲ {s_break['bullish_pct']}% Bullish{RESET} | {YELLOW}■ {s_break['neutral_pct']}% Neutral{RESET} | {RED}▼ {s_break['bearish_pct']}% Bearish{RESET}")
    print(f"\n{BOLD}Executive Takeaway:{RESET}\n{briefing['headline_takeaway']}")

    if briefing.get("key_catalysts"):
        print(f"\n{BOLD}Key Catalysts:{RESET}")
        for c in briefing["key_catalysts"]:
            tag_color = GREEN if c["impact"] == "Positive" else (RED if c["impact"] == "Negative" else YELLOW)
            print(f"  • {tag_color}[{c['impact']}]{RESET} {BOLD}{c['theme']}:{RESET} {c['summary']}")

    print(f"\n{BOLD}Investor Watch Item:{RESET} {briefing['investor_watch']}")

    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}📰 FRESH NEWS FEED (Newest First){RESET}")
    print(f"{BOLD}{'='*70}{RESET}")

    for idx, art in enumerate(unique_articles[:limit], 1):
        sent = art.get("sentiment", {})
        tag = sent.get("tag", "Neutral")
        color = GREEN if tag == "Positive" else (RED if tag == "Negative" else YELLOW)

        print(f"\n{BOLD}{idx}. {art['title']}{RESET}")
        print(f"   {color}[{tag}]{RESET} {DIM}Source:{RESET} {BOLD}{art['source']}{RESET} | {DIM}Published:{RESET} {art['relative_time']}")

        if art.get("duplicate_count", 0) > 0:
            other_sources = ", ".join([o["source"] for o in art.get("other_coverage", [])])
            print(f"   {YELLOW}⚑ Also reported by {art['duplicate_count']} source(s): {other_sources}{RESET}")

        print(f"   {DIM}Summary:{RESET} {art['summary']}")
        print(f"   {CYAN}Link:{RESET} {art['link']}")

    if len(unique_articles) > limit:
        print(f"\n{DIM}... and {len(unique_articles) - limit} more articles.{RESET}")


async def run_digest():
    print(f"\n{BOLD}{CYAN}📊 Generating Daily Investor Watchlist Digest...{RESET}")
    res = await watchlist_mgr.generate_daily_digest()
    if res["success"]:
        print(res["digest"]["markdown_export"])
    else:
        print(f"{RED}Error generating digest:{RESET} {res.get('error')}")


def main():
    parser = argparse.ArgumentParser(description="Stock News Lookup Automation Tool")
    parser.add_argument("query", nargs="?", default="", help="Stock ticker or company name (e.g. TCS, 'Tata Consultancy', TCS.NS)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to search back (default: 7)")
    parser.add_argument("--limit", type=int, default=8, help="Max articles to display (default: 8)")
    parser.add_argument("--digest", action="store_true", help="Generate daily watchlist digest")

    args = parser.parse_args()

    if args.digest:
        asyncio.run(run_digest())
    elif args.query:
        asyncio.run(lookup_stock(args.query, days=args.days, limit=args.limit))
    else:
        print(f"{YELLOW}Usage:{RESET} python cli.py <STOCK_NAME_OR_TICKER>")
        print("Example: python cli.py TCS")
        print("Example: python cli.py \"Tata Consultancy\"")
        print("Example: python cli.py TCS.NS")
        print("Example: python cli.py --digest")


if __name__ == "__main__":
    main()
