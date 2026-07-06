# Gold (GC) + Silver (SI) Onboarding — Design Spec

**Date:** 2026-07-04
**Branch:** `stocks-drop-down-backtester-optimizer`
**Status:** approved (design), pending spec review
**Author:** pairing session

## Goal

Onboard two new COMEX metals-futures instruments — **GC (Gold)** and **SI (Silver)** — end-to-end into the
existing box-strategy system: shift their boxes back one workday, generate signals, make them selectable and
backtestable in the dashboard, wire them into the optimizer, and (behind an explicit gate) optimize each.

This mirrors the already-shipped ES / ETF onboarding. It is **additive**: NQ and ES stay byte-identical.

## Non-goals

- Running the real per-instrument optimization campaigns (server compute). That is **step 5, gated** — this spec
  builds everything up to and including a tiny local wiring smoke-test, then stops.
- Any change to the frozen Stage 1 / Stage 2 signal engine, the L1 champion, or the box strategy rules.
- Re-shifting or re-optimizing NQ / ES / ETFs.

## Source data (delivered 2026-07-06)

Two zips in the repo root:

- `silver-gold-candles.zip` → `COMEX/{GC,SI}_Continuous_Data/{GC,SI}_{1m,2m,5m,15m,1h,2h,4h}.csv`
  - Schema: `datetime,open,high,low,close,volume` (identical to NQ/ES candles).
  - Coverage: `2025-01-01 18:00 → 2026-07-02 18:00` (spans the 2025-train / 2026-test OOS split).
- `silver-gold-levels.zip` → `{GC,SI}/{GC,SI}_full_data.csv` (+ day/week/month breakdowns)
  - `*_full_data.csv` column layout is **identical to `NQ_full_data.csv`** (dOpen/wOpen/mOpen + all
    D/W/M interaction / rejection / target columns). 388 daily box rows.

The candles zip's internal tree (`COMEX/GC_Continuous_Data/GC_4h.csv`) already matches the registry's expected
layout, so placement is a copy, not a transform.

## Contract economics (confirmed with user)

| Token | Instrument | Contract          | Dollars per 1.0 point move | `point_value` |
|-------|------------|-------------------|----------------------------|---------------|
| GC    | Gold       | Full COMEX (100 oz) | $100                     | `100.0`       |
| SI    | Silver     | Full COMEX (5,000 oz) | $5,000                 | `5000.0`      |

> **Note on silver's scale:** at $5,000/point, SI dollar-P/L will look much larger than NQ's. The auto
> *price-scaled permissive default* scales the SL/TP point distances by `inst_ref/NQ_ref` (median 4h close ratio),
> which keeps **risk-per-trade** in a comparable band despite the large multiplier. Not a bug — just economics.

## Architecture — how a non-NQ instrument already flows

The instrument-aware plumbing exists (built for ES); GC/SI need **data + two registry entries**, no engine changes:

```
optimize/instruments.py  TOKENS + POINT_VALUE
        │  resolve_paths(token, tf) → (decision_csv, minute_csv, box_csv)
        ▼
all-stocks-signals/instruments.py  REGISTRY[token] → candle_csv(tf), box_csv
        │
        ├──► optimize/data.py  load_inputs()/load_box()  ── backtester + dashboard combined engine
        ├──► server.py  exposes instruments.TOKENS       ── dashboard dropdown (auto-lists GC/SI)
        └──► optimize/l2/payload.py  instrument_l1_default()
                 └─ optimized champion wsh4_champions_full_<TOK>.json if present,
                    else _scaled_permissive(token)  ── sensible day-one backtest
```

So: register GC/SI in both registries → they appear in the dropdown, resolve their data, and backtest with a
scaled-permissive default immediately. The optimizer later writes `wsh4_champions_full_GC.json` / `_SI.json`,
which automatically become their dashboard defaults.

## Design decisions

### D1 — Canonical data placement
Copy verbatim into the `ALL_STOCKS` tree the registry already anchors on:
- Candles → `ALL_STOCKS/CANDLES/COMEX/{GC,SI}_Continuous_Data/{GC,SI}_<TF>.csv`
- Raw boxes → `ALL_STOCKS/BOXS/COMEX/{GC,SI}/{GC,SI}_full_data.csv`

