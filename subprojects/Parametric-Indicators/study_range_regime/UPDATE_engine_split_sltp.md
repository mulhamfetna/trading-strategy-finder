# UPDATE — Engine per-direction (split) SL/TP

Verbose change log for Phase E of `ACTION_PLAN_range_regime_sltp.md` (Q3c). **Back-compat invariant:** with no
split field set, behavior is **byte-identical** to before (golden-locked). Split applies to the FINAL
(post-flip) entry direction.

## Status
- **E1 — exact engine (`engine.py`): DONE & GATED ✅**
- E2 — fast path (`optimize/fast_engine.py`) + `optimize/core.py` + optimizer search space: PENDING
- E3 — this doc + post-`wsh4` edit registry note: in progress

---

## E1 — `engine.py` (exact `SimpleStrategy`)

### Change 1 — `SimpleStrategyParams` dataclass (+8 optional fields, at the END)
Added after `flip_entry_direction`:
```
long_sl_soft_points, long_sl_hard_points, long_tp_soft_points, long_tp_hard_points  (Optional[float]=None)
short_sl_soft_points, short_sl_hard_points, short_tp_soft_points, short_tp_hard_points (Optional[float]=None)
```
Placed last so positional construction is unaffected; each `None` ⇒ falls back to the shared `*_points`.

### Change 2 — `SimpleStrategy.__init__` resolves per-side points once
After the existing shared validation, a local `_side('long'|'short')` resolves each side's 4 points (split
field if set, else shared), validates `>0` and `hard ≥ soft` per side, and stores `self._long_pts` /
`self._short_pts` (tuples). With no split set, both tuples == the shared values.

### Change 3 — entry-line branch uses the resolved tuples
The `if edir=='long' … else …` block now reads `ss,sh,ts,th = self._long_pts` (or `_short_pts`) instead of
`self.params.*_points`. Math otherwise unchanged (`entry ∓ pts·_m`). Because the tuples equal the shared values
when no split is set, the computed lines are identical.

### Tests (all green)
| Test | Result |
|------|--------|
| **T1 golden byte-match** (`perf/check_golden.py`, all 6 TFs) | ✅ MATCH — 4h $142,203/n=214, 2h, 1h, 15m, 5m, 2m unchanged |
| **T2 degenerate split == shared** (`tests/test_engine_split_sltp.py`) | ✅ 635 trades byte-identical |
| **T3 direction-consistency** (asymmetric long/short points) | ✅ 264 long / 279 short — per-side SL/TP lines exactly as set |
| **T-valid** bad per-side ordering / ≤0 | ✅ raises `ValueError` |
| **T4 fast/exact parity** (`optimize/test_fast_parity.py`, no split) | ✅ unchanged (E1 didn't touch the fast path) |

### Revert (E1)
`git revert` the E1 commit, or: remove the 8 dataclass fields, the `_side()` block + `self._long_pts/_short_pts`
in `__init__`, and restore the line branch to `self.params.*_points`. No other file depends on E1.

---

## E2 — PENDING (fast path + optimizer)
- `optimize/fast_engine.py`: make the vectorized SL/TP line computation per-direction (same fall-back rule).
- `optimize/core.backtest_metrics`: pass split params through.
- `optimize/optimizer.py`: add long/short SL/TP bounds to the search space (guarded so existing studies that
  don't set split stay byte-identical).
- New test: **fast WITH split == exact WITH split** (extend `test_fast_parity`).

## Registry — post-`wsh4` edit (for `wsh5`)
This split is an **engine capability added AFTER the `wsh4` champion sweep**. A future `wsh5` run can search the
widened space (independent long/short SL/TP). The deployed `wsh4` champion is unaffected (it sets no split ⇒
identical). Recorded so the `wsh5` search space deliberately includes the split dimensions.
