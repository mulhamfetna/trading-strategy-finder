# Design — M2 price/trend-state Kalman director

**Date:** 2026-07-01 · **Type:** research mechanism (Phase 3 of the Kalman/fusion study) · **Status:** design
approved, spec under review · **Anchor:** NQ 4h.

Follows M0 (`docs/RESEARCH_KALMAN_FUSION_STUDY.md`) and the **M1 negative result** (discrete multi-TF box votes
are ~coin-flip OOS → STOP). M2 uses the **continuous price series** — a different information source. Builds on
the Phase-1 rig + the M1 IS/OOS machinery (`research/kalman_fusion/`).

---

## 1. Context & goal

M0 proved: payoff is structurally pinned ~0.74 (fixed exits) → the lever is **direction / win-rate**, and the
bar is the **breakeven win-rate `1/(1+0.74) ≈ 57.5%`**. M1 tried to recover direction from **discrete** finer-TF
box votes and failed OOS (win 56.7% < 57.5%). **M2 estimates direction from a *continuous* Kalman trend/velocity
on the raw price** and asks whether that clears the breakeven bar out-of-sample.

**Goal:** build M2 on NQ 4h; produce IS (2025) / OOS (2026) Pareto fronts (entry-rate × total-P/L; payoff
auto-held) for each **decision-mode × frame-config**, vs the **champion** and **box-native** references; decide
whether M2 earns adaptive-Kalman relatives (2b) or the study redirects to M3.

**Non-goals:** no exit changes (M3); no production wiring; no reliability *fitting* (equal-weight — M1's fit
overfit); adaptive Q/R + EKF/UKF/particle are **gated on M2's vanilla result**.

## 2. The estimator — local-level + trend (constant-velocity) Kalman

- **State** `x = [level, velocity]`. **Transition** `level ← level + velocity`, `velocity ← velocity + w`
  (process noise `Q`); **observation** `y = log_close = level + v` (obs noise `R`). Standard 2-state
  linear-Gaussian filter; `q = Q/R` is the single smoothing knob (fixed default, not fit).
- **Causal:** the *filtered* estimate at bar `t` uses only observations ≤ `t` (Kalman predict→update; never a
  future-smoothing pass). Output per bar: **filtered velocity** + its **variance** → the **z-score**
  `z = velocity / sqrt(var)` — a unitless trend strength used as **conviction**.
- Reusable: `velocity_z(log_prices, q=1e-5, r=1.0) -> (z, velocity, var)` in `kalman_trend.py` (fixed defaults —
  small `q/r` ⇒ a smooth trend; the ratio is the only knob), run on any series.

## 3. Two frames as voters (equal weight, no fitting)

- **4h frame:** run the filter on the 4h log-close → `z_4h` per 4h bar; the dropped signal at bar `i` uses
  `z_4h[i-1]` (the signal bar — causal).
- **1-min frame:** run the filter on the 1-min log-close → `z_1m` per 1-min bar; align to the 4h signal bar via
  the **last 1-min bar closed ≤ signal-bar close** (reuse M1's `searchsorted`-backward alignment).
- **Combined score** `z = z_4h + z_1m` (equal weight — deliberately low-capacity; no 2025 reliability fit).
- Report **three frame-configs**: `4h-only`, `1m-only`, `combined` (all free from the same z's).

## 4. Two decision modes (both swept)

For each eligible **dropped** signal at bar `i` (champion flat), with `z = combined score at i`:
- **Re-direct:** admit iff `|z| > θ`; **direction = sign(z)** (may flip the box). Only this can reach the
  oracle headroom (which needs flips).
- **Trend-filter:** admit iff `|z| > θ` **and** `sign(z) == sign(box_dir[i-1])`; **direction = box_dir** (keep
  the box call, skip on disagreement).

`policy(C, z, θ, mode) -> (admit, direction)`: `admit = engine_gate ∪ {passing dropped}`; `direction` = fused
value written at `i-1` for admitted dropped bars, 0 elsewhere (champion bars stay native). Sweep `θ` over the
z-scale.

## 5. Evaluation (reuse M1's rig + IS/OOS)

- `policy` masks → `rig.run_book(C, admit, direction)` → split trades by entry-year → 2025 (IS) / 2026 (OOS)
  `Metrics` (via `metrics.summarize`), exactly as `m1_fusion.evaluate_m1`.
- **No in-sample fit** (equal-weight z) — the only knob is `θ`, read off the front. This is the key robustness
  advantage over M1.
- References: **champion baseline** (θ→∞ admits nothing) and **box-native admit** (M0). **Gate = OOS.**

## 6. Modules, tests, deliverable

**New:**
- `research/kalman_fusion/kalman_trend.py` — `velocity_z(log_prices, q=1e-5, r=1.0) -> (z, velocity, var)`.
- `research/kalman_fusion/m2_trend.py` — `trend_z(C, frames=("4h","1m")) -> dict[str,np.ndarray]` (per-4h-bar z
  per frame + `combined`, causal) · `policy(C, z, θ, mode) -> (admit, direction)` · `evaluate_m2(C, z, θ, mode)`
  (IS/OOS, reusing the M1 split helper).
- `research/kalman_fusion/run_m2.py` — sweep modes × frame-configs × θ → IS/OOS front table + CSV.

**Tests (`test_m2.py`, TDD):**
1. `velocity_z` on synthetic: a linear up-trend → strictly positive velocity/z; a flat series → z ≈ 0; output
   length == input.
2. **Causality guard (mandatory):** truncating the price series after bar `t` leaves every `z[≤t]` byte-identical
   (filter is forward-only).
3. `trend_z` causal alignment: truncating `C` leaves past-bar combined z unchanged.
4. policy: **re-direct** flips direction when `sign(z) ≠ box_dir`; **trend-filter** skips that signal; both
   admit when aligned.
5. high-θ reproduces the champion baseline exactly (admit nothing).
6. entry-rate is non-increasing in θ.

**Deliverable:** extend `docs/RESEARCH_KALMAN_FUSION_STUDY.md` with the six IS/OOS fronts (4h/1m/combined ×
re-direct/filter) vs champion + box-native, and the gate decision.

**Compute:** the 1-min filter runs once over the ~487k-bar series (vectorised, cheap); sweeps reuse the memoized
`fast_backtest`. Full run on the AMD server per the standing rule. Golden gate untouched (research off-path).

## 7. Success criteria & risks

**Success:** decision-grade IS/OOS fronts for all six mode×frame configs vs the references, and a clear gate
(adaptive relatives vs redirect to M3). **Risk:** the trend may be *lagging* (a filtered velocity trails turns)
→ it could confirm the wrong side after a reversal; the 1m frame is noisier. If **no** mode clears 57.5% OOS at a
meaningful entry-rate, that is the answer — continuous trend doesn't recover the dropped flow either, and the
study redirects to **M3** (regime-conditioned admission + exits, the only lever that can move payoff off 0.74).
A per-frame `q` (smoothing) sensitivity check is included at 2–3 fixed values (not fit) to rule out a degenerate
default.
