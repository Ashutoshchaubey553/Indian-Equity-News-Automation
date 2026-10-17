"""
Financial Sentiment Analyzer Module
Analyzes headline and article summaries using a domain-tailored financial lexicon.
Provides:
  - Sentiment Tag: Positive (Bullish), Negative (Bearish), or Neutral
  - Sentiment Score: -1.0 to +1.0
  - Key Drivers / Rationale
"""

import re
from typing import Dict, Any, List

# High-conviction financial terminology weights
POSITIVE_TERMS: Dict[str, float] = {
    # Earnings & Performance
    "surge": 0.85, "surges": 0.85, "surged": 0.85, "surging": 0.85,
    "jump": 0.80, "jumps": 0.80, "jumped": 0.80,
    "rally": 0.80, "rallies": 0.80, "rallied": 0.80,
    "soar": 0.85, "soars": 0.85, "soared": 0.85,
    "beat": 0.75, "beats": 0.75, "beaten": 0.6,
    "record high": 0.90, "all-time high": 0.95, "multifold": 0.80,
    "profit rises": 0.85, "profit jumps": 0.90, "profit up": 0.80, "net profit rises": 0.90,
    "growth": 0.60, "strong growth": 0.85, "double-digit": 0.75,
    "revenue up": 0.75, "ebitda up": 0.80, "margin expansion": 0.85,

    # Corporate Actions & Wins
    "win": 0.70, "wins": 0.75, "won": 0.75, "winning": 0.70,
    "deal": 0.65, "deals": 0.65, "mega": 0.60,
    "order win": 0.85, "wins deal": 0.85, "secures contract": 0.85, "bags order": 0.85,
    "secures": 0.75, "contract": 0.60, "expansion": 0.65,
    "mega deal": 0.90, "partnership": 0.55, "acquisition": 0.55,
    "dividend": 0.65, "special dividend": 0.80, "bonus issue": 0.75, "buyback": 0.75,

    # Analyst & Market Stance
    "upgrade": 0.85, "upgrades": 0.85, "upgraded": 0.85,
    "target raised": 0.80, "buy rating": 0.80, "overweight": 0.70, "outperform": 0.75,
    "bullish": 0.85, "gain": 0.50, "gains": 0.55, "upbeat": 0.70, "optimism": 0.65,
    "recovery": 0.60, "turnaround": 0.75, "inflows": 0.60
}

NEGATIVE_TERMS: Dict[str, float] = {
    # Earnings & Performance
    "slump": 0.85, "slumps": 0.85, "slumped": 0.85,
    "plunge": 0.90, "plunges": 0.90, "plunged": 0.90,
    "tumble": 0.85, "tumbles": 0.85, "tumbled": 0.85,
    "drop": 0.65, "drops": 0.65, "dropped": 0.65,
    "fall": 0.60, "falls": 0.60, "fell": 0.60,
    "loss": 0.75, "losses": 0.75, "widens": 0.60, "loss widens": 0.85,
    "profit falls": 0.85, "profit drops": 0.85, "profit dips": 0.70,
    "miss": 0.70, "misses": 0.75, "missed": 0.70,
    "margin decline": 0.80, "headwinds": 0.65, "revenue down": 0.75,

    # Regulatory, Legal & Governance
    "penalty": 0.85, "penalized": 0.85, "fine": 0.70, "fined": 0.75,
    "probe": 0.85, "investigation": 0.80, "raid": 0.90, "searches": 0.70,
    "sebi": 0.50, "showcause": 0.80, "notice": 0.50, "fraud": 0.95,
    "default": 0.90, "insolvency": 0.95, "nclt": 0.65,

    # Analyst & Market Stance
    "downgrade": 0.85, "downgrades": 0.85, "downgraded": 0.85,
    "target cut": 0.80, "sell rating": 0.80, "underperform": 0.75,
    "bearish": 0.85, "selloff": 0.85, "sell-off": 0.85, "crash": 0.90,
    "sluggish": 0.65, "weak": 0.60, "weakness": 0.65, "disappointment": 0.75
}

