"""
Company Resolver Module
Resolves company names, tickers (NSE/BSE), and variations to canonical equity entities.
Handles inputs like:
  - "TCS"
  - "Tata Consultancy"
  - "Tata Consultancy Services"
  - "TCS.NS"
  - "TCS.BO"
"""

import re
import difflib
from typing import Optional, Dict, Any, List

# Curated registry of top Indian equities (Nifty 50, Next 50, and popular stocks)
COMPANIES_REGISTRY: List[Dict[str, Any]] = [
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Ltd",
        "nse": "TCS",
        "bse": "532540",
        "sector": "Information Technology",
        "aliases": [
            "tcs", "tata consultancy", "tata consultancy services", "tcs ltd",
            "tata consultancy service", "tcs limited"
        ],
        "keywords": ["Tata Consultancy Services", "TCS stock", "TCS Q2", "TCS Q3", "TCS Q4", "TCS Q1"]
    },
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Ltd",
        "nse": "RELIANCE",
        "bse": "500325",
        "sector": "Oil, Gas & Consumable Fuels / Retail / Telecom",
        "aliases": [
            "reliance", "ril", "reliance industries", "mukesh ambani reliance",
            "reliance ltd", "reliance industries limited", "jio reliance"
        ],
        "keywords": ["Reliance Industries", "RIL stock", "Reliance share"]
    },
    {
        "symbol": "INFY",
        "name": "Infosys Ltd",
        "nse": "INFY",
        "bse": "500209",
        "sector": "Information Technology",
        "aliases": [
            "infosys", "infy", "infosys ltd", "infosys limited", "narayana murthy infosys"
        ],
        "keywords": ["Infosys", "INFY stock", "Infosys share"]
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Ltd",
        "nse": "HDFCBANK",
        "bse": "500180",
        "sector": "Financial Services / Banking",
        "aliases": [
            "hdfc bank", "hdfcbank", "hdfc", "hdfc bnk", "housing development finance corporation"
        ],
        "keywords": ["HDFC Bank", "HDFCBANK stock", "HDFC Bank share"]
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Ltd",
        "nse": "ICICIBANK",
        "bse": "532174",
        "sector": "Financial Services / Banking",
        "aliases": [
            "icici bank", "icicibank", "icici", "icici bnk"
        ],
        "keywords": ["ICICI Bank", "ICICIBANK share"]
    },
    {
        "symbol": "TATAMOTORS",
        "name": "Tata Motors Ltd",
        "nse": "TATAMOTORS",
        "bse": "500570",
        "sector": "Automobile & Auto Components",
        "aliases": [
            "tata motors", "tatamotors", "tata motor", "ttmt", "jlr tata motors"
        ],
        "keywords": ["Tata Motors", "TATAMOTORS share", "JLR Tata"]
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "nse": "SBIN",
        "bse": "500112",
        "sector": "Financial Services / Public Bank",
        "aliases": [
            "sbin", "sbi", "state bank of india", "state bank", "sbi bank"
        ],
        "keywords": ["State Bank of India", "SBI stock", "SBIN share"]
    },
    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Ltd",
        "nse": "BHARTIARTL",
        "bse": "532454",
        "sector": "Telecommunication",
        "aliases": [
            "bharti airtel", "airtel", "bhartiartl", "bharti airtel ltd"
        ],
        "keywords": ["Bharti Airtel", "Airtel stock"]
    },
    {
        "symbol": "ITC",
        "name": "ITC Ltd",
        "nse": "ITC",
        "bse": "500875",
        "sector": "Fast Moving Consumer Goods (FMCG)",
        "aliases": [
            "itc", "itc ltd", "itc limited", "indian tobacco company"
        ],
        "keywords": ["ITC Ltd", "ITC share", "ITC stock"]
    },
    {
        "symbol": "LT",
        "name": "Larsen & Toubro Ltd",
        "nse": "LT",
        "bse": "500510",
        "sector": "Construction & Engineering",
        "aliases": [
            "l&t", "lt", "larsen & toubro", "larsen and toubro", "larsen & toubro ltd"
        ],
        "keywords": ["Larsen & Toubro", "L&T stock", "LT share"]
    },
    {
        "symbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank Ltd",
        "nse": "KOTAKBANK",
        "bse": "500247",
        "sector": "Financial Services / Banking",
        "aliases": [
            "kotak bank", "kotak mahindra bank", "kotak", "kotakbank"
        ],
        "keywords": ["Kotak Mahindra Bank", "Kotak Bank stock"]
    },
    {
        "symbol": "HINDUNILVR",
        "name": "Hindustan Unilever Ltd",
        "nse": "HINDUNILVR",
        "bse": "500696",
        "sector": "Fast Moving Consumer Goods (FMCG)",
        "aliases": [
            "hul", "hindustan unilever", "hindunilvr", "unilever india"
        ],
        "keywords": ["Hindustan Unilever", "HUL stock"]
    },
    {
        "symbol": "AXISBANK",
        "name": "Axis Bank Ltd",
        "nse": "AXISBANK",
        "bse": "532215",
        "sector": "Financial Services / Banking",
        "aliases": [
            "axis bank", "axisbank", "axis"
        ],
        "keywords": ["Axis Bank", "Axis Bank share"]
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Ltd",
        "nse": "BAJFINANCE",
        "bse": "500034",
        "sector": "Financial Services / NBFC",
        "aliases": [
            "bajaj finance", "bajfinance", "bajaj finserv", "bajaj fin"
        ],
        "keywords": ["Bajaj Finance", "Bajaj Finance share"]
    },
    {
        "symbol": "WIPRO",
        "name": "Wipro Ltd",
        "nse": "WIPRO",
        "bse": "507685",
        "sector": "Information Technology",
        "aliases": [
            "wipro", "wipro ltd", "wipro limited", "azim premji wipro"
        ],
        "keywords": ["Wipro", "Wipro stock", "Wipro share"]
    },
    {
        "symbol": "HCLTECH",
        "name": "HCL Technologies Ltd",
        "nse": "HCLTECH",
        "bse": "532281",
        "sector": "Information Technology",
        "aliases": [
            "hcl tech", "hcl technologies", "hcltech", "hcl"
        ],
        "keywords": ["HCL Technologies", "HCL Tech share"]
    },
    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India Ltd",
        "nse": "MARUTI",
        "bse": "532500",
        "sector": "Automobile & Auto Components",
        "aliases": [
            "maruti", "maruti suzuki", "maruti suzuki india"
        ],
        "keywords": ["Maruti Suzuki", "Maruti share"]
    },
    {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical Industries Ltd",
        "nse": "SUNPHARMA",
        "bse": "524715",
        "sector": "Healthcare / Pharmaceuticals",
        "aliases": [
            "sun pharma", "sunpharma", "sun pharmaceutical"
        ],
        "keywords": ["Sun Pharma", "Sun Pharma share"]
    },
    {
        "symbol": "ADANIENT",
        "name": "Adani Enterprises Ltd",
        "nse": "ADANIENT",
        "bse": "512599",
        "sector": "Metals & Mining / Conglomerate",
        "aliases": [
            "adani enterprises", "adanient", "adani group", "adani ent"
        ],
        "keywords": ["Adani Enterprises", "Adani share", "Adani Enterprises stock"]
    },
    {
        "symbol": "ADANIPORTS",
        "name": "Adani Ports and Special Economic Zone Ltd",
        "nse": "ADANIPORTS",
        "bse": "532921",
        "sector": "Services / Transport Infrastructure",
        "aliases": [
            "adani ports", "adaniports", "adani port", "apsez"
        ],
        "keywords": ["Adani Ports", "APSEZ stock"]
    },
    {
        "symbol": "TATASTEEL",
        "name": "Tata Steel Ltd",
        "nse": "TATASTEEL",
        "bse": "500470",
        "sector": "Metals & Mining",
        "aliases": [
            "tata steel", "tatasteel", "tata iron and steel", "tisco"
        ],
        "keywords": ["Tata Steel", "Tata Steel share"]
    },
    {
        "symbol": "ZOMATO",
        "name": "Zomato Ltd",
        "nse": "ZOMATO",
        "bse": "543320",
        "sector": "Consumer Services / Food Delivery",
        "aliases": [
            "zomato", "zomato ltd", "blinkit zomato", "deepinder goyal zomato"
        ],
        "keywords": ["Zomato", "Zomato share", "Blinkit Zomato"]
    },
    {
        "symbol": "PAYTM",
        "name": "One97 Communications Ltd (Paytm)",
        "nse": "PAYTM",
        "bse": "543396",
        "sector": "Financial Technology",
        "aliases": [
            "paytm", "one97", "one97 communications", "paytm payments"
        ],
        "keywords": ["Paytm", "One97 Communications", "Paytm share"]
    },
    {
        "symbol": "JIOFIN",
        "name": "Jio Financial Services Ltd",
        "nse": "JIOFIN",
        "bse": "543940",
        "sector": "Financial Services",
        "aliases": [
            "jio financial", "jiofin", "jio financial services", "jio finance"
        ],
        "keywords": ["Jio Financial Services", "JIOFIN share"]
    },
    {
        "symbol": "NTPC",
        "name": "NTPC Ltd",
        "nse": "NTPC",
        "bse": "532555",
        "sector": "Power Generation",
        "aliases": [
            "ntpc", "ntpc ltd", "national thermal power"
        ],
        "keywords": ["NTPC Ltd", "NTPC share"]
    },
    {
        "symbol": "POWERGRID",
        "name": "Power Grid Corporation of India Ltd",
        "nse": "POWERGRID",
        "bse": "532898",
        "sector": "Power Transmission",
        "aliases": [
            "power grid", "powergrid", "pgcil", "power grid corp"
        ],
        "keywords": ["Power Grid", "POWERGRID share"]
    },
    {
        "symbol": "ONGC",
        "name": "Oil and Natural Gas Corporation Ltd",
        "nse": "ONGC",
        "bse": "500312",
        "sector": "Oil & Natural Gas",
        "aliases": [
            "ongc", "oil and natural gas corporation"
        ],
        "keywords": ["ONGC", "ONGC share"]
    },
    {
        "symbol": "TITAN",
        "name": "Titan Company Ltd",
        "nse": "TITAN",
        "bse": "500114",
        "sector": "Consumer Durables / Gems & Jewellery",
        "aliases": [
            "titan", "titan company", "tanishq titan", "titan watches"
        ],
        "keywords": ["Titan Company", "Titan share"]
    },
    {
        "symbol": "COALINDIA",
        "name": "Coal India Ltd",
        "nse": "COALINDIA",
        "bse": "533278",
        "sector": "Metals & Mining",
        "aliases": [
            "coal india", "coalindia", "cil"
        ],
        "keywords": ["Coal India", "Coal India share"]
    },
    {
        "symbol": "ULTRACEMCO",
        "name": "UltraTech Cement Ltd",
        "nse": "ULTRACEMCO",
        "bse": "532538",
        "sector": "Construction Materials / Cement",
        "aliases": [
            "ultratech cement", "ultracemco", "ultratech", "birla cement"
        ],
        "keywords": ["UltraTech Cement", "UltraTech share"]
    },
    {
        "symbol": "HAL",
        "name": "Hindustan Aeronautics Ltd",
        "nse": "HAL",
        "bse": "541154",
        "sector": "Aerospace & Defence",
        "aliases": [
            "hal", "hindustan aeronautics", "hindustan aeronautics ltd"
        ],
        "keywords": ["Hindustan Aeronautics", "HAL share", "HAL stock"]
    },
    {
        "symbol": "BEL",
        "name": "Bharat Electronics Ltd",
        "nse": "BEL",
        "bse": "500049",
        "sector": "Aerospace & Defence",
        "aliases": [
            "bel", "bharat electronics", "bharat electronics ltd"
        ],
        "keywords": ["Bharat Electronics", "BEL share"]
    },
    {
        "symbol": "NESTLEIND",
        "name": "Nestle India Ltd",
        "nse": "NESTLEIND",
        "bse": "500790",
        "sector": "Fast Moving Consumer Goods (FMCG)",
        "aliases": [
            "nestle", "nestle india", "nestleind", "maggi nestle"
        ],
        "keywords": ["Nestle India", "Nestle share"]
    },
    {
        "symbol": "VEDL",
        "name": "Vedanta Ltd",
        "nse": "VEDL",
        "bse": "500295",
        "sector": "Metals & Mining",
        "aliases": [
            "vedanta", "vedl", "vedanta resources"
        ],
        "keywords": ["Vedanta Ltd", "Vedanta share"]
    },
    {
        "symbol": "INDIGO",
        "name": "InterGlobe Aviation Ltd (IndiGo)",
        "nse": "INDIGO",
        "bse": "539448",
        "sector": "Aviation",
        "aliases": [
            "indigo", "interglobe aviation", "indigo airlines"
        ],
        "keywords": ["IndiGo airlines", "InterGlobe Aviation"]
    }
]


