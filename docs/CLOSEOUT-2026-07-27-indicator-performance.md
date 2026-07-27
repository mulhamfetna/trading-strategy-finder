# Closeout — Indicator Performance Workstream (2026-07-27)

**Issues:** #54 (root) → #56, #57, #58 · **PRs:** #55, #59, #60, #61 (all merged to `dev`)
**Open follow-up:** #62 · **Status:** ✅ **CLOSED — clean handoff point**

---

## 1. The question that started it

> *"Our optimizer spends ~98% of its time computing indicators and only ~2% backtesting. Should we
> pre-compute every indicator once and store it — files? a database? a vector DB? a graph DB? Redis? RAM?
> GPU VRAM? — and would a GPU, an NVIDIA box, or an ARM box help?"*

## 2. The answer

**No pre-computed store. No new hardware.** The 98% was neither a storage problem nor an
arithmetic-throughput problem. It was **one indicator implemented as an extremely slow Python loop.**

| | |
|---|---|
| Root cause | `dfa` — a triple-nested loop calling `np.polyfit` ~10⁸ times, **81% of all indicator compute** |
| Fix | closed-form OLS + Numba, one pass |
| Result | **1,150–1,396×** faster, **zero** trading-decision changes |
| End-to-end | a 3-trial profile went **208 s → 40 s (5.1×)** on identical work |
| Hardware needed | **none** — ran on the CPU box we already own |

---

## 3. Everything measured (all on the real 486,969-bar NQ 1-minute frame, AMD server)

### 3.1 The three structural findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **Pre-computing all combinations is impossible** | 165 indicators × their grids = **~4.0 billion** combos ≈ **3.9 PB** for one instrument — ~32,000× the server disk |
| 2 | **The cache was already built** | `core._VOTE_MEMO` (memory) + `vote_cache.py` (disk) — the same two-level design Microsoft's Qlib uses |
| 3 | **One indicator was 81% of the cost** | `dfa` = 167 s of 206 s cold compute in the first profile |

### 3.2 Indicator accelerations (all vote-identical, all parity-gated)

| indicator | before | after | speed-up | vote flips |
|---|---:|---:|---:|:---:|
| `dfa` n=400 | **756.6 s** (12.6 min) | 0.658 s | 1,150× | **0** |
| `dfa` n=100 (default) | 248.3 s | 0.178 s | **1,396×** | **0** |
| `dfa` n=20 | 57.0 s | 0.044 s | 1,309× | **0** |
| `autocorr` n=200 | 9.47 s | 0.081 s | **116×** | **0** |
| `hurst_exp` n=400 | 5.24 s | 0.233 s | **22×** | **0** |

### 3.3 Whole-profile effect (identical work — same seed, same 233 cold computes)

| | before | after |
|---|---:|---:|
| wall clock (3 trials) | 208 s | **40 s (5.1×)** |
| cold compute | 206 s (99%) | 39 s |
| `dfa` share of cold time | **81%** | **0.42%** |

### 3.4 Worst-case parameter cost — the number to plan against

| all 165 indicators, full frame | |
|---|---:|
| at **sampled** parameters | ~39 s |
| at **worst-case** parameters | **123.6 s → 111.1 s** (after the tail fixes) |
| over a 2 s budget | **19 → 17** indicators (73.1 s → 60.2 s) |

### 3.5 Cache substrate — measured, NO-GO on everything

| substrate | p50 read | verdict |
|---|---:|---|
| `shared_memory` | 0.36 µs | 43× faster — but saves only 15 µs |
| **`.npy` (current)** | **15.32 µs** | keep |
| tmpfs `/dev/shm` | 15.17 µs | noise |
| **Redis** | **24.70 µs** | **1.6× slower** |
| mmap | 29.24 µs | 1.9× slower |

**Two independent kills:** a read is **0.009%** of the compute it replaces (15 µs vs ~167,000 µs), **and**
the disk cache's hit rate in a fresh sweep is **0.00** (1,995 lookups / 30 trials) — sweeps never repeat
parameters and every fold is a distinct slice. *Arrow Plasma excluded — removed in Arrow 12.0.0 (verified).*

