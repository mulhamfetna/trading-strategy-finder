# max-1min-open-trade-streak-cap — time-based exit — design

**Date:** 2026-06-23 · **Status:** approved (brainstorm) → ready for implementation plan
**Prerequisite (done):** verbose causal logs + log-first audit
(`docs/superpowers/specs/2026-06-23-verbose-causal-logs-and-output-audit-design.md`) — the new exit
surfaces in the log/CSV/dashboard automatically because the log is now fully field-driven.

## What & why

Add a **per-layer maximum-hold-time cap**: if an open trade is held for more than `cap_1min`
**1-minute bars** without any other exit firing, force-close it at that bar's close as a new
exit cause `TIME_CAP`. It bounds how long capital sits in a stagnant position. `cap_1min = 0`
disables it (the default), so the system is byte-identical to today unless a user opts in.

This is "max hold time" — a pure time-in-position cap. It does **not** re-evaluate indicators while in
position; "indicators not hit" simply means "no SL/TP/soft-SL exit fired."

## Decisions (locked during brainstorm)

1. **Meaning:** max hold time. Count **traded** 1-min bars since entry (bars present in the data, *not*
   wall-clock minutes); force-close on the Nth bar if nothing higher-priority fired. **Gap caveat
   (confirmed 2026-06-23):** NQ futures are closed overnight/weekends, so those windows have no 1-min
   bars. A gap-crossing trade therefore holds exactly N traded bars but can span several calendar days
   (e.g. `cap_1min=240` → 3h59m for a gap-free trade, but a Friday-afternoon entry exits ~Sunday). This
   is intended; the user chose "count traded bars" over a wall-clock cap. Dashboard label + tooltip say
   "traded 1-min bars" to make the unit explicit.
2. **Scope:** per-layer parameter `cap_1min` (L1 and L2 independent), beside `sl_soft/sl_hard/tp/...`.
3. **Mechanics:** fill at the Nth 1-min bar's **close**; precedence **hard-SL > hard-TP > soft-SL >
   TIME_CAP**; the counter spans decision windows; for L2 the existing L1-entry force-close still wins
   if it happens first.
4. **Default `0` = off** everywhere → no behaviour change, anchors/golden unchanged.
5. **Model it as a 4th exit candidate in BOTH engines** (`engine.py` loop + `optimize/fast_engine.py`
   vectorized), kept trade-for-trade identical by `test_fast_parity`. Post-processing/truncation was
   rejected — it isn't causal (closing earlier frees the account and shifts later entries).

## Counting definition (exact)

`N = cap_1min`. The trade's **bar 1** is the first 1-minute bar with timestamp ≥ `entry_time` (the same
"skip pre-entry" rule the exit walk already uses). On **bar k**, the engine first checks hard-SL,
hard-TP, soft-SL (unchanged). If none fired and `N > 0` and `k >= N`, the trade force-closes at that
bar's **close** with `exit_reason = TIME_CAP`. (Equivalently: TIME_CAP fires at the close of bar N
unless a higher-priority exit already closed the trade on bars 1..N.)

## Section 1 — Parameter & schema

- Add `cap_1min: int` (≥ 0; `0` = disabled) to the layer param schema next to
  `sl_soft/sl_hard/tp/gate_pct/dd_limit/cooldown/k`. Per-layer.
- Validation: non-negative integer; reject negatives with the existing param-error path.
- Dashboard: a **"Max hold (1-min bars)"** numeric field in the L1 and L2 forms; round-trips through
  saved profiles like every other knob (default `0`).
- `SimpleStrategyParams` (engine.py) gains `cap_1min` (default `0`).

## Section 2 — `engine.py` exit walk + new reason

- Add `'TIME_CAP'` to the `ExitReason` type.
- Track a per-trade `bars_since_entry` counter in the 1-min walk (incremented on each walked bar at/
  after entry; persists across decision-window walks; reset with the trade on close).
- After the `hard-SL > hard-TP > soft-SL` checks, add: if `cap_1min > 0 and bars_since_entry >= cap_1min
  and exit_reason is None:` set `exit_reason='TIME_CAP', fill=m_close`. This yields precedence
  SL-hard > TP-hard > soft-SL > TIME_CAP within the bar.
- For L2, the L1-entry force-close path is unchanged — first-wins.

## Section 3 — `fast_engine.py` vectorized parity

- When `cap_1min > 0`, compute `t_cap` = the 1-min index at offset `cap_1min − 1` from the trade's first
  walked bar, clamped to the walk window; else `t_cap = -1` (absent).
- Append to the existing candidate `order` as **lowest priority**:
  `order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line), (t_soft, R_SL_SOFT, None),
  (t_cap, R_TIME_CAP, None)]` — fill = that bar's close (`line is None` → close). The existing
  earliest-index / lowest-rank selection keeps TIME_CAP last on ties, matching the loop engine.
- Add the `R_TIME_CAP` reason constant + its string mapping mirroring the other `R_*` reasons.

## Section 4 — Plumbing, defaults, tests

- Thread `cap_1min` through `fast_backtest(...)`, `l1_runner.run_l1`, `engine.run_l2`, and the L1/L2
  layer-param dicts (`payload.validate_layer_params` accepts it; `_layer_from_strategy` maps the
  dashboard field).
- The new exit appears in the verbose per-candle log, CSV, and dashboard with no extra plumbing
  (field-driven); add a `TIME_CAP` label/chip styling where exit reasons are rendered.
- **Default `0` ⇒ no cap candidate ⇒ byte-identical.** `perf/check_golden.py` and the parity anchors
  stay green with **no re-lock**.
- Tests:
  - **parity (off):** `cap_1min=0` reproduces current results (golden ✅; fast==engine).
  - **behavioural:** a crafted long-held trade with `cap_1min=N` and SL/TP far away exits `TIME_CAP` at
    the close of bar N (assert exact exit bar + price + reason), both long and short.
  - **engine↔fast parity (on):** `test_fast_parity` extended with a `cap_1min>0` case, trade-for-trade.
  - **precedence:** a bar where soft-SL and the cap both come due → soft-SL wins (cap only fires when no
    higher-priority exit did).

## Out of scope

- Adding `cap_1min` to the optimizer search space (separate, later).
- Porting to the `shareable/*` bundles (follow-up, as with the verbose-logs work).
- Any change to entry logic or the other exits.

## Risks

- **Parity drift between the two engines** on the exact cap bar/price. Mitigation: a dedicated
  `test_fast_parity` case with the cap on, plus the crafted behavioural test pinning the exact bar.
- **Off-by-one in the counter** (bar 1 = first bar at/after entry). Mitigation: the behavioural test
  asserts the exact exit bar index and price for a known series.
