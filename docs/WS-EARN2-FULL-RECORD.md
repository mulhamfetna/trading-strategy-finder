# WS-EARN Return — the Full Record (the owner's roadmap ③)

**Opened 2026-08-20 (owner: "lets go") from `WS-EARN-HANDOFF.md`. Tracking #109; phases get
their own issues. Everything here is claim-bound (`claims_earn2.py`).**

## E-0 · The opening state (inherited, not re-derived)

From the original WS-EARN (#109–#113): the 783-event / 12-ticker / 16-year timestamp table
(EDGAR acceptance ET; acceptance ≠ announcement, INTC ~7min; C4 human check owner-pending
#110); H1 (a ride premium) REJECTED 0/8; announcement minutes move NQ **4.98×** matched
minutes; the sample supports 2–6 approaches (Stage-2 power discipline). From WS-FUSION: the
FU-9 schema, the bracket primitive (short included), the per-key power methodology, and the
laws (calendar pays / tape does not predict / asymmetry first-class / placebo owns positives
/ near-miss is a miss / anti-premium ≠ drift).

## E-1 · E-P1 (#169) — the earnings power model: PASS 5/5 ✅ (2026-08-20)

**The question**: is earnings-move SIZE forecastable the night before, per ticker, the way
macro size is (M2, ρ≈0.5)? **Method**: M2's own functions transplanted — P_hist per TICKER
(expanding median of prior earnings-minute |move|%, shifted, ≥8 priors) vs realized
jump_pct on the 16-year 1m frames.

**Results**: 462/783 events carry a 1m bar at the stamp (AMC thin sessions — counted);
366 scored after warmup.

| gate | line | result |
|---|---|---|
| 1 primary (NQ) | Fisher CI-lo > 0 | **ρ +0.4583, CI [+0.3733, +0.5356]** ✅ |
| 2 V1 quintiles | bucket-mean rank ≥ 0.8 | ordered ✅ |
| 3 ES replication | its own P_hist vs ES moves, CI-lo > 0 | **ρ +0.3323, CI-lo +0.2379** ✅ |
| 4 V3 falsifier | beat 200 ticker-shuffles' p95 (P_hist rebuilt) | beaten ✅ |
| 5 control | clean-minute ρ ≤ half real | materially weaker ✅ |

**Verdict: PASS — the M2 law extends to earnings.** A ticker's own history ranks tomorrow
night's index violence at ρ≈0.46 — the same magnitude as the macro power model that became
the deployed forecast layer. **POWER ≠ PREMIUM stands**: this ranks violence, it does not
claim payment (H1's 0/8 already showed the frozen ride does not collect here).

**Armed by this pass** (each behind its own pre-registration): **E-S1** — the event-state
dataset on the FU-9 schema over earnings timestamps; **E-X1** — earnings × the fused
forecast (does the live vol gate mis-forecast earnings bars the way it mis-forecasts CPI
bars?). Ledger: `EP1-EARNINGS-POWER-FORECASTABLE`, **53/53 both machines**.

## E-2 · E-X1 — earnings × the fused forecast: PASS ✅ (2026-08-20)

**FU-11's machinery verbatim, the earnings calendar swapped in. Question: is the live vol
engine as blind on earnings bars as on CPI bars, and does the night-before per-ticker power
repair it?**

| run | n evt bars | A deployed | B HAR-LS | D dummy | **C fused** | placebo | diff (B−C) | CI90 |
|---|---|---|---|---|---|---|---|---|
| NQ 1h | 92 | 1.0812 | 1.3046 | 0.8569 | **0.7945** | 0.8569 | **+0.5101** | [+0.344, +0.704] |
| ES 1h | 92 | 0.7321 | 0.8683 | 1.2045 | 0.7687 | 1.2078 | +0.0996 | [+0.021, +0.183] |

**Verdict: PASS on the four registered lines** (NQ primary CI-positive with C beating A;
ES witness positive in sign; no harm off-event; the placebo collapses EXACTLY to the dummy
level on NQ — the power magnitude carries the repair, as on macro).

**The two honest asymmetries of record**:
1. **The earnings blindness is ≈14× SMALLER than macro's** — the fitted baseline's
   earnings-bar QLIKE is ≈1.3 vs CPI's 7.6 (vs ≈0.5 everyday). AMC thin bars, single-ticker
   dilution of an index move, and the acceptance-lag smear all shrink it. Real, repairable,
   but a different order of magnitude.
2. **On ES the deployed FIXED weights beat every fitted variant on earnings bars**
   (A 0.732 < C 0.769) — the fusion repairs the fitted model's gap without beating the
   production forecast there. The pass is recorded WITH this fact, not despite it.

Also: the earnings dummy's beta is NEGATIVE with the power term strongly positive — knowing
"an earnings bar" alone over-corrects; knowing HOW BIG is the load-bearing information.

**Consequences**: the blindness-and-repair law now covers BOTH calendars; the joint
(macro + earnings) forecast is the declared follow-up; all consumers stay behind the
fusion-era consumer laws. Ledger: `EX1-EARNINGS-FUSED-FORECAST-PASS`, **54/54 both
machines**. Next armed item: **E-S1** (the event-state dataset, FU-9 schema).

## E-3 · E-S1 — the earnings event-state dataset v1: BUILT ✅ (2026-08-20)

**The FU-9 schema over the earnings calendar (spec frozen pre-build). 462 rows × 341
columns per leg (NQ, ES; 924 total): identity + the E-P1 power context — parity-anchored
EXACTLY to the committed evidence on all 366 scored rows (gate C1) — + the frozen macro
bracket as a REFERENCE outcome (432/462 with 1s coverage; H1 already rejected this ride —
stored as what-it-would-do, the FU-9/Retail precedent) + the 165-stance vector at
stamp−300s. The repaint falsifier passed again on the earnings frames (25×165 per leg,
+1h future appended, stances unchanged). Builder ~90s/leg, FU-9's machinery reused
(`stance_rows`, `c2_causality`, `ride_outcomes` imported, not re-implemented).**

**v1 FROZEN.** Ledger: `ES1-EVENT-STATE-DATASET` (V1 re-joins the power context locally;
V2 the live-executor cost identity; V3 the 8 manifest gates + non-degeneracy). **55/55
both machines.** The ×indicators phase now has its substrate — and stays bound to
mechanism-first, locked-holdout pre-registrations (macro state-conditioning measured ≈zero
in the fusion era; the earnings edition starts with that prior).

## E-4 · E-X2 — the joint two-calendar forecast: NOT CERTIFIED ✅(verdict) (2026-08-20)

**The composition question: does ONE model carrying both calendars' terms deliver both
repairs simultaneously? Four lines registered; no new placebo arms (each power term had
already survived its own falsifier — this tested composition, not existence).**

| line | NQ | ES |
|---|---|---|
| 1 no macro degradation (≤1.001×) | ✅ 0.4789→0.4791 | ✅ 0.5844→0.5844 |
| 2 no earnings degradation (≤1.001×) | **❌ 0.7945→0.7957 (ratio 1.0015)** | ✅ 0.7687→0.7680 |
| 3 union-bar CI90 > 0 | ✅ +4.52 [3.20, 6.09] | ✅ +5.29 [3.79, 7.04] |
| 4 overall single-best | ✅ 0.4853 vs B 0.5485 | ✅ 0.4771 vs B 0.5546 |

**Verdict by the registered rule: NOT CERTIFIED** — NQ's earnings-bar degradation (0.15%)
exceeds the 0.1% line by ≈0.05%, and the rule held. **The third refused near-miss** (FU-6's
0.003 AUC · FU-3's CI touch · this) — bar integrity is now a programme signature, verified
by the claim's own V3 check every ledger run.

**The texture recorded WITH the verdict**: ES composes cleanly (4/4); the union
differential is hugely positive on both instruments; the joint model is the overall
single-best forecast on both. The failure is NQ-local, tiny, and on 92 noisy bars — which
is precisely the design lesson: **tolerances must be POWERED like any other line** (a 0.1%
no-degradation line on n=92 QLIKE is noise-sensitive). A v2 with a freshly registered,
powered tolerance may be filed later; never a post-hoc widening.

**Consequences**: the single-calendar models (FU-11's macro, E-X1's earnings) stand alone
as the reference repairs; **E-D1 (productionization) is NOT armed.** Ledger:
`EX2-JOINT-FORECAST-NOT-CERTIFIED`, **56/56 both machines**.

## The workstream queue (owner-ordered, 2026-08-20)

- **E-C1 (ACTIVE)**: the ×indicators conditioning phase — see E-5 below.
- **E-X2 v2 (QUEUED by owner word)**: the joint two-calendar forecast re-registered with a
  POWERED tolerance (the E-X2 design law applied: the no-degradation line sized to the
  event-bar sample's QLIKE noise, fixed before the run). Not scheduled until called.
