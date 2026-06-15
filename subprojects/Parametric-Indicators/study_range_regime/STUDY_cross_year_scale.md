# Study — Cross-year SL/TP scale: the 2024 ÷2 finding, the harness discrepancy, and q1/q2

**Date:** 2026-06-15 · Prompted by the user's dashboard observation: the champion run as-is on **2024** loses;
with **SL/TP ÷2** (74.9/83.55/60.1) it makes **+$33,238 / $13,211 DD / 148 trades / 65.5% win**. Goal: link
SL/TP to the price-range so the strategy survives market change across years.

## 0. The result-discrepancy, resolved
My earlier engine run gave $25,786 / $17,022 / **187 trades** for "2024 ÷2" — the user's dashboard gives
$33,238 / $13,211 / **148 trades**. **Root cause: the volatility-gate threshold window.**
- **Dashboard** = `build_payload(window="2024")`: the gate percentile (86.9) is taken over the **isolated 2024**
  data → threshold **99** HAR-RV pts.
- **My study harness** (`regime_eval._eval` → `load_bundle` 2024–26 + `freeze_once`): the percentile is taken
  over the **whole 2024–26 series** (which includes 2025–26 vol spikes to 300+) → a looser threshold → **187**
  trades, including high-vol 2024 entries the dashboard correctly skips.
- **Verified:** `build_payload(window="2024", 74.9/83.55/60.1)` reproduces the dashboard **exactly**
  ($33,238 / $13,211 / 148 / 65.5% / gate 99). The dashboard path is canonical; the regime-study harness
  (S3/multi-fold) ran on the looser-gate basis and its absolute numbers are NOT dashboard-aligned.

## 1. Per-year OPTIMAL SL/TP scale (dashboard path, build_payload)
| year | best scale (by ret/DD) | P/L @best | DD @best | @1.0× (as-is) |
|------|:---:|---:|---:|---|
| 2024 | **0.5×** | $33,238 | $13,211 | ≈$117 / DD $31,215 (barely viable) |
| 2025 | **1.0×** | $113,304 | $10,505 | $113,304 |
| 2026 | **0.75×** | $23,227 | $7,820 | $28,899 / DD $14,082 |

The scale that works **moves across years** — 2024 needs half, 2025 needs full, 2026 needs ~¾. The era-gap is
huge: fixed-1.0 all-years = **$142.3k / maxDD $31.2k**; per-year-optimal = **$169.8k / maxDD $13.2k**.

## 2. q1 — does a causal VOL/RANGE scale auto-recover that optimum? → **NO (right for 2024, WRONG for 2026)**
Per-year volatility/range level (each from its own bundle) and the scale it *implies* (driver_y ÷ driver_2025):
| year | mean vf | mean ATR(14) | **vol-implied scale** | **actual optimum** | match? |
|------|---:|---:|:---:|:---:|:---:|
| 2024 | 70.0 | 110.2 | 0.71–0.72 | 0.5 | direction ✓, **under-shrinks** |
| 2025 | 97.5 | 154.6 | 1.00 | 1.0 | ✓ (reference) |
| 2026 | 120.8 | 185.8 | **1.20–1.24** | **0.75** | ✗ **opposite direction** |

**The optimal scale is NOT a monotonic function of volatility/range.** 2026 had the *highest* vol/range yet
wanted the SL/TP *narrower* — vol-scaling would have *widened* them. So the simple "scale SL/TP with the price
range" rule is **not a universal law**; it captures 2024 but inverts on 2026.

## 3. q2 — does applying the vol/range scale beat fixed cross-year? → **barely on P/L, NOT on risk, not robust**
Apply scale = ATR_y/ATR_2025 (2024×0.71, 2025×1.0, 2026×1.20) each year vs fixed-1.0:
| | 2024 | 2025 | 2026 | TOTAL P/L | max-DD |
|---|---|---|---|---:|---:|
| FIXED 1.0× | $117 | $113,304 | $28,899 | **$142,320** | $31,215 |
| **ATR-scaled (q2 rule)** | $18,124 | $113,304 | $14,790 | **$146,218** | $31,051 |
| OPT (oracle per-year) | $33,238 | $113,304 | $23,227 | **$169,769** | **$13,211** |

The vol/ATR-scaled rule **beats fixed by only +$3.9k (+2.7%) and does NOT reduce max-DD** ($31k either way): it
rescues 2024 (+$18k) but **over-sizes 2026** (widens stops when it should tighten → P/L $28.9k→$14.8k, DD
$14k→$31k), roughly cancelling out. The big prize ($170k / $13k DD) is only reachable by the *oracle* scale —
which volatility does not predict.

## 4. Conclusion (answers + the real mechanism)
- **The 2024 finding is real and important:** SL/TP scale must adapt across eras — the gap between fixed and
  per-year-optimal is **+$27k P/L and −58% max-DD**. This is the single biggest lever found.
- **But linking the scale to volatility/price-range does NOT work** (q1 NO, q2 barely/not-robust): vol and the
  optimal scale diverge (2026), so a static range-linkage formula fixes 2024 and breaks 2026.
- **The robust mechanism is PERIODIC RE-OPTIMIZATION of the SL/TP scale on recent data** (re-fit every
  regime/era on a trailing window), NOT a fixed vol-linkage. This matches the earlier councils' "keep fixed,
  refresh by re-optimization" — now with concrete proof of *why* a vol-linked dynamic formula is insufficient.
- **The per-window vol gate already does part of the era-adaptation** (it gated out 2024's high-vol bad trades —
  the 99-vs-looser-threshold effect in §0); the remaining lever is the SL/TP scale, best handled by periodic
  re-fit on trailing ranges rather than a per-bar vol formula.

## 5. Caveats / next
3 years (2026 partial); the "optimum per year" is itself look-ahead (oracle). The actionable, causal version is
a **trailing re-fit of the SL/TP scale** (e.g. choose the scale that was best over the last N months, applied
forward) — worth a causal walk-forward test as the realistic embodiment of the user's goal, and re-anchored to
the **dashboard `build_payload` path** (not the `_eval` harness, per §0). Re-run engine numbers via build_payload.
