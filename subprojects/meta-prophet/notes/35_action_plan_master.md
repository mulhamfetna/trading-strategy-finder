---
name: action-plan-master
description: Master action plan turning the Response.md braindump into sequenced workstreams (A–G) — transformer-on-1min, OHLC targets, advanced GARCH, dedicated flip models, Kalman-filter family, instruments, and a combination tournament with per-combo dashboard clones. Includes frontmatter, baby-explanation sections, ecosystem fit, guardrails, a checklist, and open questions.
type: plan
---

# Master Action Plan — next research wave

> ## 📌 PINNED — current status (2026-06-03)
> - **Current workstream: WS-G** — maximise P/L under a hard max-drawdown cap (single-contract
>   cloned engine). Tournament + drawdown-constrained optimisation + per-combo dashboards: **DONE**.
> - **Current WINNER (CORRECTED — see `notes/46`):** SL 30/40 · TP 60 · vol-gate @ 60th pct ·
>   drawdown breaker **$2,000 / 20** (global high-water mark). → **+$7,735 P/L, true maxDD $3,670
>   (<$5k), both years +.**
>   ⚠️ The earlier **+$24,720 / $4,845** (tag `v4.2`, breaker $2,500/30) was **inflated by a breaker
>   bug** (it reset its peak on unlock → drawdown wasn't actually capped). Fixed to global-HWM;
>   re-tuned. Reports `notes/44`/`45` are SUPERSEDED by `notes/46`.
> - **Caveat (stronger now):** the corrected profitable+capped tuning is **overfit (n=1)** — the
>   feasible surface is chaotic. Out-of-sample validation (WS-F) is essential before any trust.
> - **Workstream status:** A ✅ · C ✅ · G ✅ | pending: B (OHLC), D (flip committee), E (Kalman),
>   F (instruments — *blocks out-of-sample validation*), #175 (per-bar flip).
> - **Deliverables for the winner:** report [[winning-system-full-report]] (`notes/44`) ·
>   playbook (`notes/45`) · engine-edits report (`notes/42`) · **standalone self-contained
>   app `subprojects/wsg-strategy/`** (own backend+frontend+engine+docs; reproduces the winner
>   exactly with zero repo imports; the superseded `dashboard_winner/` + `winner_dashboard/`
>   clones were removed in favour of it). Progress log: `subprojects/wsg-strategy/docs/`.

This converts the raw `Response.md` ideas into a concrete, sequenced plan that fits the
**existing meta-prophet ecosystem** (numbered `scripts/`, `notes/`, the GPU `server/`
toolkit, and the **cloned** backtest engine + dashboards). Everything new stays inside
`subprojects/meta-prophet/`. Each workstream has a *baby explanation*, the concrete model
list (incl. harvested options), how it slots into the ecosystem, and a checklist.

> **Reality anchor (measured, not assumed):**
> - Next-bar **price/direction is unpredictable** at 4h *and* 1-min (return ACF ≈ 0.07 at 4h,
>   ≈ −0.006 at 1-min — both noise). Eleven price models all lost to the naive guess.
> - **Volatility IS predictable** and gets *stronger* at high frequency: |1-min return|
>   ACF ≈ 0.38, 1-min range ACF ≈ 0.73. This is where the data, the GPU, and the fancy
>   models should be pointed.
> The plan is built around that fact: chase volatility & regime/flip signals, and use the
> price models mainly to *confirm* (not re-litigate) the "price is noise" result.

---

## 0. Guardrails (do not violate)
- **Never touch the main engine, dashboard, `src/`, `frontend/`, `docs/`.** Every backtest
  / dashboard is a **clone** (sibling), as established (`engine_clone/`, clone dashboard).
- One sibling **per combination** of {model(s) × indicator(s) × strategy}. Main stays pristine.
- Only **training** runs on the server; data, results, analysis, docs stay local
  (`server/docs/MASTER.md`).
- Verified-vs-illustrative honesty: label any P/L from a single regime (n=1) as illustrative.
- CSVs are git-ignored (regenerable); commit scripts + notes + docs only.

---

## Workstream A — Advanced volatility models (GARCH family)
**Baby explanation:** We can't predict *which way* price moves, but we *can* predict *how
wild* it will be (big day vs calm day). "Volatility clusters" — storms follow storms, calm
follows calm. GARCH-type models are the classic weather-forecasters for market storms. We
already showed a simple one (HAR) beats naive by ~16%. Now we try the stronger cousins.

**Models (the 5 you named + harvested):**
- Named: **GJR-GARCH** (storms from *drops* hit harder than rallies), **EGARCH** (models the
  log so it can't go negative + asymmetry), **IGARCH** (shocks never fully fade — long memory),
  **GARCH-M** (risk feeds back into return), **DCC-GARCH** (how *two+ instruments'* vols move
  together — needs multiple instruments → ties to Workstream F).
- Harvested additions worth including: **TGARCH/APARCH** (flexible asymmetry), **FIGARCH**
  (fractional long memory), **realized-GARCH / HEAVY** (uses intraday realized vol — pairs
  with our 1-min data), and **HAR-RV extensions** (HAR + jumps/leverage: HAR-J, HAR-RS).
- Library: `arch` (Kevin Sheppard) for GARCH-family; our existing HAR code for the HAR side.
**Targets:** 4h realized vol AND 1-min-derived realized vol (the high-freq signal is stronger).
**Ecosystem fit:** new `scripts/2x_garch_*.py` following the Forecaster/walk-forward harness;
scored with QLIKE + RMSE-of-vol + lift-vs-naive-vol; report in `notes/`. CPU (no GPU needed).

## Workstream B — OHLC / multi-target (not just close)
**Baby explanation:** So far we only guessed the **Close**. But each candle has Open, High,
Low, Close. At a bar's *open* we already know the Open; the useful things to guess are the
**High, Low, and Close** for that bar (and the **range** = High − Low). Predicting High/Low
is really a volatility question (how far it stretches), which is the predictable part.
**Plan:** extend the harness target from `close` to `{high, low, close, range}` given `open`;
reuse the same models. Expect: range/high/low carry signal (volatility), close-direction
does not. This is the honest way to "use OHLC" the user asked about.
**Ecosystem fit:** add multi-output target support in `common/`; keep walk-forward causal
(only Open of the target bar is known). New `scripts/2x_ohlc_*.py` + report.

## Workstream C — High-frequency deep learning (the "more data" test)
**Baby explanation:** The transformer flopped partly because ~1,500 4h candles is tiny for a
huge model. 1-min data gives **~487,000** candles — plenty. BUT: more data only helps if
there's a pattern to learn. We measured: **1-min direction is still noise** (ACF −0.006), so
the transformer still won't beat naive on *price*. **1-min volatility, though, is very
predictable** (range ACF 0.73) — so we point the big models at **volatility**, where the
extra data genuinely unlocks them.
**Plan:**
- C1 (cheap, settles the debate): transformer/NBEATS/LSTM on 1-min **return** → expected to
  still lose to naive; documents the "data wasn't the problem, signal was" conclusion.
- C2 (the real bet): same models on **1-min realized-vol / range** → this is where depth +
  data can win. Compare against GARCH (Workstream A).
- Data scope (per your note): **1 year of 1-min, current data only** (we have 2025-01→2026-05
  of 1-min already); older years out of scope.
**Ecosystem fit:** GPU server (`server/`), batched like the Darts run; pull results local.

## Workstream D — Dedicated flip / regime models
**Baby explanation:** Our strategy won in 2025, lost in 2026; flipping in 2026 would have
won. Instead of one rule, train **several specialist detectors**, each watching the data from
a different angle, then **vote**. "When to flip" is a *change-point* problem (has the regime
turned?).
**Models (CUSUM + advanced siblings + ML):**
- Change-point detectors: **CUSUM** (have it), **Page-Hinkley**, **Bayesian Online
  Change-Point Detection (BOCPD)**, **ADWIN**, **drift detectors** (DDM/EDDM), **binary
  segmentation / PELT / kernel CPD** (`ruptures` lib).
- Learned flip-classifiers: small models predicting "normal vs flipped is better next window"
  from features (recent edge P/L, volatility regime, etc.).
- **Ensemble/committee:** combine detectors + classifier by majority/weighted vote — the
  "collection of models, different angles, combine to decide" you described.
**Ecosystem fit:** extends `scripts/19_reverse_indicator_search.py`; scored on the engine
symmetry (flipped P/L ≡ −normal P/L). Honesty: still **n=1 regime** until more data/instruments.

## Workstream E — Kalman filter family
**Baby explanation:** A Kalman filter is a smart *de-noiser/tracker*: it keeps a belief about
the hidden "true" state (e.g. de-noised price/trend/volatility), predicts the next step, then
corrects when the new bar arrives. Great for separating signal from noise.
**Variants (your list):** **KF → EKF → IEKF → UKF → CKF** (handling more nonlinearity),
**Particle Filter / SMC** (arbitrary distributions), **EnKF** (ensemble), **Adaptive KF**
(self-tuning noise), **Error-State KF**, **Invariant EKF**.
**Two uses (both, as you said):**
- **Standalone**: track de-noised level/trend/vol and forecast.
- **Embedded**: a pre-filter that feeds cleaner inputs into A/C/D models (denoise → then model).
**Ecosystem fit:** `scripts/3x_kalman_*.py`; libs `pykalman`, `filterpy`, `simdkalman`. Mostly
CPU. Expectation: most value as a **volatility/trend de-noiser feeding other models**, not as a
price oracle.

## Workstream F — Instruments / data acquisition
**Baby explanation:** Everything is one instrument (NQ) with one regime change → we can't
*validate* flip/regime models (n=1). More instruments = more regime changes = real validation,
and unlocks **DCC-GARCH** (cross-instrument vol). This is likely the single biggest unlock.
**What I need from you (report of requirements):**
- **Which instruments?** (e.g. ES, YM, RTY, CL, GC, 6E, BTC, ...). Correlated index futures
  (ES/YM/RTY) are best for cross-vol; diverse assets best for regime diversity.
- **A data source** in the same shape as the current NinjaTrader export
  (`datetime,open,high,low,close,volume`): NinjaTrader history export, a broker/data API
  (Databento, Polygon, IQFeed, Norgate, Interactive Brokers), or vendor CSVs.
- **Same boxes?** The signal logic needs the weekly/monthly box levels per instrument — do
  those exist for other instruments, or is this NQ-box-specific?
**Plan:** once a source is known, mirror the `Full_Canldes_Data` layout per instrument and the
whole pipeline (signals → models → backtest clone) generalizes (it's already timeframe/instrument-
agnostic — proven). *Optional now:* a deep-research harvest of data sources + advanced model
options (I can launch the deep-research workflow if you want).

## Workstream G — Combination tournament + per-combo dashboard clones
**Baby explanation:** Once we have several models/indicators/strategies, try **combinations**
(e.g. vol-model + flip-detector + gate) and backtest each. **Never touch the main dashboard** —
**clone** it once per combination so each combo gets its own sibling view.
**Plan (bounded, not literally exhaustive — see open question):**
- Define dimensions: {volatility model} × {flip detector} × {strategy/gate} × {single contract}.
- A small **matrix runner** (extends `17_backtest_matrix.py` on the cloned engine) runs each
  combo on the verified single-contract clone, emits P/L + risk metrics.
- A **dashboard factory**: clone the standalone HTML dashboard per selected combo into
  `engine_clone/dashboards/<combo_id>/` (data.js embedded), main untouched.
- Guard against combinatorial blow-up: phase it (shortlist by backtest, then build dashboards
  only for the top-K). Log anything dropped (no silent truncation).

---

## Sequencing (proposed; confirm in open questions)
1. **B + A** first (OHLC targets + GARCH family) — pure CPU, fast, builds on the proven
   volatility result. Quick wins.
2. **C** (high-freq DL on volatility) — uses the GPU server we just validated.
3. **D** (flip/regime committee) — extends existing reverse work.
4. **E** (Kalman) — as de-noisers feeding A/C/D.
5. **F** (instruments) — in parallel, gated on your data source; unlocks validation + DCC.
6. **G** (combination tournament + dashboards) — last, once components exist.

---

## Master checklist
- [ ] A1 GARCH family (GJR/EGARCH/IGARCH/GARCH-M/APARCH/TGARCH/FIGARCH/realized-GARCH) on 4h + 1-min RV
- [ ] A2 DCC-GARCH (blocked on Workstream F — needs ≥2 instruments)
- [ ] B1 Multi-target harness: predict {high, low, close, range} given open
- [ ] B2 Re-run model set on OHLC targets + report
- [ ] C1 DL on 1-min **return** (settle the "more data" hypothesis — expect: still loses)
- [ ] C2 DL (transformer/NBEATS/LSTM) on 1-min **realized-vol/range** (the real bet)
- [ ] D1 Advanced change-point detectors (Page-Hinkley, BOCPD, ADWIN, ruptures-PELT)
- [ ] D2 Learned flip-classifier(s) + ensemble vote
- [ ] E1 Kalman/UKF/Particle standalone trackers (price + vol)
- [ ] E2 Kalman as embedded de-noiser feeding A/C/D
- [ ] F1 Instruments requirements report + obtain data source (your input needed)
- [ ] F2 Generalize pipeline to new instrument(s); validate flip models across regimes
- [ ] G1 Bounded combination matrix on the cloned single-contract engine
- [ ] G2 Per-combo dashboard clones (sibling each; main untouched)
- [ ] Optional: deep-research harvest (advanced vol/flip/Kalman options + data vendors)

---

## Decisions locked (2026-06-02)
- **First milestone: Workstream C** (1-min deep learning on GPU).
- **1-min target: price-return FIRST** (directly test the "more data fixes the transformer"
  hypothesis; expectation per measured ACF ≈ −0.006: it still won't beat naive — we prove it).
- **Instruments: deep-research harvest** of data vendors + advanced vol/flip/Kalman options
  (launched as a parallel research task).
- **Combination tournament: bounded & phased.**

## Open questions (answered above; kept for history)
1. **Order/first milestone** — start with quick CPU wins (OHLC + GARCH), or jump to the GPU
   1-min volatility deep-learning, or the flip-committee?
2. **1-min DL target** — run the price-return test (to *prove* data isn't the fix) too, or go
   straight to volatility (where data helps)?
3. **Instruments** — which symbols, and do you have a data source/account to pull them from
   (and do non-NQ instruments have box levels)?
4. **Combination tournament breadth** — bounded/phased (recommended) vs as-exhaustive-as-feasible?

---

## One-paragraph summary (baby)
We're opening a new research wave. The honest map: *price* is unpredictable (proven again at
1-minute), so we stop chasing it and point everything — more data, the GPU, fancy models — at
the things that *are* predictable: **how big moves are (volatility)** and **when the strategy
should flip sides (regime)**. We'll add stronger storm-forecasters (GARCH family), predict the
whole candle (High/Low/Close, not just Close), let the transformer feast on 487k one-minute
bars *for volatility*, build a committee of flip-detectors (CUSUM + smarter siblings), use
Kalman filters to clean the data, get more instruments so we can finally validate, and finally
backtest every sensible combination — each in its **own cloned dashboard, never touching the
main one**. First we need your answers to the four questions above.
