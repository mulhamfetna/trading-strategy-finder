# WS-FUSION — The Full Experiment Record (running)

**Tracking #152 · started 2026-08-19 · ledger 41/41 both machines · the same discipline as
every full record: every experiment, parameter, incident and finding, in order, so nothing
survives only as a chat remark. Companion: `WS-FUSION-BRAINSTORM.md` (the FU ledger).**

---

## F-0 · The opening (2026-08-19)

Owner pipeline rule: WS-FUSION opens with deep brainstorming + a follow-up system. Delivered:
the brainstorm (TIME × STATE thesis; three families; small-n integrity constraints), the FU
ledger with its intake rule (*an idea without an FU number does not exist*), issues #153–#161,
the execution order FU-1 → FU-9 → FU-2/3 → FU-7 → FU-5/6. The owner **approved the plan,
paused it**, flagged FU-11 (#162), ordered the project-wide progress record (delivered:
`PROGRESS-RECORD.md`, pinned #163, labels/milestones/board), then **unpaused** ("proceed with
the newsxindicators").

## F-1 · Experiment FU-1 (#153) — the event-window interaction audit ✅

**Pre-registration** (`FU1-PREREGISTRATION.md`, definitions frozen pre-run): NQ champion slots
on the six golden TFs; Tier-1 calendar minutes ≥2016 (1,222 after minute-dedupe); window
[rel−5 m, rel+15 m] (= 1.013 % of session time); five metrics; bootstrap seed 0. Era-0 prior
art folded in: FAV2/B1 had measured 08:30-only spanning trades (0.3–1.1 % of the book,
give-up zero-mean/high-variance).

**Incident F-I1**: the first pass returned stop-out density = None — my stop-reason set didn't
match `fast_engine.REASON_NAME` ("STOP_LOSS_HARD"/"STOP_LOSS_SOFT"). Fixed, re-run.

**Results** (per TF: trades ≥2016 · entries in-window (density ratio) · in/out entry P&L ·
stop-outs in-window ratio · spanning give-up):

| TF | n | entries in-win | P&L in / out ($/trade) | stop ratio | give-up (p) |
|---|---|---|---|---|---|
| 4h | 445 | 38 (**8.43×**) | +117 / +169 | 3.52× | +$328 (0.26) |
| 2h | 507 | 22 (**4.28×**) | −43 / +124 | **5.78×** | +$272 (0.21) |
| 1h | 913 | 39 (**4.22×**) | −120 / +28 | 3.58× | +$183 (0.45) |
| 15m | 1,993 | 44 (2.18×) | −33 / +14 | 2.23× | −$88 (0.55) |
| 5m | 1,416 | 10 (0.70×) | −57 / −8 | 2.07× | −$132 (0.35) |
| 2m | 4,187 | 72 (1.70×) | +1 / −0 | 2.19× | −$163 (0.25) |

**Incident F-I2 → the decomposition (the dumb control earning its keep)**: the claim's V3
falsifier shifted the whole calendar +3 days expecting the densities to collapse; the 1h ratio
only fell 4.22× → 2.16×, because the shifted calendar keeps the CLOCK TIMES. So the total
density decomposes: **2.16× time-of-day seasonality floor × ≈1.95× release-SPECIFIC pull**.
The claim was rewritten to carry the decomposition before publication.

**Findings** (claim `FU1-EVENT-WINDOW-AUDIT`, checks: re-derive from per-trade CSV /
six-frame replication / shifted-calendar):
1. The book **concentrates into news windows** — entries up to 8.4×, and stop-outs elevated
   **on all six frames** (2.1–5.8×): the "94 % of stop-outs are 1-second sweeps" mechanism
   visibly lives at release minutes.
2. In-window entry P&L is worse in point estimate on 5/6 frames but **every per-TF CI includes
   zero** — directional only. The money question is a counterfactual → **FU-2's veto replay,
   now armed with its motivation numbers.**
3. The spanning give-up is insignificant everywhere — era-0's B1 conclusion generalizes to the
   full Tier-1 calendar: closing-before-news is a variance play, not a P&L play.
4. Blind spots stood: NQ-only (Phase 1); an audit sees no counterfactuals.

## F-2 · FU-11 (#162) stage 1 — the archaeology, and the premise correction ✅

**The old study is found**: `subprojects/meta-prophet/` — 39 working notes, June 2026, the
project's true beginning. NQ 4h bars 2025-01→2026-05 (2,119 bars); 11 forecasting models
(naive, Prophet tuned, pmdarima ARIMA, SARIMAX ±regressors, StatsForecast, Darts LSTM;
NBEATS/TFT paused by the OOM crash — audited honestly in note 30).

**Its verbatim conclusion is the OPPOSITE of the owner's recollection**
(`18_executive_report_forecastability.md`, F1/F2 syntheses):
> *"price direction is unforecastable, but volatility is."*

- Direction: all 11 models LOST to the naive no-change baseline (best −0.22 %); returns
  ACF lag-1 = 0.068 (~0.5 % explained); "direction is ~99 % random"; exogenous regressors
  made it worse; the 14 engineered features carried no direction signal.
- Size: range ACF 0.56; **HAR beat naive +16.3 % on next-bar range (F1); HAR-RV the same on
  realized volatility with a cleaner target (F2: RMSE 61 vs 102 pts, corr 0.41, QLIKE 0.49)**
  — the project's first positive lift over naive anywhere.

**The corrected record**: both eras independently converged on the same law — SIZE
forecastable, DIRECTION not. Direction is now dead by three independent routes (meta-prophet's
model battery; WS-NEWS2's 643 surprise pairs; era-0 fundamentals). **There is no direction
engine to fuse** — the remembered "direction × size" breakthrough has no direction ingredient.

**The reformulation posted to the owner**: fuse the **two size engines** — HAR-RV (tape
memory) × the M2 news power model (calendar, night-before, ρ≈0.5) — different information,
mechanism-sound, feeding FU-3/FU-7/stop distances. **The owner agreed, and injected a step
first: the full system layer analysis (→ FU-12), because "we have way more volatility layers
than one — the Google one, Chronos-2, and others."**

## F-3 · FU-12 — the full system layer analysis (owner-injected, 2026-08-19) ✅

Delivered as **`docs/SYSTEM-LAYERS-ANALYSIS.md`** — every layer of the whole system (job /
income / outcome / responsibilities / status), with the volatility inventory as the featured
section. **Its headline discovery, found while tracing the gate wiring**: the deployed box
vol-gate is not a naive percentile on raw vol — **`data.load_inputs` returns
`vf = vol_forecast(...)` = `har_forecast(compute_rv_pts(...))` (`volatility.py`) — the
meta-prophet HAR-RV forecast IS already the live entry gate** on every champion. The
"proven-but-never-integrated" framing of F-2 was wrong; the correction re-frames FU-11:
not "integrate HAR-RV" but **upgrade the vol engine that already drives the gate with the
calendar information it is blind to**. Full inventory and the corrected FU-11 context: see
the analysis document.
