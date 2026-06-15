# Notes for the NEXT full optimizer run (wsh5) — carry these forward

Post-`wsh4` edits that change what a fresh optimizer run should search. The deployed champion (`wsh4`,
4h decision frame / 1-min indicators) is **shared-SL/TP, all-indicators-on**; these notes widen the space.

## 1. Split long/short SL/TP is now searchable (Q3 / E2)
- New optimizer inputs available: `long_sl_soft`, `long_sl_hard`, `long_tp`, `short_sl_soft`, `short_sl_hard`,
  `short_tp` (per-side; hard = soft + delta, same per-TF bounds as the shared path).
- **Enable with:** `optimize.optimizer.run(tf, ..., split_sltp=True, study_prefix="wsh5")`.
- **Default is OFF** (`split_sltp=False`) ⇒ shared SL/TP ⇒ identical to wsh4. The wsh4 champion used
  long==short; turning this on lets buys and sells get their own stops/targets (user's point 5).
- Plumbing is golden- + fast-parity-locked (see `UPDATE_E2_split_threading.md`).

## 2. Use a NEW study prefix
Per standing rule: fresh runs use a NEW prefix (**`wsh5`**), never reuse `wsh4`. Per-TF Postgres DBs on the
AMD server (`wsh-pg`, creds in `$WSI/pg.env`).

## 3. (If adopted later) other widenings flagged by the studies — NOT yet wired
- The regime study's robust rule (trend-follow · pinned-SL · widen-only) and the structure detectors
  (IFVG / breaker / CISD / swing labels) are **not** in the optimizer search space; they'd each need a
  vote/gate wiring step before a run could search them. Documented, not built.

## 4. Adoption gate (unchanged)
Only swap the deployed champion if the new (split / wider) search OOS-dominates on return/DD under the
pre-registered walk-forward rule. Fixed champion stays deployed until then.
