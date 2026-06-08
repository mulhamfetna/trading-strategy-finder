---
name: ws-as-progress
description: WS-AS live progress — all-stocks signal export. Phase status, parity/validation evidence, measured timings. Companion to docs/{ANALYSIS,DATA_MAP,PLAN}.md.
type: progress
status: COMPLETE — 6 bundles generated, NQ byte-identical, all validated
created: 2026-06-08
workstream: WS-AS (all-stocks-signals)
---

# WS-AS — Progress

## Phase status
| Phase | State |
|---|---|
| AS.0 Scaffold + analysis/data-map/plan | ✅ done |
| AS.1 Instrument registry + coverage tests | ✅ done — `instruments.py`, 6-token no-mix contract |
| AS.2 Thin reuse wrapper (D1/D2 = NQ logic) | ✅ done — frozen Stage 1/Stage 2 reused verbatim |
| AS.3 Per-instrument driver + tests | ✅ done — `generate_signals.py` + `package_delivery.py` + `validate_bundles.py` |
| **AS.4 NQ byte-parity gate (HARD anchor)** | ✅ **PASS — 105/105 files byte-identical** to committed `NQ_SIGNALS_DELIVERY` |
| **AS.5 Generate + validate 5 new bundles** | ✅ **done** — ES + QQQ/SQQQ × RTH/ETH generated, all 6 bundles validated (5 invariants × 21 cells), packaged + zipped |
| AS.6 Parallel eval (local vs server) | ✅ done — **local, RAM-safe**; 5 instruments in ~41 min (see Timings) |
| AS.7 Final docs + REPORT + commit | ✅ done — `docs/REPORT.md` (cross-instrument totals + parity evidence) |

## Result
6 bundles, **63,200,834** signal rows / **74,391** reverse windows total. NQ **105/105 byte-identical**
to the committed delivery. All 6 × 21 cells pass 5 invariants. **32 tests green.** See `docs/REPORT.md`.

## Decisions (user, 2026-06-08)
- **D1** ETF/ETH session roll → **follow NQ logic uniformly** (futures hour≥18 roll for all 6).
- **D2** levels → **weekly + monthly only** (daily `D*` ignored), exact NQ mirror.
- **D3** run → **local, RAM-safe** (this machine; keep WS-I :8200 server up).

## Evidence
- **AS.4 parity:** `verify_nq_parity.sh` → `105 identical, 0 differ` (7 TF × 3 preset × 5 artifacts).
- **Tests:** `tests/` = 32 passing (registry coverage ×6 instruments + NQ parity on 4h/1h × 3 presets).
- **NQ structural validation:** 21/21 cells pass 5 invariants (counts, subset, partition, no-mix,
  reverse≤no_hold).

## Timings (measured)
- 1 full instrument (NQ, 7 TF × 3 presets, single-thread): **23m33s wall, 3.5 GB peak RAM**.
- Machine: 12 cores, ~5.3 GB free RAM (binding constraint) ⇒ ≤1 heavy job concurrent.
- Server (Old AMD, Ryzen 9 9950X, 16c/32t) available but **local chosen** (no transfer, simple).
- AS.5 schedule: ES (heavy) ∥ RTH lights, then ETH pair ∥ — peak ~4.5 GB, est. makespan ~37 min.

## Invariants held
Off-instrument mixing impossible (registry) · frozen Stage 1/Stage 2 math reused verbatim ·
NQ byte-identical · deterministic (stable sort) · no silent fallback (missing file → loud skip).
