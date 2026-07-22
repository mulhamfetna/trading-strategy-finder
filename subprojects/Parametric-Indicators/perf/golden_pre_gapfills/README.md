# golden_pre_gapfills — the OLD (fill-at-the-line) baseline

Captured before the gap-aware fill change of 2026-07-20 (GAP-01).

These baselines were produced by the engine when **every hard SL/TP filled exactly at its line**, even
when the triggering bar had already OPENED beyond it — i.e. a fill that was never actually available.

They are kept because that behaviour is still exactly reproducible: set `gap_fills=False`
(`SimpleStrategyParams.gap_fills` / `fast_backtest(..., gap_fills=False)`). Every historical figure in
the project's reports was produced under this model, so this directory is what makes those figures
auditable rather than merely archived.

**Do not use these as the current gate.** The live baseline is `perf/golden/`, captured under
`gap_fills=True`. See docs/superpowers/GAP-01-how-the-engine-fills-a-gapped-stop.md.
