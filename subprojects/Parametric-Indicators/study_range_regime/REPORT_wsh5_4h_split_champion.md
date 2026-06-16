---
name: report_wsh5_4h_split_champion
description: wsh5 4h split long/short SL/TP champion — extraction, adoption-gate comparison vs wsh4, new alternative profile
---

# wsh5 — 4h split long/short SL/TP champion (extraction + adoption ruling + profile)

**Date:** 2026-06-15. **Run:** `wsh5_4h` — NSGA-III, 1-minute indicators, **separate long/short SL/TP**
(`--split-sltp`), full-data **4h-ONLY** sweep (per the 2026-06-15 directive; all workers concentrated on 4h).
Completed **5028 trials** (watchdog stopped at the 5000 target). Store: Postgres `wsh-pg` on the AMD server.

> ⚠️ **The full-data optimizer runs 4h-ONLY for now** (time-saving + study focus). Parity/smoke/golden and all
> engine/system development still consider ALL timeframes — only the production sweep is narrowed. See
> `NEXT_OPTIMIZER_NOTES.md`.

## Champion (trial #5591) — feasible Pareto, max median fold P/L
Selection rule = the same one used for the deployed wsh4 champion: among **feasible** trials
(full-window max-DD ≤ 25 % of full-window P/L), take the one with the highest **median walk-forward fold P/L**.

| | median fold P/L | worst fold DD | median win | full-window P/L | full-window DD | DD % |
|---|--:|--:|--:|--:|--:|--:|
| **wsh4 4h — shared SL/TP (DEPLOYED)** | **$33,592** | $13,925 | 71.1 % | **$142,229** | $14,075 | **9.9 %** |
| **wsh5 4h — split long/short (NEW)**  | $28,228 | **$6,162** | **86.5 %** | $88,993 | $12,594 | 14.2 % |

### Champion parameters
- **Shared (base):** sl_soft `80.34` · sl_hard `106.16` · tp `70.0`
- **Long (buys):** sl_soft `151.57` · sl_hard `171.65` · tp `37.59`  *(wide stop, tight target)*
- **Short (sells):** sl_soft `113.60` · sl_hard `253.39` · tp `116.47`  *(very wide hard stop, wide target)*
- **Box/gate/breaker:** gate_pct `72.02` · dd_limit `$573.73` · cooldown `0` · flip `False` · K `2`
- **Indicators (8):** sma_trend(239/326) · vwap · keltner(162, m4.0) · obv(slope50) · bollinger(85, k4.6) ·
  adx(54, thr12) · order_block(swing_l20) · fvg(lookback1)

The long/short SL/TP are clearly **asymmetric** (long: wide stop / tight TP; short: very wide stop / wide TP),
so the free search *did* use the new degree of freedom — it just didn't pay off enough to win (below).

## Adoption ruling — **KEEP the shared champion; import the split champion as an ALTERNATIVE**
Pre-registered gate: *adopt a new champion only if it OOS-dominates the deployed one on return **and** DD.*
The split champion **does not dominate**:
- **Return:** lower — median fold P/L $28.2k vs $33.6k (−16 %); full P/L $89.0k vs $142.2k (−37 %).
- **Drawdown:** better — worst fold DD $6.2k vs $13.9k (≈ half).
- **Win rate:** better — 86.5 % vs 71.1 %.

This **confirms Q1's earlier finding** (`REPORT_Q1_split_sltp.md`): asymmetric long/short SL/TP is **not** a
strictly better strategy — here it buys a calmer, higher-hit-rate equity curve at a real cost in total return.
⇒ The deployed [[project_wsg_winner]] / **wsh4 shared** 4h champion **stays deployed**. The split champion is
added as a **new, clearly-labelled alternative profile** (the user's "import as a new profile" deliverable).

## Local reproduction (dashboard exact engine, window=full)
Running the imported preset through the dashboard's exact engine reproduces:
**P/L $94,411 · max DD $10,265 · win 79.3 % · PF 2.0 · 174 trades.**
This differs from the optimizer's `full_pnl` $88,993 because the optimizer freezes the volatility gate
**causally on the in-sample (2025) slice** (`optimizer.py` full-feasibility eval, `gate_ref_vf=vf[:n_split]`),
whereas the dashboard computes the gate over the full window. The same effect makes wsh4's golden
($142,203) differ from its optimizer `full_pnl` ($142,229) — here it's larger only because the **$574 breaker
is extremely tight**, so tiny gate-threshold differences reshuffle locks/trades. The preset is a faithful,
exact transcription of trial #5591's parameters; both numbers are real (different gate references).

## Where this profile belongs
- **Dashboard Strategy dropdown:** `⚖ WS split 4h · long/short SL/TP — typ $28,228 (DD $6,162)`
  (id `wsh5split_4h`). Selecting it fills the form **in split mode** (per-side boxes populated; shared boxes
  hidden) plus the 8 indicators above. It is an **alternative**, not the default — the ★ Winner and the
  `⏱ 1-min-trained` wsh4 champions remain the primary entries.
- **Source of truth:** `optimize/results/wsh5_4h_split_champion.json` (champion schema + split box).
- **Wiring:** `presets.py` (`_champions_wsh5_split()`, split-aware `_preset()`, `strategies()` entry).

## Caveats
1. **No new indicators in this run.** wsh5 was launched **before** the `ifvg`/`breaker`/`cisd` vote indicators
   were wired, so its search space did **not** include them. A subsequent run (a fresh prefix, e.g. wsh6) can
   search them now that engine+optimizer+dashboard all support them.
2. **n = 1** champion; single-instrument (NQ). The drawdown/win-rate advantage is promising but unproven OOS
   beyond this walk-forward.
3. Other timeframes for the split sweep are HELD (4h-only directive); `wsh5_{2h,1h,15m,5m,2m}` retain partial
   trials if the full sweep is ever resumed.
