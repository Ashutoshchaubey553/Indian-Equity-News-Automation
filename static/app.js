/**
 * AURA INTEL // Client Application Logic
 * Interactive Stock News Lookup, Multi-Source Scraping, Deduplication HUD,
 * Sentiment Breakdown, Speech Synthesis, and Watchlist Digests.
 */

// Application State
const state = {
  currentQuery: "TCS",
  resolvedEntity: null,
  articles: [],
  filteredArticles: [],
  stats: null,
  briefing: null,
  watchlist: [],
  isSpeaking: false,
  speechUtterance: null
};

// Dynamic DOM Elements Access via Proxy
const elements = new Proxy({}, {
  get: (_, id) => document.getElementById(id)
});

// Resilient Bootstrapping (handles both loading and interactive/complete readyState)
function bootApp() {
  setupEventListeners();
  fetchWatchlist();
  performSearch("TCS");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootApp);
} else {
  bootApp();
}

function setupEventListeners() {
  // Input Clear Button toggle
  elements.stockInput.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    elements.clearInputBtn.style.display = val ? "block" : "none";
    handleAutocomplete(val);
  });

  elements.clearInputBtn.addEventListener("click", () => {
    elements.stockInput.value = "";
    elements.clearInputBtn.style.display = "none";
    elements.suggestionsDropdown.style.display = "none";
    elements.stockInput.focus();
  });

  // Search submission
  elements.searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = elements.stockInput.value.trim();
    if (query) {
      elements.suggestionsDropdown.style.display = "none";
      performSearch(query);
    }
  });

  // Global key shortcut: '/' to focus search input
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== elements.stockInput && document.activeElement !== elements.addWatchlistInput) {
      e.preventDefault();
      elements.stockInput.focus();
      elements.stockInput.select();
    }
    if (e.key === "Escape") {
      elements.suggestionsDropdown.style.display = "none";
      elements.watchlistModal.classList.add("hidden");
    }
  });

  // Hide suggestions when clicking outside
  document.addEventListener("click", (e) => {
    if (!elements.searchForm.contains(e.target)) {
      elements.suggestionsDropdown.style.display = "none";
    }
  });

  // Trending Chips Clicks
  elements.trendingChipsList.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip-pill");
    if (!btn) return;
    const sym = btn.getAttribute("data-symbol");
    if (sym) {
      document.querySelectorAll(".chip-pill").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      elements.stockInput.value = sym;
      elements.clearInputBtn.style.display = "block";
      performSearch(sym);
    }
  });

  // Filters
  elements.daysFilter.addEventListener("change", () => {
    const query = state.currentQuery;
    if (query) performSearch(query, parseInt(elements.daysFilter.value));
  });

  elements.sentimentFilter.addEventListener("change", applyClientFilters);
  elements.sourceFilter.addEventListener("change", applyClientFilters);

  // Watchlist Toggle in Resolution Banner
  elements.watchlistToggleBtn.addEventListener("click", toggleCurrentStockWatchlist);

  // Watchlist Modal Open/Close
  elements.openWatchlistBtn.addEventListener("click", () => {
    elements.watchlistModal.classList.remove("hidden");
    loadLatestDigest();
  });

  elements.closeWatchlistBtn.addEventListener("click", () => {
    elements.watchlistModal.classList.add("hidden");
  });

  elements.watchlistModal.addEventListener("click", (e) => {
    if (e.target === elements.watchlistModal) {
      elements.watchlistModal.classList.add("hidden");
    }
  });

  // Add Watchlist Symbol
  elements.addWatchlistSubmitBtn.addEventListener("click", () => {
    const sym = elements.addWatchlistInput.value.trim();
    if (sym) addStockToWatchlist(sym);
  });

  elements.addWatchlistInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const sym = elements.addWatchlistInput.value.trim();
      if (sym) addStockToWatchlist(sym);
    }
  });

  // Generate Digest
  elements.generateDigestBtn.addEventListener("click", triggerGenerateDigest);

  // Copy & Download Digest
  elements.copyDigestMdBtn.addEventListener("click", copyDigestMarkdown);
  elements.downloadDigestBtn.addEventListener("click", downloadDigestReport);

  // AI Briefing Speech & Copy
  elements.speakBriefingBtn.addEventListener("click", toggleSpeechSynthesis);
  elements.copyBriefingBtn.addEventListener("click", copyBriefingText);
}

