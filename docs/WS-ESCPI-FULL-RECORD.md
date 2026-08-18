# WS-ESCPI — The ES CPI Ride: the Full Experiment Record

**Issue #139 · 2026-08-18 · ledger 36/36 local AND server · every number ledger-bound
(`claims_escpi.py`) or re-derivable from a committed file.**

This is the experiment-by-experiment record of the ES CPI study — the same discipline as
`WS-NEWS4-FULL-RECORD.md`: every run, every parameter, every incident, in the order it
happened, so nothing survives only as a remark in a chat log.

---

## 0 · Provenance of the hypothesis

WS-NEWS4/N3 (#137) measured the deployed-set ride on ES (pooled: POWERED-NULL, net +$55.04,
p=0.034 ≥ α) and, **descriptively**, its per-title slices: CPI-alone net **+$151.37/event**
(t=+3.00, n=116), NFP-alone +$17.91 (t=+0.49), FOMC-alone −$21.86 (t=−0.48). Combined with the
confirmed CPI concentration (NQ +$309, RTY +$78) and GC's descriptive +$80 (t=1.78), the
hypothesis: *the CPI premium exists on ES at deployable size*. Integrity problem: that +$151
was found by measuring ES's full history — **the history is consumed and cannot confirm
itself** (the M3/RTY lesson).

## 1 · Experiment E1 — the pre-registration (commit `051ff07`, before any new data)

Filed on #139 and committed as `docs/WS-ESCPI-PREREGISTRATION.md` BEFORE the YM file was
opened (nothing read but its existence in a directory listing). Frozen there:

- **Primary confirmatory test**: the CPI-alone ride on **YM** — 1-second data never loaded by
  any news study (WS-NEWS2 excluded YM for its 0-byte 1-minute frame; the 1s file was never
  opened). Constants by the deployed formula: PV $5/pt, tick $5 ⇒ stressed $22.50/event.
- **PASS** = two-sided p < 0.01 with positive mean · chronological half-split both halves
  gross-positive · jump gate (>1.2× quiet) · quiet-day control (400 days, seed 117) ·
  1,000-placebo noise check. POWERED-NULL if p ≥ 0.01 and MDE(80%, α=0.01) ≤ $150.
- **Data-quality gate (YM-specific)**: ≥70% of CPI windows must have ≥150 traded pre-release
  seconds, else **VOID-DATA** — the 0-byte-1m history made this mandatory.
- **Falsifier**: the same YM pipeline fed Retail-alone minutes must NOT come out positive.
- **ES robustness battery**: the full gate battery on ES's CPI slice — labeled robustness,
  never independent confirmation.
- **The interpretation rule, fixed in advance**: *"ES CPI ships only if the YM holdout PASSES
  or the owner explicitly accepts descriptive-grade evidence."*

## 2 · Experiment E2 — the runner (`wsescpi_study.py`, commit `cd97077`)

Machinery imported from the parity-proven stack (`release_executor.run_bracket`,
`news4_premium_scan.ride_all/minute_jump/control_days`, `news4_n3_deepdive.block_moments`) —
nothing re-implemented. CPI events = the deployed schedule's confirmed `Inflation Rate MoM`
rows ≥2016 (the SAME 116-event set the ES observation was measured on; 118 scheduled, 116
fill). Retail-alone minutes (overlap-excluded) as the falsifier block.

## 3 · Incident I1 — the YM file was CORRUPT

First YM run crashed parsing the file tail: **the last bytes are padding**. Diagnosis by
binary search over the raw bytes: valid rows end at **2016-01-15 15:38:36, cut mid-row**
(`...15906.0,1590`), followed by ~41 MB of NUL/space padding — an assembly process killed
mid-write (file dated 2026-08-12; same pathology family as the 0-byte YM 1m frame). Usable
overlap with the ≥2016 calendar era: **5 days, zero CPI events**. A dead holdout.

## 4 · Experiment E3 — re-assembling YM from raw

