# TEST SUITE TRIAGE — the 35 "pre-existing" failures on `dev` (2026-07-20, in progress)

**A test suite carrying 35 known-failing tests is not a safety net — it is camouflage. Today proved
exactly how expensive that is: three silent bugs in one file invalidated two workstreams' headline
results ([`BUG-01`](BUG-01-sizing-studies-ran-the-wrong-strategy.md)), and a suite nobody expects to be
green cannot warn you. This is the triage: what is genuinely broken, what is stale, and what is already
fixed.**

Branch `fundamental-analysis` · nothing in `optimize/l2/` modified (that is another workstream's code) ·
task #19.

---

## 0 — THE HEADLINE

| | |
|---|---|
| **Fixed today** | `optimize/test_news_veto.py` — 7 tests now collect where there were **0** |
| **Diagnosed, needs its owner** | the 3 `l2` parity anchors — **a stale test, not a regression** |
| **Still open** | l2 taxonomy/tf_defaults/payload, intracandle (#15), `test_ablate`, `test_instruments_comex` |
| **Confirmed** | none of these were caused by the FA merge — verified against the pre-merge baseline `5469bed` |

---

## 1 — ✅ FIXED: the `perf` import failure (and it was hiding more than a test)

**Symptom:** `optimize/test_news_veto.py` failed at *collection* with

```
ModuleNotFoundError: No module named 'perf._common'; 'perf' is not a package
```

which reads like the file is missing. It is not — `perf/_common.py` sits right there.

**Root cause:** `perf/` had no `__init__.py`, making it only a **namespace package**. Namespace packages
have the **lowest priority** in Python's import system — they are used only when no regular module of
that name exists anywhere on `sys.path`. This machine has the Linux perf-tool Python bindings installed
at `/usr/lib/python3/dist-packages/perf.cpython-314-x86_64-linux-gnu.so`, and **that system module wins**,
even with `sys.path.insert(0, ".")`.

**Why it mattered far beyond one test:** the same import is used by `study_vol_target.py` (sizing Z3) and
`run_nulltest.py`. Both were **unrunnable on any machine with that system package**, while working fine
on machines without it — the worst kind of environment-dependent failure. It is also why Z3 could not be
run locally at all when I went to wire it for the GC out-of-sample test.

**Fix:** added `perf/__init__.py` (documented, load-bearing). `perf/` becomes a regular package and
`sys.path[0]` wins outright. **7 tests now collect.**

> ⚠️ **I got this wrong twice before getting it right.** I first reported the test as "genuinely
> orphaned because `optimize/perf/` does not exist" — I had looked in the wrong directory (`perf/` is at
> the project *root*). Then I reported "`perf/*.py` are not tracked in git" — false; all 39 files are
> tracked. That came from reading `git ls-files perf/ | head`, where the uppercase `.md` filenames sort
> before `_` in ASCII, so `head` showed ten `.md` files and silently cut off every `.py`.
> **Lesson: never conclude from a truncated listing.**

---

## 2 — ✅ DIAGNOSED: the three `l2` parity anchors are STALE, not a regression

**Symptom:** three live assertions fail, and the drift is internally coherent:

| Layer | Pinned | Actual | Δ |
|---|---|---|---|
| L1 | 255 trades | **277** | +22 |
| L2 | 34 trades | **48** | +14 |
| Combined | 289 trades | **325** | +36 |

(277 + 48 = 325 — consistent, so this is one cause, not three.)

**Correction to my earlier note:** I recorded these as "documented as RETIRED/xfail pending the l2v2
re-optimization." **There are no `xfail` or `skip` markers in that file at all** — all three are live
assertions. That claim came from memory rather than from reading the file.

**Root cause (verified, not inferred).** The test pins the **frozen lean anchor's** numbers
($149,989 / 255 trades). But the 4h L1 default was **deliberately unlocked** from that anchor to the
optimized champion on 2026-07-11 — stated in `l1_default_params`' own docstring. Direct evidence:

```
l1_default_params('4h')   -> sl_soft 128.577  sl_hard 151.4424  tp 125.5612  gate 89.66   (champion)
frozen_lean_params('4h')  -> sl_soft 149.8    sl_hard 167.1     tp 120.2     gate 86.9    (frozen anchor)
```

`test_frozen_default_guard` **still passes**, so the routing *mechanism* is intact. Only the pinned
numbers are stale — the default now legitimately routes to a different, better champion.

```mermaid
flowchart TD
    A["test pins the FROZEN anchor<br/>$149,989 / 255 trades"] --> B{"what does the default<br/>resolve to today?"}
    B -->|"2026-07-11: deliberately unlocked"| C["the OPTIMIZED champion<br/>128.577 / 151.4424 / 125.5612"]
    C --> D["277 trades — a REAL, INTENDED change"]
    A --> E["test still asserts 255 => fails"]
    F["test_frozen_default_guard PASSES<br/>=> routing is fine"] --> E
```

**Recommended fix — for the L2/dev owner, deliberately NOT applied here.** Have the anchor tests pass
`frozen_lean_params()` **explicitly** instead of relying on whatever `l1_default_params` currently
returns. That preserves the guard's actual purpose — protecting the frozen cached oracle — independent
of which champion happens to be deployed. Re-pinning the anchors to the champion's new numbers is the
*worse* option: it re-couples the guard to a value that will move again at the next re-optimization.

`optimize/l2/*` belongs to another workstream. Re-pinning anchor numbers is a judgement call for its
owner, so this is documented and handed over rather than changed unilaterally.

---

## 3 — THE COMPLETE PICTURE (full suite, 2026-07-20)

**22 failed · 526 passed · 10 skipped.**

> ⚠️ **My earlier catalogue of these failures was itself built from truncated output.** The first run's
> failure list was read through `tail`, so I only ever saw the last ~19 of 36 lines and grouped the
> failures from a partial list. That is the *third* time in this session the same mistake produced a
> confident wrong statement — and it is the reason §2's "retired/xfail" claim was wrong too. The table
> below is from the complete list.

| Area | Count | Status |
|---|---|---|
| **`optimize/l2/*`** | **17** | **ONE root cause — see below** |
| `test_intracandle_parity` · `test_intracandle_engine` | 4 | task **#15** |
| `test_instruments_comex` | 1 | `resolve_paths_use_shifted_box` — separate |

### The 17 `l2` failures are all ONE cause — verified, not assumed

Every one of them carries the *same* drift signature:

| Test | Evidence |
|---|---|
| `test_parity_anchor::test_l1_anchor` | `277 == 255` — **+22** |
| `test_parity_anchor::test_l2_anchor` | `48 == 34` — **+14** |
| `test_logbook::test_causal_l1_matches_legacy_oracle` | *"Left contains **22** more items"* |
| `test_logbook::test_causal_l2_matches_legacy_engine` | *"Left contains **14** more items"* |
| `test_aggregate` (L1) | pnl **148,670** vs pinned **149,989** |
| `test_aggregate` (L2) | `48 == 34` |
| `test_logbook::test_cap_1min_produces_time_cap_exits` | `TIME_CAP` present where the control expects none |

**+22 and +14 are exactly the parity-anchor drifts.** And the `TIME_CAP` failure fits the same story: the
optimized champion preset carries **`cap_1min = 451`**, which the frozen lean anchor did not — so a
control case asserting "no time-cap exits" now sees them.

**Root cause for all 17: the 4h L1 default was deliberately unlocked from the frozen lean anchor to the
optimized champion on 2026-07-11.** These tests pin the frozen anchor's behaviour — trade counts, P&L,
and the absence of a time cap. They are **stale, not a regression.**

```mermaid
flowchart TD
    A["2026-07-11: 4h L1 default deliberately<br/>unlocked frozen anchor -> optimized champion"] --> B["different stops<br/>128.6/151.4/125.6"]
    A --> C["champion carries cap_1min=451"]
    B --> D["+22 L1 entries, +14 L2 entries<br/>pnl 149,989 -> 148,670"]
    C --> E["TIME_CAP exits appear"]
    D --> F["17 l2 tests fail — all STALE, one cause"]
    E --> F
```

### Recommended fix (for the L2/dev owner — deliberately NOT applied here)

Have these tests construct their fixture from **`frozen_lean_params()` explicitly** rather than relying
on whatever `l1_default_params()` currently returns. That keeps them guarding the frozen cached oracle —
their actual purpose — independent of which champion is deployed. Re-pinning to the champion's numbers is
worse: it re-couples the guard to a value that moves at every re-optimization.

`optimize/l2/*` belongs to another workstream; this is documented and handed over.

### Still open (not `l2`)

| Group | Count | Note |
|---|---|---|
| `test_intracandle_parity` (3) · `test_intracandle_engine` (1) | 4 | task **#15** |
| `test_instruments_comex` | 1 | `resolve_paths_use_shifted_box` |
| `local_dash_test.py` | collection | needs `playwright` installed |

*(`test_ablate` and `test_tf_defaults` failed in the earlier dev-worktree run but pass here — those were
environmental, a missing data file in that worktree.)*

---

## 4 — WHY THIS WORK IS WORTH DOING

The suite was dismissed as "35 pre-existing failures" and left alone. Investigating just two groups
found:

1. a **real environment-dependent import bug** that silently made two research studies unrunnable, and
2. a **live, unmarked assertion** guarding a load-bearing invariant, failing for a benign-but-unrecorded
   reason — meaning it can no longer warn anyone if the invariant *actually* breaks.

Neither was visible from the failure list. Both were invisible *because* the suite was already red.

**The principle:** a red suite has zero signal. Every failure must be either fixed, or marked `xfail`
with a written reason and an owner. "Known failing" without a marker is indistinguishable from "newly
broken," which is precisely the state that let today's silent-default bug survive.
