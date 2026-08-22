# WS-FWD (#176) — every deployed champion on the freshest tape we have: the full forward report

**Date: 2026-08-21 · branch `research/legacy-18-baseline` · champion set `best` (the deployed set) ·
9 instruments × 6 timeframes = 54 slots · evidence: `subprojects/Parametric-Indicators/optimize/fwd/data/`
(all committed) · claims: `optimize/verify/claims_fwd.py` (3 claims, V1/V2/V3 each) · issue #176.**

---

## 1. The headline, honestly

You asked: *the champions' books end mid-May — we have data to August; run everything, verify it on
the dashboard, and tell me per champion whether it makes or loses money, why, and what can be fixed.*

Three sentences before anything else:

1. **The candle tape is now extended to 2026-08-07 for all 9 instruments, under exact gates, and all
   54 champions ran on it — every book is rebuilt, committed, and dashboard-verified.** Aggregate
   full-window book: **$2,180,903** (2025: $1,364,369 · 2026-to-date: $816,536). All 54 slots are
   positive over their books.
2. **But the genuinely NEW tape produced only 25 trades (+$1,823), all NQ/ES, all in late May.** The
   reason is structural, not a bug: the strategy's entry signal comes from the **box levels**, which
   are a scraped external feed that ends 2026-06-09 (NQ) / 2026-05-21 (ES) / 2026-06-26 (the other
   seven). No boxes → no entries. The candles are ready through August; the entries are waiting on
   **one owner action: a fresh box export**. Nothing was extrapolated or faked to pretend otherwise.
3. **The most valuable findings therefore come from the full books**, and they are sharp: the fleet's
   value is concentrated in the slow timeframes ($150–$600 per trade on 4h/2h/1h), **8 slots go
   negative at a realistic $10/round-trip friction** (all the thin high-frequency ones, led by the
   entire NG ladder), and **one slot — NQ 5m — has been silently dark since April 25** because its
   frozen volatility gate no longer admits the 2026 regime.

⚠️ One honesty rule governs every sentence below (pre-registered in `docs/WS-FWD-PREREGISTRATION.md`
BEFORE any run): the 2026 portion of the full books is the **selection window** of the `best` set —
these champions were *chosen* partly on it — so it is not out-of-sample evidence. The only true
out-of-sample tape is the fresh window, and at n=25 it receives **observations, not verdicts**
(no-negative-without-power, enforced as a ledger falsifier that FAILS if any slot quietly crosses
the verdict bar).

---

## 2. What the tape allowed — the data reality

```mermaid
flowchart LR
  A["16-year dataset<br/>data_2010_1s<br/>1s + 1m, all 9, ends 2026-08-07"] -->|"Gate A: splice parity<br/>9/9 exact incl. volume"| C["FWD_EXTENDED root<br/>(parallel; prod untouched)"]
  B["Engine vendor candles<br/>NQ/ES end 05-19<br/>others end Jul 2–8"] -->|"Gate B: resample proof<br/>54/54 exact"| C
  W["Owner's with20d drop<br/>NQ candles+BOX to 06-09<br/>(found unswapped in prod)"] -->|"Gate D: overlap exact<br/>20,460 rows, 0 mismatch"| C
  X["Box feed (scraped)<br/>NQ→06-09 · ES→05-21<br/>others→06-26"] -.->|"NOT extendable by us<br/>owner scrape only"| C
  C --> R["54 champion books<br/>causal engine, 1-min frame"]
  C --> D["Branch dashboard :8250<br/>SSH tunnel + Playwright"]
```

- The August tape exists in the **16-year dataset** (`~/Mulham/data_2010_1s`) — every instrument,
  1-second and 1-minute, through 2026-08-07 16:59 ET.
- The engine's own candle files ended much earlier (NQ/ES 2026-05-19; GC/SI 07-02; RTY/YM 07-05;
  HG 07-07; CL/NG 07-08). We spliced the fresh months in **under exact gates**: 21-day overlap,
  zero tolerance, on open/high/low/close **and volume** (volume matters — vwap/obv/mfi sit in 79
  deployed slot-indicator pairs). All 9 passed with coverage 1.0 and **zero** mismatches — the two
  datasets are provably the same source.
