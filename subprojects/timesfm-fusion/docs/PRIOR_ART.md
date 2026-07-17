# Prior-art research — TimesFM as a volatility/regime gate (workstream #98)

**Date:** 2026-07-15. **Method:** deep-research fan-out (5 angles, ~22 search agents, 25 sourced claims).
**⚠️ Verification status:** the adversarial verify pass and the arxiv/full-text fetches **failed on a hard
weekly web limit (resets 2026-07-18 03:00)**, so no claim below was machine-verified. Each is tagged:
- **[✓ corroborated]** — I can confirm it from general knowledge; high confidence.
- **[~ snippet-only]** — comes from a search snippet whose source could NOT be fetched (esp. arxiv); treat as a
  lead to re-verify after Jul 18, not a settled fact. (The arxiv id `2606.27100` is unverified and may be wrong.)

Plain-language glossary is inline. Every "term" is spelled out.

---

## 1. What TimesFM 2.5 actually is (and can we use it)

- **[✓] Licence = Apache-2.0** (both the GitHub repo and the Hugging Face model card). Apache-2.0 permits
  commercial use, so using it for our internal/commercial trading research is legally fine.
  Sources: github.com/google-research/timesfm, huggingface.co/google/timesfm-2.5-200m-pytorch.
- **[✓] Architecture:** a *decoder-only* foundation model (same family shape as a GPT, but for numeric time
  series), **200M parameters** (smaller than v2.0's 500M), long context (the repo advertises up to ~16k history
  points; the practical config in this checkpoint is context ≈ 1024, horizon ≈ 256).
- **[✓] Where the band comes from:** TimesFM has an optional **quantile head** (~30M params) that outputs, per
  future step, the **mean plus the 10th…90th deciles** — i.e. 10 numbers describing the *distribution* of where
  price could go. The teammate's `(q90−q10)/price` "band" is exactly the 90th-decile minus 10th-decile spread,
  normalised by price. So the volatility proxy is a first-class model output, not a hack. **[✓]**
- **[✓ — important caveat] Financial data is OUT-OF-DISTRIBUTION.** The model card lists training data as
  Wikipedia pageviews, Google Trends, GiftEval, and synthetic series — **no financial/return series**, and the
  release is *"not an officially supported Google product."* So *any* financial behaviour is unsupported and
  off-label. This is a strike against trusting it as a direction engine and a reason the **band (a generic
  dispersion signal) is more plausible than the direction** (which needs financial structure it never learned).
- **[~] Training-data cutoffs** (pageviews to ~Nov 2023, Trends to end-2022) bound its knowledge — minor leakage
  relevance only, since we feed it price history at inference, not its training corpus.

## 2. Do these models fail at direction but carry useful uncertainty?

- **[~ snippet-only, arxiv unverified] TSFMs are weak at financial direction.** A benchmark on five US equities
  (TimeGPT, TimesFM-2.5, Moirai-2.0, Chronos) reportedly found only **small, sparse gains over a random-walk**
  baseline — just **two** statistically-significant accuracy wins in the whole study (Chronos/AMZN, Moirai/GOOG),
  and concluded TSFMs are **"not reliable alpha generators… low-cost priors."** This *directly supports* the
  teammate's "don't use TimesFM for direction" finding — and the fact that wins were model- and stock-specific
  echoes our **NQ-helps-but-ES-hurts** fragility. Re-verify the arxiv source after Jul 18.
- **Gap:** the search did **not** surface a paper explicitly endorsing "FM forecast band = tradeable volatility
  regime signal" or benchmarking it against GARCH/ATR/realized-vol/VIX. So **using the band as a vol gate is not
  (yet) an established, cited technique** — it's a reasonable original idea, but we can't lean on precedent for it.
  This raises the bar on our own validation. (Re-run the targeted search post-Jul-18.)

## 3. Regime/volatility gating of entries — does removing high-vol trades help?

- **[✓ direction of effect] Regime filtering can cut drawdown.** Practitioner sources report filtering trades by
  trend/volatility regime reduces drawdown and flat-spells vs. an unfiltered strategy — consistent with the
  teammate's −44% DD on NQ.
- **[✓ — THE KEY BACKFIRE CONDITION] High vol can mean high *edge*.** At least one source argues
  **trend/momentum works BETTER in high-volatility regimes** — the opposite of "veto high-vol." So a blanket
  high-vol veto is only safe when your edge is *hurt* by volatility (e.g. mean-reversion / tight-stop breakout
  systems that get stopped out in chop). **This is exactly why it can help our box-breakout NQ book but backfire
  elsewhere** — and a direct warning that it may hurt on instruments/regimes where our edge is vol-seeking. Our
  ES result (gate hurts) is the first instance of this backfire, not an anomaly.
