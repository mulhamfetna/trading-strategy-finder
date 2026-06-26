# Optimizer cap_1min Search + wsh6/l2v3 Run — Design Spec

**Date:** 2026-06-25 · **Status:** approved (brainstorm)

## Goal

Add `cap_1min` (max-hold in traded 1-min bars — the "bars" exit cap) as a **searched dimension** in the
optimizer (L1 + L2), then run a fresh **L1 round (`wsh6`)** and a **L2 round (`l2v3`)** on **4h, non-split**,
to find the hold-time that lifts PnL / shrinks DD. The resulting champions are exposed as **new
dashboard-selectable presets side-by-side** with the current ones — **nothing is overwritten**, the
frozen production L1/L2 and the golden/anchor locks stay intact.

## Decisions (locked during brainstorm)

1. **Trials: double** the per-dim budget (`--trials-per-dim 200` ≈ 10.6k L1 trials). Square is
   computationally infeasible (~28M).
2. **`cap_1min` search range:** `int 0..1440` (0 = off, up to ~1 trading day of 1-min bars).
3. **Cap mode:** search **`bars` only** (`cap_1min`; `cap_mode` stays `bars` when `cap_1min>0`, else
   `none`). End-of-day mode is NOT searched.
4. **Timeframe:** **4h only**, **non-split** SL/TP (matches the production wsh4-style champion).
5. **Execution:** launched on the remote **AMD/Postgres (`wsh-pg`)** fleet via `remote_wsi.sh`.
6. **Side-by-side, never overwrite:** `wsh6`/`l2v3` champions are saved to their own result files and
   registered as **importable dashboard presets**. Production defaults and frozen anchors are untouched;
   `perf/check_golden.py` stays ✅. Swapping a production default later is a separate explicit decision.

## Current system (from the optimizer map)

`docs/OPTIMIZER_MAP.md` has the full chart. Key seams (file:line):
- Search space `objective` (`optimizer.py:308-330`); dimension count `search_dims` (`:128-137`);
  trial budget `recommended_trials = dims × 100` (`:140`); warm-start `_native_seed`/`warm_start_seeds`
  (`:209-275`); NSGA-III, 3 objectives (median fold PnL ↑ / −worst DD / median win-rate),
  constraint `full_DD ≤ 0.25·full_PnL`.
- The missing engine wire: `core.py backtest_metrics` does NOT pass `cap_1min` to `fast_backtest`
  (the engine already accepts it — from the time-cap work).
- L2 search `l2/optimize.py suggest_l2_params`; L2 scored on L1's dropped signals; reads the frozen L1.

## Components

1. **`optimize/optimizer.py`** — `objective`: `cap_1min = trial.suggest_int("cap_1min", 0, 1440)`; add
   `cap_1min` to the params dict. `search_dims`: `base_int` 2→3 (so the plan/budget counts it).
   `_native_seed`: read `box.get("cap_1min", 0)`, clamp to `[0,1440]` (champion warm-start, default 0 →
   prior champion reproduces exactly). `CAP_1MIN_MAX = 1440` module constant.
2. **`optimize/core.py`** — `backtest_metrics`: `cap_1min = int(params.get("cap_1min", 0))`, pass
   `cap_1min=cap_1min` into the `fast_backtest(...)` call (the missing wire). `cap_mode` defaults so a
   bare `cap_1min>0` acts as `bars` (already normalised in `fast_backtest`).
3. **`optimize/l2/optimize.py`** — `suggest_l2_params`: mirror `cap_1min = trial.suggest_int(...)` so L2
   searches it too.
4. **L2-against-candidate-L1 wiring** — the L2 round must score on the **wsh6** L1's residuals, NOT the
   frozen production L1. Pass the wsh6 L1 params as an L1 override to the L2 study (the L2 optimizer
   already has a frozen-L1 read via `run_l1_cached`; add/-use an L1-params override path so the run uses
   the candidate without rewriting `wsh_lean_4h_champion.json`).
5. **Preset registration** — export `wsh6`/`l2v3` champions to their own result files
   (`optimize/results/wsh6_champions_full.json`, `l2v3_4h_champion.json`) and register them as importable
   presets (`presets.py` — the same path that lists the existing one-click champions), so they appear as
   selectable options in the dashboard alongside the current ones.
6. **Tests** — a trial's params include `cap_1min` and it reaches `fast_backtest` (a capped trial yields
   `TIME_CAP` exits); `search_dims()["total"]` increases by 1 and `recommended_trials` reflects it;
   existing optimizer + `test_fast_parity` + golden suites stay green (default cap=0 path unchanged).

## Run plan (executed on the remote fleet)

```mermaid
flowchart LR
  CODE["code: cap_1min searched (L1+L2) + tests green + golden ✅"] --> L1["L1 wsh6 · 4h non-split<br/>--trials-per-dim 200 (~10.6k)<br/>warm-start current champ (cap=0)"]
  L1 --> EX1["extract wsh6 champion<br/>→ wsh6_champions_full.json"]
  EX1 --> L2["L2 l2v3 · 4h · --trials-per-dim 200<br/>scored on wsh6 L1's dropped signals"]
  L2 --> EX2["extract l2v3 champion<br/>→ l2v3_4h_champion.json"]
  EX2 --> REG["register both as dashboard presets<br/>(side-by-side, no overwrite)"]
  REG --> VAL["report before/after on 2026 OOS<br/>(old champ vs wsh6/l2v3)"]
```