// Live Autocomplete Suggestions
async function handleAutocomplete(val) {
  if (!val || val.length < 1) {
    elements.suggestionsDropdown.style.display = "none";
    return;
  }

  try {
    const resp = await fetch(`/api/resolve?q=${encodeURIComponent(val)}`);
    const data = await resp.json();

    if (data.success && data.resolved) {
      const item = data.resolved;
      elements.suggestionsDropdown.innerHTML = `
        <div class="suggestion-item" data-query="${item.symbol}">
          <div class="suggestion-left">
            <span class="suggestion-symbol">${item.symbol}</span>
            <span class="suggestion-name">${item.canonical_name}</span>
          </div>
          <span class="suggestion-sector">${item.sector || 'Equities'}</span>
        </div>
      `;
      elements.suggestionsDropdown.style.display = "block";

      elements.suggestionsDropdown.querySelector(".suggestion-item").addEventListener("click", () => {
        elements.stockInput.value = item.symbol;
        elements.suggestionsDropdown.style.display = "none";
        performSearch(item.symbol);
      });
    } else {
      elements.suggestionsDropdown.style.display = "none";
    }
  } catch (err) {
    elements.suggestionsDropdown.style.display = "none";
  }
}

// Perform Stock Lookup & Analysis
async function performSearch(query, days = null) {
  const selectedDays = days || (elements.daysFilter ? parseInt(elements.daysFilter.value) : 7) || 7;
  state.currentQuery = query;

  try {
    // Show UI loading state safely
    elements.loadingState?.classList.remove("hidden");
    elements.errorBanner?.classList.add("hidden");
    elements.resultsDashboard?.classList.add("hidden");
    if (elements.loadingHeadline) {
      elements.loadingHeadline.textContent = `Resolving '${query}' & Querying Outlets...`;
    }

    const startTime = performance.now();
    const resp = await fetch(`/api/news?q=${encodeURIComponent(query)}&days=${selectedDays}`);
    const data = await resp.json();
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

    if (!resp.ok || !data.success) {
      showErrorState(data.error || "Failed to resolve equity", data.suggestions || []);
      return;
    }

    // Success: Update State
    state.resolvedEntity = data.resolved;
    state.articles = data.articles || [];
    state.stats = data.stats || {};
    state.briefing = data.briefing || {};

    // Update Latency HUD
    if (elements.latencyValue) {
      elements.latencyValue.textContent = `${elapsed}s Fetch Time`;
    }

    // Render Components
    renderResolutionBanner(data);
    renderAIBriefing(data.briefing, data.stats);
    renderMetricsHUD(data.stats, data.articles.length);
    populateSourceFilter(data.stats.distinct_sources || []);
    applyClientFilters();

    elements.resultsDashboard?.classList.remove("hidden");

  } catch (err) {
    console.error("Search failure:", err);
    showErrorState("Network error while connecting to news server. Please try again.", [
      { symbol: "TCS", name: "Tata Consultancy Services Ltd" },
      { symbol: "RELIANCE", name: "Reliance Industries Ltd" },
      { symbol: "INFY", name: "Infosys Ltd" }
    ]);
  } finally {
    // Ensure loading spinner is always hidden once request completes or fails
    elements.loadingState?.classList.add("hidden");
  }
}

