# Report Q1 — split long/short SL/TP sweep (champion fixed, 4h-1m) → shared WINS, split does not help

**Date:** 2026-06-15. **Setup:** the deployed champion (4h decision / 1-min indicators, 8 indicators + vol gate
+ drawdown breaker) held FIXED; only the **long-side** and **short-side** SL/TP scale varied independently
(5×5 grid of scales {0.5, 0.75, 1.0, 1.25, 1.5} applied to the shared base sl_soft 149.8 / sl_hard 167.1 /
tp 120.2). Scored via the dashboard-canonical `strategy.build_payload` (per-window gate), full 2024–2026 +
per-year. `split_sltp_sweep.py` → `results/split_sltp_sweep.csv`.

## Headline: the SYMMETRIC champion is the best cell
| long×short | full P/L | full maxDD | return/DD | n | note |
|---|---:|---:|---:|---:|---|
| **1.0 × 1.0 (shared champion)** | **$142,203** | **$14,082** | **10.10** | 214 | BEST on both P/L and ret/DD |
| 1.0 × 0.75 | $117,078 | $12,698 | 9.22 | 220 | best *asymmetric* — still worse |
| 0.5 × 0.5 | $67,041 | $8,091 | 8.29 | 252 | symmetric shrink: low DD but low P/L |
| 0.75 × 0.5 | $97,291 | $12,806 | 7.60 | 242 | |
| 0.75 × 1.0 | $116,173 | $15,348 | 7.57 | 229 | |

- **No asymmetric (long≠short) cell beats the shared champion** on return/DD or P/L. The best asymmetric
  (L1.0/S0.75) is −$25k P/L and lower ret/DD.
- **Widening the long side (L≥1.25) is actively harmful** — DD balloons to $34k–$53k (ret/DD 1.5–3.0) without a
  P/L gain, because in the 2024–26 uptrend longs already win; wider long stops just add risk.
- **Shrinking both sides (0.5/0.5)** slashes DD ($14k→$8k) but also P/L ($142k→$67k) → ret/DD 8.29 < 10.10. The
  per-year column shows the familiar effect: 2024 P/L jumps $117→$33,238 at 0.5 (the era-scaling lever from the
  cross-year study) — but that is **symmetric era-scaling, not a long/short split**, and it doesn't help full-period.

## Answer to Q1
**For separate long vs short SL/TP, simple per-side scaling does NOT improve on the symmetric champion.** Keep
shared SL/TP. The split capability is now built and golden-safe (Q3), but this coarse probe finds no edge from
asymmetry on its own.

## Caveat & the definitive test
This grid only scales each side by a common ratio (soft/hard/tp move together); it does **not** search the full
*independent* SL/TP shape per side (different soft/hard/tp geometry, jointly with gate + indicators). The
rigorous answer is the **wsh5 optimizer run with `split_sltp=True`** (search space now wired — Q3), judged OOS
on return/DD under the pre-registered adoption rule. Pinned as a task. Until then, the symmetric champion stays.

## Reproduce
`python3 study_range_regime/split_sltp_sweep.py` → `results/split_sltp_sweep.csv`.
