# FU-1 (#153) pre-registration — the event-window interaction audit

**Filed BEFORE any run. FU-1 is an AUDIT — pure measurement, no deploy decision — so what is
frozen here is the definitions, not pass lines. Every later A-family study consumes these
numbers; freezing the definitions now prevents metric-shopping later.**

## Prior art folded in (archaeology, this morning)

Era-0's FAV2/B1 (`study_close_on_news.py`) already measured the NQ 4h/1h champions against
08:30 releases: only **0.3–1.1% of trades span a release**; the give-up from closing at 08:29
is **zero-mean, high-variance** (1h: +$349/trade, p=0.217, sd $981) — the Moreira–Muir "free
variance removal" read. FU-1 generalizes: all six golden TF slots, the FULL Tier-1 calendar
(not just 08:30), and three densities B1 never measured (entries, stop-outs, P&L in-window).
The engine already carries a golden-locked `news_veto` gate (off by default) — FU-2's lever
exists; FU-1 supplies its numbers.

## Frozen definitions

- **Book slice (Phase 1)**: the NQ champion slots on the six golden TFs (4h, 2h, 1h, 15m, 5m,
  2m — `perf._common.champion_preset`, the same presets the golden gate locks), trades with
  entry ≥ 2016-01-01 (the calendar's usable era). Phase 2 (other instruments) only after
  Phase 1 reports, via the `best_*` preset registry — declared, not run here.
- **Events**: TradingView importance-1 releases, minute-deduped, ≥2016.
- **The window**: [release −5 min, release +15 min] (the deployed ride's footprint).
- **Metrics** (per TF, plus pooled):
  1. **Time share**: in-window minutes ÷ total session minutes (the uniform baseline).
  2. **Entry density**: share of trade ENTRIES whose entry bar falls in-window, vs time share.
  3. **Entry quality**: mean P&L (points × PV) of in-window entries vs out-window entries,
     bootstrap 95% CI on the difference (10,000 resamples, seed 0).
  4. **Stop-out density**: share of stop-classified EXITS (`exit_reason` ∈ stop kinds)
     landing in-window, vs time share.
  5. **Spanning give-up** (B1 replicated across all TFs and all Tier-1 minutes): held-through
     P&L minus close-at-last-bar-before-release P&L, per spanning trade.
- **Outputs**: `fu1_audit_{tf}.csv` (per-trade classification) + `fu1_result.json`
  (per-TF + pooled metrics), committed; findings as #153 comments; ledger claim before any
  number is quoted elsewhere.

## Declared blind spots

1. Phase 1 is NQ-only — the statistically dominant slice, but instrument generalization is
   Phase 2's job, not assumable.
2. The engine's decision bars are TF-coarse (a 4h "entry bar" may sit hours from the release
   minute); classification uses the 1-minute execution stream where the engine provides it
   (entry/exit times are minute-resolved in the fast engine) — stated so the 4h rows are read
   with that grain in mind.
3. An audit cannot see counterfactuals (what the vetoed book WOULD have done) — that is FU-2's
   replay, not FU-1's join.
