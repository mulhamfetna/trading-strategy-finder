# Backlog — data / analytics sources to experiment with

**Created 2026-07-15** from a user-provided list. Each source is a candidate **exogenous signal** for our
strategy — most naturally feeding the parked **exogenous-signals-fusion** workstream (VIX / breadth /
rates / options → regime state → policy, NOT entry direction) and/or **covariates** for a covariate-aware
foundation model (Chronos-2 / Moirai-2 — see [BACKLOG_TSFM_ALTERNATIVES.md](BACKLOG_TSFM_ALTERNATIVES.md)).
Run each through the [REPORTING_TEMPLATE.md](REPORTING_TEMPLATE.md) five-stage system, one at a time.

## ⚠️ Access & terms-of-service reality (read first)
Most of these are **subscription / paid-API / ToS-restricted** and several **prohibit scraping**. We will
**not** scrape any source whose terms forbid it. Per source below: preferred = official API or export the
user already has access to. Where only a paid feed exists, the experiment is **blocked on the user
providing the data or credentials**. The two `x.com` links returned **HTTP 402** (auth-walled) — they need
the user to paste the thread content or grant access; can't auto-fetch.

## The sources (priority = signal value × accessibility × fit to our futures book)

| # | Source | What it is | Signal hypothesis for us | Access reality | Prio |
|---|--------|-----------|--------------------------|----------------|------|
| 1 | **finviz.com** | screener, heatmaps, breadth, insider, news | **Market breadth / sector heatmap** as a regime feature; news-sentiment veto | free tier + paid Elite export; scraping restricted → use Elite export | ★★★ |
| 2 | **barchart.com** | futures/options data, COT, options flow, technicals | **COT positioning + options flow** on NQ/ES; intraday futures data cross-check | paid API/subscription; has an API → preferred | ★★★ |
| 3 | **macromicro.me** | macro & cross-asset dashboards | **Macro regime** features (liquidity, rates, cycle) → regime state | subscription; manual export | ★★☆ |
| 4 | **companiesmarketcap.com** | market caps & rankings | **Nasdaq-100 concentration** (top-7 weight) — directly tied to our NQ-vs-ES volatility asymmetry finding | mostly free/derivable | ★★☆ |
| 5 | **etfdb.com** | ETF data, flows, holdings | **QQQ/SPY flows + sector rotation** as a risk-on/off regime signal | free tier + paid; export | ★★☆ |
| 6 | **stockanalysis.com** | fundamentals, financials, screeners | fundamentals/earnings calendar → event-risk veto windows | free + API; lenient | ★★☆ |
| 7 | **koyfin.com** | equity+macro analytics, estimates | broad macro/cross-asset dashboard (overlaps 3) | subscription | ★☆☆ |
| 8 | **seekingalpha.com** | analysis, quant ratings, earnings | quant ratings / sentiment (noisy, ToS-strict) | subscription; scraping prohibited | ★☆☆ |
| 9 | **x.com/antpalkin/...2072774690834153532** | a trader's post/thread | a specific strategy/indicator idea to reverse-engineer + test | **HTTP 402 — need user to paste content** | ? |
| 10 | **x.com/ruujss/...2074503360208884204** | a trader's post/thread | same | **HTTP 402 — need user to paste content** | ? |

## The experiment for EACH source (report-driven, same system)
1. **CHARACTERIZE / PRIOR_ART** — exactly what fields, frequency, history depth; **access method + ToS**
   (API vs export vs blocked); the precise **signal hypothesis** and how it fuses (regime feature, covariate,
   or event veto). Deliverable: `docs/data/<source>/PRIOR_ART.md`. *(No compute; some need user data.)*
2. **ACQUIRE** a clean historical sample (via API/export the user supplies) aligned to our 2024–26 window,
   built **causally** (as-of timestamps, no revisions leaking).
3. **DUMB CONTROL** — does the feature beat a trivial proxy already in our data (e.g. does a "breadth"
   feed beat realized-vol / our own box stats)?
4. **ROBUSTNESS** — multi-regime, purged CV, does it help the *majority* of sub-periods; state confounds.
5. **VERDICT** — GO/NO-GO; log in [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md); promote survivors into the
   exogenous-signals-fusion workstream.

## Recommended first three (best value-to-effort, most accessible, best fit)
**finviz breadth (#1) → barchart COT/options-flow (#2) → companiesmarketcap NQ concentration (#4).**
All three produce a *regime* feature (risk-on/off, positioning, concentration) — the exact class the
prior-art said actually works (regime-gated participation), and complementary to the (failed) TimesFM
vol-band. #4 also directly probes our own NQ-vs-ES volatility-asymmetry finding.

## ⛔ Blockers to resolve with the user before starting
- Which of these do you have a **paid subscription / API key** for? (drives what's actually acquirable)
- **Paste the two X-thread contents** (they're auth-walled) so I can extract the idea to test.
- This program is really its **own workstream** (exogenous data → regime signals). Per the one-workstream-
  one-branch convention it should get its own branch/worktree — **say the word and I'll create it** (I won't
  auto-create per your standing rule).

## Tasks created: #106 (finviz breadth), #107 (barchart COT/flow), #108 (companiesmarketcap concentration),
#109 (characterize the rest + the two X threads once content provided).