// Render Error / Suggestion Banner
function showErrorState(message, suggestions) {
  if (elements.errorBanner) elements.errorBanner.classList.remove("hidden");
  if (elements.errorMessage) elements.errorMessage.textContent = message;
  if (elements.errorSuggestions) {
    elements.errorSuggestions.innerHTML = "";
    if (suggestions && suggestions.length > 0) {
      elements.errorSuggestions.innerHTML = `<span class="chips-label">Try popular stocks:</span>`;
      suggestions.forEach(s => {
        const btn = document.createElement("button");
        btn.className = "chip-pill";
        btn.textContent = `${s.symbol} (${s.name})`;
        btn.addEventListener("click", () => {
          if (elements.stockInput) elements.stockInput.value = s.symbol;
          performSearch(s.symbol);
        });
        elements.errorSuggestions.appendChild(btn);
      });
    }
  }
}

// Render Resolution Header
function renderResolutionBanner(data) {
  const meta = data.resolved;
  if (elements.companyName) elements.companyName.textContent = meta.canonical_name;
  if (elements.nseTicker) elements.nseTicker.textContent = `NSE: ${meta.nse_ticker || meta.symbol}`;
  if (elements.bseTicker) elements.bseTicker.textContent = meta.bse_code ? `BSE: ${meta.bse_code}` : `BSE: Active`;
  if (elements.companySector) elements.companySector.textContent = meta.sector || "Equities";

  const matchLabel = data.match_type === "exact_alias" 
    ? `Resolved alias '${data.resolved.raw_query || state.currentQuery}' to canonical entity`
    : (data.match_type === "fuzzy_match" ? `Fuzzy matched with ${Math.round(data.confidence * 100)}% confidence` : `Resolved via canonical exchange registry`);
  
  if (elements.auditText) elements.auditText.textContent = matchLabel;
  updateWatchlistBtnState();
}

// Render AI "What's Going On" Briefing Card
function renderAIBriefing(briefing, stats) {
  if (!briefing) return;

  const totalSources = stats.distinct_sources ? stats.distinct_sources.length : (briefing.sources_represented ? briefing.sources_represented.length : 1);
  if (elements.briefingMeta) {
    elements.briefingMeta.textContent = `Synthesizing ${stats.total_fetched || 0} reports across ${totalSources} outlets (Consolidated ${stats.duplicates_removed || 0} duplicates)`;
  }

  const s = briefing.sentiment_breakdown || { bullish_pct: 50, neutral_pct: 50, bearish_pct: 0 };
  if (elements.gaugeBullishLabel) elements.gaugeBullishLabel.textContent = `▲ ${s.bullish_pct}% Bullish`;
  if (elements.gaugeNeutralLabel) elements.gaugeNeutralLabel.textContent = `■ ${s.neutral_pct}% Neutral`;
  if (elements.gaugeBearishLabel) elements.gaugeBearishLabel.textContent = `▼ ${s.bearish_pct}% Bearish`;

  if (elements.gaugeBullishFill) elements.gaugeBullishFill.style.width = `${s.bullish_pct}%`;
  if (elements.gaugeNeutralFill) elements.gaugeNeutralFill.style.width = `${s.neutral_pct}%`;
  if (elements.gaugeBearishFill) elements.gaugeBearishFill.style.width = `${s.bearish_pct}%`;

  if (elements.takeawayText) elements.takeawayText.textContent = briefing.headline_takeaway || "No major headlines reported.";

  // Catalysts Grid
  if (elements.catalystsGrid) {
    elements.catalystsGrid.innerHTML = "";
    if (briefing.key_catalysts && briefing.key_catalysts.length > 0) {
      briefing.key_catalysts.forEach(c => {
        const card = document.createElement("div");
        card.className = "catalyst-item";
        card.innerHTML = `
          <div class="catalyst-theme-row">
            <span class="catalyst-theme">${c.theme}</span>
            <span class="catalyst-tag ${c.impact}">${c.impact}</span>
          </div>
          <p class="catalyst-summary">${c.summary}</p>
        `;
        elements.catalystsGrid.appendChild(card);
      });
    }
  }

  if (elements.investorWatchText) elements.investorWatchText.textContent = briefing.investor_watch || "Track corporate filings and earnings delivery.";
}

