# TimesFM → L1 fusion — consolidated experiments log

**Workstream:** `research-timesfm-fusion` (branch off dev). **Opened 2026-07-15.**
**Question:** can Google **TimesFM** add durable value to our L1 box-fusion strategy — specifically as a
**volatility/regime veto gate** (skip trades when the model's forecast is very uncertain), not as a
direction predictor? Seeded by a teammate's `TFM.zip` claiming +$20.7k / −44% drawdown on NQ.

This is the master narrative; each stage has a detailed doc (linked). **Verdict: NO-GO** (regime-specific).

---

## Timeline of experiments

| # | Stage | What we did | Result | Doc |
|---|-------|-------------|--------|-----|
| 1 | **Fact-check** | Read the teammate's `FINDINGS.md`; reconciled against the brief | Brief said **+$50k**; directory documents **+$20.7k**. Direction-prediction FAILS; the real claim is a vol veto-gate. ES hurts. | [WORKSTREAM.md](../WORKSTREAM.md) |
| 2 | **Prior-art** (deep research) | 5-angle web sweep, 25 sourced claims | TimesFM 2.5 = Apache-2.0, quantile head = the band. TSFMs weak at direction ✅. Band-as-vol-gate has **no published precedent**. High-vol veto **backfires** on vol-seeking edges. n=1 walk-forward = weakest evidence. | [PRIOR_ART.md](PRIOR_ART.md) |
| 3 | **Reproduce** | Re-ran the gate on the vendored audit trail (server) | **To the dollar**: $173,789→$194,536, DD $18,572→$10,358, Return/DD 9.36→18.78; causal mask 481/481 exact. Effect = 34 tail trades netting −$20,747. | [REPRO.md](REPRO.md) |
| 4 | **Dumb control** | Gated the same book with ATR / realized-vol / rolling-range (12 variants, kept best) | TimesFM **18.78** vs best cheap proxy **13.26** — the model genuinely beats a plain vol number *on this sample*. Not a lagged ATR (corr 0.49–0.80). | [DUMB_CONTROL.md](DUMB_CONTROL.md) |
| 5 | **Robustness** (break n=1) | Extended to **2024–26** (real TimesFM over 14,045 bars, threshold trained OOS on 2024); 5-way battery + same battery on canonical book | **FAILS OOS**: gate hurts **0/3 years**, every threshold; bootstrap P(helps) **15%**; beats only **42%** of random vetoes (=random); **max DD unchanged**. Canonical stayed special (99% / 100%). | [ROBUSTNESS.md](ROBUSTNESS.md) |

## The core discovery
The +$20.7k is **real but regime-specific**. On the 2025–26 bull window the strategy's worst drawdown
*happened* to coincide with high-forecast-volatility trades, so vetoing them helped enormously — and did
so more cleverly than any cheap proxy. **Extend by one year and that coincidence vanishes**: the deepest
drawdown is no longer a high-vol event (gated DD == ungated DD), so the gate only removes good trades. The
mechanism was a property of the sample, not a durable edge. This is precisely the failure mode the
prior-art pass flagged (n=1, tail-driven, high-vol-veto backfire — same reason it hurt ES).

## Discoveries banked (reusable beyond this workstream)
1. **TSFM direction ≈ coin-flip on index futures** — do not use any foundation model for entry direction.
2. **A single-window win must survive: dumb-control + multi-regime + random-veto null.** Our SOP caught this.
3. **The "gated DD == ungated DD" check** is a fast tell that a vol filter isn't touching the real risk.
4. **VolGate must be a single stateful instance** across the trade series (a fresh instance per call sits
   in warm-up forever and vetoes nothing) — cost me one wrong intermediate number; caught by verifying.
5. **L1 cache (`/tmp/wsh_l1_cache`) is keyed on params, not data** — clear it after any data/period change
   or you silently re-read stale results (this masked the 2024 extension until cleared).
6. **Data assembly must be proven** — candles + box verified byte-identical to canonical (diff 0.0) before
   trusting the extension.

## Environment / repro pointers (server `amd-trading`)
- Scratch: `~/Mulham/tfm-repro/` (vendored harness, `.npz` caches, `data2426/` tree, `mtf/` working copy).
- Isolated venv `~/Mulham/tfm-repro/.venv-tfm`: `timesfm` 2.0.2 (ships the 2.5 torch model) + CPU torch + pandas.
- Reproduce: see each doc's "Repro" section + [ROBUSTNESS.md](ROBUSTNESS.md).

## Open follow-ups
- **Fully settle it:** source **2010–2023 box levels** (scraped external feed, absent pre-2024) → true
  bear-inclusive test with the real strategy.
- **Successor models:** test recent TSFMs as vol/uncertainty signals → [BACKLOG_TSFM_ALTERNATIVES.md](BACKLOG_TSFM_ALTERNATIVES.md).
- **Exogenous data:** the data-platform sweep → [BACKLOG_DATA_SOURCES.md](BACKLOG_DATA_SOURCES.md) (feeds the
  parked exogenous-signals-fusion workstream).
