# Phase G — Backtesting the Volatility Model: Design & Calibration Explainer

> **Goal:** take the winning HAR-RV volatility forecast (Phase F2) and *backtest it* through a
> **clone** of the live trading engine — watching whether volatility-awareness improves the
> strategy — **without ever touching the original manual engine.**
>
> **ENGINE PROVENANCE (locked):** this uses **ONLY the verified simple single-contract engine**
> (`src/strategy/simple_strategy.py`: Stage-1 entry + dual-SL/TP exit, **1 contract, no ladder**).
> The legacy **1-1-2 ladder / scaling engine is NOT used and is explicitly out of scope** (it is
> unverified). The clone is parity-tested against the original (`tests/test_clone_parity.py`).
>
> **SINGLE-CONTRACT CONSTRAINT (locked):** position size is fixed at 1 contract in every backtest.
> Only levers that preserve single-contract are run: **S** (adaptive SL/TP) and **G** (regime gate).
> The position-sizing lever **P is EXCLUDED** — scaling contract count violates single-contract and
> would require a different, unverified engine. (P is documented below for completeness but is not run.)
>
> This doc is the design + the detailed explanation of the calibration options. Results: `28_phase_G_results.md`.

---

## 1. The crucial framing: a volatility forecast is not a strategy

HAR-RV predicts **how big** the next bar will be, not **which way** it goes. So we cannot "run the
backtest on the model" as if it were a buy/sell signal. Instead the forecast **drives three knobs**
of the *existing* strategy (whose entry signals stay exactly as they are):

| Lever | Symbol | What the vol forecast does | Single-contract? | Hypothesis |
|---|---|---|---|---|
| **S — Adaptive SL/TP** | distances | scale stop/target distances per-bar by predicted vol | ✅ yes (run) | tighter stops in calm bars, wider in turbulent → fewer premature stop-outs |
| **G — Regime gate** | trade/skip | only trade when predicted vol is in a favourable band | ✅ yes (run) | avoid the regimes where the edge historically dies |
| **P — Position sizing** | contracts | scale size by 1/predicted-vol | ❌ **NO — excluded** | (would need multi-contract; violates single-contract constraint) |

The strategy's **direction** (Stage-1 entry, normal mode, the approved manual paramset) is untouched, and **size stays at 1 contract**. We only modulate *risk geometry* (S) and *when to participate* (G). The sizing lever P is described for completeness but **not run**.

---

## 2. The combination matrix (what gets run)

Under the **single-contract constraint**, sizing (P) is excluded, leaving two valid levers → **3
non-empty combinations** + baseline = **4 backtests**:

| # | Combo | S | G | |
|---|---|:-:|:-:|---|
| 0 | **baseline** (manual, 1 contract) | – | – | reproduces the live manual version exactly |
| 1 | S | ✓ | – | adaptive SL/TP only |
| 2 | G | – | ✓ | regime gate only |
| 3 | S+G | ✓ | ✓ | the full single-contract vol-aware strategy |

Running both singles + the pair lets us **attribute** the effect — which lever helps, and whether
they interact. (The four sizing-containing cells from the original 7-combo plan — P, S+P, P+G,
S+P+G — are dropped because they require multiple contracts.)

---

## 3. The three calibration methods (detailed)

"Calibration" = how we turn a predicted volatility number into an actual distance/size. The choice
matters because it determines whether a P/L difference comes from *being adaptive* or just from
*taking more/less risk on average*. We run all three and compare.

Let `v_t` = HAR-RV forecast for bar t (in points), `v̄` = its mean over the training period, and
`d_manual` = a manual distance (e.g. sl_hard = 100 pts).

### Calibration A — Normalize to same average risk *(the fair A/B)*

```
multiplier  m_t = v_t / v̄
distance_t  = d_manual × m_t
```

- **Average multiplier ≈ 1.0**, so the *average* SL/TP across the run equals the manual values.
- The total risk budget is **the same** as manual — it's just **reallocated**: calm bars get
  proportionally tighter stops, turbulent bars wider.
- **What it isolates:** the pure value of *adaptive allocation*. If this beats baseline, it's
  because moving risk to where it's warranted helps — not because we changed how much risk we take.
- **This is the headline calibration** for the 7-combo matrix, because it's the cleanest apples-to-apples.

### Calibration B — Raw multiple (absolute, anchored to training vol)

```
distance_t = d_manual × (v_t / v_ref)      where v_ref = mean RV over 2025 (train) only
```

- Anchored to a **fixed** reference (train-period vol), **not** re-centered to the eval-period mean.
- So if 2026 is generally calmer or wilder than 2025, the **average risk drifts** with it — stops
  get absolutely tighter in a calm year, wider in a wild year.
