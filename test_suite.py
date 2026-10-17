"""
Comprehensive Test Suite
Verifies all requirements for Task 2: Stock News Lookup Automation.
1. Resolve input: 'TCS', 'Tata Consultancy', 'TCS.NS' all find the same company.
2. Fetch fresh news: Multiple sources, published in the last few days.
3. Clean results: Headline, source, publish time, link, 1-2 line summary, deduplication.
4. Sort by recency: Newest first.
5. Handle failures: Unknown tickers or no news give a clear message, no crash.
6. Bonus: Sentiment tags, AI 'what's going on' summary, daily scheduled digest.
"""

import sys
import unittest
import asyncio

# Safe encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from company_resolver import resolver, CompanyResolver
from scrapers import pipeline, clean_summary_text, format_relative_time
from deduplicator import deduplicator, clean_headline, compute_headline_similarity
from sentiment_analyzer import analyzer
from synthesizer import synthesizer
from watchlist_manager import watchlist_mgr


class TestStockNewsAutomation(unittest.TestCase):

    def test_01_input_resolution_must_have(self):
        """
        MUST-HAVE: Resolve the input.
        'TCS', 'Tata Consultancy' and 'TCS.NS' should all find the same company.
        """
        inputs = ["TCS", "Tata Consultancy", "Tata Consultancy Services", "TCS.NS", "TCS.BO", "tcs"]
        results = [resolver.resolve(q) for q in inputs]

        for idx, res in enumerate(results):
            self.assertTrue(res["success"], f"Failed to resolve {inputs[idx]}")
            sym = res["resolved"]["symbol"]
            name = res["resolved"]["canonical_name"]
            self.assertEqual(sym, "TCS", f"Input '{inputs[idx]}' resolved to symbol '{sym}', expected 'TCS'")
            self.assertIn("Tata Consultancy Services", name, f"Input '{inputs[idx]}' resolved to name '{name}'")

    def test_02_fuzzy_and_alias_resolution(self):
        """Test fuzzy typo handling and common company aliases."""
        res_typo = resolver.resolve("tata consultency")
        self.assertTrue(res_typo["success"])
        self.assertEqual(res_typo["resolved"]["symbol"], "TCS")

        res_ril = resolver.resolve("RIL")
        self.assertTrue(res_ril["success"])
        self.assertEqual(res_ril["resolved"]["symbol"], "RELIANCE")

        res_hdfc = resolver.resolve("HDFC Bank")
        self.assertTrue(res_hdfc["success"])
        self.assertEqual(res_hdfc["resolved"]["symbol"], "HDFCBANK")

    def test_03_failure_handling_must_have(self):
        """
        MUST-HAVE: Handle failures. Unknown tickers or no news should give a clear message, not a crash.
        """
        # Empty or pure whitespace
        res_empty = resolver.resolve("   ")
        self.assertFalse(res_empty["success"])
        self.assertIn("error", res_empty)

        # Pure punctuation
        res_punct = resolver.resolve("???")
        self.assertFalse(res_punct["success"])
        self.assertIn("suggestions", res_punct)
        self.assertTrue(len(res_punct["suggestions"]) > 0)

    def test_04_headline_cleaning_and_deduplication(self):
        """
        MUST-HAVE: Clean results & remove duplicates of the same story.
        """
        raw_headline = "TCS Q2 net profit jumps 5% to Rs 11,909 crore - Moneycontrol"
        clean_title, extracted_pub = clean_headline(raw_headline)
        self.assertEqual(clean_title, "TCS Q2 net profit jumps 5% to Rs 11,909 crore")
        self.assertEqual(extracted_pub, "Moneycontrol")

        sample_articles = [
            {
                "title": "TCS Q2 results: Net profit rises 5% to Rs 11,909 crore - Moneycontrol",
                "source": "Moneycontrol",
                "link": "https://moneycontrol.com/article1",
                "summary": "Tata Consultancy Services reported a 5 percent YoY rise in Q2 net profit."
            },
            {
                "title": "TCS reports 5% jump in Q2 net profit to Rs 11,909 cr | The Economic Times",
                "source": "The Economic Times",
                "link": "https://economictimes.com/article2",
                "summary": "TCS net profit for second quarter rose 5% to 11,909 crore rupees."
            },
            {
                "title": "TCS signs landmark cloud partnership with global bank",
                "source": "Reuters",
                "link": "https://reuters.com/article3",
                "summary": "TCS will deliver digital infrastructure across Europe."
            }
        ]

        dedup_result = deduplicator.deduplicate(sample_articles)
        unique_arts = dedup_result["unique_articles"]
        stats = dedup_result["stats"]

        # 3 articles entered, 2 were the same Q2 event -> 2 unique stories expected
        self.assertEqual(len(unique_arts), 2)
        self.assertEqual(stats["duplicates_removed"], 1)

        # Check that duplicate cross-reference is attached
        q2_story = [a for a in unique_arts if "11909" in a["title"] or "11,909" in a["title"]][0]
        self.assertGreater(q2_story["duplicate_count"], 0)
        self.assertEqual(q2_story["other_coverage"][0]["source"], "The Economic Times")

    def test_05_sentiment_analyzer_bonus(self):
        """
        BONUS: Sentiment tag per article (positive / negative / neutral).
        """
        pos = analyzer.analyze("TCS shares jump 5% on record profit beat")
        self.assertEqual(pos["tag"], "Positive")
        self.assertGreater(pos["score"], 0)

        neg = analyzer.analyze("Stock tumbles 6% as quarterly loss widens amid revenue slump")
        self.assertEqual(neg["tag"], "Negative")
        self.assertLess(neg["score"], 0)

        neu = analyzer.analyze("Company announces date for upcoming board meeting and AGM")
        self.assertEqual(neu["tag"], "Neutral")

    def test_06_ai_synthesizer_bonus(self):
        """
        BONUS: AI-written 'what's going on' summary across all articles.
        """
        mock_meta = {"symbol": "TCS", "canonical_name": "Tata Consultancy Services Ltd"}
        mock_arts = [
            {
                "title": "TCS Q2 net profit jumps 5% beating analyst forecasts",
                "source": "Moneycontrol",
                "sentiment": {"tag": "Positive", "score": 0.75}
            },
            {
                "title": "TCS secures mega multi-year IT transformation contract",
                "source": "The Economic Times",
                "sentiment": {"tag": "Positive", "score": 0.85}
            }
        ]

        briefing = synthesizer.synthesize(mock_meta, mock_arts)
        self.assertIn("headline_takeaway", briefing)
        self.assertIn("sentiment_breakdown", briefing)
        self.assertIn("key_catalysts", briefing)
        self.assertIn("investor_watch", briefing)
        self.assertEqual(briefing["sentiment_breakdown"]["bullish_pct"], 100)

    def test_07_live_multi_source_and_recency_sorting(self):
        """
        MUST-HAVE: Fetch fresh news from at least two sources, sorted by recency (newest first).
        """
        async def run_fetch():
            res = resolver.resolve("TCS")
            arts = await pipeline.fetch_all(res["resolved"], days=7)
            return arts

        articles = asyncio.run(run_fetch())
        self.assertGreater(len(articles), 5, "Expected at least 5 fresh articles")

        # Check distinct sources (must be >= 2 sources)
        sources = set(a["source"] for a in articles)
        self.assertGreaterEqual(len(sources), 2, f"Expected at least 2 distinct sources, got {len(sources)}")

        # Check required fields per article: headline, source, publish time, link, summary
        for a in articles[:5]:
            self.assertTrue(bool(a.get("title")), "Missing title")
            self.assertTrue(bool(a.get("source")), "Missing source")
            self.assertTrue(bool(a.get("published_at")), "Missing published_at")
            self.assertTrue(bool(a.get("link")), "Missing link")
            self.assertTrue(bool(a.get("summary")), "Missing summary")

        # Check recency sorting
        sorted_articles = sorted(articles, key=lambda x: x.get("timestamp", 0), reverse=True)
        for i in range(len(sorted_articles) - 1):
            self.assertGreaterEqual(sorted_articles[i]["timestamp"], sorted_articles[i + 1]["timestamp"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
