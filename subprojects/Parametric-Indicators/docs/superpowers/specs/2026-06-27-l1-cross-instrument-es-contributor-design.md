# L1 cross-instrument ES contributor — design

**Date:** 2026-06-27
**Status:** approved (design), pending implementation plan
**Related:** `docs/superpowers/specs/2026-06-26-cross-instrument-l2-state-feature-layer-design.md` (the L2 version),
`optimize/l2/contributors/` (the reusable contributor module), `docs/XINST_ES_STATE_TOUCH_VS_TRAVERSAL.md`.

## 1. Goal & motivation

Add **ES as a searchable cross-instrument contributor to the L1 (main) optimizer**, so the optimizer can
decide — *fairly and without forcing* — whether ES improves the whole-NQ strategy.

**Why L1, not L2.** The L2 contributor run (`l2es1`) proved sound but un-answerable: L2 trades only L1's thin
*dropped residual*, so every ES-on trial fell below the 5-trade prune floor (97/98 pruned) and ES was
structurally excluded — not fairly evaluated (see `l2es1` analysis). L1 trades the **full NQ signal set over
the whole period** (hundreds of trades), so ES-on trials survive scoring and the optimizer can keep ES on or
turn it off **on the merits**. The two-layer architecture is preserved; this only adds an *option* to L1.

**Verdict it produces:** does the best L1-with-ES champion beat the best ES-off L1 (full-period / OOS P/L vs
DD), and does the champion keep ES enabled? That answers "does ES help NQ?" and is the first concrete step
toward merging cross-instrument signals into the main decision frame (the mega-goal's unified state frame).

## 2. Architecture — where ES attaches

The L1 optimizer (`optimize/optimizer.py`) scores each trial via `optimize/folds.py:score_walkforward` →
`optimize/core.py:backtest_metrics`, which builds the NQ indicator gate **once per trial over the full
window** (`core.py:98–119`): `src = runner.indicator_source_1min(...)`, `vmask = runner.veto_mask(...)`,
`cmask = runner.confirm_mask(...)`, folded into `gate = vol_gate ∧ ¬veto ∧ confirm≥K`, then sliced per fold.

**Injection point:** the same block. After the NQ veto/confirm masks are built, compute the ES contributor
masks and combine them into the gate exactly as `engine._l2_eligibility` does for L2:

- Build a lightweight adapter exposing `df_dec / df1 / bar_td / sig_int` (all already present in
  `backtest_metrics`) and call `optimize.l2.contributors.gate.contributor_gate_masks(cfg, l1adapter)` →
  `(veto: bool[n], confirm_count: int64[n])` per enabled contributor.
- Combine by `contributor_topology` (Spec §6 of the L2 design):
  - veto = NQ veto **OR** any contributor veto (any-OR, always)
  - confirm: `separate_and` (NQ ∧ each contrib count ≥ k_es) · `merged` (pooled count ≥ min(k,#sources)) ·
    `or_boost` (NQ ∨ any contrib count ≥ k_es)
- Computed **once per trial over the full window**, then sliced per fold — same cadence as the NQ gate, so
  the (expensive) ES committee compute is paid once per trial, not once per fold.

**Reuse, don't duplicate.** The entire `optimize/l2/contributors/` module (registry, loader, align, state,
votes, gate) is instrument-agnostic and used as-is. The combine logic mirrors `_l2_eligibility`; factor the
shared topology-combine into a small helper so L1 and L2 share one source of truth (no divergence).

**Non-negotiable invariant:** with no enabled contributor, the gate is **byte-identical** to today's L1 ⇒
golden 6/6 across all 6 TFs. The contributor block is purely additive and opt-in.

## 3. Search space

Factor `optimize/l2/optimize.py:_suggest_contributor` into a shared module (e.g.
`optimize/contributor_search.py`) and add the ES block to `optimizer.py`'s objective, **opt-in** when
`--contributors` is passed (empty ⇒ byte-identical existing L1 space):

- `contributor_topology` ∈ {separate_and, merged, or_boost}
- per ES contributor: `es_enabled` (**searchable, NOT forced**), `es_state` ∈ {touch, traversal},
  `es_k_es` ∈ [1,5], composite signal voter (`es_sig_enc`/`es_sig_mode`/6-cell truth table), and the ES
  indicator committee.
- **ES committee indicators:** exclude the SMC family (already) **and** `stochastic` + `adx` (the two
  heaviest non-SMC, ~2.2s each on the 487k-bar ES frame). L1 scores K folds + a full backtest per trial, so
  committee cost matters; trimming keeps per-trial time sane. Excluded keys are reported (stdout note +
  champion JSON), reusing the existing exclusion mechanism.

## 4. Golden-safety & testing (TDD)

Build test-first. Tests:
1. **Byte-identical OFF:** with no `contributors`, the L1 gate / `backtest_metrics` output is byte-identical
   to current (gate-level equality + a full backtest P/L match on ≥1 TF).
2. **ON changes the book:** an enabled ES contributor changes the L1 trade set (proves it reaches the gate).
3. **No look-ahead:** mutating future ES bars does not change earlier-bar gate decisions (reuse the existing
   contributor look-ahead guard pattern).
4. **Topology combine parity:** the shared combine helper produces the same result as `engine._l2_eligibility`
   for the same inputs (locks the single source of truth).

**Gate:** `perf/check_golden.py` must stay 6/6 (4h $142,203/214, 2h $91,996, 1h $99,172, 15m $77,098,
5m $23,926, 2m $29,777) at every step — the contributor-off path is the safety net.

## 5. Run configuration

- New study prefix (e.g. `wshes1`), **4h**, `--contributors ES`, ES **searchable not forced**.
- Postgres-backed, watchdog/respawn pool on the AMD server; worker count per the measured bandwidth sweet
  spot (~16; the box is memory-bandwidth-bound). Trial budget sized to fit the time box (decision run, not a
  full production sweep) — set when launching.
- **Baseline / verdict:** compare the L1+ES champion to the current ES-off L1 champion (frozen/cold) on
  full-period and OOS P/L vs DD. ES "helps" iff the champion keeps `es_enabled=True` **and** beats the ES-off
  baseline out-of-sample.

## 6. Out of scope (YAGNI)

- QQQ/SQQQ contributors (ETF session alignment seam I1 + SQQQ inverse orientation — a later standard).
- The candidate-L1 cache fix (separate perf task).
- The dynamic π(state) policy head (the mega-goal; this is the substrate step before it).
- Re-running the L2 contributor study (`l2es1` stays preserved/resumable in Postgres).