---

## 4. Corrections we made to our own claims

Recorded because each was asserted confidently before being checked:

| Claim | Status |
|---|---|
| "`mode` in the cache key causes 3× confirm/veto/both duplication" (#54, #58) | ❌ **False** — `_suggest_indicators` fixes `mode` to the schema default and never searches it |
| "There is no second `dfa`; the tail is diffuse, ~40→33 s, don't over-invest" (#54) | ⚠️ **Half wrong** — measured at *sampled* parameters. At grid edges **19 of 165** blow a 2 s budget (73 s) |
| The standing hot list (`order_blocks`/`bollinger`/`cci`) | ❌ **Stale** — written at 21 indicators; now marked SUPERSEDED |
| First worst-case scan reporting `dfa` at 5.52 s | ❌ **Measurement artifact** — timed the *first* call, extrapolating Numba JIT compile ×24. Caught only because an independently measured 0.178 s existed to contradict it |

---

## 5. What shipped

### Code (`indicators/calc/quant.py`)
`dfa`, `autocorr`, `hurst_exp` now dispatch to Numba closed-form fast paths. Originals retained **verbatim**
as `dfa_reference` / `autocorr_reference` / `hurst_exp_reference` — the parity oracles. **Without numba the
code falls back to the reference**, so a missing optional dependency can never change a number.
`numba` added to `requirements.txt` as optional.

### Harnesses (`optimize/perf/`, indexed in its `README.md`)
`cache_probe.py` (result-neutral counters) · `run_baseline.py` (isolated real-optimizer profile) ·
`bench_dfa.py` · `bench_worstcase.py` (grid-corner scan) · `bench_substrate.py` · 15 parity/probe tests.

### Documentation
| Document | Role |
|---|---|
| **`docs/EXPANSION_ROUND_PLAYBOOK.md`** | **The standing rules** — read before/after any expansion round |
| `optimize/REPORT_indicator_cache_acceleration.md` | the #54 investigation end-to-end |
| `optimize/REPORT_post_dfa_tail.md` | worst-case parameter picture (#56) |
| `optimize/REPORT_cache_substrate_and_level.md` | substrate/level, measured (#58) |
| `docs/PRIOR_ART_indicator_caching_gpu.md` | vectorbt / Qlib / talipp / wickra / RAPIDS deep scrape |
| `optimize/perf/README.md` | every harness, artifact and raw log, with reproduction commands |
| `docs/PERFORMANCE.md` **§10** | folded into the authoritative speed doc |
| `optimize/REPORT_backtester_speed_optimization.md` | marked **⚠️ SUPERSEDED** (21-indicator era) |

### Evidence
8 raw server logs in `optimize/perf/logs/` (including **both control runs**) and 8 result JSONs in
`optimize/perf/results/`. Every number in every report traces to one of them.

---

## 6. Correctness — how we know nothing changed

### 6.0 The GOLDEN GATE — 6/6 byte-identical (the definitive proof)

Run on the server against `dev` immediately before the `dev → main` promotion
(`perf/check_golden.py`, log: `optimize/perf/logs/goldengate_dev_2026-07-27.log`). It re-runs every
champion timeframe and asserts **exact** summary metrics, a **SHA-256 match on the taken-trade ledger**,
and a **SHA-256 match on every enabled indicator's per-decision-bar vote array**:

```
[4h]  ✅ MATCH  (P/L $151,655, n=277, 8 indicators)
[2h]  ✅ MATCH  (P/L $101,518, n=173, 8 indicators)
[1h]  ✅ MATCH  (P/L $110,038, n=353, 7 indicators)
[15m] ✅ MATCH  (P/L  $82,156, n=654, 8 indicators)
[5m]  ✅ MATCH  (P/L  $20,092, n=314, 7 indicators)
[2m]  ✅ MATCH  (P/L  $31,898, n=276, 7 indicators)

✅ ALL GOLDEN BASELINES MATCH — results unchanged.
```

**This is the strongest statement available:** three indicators were rewritten and made up to 1,396×
faster, and **not one hash moved**. It also independently corroborates that the 25 failing tests (§6, last
bullet) are not real regressions — the golden gate exercises the actual champion path end-to-end and is
clean.

- **Parity contract:** these are **veto** indicators, so the binding requirement is the veto *decision*, not
  the float. `np.polyfit` goes through LAPACK, so bit-identity is impossible; **zero differing decisions
  across each indicator's entire searched threshold grid** on the real series is what was proven.
- **15 tests** green, including end-to-end tests driving the real Indicator objects.
- **Control runs:** the full suite was run on identical trees with and without the changes. **Same 25
  failures, empty diff both directions ⇒ zero regressions.**
- **Those 25 failures are pre-existing** (`optimize/l2/*`, `test_intracandle_*`; none touch `quant`).
  `test_parity_anchor.py` is a known-stale test; `test_intracandle_parity.py` had uncommitted local edits
  before this work. Some may be an artifact of the server deploy excluding `*.csv`. **They were not
  individually diagnosed** — the control established only that this work did not cause them. ⚠️ **This is
  the top open risk for the next agent** (see §8).

---

## 7. Honest gaps

1. **The 25 pre-existing test failures are undiagnosed** (proven not ours, but unexplained).
2. **17 indicators remain over the 2 s budget** (~60 s worst-case) — tracked as **#62**.
3. **Worst-case projections for those 17 are extrapolated** from a 20,000-bar subset (validated to within
   3% on the two measured at full scale).
4. **Only grid corners tested** (all-min / all-max / defaults) — a peak at a *mixed* parameter combination
   could be missed.
5. **Hit rate measured on a deliberately cold cache**; a production run against the accumulated 4.3 GB
   cache could differ on repeated studies.
6. **Per-fold `directions()` sharing was reasoned, not tested** — inferred non-result-neutral from how
   warm-up works. That assumption is the thing to test first if anyone wants that win.
7. **Single instrument (NQ)** — cost should be data-shape-independent for fixed parameters, unverified.

---

## 8. Handoff — state of the world

**Branch state:** `dev` = `main` (this closeout), all four workstream PRs merged, all worktrees removed,
server scratch cleaned.

**If you are the next agent, read in this order:**
1. `docs/EXPANSION_ROUND_PLAYBOOK.md` — the rules, especially before adding indicators
2. `docs/PERFORMANCE.md` §10 — the current cost picture
3. `optimize/perf/README.md` — how to re-measure anything here

**Top open risks / next actions**

| Priority | Item | Where |
|---|---|---|
| 🔴 **1** | **Diagnose the 25 failing tests.** Proven not caused by this work, but a suite with 25 red tests cannot gate anything. Start by checking whether they pass on a clean local `dev` with full `*.csv` results present. | — |
| 🟡 2 | Work the 17 over-budget indicators down to 2 s; prioritize the ones expensive at **default** params (`sinewave`, `ifvg`, `cmo_chande_dmi`, `ichimoku_cloud`) | **#62** |
| 🟡 3 | Wire `bench_worstcase.py` into CI / the expansion-round checklist so a new indicator cannot silently reintroduce a 12-minute compute | #62 |
| 🟢 4 | Consider bumping `vote_cache.CACHE_VERSION` if any future indicator change is *not* vote-identical | — |

**Explicitly closed — do not reopen without new evidence:** pre-computing all indicator combinations
(impossible, 3.9 PB) · every cache substrate change (0.009% of cost, 0.00 hit rate) · GPU / NVIDIA / ARM
hardware (the bottleneck was algorithmic, and the CPU fix beat published GPU speed-ups for comparable work).
`REPORT_cache_substrate_and_level.md` §7 states exactly what evidence *would* reopen the substrate question.

---

## 9. The lesson, in one line

> **Correctness is gated on every PR; cost is gated on none — so measure first. We were one decision away
> from buying a GPU to fix a Python loop.**