### D2 — Box shift −1 workday
Reuse the ETF shift logic exactly: `new_Date = old_Date − pandas.offsets.BDay(1)` (weekend-only holidays), with
the **loud invariants** (no post-shift weekend date, no duplicate/collision, every date strictly moved back). Map:
Mon→Fri(prev wk), Tue→Mon, Wed→Tue, Thu→Wed, Fri→Thu. Shifted box saved to an audit file
`shifted_boxes/{GC,SI}_full_data_shifted.csv`.

### D3 — Which box the backtester reads  ⚠️ precedent difference (flag for review)
The registry `box_csv` for GC/SI points at the **SHIFTED** box, so the delivered signals and the backtest use the
same box.
**Precedent note:** ES — the only non-NQ instrument currently wired into the optimizer — uses its **raw,
unshifted** box; the −1-workday shift was so far an ETF *signal-delivery-only* treatment (ETFs are deferred from
the optimizer). GC/SI intentionally diverge from ES here because the user's pipeline defines shift → signals →
backtester → optimizer as one chain. If cross-instrument comparability with ES matters more than internal
signal/backtest agreement, flip this to the raw box. **Chosen: shifted box.**

### D4 — Tokens / dropdown labels
`GC` and `SI` (ticker tokens, matching the data folders and every other instrument in the registry). No separate
display-name layer added (YAGNI).

### D5 — Signal generation
Frozen Stage 1 + Stage 2 engine (read-only, uniform "NQ logic"), run against the **shifted** box over
7 TF × 3 presets (`full`, `2025`, `2026`). Produces `GC_SIGNALS_DELIVERY/` + `SI_SIGNALS_DELIVERY/` bundles with
the standard folder schema and the 5 validation invariants. An isolated script (`isolated_comex_box_shift.py`,
modeled on `isolated_etf_box_shift.py`) does shift + generate + validate + package for COMEX only, never touching
NQ/ES/ETF outputs.

### D6 — Optimizer wiring + study prefixes
Instrument+tf is already plumbed. Add study prefixes `gc1` / `si1`. Prove wiring with a **1-trial local smoke
test** per instrument (proves data resolves + a trial completes; NOT a campaign). Then STOP.

### D7 — Gate before server compute
Real optimization campaigns (step 5) are **not** part of this build. After the smoke test, report proposed trial
budgets and wait for the user's explicit go before anything runs on the AMD server. (Standing rule: never run
heavy compute on the local box; optimize on the server.)

## Data flow (per instrument)

```
raw box CSV ──shift −1 BDay──► shifted box CSV ──┬──► Stage1+Stage2 ──► signal delivery bundle
                                                 └──► registry box_csv ──► backtester/dashboard/optimizer
candles CSV (7 TF) ───────────────────────────────────► registry candle_csv ──► same consumers
```

## Testing & safety

1. **Golden gate:** `python3 perf/check_golden.py` = **6/6 byte-identical** (NQ untouched). Hard stop on mismatch.
2. **Shift invariants:** the 3 loud asserts fail the run on any collision / weekend / non-backward date.
3. **Signal invariants:** the 5 existing delivery checks (count partition, no-hold = long+short, no hold in
   no-holds, reverse partition, box_id ⊆ shifted index).
4. **Registration smoke:** for each of GC/SI, `optimize.data.load_inputs("4h", instrument=<TOK>)` resolves and a
   backtest with the scaled-permissive default returns a finite trade count + P/L.
5. **Optimizer smoke:** 1 local trial per instrument completes and writes to its study.
6. **Sensitive files:** nothing under `keypass.txt`, `login.txt`, `kw-full.ovpn`, `SERVER_DETIALS.md` is ever
   staged. The two source zips + `ALL_STOCKS` data are data artifacts (respect existing .gitignore rules).

## Deliverables

- COMEX data placed in `ALL_STOCKS`; shifted boxes; `GC_SIGNALS_DELIVERY/` + `SI_SIGNALS_DELIVERY/` bundles.
- `isolated_comex_box_shift.py` (shift+gen+validate+package, COMEX-only, isolated).
- GC/SI registered in both registries; dropdown lists them; scaled-permissive backtest works.
- Optimizer prefixes `gc1`/`si1`; passing local smoke tests.
- Golden 6/6 green. Then GATE.

## Open for user (review gate)
- **D3** — confirm GC/SI backtester should read the **shifted** box (diverges from ES's raw-box precedent).
- Everything else follows the established ES/ETF pattern.
