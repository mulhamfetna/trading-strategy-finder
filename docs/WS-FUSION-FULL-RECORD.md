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

## F-4 · FU-13 (#165) — the Exp2 ramp through the deployment battery: NOT-DEPLOYED ✅(verdict)

Pre-registration `FU13-FU14-PREREGISTRATION.md` fixed R/X/M PASS lines and the deploy rule
before any run. Results (`subprojects/regime-edge/fu13_result.json`, ledger claim
`FU13-SIZING-RAMP-NOT-DEPLOYED`):

- **R (reproduce)** — EXACT: the original NQ book (found preserved at
  `~/Mulham/tfm-repro/nq_2426_mtf_log.csv`) gives flat $151,872 / ramp $162,228 (+$10,356
  equal-risk) — the deploy card to the dollar; overlay OFF is byte-identical.
- **X (independent book)** — FAIL: the ES 1h+4h combined book was generated fresh with the
  CURRENT machinery (`shareable/mtf_layer_fusion_backtester/backtest_mtf.py`, ES champions:
  $57,315 / 263 trades / DD $6,060), the ES causal regime built by the same HMM methodology
  (16-year ES_1h, TRAIN_END 2024-01-01). The SAME a-priori ramp: **−$18,632** at equal risk
  (Ret/DD 9.46 → 6.38). Deeper: on ES even RANDOM regime→size maps hurt (median −$12,282;
  the ramp ranks P27 among 1,000) — the ES book does not reward vol-mapped size dispersion
  at all, echoing the TimesFM-era "ES is vol-agnostic" asymmetry from the GATING side.
- **M (pooled)** — FAIL: pooled uplift −$8,276, 90% CI [−$25,557, +$9,069] includes zero.
- **Verdict per the rule: NOT-DEPLOYED.** The Exp2 magnitude does not generalize beyond its
  n=1 NQ book; the SECOND TEST's caution was vindicated by the first independent book. The
  overlay stays EXPERIMENTAL-OFF. Re-open only via new data (the never-built 2010-23
  bear-inclusive book) and a fresh pre-registration.
- Incidents: the frozen tfm-repro snapshot crashed on ES (stale code) — the current-tree
  runner used instead; bundle ES_1h starts 2025 (empty HMM training slice) — the 16-year
  archive file used; numpy-bool JSON cast.

## F-5 · FU-14 (#166) — the power model productionized: DEPLOYED ✅

`src/deploy/power_forecast.py` — M2's own functions imported, nothing re-implemented.
- **P (parity)**: all five instruments PASS — max |Δpred| ≤ 1e-16, zero unmatched rows.
- **S (statistic)**: Spearmans reproduced exactly — NQ .5907 · ES .5719 · RTY .6184 ·
  GC .4932 · CL .5461.
- **F (falsifier)**: scrambled series labels collapse the correlation +0.591 → +0.212
  (the committed shuffle floor).
- **A (artifact)**: forward mode emits the night-before per-event predicted power
  (expanding + trailing-24, % and $/contract); the historical `--now 2026-02-01` run
  produced regime-sane forecasts (CPI t24 0.39% ≈ $2,004/contract on NQ).
- **D**: golden gate 6/6 re-run green; the module is an INFORMATION layer — no trading
  consumer; consumers remain separate gated studies (the FU-11 draft is first in line).
- Ledger claim `FU14-POWER-FORECAST-DEPLOYED`; suite **43/43**.

## F-6 · FU-11 Stage 1 (#162) — the fused size engine: FORECAST-QUALITY stage ✅ PASS 4/4

**Owner's "proceed" (2026-08-20) opened execution. Order held: prior-art pass → pre-registration
(`docs/FU11-STAGE1-PREREGISTRATION.md`, PASS lines fixed) → server runs → ledger → this record.**

