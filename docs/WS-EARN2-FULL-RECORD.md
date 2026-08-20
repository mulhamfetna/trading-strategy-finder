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
