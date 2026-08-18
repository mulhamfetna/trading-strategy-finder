# WS-NEWS3 M3 — the complete experiment log: the straddle dissected leg by leg, second by second

**Date:** 2026-08-16 · **Issue:** #117 (closed), parent #124 · **Companion:** the stage report
`WS-NEWS3-REPORT-M3-the-straddle-verdict.md` carries the verdicts; **this report carries the full
record** — the run inventory, the exact execution model, every one of the 18 cells with both legs
decomposed, the CL inversion, the sparse-bar discovery, the distribution and slippage anatomy of
the winning trade, and the claims that pin it. Everything re-derives from committed files
(`p3_events_{NQ,RTY,CL}.csv`, `p3_result_*.json`, `p3_v1_NQ.json`; ledger `claims_news3.py`
**27/27**; selftest 5/5).

---

## Part 0 — Run inventory

| # | run | outcome |
|---|---|---|
| 1 | pre-registration on #117 | arms, grid, execution model, primary, V1/V2/V3, α budget — fixed before any code |
| 2 | data check | 1-second files confirmed on server for all 9 instruments incl. NQ (7.8 GB), RTY, CL |
| 3 | `--v1`, NQ | **PASS** — 1s pipeline reproduces P1's 1m cell: +$80.80 vs +$84.24, n=574 exact |
| 4 | mains #1: NQ, RTY, CL | gates as final; ⚠️ a TIMING readout in wrong units found in analysis (bars printed as seconds) |
| 5 | timing fix + mains #2 (numbers of record) | exits timestamped in real seconds from the release; all verdicts unchanged |
| 6 | ledger: 3 claims | 27/27 · selftest 5/5 |

No verdict moved between runs 4 and 5 — the fix changed only the *timing* columns; every P&L,
gate, and rate is identical (same events, same fills).

## Part 1 — The trade, mechanically exact

```
universe    NQ, RTY on {CPI MoM, NFP, FOMC}  (M2's power targets; M1's premium lives only here)
            CL on {EIA crude} — the NO-PREMIUM CONTROL INSTRUMENT (⚠️ unverified provenance, #123)
            events matched to 1s bars: NQ 329 · RTY 239 · CL 549 (floors 2016/2019/2016 → 2026-07)
entry       close of the 1-SECOND bar at (release − 300s); entry bar must sit within 60s of that time
arms        STRADDLE = long + short simultaneously (2 legs) · LONG-ONLY = the premium-tilted variant
stops       fill = worse of (stop line, bar open)              [GAP-01]
take-profit resting limit: fill = better of (TP line, bar open)
⚠️ tie rule if ONE 1-second bar breaches BOTH a leg's stop and its TP → counted as STOPPED (pessimistic)
exit        any leg alive at (release + 900s) closes on that bar's close
grid        S ∈ {0.05, 0.10, 0.20}% × TP ∈ {0.20, 0.40, ∞}%  → 9 combos × 2 arms × 3 groups = 54 cells
costs/LEG   $2.50 + {1,2,4} ticks → NQ 7.50/12.50/22.50 · RTY same · CL 12.50/22.50/42.50
            a straddle pays TWO legs (NQ stressed $45/event). STRESSED leads all reporting.
primary     ONE pre-registered test: straddle, S=0.10, TP=0.40, NQ pooled, net stressed > 0, α=0.05
            everything else: descriptive unless it clears α=0.05/54 AND sign-holds on both halves
```

## Part 2 — The gates, with the two discoveries they forced

**V1 — the frame bridge.** The long-only arm (S=0.20%, no TP) on P1's *full five-series* NQ set,
computed from the 1-second file, against P1's 1-minute pipeline: **+$80.80 vs +$84.24** (tolerance
±$15, n=574 exactly). Two data frames, two codebases, one trade — the $3.44 is finer stop-fill
resolution at 1s, in the direction finer resolution should move it. This single check retires the
"is the 1s pipeline aligned/scaled correctly?" class of doubt for everything below.

**V2 — the release-second physics.** Mean fraction of the |move(release → +900s)| already present
at release+60s: **NQ 0.97 · RTY 1.01 · CL 0.91** (RTY > 1 = overshoot-and-retrace). Round 1's
"$132 of $137 inside the minute" reproduced at 1-second resolution, on all three instruments.

**V3 — the structure must NOT pay where there is no release.** NQ control straddle **−$31.44**
(one-sided p=0.99) ✅ · RTY **−$3.63** (p=0.73) ✅ · **CL +$19.12, p=0.002 — FAIL ⇒ CL VOID.**

### 2.1 The CL inversion, dissected (the falsifier earning its keep on the third instrument)

| CL, S=0.10 TP=0.40 | long | short | straddle |
|---|---|---|---|
| EIA releases (n=549) | −$1.69 | −$0.16 | **−$1.85** |
| clean control minutes (n=523) | **+$28.91** | −$9.80 | **+$19.12** |

