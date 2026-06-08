---
name: all-stocks-signals-report
description: WS-AS completion report — 6 per-instrument signal delivery bundles (NQ, ES, QQQ-RTH, QQQ-ETH, SQQQ-RTH, SQQQ-ETH) mirroring NQ_SIGNALS_DELIVERY, candles matched to own boxes. NQ byte-parity proven; all bundles structurally validated; counts, timings, file map, and how-to-regenerate.
type: report
status: complete
created: 2026-06-08
workstream: WS-AS (all-stocks-signals)
---

# WS-AS — All-Stocks Signal Export: Completion Report

## 0. TL;DR
The frozen NQ signal-export pipeline was generalized to **all 6 instruments** in `ALL_STOCKS/` and
produced **6 delivery bundles** that mirror `NQ_SIGNALS_DELIVERY` exactly — 4-stage product
(all-signals → holds-dropped → reverse-signals → reverse-by-direction) × 7 timeframes × 3 presets,
each instrument's candles matched to **its own** boxes with **no mixing**. Per the user's decisions
(D1/D2), every instrument runs the **identical frozen logic** (futures hour≥18 roll + weekly/monthly
levels), so the regenerated **NQ bundle is byte-identical** to the committed original (105/105 files).
All 6 bundles pass a 5-invariant structural validation. Built test-first (**32 tests green**).

## 1. What shipped — 6 bundles
`<INSTR>_SIGNALS_DELIVERY/` for `<INSTR>` ∈ {NQ, ES, QQQ-RTH, QQQ-ETH, SQQQ-RTH, SQQQ-ETH}, each
**106 CSVs** (21 all-signals + 21 holds-dropped + 21 reverse + 42 by_direction + SUMMARY) + README +
`.zip`, structurally identical to the NQ reference.

| Instrument | signal rows (Σ 21 cells) | long | short | no_hold | reverse | dir / zip |
|---|--:|--:|--:|--:|--:|--:|
| NQ | 16,777,916 | 39,854 | 40,548 | 80,402 | 16,881 | 1.7G / 86M |
| ES | 16,698,388 | 37,098 | 37,392 | 74,490 | 16,110 | 1.6G / 80M |
| QQQ-RTH | 4,663,768 | 18,312 | 17,886 | 36,198 | 8,109 | 462M / 26M |
| QQQ-ETH | 10,683,802 | 27,042 | 28,002 | 55,044 | 11,973 | 1.1G / 55M |
| SQQQ-RTH | 4,623,364 | 16,036 | 16,074 | 32,110 | 8,525 | 458M / 25M |
| SQQQ-ETH | 9,753,596 | 24,162 | 23,780 | 47,942 | 12,793 | 947M / 48M |
| **TOTAL** | **63,200,834** | | | | **74,391** | |

(RTH bundles ~30% and ETH ~60% the size of the futures, reflecting shorter ETF sessions.)

## 2. Correctness evidence
- **NQ byte-parity (the anchor):** regenerated NQ output diffs **byte-identical** to the committed
  `NQ_SIGNALS_DELIVERY` for **all 7 TF × 3 presets × 5 artifacts = 105 files** (`verify_nq_parity.sh`
  → `105 identical, 0 differ`). This proves the generalization didn't perturb the frozen path.
  Verified separately: `ALL_STOCKS` NQ candles + box are byte-identical to the original sources.
- **Structural validation (all 6):** `validate_bundles.py` → every instrument's 21 cells pass 5
  invariants: (1) long+short+hold = signal_rows; (2) no_hold = long+short; (3) by_direction splits
  partition reverse exactly; (4) **no-mix** — every `box_id` date resolves inside that instrument's
  own box index; (5) reverse ≤ no_hold. **0 errors.**
- **Tests:** 32 passing — registry coverage (files exist, box ⊇ candle range, unique tokens) for all
  6 instruments + NQ parity (all-signals & reverse) on 4h/1h × 3 presets.

## 3. Decisions applied (user, 2026-06-08)
- **D1** ETF/ETH session roll → **follow NQ logic uniformly**: every instrument uses the futures
  `hour≥18 → +1 day` roll (`BoxLookup._candle_to_box_date`). For ETF-RTH the roll never fires (no
  bars ≥18); for ETF-ETH the 18:00/19:00 after-hours bars roll to the next day's box, same as NQ.
- **D2** levels → **weekly + monthly only** (`_WEEKLY_LEVELS + _MONTHLY_LEVELS`); daily `D*` columns
  ignored, exactly as the NQ delivery.
- **D3** run → **local, RAM-safe** on this machine (WS-I `:8200` review server kept up).

## 4. How it works (no math drift)
A config-driven driver reuses the **frozen** generators verbatim — `generate_stage1._emit_rows`
(Stage 1) and `stage1_0_reverse_signals.generate_stage2.generate` (Stage 2). Because D1/D2 = "NQ
logic uniformly", no rule parameterization was needed: the only per-instrument input is **identity**
(candle dir + box CSV + output token), declared once in `instruments.py`. Cross-instrument mixing is
impossible by construction — a token resolves to exactly one candle dir and one box file.

