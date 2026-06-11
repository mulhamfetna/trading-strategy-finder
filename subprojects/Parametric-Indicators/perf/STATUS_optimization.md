# Backtester Speed Optimization — PINNED STATUS (task #210)

**Updated:** 2026-06-11 · branch `dev` (local only, not pushed). Single source of truth for where the
optimization stands. Each step has its own `perf/UPDATE_step_*.md`; this pins the whole picture.

---

## Plan (from `optimize/REPORT_backtester_speed_optimization.md`)

| Phase | Steps | Status |
|-------|-------|--------|
| **0 — Safety net** | golden baselines + harness + equivalence framework | ✅ done |
| **1 — Vectorize + de-dup** | D obv · A1 bollinger · A2 cci · A3 stochastic/atr/keltner/mfi · B de-dup SMC | ◑ D/A1/A2 done; A3, B pending |
| **2 — JIT + cache** | F cache 1-min sampling map · C Numba SMC loops | ⏳ pending |
| **3 — Polish (optional)** | E sampled-overlap · G thread indicators · H Numba exit walk | ⏳ pending |

---

## Commits (rollback points) on `dev`

| SHA | Step | Result |
|-----|------|--------|
| `f9d6f36` | Phase 0 safety net | golden baselines (6 TFs) + check_golden + bench + equiv framework — **the rollback anchor** |
| `e76448` | D — vectorize obv | 64×, bit-identical |
| `1f1c29f` | A1 — vectorize bollinger | 40×, bit-identical |
| `f178ec3` | A2 — vectorize cci | 4×, bit-identical |

Revert any step: `git revert <sha>`. Reset to pre-optimization: `git reset --hard f9d6f36`.

---

## Results so far (all proven results-UNCHANGED)

- **4h backtest: 36.2 s → 25.6 s (−29%)** after D+A1+A2. Per-function micro-benchmarks: obv 540 ms→8 ms
  (64×), bollinger 6,375 ms→159 ms (40×), cci 3,567 ms→925 ms (4×) — each **bit-identical on the real
  486,969-bar 1-minute series**.
- The big remaining lump is **`smc.order_blocks` ~18.5 s** (computed ~2×) — addressed by **B** (de-dup)
  then **C** (Numba). Classic rolling indicators are mostly done.

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
