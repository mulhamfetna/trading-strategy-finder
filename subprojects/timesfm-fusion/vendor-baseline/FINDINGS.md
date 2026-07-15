# Findings — TimesFM for NQ/ES futures (as of this run)

Data: 2025-01-01 → 2026-05-19 (~16.5 months, a bull sample). n=1 period. TimesFM 2.5 (200M, zero-shot,
CPU). All "OOS"/"causal" numbers below use no future information.

## 1. TimesFM as a DIRECTION predictor — fails (as expected)

On raw price, the median forecast is ~flat (persistence / random walk). Directional diagnostics
across timeframes — direction gets WEAKER intraday, band calibration stays ~72–73% everywhere:

| tf | hit rate | corr(exp,realized) | band calibration |
|---|--:|--:|--:|
| ES 1h | 51.5% | +0.17 | 73% |
| NQ 1h | 53.4% | +0.18 | 72% |
| ES 30m | 50.3% | +0.11 | 73% |
| NQ 30m | 52.1% | +0.06 | 72% |
| ES/NQ 15m | ~50% | (weaker still) | ~72% |

Standalone directional walk-forward (70/30): ES OOS +$2.8k (retDD 0.42), **NQ OOS −$12.7k**. The
train edge does not survive OOS. **Do not use TimesFM to pick direction, at ANY timeframe.** The
corr is inflated by overlapping forecast windows; going finer only adds noise.

## 2. TimesFM as a VOLATILITY / regime filter — the real edge

The quantile band is reasonably calibrated (~73%). Overlaying a **causal, untuned** vol gate on the
REFERENCE strategy's own trades (drop trades whose pre-entry forecast band is in the top ~15–25% of
its expanding history):

**NQ 1h — big, robust win:**
| | trades | P/L | maxDD | Return/DD | win | PF |
|---|--:|--:|--:|--:|--:|--:|
| reference (all) | 481 | $173,789 | $18,572 | 9.36 | 55% | 1.51 |
| **+ vol gate p85** | 447 | **$194,536** | **$10,358** | **18.78** | 56% | 1.66 |
| + vol gate p75 | 427 | $183,973 | $9,958 | 18.47 | 56% | 1.64 |

Profit **up** +12%, drawdown **down** −44%, Return/DD **doubled**. Mechanism: the ~34 dropped trades
netted ≈ −$20.7k and caused the deepest drawdown; they were taken in high-forecast-vol regimes.

**ES 1h — no benefit:** gate 13.62 → 12.18; vol-target sizing 13.62 → 10.86. ES's edge is already
vol-agnostic (S&P calmer than Nasdaq); nothing to gain from a vol overlay here.

**Binary gate >> continuous vol-target sizing.** Sizing lifts NQ profit ($210k) but also DD ($19.2k)
→ Return/DD only 10.92. The power is in *removing* high-vol trades, not rescaling them.

**Robustness (NQ, causal p80, 4 chronological quarters):** gate helps in Q1 (1.2→4.0), Q3 (5.6→5.9),
Q4 (7.4→9.2) and is neutral in Q2 — never hurts. The 44 dropped trades netted −$15.6k at a 36% win
rate and were direction-balanced (22 long / 22 short) → a pure volatility effect, not a directional one.

**Cross-timeframe gate tested and rejected:** gating NQ's 1h trades with the finer 30m band peaks at
retDD 15.11 — worse than the 1h self-gate (18.78). Match the gate's horizon to the trade's horizon.

## Deployable rule (NQ) — integrated
> Skip an NQ entry when TimesFM's forecast band (q90−q10) at the prior bar is in the top ~15–25% of
> its recent history. Nearly doubles risk-adjusted return on this sample. Re-validate per regime.

Shipped as `gate_service.VolGate` (a live decision object — `.allow(rel_band)` per trade, causal) +
`deploy_gate.py` (applies it to the reference book, writes `nq_gated_book.csv` audit trail). Reproduces
$194,536 / maxDD $10,358 / Return/DD 18.78.

## Causality proof (no look-ahead)
Re-running the gate with the forecast taken at the prior bar (k−1, used), two bars prior (k−2), and —
as a cheating control — the NEXT bar (k+1, peeks at future): retDD 18.78 / 18.09 / **17.57**. The
future-peeking version is *worse*, proving the gate rides a slow-moving volatility regime, not leakage.

## Caveats
- One 16.5-month bull period, n=1. The gate rule is causal/untuned (good), but the model+strategy
  live on this one period; a different regime/year is untested (no other data available here).
- Overlay is 1h-only because the reference trade log is the 1h+4h fusion. Lower-timeframe standalone
  work is in progress (caches building), but standalone direction is not expected to beat this.
