# WS-NEWS3 M2 — the complete experiment log: the power model, its two honest failures, and the regime underneath

**Date:** 2026-08-16 · **Issue:** #126 (closed), parent #124 · **Companion:** the stage report
`WS-NEWS3-REPORT-M2-the-power-model.md` carries the verdicts; **this report carries the full
record** — every run, every gate line on every instrument, the two failure post-mortems, the
regime anatomy the failures exposed, and two analyses that exist only here: the CPI regime
trajectory year by year, and the model's **operational today-values** (which reorder the headline
table). Everything re-derives from committed files (`p2_power_events_*.csv`, `p2_power_rank_*.csv`,
`p2_power_result_*.json`, incl. `_t24` variants; ledger `claims_news3.py`, **24/24**; selftest 5/5).

---

## Part 0 — Run inventory

| # | run | outcome |
|---|---|---|
| 1 | pre-registration filed on #126 | grid, primary, V1/V2/V3, control — all fixed before any code ran |
| 2 | primary (expanding median), NQ/ES/GC/CL/RTY | primary PASS 5/5 · V3 PASS 5/5 · control PASS 5/5 · **V1 FAIL on NQ** · **V2 FAIL on NQ/ES** |
| 3 | diagnosis from committed outputs | the two failures share one root: regime lag; plus the V2 anchor named the wrong quantity |
| 4 | trailing-24 variant (declared post-hoc, same gates), 5 instruments | ρ up everywhere, NQ V1 cured (+0.70 → +1.00) |
| 5 | ledger: 3 claims | one V1 *check* itself defective on first write (row-count proxy) — rebuilt, expect untouched, 24/24 |

## Part 1 — The model, exactly

```
P_hist(event e of series s on instrument i)
    = median of jump_pct over the PRIOR releases of (s, i)     ← shifted: never sees event e
      jump_pct = |Close − Open| / Open × 100 of the release bar (1-minute frame)
      expanding window (pre-registered primary)  /  last-24 window (declared variant)
      ≥ 8 prior releases required, else the event is EXCLUDED FROM SCORING (counted: 40 of 574 on NQ)
```

Deliberately the dumbest defensible model — nothing to overfit, nothing tuned. Universe: the P1
series sets (NFP, CPI MoM, Retail Sales, Durables + FOMC; + EIA/API on CL, unverified-marked),
per-instrument floors, data through 2026-07. Secondary feature tested as an add-on: |forecast −
previous|, z-scored within series (expanding, shifted).

## Part 2 — Run 2, every gate on every instrument (the record)

| gate | NQ | ES | GC | CL | RTY |
|---|---|---|---|---|---|
| **primary** ρ(P_hist, jump) OOS | **+0.530** [+0.466,+0.589] | **+0.515** [+0.450,+0.575] | **+0.472** [+0.403,+0.536] | **+0.546** [+0.508,+0.583] | **+0.582** [+0.511,+0.645] |
| n scored | 534 | 534 | 531 | 1,349 | 378 |
| resolution-window variant | +0.404 | +0.392 | +0.360 | +0.376 | +0.403 |
| V1 quintile means (low→high) | .047 .099 **.297 .269** .289 → +0.70 ⛔ | .039 .076 .224 .224 .230 → +0.90 ✅ | monotone → +1.00 ✅ | .071….463 → +0.90 ✅ | monotone → +1.00 ✅ |
| V2 top-2 by predicted power | NFP, FOMC ⛔(anchor said CPI) | FOMC, NFP ⛔ | NFP, FOMC ✅ | **EIA, API** ✅ | NFP, **CPI** ✅ |
| V3 shuffle: median / p95 / observed | +.120 / +.168 / **+.530** ✅ | +.076 / +.122 / **+.515** ✅ | −.015 / +.047 / **+.472** ✅ | +.097 / +.127 / **+.546** ✅ | +.194 / +.240 / **+.582** ✅ |
| control (no-news minutes) | +0.117 ✅ | +0.041 ✅ | −0.042 ✅ | +0.109 ✅ | +0.097 ✅ |
| secondary \|f−p\| on residual | −0.003 (p=.95) | −0.008 (p=.85) | −0.078 (p=.08) | **−0.084 (p=.003)** | −0.046 (p=.41) |

