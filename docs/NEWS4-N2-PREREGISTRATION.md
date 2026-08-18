# WS-NEWS4 / N2 pre-registration — the wide-series premium scan (#136)

**Filed BEFORE any scan runs** (commit date = filing date). Same discipline as M3/RTY (#126):
the tests, thresholds, and corrections below are frozen; anything not listed here that we
later compute is exploratory and will be labeled so. `expect` values are never adjusted.

## Question

Does the confirmed announcement-premium ride pay on release moments the funnel never tested?
The ride needs only timestamps, so the consensus-provenance restriction that produced the
original 5-series funnel does not apply.

## Frozen trade spec (inherited verbatim from #117 / the deployed executor — no re-tuning)

LONG at release−300 s · stop 0.10 % (worse-of line/open, GAP-01) · TP 0.40 % (resting limit,
better-of) · tie inside one 1 s bar ⇒ STOP · timed exit at release+900 s · **stressed costs
($22.50/leg NQ, RTY per its table) lead all reporting**. Instruments: **NQ and RTY** (the
deployed pair). Window: **2016-01-01 → data end** (pre-2016 calendar DST-broken). Any change
to these constants is a different study and must be declared as such.

## Scan unit

The **release moment** (minute-deduped), from the N1 machinery (`news4_n2_moments.csv`
logic recomputed per block at run time), with two exclusions:

1. **Covered-minute exclusion** — minutes containing any premium-tested series
   (CPI, NFP, FOMC, Retail, Durables, EIA-crude, API) are evidence already; excluded.
2. **Window-overlap exclusion (NEW, stricter than N1)** — a moment is excluded if its
   [rel−300 s, rel+900 s] window intersects the window of ANY deployed-set event that day
   (e.g. a 12:15 ADP ride would still be open at a 12:30 CPI print — that observation
   would contaminate both).

**Title-rename merges** (same series, renamed by the source): ISM Non-Manufacturing PMI ↔
ISM Services PMI · Markit ↔ S&P Global PMI · Jobless Claims 4-Week ↔ 4-week Average ·
Baker Hughes Total Rig ↔ Rigs Count · Personal Income (MoM) ↔ Personal Income MoM ·
Building Permits ↔ Building Permits Prel/Final chains. Merges are by title map, applied
before block assembly.

## Tier 1 — confirmatory family (pre-registered; Bonferroni across ALL of it)

Chosen on three declared criteria, before looking at any outcome: (a) prior-art support
(Savor–Wilson's original set included **PPI**; pre-announcement drift documented for
GDP/ISM; ex-ante event premiums documented beyond the big three), (b) n ≥ 40 usable
moments, (c) SCHEDULED-PRINT timestamp quality (no speeches).

| # | block (anchor series) | UTC | approx. clean moments |
|---|---|---|---|
| 1 | Initial Jobless Claims (Thu block) | 12:30 | ~438 |
| 2 | PPI MoM | 12:30 | ~120 |
| 3 | Core PCE Price Index MoM (Personal Income/Spending block) | 12:30 | ~120 |
| 4 | GDP Growth Rate QoQ Adv | 12:30 | ~42 |
| 5 | ISM Manufacturing PMI | 14:00 | ~128 |
| 6 | ISM Services PMI (incl. Non-Mfg rename) | 14:00 | ~128 |
| 7 | JOLTs Job Openings | 14:00 | ~128 |
| 8 | Michigan Consumer Sentiment Prel | 14:00 | ~128 |
| 9 | ADP Employment Change | 12:15 | ~126 |
| 10 | FOMC Minutes | 18:00 | ~86 |

**20 confirmatory tests** (10 blocks × 2 instruments). **α = 0.05/20 = 0.0025 per test**
(Bonferroni across the whole confirmatory family).

### Primary statistic and PASS definition (per block × instrument)

- Statistic: mean **net-stressed** $/event of the frozen ride; two-sided one-sample t-test
  vs 0.
- **CONFIRMED premium** requires ALL of:
  1. t-test p < 0.0025 with positive mean (net stressed);
  2. **half-split**: split the block's moments chronologically in half — both halves'
     gross means positive;
  3. **quiet-minute control**: the same clock-time entry on days with NO release within
     ±30 min (checked against the FULL 39k calendar) must NOT itself pass (1) — and the
     block's mean must exceed the same-clock-time seasonality floor (the M1 8:30-floor
     method, computed per clock time);
  4. **noise check**: 1,000 shuffled-date placebos; the observed mean above the 99th
     percentile.
- **POWERED NULL** (the only allowed negative verdict): fails (1) AND the block's minimum
  detectable effect (MDE, 80 % power at α=0.0025) is ≤ $150/event — i.e. we could have
  seen a deployment-relevant premium and did not.
- **UNDERPOWERED** : fails (1) and MDE > $150/event — verdict is "cannot tell", never "no".
- **VOID-TIMESTAMP**: before any premium verdict, the block must pass the V2 jump gate —
  release-minute |open→close| exceeds its quiet control by > 1.2× (median). A block that
  fails carries suspect timestamps (the auction-time trap); its premium result is VOID,
  not negative.

## Tier 2 — exploratory sweep (descriptive only)

Every remaining moment group with ≥ 40 clean moments (~82 groups: auctions, MBA, Redbook,
Baker Hughes, EIA natural gas, regional Fed indices, Fed speeches…). Same ride, same
statistics, reported with **Benjamini–Hochberg FDR (q = 0.10)** and labeled EXPLORATORY.
Nothing in Tier 2 can be called confirmed in this study: any survivor is promoted to its
own follow-up pre-registration on data/eras it has not consumed. Speech blocks additionally
carry a ±120 s timestamp-fuzz sensitivity run; if the result flips sign under fuzz it is
VOID-TIMESTAMP.

## Declared blind spots (V3 habit)

1. **Timestamp provenance is TradingView's alone** for series beyond the 4 ALFRED-verified
   ones — the V2 jump gate is the only defense; a systematically shifted (not just noisy)
   timestamp that still jumps within the minute would mis-anchor the entry by up to 59 s.
2. **Era concentration**: the confirmed {CPI,NFP,FOMC} premium is 2022+-heavy. A Tier-1
   pass driven entirely by 2022+ is still a pass (half-split only requires sign), but the
   era table is reported and a 2022+-only premium is flagged for the regime monitor.
3. **Multiplicity across instruments is handled, across FUTURE re-runs it is not** — if
   this scan is ever re-run with different blocks, the ledger must count both runs.
4. **The $150/event MDE line is a judgment call** (≈ the deployed NQ net premium level);
   declared here so it cannot drift after results are seen.

## Mechanics

- Implementation: `news4_premium_scan.py` reusing the executor's loader/bracket
  (`src/deploy/release_executor.py` — the parity-proven fill model), not a re-implementation.
- Runs on the server (`~/Mulham/earn1`), 1 s frames; outputs scp'd back and committed.
- V1/V2/V3 + claims-ledger entries (`optimize/verify/claims_news4.py`) before any number
  is published. Every step posted to #136 as it happens.