**The question**: the live vol engine (`volatility.py` HAR-RV, every champion's entry gate)
reads tape memory only — it cannot know tomorrow 08:30 is a CPI print. The FU-14 power layer
knows each release's expected size the night before. Does fusing them produce a measurably
better forecast of the engine's own target (`rv_pts`)?

**Prior art (recorded pre-run)**: HAR + scheduled-announcement dummies is an established
published family ("HAR-M"); the recorded risk — the literature's gain may be the DUMMY, not
the power magnitude — became the mandatory D-arm decomposition.

**Design (fixed pre-run)**: five models on identical rows — A deployed fixed-weight HAR ·
B fitted HAR-LS (the honest baseline: fusion must beat FITTING) · C fused (B + event dummy +
M2 night-before expanding power) · D dummy-only · C* shuffled-power placebo ×20. Research
1h frames from the 16-year 1m archives (NQ/ES/RTY/GC/CL) + NQ 4h; train <2024, test 2024→;
decision statistic = paired event-bar QLIKE differential (B−C), bootstrap 90% CI.

**Results (test event bars; QLIKE, lower better)**:

| run | n evt | A deployed | B HAR-LS | D dummy | **C fused** | placebo | diff (B−C) | 90% CI |
|---|---|---|---|---|---|---|---|---|
| NQ 1h | 140 | 8.11 | 7.64 | 1.20 | **0.48** | 1.21 | **+7.16** | [+4.96, +9.69] |
| ES 1h | 140 | 9.94 | 9.28 | 1.33 | **0.58** | 1.34 | **+8.69** | [+6.18, +11.62] |
| RTY 1h | 140 | 25.05 | 22.52 | 2.40 | **1.10** | 2.42 | **+21.42** | [+14.77, +29.27] |
| GC 1h | 139 | 7.12 | 7.32 | 1.17 | **0.89** | 1.17 | **+6.43** | [+5.17, +7.78] |
| CL 1h | 380 | 0.47 | 0.61 | 0.41 | **0.32** | 0.41 | **+0.29** | [+0.21, +0.38] |
| NQ 4h | 140 | 3.84 | 3.55 | 0.47 | **0.31** | 0.47 | **+3.25** | [+2.73, +3.79] |

**Verdict — PASS on all four pre-registered lines**: (1) NQ CI decisively positive; (2)
cross-instrument 4/4 (needed 3/4); (3) overall test QLIKE not only unharmed but IMPROVED
(NQ 0.548→0.487, ≈11%); (4) the placebo collapses exactly to the dummy level on every run
(placebo gain over D is ~0 or negative everywhere) — **the power MAGNITUDE carries the gain:
the fusion is POWER-AWARE, not merely calendar-aware** (D→C is a further −0.72 QLIKE on NQ
that shuffled power cannot reach). Era halves both positive on all six runs, with the honest
note that the gain roughly HALVES in 2025+ vs 2024 (e.g. NQ +10.88 → +4.76) — decisive but
shrinking; consumers must not assume the 2024 magnitude.

**The insights of record**:
1. ⭐⭐ **The live gate's forecast is catastrophically wrong exactly on release bars** —
   event-bar QLIKE ≈8 versus its ~0.5 everyday regime. Every champion's entry gate is blind
   at the moments the book concentrates into (FU-1). The night-before calendar terms repair
   most of that error for free.
2. The fitted HAR-LS barely improves on the deployed fixed weights (7.64 vs 8.11 on NQ event
   bars) — the deployed engine's weakness is NOT its weights, it is its information set.
3. CL is the outlier that proves the pattern: its dense weekly calendar (EIA/API era) makes
   event bars routine (380 in test), so its baseline is already decent (0.47) and the gain
   small (+0.29) — the fusion matters most where events are RARE and violent (equity indexes).
4. GC: the deployed HAR beats fitted HAR-LS (7.12 vs 7.32) — fitting can overfit quiet bars;
   the calendar terms still dominate both.

**Ledger**: `FU11-STAGE1-FUSED-FORECAST-WINS` — V1 internal re-derivation of every decision
field, V2 CI+era stability on all six runs, V3 the placebo falsifier; **44/44 both machines**.

**What this stage did NOT do (by design)**: change any deployed component, touch any golden
number, or claim any P&L. Consumers are now ARMED, each behind its own future pre-registration:
① champions' entry re-gate on ENGINE frames (predicted neutral by the Chronos program rule;
lowest priority), ② the sizing ramp with the fused forecast as regime input (FU-13's kill
demands per-instrument design), ③ FU-7 power-scaled news-leg geometry, ④ box stop distances.
Queue position: the approved order resumes (FU-9 event-state dataset → FU-2 veto replay →
FU-3/FU-7 as the consumer implementations).

## F-7 · FU-9 (#161) — the event-state dataset v1: BUILT ✅ (2026-08-20)

**The substrate every B-family study (FU-5/FU-6/FU-8), FU-15's design, and the WS-EARN return
consume. Spec FROZEN before the build (`docs/FU9-DATASET-SPEC.md`); the dataset is only
written when its four integrity gates pass — and all 16 (4 gates × 4 legs) passed.**

**Shape**: one row per (event × leg) — 1,765 rows: NQ 449, ES 449, RTY 418 (its 2019 price
floor), YM 449; series {CPI 116-118, NFP 107-127, FOMC 72-84, Retail 89-120} ≥2016; 342-348
columns: identity + M2 power context (pred_exp/pred_t24/n_priors/jump_pct) + the frozen ride
outcome (deployed `run_bracket`, qty=1, stressed costs) + 330 stance columns (cdir/vdir ×165
registry indicators at DEFAULT params, evaluated on the last 1m bar CLOSED before the
rel−300s entry, 2,000-bar context, the deployed --ind-1min convention) + NQ box-book state
per TF from the FU-1 audits.

