# EXECUTIVE SUMMARY — news-release-long v1.1.0
**One page. 2026-08-17 · branch `feat/ws-deploy-news-executor` (isolated) · ⛔ merge/live gated on the owner (#127)**

## What this is
The first confirmed news trade of the research programme, packaged for deployment: **LONG NQ/RTY,
enter before {CPI, NFP, FOMC} releases, stop 0.10%, take-profit 0.40%, timed exit +900s.** It
harvests the announcement premium — payment for holding equity risk through macro uncertainty —
and needs no directional prediction (direction was proven unpredictable; this pays anyway).

## Why the numbers are believable
Confirmed at the programme's strictest bar (Bonferroni α/54 + era half-split) → the executor
reproduces the committed study evidence **to the cent** (NQ 327/327 events) → this bundle's
portable code re-verifies itself (`--verify` = PASS) → the branch dashboard renders **byte-identical**
to production → the golden gate shows the rest of the book untouched.

## The headline economics (2024→2026, net of the HARSHEST cost scenario)
| qty | entry model | NQ + RTY total | yearly pace | status |
|---|---|---|---|---|
| 1 | single-second (as verified) | +$44,390 | ≈ $17k/yr | ready at merge |
| 5 | worked entry | +$214,785 | ≈ $83k/yr | feasible now |
| 10 | worked entry | +$429,571 | ≈ $165k/yr | model-validated |
| 20 | worked entry | **+$859,141** | **≈ $330k/yr** | validated ceiling |

Did it help the existing system? Measured, same window, with-vs-without: **+31% profit for +6.6%
drawdown**, near-zero correlation (+0.098), ~14 hours/year in the market.

## What the scaling studies found (D3 + D4)
The constraint is the **quiet entry second** (7 contracts median on NQ), not the violent exit
(deep at every size tested). The fix — a **worked VWAP entry over the 300s pre-release window**
(1.3–2.5% participation at qty=20) — was validated: NQ keeps 96% of its edge, **RTY improves +24%**.

## Know what you own
Win rate ~40%; the **median event loses**; a third of events hit +4R and pay for everything; worst
measured fill = 2.1× the nominal stop → budget −2R per event. The premium is **era-concentrated**
(≈0 before 2020, strongest 2025–26) — the **regime monitor** (rolling 24-CPI net-stressed mean < $0
⇒ sticky STAND-DOWN, owner-cleared only) is a deployment condition, not an option.

## The two things only the owner can do
1. **Merge instruction on #127** (everything stays isolated + paper until then).
2. **Broker margin at size** (a six-figure commitment at qty=10–20 — verify current rates).

*Everything in this bundle re-derives from committed evidence; run `portable_backtester.py --verify`
before trusting any number you did not compute yourself.*
