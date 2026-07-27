# Closeout — Test-Suite Repair (2026-07-27)

**Issue:** #66 · **Branch:** `fix/issue66-failing-tests` · **Status:** ✅ CLOSED — suite green

The performance workstream (#54) left **25 failing tests** on `dev`/`main`. They were proven *not* caused
by that work (a control run on unmodified code produced the identical failure set) but were undiagnosed.
This closes them.

---

## 1. Headline

**25 failing → 0.** Not one was flaky, and **not one was a product bug**. Every failure was a test that had
drifted out of step with a deliberate change. The **golden gate stayed 6/6 byte-identical throughout** —
which is exactly why the failures were suspicious rather than alarming: the champion path was provably
correct while the tests describing it were not.

## 2. The five root causes

| # | Class | Tests | What actually happened |
|---|---|---:|---|
| 1 | **Undefined variable** | 3 | `test_intracandle_parity` passed `m_open=MO` but never defined `MO` → `NameError`. The file could not run at all. |
| 2 | **Missing time cap** | (same 3) | `build_params()` does not carry `cap_1min`/`cap_mode`, but the exact engine applies them — so the fast and exact sides were **comparing different strategies** (exact produced `TIME_CAP` exits the fast side could not). |
| 3 | **Stale champion anchors** | ~14 | Numbers pinned before the 2026-07-22 gap-aware-fill champion adoption: 214/$142,203, 255/$149,989, 34/$25,383, 289/$175,372. |
| 4 | **Superseded champion set** | 2 | Tests asserted against `wsh4_*`, but the deployed set moved to `best_*` (`DEFAULT_CHAMPION_SET`; +31.6% 2026 OOS, UI-verified 31/31). |
| 5 | **Signature / path drift** | 4 | A monkeypatch stub `lambda inst:` after `_instrument_champions_path` gained a `cset` parameter → `TypeError`; and an ES box path retired on 2026-07-06 in favour of the `-1`-workday shifted box. |
| — | **Collection abort** | (all) | `local_dash_test.py` ran `sync_playwright().chromium.launch()` at **module level**; pytest imports it by name, so on a box without Chrome it aborted collection for the **entire suite** — the reason a run could report "1 error, no tests ran". |

## 3. The subtle one — lean vs champion

The last five failures shared a single cause worth recording, because it will recur:

```python
legacy = l1_runner.run_l1("4h")                     # the FROZEN LEAN oracle  -> 255 trades
res    = logbook.run_causal(l1_default_params("4h"))# the DEPLOYED CHAMPION   -> 277 trades
assert l1_entries == legacy_entries                 # can never agree
```

There are **two different 4h L1s**, and the default silently moved from one to the other:

| path | serves | trades |
|---|---|---:|
| `l1_runner.run_l1("4h")` / `run_l1_cached("4h")` / `frozen_lean_params()` | frozen **lean** oracle | **255** |
| `run_causal(l1_default_params("4h"))` | deployed **champion** | **277** |

Tests whose stated intent is *"the causal log matches the legacy oracle"* were fixed by pinning the causal
side to `frozen_lean_params("4h")` — restoring the comparison rather than re-baselining the numbers.

**A second-order discovery:** even the frozen lean anchor's P/L moved, **$149,989 → $154,646**, because
gap-aware fills changed the **engine** for every strategy. Its trade count (255) and DD ($15,491) were
unaffected. An "anchor" is only frozen with respect to the engine that produced it.

## 4. How the re-baselines were kept honest

Re-baselining tests to current behaviour is how real regressions get hidden. Three rules were applied:

1. **Anchor to the golden baseline, not to the code.** Every champion figure traces to `perf/golden/4h.json`
   — $151,655 / 277 — independently verified by `perf/check_golden.py`, not to "whatever the code printed".
2. **Reconcile independently.** Combined = 325 = 277 + 48; $176,154 = $151,655 + $24,498. The legacy engine
   returned $24,746 for L2-on-lean, matching the causal path exactly.
3. **Measure, don't infer.** Every new constant was produced by running the code and reading the value,
   then cross-checked against a second path.

## 5. A mistake worth recording

A blanket `255 → 277` replace across the `l2` test directory **broke three tests that were passing**, because
`run_l1_cached()` serves the *lean* oracle (255) while `run_causal(l1_default_params())` serves the
*champion* (277). Caught by the next test run and reverted precisely.

> **Lesson, now a rule: a pinned number is meaningless without knowing which code path produced it.
> Verify per assertion — never `sed` across a directory.**

## 6. Result

| | before | after |
|---|---:|---:|
| failing | **25** | **0** |
| passing | 834 | 879 |
| collection errors | 1 (aborted the whole suite) | 0 |
| golden gate | 6/6 | 6/6 (unchanged throughout) |

**No product code was modified** — the diff is confined to test files and one browser script. The golden
gate therefore remains valid without re-running, though it was re-run anyway.

## 7. Honest gaps

1. **`local_dash_test.py`'s expected values were not verified.** It is a manual browser script needing a
   running dashboard; it now imports cleanly and skips, but its four pinned P/L figures (e.g. NQ 4h
   $148,670) predate the champion adoption and are **probably stale too**. Anyone running it should expect
   mismatches and re-verify against the current playbooks.
2. **Some re-baselined constants are derived stats** (`box_silence_total` 1290 bars, `noentry_streak_n`)
   that were re-measured but have no second source to cross-check against, unlike the P/L figures.
3. The suite takes **~9 minutes**; the intra-candle parity tests dominate (~80 s each) because they now
   genuinely run instead of erroring instantly.

## 8. Recommended next step

Treat "the suite is green" as a real gate again — it now is. Wire it into the pre-merge checklist alongside
the golden gate, so the next drift is caught in days rather than months.