**The gates**:
- **C1 replay parity**: on all 307 events overlapping the committed wsescpi replay evidence
  (NQ 81, ES 29, RTY 81, YM 116) the ride P&L matches **to the cent** — the outcome
  generator is pinned to the deployed executor's proven behaviour.
- **C2 repaint falsifier** ⭐: for 25 seeded events × 165 indicators PER LEG, the stance is
  UNCHANGED when +1h of FUTURE bars is appended to the context — no indicator in the
  registry repaints. This is now a proven property of the whole library at default params.
- **C3 uniqueness / C4 coverage**: clean; 2 CPI events lack 1s ride coverage (kept as
  state-only rows, itemized).

**Incidents kept**: `schedule.load` import name; YM missing from the M-era `FLOOR` dict
(onboarded v5.4.1 — floor 2016 set explicitly, printed, not silently defaulted).
**Cost profile** (measure-first): the whole 165-indicator × 449-event evaluation is ~80s/leg;
the top consumers are rsi_connors/hma (~3s cumulative each) — no dfa-class problem at this
window size.

**Ledger**: `FU9-EVENT-STATE-DATASET` — V1 cost-identity/alphabet/scope re-derivation, V2
LOCAL cent-exact re-join vs the independent committed evidence, V3 manifest falsifier +
non-degeneracy. **45/45 both machines.** v1 FROZEN; the spec's discipline reminder stands:
the table existing is not permission to scan it.

## F-8 · FU-2 (#154) — the news-veto replay: CLOSED-NULL ✅ (2026-08-20)

**The counterfactual FU-1 armed: does BLOCKING new box entries inside [rel−5m,+15m] Tier-1
windows pay? Pre-registration (`docs/FU2-PREREGISTRATION.md`) fixed the verdict rule before
the run; the verdict is the rule's, not ours.**

**Method**: the engine's own entry gate masked on in-window decision bars, through the
identical `fast_backtest` call FU-1 used — full path dependence (a vetoed entry can change
every later trade), never log filtering. Built-in parity gate: **all six baselines reproduce
the committed FU-1 books exactly** (trade counts and totals to the cent). Control: the
+3-day shifted calendar (clock times kept — the seasonality-only veto).

**Results (2016→, engine $, per frame)**:

| tf | base trades / net / maxDD | veto Δnet | veto ΔmaxDD | shifted Δnet |
|---|---|---|---|---|
| 4h | 445 / $73,209 / $37,609 | **−$3,159** | **+$10,430 (worse)** | +$15,859 |
| 2h | 507 / $59,401 / $33,014 | +$6,447 | +$748 | +$5,847 |
| 1h | 913 / $19,650 / $83,340 | +$10,768 | −$6,202 | +$10,625 |
| 15m | 1,993 / $25,242 / $37,343 | +$1,705 | −$1,837 | −$2,391 |
| 5m | 1,416 / −$11,759 / $27,761 | +$583 | −$801 | −$327 |
| 2m | 4,187 / −$1,551 / $27,961 | +$877 | −$3,444 | −$4,667 |

**Pooled**: Δnet **+$17,221**, day-bootstrap 90% CI **[−$36,107, +$71,273]** (MDE $53,960 —
the book's daily variance hides anything smaller); ΣΔmaxDD −$1,106 (≈nothing). **Verdict by
the pre-registered rule: CLOSED-NULL.**

**The mechanism is dead beyond the power question**: the SHIFTED-calendar veto gains MORE
(+$24,946) than the real one (+$17,221) — the release-specific component is **−$7,725**,
i.e. zero-to-negative. Whatever drift the veto captures is time-of-day seasonality
(avoidable on ANY day at those clock times), not the releases. And on the 4h frame — the
8.4× concentration FU-1 found — the veto HURTS (−$3,159 with DD $10,430 WORSE): those
in-window entries pay.

**Honesty anchors settled**: the recorded expectation ("the DD improvement is the likelier
win") was WRONG — ΔDD ≈ 0. FU-1's every-CI-includes-zero was the true answer all along: the
box book and the news layer coexist; **no stand-aside overlay will be built**.
Close-before-release (an EXIT-side idea) was not tested and stays in the parking lot,
now with a lowered prior.

**Ledger**: `FU2-NEWS-VETO-CLOSED-NULL` — V1 pooled-from-daily re-derivation, V2 the 6/6
FU-1 parity anchors, V3 the shifted-control mechanism kill + mandatory MDE. **46/46 both
machines.**
