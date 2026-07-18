# Chronos-2 vol-gate — NO-GO (identical failure to TimesFM) + program-level conclusion

**2026-07-18, server.** Ran the full TimesFM battery on the Chronos-2 forward band (2024–26 NQ 1h, same
context 512 / horizon 24, band = `(q0.9−q0.1)/price`), with a direct A/B vs TimesFM on the same book.

## Result — Chronos-2 fails exactly like TimesFM

| test | **Chronos-2 p85** | **TimesFM p85** (A/B) |
|---|--:|--:|
| gate effect (Return/DD) | 5.52 → **4.63** | 5.52 → 4.62 |
| max drawdown | $27,508 → **$27,508** (unchanged) | unchanged |
| per-year (2024/2025/2026) | 1.15→0.88 · 7.24→6.52 · 10.76→8.50 (**all hurt**) | all hurt |
| threshold sweep p75–p90 | 3.16–4.72 (**all < 5.52**) | all ≤ 5.19 |
| block-bootstrap P(gate helps) | **18%** | 17% |
| beats random vetoes | **37%** (worse than random) | 42% |
| corr(Chronos band, TimesFM band) | **0.71** | — |

Chronos-2's richer 21-quantile *forward* band buys **nothing** here — it correlates 0.71 with TimesFM's band
(they measure the same forward volatility), hurts every year, leaves the drawdown untouched, and its trade
selection is no better than random. **NO-GO** for the veto framing.

## Covariate framing (the one remaining Chronos-2-unique angle)
Not run. Given (a) three methods now agree vol/uncertainty-conditioning doesn't help this strategy and (b) the
HMM regime is itself a vol proxy that already failed, feeding the regime as a covariate is **expected-negative**
and not worth the compute on THIS strategy. The covariate capability stays on the shelf for a *different*
(vol-hurt) strategy or for genuinely non-vol exogenous inputs.

## PROGRAM-LEVEL CONCLUSION (the important takeaway)
**Volatility / forecast-uncertainty gating does not help the box-fusion strategy — now confirmed by THREE
independent methods:** TimesFM vol-band, Chronos-2 vol-band, and HMM/Jump-Model regimes. All three reach the
same place: the strategy is **vol-seeking** (its edge lives in turbulent regimes), so any "skip the uncertain /
high-vol trades" rule removes good trades and leaves the real drawdown untouched. The answer is **robust** —
stop testing vol-veto variants.

### Actionable implication for the backlog
- **#103 TiRex, #104 Moirai-2, #105 Toto-2 as vol-VETO signals → expected-negative; do NOT spend compute on
  them for this use.** They would only re-confirm this NO-GO. (Their *covariate/multivariate* abilities could
  matter for a different framing, but not the veto.)
- **Redirect effort to genuinely different information**, where the prior-art actually supports an edge:
  1. **Non-vol exogenous signals** — breadth / positioning (COT) / macro / concentration (the data-source
     backlog) carry information *orthogonal* to price-vol.
  2. **A vol-HURT strategy** — apply regime/vol gating to a mean-reversion system or the L2 layer, where a
     high-vol veto has a real mechanism.
  3. **Sizing, not veto** — the strategy earns in high vol, so *upsize* there / downsize in calm (needs a
     longer book + OOS selection to avoid the overfit already shown).

## Verdict: **NO-GO** (veto). Value delivered: closed the "best successor" question decisively and produced a
robust, three-method program conclusion that saves the remaining model experiments from re-proving it.