Readings:
- **The primary criterion (every equity CI-lo > 0) passed everywhere**, and the two falsifiers that
  could have voided it did their work honestly: shuffled series labels retain only ρ ≈ 0.1 (that
  residue is real volatility clustering — the shuffle *quantifies* it instead of letting it
  masquerade as skill), and no-news minutes retain ≤ +0.15.
- **The secondary is a clean kill**: |forecast − previous| adds nothing anywhere; the single
  significant value (CL −0.084) is *negative* — a bigger anticipated change predicts, if anything,
  a slightly *smaller* residual move. With H1-B/C (direction) and this (size), **the consensus
  numbers are now fully dead as pre-release inputs** — the model needs only the series' own tape.

## Part 3 — Failure post-mortem #1: V2 on NQ/ES was MY error, and the model was right

The registered anchor: *"CPI must rank top-2 predicted power for NQ/ES/RTY."* It failed on NQ/ES —
and the failure indicts the anchor, not the model. M1 ranked **premium** (signed $ P&L of a long
ride); M2 ranks **power** (unsigned |move|). Those are different physical quantities, and by power
the model's answer — NFP and FOMC on top — is the textbook-correct one (NQ realized medians: NFP
0.178%, FOMC 0.135%, CPI 0.188% *mean-tail-driven* with a lower median in full-sample view).

> ⭐⭐ **POWER ≠ PREMIUM — now a design principle.** NFP/FOMC: biggest movers, ~zero/negative
> premium. CPI: third-biggest mover by full-sample median, the ONLY meaningful premium (+$424/event
> NQ). A release-selection filter needs both columns: |move| decides whether the prize clears the
> cost floor; premium decides whether any leg deserves a tilt.
>
> ⭐ Registration rule extracted: **when registering an anchor, name the quantity it ranks, and
> check that the anchor's source measured the SAME quantity.** The gate stays FAILED in the record.

## Part 4 — Failure post-mortem #2: V1 on NQ exposed the regime lag (and became a claim)

NQ's quintile means invert at the top (Q3 .297 > Q4 .269): CPI events sit in *mid* prediction
buckets but realize *top-tier* moves. The mechanism, pinned as `P2-REGIME-LAG` (expect 4.155):