- **[✓] Weak-evidence pattern:** the enthusiastic regime-filter blogs show results with **no out-of-sample test
  and single-account testimonials** — i.e. the field is full of n=1 claims exactly like the one we're auditing.

## 4. Look-ahead / leakage pitfalls for a quantile-band gate

- **[✓] Ordinary k-fold cross-validation is invalid for time series** (observations aren't independent; the
  future leaks into the past). The fix is **purging** (drop training points whose outcome window overlaps the
  test window) and **embargoing** (skip a buffer after each test window) — López de Prado's method.
- **[✓] Expanding-percentile thresholds are a leakage trap.** The gate compares each trade's band to the p85 of
  *history so far* — this is causal **only if** the percentile never sees the current-or-future band. The
  teammate's `VolGate.allow()` appends the reading **after** the decision, and their k−1/k−2 vs k+1 test (future
  peek is *worse*) is the right causality proof. We must preserve both properties in the L1 integration.
- **[✓] Forecast-window overlap inflates apparent skill** — overlapping horizons make sequential forecasts
  correlated, which is why the teammate warned their direction `corr` was inflated. For the *band* (a level, not
  a bet) this matters less, but our validation must not double-count overlapping windows.

## 5. Overfitting / robustness — is n=1 enough? (No.)

- **[✓] A single walk-forward split is the WEAKEST overfit check.** Sources rank **Combinatorial Purged
  Cross-Validation (CPCV)** highest (lowest Probability of Backtest Overfitting, best Deflated Sharpe), with a
  single chronological train/test split (walk-forward) the **most prone to a spuriously good result** — which is
  precisely the n=1, 16.5-month, *bull-only* window our +$20.7k rests on.
- **[✓] 70/30 OOS is vulnerable to "regime luck"** — if the test window is a bull market, a good score may just
  be luck. Recommended: **randomized OOS resampling repeated 1,000+ times**, and holding the edge across the
  **majority** of windows spanning different regimes — not one.
- **[✓] Threshold-selection overfit:** picking "top ~15%" (p85) on one sample inflates artifact risk. The p85/p75
  robustness the teammate showed is reassuring but still in-sample to the same period.

## 6. Why NQ but not ES (the asymmetry)

- **[~] NQ is structurally ~1.3–1.5× more volatile than ES** (Nasdaq-100 tech concentration — top ~7 names ≈ 50%
  of the index). More volatility dispersion = more for a vol gate to *discriminate*: NQ has genuinely
  high-vol-regime trades worth dropping, whereas ES is calmer and its edge is already "vol-agnostic," so the gate
  only removes good trades. This is a *coherent* mechanism, not a fluke — but §3's backfire warning means it must
  be **re-derived per instrument**, never assumed.

---

## Go / No-Go

**GO — to *reproduce and rigorously re-validate*, NOT to deploy.** The prior art *supports the shape* of the
finding (TSFMs weak at direction ✓; the band is a real model output ✓; regime gating cuts DD ✓; Apache-2.0 ✓)
but simultaneously **flags the exact way it could be a mirage**: (a) the band-as-vol-gate is not an established,
benchmarked technique, (b) high-vol-veto has a known backfire (vol-seeking edges), already visible in ES, and
(c) a single bull-market walk-forward is the weakest possible evidence. The +$20.7k is a *lead worth chasing*,
not a result to trust.

## Validation protocol to run on OUR data (before believing +$20.7k)

1. **Reproduce** the exact NQ p85 book from the vendored `.npz` caches ($194,536 / DD $10,358 / 18.78) and
   re-run the k−1/k−2/k+1 causality control. *(#99 — no web, server compute.)*
2. **Dumb-control** (our SOP): compare the TimesFM gate against **cheap vol proxies** — realized volatility, ATR,
   and a plain rolling-range percentile gate. If ATR-p85 captures most of the −44% DD, we don't need a 200M model.
3. **Regime split, not one window:** re-test across multiple sub-periods / CPCV folds and (when we have it) a
   **non-bull** sample. Require the edge to hold in the *majority* of folds, not one.
4. **Per-instrument re-derivation:** treat NQ-helps / ES-hurts as a hypothesis; measure the gate on every
   instrument separately (metals/energy included) — never port the NQ threshold blindly.
5. **Power / noise check:** is +$20.7k large vs the per-trade P&L swing, or is it a handful of tail trades? (The
   teammate says ~34 trades netted −$20.7k — so the *entire* effect is a small tail; that concentration is itself
   a fragility to quantify.)

## To finish this research pass properly
Re-run the adversarial verification + arxiv/full-text fetch **after 2026-07-18 03:00** (web limit reset):
`Workflow({scriptPath: "…/deep-research-wf_1d15f50b-642.js", resumeFromRunId: "wf_1d15f50b-642"})` replays the
cached search agents for free and only re-runs the failed verify/fetch calls.
