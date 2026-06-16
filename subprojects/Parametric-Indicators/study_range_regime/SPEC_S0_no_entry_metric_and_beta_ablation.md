---
name: spec_s0_no_entry_metric_and_beta_ablation
description: "Spec — S0 no-entry-streak metric (with warmup-vs-decision source attribution) + β indicator-ablation tool for the wsh4 1-min 4h champion. First of a 3-part strategy-refinement workstream (S0 → β → α). Goal: shrink the live decision pause and find droppable indicators without materially hurting the $142,203 champion."
metadata:
  type: project
  workstream: strategy-refinement
  stage: S0 + beta
  date: 2026-06-16
---

# SPEC — S0 (no-entry metric) + β (indicator ablation)

## 0. Context & goal
The deployed champion **'wsi-4h-1m'** (wsh4 1-min-trained 4h, preset `wsi1m_4h`) is excellent and **NOT** a
target for higher returns: full P/L **$142,203** / max DD **$14,082** / win **71.1%** / PF ~1.6, **8
indicators**. Two real problems remain (from the user):
- **Issue 1 (pause):** it can go ~14 days / ~35 candles with no entry. Want the *recurring* pause ≤ ~3 days.
- **Issue 2 (indicator count):** prefer fewer indicators; willing to give up ~5% P/L to drop 3–4.
- **Issue 3 (data footprint):** the live trader wants minimal history; high-lookback indicators (~240+
  candles) are drop candidates. Embedded in issue 2.

This workstream is split **S0 → β → α** (this spec covers **S0 + β**; α is a separate spec):
- **S0** — shared no-entry-streak metric (additive engine output).
- **β** — isolated indicator-ablation tool (issues 2 + 3).
- **α** (later) — optimizer objective swap (win-rate → min decision-pause) on the wsh4-era space (issue 1).

