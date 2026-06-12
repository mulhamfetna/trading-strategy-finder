# Backtester Speed Optimization — PINNED STATUS (task #210)

**Updated:** 2026-06-12 · branch `dev` (local only, not pushed). Single source of truth for where the
optimization stands. Each step has its own `perf/UPDATE_step_*.md`; this pins the whole picture.

---

## Plan (from `optimize/REPORT_backtester_speed_optimization.md`)

| Phase | Steps | Status |
|-------|-------|--------|
| **0 — Safety net** | golden baselines + harness + equivalence framework | ✅ done |
| **1 — Vectorize + de-dup** | D obv · A1 bollinger · A2 cci · A3 stochastic/atr/keltner/mfi · ~~B de-dup SMC~~ | ◑ D/A1/A2 done; A3 pending; **B DROPPED (profiler misread — ~0.05 s, not ~9 s)** |
| **2 — JIT + cache** | F cache 1-min sampling map · ~~C Numba SMC loops~~ → **C′ numpy rewrite** | ◑ C′ done; C(Numba) **blocked** (Py 3.14 + PEP 668); F pending |
| **3 — Polish (optional)** | E sampled-overlap · G thread indicators · H Numba exit walk | ◑ **E done**; G/H pending |
| **4 — Axis B (per-decision loop)** | B1 vectorize signal · B2 inject into engine · B3a numpy df_4h rows · B3b numpy exit walk | ✅ **B1/B2/B3a/B3b ALL done** — fine-TF backtests −50…−67%, byte-identical |

---

## Commits (rollback points) on `dev`

| SHA | Step | 4h time | Result |
|-----|------|--------:|--------|
| `f9d6f36` | Phase 0 safety net | 36.2 s | golden baselines (6 TFs) + check_golden + bench + equiv framework — **the rollback anchor** |
| `e76448` | D — vectorize obv | — | 64×, bit-identical |
| `1f1c29f` | A1 — vectorize bollinger | — | 40×, bit-identical |
| `f178ec3` | A2 — vectorize cci | 25.6 s | 4×, bit-identical |
| `08b8c77` | E — order_blocks sampled-overlap | 16.5 s | −9 s, byte-identical |
| `5d1945e` | C′ — order_blocks numpy zones | **12.1 s** | order_blocks 16.6→5.8 s (2.8×), byte-identical |
| `6b89b22` | **B1** — vectorize decision_signals | — | signal precompute 100–490×, +18 equiv tests, bit-identical |
| `6bab4e2` | **B2** — inject signal into engine | — | fine TFs −36…−58%, all 6 golden byte-identical |
| `e20c8b8` | **B3a** — numpy df_4h row access | — | fine TFs further −14…−19%, all 6 golden byte-identical |
| `7fc9655` | **B3b** — numpy 1-min exit walk | — | Axis B complete, all 6 golden byte-identical |

Revert any step: `git revert <sha>`. Reset to pre-optimization: `git reset --hard f9d6f36`.

### Axis-B clean benchmark (baseline `manual_bg` → `B3b_exitwalk_numpy`, idle box)
| TF | baseline | after Axis B | Δ |
|----|--------:|-------------:|---:|
| 4h | 13.7 s | 11.1 s | −19% |
| 1h | 21.2 s | 15.8 s | −25% |
| 15m | 43.7 s | 21.9 s | **−50%** |
| 5m | 96.3 s | 35.2 s | **−63%** |
| 2m | 269.1 s | 89.4 s | **−67%** |

---

## Results so far (all proven results-UNCHANGED, golden vote-hashes byte-identical every step)

- **4h backtest: 36.2 s → 12.1 s (−67%)** after D+A1+A2+E+C′ (Axis A). **166 tests passing** (+18 from B1).
- **Axis B (per-decision loop, B1–B3b): fine-TF backtests −50…−67%** (15m 43.7→21.9 s, 5m 96.3→35.2 s,
  **2m 269.1→89.4 s**), all 6 golden baselines byte-identical at every step. See
  `perf/INVESTIGATION_axisB_per_decision_loop.md` + `perf/ACTION_PLAN_axisB.md` + `perf/UPDATE_step_B*.md`.
  The slow `engine.SimpleStrategy` (used only by `build_payload`/dashboard/standalone — the optimizer uses
  `fast_engine`) now reads a precomputed numpy signal + numpy OHLC arrays instead of per-bar pandas.
- Per-function micro-benchmarks (all bit-identical on the real 486,969-bar 1-minute series):
  obv 540 ms→8 ms (64×) · bollinger 6,375 ms→159 ms (40×) · cci 3,567 ms→925 ms (4×) ·
  order_blocks (E+C′, sampled) 16.6 s→5.8 s (2.8×).
- **Plan corrections discovered by profiling:** (1) **B (de-dup SMC) dropped** — the "second
  order_blocks" is the cheap ~0.05 s decision-frame call, not a ~9 s duplicate; (2) **C (Numba) blocked**
  here (Python 3.14 has no numba wheel + PEP 668 forbids a safe install) → replaced by the dependency-free
  **C′ numpy-zone rewrite**.
- Remaining order_blocks cost ≈ 5.8 s is now the outer Python loop + `market_structure` (~2.2 s).

## Golden baselines (immutable reference, frozen at Phase 0)

| TF | P/L | DD | n | trades SHA |
|----|----:|---:|--:|:----------:|
| 4h | $142,203 | $14,082 | 214 | 64bd6101 |
| 2h | $91,996 | $16,331 | 262 | d082404d |
| 1h | $99,172 | $16,870 | 315 | af13d36b |
| 15m | $77,098 | $7,889 | 654 | cf7d893e |
| 5m | $23,926 | $4,636 | 332 | e1bb7c2e |
| 2m | $29,777 | $3,261 | 276 | 9716070e |

Plus a per-indicator per-decision-bar **vote-hash** per TF (catches indicator-level drift).

## Verification cadence (per step)
1. equivalence unit tests (`tests/test_speedopt_equiv.py`) — optimized == frozen `_reference`, random +
   adversarial, tight tolerance;
2. golden byte-match on coarse TFs (4h/2h/1h) via `perf/check_golden.py`;
3. `optimize/test_parity.py` + `optimize/test_indicator_parity.py` + full `pytest`;
4. micro-benchmark; verbose update report; one commit.
**Phase boundary:** full 6-TF golden check (incl. 15m/5m/2m).

## Two cost axes (measured)
1. **1-minute indicator compute** (TF-independent) — what Phase 1–2 target.
2. **Per-decision-bar `build_payload` loop** — dominates *fine* TFs (5m 113 s, 2m >600 s). A later step
   (Phase 3) can attack this.

## Pending / next
- A3 (finish classic vectorizations), B (de-dup SMC), then Phase 2 (Numba SMC + cache) — each
  approval-gated. Current test count: **127 passing**.
- Related research: `optimize/RESEARCH_indicator_recurrence_relations.md` (incremental-recurrence study).