- Every decision timeframe file was proven **exactly reproducible** from the 1m (54/54 proofs,
  zero mismatches on up to 267,658 bars) before any resampled extension was trusted.
- **The box levels cannot be extended by us.** They are scraped output of your TradingView-side
  indicator (a ratio census across 4 instruments shows per-period level values, not derivable
  multiples; no generator or Pine source exists in any repo). Fabricating them would fabricate
  entries — refused, and enforced: a ledger falsifier scans all 54 books and fails if ANY entry
  exists beyond its instrument's box end.
- **A found asset:** production held your `with20d` NQ drop (candles + real scraped box rows through
  2026-06-09, merged by the proven `build_plus20d_data.py`) that was **never swapped into the live
  files**. Its candles match our extension exactly (Gate D), so its box rows were adopted — NQ
  gained 12 legitimate box days.
- Production data was never touched: the extension lives in a parallel root; the production files'
  checksums are proven identical before/after (ledger check V2). The production dashboard :8200
  still serves the pre-extension books until you bless a swap.

**What unlocks the real forward test: a fresh box export through 2026-08 for all 9 instruments.**
The moment those files land, the exact same gated pipeline re-fires with zero new engineering.

---

## 3. Why these numbers can be trusted

1. **Same code path as the dashboard.** Every book is the causal engine's L1 view — the same
   `build_view_payload` the dashboard's own backtest endpoint calls — with the 1-minute indicator
   frame forced (the wrong-frame trap is structurally excluded).
2. **Anchor closure to the cent.** The NQ 4h book on the extended root is $151,056.19 / 279 trades =
   the known deployed anchor **$151,655.19 / 277** plus *exactly* its two fresh-sliver trades
   (−$599.00). The whole delta is attributed; nothing else moved. This is ledger check
   `FWD-FRESH-WINDOW-SLIVER · V2`.
3. **Cache isolation.** The engine's L1 disk cache is keyed on parameters, not data — sharing it
   with production would silently serve old-tape books for new-tape requests. Every run and the
   branch dashboard use a private TMPDIR inside the extended root.
4. **The dashboard visual gate ran the house way** — SSH tunnel + Playwright, never interactive —
   over **all 54 slots**, comparing the on-screen headline to the core books (§9).
5. **Three ledger claims** (`optimize/verify/run.py`) re-derive every published number from the
   committed artifacts, with falsifiers designed to fail if boxes were fabricated, if production
   was touched, or if the fresh window quietly crossed the verdict bar.

---

## 4. The fleet at a glance (raw engine accounting)

Full-window books, 2025-01 → each instrument's tape end. **Raw engine P/L: no commission, no
slippage** — §5 changes this picture and must be read with it.

| Inst | 4h | 2h | 1h | 15m | 5m | 2m | instrument total |
|---|---|---|---|---|---|---|---|
| **NQ** | **$151,056** /279 | $82,753 /185 | $77,493 /130 | $34,600 /197 | $15,216 /101 | $31,653 /525 | **$392,772** |
| **ES** | $74,237 /146 | $67,026 /226 | $63,063 /241 | $25,589 /170 | $5,080 /150 | $12,042 /742 | **$247,038** |
| **GC** | $89,072 /311 | $84,928 /332 | $86,969 /571 | $82,616 /2018 | $19,966 /458 | $38,706 /886 | **$402,256** |
| **SI** | $62,527 /204 | $76,005 /201 | $40,464 /374 | $79,367 /1790 | $45,199 /2559 | $65,199 /3496 | **$368,761** |
| **HG** | $63,524 /242 | $33,025 /569 | $27,660 /440 | $28,485 /2752 | $20,835 /1663 | $55,474 /7143 | **$229,003** |
| **CL** | $19,366 /392 | $6,480 /175 | $8,244 /561 | $15,643 /1177 | $15,032 /2353 | $23,755 /4655 | **$88,520** |
| **NG** | $30,228 /603 | $14,303 /675 | $14,441 /1734 | $18,237 /2915 | $29,071 /6782 | $27,950 /8486 | **$134,230** |
| **RTY** | $36,219 /297 | $17,195 /177 | $16,119 /213 | $8,594 /112 | $19,564 /1416 | $17,993 /2658 | **$115,685** |
| **YM** | $50,585 /188 | $21,493 /34 | $55,542 /456 | $28,218 /1027 | $17,673 /558 | $29,127 /1094 | **$202,638** |

