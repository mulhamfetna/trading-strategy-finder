# UPDATE — Phase E2: thread split long/short SL/TP through fast engine + core + optimizer (Q3)

**Date:** 2026-06-15. **Goal (Q3):** make the *fast* path and the *optimizer* able to use separate long vs
short SL/TP, with **defaults equal to the current winning strategy** (long==short==shared ⇒ byte-identical),
and **flag a note for the next full optimizer run** that long/short can now differ. Engine E1 (exact
`SimpleStrategy`) already had the split fields; this wires the rest.

## Every change (with why)
1. **`optimize/fast_engine.py::fast_backtest`** — added 6 optional kwargs `long_sl_soft/long_sl_hard/long_tp`
   and `short_*` (default `None`). Resolved ONCE before the loop to `L_*`/`S_*`, each falling back to the shared
   `sl_soft/sl_hard/tp` when `None`. The per-trade line block now picks the FINAL-direction's points
   (`L_*` for long, `S_*` for short). *Why:* mirrors the exact engine's `_long_pts`/`_short_pts`; `None`
   everywhere ⇒ `L_*==S_*==shared` ⇒ bit-identical to the old path.
2. **`optimize/core.py::backtest_metrics`** — reads `long_*`/`short_*` from `params` (each `None` if absent)
   into `_split` and passes `**_split` to `fast_backtest`. *Why:* lets the optimizer/dashboard pass split
   values through the metrics wrapper; absent ⇒ shared ⇒ identical.
3. **`optimize/optimizer.py::run`** — added `split_sltp: bool = False`. When `True`, `objective` suggests
   `long_sl_soft/long_sl_hard_delta/long_tp` + `short_*` (same per-TF bounds `b`; hard = soft + delta per side)
   and puts them in `params`. When `False` (default) nothing changes. *Why:* opt-in widened search for the next
   run; current runs are untouched.
4. **`optimize/test_fast_parity.py`** — added **T4**: two split cases (different long vs short points, normal +
   flip) asserting fast == exact engine trade-for-trade.

## Verification (all green)
- **fast-vs-exact parity** incl. T4 split: 8/8 cases OK (split L30/40/60·S50/70/90 → 247/247; split-flip → 783/783).
- **optimizer core parity** (`test_parity.py`): PARITY OK ✓.
- **golden byte-match**: 6/6 TFs MATCH (engine results unchanged — split defaults to shared).
- **unit**: `tests/test_smc.py` + `tests/test_engine_split_sltp.py` 16/16 pass.

## Defaults = current winning strategy
No split values are set anywhere by default → both directions use the deployed champion's shared
`sl_soft=149.8 / sl_hard=167.1 / tp=120.2`. Behaviour is identical to before this change until someone
explicitly sets split values (the Q1 sweep) or runs the optimizer with `split_sltp=True`.

## Revert
Remove the 6 kwargs + `L_*`/`S_*` block in `fast_backtest`; remove `_split` + `**_split` in `backtest_metrics`;
remove the `split_sltp` arg + its `objective` block in `optimizer.run`; drop the T4 cases in test_fast_parity.
Nothing else references these, so removal restores the prior bytes exactly.

## NOTE FOR THE NEXT FULL OPTIMIZER RUN (wsh5)
See `NEXT_OPTIMIZER_NOTES.md`. In short: launch `optimizer.run(..., split_sltp=True, study_prefix="wsh5")` to
search separate long/short SL/TP. The deployed wsh4 champion used shared values; split widens the space.
