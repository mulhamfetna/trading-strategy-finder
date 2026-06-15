# Detailed report — structure/registry + split-SL/TP stream (2026-06-15)

One report for the whole task stream the user opened after the price-range registry: the LL/HL/HH/LH structure
tables + ICT detectors, the registry trend-rule change, the split long/short SL/TP plumbing + sweep, and the
charts. Every code change is listed with its verification. Companion docs are cross-linked.

## 0. What was asked (Q1–Q6) and what was delivered
| Q | Ask | Delivered | Key file(s) |
|---|---|---|---|
| Q5 | trend follows HH (up) / LL (down); keep new/repeat on cumulative all-time record; regenerate | ✅ | `range_registry.py`, `REPORT_Q5_trend_rule.md` |
| Q1 | sweep split long/short SL/TP (champion fixed), table+report; pin wsh5 input | ✅ | `split_sltp_sweep.py`, `REPORT_Q1_split_sltp.md`, task #217 |
| Q3 | thread split SL/TP through fast engine + optimizer; defaults = current strategy; flag next run | ✅ | `fast_engine.py`, `core.py`, `optimizer.py`, `strategy.py`, `UPDATE_E2_split_threading.md`, `NEXT_OPTIMIZER_NOTES.md` |
| Q2 | charts after updates+tests+docs; full csv/markdown/chart set | ✅ | `regime_charts.py` (+ regenerated tables) |
| Q6 | plan OB/breaker entry placement + confirmation (plan only) | ✅ | `PLAN_entry_rules.md` |
| (B) | LL/HL/HH/LH tables + IFVG + breaker + CISD | ✅ | `indicators/smc.py` (+4 detectors), `structure_tables.py`, `DEFINITION_BOOK.md` |

## 1. Engine / optimizer code changes (all golden- + parity-locked)
- **`indicators/smc.py`** — added 4 causal detectors: `swing_labels` (LL/HL/HH/LH), `ifvg` (inverse FVG,
  close-burn), `breaker_blocks` (OB closed-through → flipped entry zone), `cisd` (standard close-through prior
  delivery-leg open). Existing detectors untouched.
- **`optimize/fast_engine.py`** — `fast_backtest` gained 6 optional split args (`long_*`/`short_*`); resolved
  to per-side points, lines keyed on the FINAL direction. None ⇒ shared ⇒ byte-identical.
- **`optimize/core.py`** — `backtest_metrics` reads split keys from `params` and passes them through.
- **`optimize/optimizer.py`** — `run(..., split_sltp=False)`; when True the objective searches separate
  long/short SL/TP. Default off ⇒ identical to wsh4.
- **`strategy.py`** — `validate_params` accepts optional split keys (validated per side, None default);
  `build_payload` threads them into `SimpleStrategyParams`. None ⇒ byte-identical (golden presets set none).
- **`optimize/test_fast_parity.py`** — added T4 split cases.
- **`tests/test_smc.py`** — +4 detector tests.

### Verification (every gate green)
- **golden byte-match 6/6 TFs** — run TWICE (after `fast_engine` and after `build_payload`): all MATCH
  ($142,203/$91,996/$99,172/$77,098/$23,926/$29,777). Engine results unchanged.
- **fast-vs-exact parity** incl. split T4: 8/8 (split 247/247, split-flip 783/783 trade-for-trade).
- **optimizer core parity** (`test_parity.py`): OK.
- **unit**: `tests/test_smc.py` (13) + `tests/test_engine_split_sltp.py` (3) = 16/16 pass.

## 2. Findings
- **Q5 trend (relative HH/LL):** LOW_TREND now appears (month 8 / quarter 2; e.g. 2024-04, 2025-04 dips). The
  new/repeat signal stays on the cumulative all-time record (0 NEW_LOW over the up-only era — correct).
- **Q1 split SL/TP:** the **symmetric champion (1.0/1.0 = $142,203, ret/DD 10.10) is the best cell**; no
  asymmetric long≠short cell beats it (best asym L1.0/S0.75 = $117,078, ret/DD 9.22). Widening longs balloons
  DD; shrinking both cuts P/L. → keep shared; the definitive test is the wsh5 free joint search (task #217).
- **Structure tables (swing_l=3):** 740 pivots — HH 209 / HL 212 / LH 164 / LL 153 (HH+HL dominance = uptrend,
  matches the registry HIGH_TREND).

## 3. Artifacts (study_range_regime/results/)
CSV: `registry_{month,quarter,year}.csv`, `band_registry_*.csv`, `structure_swings_l{2,3,5}.csv`,
`structure_swings_summary.csv`, `structure_events_l3.csv`, `split_sltp_sweep.csv`.
Markdown: `REGISTRY_TABLES.md`, `STRUCTURE_TABLES.md`.
Charts: `chart_regime_ribbon.png`, `chart_structure_swings.png`, `chart_period_bands.png`.

## 4. Still open (pinned, not built)
- **task #217** — wsh5 optimizer with `split_sltp=True` (definitive split test).
- **Q6 entry rules** (`PLAN_entry_rules.md`) — OB/breaker entry placement + confirmation, IFVG/breaker/CISD as
  optimizer votes — awaiting go-ahead.
- The 3 earlier dynamic-SL/TP open items (regime_charts is now done; split-sweep done; E2 done) — effectively
  closed by this stream except the wsh5 run itself.

## 5. Reproduce
`range_registry.py` → `structure_tables.py` → `split_sltp_sweep.py` → `regime_charts.py`; gates:
`optimize/test_fast_parity.py`, `optimize/test_parity.py`, `pytest tests/test_smc.py tests/test_engine_split_sltp.py`,
`perf/check_golden.py`.