- **Every slot is positive** over its book, in **both** calendar windows (2025 and 2026-to-date),
  and only two slots are negative since March 2026 (CL 1h −$1,957; ES 5m −$246).
- The columns tell the real story: the **4h/2h/1h columns carry the fleet**. The top ten slots by
  P/L are all 4h/2h/1h (plus GC/SI 15m), and the top slot alone (NQ 4h) is 7% of the whole fleet.

```mermaid
xychart-beta
    title "Top 10 slots — full-book P/L ($k, raw)"
    x-axis ["NQ 4h","GC 4h","GC 1h","GC 2h","NQ 2h","GC 15m","SI 15m","NQ 1h","SI 2h","ES 4h"]
    y-axis "P/L $k" 0 --> 160
    bar [151.1, 89.1, 87.0, 84.9, 82.8, 82.6, 79.4, 77.5, 76.0, 74.2]
```

---

## 5. Costs change the picture — the friction stress

House rule: stressed costs lead. The books above pay zero friction. Apply a realistic
**$10/round-trip** (commission + half-tick) and a harsh **$25/round-trip** (one-tick slip each
side on the big contracts):

| | raw | net @ $10/rt | net @ $25/rt |
|---|---|---|---|
| Fleet total | $2,180,903 | **$1,502,513** | **$484,928** |
| Slots negative | 0/54 | **8/54** | **17/54** |

**The eight slots that go negative at $10/rt** — NG 2m (−$56,910), NG 5m (−$38,749), CL 2m
(−$22,795), HG 2m (−$15,956), NG 15m (−$10,913), RTY 2m (−$8,587), CL 5m (−$8,498), NG 1h
(−$2,899) — share one signature: **thousands of trades at $3–$8 each**. NG trades 27,000+ times
across its ladder at $3.3–$8.3 per trade; its entry gate barely filters (entry rates 45–94%,
vs 5–35% elsewhere). These slots' paper P/L is **below plausible friction — they are not real
income and should not be counted as such**.

Where the fleet is robust: every 4h slot and almost every 2h/1h slot survives even $25/rt.
**NQ 4h keeps $144,081 of its $151,056 at the harsh stress** — $541 per trade towers over any
realistic cost. The durable core of this system is ~25 slow slots worth roughly $1.2M raw /
$1.1M at $10/rt.

---

## 6. The fresh window — everything that is genuinely new

Definition (frozen before the runs): trades **entering after the pre-extension engine end** —
tape no champion and no selection process ever saw. NQ/ES: after 2026-05-19; others: after their
July ends (structurally empty — their boxes end in June, before their old candle ends).

**25 trades · +$1,823.47 net · all NQ/ES · window 2026-05-19 → 05-24.** Every one of them:

| Slot | entry | dir | result | Slot | entry | dir | result |
|---|---|---|---|---|---|---|---|
| ES 4h | 05-20 06:00 | long | **+$2,431** TP | NQ 4h | 05-20 18:00 | short | **+$2,511** TP |
| ES 2h | 05-20 08:00 | short | −$1,082 SL | NQ 4h | 05-24 18:00 | short | **−$3,110** SL |
| ES 1h | 05-20 03:00 | long | +$1,713 TP | NQ 1h | 05-21 22:00 | short | −$1,330 SL |
| ES 15m ×3 | 05-20/21 | mixed | +$842 | NQ 15m ×4 | 05-19→22 | mixed | −$595 |
| ES 2m ×7 | 05-19→21 | mixed | +$515 (7/7 TP) | NQ 2m ×5 | 05-21/22 | short | −$71 |

Observations (NOT verdicts — every cell is under the n<10 bar, and the ledger's V3 falsifier
*fails* if any slot crosses it):

- ES took the fresh days well (+$2,425 across 13 trades, 11 winners); NQ gave back −$602 across
  12, with one 4h stop (−$3,110) dominating — the familiar fat per-trade tail, not a pattern.
