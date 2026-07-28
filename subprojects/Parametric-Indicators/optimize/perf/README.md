# `optimize/perf/` — performance harnesses & artifacts

Everything here was produced by the indicator-performance workstream (**#54 → #56/#57/#58 → #62**).
All measurements ran on the AMD server (`ssh amd-trading`, 32 cores / 123 GB RAM, no GPU) against the real
**486,969-bar NQ 1-minute frame**. Nothing here runs in the production optimizer path; every accelerator
lives in `indicators/calc/quant.py` behind a numba-optional fallback.

> **Read first:** [`docs/EXPANSION_ROUND_PLAYBOOK.md`](../../../../docs/EXPANSION_ROUND_PLAYBOOK.md) —
> the rules these tools exist to enforce.

---

## Tools

| File | What it does | Typical invocation |
|---|---|---|
| `cache_probe.py` | **Result-neutral** instrumentation. Wraps `vote_cache.get/put` and `runner._ind_vote` to count cache hits/misses, bytes, and **cold-compute wall-clock per indicator**. Arrays pass through unchanged. | used by `run_baseline.py` |
| `run_baseline.py` | Runs the **real optimizer** for N trials with the probe installed, isolated via a throwaway `WSH_JOURNAL_DIR` + cold `vote_cache` (zero production pollution). Emits the cold/warm/IO split + per-indicator cold-cost ranking. | `python3 -m optimize.perf.run_baseline --tf 4h --trials 30` |
| `bench_dfa.py` | Times `dfa` reference vs accelerated at n∈{20,100,400} on the real frame and re-verifies **zero vote flips** across the full threshold grid. | `python3 -m optimize.perf.bench_dfa` |
| `bench_worstcase.py` | Scans **every** registered indicator at defaults / all-min / all-max, projects to the full frame, and **exits non-zero if anything is over the budget** — so it is a gate, not a report. **The automated form of playbook rule P4.** ⚠️ It builds a single-instrument context, so the four cross-series indicators short-circuit and time at 0.00 s: that is "never ran", not "cheap". | `python3 -m optimize.perf.bench_worstcase --bars 20000 --budget-s 2.0` |
| `probe_xseries.py` | **Issue #74.** The four-question harness for the CROSS-SERIES indicators, which every other scan is blind to: `wiring` (do they emit anything on the production `--ind-1min` path?) · `control` (do they on the decision-TF path with the same reference?) · `cost` (what would they cost on the 1-minute frame if wired) · `parity` (accelerated vs reference on the **FULL** frame — deliberately NOT the cost subset). It is what found #75. | `python3 -m optimize.perf.probe_xseries --tf 4h --instrument NQ --reference ES` |
| `bench_budget.py` | The **#62 evidence harness**. Five phases on the real frame: `primitives` (bit-identity of the shared leaves) · `exactness` (per-accelerator value diff, plus the decision-boundary MARGIN where 1 ULP is unavoidable) · **`control`** (compares every function to ITSELF — any non-zero flip means the harness is broken) · `votes` (emitted confirm/veto arrays, fast vs reference, swept across the searched grid) · `timing`. Swaps implementations by **identity across every loaded `indicators.*` module**, because the leaves are bound at import time. | `python3 -m optimize.perf.bench_budget --phases primitives,exactness,control,votes,timing` |
| `bench_substrate.py` | Times cache retrieval through `.npy` / tmpfs / mmap / `shared_memory` / Redis / dict at 1 and N readers, on **real** cached arrays. | `python3 -m optimize.perf.bench_substrate --n-files 300 --readers 30` |
| `cold_accel.py` | Thin aliases (`dfa_fast`, `dfa_reference`) so benchmarks read naturally and `indicators/` never imports `optimize/`. | — |

**Tests:** `test_cache_probe.py` (probe is result-neutral), `test_cold_accel_parity.py` (`dfa` vote-identity),
`test_tail_accel_parity.py` (`autocorr` / `hurst_exp` vote-identity), `test_budget_accel_parity.py` (**#62** —
bit-identity for the shared leaves, the SMC state machines and the whole window-statistic family; vote-identity
for the three Ehlers filters; plus a `pw_sum`-matches-numpy test and a deliberately-wrong-implementation test
so the gate cannot go vacuous).

⚠️ **CI has no Numba, so every dispatcher falls back to its own reference and a naive parity test compares
the reference to ITSELF — green, and proving nothing.** `test_budget_accel_parity.py` monkeypatches
`_HAVE_NUMBA = True`; `njit` is then a no-op decorator, so the kernel body still runs (in pure Python) and its
LOGIC is checked in both environments. This is not paranoia: 84 local tests passed and the server deploy
immediately **segfaulted**, because a *recursive* `@njit` called from inside another kernel crashes under
Numba 0.65 — locally it had been ordinary Python recursion. **Always run the accelerated path on a box that
has the accelerator before believing a green suite** (playbook C11/C13).

⚠️ **When timing anything here, warm up first.** `bench_worstcase.py` calls each configuration twice and
times only the second. The first version did not, so **Numba JIT compile time was extrapolated ×24** and it
reported `dfa` at 5.52 s against a measured 0.178 s.

---

## Artifacts — `results/`

| File | Produced by | What it shows |
|---|---|---|
| `baseline_NQ_4h_smoke3.json` | `run_baseline` (3 trials, **before** any fix) | **The finding that redirected the workstream:** cold = 206 s of 208 s wall (99%); **`dfa` = 167 s = 81% of all indicator compute** |
| `baseline_NQ_4h_after_dfa.json` | `run_baseline` (3 trials, **after** the `dfa` fix) | Same seed ⇒ same trials, **same 233 cold computes** ⇒ apples-to-apples: wall **208 s → 40 s (5.1×)**; `dfa` 167 s → 0.161 s (81% → 0.42%) |
| `baseline_NQ_4h_30trials.json` | `run_baseline` (30 trials) | The **hit-rate** measurement: 1,995 lookups, **hit_rate = 0.00**; wall 317 s, cold 301 s (95%) |
| `dfa_bench_NQ_1m.json` | `bench_dfa` | `dfa` on the real frame: n=20 **1,309×**, n=100 **1,396×**, n=400 **1,150×** (756.6 s → 0.658 s), **0 vote flips** at every n |
| `tail_bench.json` | ad-hoc (see `REPORT_post_dfa_tail.md`) | `autocorr` 9.47 s → 0.081 s (**116×**), `hurst_exp` 5.24 s → 0.233 s (**22×**), 0 vote flips |
| `worstcase_scan.json` | `bench_worstcase` (**before** tail fixes) | **19 of 165** indicators over a 2 s budget = 73.1 s; all 165 worst-case = **123.6 s** |
| `worstcase_scan_after.json` | `bench_worstcase` (**after** tail fixes) | **17** over budget = 60.2 s; all 165 = **111.1 s** |
| `substrate_bench.json` | `bench_substrate` | `.npy` 15.32 µs · tmpfs 15.17 µs (noise) · `shared_memory` 0.36 µs · **Redis 24.70 µs (1.6× slower)** · mmap 29.24 µs |

## Raw evidence — `logs/`

Verbatim server output, kept so every number in the reports is traceable to a run.

| File | Contents |
|---|---|
| `issue54_dfa_bench.log` | the `dfa` before/after timings as they were produced |
| `issue54_rebaseline.log` | the 3-trial re-baseline proving 208 s → 40 s |
| `issue54_full_pytest.log` | full suite **with** the `dfa` fix — 25 failed / 834 passed |
| `issue54_ctrl_pytest.log`, `issue54_ctrl_targeted.log` | the **control** run on an identical tree with the *original* code — the same 25 failures, proving **zero regressions** |
| `issue56_worstcase.log` | the worst-case parameter scan |
| `issue56_full_pytest.log` | full suite with the tail fixes — 25 failed / 854 passed (same 25) |
| `issue58_hitrate.log` | the 30-trial run showing `hit_rate = 0.00` throughout |

**About those 25 failures:** they are **pre-existing** and unrelated to this work — proven by running the
identical suite against unmodified code and diffing the failure sets (empty both directions). They sit in
`optimize/l2/*` and `test_intracandle_*`; none touch `quant`. `test_parity_anchor.py` is a known-stale test
and `test_intracandle_parity.py` had uncommitted local edits before this workstream began. Some may also be
an artifact of the server deploy excluding `*.csv`. **They were not individually diagnosed** — the control
established only that this work did not cause them.

---

## Reproducing

```bash
# on the server (the venv has numpy/pandas/optuna/scipy/numba)
cd <deploy>/Parametric-Indicators
export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
/home/dev/Mulham/.venv/bin/python3 -m optimize.perf.run_baseline    --tf 4h --trials 30
/home/dev/Mulham/.venv/bin/python3 -m optimize.perf.bench_worstcase --bars 20000 --budget-s 2.0
/home/dev/Mulham/.venv/bin/python3 -m optimize.perf.bench_dfa
```

`run_baseline` isolates itself (throwaway journal store + cold cache) and cleans up after itself, so it is
safe to run alongside production work.
