# Plan — M3 vol-regime exits & admission

Spec: `docs/superpowers/specs/2026-07-02-kalman-m3-regime-design.md`. TDD, off-path (`research/kalman_fusion/`),
golden untouched. Walk-forward only. 3a is the decisive gate; 3b runs only if 3a survives.

## Task 1 — loader surface (additive)
- `counterfactual_pause.load_champion`: add `vf=vf, n_split=n_split` to the returned dict.
- Add `simulate_one_custom(C, entry_idx, sls, slh, tp, flip)` = `simulate_one` with exit params exposed;
  keep `simulate_one` delegating to it with champion params (proves identity).
- Verify: existing `test_*` still green (no behavior change).

## Task 2 — `test_m3.py` (write FIRST, must fail)
The 6 tests from spec §6.

## Task 3 — `m3_regime.py`
- `regime_labels(vf, train_hi)` → int array {0,1,2}; cuts = `np.quantile(vf[:train_hi], [1/3, 2/3])`.
- `EXIT_SCHEMES = {"TIGHT":0.75, "BASE":1.0, "WIDE":1.5}`.
- `rescore_trade(C, trade, scheme)` → P/L via `simulate_one_custom` with scaled `(sls, slh, tp)`.
- `learn_exit_map(C, trades, regimes, train_mask)` → `{regime: scheme}` (train P/L-max).
- `apply_exit_map(C, trades, regimes, exit_map, test_mask)` → summed test P/L.
- `admit_by_regime(C, regimes, train_mask, breakeven=0.575)` → set of admitted regimes.

## Task 4 — `m3_walkforward.py`
- Reuse `m2_walkforward.quarter_folds`.
- `walk_forward_3a(C)` → per-fold rows {q, exit_map, m3_pnl, base_pnl, champ_pnl, m3>base}, aggregate + verdict.
- `walk_forward_3b(C)` → per-fold admission rows vs champion (only called if 3a survived).

## Task 5 — `run_m3.py` CLI + run
- Print 3a table + ✅/❌ verdict; if survived, 3b table.
- Run on NQ 4h; record numbers.

## Task 6 — record verdict
- Append M3 section to `docs/RESEARCH_KALMAN_FUSION_STUDY.md` (honest, walk-forward numbers).
- Commit to dev.
