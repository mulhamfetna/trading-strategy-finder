# WS-GRID pre-registration — the literal full-grid closure of the premium ride

**Filed BEFORE any run (commit date = filing date). Owner instruction (2026-08-18): "proceed to
the literal full grid closed, no single possible combination is skipped at all."**

## Scope — what "the full grid" means, exactly

The **premium-ride grid**: the frozen deployed trade (LONG rel−300 s · stop 0.10 % worse-of ·
TP 0.40 % better-of · tie⇒STOP · exit +900 s · stressed costs lead) on **every release
moment-block × every instrument in the registry** (`TOKENS`: NQ, ES, GC, SI, HG, CL, NG, RTY,
YM). Out of scope here, queued separately in the research queue: the *direction* grid's YM row
(direction needs the surprise pipeline, a different machine; it was dead on all 8 instruments
tested) and non-frozen trade shapes (short side / other geometries / conditional — WS-FUSION).

## The remaining untested cells (from the coverage record + N2/N3/ESCPI evidence)

An instrument's `tested_at_spec` set = titles with **deployed-spec** evidence on THAT
instrument. M1's 5-series grid on ES/GC/CL used a different geometry (no TP) and does NOT count.

| instrument | already evidenced at the frozen spec | cells THIS sweep must run |
|---|---|---|
| NQ, RTY | all N2 blocks + {CPI,NFP,FOMC} (M3) + {Retail,Durables} (N3) | **EIA-crude, API** (their N2 "covered-minute" status was CL-only evidence — a real gap) |
| ES, GC | {CPI,NFP,FOMC} (N3 pooled + slices) | all ~90 N2-style blocks + Retail + Durables + EIA-crude + API |
| CL | {EIA-crude, API} (N3) | all N2-style blocks + the 5 macro series {CPI,NFP,FOMC,Retail,Durables} |
| SI, HG, NG, YM | nothing | EVERYTHING: all blocks + the 5 macro + EIA-crude + API |

## Frozen constants

Point values from the registry (`optimize/instruments.py POINT_VALUE`): NQ 20 · ES 50 · GC 100
· SI 5000 · HG 25000 · CL 1000 · NG 10000 · RTY 50 · YM 5. Tick $ (exchange specs — the repo
still lacks a canonical tick table, open issue #93; declared here): NQ/RTY $5 · ES/HG $12.50 ·
GC/CL/NG $10 · SI $25 · YM $5. **Stressed cost/event = $2.50 + 4 × tick$**: NQ/RTY/YM $22.50 ·
GC/CL/NG $42.50 · ES/HG $52.50 · SI $102.50.

## Design (identical to the N2 machinery — nothing re-implemented)

- Blocks from the N1 moment logic with the per-instrument `tested_at_spec` as the
  covered-minute set; the previously-"covered" titles missing on that instrument run as their
  own explicit blocks (schedule selection for CPI/NFP/FOMC; Retail/Durables/EIA/API-alone
  minutes with the same window-overlap hygiene as N3).
- Verdict ladder unchanged: jump gate (>1.2× quiet, else VOID-TIMESTAMP) → t-test →
  chronological half-split → quiet-day control (400 days/clock, seed 117) + floor →
  1,000-placebo noise check. Speech blocks: ±120 s fuzz sensitivity.
- **This is an EXPLORATORY COMPLETION SWEEP — no confirmatory tier.** Per-instrument BH-FDR
  q=0.10 labels; any survivor goes to the research queue for its own fresh pre-registered
  confirmation (the WS-ESCPI pattern); nothing is "confirmed" out of this sweep.
- Negatives: POWERED-NULL if MDE(80 %, α=0.05) ≤ $150/event (the line is nominal-dollar and
  declared, NOT variance-scaled per instrument — a known crudeness, same as N3), else
  UNDERPOWERED.
- Per-instrument data-quality REPORTING (coverage of traded pre-release seconds) — voiding
  stays per-block via the jump gate (the YM lesson: thin ≠ dead; a wrong-minute block must
  not read as a premium null).

## Declared blind spots

1. One trade shape only, as everywhere in this programme.
2. The $150 powered-null line in SI dollars (cost $102.50/event) is generous and in NG dollars
   tight — cross-instrument MDE comparisons must use the per-block MDE column, not the label.
3. Thin-tape instruments (YM everywhere, SI/HG/NG at off-hours blocks) will produce many
   UNDERPOWERED/VOID cells — the grid is *closed* by having a recorded verdict per cell, not
   by every cell being decisive. The completeness claim this buys: **every cell has a status;
   no silent gaps.**
4. Multiplicity across this sweep and any future re-run must be counted together in the ledger.