// Render Metrics HUD
function renderMetricsHUD(stats, uniqueCount) {
  if (elements.hudTotalScanned) elements.hudTotalScanned.textContent = stats.total_fetched || 0;
  if (elements.hudDuplicatesRemoved) elements.hudDuplicatesRemoved.textContent = `${stats.duplicates_removed || 0} (${stats.dedup_percentage || 0}%)`;
  if (elements.hudUniqueStories) elements.hudUniqueStories.textContent = uniqueCount;
  if (elements.hudSourcesCount) elements.hudSourcesCount.textContent = `${(stats.distinct_sources || []).length} Outlets`;
}

// Populate Source Filter Dropdown
function populateSourceFilter(sources) {
  const currentVal = elements.sourceFilter.value;
  elements.sourceFilter.innerHTML = `<option value="all">All Publishers (${sources.length})</option>`;
  sources.forEach(src => {
    const opt = document.createElement("option");
    opt.value = src;
    opt.textContent = src;
    elements.sourceFilter.appendChild(opt);
  });
  if (sources.includes(currentVal)) {
    elements.sourceFilter.value = currentVal;
  }
}

// Apply Client Filters (Sentiment & Source)
function applyClientFilters() {
  const sentimentVal = elements.sentimentFilter.value;
  const sourceVal = elements.sourceFilter.value;

  let filtered = [...state.articles];

  if (sentimentVal !== "all") {
    filtered = filtered.filter(a => a.sentiment && a.sentiment.tag === sentimentVal);
  }

  if (sourceVal !== "all") {
    filtered = filtered.filter(a => a.source && a.source.toLowerCase() === sourceVal.toLowerCase());
  }

  state.filteredArticles = filtered;
  elements.feedCountSubtitle.textContent = `Showing ${filtered.length} stories sorted by recency`;
  renderNewsCards(filtered);
}