def clean_query_string(raw: str) -> str:
    """Normalize input string by removing special characters, exchange suffixes, and whitespace."""
    if not raw:
        return ""
    s = raw.strip()
    # Strip common exchange suffixes like .NS, .BO, .BSE, :NSE, :BSE, -EQ
    s = re.sub(r'(\.NS|\.BO|\.BSE|\.NSE|:NSE|:BSE|-EQ)$', '', s, flags=re.IGNORECASE)
    # Strip leading/trailing symbols or punctuation
    s = re.sub(r'^[^\w]+|[^\w]+$', '', s)
    # Collapse multiple whitespaces
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def normalize_for_matching(text: str) -> str:
    """Lowercase and remove company suffixes for fuzzy comparison."""
    if not text:
        return ""
    t = text.lower()
    # Remove suffixes like .ns, .bo
    t = re.sub(r'(\.ns|\.bo|\.bse|\.nse|:nse|:bse|-eq)$', '', t)
    # Remove legal suffixes
    t = re.sub(r'\b(ltd|limited|corp|corporation|inc|incorporated|pvt|co|company)\b', '', t)
    # Remove punctuation
    t = re.sub(r'[^\w\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


class CompanyResolver:
    """
    Resolves arbitrary user input (ticker, short code, full name, or typo)
    to a standardized equity record.
    """

    def __init__(self, registry: Optional[List[Dict[str, Any]]] = None):
        self.registry = registry or COMPANIES_REGISTRY
        # Build lookup indices for fast O(1) matching
        self.symbol_index: Dict[str, Dict[str, Any]] = {}
        self.alias_index: Dict[str, Dict[str, Any]] = {}

        for item in self.registry:
            sym = item["symbol"].upper()
            self.symbol_index[sym] = item
            self.symbol_index[item.get("nse", sym).upper()] = item
            if "bse" in item and item["bse"]:
                self.symbol_index[str(item["bse"])] = item

            # Index all aliases
            for alias in item.get("aliases", []):
                norm_alias = normalize_for_matching(alias)
                if norm_alias:
                    self.alias_index[norm_alias] = item

            # Index the canonical name
            norm_name = normalize_for_matching(item["name"])
            if norm_name:
                self.alias_index[norm_name] = item

    def resolve(self, raw_input: str) -> Dict[str, Any]:
        """
        Main entry point to resolve an input string.
        Guarantees that 'TCS', 'Tata Consultancy', 'TCS.NS' all return the identical canonical entity.
        Never throws an exception on weird or unknown queries.
        """
        if not raw_input or not raw_input.strip():
            return {
                "success": False,
                "error": "Please enter a stock name or ticker (e.g. TCS, Reliance, Infosys).",
                "raw_query": raw_input,
                "resolved": None
            }

        cleaned = clean_query_string(raw_input)
        upper_clean = cleaned.upper()
        norm_query = normalize_for_matching(raw_input)

        # 1. Exact match on Symbol / NSE / BSE code
        if upper_clean in self.symbol_index:
            target = self.symbol_index[upper_clean]
            return self._build_success_response(target, raw_input, match_type="exact_symbol")

        # 2. Exact match on normalized alias or company name
        if norm_query in self.alias_index:
            target = self.alias_index[norm_query]
            return self._build_success_response(target, raw_input, match_type="exact_alias")

        # 3. Substring / Token containment match
        # Check if query matches all words in an alias or vice versa
        query_words = set(norm_query.split())
        best_candidate = None
        best_score = 0.0

        for item in self.registry:
            # Check all aliases of this item
            for alias in item.get("aliases", []) + [item["name"]]:
                norm_alias = normalize_for_matching(alias)
                alias_words = set(norm_alias.split())

                # If all query words are contained in the alias words (e.g. "tata consultancy" in "tata consultancy services")
                if query_words and query_words.issubset(alias_words):
                    overlap_ratio = len(query_words) / len(alias_words)
                    if overlap_ratio > best_score:
                        best_score = overlap_ratio
                        best_candidate = item

        if best_candidate and best_score >= 0.5:
            return self._build_success_response(best_candidate, raw_input, match_type="token_containment")

        # 4. Fuzzy Match (Levenshtein / SequenceMatcher) across all aliases & names
        candidates_pool = []
        for item in self.registry:
            for alias in item.get("aliases", []) + [item["name"], item["symbol"]]:
                candidates_pool.append((normalize_for_matching(alias), item))

        best_fuzzy = None
        best_ratio = 0.0
        for norm_cand, item in candidates_pool:
            ratio = difflib.SequenceMatcher(None, norm_query, norm_cand).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_fuzzy = item

        # If similarity is sufficiently high (> 0.72)
        if best_fuzzy and best_ratio >= 0.72:
            return self._build_success_response(best_fuzzy, raw_input, match_type="fuzzy_match", confidence=round(best_ratio, 2))

        # 5. Fallback for unlisted / arbitrary tickers (e.g. ZOMATO, SUZLON, CDSL, or any custom valid stock)
        # If the input looks like a valid ticker or company name (letters/numbers, at least 2 chars)
        if len(cleaned) >= 2 and re.match(r'^[A-Za-z0-9\s\.\-&]+$', cleaned):
            ticker_guess = upper_clean
            name_guess = cleaned.title()
            custom_entity = {
                "symbol": ticker_guess,
                "name": f"{name_guess} (Custom Ticker)",
                "nse": ticker_guess,
                "bse": "",
                "sector": "Indian Equities",
                "aliases": [cleaned.lower()],
                "keywords": [f"{name_guess} stock", f"{ticker_guess} share", f"{ticker_guess} NSE"]
            }
            return {
                "success": True,
                "is_custom": True,
                "match_type": "dynamic_fallback",
                "raw_query": raw_input,
                "confidence": 0.75,
                "resolved": {
                    "symbol": ticker_guess,
                    "canonical_name": name_guess,
                    "nse_ticker": ticker_guess,
                    "bse_code": "",
                    "sector": "Equities",
                    "search_query": f"{cleaned} stock OR {ticker_guess} NSE",
                    "news_search_terms": [cleaned, f"{ticker_guess} stock", f"{cleaned} share"]
                }
            }

        # 6. Completely unrecognized or invalid
        return {
            "success": False,
            "error": f"Could not recognize '{raw_input}'. Try typing a company name like 'TCS', 'Reliance', 'Infosys' or ticker 'TATAMOTORS.NS'.",
            "raw_query": raw_input,
            "suggestions": [
                {"symbol": "TCS", "name": "Tata Consultancy Services Ltd"},
                {"symbol": "RELIANCE", "name": "Reliance Industries Ltd"},
                {"symbol": "INFY", "name": "Infosys Ltd"},
                {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd"},
                {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd"}
            ],
            "resolved": None
        }

    def _build_success_response(self, item: Dict[str, Any], raw_query: str, match_type: str, confidence: float = 1.0) -> Dict[str, Any]:
        """Format resolved entity for consumer modules."""
        sym = item["symbol"]
        primary_name = item["name"]
        keywords = item.get("keywords", [primary_name, f"{sym} stock"])
        # Formulate optimal search query for Google News and Indian financial outlets
        search_query = f'("{primary_name}" OR "{sym}" stock OR "{sym}" NSE)'

        return {
            "success": True,
            "is_custom": False,
            "match_type": match_type,
            "confidence": confidence,
            "raw_query": raw_query,
            "resolved": {
                "symbol": sym,
                "canonical_name": primary_name,
                "nse_ticker": item.get("nse", sym),
                "bse_code": item.get("bse", ""),
                "sector": item.get("sector", "Equities"),
                "search_query": search_query,
                "news_search_terms": [primary_name, sym] + keywords[:2]
            }
        }


# Global default instance
resolver = CompanyResolver()

if __name__ == "__main__":
    # Test cases from user requirements
    test_inputs = [
        "TCS",
        "Tata Consultancy",
        "Tata Consultancy Services",
        "TCS.NS",
        "TCS.BO",
        "tcs",
        "Reliance",
        "RIL",
        "RELIANCE.NS",
        "infy",
        "Infosys",
        "HDFC Bank",
        "hdfcbank.ns",
        "Tata Motors",
        "tatamotors",
        "tata consultency",  # typo test
        "relience",          # typo test
        "SUZLON.NS",         # dynamic unlisted
        "xyznonexistent999"  # invalid test
    ]

    print("=== TESTING COMPANY RESOLVER ===")
    for q in test_inputs:
        res = resolver.resolve(q)
        if res["success"]:
            r = res["resolved"]
            print(f"[{q}] -> Symbol: {r['symbol']} | Name: {r['canonical_name']} (Match: {res['match_type']}, Conf: {res.get('confidence', 1.0)})")
        else:
            print(f"[{q}] -> ERROR: {res['error']}")
