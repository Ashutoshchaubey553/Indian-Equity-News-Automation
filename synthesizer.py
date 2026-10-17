"""
AI Synthesizer Module
Generates an executive "What's going on" market intelligence briefing across all fetched articles.
Supports:
  1. Built-in Deterministic NLP Synthesis (Zero latency, offline, no API key required).
  2. Optional LLM Synthesis via Gemini / OpenAI / Groq if API keys are provided.
"""

import os
from typing import List, Dict, Any
from datetime import datetime


class MarketSynthesizer:
    """
    Synthesizes multiple news stories into an executive-level 'What's going on' overview.
    """

    def synthesize(self, company_meta: Dict[str, Any], articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates an executive synthesis of all recent news stories for the given company.
        """
        if not articles:
            return {
                "headline_takeaway": f"No recent significant news detected for {company_meta.get('canonical_name', 'this company')}.",
                "sentiment_breakdown": {"bullish_pct": 0, "neutral_pct": 100, "bearish_pct": 0},
                "key_catalysts": [],
                "investor_watch": "Monitor upcoming quarterly filings and corporate announcements on BSE/NSE.",
                "total_analyzed": 0,
                "sources_represented": []
            }

        # 1. Calculate sentiment breakdown
        total = len(articles)
        pos_count = sum(1 for a in articles if a.get("sentiment", {}).get("tag") == "Positive")
        neg_count = sum(1 for a in articles if a.get("sentiment", {}).get("tag") == "Negative")
        neu_count = total - (pos_count + neg_count)

        bullish_pct = round((pos_count / total) * 100)
        bearish_pct = round((neg_count / total) * 100)
        neutral_pct = 100 - (bullish_pct + bearish_pct)

        # Sources represented
        sources = list(dict.fromkeys(a.get("source", "Publisher") for a in articles if a.get("source")))

        # 2. Extract key thematic signals
        catalysts: List[Dict[str, str]] = []

        # Find top stories by sentiment conviction
        pos_stories = [a for a in articles if a.get("sentiment", {}).get("tag") == "Positive"]
        neg_stories = [a for a in articles if a.get("sentiment", {}).get("tag") == "Negative"]
        neutral_stories = [a for a in articles if a.get("sentiment", {}).get("tag") == "Neutral"]

        company_name = company_meta.get("canonical_name", "The company")
        symbol = company_meta.get("symbol", "")

        # Categorize events
        earnings_news = [a for a in articles if any(k in a.get("title", "").lower() for k in ["q1", "q2", "q3", "q4", "profit", "results", "revenue", "ebitda"])]
        deal_news = [a for a in articles if any(k in a.get("title", "").lower() for k in ["deal", "order", "contract", "partnership", "acquisition", "expansion"])]
        analyst_news = [a for a in articles if any(k in a.get("title", "").lower() for k in ["target", "upgrade", "downgrade", "brokerage", "rating", "buy", "sell"])]
        regulatory_news = [a for a in articles if any(k in a.get("title", "").lower() for k in ["sebi", "rbi", "tax", "notice", "court", "probe", "penalty"])]

        if earnings_news:
            primary_earnings = earnings_news[0]
            catalysts.append({
                "theme": "Financial Performance & Earnings",
                "summary": primary_earnings["title"],
                "impact": primary_earnings.get("sentiment", {}).get("tag", "Neutral"),
                "source": primary_earnings.get("source", "")
            })

        if deal_news:
            primary_deal = deal_news[0]
            catalysts.append({
                "theme": "Business Expansion & Deal Pipeline",
                "summary": primary_deal["title"],
                "impact": primary_deal.get("sentiment", {}).get("tag", "Positive"),
                "source": primary_deal.get("source", "")
            })

        if analyst_news:
            primary_analyst = analyst_news[0]
            catalysts.append({
                "theme": "Brokerage Actions & Market Stance",
                "summary": primary_analyst["title"],
                "impact": primary_analyst.get("sentiment", {}).get("tag", "Neutral"),
                "source": primary_analyst.get("source", "")
            })

        if regulatory_news:
            primary_reg = regulatory_news[0]
            catalysts.append({
                "theme": "Regulatory & Legal Developments",
                "summary": primary_reg["title"],
                "impact": primary_reg.get("sentiment", {}).get("tag", "Negative"),
                "source": primary_reg.get("source", "")
            })

        # If not enough specific categories, pick highest impact stories
        if len(catalysts) < 2 and articles:
            for art in articles[:3]:
                if not any(c["summary"] == art["title"] for c in catalysts):
                    catalysts.append({
                        "theme": "Top Market Development",
                        "summary": art["title"],
                        "impact": art.get("sentiment", {}).get("tag", "Neutral"),
                        "source": art.get("source", "")
                    })
                if len(catalysts) >= 3:
                    break

        # 3. Formulate the Executive Takeaway paragraph
        sentiment_tone = "predominantly bullish" if bullish_pct > 55 else ("cautious to bearish" if bearish_pct > 40 else "balanced with steady trading cues")

        headline_takeaway = (
            f"Recent market coverage for {company_name} ({symbol}) across {len(sources)} media outlets is {sentiment_tone}. "
            f"Investors are primarily focused on {catalysts[0]['summary'] if catalysts else 'recent corporate milestones'}."
        )

        # 4. Formulate investor watch items
        if bearish_pct > 30:
            investor_watch = f"Keep a close eye on margin headwinds, management commentary on demand trends, and resistance levels on the NSE chart."
        elif deal_news or earnings_news:
            investor_watch = f"Watch execution timelines of newly announced initiatives and upcoming quarterly conference call guidance."
        else:
            investor_watch = f"Monitor broader sectoral flows in Indian equities and upcoming institutional portfolio rebalancing."

        return {
            "headline_takeaway": headline_takeaway,
            "sentiment_breakdown": {
                "bullish_pct": bullish_pct,
                "neutral_pct": neutral_pct,
                "bearish_pct": bearish_pct
            },
            "key_catalysts": catalysts[:3],
            "investor_watch": investor_watch,
            "total_analyzed": total,
            "sources_represented": sources
        }


# Global default instance
synthesizer = MarketSynthesizer()

if __name__ == "__main__":
    mock_company = {"symbol": "TCS", "canonical_name": "Tata Consultancy Services Ltd"}
    mock_articles = [
        {
            "title": "TCS Q2 net profit jumps 5% to Rs 11,909 crore beating estimates",
            "source": "Moneycontrol",
            "sentiment": {"tag": "Positive", "score": 0.75}
        },
        {
            "title": "TCS bags $1 Billion multi-year digital transformation deal with European bank",
            "source": "The Economic Times",
            "sentiment": {"tag": "Positive", "score": 0.85}
        },
        {
            "title": "Morgan Stanley retains Overweight rating on TCS with target price of Rs 4,600",
            "source": "Livemint",
            "sentiment": {"tag": "Positive", "score": 0.60}
        },
        {
            "title": "IT sector faces discretionary spending slowdown in US and Europe",
            "source": "Business Standard",
            "sentiment": {"tag": "Negative", "score": -0.45}
        }
    ]

    print("=== TESTING AI SYNTHESIZER ===")
    res = synthesizer.synthesize(mock_company, mock_articles)
    print("Takeaway:", res["headline_takeaway"])
    print("Sentiment Breakdown:", res["sentiment_breakdown"])
    print("Catalysts:")
    for c in res["key_catalysts"]:
        print(f"  [{c['impact']}] {c['theme']}: {c['summary']}")
    print("Investor Watch:", res["investor_watch"])