// Render News Feed Cards
function renderNewsCards(articles) {
  elements.newsCardsContainer.innerHTML = "";

  if (articles.length === 0) {
    elements.newsCardsContainer.innerHTML = `
      <div class="news-card text-center" style="text-align: center; padding: 2.5rem 1rem;">
        <h4 style="color: var(--text-muted); margin-bottom: 0.5rem;">No stories matching your filters</h4>
        <p class="text-dim" style="font-size: 0.85rem;">Try selecting "All Sentiments" or "All Publishers" to view all articles.</p>
      </div>
    `;
    return;
  }

  articles.forEach((art, idx) => {
    const card = document.createElement("article");
    card.className = "news-card";

    const sent = art.sentiment || { tag: "Neutral", score: 0, rationale: "" };
    const hasDuplicates = art.duplicate_count && art.duplicate_count > 0;
    const dupId = `dup-details-${idx}`;

    let duplicateHtml = "";
    if (hasDuplicates) {
      const otherList = (art.other_coverage || []).map(o => `
        <div class="dup-item">
          • <a href="${o.link}" target="_blank" rel="noopener">${o.title}</a> 
          <span class="text-dim">(${o.source})</span>
        </div>
      `).join("");

      duplicateHtml = `
        <div class="duplicate-banner" onclick="toggleDuplicates('${dupId}')">
          <span>⚑ Consolidated ${art.duplicate_count} duplicate coverage from other outlets</span>
          <span style="font-size: 0.7rem;">▼ View</span>
        </div>
        <div class="duplicate-details" id="${dupId}">
          ${otherList}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="news-card-meta">
        <div class="meta-left">
          <span class="source-pill">${art.source}</span>
          <span class="time-pill" title="${art.published_at}">${art.relative_time}</span>
        </div>
        <span class="sentiment-badge ${sent.tag}">
          ${sent.tag === 'Positive' ? '▲ Bullish' : (sent.tag === 'Negative' ? '▼ Bearish' : '■ Neutral')}
        </span>
      </div>

      <h3 class="news-headline">
        <a href="${art.link}" target="_blank" rel="noopener noreferrer">${art.title}</a>
      </h3>

      <p class="news-summary">${art.summary}</p>

      ${duplicateHtml}

      <div class="news-card-footer">
        <span class="sentiment-rationale" title="${sent.rationale}">${sent.rationale}</span>
        <a href="${art.link}" target="_blank" rel="noopener noreferrer" class="read-link">
          Read Story <span>↗</span>
        </a>
      </div>
    `;

    elements.newsCardsContainer.appendChild(card);
  });
}

// Toggle Duplicate Coverage Accordion
window.toggleDuplicates = function(id) {
  const elem = document.getElementById(id);
  if (elem) {
    elem.classList.toggle("open");
  }
};

// Text-to-Speech (Audio Briefing)
function toggleSpeechSynthesis() {
  if (!('speechSynthesis' in window)) {
    alert("Speech synthesis is not supported in this browser.");
    return;
  }

  if (state.isSpeaking) {
    window.speechSynthesis.cancel();
    state.isSpeaking = false;
    elements.speakBriefingBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
      <span>Listen</span>
    `;
    return;
  }

  const takeaway = elements.takeawayText.textContent;
  const watch = elements.investorWatchText.textContent;
  const textToRead = `${state.resolvedEntity ? state.resolvedEntity.canonical_name : 'Stock'} market update. ${takeaway}. What investors are watching: ${watch}`;

  state.speechUtterance = new SpeechSynthesisUtterance(textToRead);
  state.speechUtterance.rate = 1.0;
  state.speechUtterance.pitch = 1.0;

  state.speechUtterance.onend = () => {
    state.isSpeaking = false;
    elements.speakBriefingBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
      <span>Listen</span>
    `;
  };

  window.speechSynthesis.speak(state.speechUtterance);
  state.isSpeaking = true;
  elements.speakBriefingBtn.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
    <span>Stop</span>
  `;
}

// Copy Briefing to Clipboard
function copyBriefingText() {
  const takeaway = elements.takeawayText.textContent;
  const watch = elements.investorWatchText.textContent;
  const company = state.resolvedEntity ? state.resolvedEntity.canonical_name : "Stock";
  const text = `📊 AI EXECUTIVE BRIEFING: ${company}\n\nWhat's Going On:\n${takeaway}\n\nInvestor Watch:\n${watch}`;

  navigator.clipboard.writeText(text).then(() => {
    const originalText = elements.copyBriefingBtn.innerHTML;
    elements.copyBriefingBtn.innerHTML = `<span>✓ Copied!</span>`;
    setTimeout(() => {
      elements.copyBriefingBtn.innerHTML = originalText;
    }, 2000);
  });
}

// Watchlist API Calls
async function fetchWatchlist() {
  try {
    const resp = await fetch("/api/watchlist");
    const data = await resp.json();
    state.watchlist = data || [];
    elements.watchlistCount.textContent = state.watchlist.length;
    renderWatchlistModalTags();
    updateWatchlistBtnState();
  } catch (err) {
    console.error("Watchlist fetch error:", err);
  }
}

function updateWatchlistBtnState() {
  if (!state.resolvedEntity) return;
  const sym = state.resolvedEntity.symbol;
  const isPresent = state.watchlist.some(w => w.symbol === sym);
  if (isPresent) {
    elements.watchlistToggleBtn.classList.add("active");
    elements.watchlistBtnLabel.textContent = "In Watchlist";
  } else {
    elements.watchlistToggleBtn.classList.remove("active");
    elements.watchlistBtnLabel.textContent = "Add to Watchlist";
  }
}

async function toggleCurrentStockWatchlist() {
  if (!state.resolvedEntity) return;
  const sym = state.resolvedEntity.symbol;
  const isPresent = state.watchlist.some(w => w.symbol === sym);

  if (isPresent) {
    await fetch(`/api/watchlist/${sym}`, { method: "DELETE" });
  } else {
    await fetch(`/api/watchlist?symbol=${sym}`, { method: "POST" });
  }
  await fetchWatchlist();
}

function renderWatchlistModalTags() {
  elements.watchlistTagsGrid.innerHTML = "";
  if (state.watchlist.length === 0) {
    elements.watchlistTagsGrid.innerHTML = `<span class="text-dim" style="font-size: 0.8rem;">Watchlist is empty.</span>`;
    return;
  }

  state.watchlist.forEach(item => {
    const tag = document.createElement("div");
    tag.className = "watchlist-tag";
    tag.innerHTML = `
      <span class="tag-sym">${item.symbol}</span>
      <span class="text-dim" style="font-size: 0.75rem;">${item.canonical_name || item.name || ''}</span>
      <button class="tag-remove" title="Remove" onclick="removeStockFromWatchlist('${item.symbol}')">×</button>
    `;
    elements.watchlistTagsGrid.appendChild(tag);
  });
}

window.removeStockFromWatchlist = async function(symbol) {
  try {
    await fetch(`/api/watchlist/${symbol}`, { method: "DELETE" });
    await fetchWatchlist();
  } catch (err) {
    console.error("Failed to remove stock:", err);
  }
};

async function addStockToWatchlist(query) {
  try {
    const resp = await fetch(`/api/watchlist?symbol=${encodeURIComponent(query)}`, { method: "POST" });
    const data = await resp.json();
    if (data.success) {
      elements.addWatchlistInput.value = "";
      await fetchWatchlist();
    } else {
      alert(data.error || "Could not add stock to watchlist.");
    }
  } catch (err) {
    alert("Error adding stock to watchlist.");
  }
}

// Daily Digest Generation
async function triggerGenerateDigest() {
  elements.generateDigestBtn.disabled = true;
  elements.generateDigestBtnText.textContent = "⚡ Compiling Watchlist Digest...";
  elements.digestContentBox.textContent = "Querying live feeds for all watchlist equities and synthesizing market tone...";

  try {
    const resp = await fetch("/api/digest/generate", { method: "POST" });
    const data = await resp.json();

    elements.generateDigestBtn.disabled = false;
    elements.generateDigestBtnText.textContent = "⚡ Compile Digest Now";

    if (data.success && data.digest) {
      renderDigest(data.digest);
    } else {
      elements.digestContentBox.textContent = `Error: ${data.error || 'Failed to generate digest.'}`;
    }
  } catch (err) {
    elements.generateDigestBtn.disabled = false;
    elements.generateDigestBtnText.textContent = "⚡ Compile Digest Now";
    elements.digestContentBox.textContent = "Network error while generating digest.";
  }
}

async function loadLatestDigest() {
  try {
    const resp = await fetch("/api/digest/latest");
    const data = await resp.json();
    if (data.has_digest && data.digest) {
      renderDigest(data.digest);
    }
  } catch (err) {
    console.error("Latest digest fetch error:", err);
  }
}

function renderDigest(digest) {
  elements.digestMarketTone.textContent = `Market Tone: ${digest.market_tone} (${digest.avg_bullish_pct}% Bullish)`;
  elements.digestContentBox.textContent = digest.markdown_export;
  state.lastDigestMarkdown = digest.markdown_export;
}

function copyDigestMarkdown() {
  if (!state.lastDigestMarkdown) return;
  navigator.clipboard.writeText(state.lastDigestMarkdown).then(() => {
    const orig = elements.copyDigestMdBtn.textContent;
    elements.copyDigestMdBtn.textContent = "✓ Copied!";
    setTimeout(() => { elements.copyDigestMdBtn.textContent = orig; }, 2000);
  });
}

function downloadDigestReport() {
  if (!state.lastDigestMarkdown) return;
  const blob = new Blob([state.lastDigestMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `Market_Digest_${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
