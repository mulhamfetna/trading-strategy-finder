# Gold (GC) + Silver (SI) + ES Onboarding — Status

**Date:** 2026-07-04  ·  **Branch:** `stocks-drop-down-backtester-optimizer`
**Spec:** `docs/superpowers/specs/2026-07-04-goldsilver-onboarding-design.md`
**Plan:** `docs/superpowers/plans/2026-07-04-goldsilver-onboarding.md` (+ REVISION 2)

## Instruments
| Token | Name   | Exchange | Contract        | point_value | Box       |
|-------|--------|----------|-----------------|-------------|-----------|
| GC    | Gold   | COMEX    | Full (100 oz)   | 100.0       | shifted −1 workday |
| SI    | Silver | COMEX    | Full (5,000 oz) | 5000.0      | shifted −1 workday |
| ES    | E-mini S&P | CME  | (existing)      | 50.0        | **re-pointed** to shifted −1 workday |
| NQ    | (anchor) | CME    | (existing)      | 20.0        | **never shifted** (golden anchor) |

## Done (prep — local, light, single-process only)
- **Data placed** under `ALL_STOCKS/{CANDLES,BOXS}/COMEX` for GC + SI (7 TF each + boxes). ES already on disk.
- **Boxes shifted −1 workday** for ES/GC/SI via the reusable `all-stocks-signals/onboard_stock.py`
  (`shifted_boxes/{ES,GC,SI}_full_data_shifted.csv`) — clean backward bijection, unit-tested.
- **Registered** GC (pv 100) + SI (pv 5000) in both registries; **ES re-pointed to its shifted box**. Dashboard
  dropdown now lists NQ/ES/GC/SI. Each non-NQ backtests with the auto price-scaled permissive default.
- **Stale ES champion retired:** `wsh4_champions_full_ES.json` → `…_ES.stale-rawbox.json` (it was tuned on the
  raw box). ES now uses the scaled default until re-optimized on the shifted box. The Jun-30 `*_wsi_pareto_ES.*`
  set is likewise raw-box history.
- **Golden 6/6 byte-identical** — NQ unchanged (4h $142,203/214, 2h $91,996/262, 1h $99,172/315, 15m $77,098/654,
  5m $23,926/332, 2m $29,777/276).
- **9/9 instrument tests green**; GC/SI/ES all resolve candles + shifted box in-process (GC/SI 2318 4h bars;
  ES 2119).
- **Reusable pipeline + SOP** shipped: `onboard_stock.py` + `NEW_STOCK_ONBOARDING_SOP.md` (STEP 0 human-gate:
  confirm same-or-modified pipeline + point-value per contract before onboarding any new stock).
- **Signals generated** (Stage 1 + Stage 2, 7 TF × 3 presets, against the shifted box) → `{ES,GC,SI}_SIGNALS_DELIVERY`
  (+ `.zip`, 80/103/94 MB). Each validated OK on the 5 invariants; 105 CSVs per token.
  - **Ran on the AMD server** (`amd-trading`, 32 threads, 128 GB RAM) via `onboard_stock.py --jobs 16` — minutes,
    not the ~1 hr the RAM-bound local serial pass would take. Local box (14 GB, ~3.5 GB free) can't safely
    parallelize the 1m pass, so heavy signal-gen is a server task now.
  - **Parallel == serial parity proven:** server-parallel SUMMARY is byte-for-byte identical to the local-serial
    SUMMARY for ES and GC. `--jobs` only changes concurrency, not output.

## Optimizer wiring
The optimizer already threads `instrument` end-to-end (`optimizer.run(... instrument=...)`, `_bounds_for` scales
point-bounds for non-NQ, `point_value(instrument)`). Its data entry point is `data.load_inputs(tf, instrument)` —
the exact call the in-process resolve smoke already exercised successfully for GC/SI/ES. The **1-trial optimizer
smoke was intentionally NOT run locally** (no-local-compute rule; the optimizer is what strained the box on
2026-06-30). It becomes the first, tiny step of the server run below.

## GATE — awaiting explicit user go before ANY server / optimizer compute
Real per-instrument campaigns are **not** started. When approved, on the AMD server only:
1. 1-trial wiring smoke per token (`optimizer.py 4h --trials 1 --folds 2 --study-prefix <t>1 --instrument <TOK>`).
2. Full `--auto-trials` campaign on 4h first, then other TFs, per token: `gc1`, `si1`, and an ES re-opt on the
   shifted box (e.g. `es_shift1`).
3. Extract each champion → `wsh4_champions_full_{GC,SI,ES}.json` → verify dashboard default → 2026 OOS check.