The Databento raw (`~/Mulham/data_2010_1s/YM.csv`, 10.8 GB, ts_event/symbol schema) and the
assembler (`main_futures_seconds.py` — the same script that built every other instrument:
spread-contract removal, UTC→ET wall-clock, volume-dominant continuous contract, resample
with 18:00 origin) were both present on the server. Re-ran for YM (~15 min, 123 GB box):
YM_1s.csv **830 MB corrupt → 4.88 GB complete**, span 2010-06-06 → 2026-08-07, and every
other timeframe regenerated — **the 0-byte YM 1m frame that excluded YM from WS-NEWS2 is
fixed**. YM is now fully studyable for all future work.

## 5 · Incident I2 — the coverage gate mis-fired on ES

First ES run returned VOID-DATA: ES coverage = 62.7% of CPI windows with ≥150 traded
pre-release seconds, under the 70% line. But the gate was **registered for YM specifically**
(the degenerate-file guard); the runner had over-applied it to ES — data known-good (N3
filled 116 events at jump 20×). Fix `2886f9a`: the gate voids **YM only**, ES reports
coverage. No thresholds changed; the registered wording restored.

## 6 · Experiment E4 — the ES robustness battery: PASS on every gate

n=**116** · gross +$203.87 · **net +$151.37**/event ($52.50 stressed) · t≈3.0, p=**0.0027**
< α=0.01 · both halves gross-positive · jump **20.5×** quiet baseline · quiet-control floor OK
(08:30 control itself ≈ −$50 net = cost drag + drift) · noise check OK.
**Falsifier behaves**: Retail-alone on ES is significantly NEGATIVE (gross −$66.38,
p=2.7e-09) — the pipeline does not bless everything it touches.

Per-year net $/event (the era table): 2016 −71 · 2017 −25 · 2018 +136 · 2019 −74 · 2020 −105
· 2021 +158 · 2022 +238 · 2023 −89 · **2024 +256 · 2025 +823 · 2026 +580**. Same
era-concentration as NQ/RTY ⇒ the regime monitor must guard ES identically.
**The owner's 2024→2026 verification window: n=29, net +$529.44/event, total +$15,353.82 per
contract.**

## 7 · Experiment E5 — the YM holdout on the complete file: VOID-DATA

Coverage: **12.7%** of CPI windows reach 150 traded pre-release seconds; median **101**
seconds (p25 75 / p75 128), 2 windows empty. YM's premarket tape is genuinely thin — the
registered gate scores **VOID-DATA: no premium verdict claimable either way**. The 150s/70%
calibration was an a-priori guess that proved stricter than YM's real (thin but functional)
tape — disclosed, and per discipline NOT loosened after seeing the data.

**Descriptive, under the VOID label** (committed as `wsescpi_events_YM_descriptive.csv`):
n=**116**/118 fill (a dead file fills nothing) · gross +$130.14 · **net +$107.64** · t=3.15,
p=0.0016 — it *would have* passed the α=0.01 primary test · 2024→2026 slice **+$355.72**/event.
Sign, size-order and era all agree with ES; formally it confirms nothing.

## 8 · Experiment E6 — engine stage: the executor learns ES (commit `90df68c`)

`src/deploy/release_executor.py`: PV["ES"]=50, TICK_USD["ES"]=12.5 (⇒ stressed $52.50 by the
same 2.50+4t formula), and `--series` (comma-separated schedule titles) on replay/paper so an
instrument can ride a SUBSET of the schedule — ES deploys riding CPI only. Default (no
filter) is **byte-identical** for NQ/RTY. Isolation battery **18/18**.

## 9 · Experiment E7 — the three replays and two-implementation parity

Executor replays, floor 2024, `deploy_out_escpi/` → committed as `wsescpi_replay_*.csv`:

| instrument | events | gross/event | net/event | cross-check |
|---|---|---|---|---|
| NQ (all 3 series) | 81 | +$447.03 | +$424.53 | = the WS-DEPLOY playbook to the cent |
| RTY (all 3 series) | 81 | +$117.69 | +$95.19 | = the playbook to the cent |
| ES (`--series "Inflation Rate MoM"`) | 29 | +$581.94 | **+$529.44** | = the study runner **to the cent** (independent implementation) |

## 10 · Experiment E8 — integration & joint risk (2024→2026, qty=1, net stressed)