- **What it tests:** sizing stops to *absolute* predicted volatility, accepting that average risk
  floats with the regime. More realistic for live deployment (you don't know the future mean), but
  P/L differences mix "adaptive" with "more/less total risk."
- Difference from A: A uses the *contemporaneous* mean (look-ahead-free only if computed causally);
  B uses a *frozen* train mean (always causal, but average risk can drift).

### Calibration C — Sweep a scaling constant k

```
distance_t = k × d_manual × (v_t / v_ref)      for k in {0.5, 1.0, 1.5, 2.0}
```

- Wraps calibration B with an overall risk dial `k`: `k<1` = tighter everywhere (more stop-outs but
  smaller losses), `k>1` = looser everywhere (fewer stop-outs but bigger losses).
- **What it shows:** the **sensitivity curve** — is the strategy's P/L robust to the risk level, or
  is there a sharp optimum? A flat curve = robust; a peaked curve = fragile / overfit-prone.
- Reported as a P/L-vs-k plot, run on the SL/TP-alone lever.

**Why all three:** A answers "does adaptivity help, holding risk constant?" B answers "does
absolute vol-sizing help in a realistic causal setup?" C answers "how sensitive is it to the risk
dial?" Together they separate *adaptivity* from *risk level* from *robustness*.

---

## 4. How each lever is implemented (in the CLONE, not the original)

### S — Adaptive SL/TP
At trade entry the engine computes `sl_soft_line = close − sl_soft_points`, etc. In the clone we
multiply all four distances by the per-bar `m_t`. Scaling all four by the *same* factor preserves
the engine's ordering constraints (`sl_hard ≥ sl_soft`, `tp_hard ≥ tp_soft`), so no validation
breaks. Causal: `m_t` uses only the HAR-RV forecast available at bar t's open.

### P — Position sizing
P/L is linear in contract count and sizing does **not** change entry/exit timing or lines — so it's
applied **post-hoc** to the trade list: `pnl_sized = pnl_points × size_factor_t × point_value`,
where `size_factor_t = v̄ / v_t` (constant-risk: bigger when vol is low). Normalized so mean size = 1
contract → fair vs the 1-contract baseline. (No engine change needed; provably equivalent to sizing
inside the loop.)

### G — Regime gate
Inside the clone's entry block: `if not entry_allowed_t: continue`. Skipping an entry leaves the
engine flat, so it naturally evaluates the next bar — correct state handling (this is *why* the gate
must be inside the engine, not a post-hoc trade filter, which would mis-handle re-entry timing).
Default gate: trade only when `v_t` is at or below its 80th percentile (skip the most turbulent
20% of bars) — testable, and motivated by the fat-tail risk in turbulent regimes.

---

## 5. The "never touch the original" mechanism

- The live engine `src/strategy/simple_strategy.py` is **copied verbatim** into
  `subprojects/meta-prophet/engine_clone/simple_strategy_adaptive.py`. The original file is **never
  edited** — it keeps running the manual version exactly as before.
- The clone adds three optional arguments to `backtest()` (`sl_tp_mult`, `entry_gate`, and the
  sizing is post-hoc). When all are off/None, **the clone is byte-for-byte behaviourally identical
  to the original** — verified by a regression test that runs both on the same data and asserts
  identical trades. That equality is the proof we didn't change the manual logic.
- Data is loaded **read-only** (the `NQ_full_data_{year}.csv` box files + 4h + 1min), same pattern
  the `trends_agenitic_analysis` subproject already uses.

---

## 6. What we measure (per backtest)

| Metric | Why |
|---|---|
| **Total P/L ($)** | headline — does vol-awareness make more money? |
| **vs baseline (%)** | the comparison that matters |
| **Win rate** | did adaptivity change hit quality? |
| **# trades** | gate reduces this; sizing/SL don't |
| **Max drawdown** | risk — sizing should help most here |
| **P/L per trade** | efficiency |
| **Sharpe-like (P/L / std of trade P/L)** | risk-adjusted — the metric sizing targets |

The verdict isn't just "more P/L" — a combo that makes similar P/L with **lower drawdown** or
**higher Sharpe** is a real win, especially for the sizing lever.

---

## 7. Causality & honesty guards

- HAR-RV forecast is computed **walk-forward** (fit on 2025, predict 2026 bar-by-bar) — never uses
  future data. Same discipline as Phase F.
- The gate percentile and `v̄` use **training-period** statistics (frozen), so the eval period has
  no look-ahead.
- Baseline = the *approved* manual paramset (`sl_soft=80, sl_hard=100, tp_hard=50`, normal mode,
  1 contract) — the same configuration the live system is signed off on (`backtest-approved/simple-1c-v4.0`).
- n=1 regime caveat applies (one observed 2025→2026 transition), same as every phase — results are
  indicative, not statistically conclusive.

---

## 8. Deliverables

- `engine_clone/simple_strategy_adaptive.py` — the faithful clone + 3 levers (original untouched).
- `scripts/17_backtest_matrix.py` — loads data, builds causal HAR-RV levers, runs the 8 cells + 3-calibration deep-dive.
- `outputs/backtest_matrix.csv`, `outputs/calibration_sweep.csv` — machine-readable results.
- `plots/backtest_*.png` — equity curves + matrix bar chart + calibration sweep.
- `notes/28_phase_G_results.md` — the verdict.

Next: implement the clone (G2), run the matrix (G3), report (G4).