| NQ, expanding model | predicted med | realized med | ratio |
|---|---|---|---|
| CPI | 0.0451% | 0.1875% | **4.16× — the lag** |
| NFP (stable power) | 0.1336% | 0.1782% | **1.33× — no lag** (this contrast is the claim's V3) |

### The regime itself, year by year (NQ CPI realized median |move|%):

| 2016 | 2017 | 2018 | 2019 | 2020 | **2021** | **2022** | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| .021 | .041 | .140 | .061 | .026 | **.298** | **1.441** | .430 | .383 | .516 | .292 |

The break is at **2021**, the peak **2022 (1.44% — seventy times the 2016 median)**, and 2023–2026
still run **5–15× the old regime**. An expanding median that includes 2016–2020 *must* under-predict
this — the lag is arithmetic, not mystery. It is the same regime M1's premium lives in, seen from
the magnitude side.

## Part 5 — The declared variant: trailing-24, same gates, reported beside the primary

| instrument | primary ρ | **trailing-24 ρ** | V1 quintiles | V3 / control |
|---|---|---|---|---|
| NQ | +0.530 | **+0.591 [+0.533,+0.643]** | .041 .110 .129 .246 .475 → **+1.00 ✅ (cured)** | ✅ / ✅ |
| ES | +0.515 | **+0.572** | +1.00 ✅ | ✅ / ✅ |
| GC | +0.472 | **+0.493** | +1.00 ✅ | ✅ / ✅ |
| CL | +0.546 | +0.546 | +1.00 ✅ | ✅ / ✅ |
| RTY | +0.582 | **+0.618** | +0.90 ✅ | ✅ / ✅ |

CPI lag: NQ 4.16× → 2.73×; **RTY 1.04× — closed** (its 2019+ history carries no stale weight).
Residual honesty: trailing-24 on a monthly series is a two-year window; it still lags a fast regime
by up to that much (in the claim's blind-spot field). The variant was declared post-hoc with its
motivation committed BEFORE its first run, and the pre-registered primary keeps primacy in every
claim.

## Part 6 — ⭐ The operational table (new here): what the model says TODAY

Full-sample tables answer "was the model right on average." M3 trades **next month**, so the value
that matters is the *latest* trailing-24 prediction per series — and it reorders the headline:

| release | NQ (as of 2026-07/08) | RTY | CL |
|---|---|---|---|
| **CPI** | **0.334% — #1** | **0.784% — #1** | 0.081% |
| NFP | 0.185% | 0.375% | 0.104% |
| FOMC | 0.170% | 0.309% | 0.081% |
| EIA crude | — | — | **0.153% — #1** ⚠️unverified |
| Retail Sales | 0.028% | 0.078% | 0.045% |
| Durables | 0.022% | 0.035% | 0.057% |
| API crude | — | — | **0.036% — collapsed to last** ⚠️unverified |

- **In the current regime CPI is BOTH the most powerful release on the indices AND the only one
  with a premium** — the full-sample "NFP first" ranking was an average over dead eras. (This is a
  descriptive read of the same committed data, not a new inference; no gate was re-scored.)
- ⚠️ **API's power has collapsed** (0.036%, last place on CL) — the S4 drift survivor's underlying
  event barely moves the market *today*. One more reason #123's "do not chase it" stands.
- Concrete scale for M3: RTY CPI 0.784% of ≈ 2,300 ≈ 18 points ≈ **$900 expected |move| per
  contract** inside the release minute, against a $12.50 realistic / $22.50 stressed cost floor.

## Part 7 — The ledger, including the check that was itself defective

3 claims: `P2-POWER-MODEL-CONFIRMED` (0.530) · `P2-FP-ADDS-NOTHING` (0 instruments where it helps;
null powered to ρ≈0.16) · `P2-REGIME-LAG` (4.155; V2 = the cure works, V3 = NFP shows no lag).

⚠️ Kept visible: `P2-FP-ADDS-NOTHING`'s first V1 compared row *counts* across two different filters
(rows having |f−p| = 533 vs rows also having a valid z-score = 493) and failed — **a defect in the
check, not the claim**. Rebuilt to re-derive the actual statistic (matches to 1e-6, n exactly);
`expect` untouched; the reason recorded in code. Same lesson as V2 at smaller scale: **a
verification instrument must measure the same quantity as the thing it verifies.**

## Part 8 — Threats that remain

1. **Within-series timing is unmodeled** — the model ranks releases; it cannot say *which* CPI day
   will be the big one (M1's distribution: that single day carries the year).
2. **Shared infrastructure blind spot** — one calendar, one prediction implementation, five
   instruments; a defect there is invisible to every cross-instrument check.
3. **Two-year window lag** — a regime that ends in 2027 would be over-predicted into 2028.
4. **CL's EIA/API rows remain provenance-unverifiable** (#123) — marked in every output.

## Part 9 — What went well / what went wrong

**Well:** pre-registration converted both gate failures into the stage's two most valuable
products (power≠premium; the regime-lag claim); the dumbest-defensible-model choice left nothing
to overfit and still delivered ρ ≈ 0.5; the falsifier *quantified* the vol-clustering alternative
(ρ ≈ 0.1) instead of merely rejecting it.

**Wrong, kept visible:** the V2 anchor named the wrong quantity (mine); one verification check was
built on a proxy (row counts) instead of the statistic (mine); both corrected same-day with reasons
in code and issue thread, no expect adjusted.

## Part 10 — Hand-off to M3 (#117)

The straddle test inherits, from measurement rather than intuition: **targets** = CPI, NFP, FOMC on
NQ/RTY (+ EIA on CL as the no-premium control); **tilt** = long only where the premium is (CPI);
**prize estimates** = Part 6's operational table; **entry lead** = minutes, not an hour (H1-A);
**threat model** = both-legs-swept whipsaw (94% of stop-outs are 1-second sweeps) measured on
1-second bars, stressed costs leading, pessimistic same-bar stop-vs-TP resolution.
