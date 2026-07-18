# Experiment 3 — Gate a vol-HURT strategy

**2026-07-18, server.** **Verdict: INCONCLUSIVE** — the quick test bed has no edge to protect; a proper test
needs the real L2 layer.

## Hypothesis
The high-vol veto HURT our breakout (vol-seeking). On a strategy that volatility *hurts* (mean-reversion —
fading a strong move gets run over), the SAME causal high-vol veto should HELP. If so, the earlier NO-GOs were
strategy-specific, not a flaw in the vol signal.

## What we built + result
A self-contained causal NQ 1h mean-reversion baseline (fade 2σ deviations from a 20-bar mean, exit on
reversion or a 24-bar max hold), 2015–2026, then the same causal p85 VolGate on each entry's realized vol.

| | P/L | maxDD | Return/DD | win |
|---|--:|--:|--:|--:|
| ungated mean-reversion | **−$230,580** | $255,245 | **−0.90** | 60% |
| + high-vol veto p85 | −$235,110 | $272,695 | −0.86 | — |

The mean-reversion baseline **loses money** (60% win rate but the losers dwarf the winners — "pennies in front
of a steamroller"). The vol veto moves Ret/DD −0.90 → −0.86 (both negative = meaningless) and is mixed
per-year (helps 5, hurts 6). **No edge to protect → the hypothesis is untestable on this proxy.**

## What this DOES tell us
A naive fade is a **persistent loser on NQ** (2015–26) — NQ rewards momentum/breakout and punishes
mean-reversion. This is *consistent* with the whole program's theme (the breakout is vol-seeking; NQ trends),
but it means a simple NQ mean-reversion cannot be the vol-hurt test bed.

## Proper next step (out of this quick pass)
Test the vol veto on a **profitable vol-hurt book** — the real **L2 layer** trade log (it manages L1's dropped
signals and may be genuinely vol-hurt) — generated from the L2 backtester, not a toy strategy. That requires
wiring the L2 harness (scope beyond this cycle). Alternatively, a mean-reversion on a mean-reverting instrument
(e.g. a spread / a range-bound market), not trending NQ.

Script: `meanrev_experiment.py`.