NEGATION_TERMS = {"not", "no", "never", "despite", "fails", "fail", "failed", "unlikely"}


class SentimentAnalyzer:
    """
    Evaluates financial sentiment from headlines and summaries.
    """

    def analyze(self, title: str, summary: str = "") -> Dict[str, Any]:
        combined_text = f"{title}. {summary}".lower()

        # Tokenize and look for multi-word and single-word indicators
        pos_score = 0.0
        neg_score = 0.0
        pos_reasons: List[str] = []
        neg_reasons: List[str] = []

        # Check positive phrases/words
        for term, weight in POSITIVE_TERMS.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = list(re.finditer(pattern, combined_text))
            if matches:
                # Check for negation preceding within 3 words
                negated = False
                for m in matches:
                    start_idx = max(0, m.start() - 25)
                    prefix = combined_text[start_idx:m.start()]
                    if any(neg in prefix.split() for neg in NEGATION_TERMS):
                        negated = True
                        break

                if negated:
                    neg_score += weight * 0.8
                    neg_reasons.append(f"Negated {term}")
                else:
                    pos_score += weight
                    pos_reasons.append(term)

        # Check negative phrases/words
        for term, weight in NEGATIVE_TERMS.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = list(re.finditer(pattern, combined_text))
            if matches:
                negated = False
                for m in matches:
                    start_idx = max(0, m.start() - 25)
                    prefix = combined_text[start_idx:m.start()]
                    if any(neg in prefix.split() for neg in NEGATION_TERMS):
                        negated = True
                        break

                if negated:
                    pos_score += weight * 0.7
                    pos_reasons.append(f"Overcame {term}")
                else:
                    neg_score += weight
                    neg_reasons.append(term)

        # Compute net normalized sentiment score (-1.0 to 1.0)
        net_diff = pos_score - neg_score
        total_signals = pos_score + neg_score

        if total_signals == 0:
            score = 0.0
            tag = "Neutral"
            rationale = "Neutral / factual corporate reporting without strong market directional catalyst."
        else:
            # Dampen with hyperbolic tangent style curve
            normalized = net_diff / (1.0 + abs(net_diff))
            score = round(max(-1.0, min(1.0, normalized)), 2)

            if score >= 0.18:
                tag = "Positive"
                reasons_str = ", ".join(list(dict.fromkeys(pos_reasons))[:3])
                rationale = f"Bullish catalyst: mentions of {reasons_str}."
            elif score <= -0.18:
                tag = "Negative"
                reasons_str = ", ".join(list(dict.fromkeys(neg_reasons))[:3])
                rationale = f"Bearish headwind: mentions of {reasons_str}."
            else:
                tag = "Neutral"
                rationale = "Balanced or mixed market signals."

        return {
            "tag": tag,
            "score": score,
            "rationale": rationale,
            "signals": {
                "positive": list(dict.fromkeys(pos_reasons))[:4],
                "negative": list(dict.fromkeys(neg_reasons))[:4]
            }
        }


# Global default instance
analyzer = SentimentAnalyzer()

if __name__ == "__main__":
    test_headlines = [
        "TCS shares jump over 5% after Q2 results beat estimates; IT stocks rally",
        "TCS net profit drops 4% due to margin pressure and US tech spending slowdown",
        "Tata Consultancy Services board to consider interim dividend on October 10",
        "Sebi issues showcause notice to company over disclosure lapses; stock slides 3%",
        "Company wins mega multi-million dollar cloud deal with European bank"
    ]

    print("=== TESTING SENTIMENT ANALYZER ===")
    for h in test_headlines:
        res = analyzer.analyze(h)
        print(f"[{res['tag']} | Score: {res['score']:+.2f}] {h}")
        print(f"  -> Rationale: {res['rationale']}")
