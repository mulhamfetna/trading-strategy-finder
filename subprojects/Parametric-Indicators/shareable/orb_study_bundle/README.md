# ORB Study Bundle — WS-ORB (#183), 2026-08-23

Self-contained record of the opening-range-breakout study on 9 futures (NQ ES GC SI HG CL NG RTY YM),
16 years of 1-minute data (2010-06-06 → 2026-08-07), 1 contract, pre-registered before any run.

**Headline: 0 of 225 grid cells met the positive bar (t ≥ 2.5 at $25/round-trip on 2018–2024 with sign
agreement 2010–2017 and year stability). Raw +$1.57M becomes −$6.49M after $25/rt friction; the median gross
edge is −0.01 ticks per trade. ORB is not a viable entry family on these markets at realistic costs.**

## Contents
- `docs/WS-ORB-PRIOR-ART.md` — verified prior art (99-agent research pass; includes the refuted-claims list).
- `docs/WS-ORB-PREREGISTRATION.md` — definitions, grid, verdict rules, controls — filed BEFORE the run;
  includes the pre-run anchor-check note (SI → 07:00, HG → 09:00 by volume profile, never by P/L).
- `docs/WS-ORB-REPORT.md` — full report (fleet tables, per-instrument deep dives, controls, meaning).
- `optimize/orb/orb_reference.py` — the entire strategy definition in one file (sessions, ranges, rules
  R1/R2/R3, comparator C1, gap-at-open fills, stop-first). `test_orb_reference.py` — 6 hand-computed
  synthetic-session tests (`python3 -m pytest test_orb_reference.py`).
- `optimize/orb/orb_anchor_check.py` / `orb_run.py` / `orb_power.py` / `orb_controls.py` — the pipeline:
  anchor volume check → 225-cell grid → verdicts with power (MDE) → random-anchor + vol-tercile controls.
- `optimize/orb/data/anchor_check.json` — the anchor evidence.
- `optimize/orb/data/grid1/` — `orb_summary.json` (all 225 cells: per-window stats at $0/$10/$25, per-year
  table), `grid_table.csv` + `verdicts.csv` (flat tables), `controls_top.json` (random-anchor draws + vol
  terciles for the 4 best cells), `verdicts_output.txt`, `report_inputs.txt`, `run.log`.
- `optimize/verify/claims_orb.py` — the ledger claim (V1 definitions held, V2 verdict table reproduces,
  V3 falsifier: the top cell's anchor carries no information). Requires the repo's verify harness to run.

## Not included
The 225 per-cell trade books (74 MB CSV) live on the compute server (`wsg-i/orb_runs/grid1/orb_book_*.csv`);
`orb_run.py --root <1m-tape> --out <dir> --jobs 9` regenerates all of them in ~90 s (deterministic, no fitted
parameters). The 1-minute tape itself is not distributed.

## Reproduce
```
python3 -m pytest optimize/orb/test_orb_reference.py
python3 optimize/orb/orb_anchor_check.py <tape_root> optimize/orb/data/anchor_check.json
python3 optimize/orb/orb_run.py --root <tape_root> --out <outdir> --jobs 9
python3 optimize/orb/orb_power.py <outdir>
python3 optimize/orb/orb_controls.py --root <tape_root> --out <outdir>/controls_top.json \
        --cells NQ_globex_60_R1,NQ_cash_15_R2,NG_globex_60_R3,NQ_globex_60_R2
```
Tape layout: `<tape_root>/<TOK>_Continuous_Data/<TOK>_1m.csv` with `datetime,open,high,low,close,volume`
(ET-naive, bars labelled by start).
