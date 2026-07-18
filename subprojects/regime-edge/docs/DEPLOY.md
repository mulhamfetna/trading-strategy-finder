# Deployed — EXPERIMENTAL regime size-ramp overlay (candidate)

**2026-07-18.** The one (qualified) research winner, deployed to the backtesting system **as an experimental,
off-by-default flag** — NOT a confirmed edge. See [SECOND_TEST.md](SECOND_TEST.md) (magnitude unconfirmed, n=1).

## What ships
- `apply_regime_sizing.py` — overlay on any mtf trade book. `--enable` (default OFF). When OFF, the book is
  returned **byte-identical** (verified golden-safe). When ON, each trade's P/L is scaled by a linear ramp on
  the day's causal HMM regime (0.5×→1.5×), then normalized to hold max-drawdown at the flat risk budget.
- `precompute_regime.py` → `data/nq_daily_regime.csv` — the static causal daily regime, so the overlay needs
  no hmmlearn/model at run time.
- `deploy_card.py` → `reports/figures/deploy_candidate_card.png` — the dashboard-style result screenshot.

## Verified
| state | Profit | maxDD | Ret/DD | note |
|---|--:|--:|--:|---|
| OFF (default) | $151,872 | $27,508 | 5.52 | **identical to flat — golden-safe** |
| ON (experimental) | $162,228 | $27,508 (held) | 5.90 | **+$10,356 at equal risk — CANDIDATE** |

## Honest labels (do not drop these)
- **Off by default**; enabling is opt-in and marked experimental.
- **Magnitude unconfirmed** on the n=1 (2024–26) book; the signal is real (ordering beats 96% of random,
  helps 4/5 purged folds) but the dollar uplift's 90% CI includes zero.
- **Not uniform per-layer** (helps L2 + combined, hurts L1 alone) — re-derive the ramp per layer if applied per
  layer. Deploy on the combined book.
- **Upgrade path:** a longer / bear-inclusive book (2010–23 box levels) confirms or kills the magnitude.
