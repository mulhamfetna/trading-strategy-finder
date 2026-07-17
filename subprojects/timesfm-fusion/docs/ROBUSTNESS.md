# Robustness — the TimesFM vol-gate does NOT generalize (workstream #101)

**2026-07-15, server.** Goal: break the n=1. The +$20.7k lived on one 16.5-month **bull** window
(2025-01→2026-05). We extended to **2024–2026** (adds the Aug-2024 vol spike; box levels only exist
2024+, so no true 2022 bear — see the plan decision), regenerated the fusion book with the strategy's
own gate **trained on 2024** (honest out-of-sample), ran real **TimesFM 2.5** over the 14,045-bar 1h
series (CPU, isolated venv), and stress-tested the causal p85 gate five ways. Same battery on the
canonical book for an apples-to-apples in-sample vs OOS contrast.

## Result: real in-sample, fails out-of-sample

| test | **Canonical 2025–26** (in-sample) | **Extended 2024–26** (OOS threshold) |
|---|---|---|
| gate effect (Return/DD) | 9.36 → **18.78** ✅ | 5.52 → **4.62** ❌ |
| max drawdown | $18,572 → **$10,358** (−44%) | $27,508 → **$27,508** (unchanged) |
| per-year help | (helped per-quarter, teammate) | **0/3 years** — hurts 2024, 2025 & 2026 |
| threshold p75/p80/p85/p90 | all help | all **hurt** (4.39–5.19 < 5.52 ref) |
| block-bootstrap P(gate helps) | **99%** (median Δ +4.34) | **15%** (median Δ −0.97) |
| random-veto control | beats **100%** of random vetoes | beats **42%** (= random) |

## What this means (plainly)
- On the **original** 2025–26 bull sample the effect is **genuinely special** — a bootstrap says it
  helps 99% of the time and its 34 vetoed trades beat 100% of same-size random vetoes. Our earlier
  reproduction + dumb-control were correct *for that sample*.
- **Add one more year and train the strategy honestly out-of-sample, and it collapses:** the gate
  hurts in every year, at every threshold, its trade selection is **no better than random** (42%), and
  — the mechanistic tell — the **max drawdown is identical gated vs ungated** ($27,508). On 2024–26 the
  deepest drawdown simply **isn't** a high-forecast-volatility event, so the gate has nothing to fix.
  The teammate's whole mechanism ("the worst trades were high-vol") was **specific to the 2025–26 sample**.

This is exactly the failure the prior-art pass predicted: n=1 walk-forward is the weakest evidence, the
effect was 34 tail trades, and a high-vol veto backfires when volatility isn't what's hurting the edge
(the same reason it hurt ES). Our SOP — power/robustness + dumb-control — did its job: it caught an
attractive single-regime artifact before it shipped.

## Honest confound (stated, not hidden)
The extended book changed **two** things at once: (a) added 2024, (b) retrained the fusion's own gate
threshold on 2024 → a different 539-trade book, not "the same 481 + 58 more." A fully clean test would
hold the strategy fixed and vary only the gate's evaluation window. Mitigating evidence that it's the
gate, not just the confound: the gate hurts **within each year separately** (2024, 2025, 2026), and the
random-veto null is decisive (in-sample 100% → OOS 42%). But the cleanest possible test — a true bear
regime (2022) with the real strategy — **still needs the 2010–2023 box levels backfilled** (they're a
scraped external feed we don't have pre-2024).

## Verdict: **NO-GO** for deploying the TimesFM vol-gate as an always-on L1 filter
It is a real but **regime-specific** effect, not a durable edge. Do **not** integrate it as a standing
gate (task #100 → do not proceed as designed). Salvageable directions, if pursued later:
1. **Source 2010–2023 box levels** and run the true multi-regime (bear-inclusive) test with the real
   strategy — the only way to fully settle it.
2. Reframe as a **regime-conditional** signal (only act on the band in specific, independently-detected
   states) rather than an always-on veto — but that's a new hypothesis needing its own out-of-sample proof.

## Repro
`build_2426_tree.py` (data assembly, verified byte-identical to canonical over 2025–26) →
`mtf/backtest_mtf.py` with `YEARS=(2024,2025,2026)` after `rm -rf /tmp/wsh_l1_cache` →
`forecast_2426.py` (TimesFM 2.5, isolated venv `~/Mulham/tfm-repro/.venv-tfm`) →
`robustness_2426.py` + `robustness_canonical.py`. NB: `VolGate` must be a **single instance** across
the trade series (a fresh instance per call stays in warm-up and vetoes nothing).
