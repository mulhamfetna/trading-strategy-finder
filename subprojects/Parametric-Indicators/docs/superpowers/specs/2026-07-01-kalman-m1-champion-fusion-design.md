# Design — M1 champion-signal fusion (directional classifier for dropped signals)

**Date:** 2026-07-01 · **Type:** research mechanism (Phase 2 of the Kalman/fusion study) · **Status:** design
approved, spec under review · **Anchor:** NQ 4h.

Phase 2 of `docs/superpowers/specs/2026-07-01-kalman-signal-fusion-study-design.md`, unlocked by the **M0
ceiling** (`docs/RESEARCH_KALMAN_FUSION_STUDY.md`). Builds on the Phase-1 rig (`research/kalman_fusion/`).

---

## 1. What M0 established (why M1 is shaped this way)

The M0 ceiling proved:
- **Payoff ratio is structurally pinned at ~0.74** by the champion's fixed exits (TP≈120pt / hard-SL≈163pt) —
  entry selection moves **win-rate → total P/L**, never payoff. So "hold payoff while admitting more" is free;
  the entire lever is **direction / win-rate**.
- Admitting the 482 dropped signals **box-native loses** ($78,074 < the champion's $142,203, 59.5% win), but
  the **oracle** (perfect director) reaches **$1,300,931 (90.5% win)**. The native→oracle gap is **pure
  directional-information headroom**, roughly even across the vetoed (278) and vol-gated (204) strata.

**M1 is therefore a causal directional classifier for the dropped signals** — decide *long / short / skip* —
with exits unchanged. Success = capturing a meaningful, **OOS-robust** fraction of the native→oracle gap.

## 2. Goal & scope

Build and evaluate M1 on NQ 4h. Deliver an **IS (2025) and OOS (2026) Pareto front** (entry-rate × total-P/L;
payoff auto-held ~0.74) for the M1 director vs two references — the **champion baseline** and the **box-native
admit** line — and a **go/no-go for Phase 2b (Kalman)**.

**Non-goals:** no exit changes (that's M3); no production wiring; no cross-instrument inputs (ES was found
redundant for L1 direction — M1 uses NQ multi-timeframe only); Phase 2b (dynamic Kalman) is built **only if**
2a beats box-native OOS.

## 3. Observations — multi-timeframe NQ directions (strictly causal)

For each dropped 4h signal at decision bar `i` (signal read from bar `i-1`, the just-closed 4h bar):
- Observe the **Stage-1 box direction** (`-1/0/+1`, via `optimize.signals.decision_signals`) of the finer NQ
  timeframes **1h, 15m, 5m**, each taken from that TF's **last bar closed at or before the 4h signal bar's
  close time** — no look-ahead. Reuse the existing MTF/contributor causal alignment (`align_decbars` /
  `master_grid` machinery) so alignment is the parity-tested one.
- The **4h box direction** itself is included as one voter.
- Result: a per-dropped-signal observation vector `z ∈ {-1,0,+1}^T` (T = 4 timeframes).

## 4. Phase 2a — static weighted vote (build first)

- **Weight fit (2025 in-sample only).** For each TF `t`, its **directional reliability** = how often `dir_t`
  matches the *profitable* side of the dropped signal. The profitable side per 2025 dropped signal comes from
  M0's `signal_outcomes` (`native` vs `opposite` P/L → `sign` of the better). `w_t ∝ (hit_rate_t − 0.5)`
  (clamped ≥ 0), or a small logistic fit `P(profitable-long | z)`; start with the weighted-hit-rate form
  (simplest), keep the logistic as a within-2a variant.
- **Fusion.** `score = Σ_t w_t · dir_t`; **fused direction** = `sign(score)`; **conviction** =
  `|score| / Σ_t |w_t| ∈ [0,1]`.
- **Decision policy `policy(θ)`.** For each dropped signal: **admit** iff `conviction > θ` and `fused dir ≠ 0`,
  entering in the **fused direction**; else **skip**. The champion's own taken flow is always kept.
- **Sweep θ ∈ [0,1]** → the Pareto front (entry-rate × total-P/L). θ→1 admits nothing (⇒ champion baseline);
  θ→0 admits every confident signal.

## 5. Phase 2b — Kalman (gated on 2a's OOS result)

Only if 2a's OOS front beats box-native: latent conviction `x_t` as an AR(1) state; finer-TF votes as
observations with per-TF noise `R_t` (from reliability); Kalman posterior mean + variance → **dynamic
(time-varying) weights** and an **agreement/uncertainty gate** (admit only when posterior variance is low).
Compare its IS/OOS front against 2a.

## 6. Rig integration

Reuse `research/kalman_fusion/rig.evaluate(C, admit, direction)`:
- `admit` = `engine_gate(C)` ∪ {dropped signals passing `policy(θ)`} (boolean, length n).
- `direction` = box-native at the champion's own bars, **fused direction** at each admitted dropped bar,
  written at index `i-1` (the engine's read position); `0` elsewhere (rig keeps native there).
- `evaluate` runs the ONE parity-locked `fast_backtest` over the combined book → `Metrics`. Sequential entry
  means admits can shift later entries (known, non-monotonic — the rig captures it honestly).

## 7. IS/OOS evaluation

- Fit weights on **2025 dropped signals** only; **freeze**; apply `policy(θ)` to all dropped signals; run the
  rig; **split the ledger by entry year** → 2025 (IS) and 2026 (OOS) `Metrics`.
- Report both fronts vs the **champion baseline** and **box-native admit** points.
- **Gate:** M1 → Phase 2b only if the **OOS** front lifts total-P/L over box-native at comparable entry-rate.
  (l2v3 lesson: IS fronts lie.)

## 8. Modules, tests, deliverable

**New:** `research/kalman_fusion/m1_fusion.py` — `finer_tf_directions(C, tfs)` (causal align) · `fit_weights(...)`
(2025) · `fused(z, w) → (direction, conviction)` · `policy(C, weights, theta) → (admit, direction)`. Plus
`run_m1.py` CLI (sweeps θ, writes the IS/OOS front CSV + prints the table). One focused file each.

**Tests (TDD, `research/kalman_fusion/test_m1.py`):**
1. **Causality guard (mandatory):** input-truncation — truncating bars after `i` leaves every bar ≤ `i`'s
   finer-TF observation + fused direction byte-identical (mirrors `optimize/l2/test_causality.py`).
2. `fit_weights`: a synthetic TF that always matches the profitable side gets the top weight; a coin-flip TF ≈ 0.
3. `fused`: sign(score) correct; conviction ∈ [0,1]; unanimous → conviction 1.0.
4. rig-combined: `policy(θ=1.0)` admits nothing ⇒ `evaluate` reproduces the champion baseline exactly.
5. θ-sweep: entry-rate is non-increasing in θ.

**Deliverable:** extend `docs/RESEARCH_KALMAN_FUSION_STUDY.md` with M1's IS + OOS Pareto fronts (vs box-native +
champion) and the Phase-2b go/no-go. Artifacts under `research/kalman_fusion/` (CSVs gitignored).

**Compute:** fit + θ-sweeps reuse the memoized `fast_backtest` (cheap); the full run executes on the AMD server
per the standing no-local-heavy-compute rule. Production engine + golden gate untouched (research layer off-path).

## 9. Success criteria & risks

**Success:** a decision-grade IS/OOS front for M1 vs box-native + champion, and a clear Phase-2b go/no-go.
**Key risk:** the dropped-signal set is small (482, split ~2025/2026) → weight-fit can overfit; OOS is the gate,
and the static baseline's few parameters (T≈4 weights + θ) are deliberately low-capacity to resist it. If even
the oracle-informed weights don't generalize OOS, that itself is the answer (multi-TF direction on the dropped
flow isn't robustly recoverable) — a valid, cheap result that redirects to M2/M3.
