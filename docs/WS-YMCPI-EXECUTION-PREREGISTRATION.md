# RQ-7 / #147 pre-registration — the YM CPI execution study and the ACQUIRE rule

**Filed BEFORE any measurement (commit date = filing date). Owner instruction (2026-08-18):
"walk it through the verification layers required to verify it and either acquiring it or not."**

## What is already verified (not re-run here)

Statistics: the only positive of the 661-cell grid (+$107.64 net/event, p=0.0016, jump 9.8×,
halves/floor/noise green). Core: executor parity to the cent (full era n=116; 2024→2026 n=29,
+$355.72/event). Engine: golden 6/6. Dashboard: branch ≡ production, screenshots. Ledger 38/38.

## What is NOT yet verified — the execution layer

Every number above assumes the replay's fill: **entry at the close of the last traded 1-second
bar at/before release−300 s**. On YM's thin premarket tape (median 101 traded seconds in the
300-second entry window) that bar may be stale, the true spread may exceed the 4-tick cost
formula, and the book may be too shallow even for one contract. Four measurements decide, each
with an a-priori PASS line fixed here:

| # | layer | measurement (from YM_1s, volume kept) | PASS line (a-priori) |
|---|---|---|---|
| ACQ-1 | **Fill staleness** | age of the entry bar: (rel−300 s) − t(entry bar), per event | median ≤ 30 s AND p95 ≤ 60 s (the executor tolerance) |
| ACQ-2 | **Slippage reality** | re-run the ride with the HARSHER fill: entry at the OPEN of the FIRST traded bar AFTER rel−300 s (what a late-arriving order actually gets; `run_bracket(entry_price=next_open, walk_from=next+1)`) | net-stressed mean stays > **$50/event** and the sign of every prior gate conclusion is unchanged |
| ACQ-3 | **Entry depth** | volume of the entry bar and of the [rel−300, rel) window, per event | median entry-window volume ≥ **20 contracts** (qty=1 = ≤5% of the window; worked entry viable) |
| ACQ-4 | **Exit-side tape** | traded seconds and volume in [rel, rel+900] (where all exits happen) | median traded seconds ≥ **300/900** and median volume ≥ **200 contracts** |

Additional stress reported (not gating): flat ±2-tick and ±4-tick adverse entry arithmetic.

## The decision rule, fixed now

**ACQUIRE** (deploy YM CPI to production through the same ship pipeline: playbook promotion →
dev → main → release) **iff ALL FOUR pass.** Any failure ⇒ **NOT ACQUIRED**: the candidate is
parked with the failing layer named, re-openable only by new data (e.g. a thicker micro-YM
tape) — no threshold may be revisited after seeing the measurements.

## Blind spots (declared)

1. 1-second OHLCV cannot see the book: "volume traded" bounds participation but not the quote
   spread; ACQ-2's next-bar-open fill is the best tape-only proxy for crossing it.
2. The $50 ACQ-2 line is a judgment call (≈ half the replay edge), fixed here precisely so it
   cannot drift after results.
3. Thin tape at qty=1 says nothing about qty>1 — any scaling would need its own D3/D4 study
   (the ES RQ-1 pattern).