The control *beats* the release. Reading: CL's ordinary matched minutes carry enough directional
drift/continuation for the asymmetric bracket to harvest, while the EIA minute itself chops the
structure to zero. Whatever that control-side drift is, **it is not news** — so no CL release
result could ever be attributed to the release, which is precisely what VOID means. (And even the
control's +$19 gross is −$66 net of the $85 stressed two-leg cost — dead economically regardless.)
The gate was registered to catch "the pipeline manufactures profit"; what it caught is subtler and
more useful: **on CL the structure's profit source exists everywhere, so the release explains
nothing.**

### 2.2 The sparse-bar discovery (a units lie caught before publication)

Run 4's analysis printed "median time-to-TP 239 s" — impossible, since that precedes the release
at 300 s. The number was 239 **bars**: 1-second files carry bars **only for seconds with trades**,
and the pre-release lull is sparse — NQ has a median **203** traded seconds of the 300, RTY only
**116**. Consequences, now permanent method notes:
- a bar offset in a 1-second file is NOT a duration — always convert through the timestamp;
- RTY's pre-release book is thin (116/300) — its 0.05% stop's 24.8% *pre-release* stop-out rate
  partly reflects sparse-bar jumpiness, worth remembering before quoting RTY microstructure.

## Part 3 — All 18 cells, both legs decomposed (mean $/event; the domination table)

**NQ (329 events, {CPI, NFP, FOMC}):**

| S% | TP% | LONG | SHORT | straddle | both-legs-stopped |
|---|---|---|---|---|---|
| 0.05 | none | +142.66 | −18.54 | +124.12 | 65.4% |
| 0.05 | 0.20 | +81.19 | −31.09 | +50.10 | 48.6% |
| 0.05 | 0.40 | +118.55 | −25.11 | +93.44 | 60.6% |
| 0.10 | none | **+184.28** | −45.71 | +138.56 | 46.2% |
| 0.10 | 0.20 | +102.26 | −59.03 | +43.22 | 24.2% |
| **0.10** | **0.40** | **+155.56** | −60.23 | +95.33 | 39.4% |
| 0.20 | none | +171.55 | −40.10 | +131.45 | 20.5% |
| 0.20 | 0.20 | +102.18 | −115.24 | **−13.06** | 0.9% |
| 0.20 | 0.40 | +163.08 | −101.94 | +61.14 | 12.8% |

**RTY (239 events):** same shape — long +$16.82…+$122.72 (all 9 positive), short −$3.62…−$34.91
(all 9 negative), straddle everywhere below its long leg; S=0.20/TP=0.20 again the worst straddle.

Three structural facts the decomposition makes undeniable:
1. **The long leg is positive in 18/18 cells; the short leg is negative in 18/18.** The straddle
   is a confirmed trade with a confirmed anti-trade stapled to it, plus a second cost.
2. **The short leg's loss GROWS with the stop width** (NQ: −$19 at 0.05% → −$102 at 0.20%/TP 0.40):
   a wide-stopped short survives its sweep and then rides the premium *against* itself for 15
   minutes. The tighter the stop, the cheaper the wrong leg — the owner's "small stop" intuition
   is *correct for the leg that is wrong*, which is exactly why it cannot rescue the pair.
3. **The symmetric 1R:1R bracket (S=0.20, TP=0.20) is the only negative-gross straddle** — with
   both-legs-stopped at 0.9%, it is a pure cost-and-chop donor: symmetric target, symmetric stop,
   asymmetric market.

## Part 4 — The primary as registered, and the honest reading

> **STRADDLE S=0.10 TP=0.40, NQ, net of stressed 2-leg costs: +$50.33/event, t=+1.35, one-sided
> p=0.0897, n=327 → NOT CONFIRMED.** And NOT excluded: the cell's MDE is ≈$104/event, the CI spans
> [−23, +124]. Resolving a true +$50 at 80% power would need ≈4× the events (~40 more years of
> CPI/NFP/FOMC or more instruments) — recorded, not pursued: the domination result makes the
> question moot, since the long leg is available and strictly better in every configuration.

## Part 5 — The trade that IS confirmed (the strict secondary bar), and its full anatomy

Bonferroni α=0.05/54 + sign-consistent chronological halves — met by the LONG arm on both
instruments (NQ S=0.10/TP=0.40 t=4.13; also S=0.20/TP=0.40 t=3.65 and S=0.10/no-TP t=3.41;
RTY S=0.10/TP=0.40 t=3.79, S=0.20/no-TP t=3.58). Falsifiers: the same cell is **negative on
control windows** (NQ −$27.91, RTY −$8.01) and **null on FOMC** (−$4.32), the release M1 showed
carries no premium — this is release-specific and premium-specific, not "any window pays."

**Distribution anatomy (NQ winning cell):** win rate **36.4%**, median **−$136** — even more
tail-driven than P1's ride (the bracket structure concentrates outcomes into −1R/+4R/timed):

| outcome | share | typical |
|---|---|---|
| stopped after the release | 48.6% | ≈ −1R (0.10% ≈ −$476 at 2026 prices) |
| **take-profit +4R** | **22.9%** | ≈ +0.40% |
| timed exit (+900s) | 15.6% | residual drift |
| stopped before the release | 12.8% | −1R, news never seen |

p5 −$444 · p95 **+$1,675** · best **+$2,900 (CPI 2026-07-14)** · worst **−$995 (NFP 2026-03-06)**.

⭐ **The worst loss is ≈2.1× the nominal stop** — that is gap-through-stop slippage, *measured*: the
release second jumped the stop and GAP-01 filled at the traded price, not the line. One number to
carry into any deployment spec: the −1R leg can be −2R on a sweep second.

**Timing (real seconds, run 5):** TP fills at **median +15s** after the print on NQ (p25 +1s, p75
+80s), **+3s** on RTY; ~90% of TPs are post-release (13.3% NQ / 9.8% RTY fired before it — the
pre-release drift occasionally reaches +0.40% on its own). Post-release stops: p25 **+1s**, median
**+3s**, p75 +77s. **Five quiet minutes of waiting, then the trade decides in seconds.**

**Per series (NQ winning cell):** CPI **+$331.52 [+187, +476]**, n=116 · NFP +$100.60 (ns) · FOMC
−$4.32 — the engine is CPI for the third method in a row (M1 1-minute ride, M2 magnitude ranking,
M3 1-second bracket). **Per era:** 2016–19 +$58.95 · 2020–21 +$23.76 · 2022+ **+$291.87** —
positive in all three eras (the registered sign rule), magnitude squarely in the current regime.

**Worth at 1 contract:** NQ ≈ 52 events/yr × net +$133 ≈ **+$6,900/yr**; RTY ≈ +$1,800/yr; the
CPI-only variant concentrates most of it into 12 events/yr.

## Part 6 — The whipsaw table (what the "small stop" really does at the release)

| stop | NQ both-legs-stopped | RTY | reading |
|---|---|---|---|
| 0.05% | **65.4%** | **72.7%** | two of three straddles die on both sides |
| 0.10% | 46.2% | 55.9% | half die twice |
| 0.20% | 20.5% | 31.9% | survivable — but the short leg's loss triples |

Monotone in stop width (the claim's falsifier — a rate indifferent to the stop would have been a
pipeline artefact). The single long leg lives in this same storm and pays anyway, because it only
needs the upside once; the pair pays the sweep twice by construction.

## Part 7 — Claims (ledger 27/27, selftest 5/5)

| claim | pins | V1 | V2 | V3 (falsifier) |
|---|---|---|---|---|
| `P3-STRADDLE-NOT-CONFIRMED` | +50.33 | primary re-derived from per-event file | long dominates 18/18 by independent aggregation | **the machinery CAN confirm** — long cell t>3.28 on identical events |
| `P3-LONG-RELEASE-TRADE-CONFIRMED` | +155.56 | clears α/54 + half-sign from raw events | RTY clears the same bar on its own file | **controls negative AND FOMC null** |
| `P3-WHIPSAW-MEASURED` | 0.654 | rates re-derived from raw events | RTY same magnitude | **monotone in stop width** |

Blind spots declared in code: fills inside the release second assume line-or-open execution on
1-second bars (sweep slippage beyond the stressed 4 ticks — and beyond the measured 2.1× worst
case — is invisible); structures outside the grid (stop-and-reverse, laddered TPs) untested;
era concentration pinned via the halves rule only.

## Part 8 — Threats that remain

1. **Regime dependence** — the magnitude lives in 2022+; the sign held in 2016–19 but at $59, not
   $292. Any deployment carries the rolling-CPI-mean alarm (M4's packet).
2. **Execution realism** — median TP at +15s and stops at +3s mean the entire economic event
   happens in the most contested seconds of the day. The measured 2.1× worst-case stop slippage is
   a floor on realism, not a ceiling.
3. **No quantity term in the engine** — nothing here can trade a single extra contract until the
   sizing/multi-leg decision is made (owner's, standing).
4. **n=116 CPI events** carries the confirmed cell's economics; a 2-year CPI regime change moves it.

## Part 9 — What went well / what went wrong

**Well:** testing the owner's structure *exactly as proposed* — and letting it fail its registered
primary — is what makes the long-leg confirmation credible: same events, same machinery, stricter
bar. The leg decomposition turned "the straddle underperforms" into a mechanism (a confirmed trade
+ its anti-trade + a second cost). The falsifiers did real work on every instrument: NQ/RTY's
controls certified the effect, CL's control *voided* an instrument, and the whipsaw monotonicity
certified its own measurement.

**Wrong, kept visible:** the timing readout shipped to logs in wrong units (bars ≠ seconds in a
trade-sparse file) — caught in analysis before any report carried it, fixed with the reason in
code; and the registered primary's arm was knowably the weaker hypothesis going in (registered
anyway because it was the owner's actual proposal — the right call, recorded as a tension rather
than smoothed over).

## Part 10 — Where this leaves the workstream

**The experimental programme is COMPLETE.** Every clause of the restated goal now has a measured
answer (M0 audit → M1 ride/drift → M2 power model → M3 structure). What remains is **M4 — the
closeout**: no new experiments; the final report, the owner decision packet (sizing/multi-leg
engine change; monitoring rule; the confirmed spec: long, release−300s, S=0.10%, TP=0.40%, on
{CPI, NFP} with CPI carrying the economics), and the memory/board close.