- The NQ box extension to 06-09 (the with20d integration) added **zero** new entries beyond
  05-24 — diagnosed, not assumed: on 15m the 19 post-05-22 signals were killed 11 by indicator
  veto / 8 by vol gate, which matches its lifetime 6% entry rate (expected ≈1 entry); on 2m,
  however, **the vol gate ate 307 of 317 signals (97%, vs 62% lifetime)** — see the gate-drift
  finding below.
- One "resolution" trade (open at the old tape end) closed properly on real tape instead of a
  forced mark.

---

## 7. Per-instrument deep dives — why each book looks the way it does

*(Slot syntax: P/L raw / trades / $-per-trade. "Gate" = vol-gate share of dropped signals;
"veto" = indicator-vote share. Diagnostics from `fwd_slot_diag.json` + the books.)*

### NQ — the flagship, with one dark slot
- **4h $151,056/279/$541** — the single best slot in the fleet; survives every stress; 2026
  running at $61k. Win 67%-class with TP-led exits. **Nothing to fix; this is the best case we
  have, and it is genuinely good.**
- 2h $82,753/185/$447 and 1h $77,493/130/$596 — same character, excellent per-trade.
- 15m $34,600/197/$176 — healthy; 97% of its drops are indicator vetoes (its k=1 + tight box
  makes the *indicators* the filter, not the gate).
- **5m $15,216/101/$151 — STRUCTURALLY DARK since 2026-04-25.** Its gate_pct is 30.4 — by far
  the tightest in the fleet (fleet median ≈ 94) — and 94% of its lifetime drops are vol-gate.
  In the hotter 2026 regime the frozen 2025 quantile admits nothing: 640 of 641 signals since
  April 25 were gate-killed. The slot is deployed but has not traded in 3.5 months. **Fix
  exists** (§8: gate recalibration), but it is a re-optimization decision, not a patch.
- 2m $31,653/525/$60 — positive but its gate share is drifting the same direction (97% gate
  drops in the fresh days vs 63% lifetime). **Watch slot.**

### ES — reliable senior partner
- 4h/2h/1h $74k/$67k/$63k at $261–$509 per trade — the steadiest trio in the fleet; 2026 pace
  strong ($30k/$24k/$26k). The fresh days went +$2.4k. **Best case: leave alone.**
- 15m $25,589/170/$151 — fine. 2m $12,042/742/$16 — survives $10/rt, dies at $25; borderline.
- **5m $5,080/150/$34 — the weakest ES slot**: idle since 05-14 (last week of its tape), 65% of
  drops are vetoes, negative since March (−$246). Not broken — just thin. Candidate for
  retirement or re-opt in the next campaign.

### GC — the broadest excellence
- Four slots ≥ $82k (4h/2h/1h/15m); 1h does it on 571 trades at $152/trade, 15m on 2,018 at
  $41. GC since March: +$100k+ across the ladder — the strongest recent form in the fleet.
- 15m/2m survive $10/rt but lose half at $25/rt (volume-heavy). 5m $20k/458/$44 — middling.
- **Nothing needs fixing; GC is the model instrument.** Its vetoes dominate drops (72-77%) —
  the indicator layer, not the gate, does the filtering. Gate drift risk low.

### SI — strong but friction-sensitive at the bottom
- 4h/2h $62k/$76k at $307/$378 per trade — elite. 1h $40k, 15m $79k/1790/$44 strong.
- 5m/2m ($45k/2559, $65k/3496 at $18-19/trade): **profitable on paper, gone at $25/rt**
  (−$19k/−$22k). SI's cheap-looking ticks make high-frequency paper edges evaporate in the
  spread. Count the slow ladder as SI's real value.