Layer today $42,097.32 (NQ $34,386.93 + RTY $7,710.39) + ES CPI **+$15,353.82** ⇒
**$57,451.46 = +36.5%**. Joint-risk measurement (merge by event minute):
ES↔NQ same-event correlation **0.78** (RTY↔ES 0.38) · **24%** of CPI events lose on all three
legs · worst joint CPI event 2025-09-11: **−$1,023** (NQ −501 / RTY −142 / ES −380) · the
layer's worst overall event unchanged (2026-03-06 NFP −$1,168 — ES has no leg there).
Verdict wording fixed in the ledger: **this SCALES the CPI bet; it does not diversify it.**

## 11 · Experiment E9 — engine gate: golden 6/6

With the executor change present, `perf/check_golden.py` on the server worktree:
4h $151,655/n=277 · 2h $101,518/n=173 · 1h $110,038/n=353 · 15m $82,156/n=654 ·
5m $20,092/n=314 · 2m $31,898/n=276 — **ALL MATCH**. The optimizer engine is untouched.

## 12 · Experiment E10 + Incidents I3/I4 — dashboard stage (SSH + server-side Playwright)

- **I3**: a **stale :8250 dashboard** from the *deleted* deploy-news worktree was still
  running (nohup survives worktree removal). Killed **by port** (`ss -ltnp` → PID), never by
  name (the pkill self-match trap). Fresh :8250 started from the legacy18 worktree.
- **E10**: `perf/escpi_dashboard_capture.py` (committed this time — the WS-DEPLOY session's
  script never was): Playwright drives the real UI on loopback — select NQ, 1h, champion
  preset, click Run, wait for the report, full-page screenshot, extract the cards text — on
  BOTH :8250 (branch) and :8200 (production).
- **I4**: the first cut compared against the engine-golden $110,038 — the **wrong
  reference**: the dashboard's verified 1h book (established in the #130 browser
  verification) is **+$78,823 / 129 L1 entries / $8,815 DD** — a different measurement
  (dashboard window/config vs optimizer champion). Corrected and documented in the script.
- **Result: PASS — branch ≡ production, identical card text, both showing the verified
  book.** Screenshots committed: `playbooks/news-release-long/evidence/escpi/*.png`
  (visually inspected: WS champion 1h, SL 59.696/TP 124.993, 129 entries, +$78,823).

## 13 · The ledger (suite 36/36 local AND server)

`claims_escpi.py` — three claims, nine checks, each triple failing for a different reason:
- **ESCPI-ES-BATTERY-PASS** (V1 re-derive fills · V2 executor parity · V3 Retail falsifier).
  Blind spot: robustness ≠ independence — this claim alone can never justify shipping.
- **ESCPI-YM-HOLDOUT-VOID** (V1 manifest consistency · V2 descriptive file re-derives ·
  V3 the VOID is thinness, not a dead file — 116/118 fill). Blind spot: the a-priori gate
  calibration is exactly why the strong descriptive result stays descriptive.
- **ESCPI-INTEGRATION-36PCT** (V1 totals re-derive · V2 NQ/RTY = the WS-DEPLOY playbook ·
  V3 "it diversifies" is FALSE — corr and joint-loss measured). Blind spot: qty=1 arithmetic
  only; ES scaling unmeasured.

## 14 · Deliverables and the decision

`docs/WS-ESCPI-REPORT-BILINGUAL.html` (L0→L3, AR+EN) · `champion.json.escpi_candidate` +
`PLAYBOOK.md` §8 (candidate, NOT deployed) · this record.
**⛔ Ship**: by the pre-registered rule, blocked on the owner's explicit #139 decision
(descriptive-grade acceptance / forward paper-confirmation / decline). Everything else green.

## 15 · What went well / what went wrong

**Well**: the pre-registration survived contact with two data disasters without bending; a
corrupt holdout was *rebuilt from raw* instead of shrugged off (and fixed YM for the whole
project); two implementations agree to the cent; all three ship-gate stages closed same-day.

**Wrong (kept)**: I1 the corrupt YM file (assembly hygiene — no completeness check existed);
I2 the gate over-application to ES; I4 the wrong dashboard reference; and the registered
150s/70% line itself — an a-priori calibration that voided a thin-but-real tape, the price of
which is that YM's agreeing evidence stays descriptive.