Launch via `remote_wsi.sh` (reports the plan + asks acceptance; watchdog loop to the trial target);
fresh prefixes `wsh6` / `l2v3` per the no-mix rule; storage on `wsh-pg` Postgres.

## Testing & gates

- New unit tests (above) + the existing optimizer suite.
- `perf/check_golden.py` ✅ ALL MATCH (cap-default path unchanged; no production file touched).
- After the run: a before/after report (current champion vs `wsh6`/`l2v3`) on full + 2026 OOS, and a
  dashboard check that both presets load and run.

## Out of scope (YAGNI)

- No production-default swap (separate explicit decision after reviewing results).
- No all-TF sweep (4h only this round).
- No end-of-day mode in the search (bars cap only).
- No bundle port.

## Results (2026-06-26)

The run executed, and the outcome was **richer than the spec anticipated** — it surfaced a methodological
finding (cold-start seeding bias) and an OOS-verified, triple-confirmed new champion. Full narrative:
`docs/MILESTONE_two_layers_time_capped.md`.

### wsh6 warm search — verdict: "a cap only costs PnL"

The planned warm-started `wsh6` 4h non-split cap search ran to **11,407 trials** (**8,650 feasible**).
Warm-started from the current champion (`cap=0`), it found **no capped configuration that beat the
uncapped champion on PnL**. Taken alone this would have closed the question as "the time-cap doesn't help."

### The cold-start discovery

We did **not** trust the single warm verdict. **Warm-start is a floor, not a freeze** — enqueuing the
champion guarantees `≥ seed` but re-samples all 57 dims every trial, biasing the search toward the seed's
neighbourhood. A **cold-start control** `wsh6cold` (`--no-warm-start`, **22,868 trials**, **17,807
feasible**) found a **moderate `cap=448`** config the warm search had **skipped** — exposing a mild
**seeding bias** in the warm run.

### wsh6cold champion + OOS verification

| config | full PnL | full DD | 2025 PnL | 2026-OOS PnL | OOS DD | OOS win | OOS payoff |
|---|--:|--:|--:|--:|--:|--:|--:|
| WARM / old champ (`cap0`) | $149,989 | $15,491 | $91,960 | $58,029 | $8,141 | 72.5% | 0.74 |
| COLD wsh6cold (`cap448`) | **$153,321** | **$9,589** | $90,513 | **$60,488** | $8,280 | 60.6% | **1.32** |

- **Reproduced to the cent: $153,321 / $9,589 DD.**
- **Edges the old champion OOS:** +$2,459 ($60,488 vs $58,029), **payoff 1.32 vs 0.74**, **PF 2.02 vs
  1.93**. Lower OOS win-rate (60.6% vs 72.5%) but a much healthier payoff profile.
- **DD nuance:** the −38% full-window DD is **mostly in-sample** (2025: 9,589 vs 15,491); the **2026 OOS
  DDs converge** (~$8.2k each) → **≈ DD-neutral OOS**, healthier payoff the real win.
- **Cap is load-bearing:** **127/211** trades exit via `TIME_CAP`; the **SAME config uncapped** earns only
  **$114,438 / $18,755 DD**.

**wsh6cold params:** box `sl_soft=123.30`, `sl_hard=190.45`, `tp=230.74`, `gate_pct=97.69`,
`dd_limit=1766.21`, `cooldown=1`, `k=3`, `flip=false`, `cap_1min=448`, `ind_1min=true`. 7 indicators:
`ema_trend`(fast 172/slow 362), `macd`(95/39/98), `obv`(slope 128), `cci`(n 139/thr 50),
`bollinger`(n 108/k 4.0), `adx`(n 38/thr 17), `cisd`.

### wsh7 triple-confirmation

A third re-optimization (**24,237 trials**) warm-started from **BOTH** the old champion **and** the cold
`cap=448` winner. Its best-feasible **converged back to the cold seed** (surfaced as **trial #2**);
**nothing beat it**. So `cap=448` is: **discovered by cold-start · verified OOS · unbeaten by
re-optimization**.

### L2 rounds (l2v3 / l2v4)

- **l2v3** (L2 on the **OLD frozen L1**) **overfit**: **+$78,651 in-sample → −$6,651 2026-OOS** → **NOT
  promoted**; production L2 stays **l2v2**.
- **l2v4** (L2 cold-start on the **wsh6cold L1's 569 residual signals**, via `--l1-champion`) is
  **RUNNING / pending** and will be **OOS-gated** before any promotion.

### Infrastructure delivered (beyond the spec)

- `--l1-champion` CLI flag — score L2 on any candidate L1's residuals (`617c610`).
- Candidate-L1 disk cache in `run_l1_cached` (`params != None`) — **406× faster** reload (`c03ed8a`).
- `warm_start_seeds` now enqueues **both** the old champion **and** the cold winner (`c831320`).
- wsh6cold registered as a **side-by-side dashboard preset** AND an **L1-tab profile**
  (`profiles/l1_profiles.json`) (`c831320`, `5c5c67f`).
- Verified shareable bundle `shareable/wsh6cold_4h_backtester` reproducing **$153,321**.

### Gate status

`perf/check_golden.py` ✅ 6/6 (default `cap=0` path unchanged; no production file overwritten); both
engines parity-locked on the time-cap; production defaults and anchors untouched (everything additive).
