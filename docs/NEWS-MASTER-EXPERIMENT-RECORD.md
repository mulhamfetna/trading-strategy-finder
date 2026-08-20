# The News Programme — Master Experiment Record

**Every experiment, its result and its finding, across the entire programme (2026-06 → 2026-08-20).
Current through v5.4.3 + FU-11 Stage 1: all profitable news deployed and scaled, the premium
grid literally closed, the fusion workstream executing (the fused size engine has WON its
forecast-quality stage), ledger 44/44 on both machines.**

This is the master index. Each workstream's full detail lives in its own record —
`NEWS-PROGRAMME-FULL-RECORD.md` (WS-NEWS2/3), `WS-NEWS4-FULL-RECORD.md`,
`WS-ESCPI-FULL-RECORD.md` (+ 2 addenda), `WS-GRID-RESULTS.md`, `WS-FUSION-FULL-RECORD.md`
(F-0…F-6) — and every number below is bound to the claims ledger
(`optimize/verify/run.py`, 44/44) or a committed evidence file.

```mermaid
flowchart TD
  A[Fundamentals era\nGC replication · stop-outs · sessions] --> B[WS-NEWS2 #114-#123\ndirection & surprise: DEAD everywhere]
  B --> C[WS-NEWS3 #117,#124-#126\nthe premium found: the confirmed ride]
  C --> D[WS-DEPLOY #127-#132\nexecutor · monitor · scaling · v5.3.0]
  D --> E[WS-NEWS4 #134-#138\nthe dropped series: zero new premiums]
  E --> F[WS-ESCPI #139\nES CPI shipped v5.4.0]
  E --> G[WS-GRID #140\n661 cells: ONE positive = YM CPI]
  G --> H[RQ-7 #147\nexecution gate: YM ACQUIRED v5.4.1]
  F --> I[THE LAYER: 4 legs, one CPI bet\n$67,767 net 2024-26 at qty=1/leg]
  H --> I
  I --> J[WS-FUSION #152+\nFU-1 audit · FU-13 killed · FU-14 deployed]
  J --> K[FU-11 Stage 1 PASS 4/4\nfused vol forecast beats the live gate]
  K --> L[Consumers armed, each gated\nre-gate · ramp · geometry · stops]
```

---

## Era 0 — the fundamentals prelude (pre-programme)

| # | experiment | result → finding |
|---|---|---|
| 0.1 | Fundamental analysis (macro levels vs the box strategy) | CLOSED: macro IS priced in; no entry edge. **94% of stop-outs are 1-second sweeps** — the fact that later justified 1-second data everywhere. |
| 0.2 | GC replication of macro-surprise sensitivity | Gold reacts INVERSELY to macro surprises (Spearman −0.193; Pearson blind — fat tails) but un-tradeable at cost. Finding: report rank correlation beside Pearson on fat-tailed data. |
| 0.3 | Session/own-distribution studies | Session structure is real in tape and risk, not a tradeable entry edge; the per-trade tail (±$1,600) defeats every weak edge. |
| 0.4 | h1a pre-event stop-out scan (8 instruments) | Pre-event stop-out risk quantified per instrument — the input that later shaped GAP-01 fills. |
| 0.5 | EIA/API mechanism probe (CL) | The inventory releases move CL violently — the observation that kept energy in every later funnel. |

## Era 1 — WS-NEWS2 (#114–#123): the calendar and the death of direction

