# WS-FWD (#176) — forward OOS of the deployed champions: pre-registration

**Filed 2026-08-21 BEFORE any run. This fixes the data-extension gates, the fresh-window
definition, and the reporting rules for the owner's order: "apply the champions we have on all
the assets" on the tape that now extends past the books' ends, with dashboard (SSH tunnel +
Playwright) verification and a full per-slot diagnostic report.**

## What Phase 0 established (evidence on #176)

- Engine candles end: NQ/ES **2026-05-19**; GC/SI 07-02; RTY/YM 07-05; HG 07-07; CL/NG 07-08.
- The August tape exists in the 16-year dataset `~/Mulham/data_2010_1s` — all 9 instruments,
  1s and 1m, through **2026-08-07 16:59 ET**.
- Box CSVs (the entry-signal substrate) are **owner-scraped externals** with no in-repo
  generator: NQ ends 2026-05-22, ES 2026-05-21, the seven others 2026-06-26 (shifted).
  An empirical derivability probe (ratio census vs wOpen/mOpen across 4 instruments) shows
  per-period level values, NOT fixed multiples — the levels are the output of the owner's
  TradingView-side indicator and **cannot be fabricated**. Extending them is an owner action.

## Phase 0.5 — candle extension (frozen design)

Extension source: `data_2010_1s` 1m. Target: a **parallel extended data root** on the server
(`~/Mulham/wsg-i/FWD_EXTENDED`, mirror layout, symlinks for everything not extended). The
production root's files are NEVER modified (checksummed before/after). All champion runs and
the branch dashboard point at the extended root via `WSH_DATA_BASE`/`WSG_DATA_ROOT`; production
:8200 stays on the old root until the owner blesses a swap.

### Gate A — 1m splice parity (per instrument)

Overlap window = last **21 calendar days** of engine 1m coverage. On the timestamp
intersection: **exact** equality of open/high/low/close **and volume** (volume is load-bearing:
vwap ×32, obv ×29, mfi ×18 slots in the deployed set). Coverage: intersection must be ≥ **99%**
of engine rows in the window; asymmetric minutes are counted and reported.
**PASS = 0 OHLC mismatches AND 0 volume mismatches AND coverage ≥ 99%.** Any failure ⇒ that
instrument is NOT appended; reported as blocked — never patched silently.

### Gate B — timeframe resample proof (per instrument × 6 decision TFs)

The vendor TF files must be provably reproducible from the vendor 1m before any resampled
extension is trusted. Rebuild all TF bars from the vendor 1m over the vendor's own coverage
(bars labeled by start, 18:00-anchored sessions), compare to the vendor TF file excluding the
final (possibly partial) bar. **PASS = bar-set equality AND 0 OHLCV mismatches.** Failure ⇒
that TF is not extended; reported.

### Gate C — post-extension audit

Re-run `optimize/fwd/phase0_data_audit.py` against the extended root: all appended frames end
2026-08-07; strictly increasing timestamps; no duplicates; original-root checksums unchanged.

## Phase 1 — the runs (frozen)

Champion set **`best`** (the deployed set), 9 instruments × 6 TFs, run through the SAME loader
the dashboard uses (`optimize.data.load_inputs` → the causal engine), full window, on the
extended root, server-only. Per-slot outputs: full trade book CSV + summary JSON (net, DD,
trades, win rate, per-month P/L). scp'd back and committed (LOCAL = source of truth).

## Phase 2 — the fresh-window cut (frozen definitions)

- **Fresh window per instrument** = trades ENTERING after the pre-extension engine end
  (NQ/ES 2026-05-19, GC/SI 07-02, RTY/YM 07-05, HG 07-07, CL/NG 07-08).
- **Declared limitation (fixed now):** with stale boxes, fresh entries can exist only up to
  each instrument's box end (NQ 05-22 / ES 05-21 / others ~06-26 shifted) — i.e. the NQ/ES
  fresh-entry sliver is ~3 days and the others have NONE inside the candle-fresh zone. What the
  extension DOES buy immediately: (a) trades open at the old candle end now resolve on real
  tape instead of being force-marked, (b) the full-book diagnostic the owner asked for runs on
  current data, (c) the moment the owner drops fresh box scrapes, the entry side lights up with
  no further engineering. **No box rows are fabricated, forward-filled, or extrapolated.**
- Verdict language: per-slot fresh-window P/L is REPORTED, not judged against expectation,
  wherever the entry count is < 10 (a povertied sample gets no verdict — the no-negative-
  without-power rule). Full-book diagnostics carry the analytical weight instead.

## Phase 3 — dashboard visual gate (frozen)

Branch dashboard :8250 restarted against the extended root; SSH tunnel; Playwright drives
instrument × TF runs; screenshots committed as evidence. Headline dollar figures on screen must
equal the Phase-1 core numbers for the same slot (exact). NEVER Claude-in-Chrome.

## Phase 4 — the report

Verbose no-jargon per-slot report: full-book performance, fresh-window observation, why
positive/negative (regime/costs/tail diagnostics from the book), fix/enhance verdict — with the
honesty rules (no positive without dumb control + noise check; no negative without power).
Claims enter the ledger (`optimize/verify/claims_fwd.py`) before any number is published.

## Blind spots (declared)

1. Fresh boxes are owner-only input; until they land the fresh window is exit-resolution plus
   the NQ/ES 3-day sliver. This pre-registration does NOT authorize inventing box levels.
2. The 16y dataset and the engine vendor set are independent continuous-contract splices;
   Gate A can only certify the overlap it sees (21 days). A roll INSIDE the appended window
   that the two vendors would have handled differently is undetectable until the next vendor
   drop — recorded as a risk, mitigated by the 1s dataset being the SAME source that passed
   cent-parity in FU-9/WS-NEWS.
3. `best` champions were selected on data through mid-May 2026 (NQ/ES) — the fresh window is
   honest OOS for them; for the 7 others the "fresh" candle zone (May→Jul) was partially
   inside their extraction data; only entries after each engine end are called fresh.
