# WS-ESCPI — the ES CPI-alone ride: study case, confirmation, integration, ship gate

## Where this comes from
WS-NEWS4/N3 (#137) found, **descriptively**, that the CPI-alone slice of the deployed-set ride on ES nets **+$151.37/event stressed (t≈3.00, n=116)** — the 4th instrument in a row where CPI carries whatever premium exists (NQ +$309 confirmed, RTY +$78 confirmed, GC +$80 t≈1.8). The owner ordered its own study case (2026-08-18): confirm with the established system, verify over 2024→2026, integrate into the three-news layer and measure the added profit, then — if approved — ship into the main system after the three-stage verification (research → backtester engine → dashboard visual inspection via SSH+Playwright with screenshots), then the comprehensive report and playbook.

## Is it profitable? (the honest first-pass economics)
- ES CPI-alone: net **+$151.37/event** at stressed costs ($52.50/event — ES tick is $12.50); ~11 usable CPI prints/yr ⇒ **≈ $1,650/yr per contract**.
- For scale context: NQ CPI ≈ $3,400/yr/contract, RTY CPI ≈ $860/yr; the whole deployed news layer ≈ $16.2k/yr at 1 contract (2024→2026 pace). ES CPI would add ≈ +10% to the layer at 1 contract — modest in absolute dollars, but the same convex, near-zero-exposure-time, CPI-anchored stream, on the **deepest equity future there is** (best scaling surface of all four).

## ⚠️ The integrity problem this study exists to solve
The +$151 was found by measuring ES's full history — that history is **consumed** and cannot confirm itself. Per protocol (the M3/RTY lesson), confirmation must come from data the hypothesis never touched.

## Pre-registration (filed HERE, BEFORE any new data is loaded)
**Primary confirmatory test — the YM holdout.** YM (Dow futures) 1-second data exists on the server (`YM_Continuous_Data/YM_1s.csv`) and has NEVER been loaded by any news study (WS-NEWS2 excluded YM because its 1-minute frame was 0 bytes; the 1s file was never opened). As of this filing, nothing about the file has been read except its existence in a directory listing.
- H1: the CPI-alone ride (frozen deployed spec: LONG rel−300s, S 0.10% worse-of, TP 0.40% better-of, tie⇒STOP, exit +900s) on YM has **positive net-stressed mean** over all usable CPI events (≥2016, bars available).
- YM constants by the deployed formula: point value $5, tick 1.0 pt = $5 ⇒ stressed cost/event = 2.50 + 4×5 = **$22.50**.
- PASS requires ALL of: two-sided p < **0.01** with positive mean · chronological half-split both halves gross-positive · V2 jump gate (CPI minute > 1.2× quiet baseline on YM) · quiet-day control (400 days, seed 117, not significantly positive; block mean above control mean) · 1,000-placebo noise check (observed > 99th pct).
- **POWERED-NULL** if p ≥ 0.01 and MDE(80%, α=0.01) ≤ $150/event; else UNDERPOWERED.
- ⚠️ Data-quality gate first: if YM's 1s file is degenerate (the 0-byte-1m history is a warning), the jump gate and a bar-coverage check (≥70% of CPI windows must have ≥150 traded pre-release seconds) decide VOID-DATA — no premium verdict claimable either way.
- **Falsifier (V3)**: the same YM pipeline fed the Retail Sales minutes must NOT come out positive (Retail is the confirmed anti-premium; if YM shows Retail positive, the YM pipeline is broken, not the market generous).
- **ES robustness battery** (labeled robustness, NOT independent confirmation): the full gate battery on the ES CPI slice — half-split, era table, quiet control, noise check, per-year 2024→2026.
- Interpretation rule, fixed now: **ES CPI ships only if the YM holdout PASSES** (the premium generalizes across equity-index futures) **or** the owner explicitly accepts descriptive-grade evidence. A YM POWERED-NULL means the ES observation does not generalize and the case closes unshipped.

## The owner's full pipeline for this case
1. ~~Verbose in-depth WS-NEWS4 record~~ ✅ `docs/WS-NEWS4-FULL-RECORD.md` (f650adf)
2. This study case: YM holdout + ES robustness (server, 1s archive)
3. Verification over 2024→2026 (per-year tables, both instruments)
4. Integration: three-news layer (NQ+RTY) + ES-CPI rides, 2024→2026, measure added profit
5. Ship gate (only if approved): three-stage verification — research ✓ → backtester engine (executor extended with ES + per-instrument series filter, replay parity) → dashboard visual inspection via SSH+Playwright with captured screenshots
6. Comprehensive report + playbook update
7. Then, and only then, WS-FUSION opens.

Standing gates: V1/V2/V3 + claims ledger before any published number; every step as a comment here; stressed costs lead; all work inside the trading root on legacy18.