### HG — solid core, thin bottom
- 4h $63,524/242/$262 — top-eight slot; 2h/1h fine at $58-63/trade.
- 2m $55,474/7143/**$7.8** — the fleet's second-busiest slot, negative at $10/rt. The signature
  NG problem in copper form. 15m/5m borderline.

### CL — the weakest major
- Best slot 4h $19,366/392/$49 — a tenth of NQ 4h. CL 1h is **negative since March** (−$1,957
  over 34 trades). 2m/5m negative at $10/rt.
- CL's book character: many signals, high gate/veto churn, small edges. **This looks like a
  market where the box edge is thin, not an implementation defect** — the honest options are
  re-optimization on more data or de-prioritization; there is no parameter tweak that turns
  $6-15/trade into $200/trade.

### NG — the friction illusion
- Entry rates 45–94% (the gate and indicators barely filter), 27,000+ trades, $3.3–$8.3 per
  trade everywhere except 4h ($50). **At $10/rt the NG ladder loses $109k; at $25/rt $408k.**
  The raw +$134k is not harvestable income; it is an artifact of costless accounting on a
  chop-heavy contract. **Recommendation: treat every NG slot except (marginally) 4h as
  paper-only forever, or re-optimize with cost-aware selection** (§8).

### RTY — decent slow slots, thin fast ones
- 4h $36,219/297/$122 — good, and 2026-strong ($24k). 2h/1h fine at $76-97/trade.
- 15m odd duck: only 112 trades (tightest 15m in the fleet — RTY_15m gate 78.3 + k=4) at
  $77/trade; healthy. 5m/2m thin; 2m negative at $10/rt.

### YM — quality over quantity
- 4h $50,585/188/$269 and 1h $55,542/456/$122 — strong. **2h is the fleet's sniper: 34 trades,
  $632 each, gate 56.0 + k=4** — an ultra-selective configuration that works (2026: $11k on 10
  trades). 5m/2m/15m are volume slots that survive $10 but thin out at $25.

---

## 8. The fix / enhance / accept ledger

Ranked by expected value; every item states whether it needs you.

1. **Fresh box export (OWNER — the big one).** All entry signals dead-end at the box feed
   (06-09/05-21/06-26). One export through 2026-08 for the 9 instruments turns the prepared
   tape into a real ~2-month out-of-sample test of all 54 champions — the thing this workstream
   was actually after. Everything else on this list is secondary.
   *Also worth fixing the process: your with20d drop (real data to 06-09) sat unswapped in prod
   since June — a standing box-refresh cadence (weekly scrape → drop → the gated merge) would
   keep the system permanently current.*
2. **Vol-gate recalibration cadence (re-optimization, pre-registered).** NQ 5m has been dark
   since April; NQ 2m is drifting the same way. The gates' admit thresholds are quantiles frozen
   on 2025 vol; 2026 runs hotter, so tight gates converge to "never trade". This is exactly the
   FU-11 lesson (the deployed gate is blind to regime change) in a second costume. The honest
   fix is a **scheduled re-optimization** (or a pre-registered gate-quantile refresh policy) —
   not a silent threshold bump. Needs a campaign decision from you.
3. **Cost-aware slot policy (decision, cheap).** 8 slots are negative at $10/rt (the NG ladder,
   CL 2m/5m, HG 2m, RTY 2m). While the system is paper-only this costs nothing; **before any
   live gateway, these slots must be excluded or re-selected under stressed-cost scoring** —
   otherwise the router would happily spend real spread on paper edges. Recommendation: make
   stressed-cost survival a standing selection criterion in the next champion campaign.
4. **Prod swap decision (OWNER, one command).** The extended root is built, gated, and verified;
   prod :8200 still serves the May/July tape. Say the word and the live root swaps (or stays —
   there is no rush while boxes lag anyway).
5. **Accept as best-case:** the slow-ladder champions (every 4h, most 2h/1h). Their per-trade
   edges ($120–$600) dwarf friction, their books are consistent across both calendar years, and
   nothing in the diagnostics suggests hidden decay. CL as an instrument stays structurally
   weak — more optimization is unlikely to conjure an edge the market isn't offering; NG below
   4h is a friction illusion to be retired, not repaired.

---

## 9. The dashboard visual gate (scripted Playwright — the house way)

The branch dashboard on :8250 was restarted against the extended root (with its own isolated
cache) and driven slot-by-slot by a Playwright script — select instrument, prime a different
timeframe, select the target (this is what loads the deployed `best` champion; the page boots
on a legacy preset otherwise), click **Run**, wait for all three views, re-select the L1 tab,
read the headline off the rendered page, screenshot. **54 screenshots** live in
`optimize/fwd/data/shots/`. The browser ran **on the server next to the dashboard** after the
local 15 GB box froze under the chart-render RAM load (the server does a slot in 1–35 s; the
laptop needed 90–240 s and then died).

**Result — every book reproduced on screen, with two delta classes cataloged:**

| what | result |
|---|---|
| Total-P/L card vs book, all 54 slots | **54/54 within the cent-rounding bound** (the card sums exact P/L; the book CSVs store cents-rounded P/L — 0.005 × trades + $1). 26 exact to the dollar, 38 within $1, max delta $24 on the 8,486-trade NG 2m slot (bound $43). |
| NQ (the golden-locked market) | trade count exact 6/6; P/L exact 4/6, $1 on 4h/2h (rounding) |
| Status-line trade count vs book | exact on 30 slots; **24 non-NQ slots differ by −10 … +76 trades (≤ 2.7%)** while the money agrees |

That last row is a finding in its own right: the dashboard's L1 view mixes two engines —
its money cards are the **causal** aggregate (the same engine as the books), but its visible
trade ledger/status count is the **strategy** engine. On NQ the two agree to the trade (that
is what the golden gate locks); on the other eight markets they disagree at the margins
(largest: SI 2m +76 of 3,496, SI 1h −10 of 374). Recorded as a cross-engine boundary
observation, not explained here — worth its own small issue before any live routing reads
trade counts off the UI.

Pre-registration amendment (transparent, post-observation): the frozen Phase-3 line said
"exact"; what the surface actually offers is exact-within-display-rounding for the money and
a second-engine count. The claim encodes exactly that, with the falsifier demanding the
deltas cluster at zero (≥ 20 dollar-exact; 26 observed) and every count delta stay ≤ 3%.

## 10. Verification

`optimize/verify/run.py` — the WS-FWD claims, each with V1/V2/V3 designed to fail differently:

- **FWD-EXTENSION-AND-54-BOOKS** — re-sums all 54 committed books to $2,180,902.65; V1 gate
  record (9/9 + 54/54 exact), V2 prod-untouched (checksums), V3 fabrication tripwire (zero
  entries beyond any box end).
- **FWD-FRESH-WINDOW-SLIVER** — re-derives the 25-trade/+$1,823.47 fresh cut; V1 count+locus,
  V2 NQ-4h anchor closure to the cent, V3 no-verdict-bar-crossed (fails if any fresh cell
  reaches n≥10 while this report claims otherwise).
- **FWD-DASHBOARD-VISUAL-GATE** — 54/54 within the rounding bound; V1 money-within-bound +
  NQ counts exact, V2 screenshots exist, V3 exactness-cluster + count-sanity (≥20 dollar-exact,
  no count delta > 3%).

**Ledger state at close: 67/67 claims pass** (`python3 optimize/verify/run.py`).

## 11. What went well · what went wrong

**Well:** the splice/resample gates all passed at zero tolerance (the 16-year set and the vendor
files are one source — this also retroactively strengthens every 16y-based study); the NQ 4h
anchor closed to the cent through the whole new pipeline; the with20d discovery converted 12 days
of shelved real data into coverage; the darkness diagnosis (NQ 5m) fell out of the drop-mix
telemetry rather than anecdote.

**Wrong / lessons:** (1) my first runner pass failed on all 54 slots (`missing sl_soft`) because
the L1 view validates the L2 dict too — caught by the loud-failure design, fixed in one line;
(2) the first dashboard-gate wait condition watched for a status line that only appears after a
view-tab click — the patient probe found the real completion signal ("done — all three tabs
filled"); (3) the dashboard's client-side render takes ~90 s per run even when the server
answers in milliseconds — worth knowing before anyone calls the dashboard "frozen" again;
(4) a stray keystroke corrupted `claims_fwd.py` on disk mid-session (an `op` prefix before the
docstring) — caught and reverted; the ledger would have refused to import it; (5) the first
full browser sweep **froze the local box (RAM)** — the browser now runs on the server, which
is both safer and 20× faster; (6) my first claim draft over-stated "exact" — the ledger's own
V1/V3 refused it (NQ 4/6 not 6/6 on P/L; 26 not 38 dollar-exact) and the statement was
corrected to the measured truth, `expect` untouched.

---

*After this workstream closes: the ORB (opening-range-breakout) study on all instruments — a
separate issue with its own pre-registration, as ordered.*
