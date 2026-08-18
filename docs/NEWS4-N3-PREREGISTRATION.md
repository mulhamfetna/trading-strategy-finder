# WS-NEWS4 / N3 pre-registration — the partially-tested deep-dives (#137)

**Filed BEFORE any N3 run** (commit date = filing date). Inherits every mechanism from the N2
pre-registration (a988f17): the frozen ride spec, the verdict ladder, the jump gate, controls,
noise check, and the $150 powered-null line. New here: the confirmatory family and per-instrument
constants.

## Scope resolved by N1/N2 already (no new runs)

- **FOMC-adjacent events** (item 4 of #137): N2 covered them. FOMC Minutes UNDERPOWERED (NQ
  −$58/ev) / POWERED-NULL (RTY −$15); Fed Press Conference VOID-TIMESTAMP (fuzz flip);
  Powell speeches POWERED-NULL. Closed by reference to `news4_scan_blocks_*.csv`.
- **The short leg** (item 5): conditional on N2 positives — there were none. The Tier-2
  anti-premium observations (IBD/TIPP, Wholesale Adv, 42-Day Bill) cannot be promoted: their
  full history is already consumed and n is small; recorded as unpromotable observations.

## The confirmatory family — 8 tests, Bonferroni α = 0.05/8 = 0.00625

| # | question | block | instrument | note |
|---|---|---|---|---|
| 1-2 | Is Retail's negative premium real? | Retail Sales MoM minutes | NQ, RTY | two-sided; a CONFIRMED-NEGATIVE requires gross (not only net) mean < 0, half-split both halves negative, and the gates |
| 3-4 | Durables: powered null or unknown? | Durable Goods Orders MoM minutes | NQ, RTY | expectation: POWERED-NULL |
| 5 | EIA re-check at the deployed spec | EIA Crude Oil Stocks Change minutes | CL | the M1 VOID inherited the provenance restriction; the ride needs timestamps only |
| 6 | API re-check | API Crude Oil Stock Change minutes | CL | same |
| 7-8 | Does the deployed-set premium exist on other instruments? | the deployed schedule minutes (pooled) | ES, GC | CPI-alone reported descriptively alongside |

## Per-instrument constants (same formula as the deployed pair: stressed = $2.50 + 4 ticks/event)

| instrument | point value | tick $ | stressed cost/event |
|---|---|---|---|
| ES | 50 | 12.50 | $52.50 |
| GC | 100 | 10.00 | $42.50 |
| CL | 1000 | 10.00 | $42.50 |

NQ/RTY unchanged ($22.50). Retail/Durables blocks take their minutes WITHOUT the covered-minute
exclusion (they ARE tested titles — that is the point) but WITH the deployed-window-overlap
exclusion, so a Retail minute that co-fires with CPI/NFP is excluded (its evidence belongs to
the deployed set).

## Declared expectations (cannot drift after results)

- Retail: M1's grid indicator showed NQ −$98/ev at the no-TP cell. If the deployed-spec test is
  significantly negative on gross with both halves negative, the anti-premium is REAL and Retail
  becomes a documented "do-not-ride" series; if not, M1's negative was noise/geometry-specific.
- Durables: expect POWERED-NULL (RTY at least; NQ possibly UNDERPOWERED).
- EIA/API on CL: no expectation — this is the first costed test at the deployed spec.
- ES/GC deployed set: M1's grid indicator suggests a positive (ES CPI +$219, GC CPI +$197 at
  the no-TP cell); if the pooled set confirms at the deployed spec, that is NEW deployable
  surface (owner decision, not automatic).

## Blind spots

1. CL's session structure differs (10:30/16:30 ET, energy-specific tape) — the $150 powered-null
   line was calibrated on equity-index dollars and is declared, not derived, for CL/GC/ES.
2. ES/GC deployed-set tests reuse the same event minutes as NQ's evidence — they are independent
   PRICE files but not independent EVENTS; a calendar defect passes through identically.
3. Everything the N2 blind spots say about shape (short side, other geometry, conditioning).
