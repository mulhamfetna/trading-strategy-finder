# Design — Shareable per-market per-timeframe playbooks (36)

**Date:** 2026-07-08
**Branch:** `stocks-drop-down-backtester-optimizer`
**Status:** approved (design + Path B), executing

## Goal

Produce **one shareable playbook per instrument per timeframe** — 6 instruments × 6 timeframes = **36
self-contained documents** — that a trader or stakeholder can read cold to (a) understand what the strategy
does on that market+timeframe, (b) reproduce the exact champion in the dashboard, and (c) judge whether it is
worth trading, out-of-sample included.

Instruments: **NQ** (Nasdaq-100), **ES** (S&P 500), **GC** (Gold), **SI** (Silver), **RTY** (Russell 2000),
**YM** (Dow). Timeframes: **4h, 2h, 1h, 15m, 5m, 2m**.

## Approved decisions

- **Content = both, full** — a plain-language how-to narrative *and* the complete metric tearsheet.
- **Format = local pageless PDF**, one file per playbook (matches the house report format; embeds the
  dashboard snapshot + Mermaid; offline; easy to send). 36 files.
- **Weak slots included with an honest warning** — every slot gets a playbook; slots that fail the risk bar,
  go negative out-of-sample, or use a degenerate config say so plainly ("do not trade this combo"), never
  dressing up a bad number.
- **Numbers via Path B (server pass)** — capture the dashboard's own values, including a real 2026
  out-of-sample split, rather than reading stale JSON.

## Anatomy of one playbook

1. **Header** — market + timeframe (e.g. "GOLD (GC) — 4-hour playbook") and a one-line verdict badge:
   **Deployable ✓ / Caution ⚠ / Non-feasible ✗**.
2. **What this is** — which market, what the box strategy does on this timeframe, who it's for.
3. **Load these settings** — copy-paste-ready champion: box params (SL soft/hard, TP, gate %, DD limit,
   cooldown, flip, K-confirms, 1-min cap) + the indicator set with parameters, so anyone can reproduce it in
   the dashboard (pick instrument → timeframe → these settings → Run).
4. **How it trades** — plain-language entry/exit/risk narrative *derived from the settings* (flip on/off,
   reward:risk from TP vs SL, K-confirm strictness, DD breaker).
5. **Complete tearsheet** — full-window headline metrics (on-screen truth: Total P/L, Max Drawdown, Win Rate,
   Profit Factor, Payoff, L1 entries) + richer detail (avg win/loss, hold-time, no-entry streaks) + the
   embedded full-page dashboard snapshot as the authoritative complete picture.
6. **2026 out-of-sample** — the champion re-run on the held-out 2026 window: P/L, DD, trades, win %, and a
   plain verdict (holds up / thin / fails).
7. **Risk & caveats / when NOT to trade** — per-slot honest warnings.
8. **Provenance footer** — study prefix, champion source file, "verified in dashboard UI on <date>", and the
   author attribution block.

## Source of truth (respects the project's hard rules)

| Playbook element | Source | Note |
|---|---|---|
| Settings to load | `optimize/results/wsh4_champions_full_<TOK>.json` (`box` + `indicators`) | authoritative for *what to load* |
| Headline metrics (full + 2026) | **rendered dashboard cards** captured by the server UI-driver | on-screen truth; the "Total P/L" card is **not** `summary.pnl` (GC 4h card $57,570 vs summary.pnl $56,480) |
| Deeper metrics | `/api/backtest` `meta.summary` (avg win/loss, hold-times, streaks, `pnl_2025`/`pnl_2026`) | richer tearsheet detail |
| 2026 OOS | dashboard `#l1_window=2026` run (cards + summary) | true held-out split |
| Complete visual | existing 36 full-page snapshot PNGs (`optimize/reports/dashboard_snapshots_all/`) | embedded per slot |

**Rule compliance:** all metric computation runs **on the AMD server** (`amd-trading`) — heavy 2m/5m
timeframes require it, and the no-local-compute rule forbids running it on the 14 GB laptop. Only the PDF
rendering (headless-Chrome HTML→PDF) runs locally, which is light.

## Path B — the server pass

`playbook_enrich.py` drives the live dashboard UI (Playwright, headless chromium) for each of the 36 slots and,
for `window=full` and `window=2026`, records: the rendered metric **cards** (on-screen truth), the full
`/api/backtest` **summary**, and the exact champion **params** the UI sent. Output:
`~/Mulham/wsg-i/playbook_metrics.json`, pulled local. This reuses the same endpoint and champion resolution the
browser uses, so the numbers are byte-identical to the UI.

## Build pipeline

1. **Server pass** → `playbook_metrics.json` (full + 2026 per slot). *(running)*
2. **Pull local** → `playbook_metrics.json` + reuse the local 36 snapshot PNGs.
3. **Generate** → a local script renders 36 pageless PDFs from one HTML template
   (settings from champion JSON, numbers from the enriched cards/summary, embedded snapshot, Mermaid
   diagrams, how-to narrative, honest warnings, attribution). Playwright `page.pdf(prefer_css_page_size)`.
4. **Verify** each PDF's headline P/L equals the recorded on-screen value; place in
   `optimize/reports/playbooks/<INST>_<TF>_playbook.pdf`.

## Weak-slot handling (verdict logic)

- **Non-feasible ✗** — failed the drawdown/feasibility gate (e.g. SI 4h reproduces $21,928 on screen but at
  32% win / $7,452 DD it is flagged non-feasible): say "not deployable — do not trade."
- **Caution ⚠** — negative or thin 2026 OOS, low win-rate + high DD, or degenerate low-TF config: warn
  explicitly.
- **Deployable ✓** — reproduces, clears the risk bar, positive/held OOS.

## Deliverable

36 × `optimize/reports/playbooks/<INST>_<TF>_playbook.pdf`, self-contained, plus the generator script kept in
the repo. Snapshots and any large intermediates stay gitignored per house convention.

## Non-goals

- No re-optimization; playbooks report existing champions only.
- No L2/Combined layer detail beyond the L1 champion (playbooks are the deployable L1 story).
- No live/broker wiring; these are reproduction + expectation documents.

---
_Author: Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X_
