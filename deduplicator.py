"""
Deduplicator Module
Identifies and merges duplicate news coverage of the same underlying event across different sources.
Computes token Jaccard similarity, sequence matching, and entity overlap.
"""

import re
import difflib
from typing import List, Dict, Any, Tuple

# Common stop words and financial filler terms that shouldn't inflate similarity
STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just",
    "don", "should", "now", "today", "live", "update", "updates", "share", "shares",
    "stock", "stocks", "price", "prices", "market", "markets", "nse", "bse", "india"
}


def clean_headline(title: str) -> Tuple[str, str]:
    """
    Cleans a headline by stripping trailing publisher tags like ' - Moneycontrol'
    Returns (cleaned_title, extracted_publisher_if_found).
    """
    if not title:
        return "", ""

    extracted_pub = ""
    # Strip typical endings: ' - The Economic Times', ' | Livemint', ' : NDTV Profit'
    match = re.search(r'\s+[-|–—:]\s+([A-Za-z0-9\s\.\&]+)$', title)
    if match:
        extracted_pub = match.group(1).strip()
        cleaned = title[:match.start()].strip()
    else:
        cleaned = title.strip()

    # Clean HTML entities if any left
    cleaned = cleaned.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    return cleaned, extracted_pub


def extract_keywords(text: str) -> set:
    """Extract significant keywords from text for similarity comparison, preserving financial quarters, numbers and metrics."""
    if not text:
        return set()
    # Normalize numbers (e.g. 11,909 -> 11909)
    normalized = re.sub(r'(\d+),(\d+)', r'\1\2', text.lower())
    # Strip punctuation except alphanumeric
    cleaned = re.sub(r'[^\w\s]', ' ', normalized)
    words = cleaned.split()
    # Keep words longer than 1 char (keeping q1, q2, q3, q4, fy, etc.)
    return {w for w in words if w not in STOPWORDS and len(w) >= 2}


def compute_headline_similarity(title1: str, title2: str) -> float:
    """
    Calculates combined similarity using token Jaccard + sequence matching on cleaned titles.
    """
    c1, _ = clean_headline(title1)
    c2, _ = clean_headline(title2)

    tokens1 = extract_keywords(c1)
    tokens2 = extract_keywords(c2)

    if not tokens1 or not tokens2:
        return 0.0

    # Jaccard index
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    jaccard = len(intersection) / len(union) if union else 0.0

    # Check key financial anchors (quarters, major numbers like 11909 or percentage)
    common_keys = intersection.intersection({"q1", "q2", "q3", "q4", "fy24", "fy25", "fy26", "profit", "dividend", "deal"})
    bonus = 0.12 if common_keys else 0.0

    # Sequence similarity on normalized string
    norm1 = " ".join(sorted(tokens1))
    norm2 = " ".join(sorted(tokens2))
    seq_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()

    # Weighted blend (60% Jaccard token overlap, 40% sequence match) + anchor bonus
    score = (0.6 * jaccard) + (0.4 * seq_ratio) + bonus
    return min(1.0, score)


class NewsDeduplicator:
    """
    Deduplicates news articles from multiple sources, grouping overlapping stories
    while keeping the primary item and linking duplicate sources.
    """

    def __init__(self, similarity_threshold: float = 0.45):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw list of articles, cleans headlines, merges duplicates,
        and attaches cross-source references.
        """
        if not articles:
            return {
                "unique_articles": [],
                "stats": {
                    "total_fetched": 0,
                    "unique_count": 0,
                    "duplicates_removed": 0,
                    "dedup_percentage": 0.0
                }
            }

        # Clean all headlines first
        prepared_articles = []
        seen_urls = set()
        for art in articles:
            url = art.get("link", "").strip()
            if url and url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = art.get("title", "")
            cleaned_title, pub_from_title = clean_headline(raw_title)
            source = art.get("source") or pub_from_title or "Financial News"

            item = dict(art)
            item["title"] = cleaned_title if cleaned_title else raw_title
            item["source"] = source
            prepared_articles.append(item)

        # Cluster by story similarity
        unique_list: List[Dict[str, Any]] = []

        for item in prepared_articles:
            item_title = item.get("title", "")
            is_dup = False

            for existing in unique_list:
                existing_title = existing.get("title", "")
                sim = compute_headline_similarity(item_title, existing_title)

                if sim >= self.similarity_threshold:
                    # Found duplicate story
                    is_dup = True
                    existing.setdefault("duplicate_count", 0)
                    existing["duplicate_count"] += 1
                    existing.setdefault("other_coverage", [])
                    existing["other_coverage"].append({
                        "source": item.get("source", "Other Publisher"),
                        "title": item_title,
                        "link": item.get("link", ""),
                        "published_at": item.get("published_at", "")
                    })

                    # If duplicate item has a better/longer summary, adopt it
                    if len(item.get("summary", "")) > len(existing.get("summary", "")):
                        existing["summary"] = item["summary"]
                    break

            if not is_dup:
                clean_item = dict(item)
                clean_item["duplicate_count"] = 0
                clean_item["other_coverage"] = []
                unique_list.append(clean_item)

        total_fetched = len(articles)
        unique_count = len(unique_list)
        dups_removed = total_fetched - unique_count
        dedup_pct = round((dups_removed / total_fetched) * 100, 1) if total_fetched > 0 else 0.0

        return {
            "unique_articles": unique_list,
            "stats": {
                "total_fetched": total_fetched,
                "unique_count": unique_count,
                "duplicates_removed": dups_removed,
                "dedup_percentage": dedup_pct
            }
        }


# Global default instance
deduplicator = NewsDeduplicator()

if __name__ == "__main__":
    sample_news = [
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
            "title": "Tata Consultancy Services Q2 profit up 5% at Rs 11,909 crore - Livemint",
            "source": "Livemint",
            "link": "https://livemint.com/article3",
            "summary": "India's largest software exporter TCS posted 5% growth in net profit."
        },
        {
            "title": "TCS bags multi-million pound deal from British retailer Marks & Spencer",
            "source": "Business Standard",
            "link": "https://business-standard.com/article4",
            "summary": "TCS has expanded its strategic partnership with Marks and Spencer."
        }
    ]

    print("=== TESTING DEDUPLICATOR ===")
    res = deduplicator.deduplicate(sample_news)
    print(f"Stats: Fetched {res['stats']['total_fetched']}, Unique: {res['stats']['unique_count']}, Duplicates Removed: {res['stats']['duplicates_removed']}")
    for art in res["unique_articles"]:
        print(f"- {art['title']} (Source: {art['source']}, Duplicates: {art['duplicate_count']})")
        if art.get("other_coverage"):
            for other in art["other_coverage"]:
                print(f"    * Also covered by: {other['source']}")