## 5. Execution & timings (local, RAM-safe)
- Per full instrument (7 TF × 3 presets, single-thread): **~23–25 min wall, 3.5 GB peak RAM** (heavy
  futures); ETFs proportionally less.
- Machine: 12 cores, ~5.3 GB free RAM (the binding constraint) ⇒ at most one heavy job concurrent.
- Schedule used (`run_remaining_ramsafe.sh`): **ES ∥ RTH-lights**, then **ETH pair ∥** after ES freed
  memory. Phase 1 14:01→14:26, Phase 2 14:26→14:42 — 5 instruments in **~41 min**, peak ~4.5 GB.
- The Old AMD server (Ryzen 9 9950X, 16c/32t) was available for true 6-wide parallelism (~23 min
  makespan) but local was chosen — no transfer, simpler, and the job is one-shot.

## 6. File map (`subprojects/all-stocks-signals/`)
- `instruments.py` — 6-instrument registry (the no-mix contract).
- `generate_signals.py` — config-driven driver (reuses frozen Stage 1/Stage 2).
- `package_delivery.py` — per-instrument bundle packager (mirrors NQ layout) + optional zip.
- `validate_bundles.py` — 5-invariant structural validator.
- `verify_nq_parity.sh` — full NQ byte-parity gate. `run_remaining_ramsafe.sh` — RAM-safe scheduler.
- `tests/test_instruments.py`, `tests/test_parity_nq.py` — 32 tests.
- `docs/{ANALYSIS,DATA_MAP,PLAN,REPORT}.md`, `README.md`, `WS-AS_PROGRESS.md`.
- Outputs (gitignored, build artifacts): `output/<token>/...` (technical tree) and the root
  `<INSTR>_SIGNALS_DELIVERY/` bundles + `.zip` (same handling as the untracked `NQ_SIGNALS_DELIVERY`).

## 7. Regenerate
```bash
# generate all 6 (or a subset) into output/<token>/...
python3 subprojects/all-stocks-signals/generate_signals.py            # all 6 (sequential)
bash    subprojects/all-stocks-signals/run_remaining_ramsafe.sh        # RAM-safe local schedule
# verify + validate + package
bash    subprojects/all-stocks-signals/verify_nq_parity.sh             # NQ byte-parity (105/105)
python3 subprojects/all-stocks-signals/validate_bundles.py             # 5 invariants × 6
python3 subprojects/all-stocks-signals/package_delivery.py --zip       # 6 bundles + zips
```

## 8. Notes / caveats
- `output/SUMMARY_ALL.csv` is authoritative only when all instruments run in one invocation; under
  the parallel per-instrument run each process rewrites it, so the combined table is rebuilt from the
  per-instrument `output/<token>/SUMMARY.csv` files (which each bundle carries correctly).
- Determinism: same inputs + same code → byte-identical outputs regardless of worker count.

## 9. ETF box-shift re-export (WS-AS.8 — isolated, ETFs only)
After NQ & ES were **approved and frozen**, the 4 ETF bundles were regenerated with each instrument's
box `Date` shifted **back one business day** (weekends are the only holidays):
`new_Date = old_Date − 1 BDay` → Monday→Friday, Tuesday→Monday, Wednesday→Tuesday,
Thursday→Wednesday, Friday→Thursday. Done by a **strictly isolated** script
(`isolated_etf_box_shift.py`) that hardcodes only the 4 ETF paths, reuses the frozen Stage 1/Stage 2
engine read-only, and **never references NQ/ES** (asserted). The shift was verified a clean bijection
(weekday-only boxes, 0 post-shift duplicate dates); a loud assertion guards against weekend/collision
results. Shifted boxes saved to `shifted_boxes/<TOKEN>_full_data_shifted.csv` (Date 2024-12-31 ..
2026-05-21). All 4 re-exports pass the 5-invariant validation against the **shifted** box index
(box_id dates now resolve in the shifted index). The 4 ETF `*_SIGNALS_DELIVERY` bundles + zips were
replaced with the shifted versions (README carries a `BOX-SHIFTED` marker); NQ/ES bundles untouched.

Effect (reverse-window totals, Σ 21 cells — unshifted → shifted):
| ETF | rows | long | short | reverse |
|---|--:|--:|--:|--:|
| QQQ-RTH | 4,663,768 → 4,666,576 | 18,312 → 17,436 | 17,886 → 18,186 | 8,109 → 8,197 |
| QQQ-ETH | 10,683,802 → 10,717,022 | 27,042 → 25,820 | 28,002 → 26,984 | 11,973 → 11,781 |
| SQQQ-RTH | 4,623,364 → 4,629,284 | 16,036 → 16,116 | 16,074 → 16,070 | 8,525 → 8,721 |
| SQQQ-ETH | 9,753,596 → 9,796,028 | 24,162 → 23,544 | 23,780 → 24,054 | 12,793 → 12,875 |

Re-run: `python3 subprojects/all-stocks-signals/isolated_etf_box_shift.py` (the unshifted ETF output
tree under `output/` is retained for audit; NQ/ES are never run by this script).

## 10. Status
**WS-AS complete.** NQ & ES = approved/frozen (byte-identical, untouched). The 4 ETF bundles =
box-shifted −1 business day, validated. 32 tests green. Returning to the paused **WS-I.5** sign-off.
