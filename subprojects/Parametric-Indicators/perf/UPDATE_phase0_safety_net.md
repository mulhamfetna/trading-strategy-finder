# Update Report — Phase 0: Safety Net (no engine changes)

**Date:** 2026-06-11 · branch `dev` · task #210 · plan phase **0 of 3**
**Type:** infrastructure only — **zero engine/behavior change.** This builds the verification scaffolding
that every later optimization step is gated on.

---

## 1. What & why (plain + professional)

**Professional.** Before optimizing the backtester we froze the current engine's exact outputs as
immutable **golden baselines** across all six champion timeframes, plus a benchmark harness and an
equivalence-test framework. Optimizations are only accepted if they reproduce these baselines
byte-for-byte.

**Baby.** We took perfect "before" photographs of the machine's answers in six situations and locked them
in a safe. From now on, after we change anything, we re-take the photo and compare to the locked one. If a
single number differs, the change is rejected.

---

## 2. Files added (all under `perf/`, no engine touched)

| File | Role |
|------|------|
| `perf/_common.py` | shared loader: builds each TF's champion bundle (candles + 1m + box + HAR-RV + preset) exactly as `build_payload` consumes it; plus per-indicator vote extraction. |
| `perf/capture_golden.py` | freezes the CURRENT outputs → `perf/golden/<tf>.json` (summary + SHA-256 of trades + SHA-256 of every indicator's vote array) + `<tf>_trades.csv` + `<tf>_votes.npz`. |
| `perf/check_golden.py` | **the regression gate** — re-runs the engine and asserts byte-equality vs the golden (summary + trades hash + every vote hash). Non-zero exit on any drift. |
| `perf/bench.py` + `perf/bench_history.json` | times a full backtest per TF; appends a labelled record so every step has before/after numbers. |
| `perf/equiv.py` | equivalence framework: random + **adversarial** input generators (constant / monotonic / leading-NaN / mid-NaN / tiny / jump series) + `assert_equiv` (NaN-for-NaN, tight tolerance). Used by Phase 1/2 per-indicator tests. |

---

## 3. Golden baselines frozen (the immutable reference)

| TF | net P/L | max DD | trades (n) | trades SHA | indicators |
|----|--------:|-------:|-----------:|:----------:|:----------:|
| 4h | $142,203 | $14,082 | 214 | `64bd6101` | 8 |
| 2h | $91,996 | $16,331 | 262 | `d082404d` | 8 |
| 1h | $99,172 | $16,870 | 315 | `af13d36b` | 8 |
| 15m | $77,098 | $7,889 | 654 | `cf7d893e` | 8 |
| 5m | $23,926 | $4,636 | 332 | `e1bb7c2e` | 7 |
| 2m | $29,777 | $3,261 | 276 | `9716070e` | 7 |

Each golden also stores a **SHA-256 of every enabled indicator's per-decision-bar vote array** — so a
change that alters an indicator's output is caught even if the final trade set happens to be unchanged.

---

## 4. Baseline performance (the "before" we must beat)

One full backtest, current engine (warm single run):

| TF | 4h | 2h | 1h | 15m | 5m | 2m |
|----|---:|---:|---:|----:|---:|---:|
| seconds | 36.2 | 17.9 | 36.1 | 84.4 | 113.4 | >600 (timed out) |

(In `perf/bench_history.json`, label `baseline`.) **New finding beyond the report:** the fine timeframes
(5m, 2m) are far slower than 4h — so there are **two** cost axes, not one: (a) the 1-minute *indicator*
compute (TF-independent, ~the 4h cost) and (b) the per-decision-bar Python work in `build_payload`
(event/attribution/sampling loops) which scales with the *number of decision bars* and explodes on fine
TFs. Phase 1–2 target axis (a); a later step can attack axis (b) if needed.

---

## 5. The verification ritual these enable (used every later step)

1. **test-first** equivalence unit test (optimized fn == kept reference) on random + edge inputs;
2. `python3 perf/check_golden.py` → all 6 byte-match;
3. `optimize/test_parity.py` + `optimize/test_indicator_parity.py` + full `pytest` (88);
4. `perf/bench.py <label>` → record the speed-up;
5. verbose update report (this format) + a separate commit.

> **Verification cadence (refined after measuring):** a full 6-TF golden check runs six real backtests +
> a vote recompute — with 5m≈113s and 2m>600s that is ~25 min, too slow to run every micro-step. Because
> the Phase 1–2 optimizations are all in **indicator math computed on the 1-minute frame** (TF-independent),
> the **equivalence unit tests** (`perf/equiv.py`, milliseconds, random + adversarial inputs) are the
> *primary* precision gate — if `optimized==reference` on the math, the votes and every downstream number
> are identical for **all** timeframes by construction. So the cadence is:
> 1. **every step:** equivalence unit tests (exhaustive, fast) **+** golden check on the **coarse TFs
>    (4h, 2h, 1h)** **+** `test_parity` + `test_indicator_parity` + `pytest`;
> 2. **every phase boundary:** the **full 6-TF** golden check (incl. 15m/5m/2m) as confirmation.
> This keeps math-level rigor on every change while keeping the loop practical.

---

## 6. Reverting Phase 0

Phase 0 adds only new files under `perf/` and changes **no** engine code, so there is nothing to "revert"
behaviorally. To remove the scaffolding entirely:
```bash
git rm -r subprojects/Parametric-Indicators/perf
git commit -m "remove perf safety net"
```
The Phase 0 commit SHA is recorded below and serves as the rollback point before Phase 1.

---

## 7. Status

- ✅ Safety net built; all 6 golden baselines frozen; baseline timings recorded.
- ⛔ No engine change yet.
- ▶️ Next: **Phase 1, Step 1 = B (de-duplicate the SMC compute)** — pending your approval.

**Phase 0 commit:** _(filled at commit)_
