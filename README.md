# Aura Intel // Indian Equity News & Market Intelligence Automation

A high-speed, multi-source Indian equity news lookup, deduplication, sentiment analysis, and executive market briefing automation engine.

### 🔴 [Live Demo → https://aura-intel-phi.vercel.app](https://aura-intel-phi.vercel.app)

---

## 🌟 Key Features

1. **Input Resolution & Canonical Mapping**
   - Resolves stock names, tickers, and exchange-suffixed identifiers (e.g., `TCS`, `Tata Consultancy`, `TCS.NS`, `TCS.BO`) into canonical equities with NSE ticker and BSE security code.
   - Built-in typo handling via fuzzy matching with confidence thresholds and fallback popular stock suggestions.

2. **Multi-Source Scraping**
   - Concurrently scrapes fresh financial news across multiple verified Indian market sources (Google News RSS, Yahoo Finance, Moneycontrol, The Economic Times, Livemint, Business Standard).
   - Recency filtering (last 24h, 3 days, 7 days, 14 days, 30 days) and automatic timestamp normalization.

3. **Intelligent Deduplication**
   - Automatically clusters and consolidates syndicated and duplicate stories using title normalization and Levenshtein/token-overlap algorithms.
   - Cross-references alternate coverage from other publishers in collapsible accordions.

4. **Financial Sentiment Analysis & AI Synthesis**
   - Analyzes sentiment per headline (`Bullish`, `Neutral`, `Bearish`) with market-weighted scoring and contextual financial rationale.
   - Generates an executive **"What's Going On"** briefing, sentiment distribution gauge, key business catalysts, and investor watch items.

5. **Watchlist & Daily Scheduled Digest**
   - Persistent watchlist management backed by local JSON.
   - On-demand and scheduled daily market digest generation with Markdown export, copy-to-clipboard, and download options.

6. **Full-Featured Web Dashboard & Interactive CLI**
   - Modern dark glassmorphism dashboard built with Vanilla HTML5, CSS3, and JavaScript.
   - Terminal CLI tool with ANSI color-coded reporting.

---

## 🚀 Quickstart

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/Ashutoshchaubey553/Indian-Equity-News-Automation.git
cd Indian-Equity-News-Automation
pip install -r requirements.txt
```

### 2. Run the Web Dashboard
Launch the FastAPI development server:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### 3. Run via CLI
Look up any company or ticker directly from the terminal:
```bash
# Look up by symbol
python cli.py TCS

# Look up by full name
python cli.py "Tata Consultancy"

# Look up with exchange suffix
python cli.py TCS.NS

# Generate daily watchlist digest
python cli.py --digest
```

### 4. Run the Test Suite
Run the test suite verifying input resolution, multi-source scraping, deduplication, sentiment scoring, AI synthesis, and recency sorting:
```bash
python test_suite.py
```

---

## 🏗️ Project Architecture

```
├── app.py                 # FastAPI backend server with REST endpoints and static file serving
├── cli.py                 # Interactive terminal CLI tool with rich formatting
├── company_resolver.py    # Canonical Indian equity dictionary and fuzzy resolver
├── scrapers.py            # Async multi-source scraper pipeline (Google News, Yahoo Finance)
├── deduplicator.py        # Duplicate headline clustering and syndication detection
├── sentiment_analyzer.py  # Rule-based financial sentiment scoring engine
├── synthesizer.py         # AI executive briefing and catalyst synthesizer
├── watchlist_manager.py   # Watchlist storage and daily digest generator
├── test_suite.py          # Comprehensive unit test suite
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html         # Web dashboard HTML
│   ├── style.css          # Dark glassmorphism styles and animations
│   └── app.js             # Client-side UI logic and API communication
└── data/
    ├── watchlist.json     # Watchlist symbols persistence
    └── digests.json       # Historical digest reports
```

---

## 📜 License
MIT License.
