# WS-GRID results — the literal full-grid closure (#140)

**Pre-registration `b629543` (before any run) · 661 grid cells across 9 instruments ·
2026-08-18 · evidence: `news4_scan_blocks_{INST}_grid.csv` + events/manifests/logs, committed.**

With this sweep, **every release moment-block × every registry instrument now has a recorded
verdict at the frozen deployed spec**. Combined with N2 (NQ/RTY full calendar), M3, N3 and
WS-ESCPI, the premium-ride grid is CLOSED: no silent gaps remain — every cell is TESTED,
VOID-with-cause, or a labeled null.

## The one-line verdict table

| verdict | cells | reading |
|---|---|---|
| VOID-TIMESTAMP | 370 | the calendar minute does not move that instrument's tape (jump ≤1.2×) — no premium claim possible either way |
| SIGNIFICANT-NEGATIVE | 179 | **41% have gross > −$5 and 29% have gross > 0** — mostly the cost line made visible by low variance, not anti-premiums |
| POWERED-NULL | 106 | informative zeros (MDE ≤ $150) |
| UNDERPOWERED | 5 | cannot tell |
| **EXPLORATORY-POSITIVE** | **1** | **YM CPI** — the only positive in the entire sweep |

## The three structural findings

### 1 · The CPI premium is an EQUITY-INDEX phenomenon, ordered by index beta
Net stressed $/event, CPI-alone, frozen spec (grades differ — see sources):
**NQ +$309 (confirmed) > ES +$151 (battery PASS, robustness) > YM +$108 (exploratory, this
sweep + the ESCPI descriptive) > RTY +$78 (confirmed)**. Metals: HG gross +$80 / SI gross +$48
— possibly real but drowned by their cost lines ($52.50/$102.50) → POWERED-NULL. CL: gross
+$1.31 (zero). NG: VOID (its tape ignores 8:30 macro minutes entirely).

### 2 · The Retail anti-premium is close to UNIVERSAL
Gross-negative and significant on **seven instruments**: NQ −$86, ES −$66, GC −$46, HG −$37,
SI −$30, RTY −$32, YM −$23 (CL/NG void — their tape doesn't react at that minute). Whatever
mechanism sends risk assets *down* around a Retail Sales print, it is market-wide.
(The short side remains untested and queued — RQ-2.)

### 3 · POWER ≠ PREMIUM, final form
The sweep's most violent minutes pay nothing: NG's own inventory release jumps **8.5×** on NG
and grosses **−$4.89**; SI's FOMC minute jumps 14×, NFP 9× — all nulls or cost-drag negatives.
Across ~1,300 total cells now measured in this programme, volatility is everywhere and the
harvestable premium exists in exactly one place: **equity-index futures at the CPI print.**

## Reading discipline for the 179 "significant negatives"
On instruments with big cost lines (SI $102.50, ES/HG $52.50, GC/CL/NG $42.50 per event), a
low-variance ride makes the cost itself statistically significant. Only gross-negative +
half-split-consistent cells (the Retail family) are candidate anti-effects; the rest are the
fee schedule, measured precisely.

## What this supersedes
`NEWS-COVERAGE-MATRIX.md`'s premium column ("NEVER" for 230 series) is now historical: the
grid CSVs are the live per-cell record. Regenerating the matrix to merge grid verdicts is
queued (RQ-6) rather than hand-edited.