| # | experiment | result → finding |
|---|---|---|
| 1.1 | Source evaluation (8 calendar providers) | 7 rejected (403s / no timestamps / date bugs). **TradingView chosen**: real UTC per event, DST correctly encoded. |
| 1.2 | Calendar verification (`tv_calendar.py --verify`) | ⚠️⚠️ **2013-2015 summer timestamps are one hour late** (fixed-offset back-fill; 87 series affected) → the programme-wide **≥2016 rule**. NFP alone passes even when 90% is broken — single-series checks don't generalize. |
| 1.3 | Provenance battery (#119/#120) | `previous` proven point-in-time vs ALFRED on 4 series; `forecast` unverifiable (no archive) — the honest blind spot every later study inherits. |
| 1.4 | Phase-2 pre-registration + the 643-pair direction scan (82 series × 8 instruments) | **Direction is DEAD everywhere**: surprise explains the release-minute JUMP (ρ to −0.63) and NOTHING after; edge excluded at 95% on all pairs. Four attacks, four real effects, none tradeable. Finding: the fix is SIZING, not prediction. |
| 1.5 | YM row | ⛔ Excluded — the YM 1m frame was 0 bytes (repaired much later, era 6). |

## Era 2 — WS-NEWS3 (#117, #124–#126): the premium found

| # | experiment | result → finding |
|---|---|---|
| 2.1 | Goal re-audit vs the owner's goal statement | The premium/ride had never actually been tested — POWER had been conflated with PREMIUM. Meta-rule: close workstreams against the GOAL STATEMENT. |
| 2.2 | M1 ride-through grid (5 series × 5 instruments, 1s bars) | Only **CPI** carries a ride premium (NQ grid-cell +$463 gross at no-TP); Retail is NEGATIVE (−$98 — flagged, resolved era 5); NFP weak; FOMC ≈ 0. Controls: quiet-minute placebos vs the FULL 39k calendar; the 8:30 seasonality floor declared. |
| 2.3 | M2 power model | Move SIZE is predictable night-before (ρ≈0.5); **POWER ≠ PREMIUM** becomes the programme's central law. |
| 2.4 | M3 the confirmed trade (pre-registered, Bonferroni α/54 + half-split) | **LONG NQ/RTY at release−300s, S 0.10%, TP 0.40%, tie⇒STOP, exit +900s over {CPI,NFP,FOMC}: NQ +$155.56/ev gross t=4.13, net +$133.06 stressed; RTY holdout (never loaded before filing) confirms.** Win 36.4%, median loses, the +4R tail pays. One-sided: the straddle's short leg loses 18/18. |
| 2.5 | Controls & falsifiers battery | Consensus numbers fully dead pre-release; clean-day controls ≈ $0; the “no release that day ≠ no news at that minute” lesson. |

## Era 3 — WS-DEPLOY (#127–#132, → v5.3.0)

| # | experiment | result → finding |
|---|---|---|
| 3.1 | D1 release executor + schedule | Replay parity **NQ 327/327, RTY 238/238 exact**. Found: the study's same-minute tie-break was per-instrument unstable (2026-03-06 NFP+Retail minute) — pandas non-stable sort as a scientific instrument. |
| 3.2 | Engine qty hook | `pnl = pnl × pv × qty`, byte-identical at qty=1; linearity to the cent. |
| 3.3 | D2 regime monitor | Rolling 24-CPI net-stressed mean < 0 ⇒ STAND_DOWN, sticky; GO at build (+$1,231). Registration error kept honestly: 2016-19 was expected to stand down and did not. |
| 3.4 | With/without measurement | The overlay adds +31.1% profit for +6.6% DD on the 1h slot; daily correlation +0.098 — near-orthogonal to the box book. |
| 3.5 | D3 scaling (qty 5/10/20) | **The constraint is the QUIET ENTRY SECOND** (NQ median 7 contracts) not the violent exit (231); worked entry over 300s is easily fed (1,531 median). |
| 3.6 | D4 worked entry validation | VWAP entry keeps 96% of NQ's edge; RTY IMPROVES +24%; combined qty=20 pace ≈ $330k/yr. Ship v5.3.0 after golden 6/6 + dashboard parity. |

## Era 4 — WS-NEWS4 (#134–#138): the dropped series

| # | experiment | result → finding |
|---|---|---|
| 4.1 | N1 coverage matrix (evidence-generated) | Premium had been tested on **5 of 237** series; **11,822 untested moments** in 92 groups. Traps recorded: Jobless Claims is TV-importance 0; title renames split series; the scan unit is the MINUTE. |
| 4.2 | N2 pre-registration + wide scan (Tier-1: 10 blocks × NQ/RTY at α=0.05/20; Tier-2 ~79 blocks) | **0/20 new premiums.** All Tier-1 jump-gates pass (1.6–4.7×) yet nothing pays — POWER ≠ PREMIUM at full-calendar scale. NQ MDEs $67–$234 all below the CPI-sized +$309: **powered zeros**. |
| 4.3 | The positive control | The deployed set through the identical pipeline reproduces **+$133.06 to the cent** — and caught a live bug pre-results (two-sided control gate wrongly vetoed CPI; fixed to the registered wording, all re-run). |
| 4.4 | CPI concentration measurement | CPI alone confirms on BOTH deployed instruments (NQ +$309, RTY +$78 net); NFP/FOMC alone never confirm anywhere. |
| 4.5 | N3 deep-dives (8 pre-registered tests, 5 instruments) | ⭐ **Retail anti-premium REAL** (gross −$86.10 NQ / −$32.41 RTY, both halves negative, series-specific); Durables powered nulls; **EIA/API definitive NO** (gross ≈ $0 at n=551/433 while jumping 5–8×); ES/GC pooled: no new surface; **ES CPI-alone +$151 t≈3.0 filed as the promotion candidate**. |
| 4.6 | N4 reports | The bilingual leveled report + the full record; both programme reports cross-linked. |

## Era 5 — WS-ESCPI (#139): ES shipped, the YM saga

| # | experiment | result → finding |
|---|---|---|
| 5.1 | E1 pre-registration (before opening YM) | YM named the true holdout; the ship rule fixed: *"ES ships only if YM PASSES or the owner explicitly accepts descriptive grade."* |
| 5.2 | I1+E3 the corrupt YM file → rebuilt from raw | YM_1s ended 2016-01-15 mid-row + 41MB NULs; re-assembled from the 10.8GB Databento raw. **Side effect: the 0-byte YM 1m frame is fixed — YM fully studyable.** |
| 5.3 | E4 ES robustness battery | PASS every gate: net +$151.37/ev, p=0.0027, jump 20.5×; Retail falsifier correctly negative. 2024→2026: +$529.44/ev, +$15,353.82/contract. |
| 5.4 | E5 YM holdout | **VOID-DATA** — thin tape vs the registered 150s line (median 101 traded pre-release seconds); descriptive +$107.64 t=3.15 agrees but confirms nothing. Gate NOT loosened after seeing data. |
| 5.5 | E6-E10 ship stages | Executor learns ES + `--series`; two-implementation parity to the cent; golden 6/6; dashboard branch ≡ production with screenshots. |
| 5.6 | E8 integration & joint risk | +36.5% layer profit at qty=1; ES↔NQ same-event corr **0.78**; 24% of CPI events lose all legs — **SCALING the CPI bet, not diversifying**. |
| 5.7 | The ship (owner word) → v5.4.0 | Playbook v1.2.0, portable `--verify` PASS, PR #148, release with bundle. |

## Era 6 — WS-GRID (#140): the literal closure

| # | experiment | result → finding |
|---|---|---|
| 6.1 | Pre-registration + the 661-cell sweep (all 9 instruments) | **ONE positive in the entire sweep: YM CPI (+$107.64, p=0.0016, jump 9.8×).** Census: 370 VOID-TIMESTAMP · 179 significant negatives (41% pure cost drag, 29% gross-POSITIVE — the fee schedule measured) · 106 powered nulls · 5 underpowered. |
| 6.2 | Structural findings | **CPI premium = equity-index phenomenon ordered by beta (NQ > ES > YM > RTY)**; metals gross-positive but cost-drowned (HG +$80, SI +$48 gross → RQ-5); **Retail gross-negative on 7 instruments**; NG's own inventory release jumps 8.5× and grosses −$4.89 (POWER ≠ PREMIUM, final form). |
| 6.3 | The research queue instituted | RQ-1..RQ-8 → issues #141-#147; the standing intake rule: *an observation without an RQ number does not exist.* |

## Era 7 — RQ-7 (#147): the execution gate and the acquisition → v5.4.1

| # | experiment | result → finding |
|---|---|---|
| 7.1 | E12-E14 the YM walk (owner-ordered) | Executor parity to the cent (full era +$107.64; 2024-26 +$355.72); golden 6/6; dashboard re-captured. |
| 7.2 | E15 the execution study (pre-registered ACQUIRE rule) | **ALL FOUR layers PASS**: fill staleness median 0.0s/p95 7.2s · next-open fill Δ**$0.58**/event · entry-window depth **364 contracts** median · exit tape 638s/4,081 contracts. **Lesson: traded-seconds density ≠ fill quality** — liquidity concentrates exactly at the entry second on CPI mornings. |
| 7.3 | The acquisition → v5.4.1 | Playbook v1.3.0, portable `--verify` PASS on YM, PR #149, release with bundle. ⛔ qty>1 on YM forbidden (entry BAR median 2 contracts) pending its own D3/D4. |

## The programme's laws (what every era kept re-proving)

1. **POWER ≠ PREMIUM** — violence is everywhere; payment lives in one place.
2. **The premium is an inflation-print, equity-index phenomenon**, ordered by index beta.
3. **Retail Sales is the calendar's one confirmed anti-premium**, market-wide.
4. **Read gross beside net** — on a $22.50–$102.50 cost line, low variance makes the fee schedule look like an anti-premium.
5. **Pre-register or perish** — every gate that embarrassed us (the two-sided control, the 150s line) was survivable *because* it was written down first.
6. **Positive controls are not optional** — one caught a live bug that would have silently hardened a zero.
7. **A verdict for every cell** — VOID-with-cause and powered-null are recorded states; silence is the only forbidden outcome.

## Era 8 — RQ-1 + RQ-9 (#141/#150): the scaling of the new legs → v5.4.2

| # | experiment | result → finding |
|---|---|---|
| 8.1 | Pre-registration of the scaled-deploy rule (before any run) | Participation median ≤2.5%/p95 ≤5% (worked mode) + retention ≥80% + the D3/D4 hard gates; "deploy each leg at the highest passing tier"; YM's borderline (≈5.5% naive estimate at q20) called out in advance — *the rule decides, not preference*. |
| 8.2 | D3 participation battery (ES, YM; CPI-only via the new `--series` filter) | Hard gates green both legs (V1 linearity to the cent; volume physics 48.8×/51.0×). The entry-second wall replicates: single-shot dies above qty=1 on both (ES q5 = 33% of the entry second; YM q1 already 50%). |
| 8.3 | D4 worked-entry validation (ES, YM) | Gates green (dual-path VWAP 0 mismatches; shifted-window falsifiers flip by $943/$616). Retention: ES **85.9%** (+$454.96 of +$529.44), YM **84.3%** (+$299.87 of +$355.72) — both clear the 80% line. |
| 8.4 | Window-participation measurement | ES window median **3,389 contracts** ⇒ q20 = **0.59%/0.98%** — approved at **20**. YM window median 375 ⇒ q5 = 1.33%/3.05% ✓ but q10 = **2.67%/6.11% breaches both lines** ⇒ **capped at 5**. The rule rejected a tier — it is not a rubber stamp. |
| 8.5 | Scaled deployment (v5.4.2) | Per-leg quantity rules shipped in playbook v1.4.0. Worked-entry window economics 2024→2026: ES q20 +$263,880 · YM q5 +$43,481 · NQ+RTY q20 +$859,141 ⇒ **layer at max approved tiers ≈ $1.167M/window (≈$450k/yr pace)** — a model-grade figure (VWAP fills at ≤2.5% participation), margin owner-side. Reconciliation recorded: YM single-shot qty=1 stays governed by RQ-7's direct fill measurement (Δ$0.58), which supersedes the participation heuristic at that size. |

## Era 9 — WS-FUSION opens (#152–#164): the audit, the archaeology, the system analysis

| # | experiment | result → finding |
|---|---|---|
| 9.1 | FU-1 event-window audit (#153, pre-registered definitions) | The NQ book CONCENTRATES into Tier-1 news windows: entry density up to 8.4×, **decomposed by the shifted-calendar control into a 2.16× time-of-day floor × ≈1.95× release-specific pull**; stop-outs 2.1–5.8× on all six frames; in-window P&L worse 5/6 (CIs include zero → FU-2's replay owns the money question); give-up insignificant (era-0 B1 generalizes). Ledger 41/41. |
| 9.2 | FU-11 archaeology (#162) | The early study is `subprojects/meta-prophet/` and its verbatim verdict — *"price direction is unforecastable, but volatility is"* — is the OPPOSITE of the recollection: 11 models lost to naive on price; HAR/HAR-RV beat naive +16.3% on range/RV. Direction dead by three independent routes; the remembered direction×size fusion has no direction ingredient. Reformulated (owner agreed): fuse the SIZE engines. |
| 9.3 | FU-12 system layer analysis (#164, owner-injected) | `SYSTEM-LAYERS-ANALYSIS.md`: full layer breakdown + the 9-entry volatility inventory. ⭐ **The deployed box vol-gate IS the meta-prophet HAR-RV forecast** (`volatility.py: vol_forecast`) — so FU-11 becomes "upgrade the live vol engine with the calendar terms it cannot see", forecast-quality stage first, consumers gated after; the FM bands' NO-GOs (gating) do not forbid their audition as forecast INPUTS. |

### Era 9 (continued) — the owner-ordered end-to-end arc (v5.4.3)

| # | experiment | result → finding |
|---|---|---|
| 9.4 | FU-13 (#165): the Exp2 sizing ramp through the pre-registered R/X/M deployment battery | **NOT-DEPLOYED by its own rule.** R exact (the preserved NQ book reproduces the deploy card to the dollar: flat $151,872 → ramp $162,228, +$10,356 equal-risk — the machinery proven). X FAIL: a freshly generated independent ES 1h+4h book ($57,315/263 trades) REVERSES the identical a-priori ramp (**−$18,632**; on ES even random regime→size maps lose, median −$12,282 — that book rewards no vol-mapped size dispersion). M FAIL: pooled 90% CI [−$25,557, +$9,069] includes zero. Insights: the SECOND TEST's n=1 caution vindicated by the first out-of-sample book; the "ES is vol-agnostic" asymmetry (known from gating) now proven on the sizing side; instrument asymmetry is a first-class design axis for any revival. Incidents kept: the frozen tfm-repro snapshot crashes on ES; bundle ES_1h starts 2025 (empty HMM train slice — use the 16-year file). |
| 9.5 | FU-14 (#166): the M2 power model productionized through B/P/S/F/A/D | **DEPLOYED (v5.4.3).** `src/deploy/power_forecast.py` (M2's own functions): parity 5/5 instruments exact (≤1e-16; Spearman NQ .5907 · ES .5719 · RTY .6184 · GC .4932 · CL .5461); scramble falsifier collapses (+0.591→+0.212); night-before forward artifact live (historical `--now` check regime-sane); golden 6/6. **Insight: deployment of a forecast = parity + falsifier + an ops artifact — zero direct P&L by design**; consumers (FU-11/FU-3/FU-7) remain gated studies. Playbook bundle v1.0.0 on the release. |
| 9.6 | The registrations and saves around the arc | FU-11's fused-size design SAVED as a standing file (`FU11-FUSED-SIZE-DESIGN-DRAFT.md`) per the owner's word; the system-layers analysis updated to v5.4.3 (two deployed forecast layers now; the killed ramp recorded); `ACHIEVEMENTS-SUMMARY.md` written — the release trail v5.2.0→v5.4.3, the laws, the kill list as an achievement. |
| 9.7 | FU-15 (#168) registered — the owner's dual-sided bracket | Simultaneous LONG+SHORT with power-informed SL/TP = a stop-replicated straddle monetizing forecastable SIZE with dead direction; killers pre-declared (two-way sweep double-stop — 94% of stop-outs are 1-sec sweeps; doubled costs; the losing median event; overlap with the deployed LONG ride). **Parked by owner behind FU-11.** |
| 9.8 | FU-11 Stage 1 (#162): the fused size engine's forecast-quality stage | **PASS 4/4 pre-registered lines (2026-08-20).** Adding the calendar terms the live vol engine is blind to (event dummy + M2 night-before power) beats BOTH the deployed fixed-weight HAR and the fitted HAR-LS on the engine's own target: NQ 1h event bars QLIKE 8.11→7.64→**0.48** (deployed→fitted→fused), diff +7.16 CI [+4.96,+9.69]; cross-instrument 4/4 (ES +8.69, RTY +21.42, GC +6.43, CL +0.29) + NQ 4h +3.25; overall QLIKE improves too (0.548→0.487). Placebo collapses to the dummy level everywhere ⇒ **POWER-AWARE, not merely calendar-aware** (D→C −0.72 QLIKE the shuffle cannot reach). ⭐⭐ Insight: **the live gate is catastrophically wrong exactly on release bars** (QLIKE ≈8 vs ~0.5 everyday) — its weakness is its information set, not its weights (HAR-LS barely helps). Honest note: gains halve in 2025+ vs 2024. Claim `FU11-STAGE1-FUSED-FORECAST-WINS`, **44/44 both machines**. Nothing deployed; consumers ①–④ armed, each own pre-reg. |

---

## The programme state as of 2026-08-20 (the running verdict)

**Deployed and earning (paper-only until a live gateway; regime monitor GO required):**

| layer | what it is | the number of record |
|---|---|---|
| The news layer (v5.4.2) | 4 legs, one CPI bet: NQ+RTY (CPI/NFP/FOMC) + ES (CPI) + YM (CPI); frozen ride LONG rel−300s, S 0.10% worse-of, TP 0.40% better-of, exit +900s; stressed costs lead | $67,767 net 2024→2026 at qty=1/leg; ≈$1.167M/window model-grade at max approved tiers (NQ/RTY/ES ≤20, YM ≤5 worked-entry; ⛔ YM >5 needs its own study) |
| The box book | 55 champions / 9 markets (context, not news) | ≈$840k/yr 2026-OOS at deployed caps |
| HAR-RV vol gate | the live entry gate of every champion (`volatility.py`) | the system's FIRST deployed forecast |
| Power-forecast layer (v5.4.3) | FU-14: night-before event-size forecasts, information-only | parity 5/5 ≤1e-16; ρ≈0.5–0.62; the SECOND deployed forecast |

**Killed, with cause (the kill list is an asset):** direction prediction (3 independent
routes) · surprise-based post-jump edge (612 pairs) · all non-CPI new premiums (WS-NEWS4,
powered) · vol/uncertainty GATING of the vol-seeking box (TimesFM, Chronos-2) · regime
HMM/jump edges · the Exp2 sizing ramp as-deployed (FU-13: ES reverses it) · Retail longs
(confirmed ANTI-premium on 7 instruments — a tradeable-short question parked in FU-8).

**The laws the programme keeps re-proving:** POWER ≠ PREMIUM · the CPI premium is an
equity-index phenomenon ordered by beta (NQ>ES>YM>RTY) · size is forecastable, direction is
not · read gross beside net (cost drag masquerades as anti-premium) · traded-seconds density
≠ fill quality · same-seed agreement ≠ replication.

**The fusion frontier (era 9, open):** FU-11 Stage 1 PASSED — the live vol engine's one
blindness (the calendar) is now proven repairable, and the repair is power-aware. Armed and
waiting, each behind its own pre-registration: the four fused-forecast consumers (re-gate ·
sizing ramp · news geometry · box stops), FU-9's event-state dataset, FU-2's veto replay,
and the parked FU-15 dual-sided bracket. Ledger **44/44 both machines**; every number above
is claim-bound.