## 1. Locked decisions (from brainstorming)
| # | Decision |
|---|---|
| D1 | Build order **S0 → β → α**; this spec = S0 + β |
| D2 | Target = **wsh4 1-min 4h champion** ($142,203; 8 ind: bollinger, cci, keltner, mfi, obv, order_block, sma_trend, structure_trend) |
| D3 | No-entry metric = **max gap between consecutive entries, in days** (edges/leading handled via attribution, below) |
| D4 | Ablation = **full-period** backtest per subset (not folds) |
| D5 | Report = **full ranked report, no hard filter** (user picks tolerance by eye) |
| D6 | **Source attribution** (user's note): separate **warmup** startup pause from **decision** recurring pause; α will minimize only the decision pause |
| D7 | β runs **all 2⁸ = 256 subsets**, **parallel** (~10 workers, ~6–10 min on 12 cores); no engine change beyond S0 |

## 2. S0 — no-entry-streak metric (with warmup/decision attribution)

**Where:** `optimize/core.py::backtest_metrics`, after the `trades` list is built. Purely **additive** new
keys ⇒ golden byte-identical (verified 6/6).

**Definitions** (decision-bar indices; `bar_hours` from the timeframe; 4h ⇒ 6 bars/day):
- `warmup_bars` = max over the **enabled** indicators of `indicator.warmup_bars(params)` (the data footprint;
  before this bar no entry is even possible). `warmup_days = warmup_bars × bar_hours / 24`.
- `first_entry_bar` = `trades[0].entry_idx` (when trading actually began); `None`/−1 if no trades.
- `max_no_entry_bars` = largest gap between consecutive `entry_idx` (and the leading gap `first_entry_bar − 0`);
  `< 2` trades ⇒ 0. `max_no_entry_days` accordingly. **(overall, incl. startup)**
- **`max_no_entry_bars_decision`** = largest gap among gaps whose **start index ≥ `warmup_bars`** (i.e. the
  leading warmup region is excluded). `max_no_entry_days_decision` accordingly. **(the recurring operational
  pause — issue 1's true target)**
- **`longest_gap_source`** = `"warmup"` if the overall longest gap lies (mostly) within `[0, warmup_bars]`,
  else `"decision"`.

> Rationale (user's note): the warmup pause is a one-time startup cost we are **not** optimizing now; the
> decision pause is the recurring one we care about. If `max_no_entry_days_decision < warmup_days`, that is a
> *perfect* outcome — the live logic never pauses longer than the unavoidable startup.

**Trailing gap (last entry → end of data):** reported as `trailing_no_entry_days` but **excluded** from
`max_no_entry_*_decision` (a strategy that simply stopped at the data edge is an edge artifact, not a
recurring pause). This matches D3 ("max gap between entries").

**Test (S0):** `optimize/test_no_entry_metric.py` — synthetic `trades` lists with known entry indices →
assert `max_no_entry_bars`, the decision-only value (with a given `warmup_bars`), and `longest_gap_source`.
Plus: `perf/check_golden.py` 6/6 unchanged.

## 3. β — indicator-ablation tool

**File:** `optimize/ablate_indicators.py`.

**Inputs:** the champion (wsh4 1-min 4h) — box + continuous knobs + the 8 enabled indicators with their
champion params. Loaded from `optimize/results/wsh4_champions_full.json["4h"]` (same source the warm-start /
preset uses).

**Enumeration:** all `2⁸ = 256` on/off subsets of the **8 enabled** indicators. The champion's *disabled*
indicators stay OFF in every subset (we only ablate what the champion actually uses). Each enabled
indicator keeps its champion params; only its on/off flag varies. (Note: 256 subsets, not 8! — it is the
power set of the 8.)

**Per-subset evaluation (parallel, ~10 workers):** build the engine params (champion knobs + this subset's
indicator on/off + frozen params), run **full-period** `backtest_metrics` with `ind_1min=True`, collect:
`pnl, max_dd, win, pf, n_trades, max_no_entry_days, max_no_entry_days_decision, longest_gap_source,
warmup_days, data_footprint_bars` (= `warmup_bars` for the subset), `n_indicators`, `kept` (list).

**Baseline:** the all-8-on subset = the champion; assert it reproduces the golden **$142,203** (a HARD anchor
— if it doesn't, the loader/params are wrong and the run aborts). Every subset reports `delta_pnl_pct` and
`delta_dd` vs this baseline.

**Outputs:**
- `optimize/results/ablation_wsi1m_4h.json` — all 256 rows (raw, machine-readable).
- `study_range_regime/REPORT_indicator_ablation_wsi1m_4h.md` — **full ranked report** (Mermaid where it
  helps), with:
  - a **ranked table** (all 256, or top-N + the rest collapsed): `kept · #dropped · PnL · ΔPnL% · DD · ΔDD ·
    win · decision-pause-days · warmup-days · footprint-bars`, ranked by a **score** =
    `pnl + DROP_BONUS × n_dropped` (so "drop the most for the least P/L cost" floats up; `DROP_BONUS`
    documented + configurable). **No hard pass/fail filter** (D5).
  - a **per-indicator marginal-impact table**: for each of the 8, the mean `ΔPnL%` / `ΔDD` /
    `Δdecision-pause` across all subsets where it is removed vs present (which single indicators are
    cheap/expensive to drop).
  - a **data-footprint summary** (issue 3): each indicator's warmup-bars, and the footprint of the
    recommended lean subsets (so the user sees the live-data saving).

**CLI:** `python3 -m optimize.ablate_indicators [--champion wsh4_4h] [--workers 10] [--drop-bonus N] [--top N]`.

**Reuse / safety:** uses the **golden engine path** (`backtest_metrics`) + the champion-loader pattern from
`two_stage._Ctx` (data load once, then parallel per-subset eval). No engine change beyond S0's additive
keys. ~6–10 min on 12 cores. (Future accelerator, NOT v1: precompute the 8 indicators' vote arrays once and
recombine per subset → ~1 min; deferred to keep v1 engine-change-free.)

**Test (β):** `optimize/test_ablate.py` — (a) enumeration yields exactly 256 distinct subsets incl. all-on
and all-off; (b) the param-builder maps a subset to the right en-flags with frozen params; (c) on a tiny
stub the runner returns a well-formed row dict with the new metric keys; (d) the all-on baseline equals the
champion params. (The full 256-run + golden $142,203 baseline match is the acceptance smoke, run once.)

## 4. Non-goals (this spec)
- **No** optimizer change (that's α). **No** engine logic change (only additive metric keys). **No** warmup
  optimization (we *measure/attribute* it, we don't tune it). **No** hard tolerance filter (full report only).
- **No** ablation of the champion's *disabled* indicators (we only test removing what it uses).

## 5. Files
```
optimize/core.py                       # S0: +no-entry/warmup metric keys (additive)
optimize/ablate_indicators.py          # β: enumerate 256 subsets, parallel backtest, rank, report
optimize/test_no_entry_metric.py       # S0 unit lock
optimize/test_ablate.py                # β unit lock
optimize/results/ablation_wsi1m_4h.json            # β output (raw)
study_range_regime/REPORT_indicator_ablation_wsi1m_4h.md   # β output (ranked report, Mermaid)
```

## 6. Acceptance
- S0 unit test green; golden 6/6 unchanged.
- β: 256 subsets enumerated; all-on baseline reproduces $142,203; report ranks subsets by score with
  ΔPnL%/ΔDD/decision-pause/warmup/footprint; per-indicator marginal-impact + footprint summary present.
- Deliverable answers both: "which indicators can I drop for ≤X% P/L?" and "is the worst pause warmup or
  decision-driven?"

## 7. Next (held)
- **α** — optimizer objective swap (win-rate → **min `max_no_entry_days_decision`**) on the wsh4-era search
  space (exclude ifvg/breaker/cisd, shared SL/TP), new study prefix; its own spec.
