# Closeout — The Cross-Series Reference Never Reached the Indicators (2026-07-28)

**Issue:** #75 · **Branch:** `fix/75-xseries-reference-wiring` · **Found by:** #74 · **Status:** ✅ **CLOSED**

---

## 1. Three bugs, one cause

The four cross-series indicators had apparently never been run end-to-end. Three separate defects sat
on the path, each hidden by the one in front of it.

### Bug 1 — the reference never reached the 1-minute context

```python
def indicator_source_1min(df_dec, df1, bar_td):
    ctx_1m = market_context(df1)        # ← no ref_df argument, and no caller passed one
```

`--ind-1min` is the production default, so on the path that actually runs, every cross-series
indicator found `ctx.ref_close is None` and returned all zeros — **regardless of `--reference`**. The
decision-frame context that *did* carry the reference was discarded the moment `src` was non-None.

### Bug 2 — and it was worse than dormant

`confirm_mask` decided whether a cross-series indicator was *active* from `ref_df is not None`, i.e.
from whether a reference was **configured** — while the votes came from a context that did not have
one. With `k_eff = min(k, len(confirmers))`, enabling one added a confirmer that could **never
confirm**, making the K-rule strictly harder.

Measured on the deployed 4h champion (7 confirmers) with `k` set so the added indicator is pivotal:

| indicator | mode | pre-fix | fixed, no reference | fixed, reference wired |
|---|---|---:|---:|---:|
| `rolling_beta` | confirm | **0 entries** | 13 | 2 |
| `cointegration` | both | **0 entries** | 13 | 3 |
| `pca_factor` | confirm | **0 entries** | 13 | 4 |
| `rolling_corr` | *veto* | 13 | 13 | 13 |

**Enabling a cross-series confirmer took the strategy to zero trades.** `rolling_corr` is unaffected
because it is a *veto*: a vetoer that never vetoes changes nothing. So the damage was confirm-path
only — and the optimizer, seeing trials that enabled these indicators produce nothing, would have
learned to avoid them for a reason that was purely a wiring bug.

> **Control:** the same harness at `k=99` moves entries 277 → 13, so it demonstrably *can* see a
> confirm-gate change. An earlier version of this measurement used `k = champion_k + 1 = 2` and
> reported a difference of exactly zero for all four — because 7 confirmers already satisfy `k=2`. That
> was **unfalsifiable, not null.** The finish line moved only after the control was added.

### Bug 3 — a latent crash

```python
def build_entry_resolver(df, box, indicators, k, ..., src=None, votes=None):   # no `ref_df` parameter
    confirmers = [ind for ind in indicators
                  if ... and not (ind.needs_ref and ref_df is None)]           # ← NameError
```

`and` short-circuits, so `ref_df` was never evaluated for an indicator with `needs_ref=False`. Enable a
cross-series indicator on the dashboard / exact-engine path and it raises
`NameError: name 'ref_df' is not defined`. Reproduced, then fixed.

---

## 2. The fix

1. `indicator_source_1min(df_dec, df1, bar_td, ref_df1=None)` → `market_context(df1, ref_df1)`.
   `ref_df1` is the reference's **1-minute** frame, not its decision frame — the alignment has to
   happen at the resolution the indicators actually read.
2. **Activity now reads the vote-producing context**, via `_reference_reaches(src, ref_df)`. This is
   the part that makes the class of bug unrepeatable: wire up a new call site and forget the
   reference, and the indicator goes *inert* rather than becoming a confirmer that never confirms.
3. `build_entry_resolver` / `build_layer` take and forward `ref_df` (fixing the NameError, and letting
   the exact engine use a reference at all).
4. `core._cached_source` takes `ref_df1` **and keys its memo on it** — a source built reference-free
   and one built with a reference are indistinguishable to `_slice_sig`, and serving the wrong one
   would silently invent or erase every cross-series vote.
5. `optimizer.py` now loads **both** reference frames (`ref_df, ref_df1, *_ = load_inputs(...)`) and
   threads `ref_df1` through `score_walkforward` → `backtest_metrics`.

Every parameter defaults to `None`, and every caller that has no reference — the dashboard, the L2
engine, the pause diagnostics, the sub-optimizers — passes nothing and is byte-identical.

---

## 3. What changes, and what does not

| | |
|---|---|
| **No `--reference`** (the golden-gated path, and every current champion) | **Byte-identical.** Verified directly (`impact` phase A) and by the golden gate. |
| **With `--reference`, no cross-series indicator enabled** | unchanged |
| **With `--reference`, a cross-series indicator enabled** | **CHANGES** — this is the bug being fixed. The indicator now actually votes. |

⚠️ **Any Optuna study run with `--reference` under the old code explored a mis-specified space**: every
trial that enabled a cross-series indicator was scored as if that indicator vetoed nothing and
confirmed nothing (and, at a binding `k`, produced zero trades). Those trials are not reproducible
under the fix, and should not be — they were measuring a bug. No champion currently enables a
cross-series key, so nothing deployed is affected.

**Cost, now that they are live:** cross-series votes are deliberately never cached (the cache key does
not encode the reference), so they are recomputed every trial — **0.28 s for all four together** on the
full 1-minute frame. Before #74 that same number was **27.4 s**, which is why #74 had to land first.

---

## 4. Verification

| gate | result | log |
|---|---|---|
| impact phase A — no reference, old vs new | **identical** | `issue75_impact.log` |
| control — k=99 must move entries | 277 → 13 ✅ the measurement is falsifiable | `issue75_impact.log` |
| impact phase B — starvation | **0 → 13 entries** for all three confirm-capable indicators | `issue75_impact.log` |
| new regression tests (`optimize/test_xseries_wiring.py`) | 12 passed | — |
| full test suite | *(§6)* | `issue75_full_pytest.log` |
| golden gate | *(§6)* | `issue75_golden.log` |

---

## 5. Still the user's call — deliberately not done here

This closes the **defect**. It does not decide the **strategy** questions:

1. **Should cross-series indicators be in the optimizer's search space at all?** They are admitted
   today whenever a reference is loaded. Now that they work, that is a real choice with a real cost
   (0.28 s/trial, uncached) — and the #14 adopt-gate is the right instrument for it.
2. **Should any study be re-run with `--reference`?** No champion uses one, so nothing is pending;
   but any past `--reference` study is void.
3. **Does the ES contributor path (`l2/contributors/gate.py`) want its own reference?** It builds ES's
   *own* 1-minute context, where the natural reference would be NQ. Out of scope, untouched, noted.

---

## 6. Verification results

AMD server, real data (NQ 4h + ES reference, 486,969-bar 1-minute frame). Logs committed under
`optimize/perf/logs/`.

| gate | result |
|---|---|
| impact A — no reference, `ref_df1=None` vs the old signature | **identical** (P/L $151,655 · DD $15,560 · 277 trades) |
| impact CONTROL — `k=99` | entries **277 → 13** ⇒ the confirm gate is detectable, phase B is falsifiable |
| impact B — starvation, the three confirm-capable indicators | **0 → 13 entries** (pre-fix → fixed) |
| impact B — `rolling_corr` (veto-mode) | 13 / 13 / 13 — unaffected, correctly: a vetoer that never vetoes changes nothing |
| impact C — cost of all four live, uncached | **0.28 s per trial** (27.4 s before #74) |
| full test suite | **1,004 passed · 1 skipped · 0 FAILED** (992 → 1,004: +12 wiring regression tests) |
| golden gate | **6/6 ✅ byte-identical** — 4h $151,655/277 · 2h $101,518/173 · 1h $110,038/353 · 15m $82,156/654 · 5m $20,092/314 · 2m $31,898/276 |

The golden gate passing is the containment proof that matters here: it exercises the no-reference path,
which is what every champion and the dashboard use, and it did not move by a byte.

---

## 7. One paragraph

A feature that had shipped, been documented, been given a `--reference` flag and a place in the search
space had **never once executed**. Three defects were stacked on the same path: the reference was never
passed to the context the indicators read; the "is it active?" test asked the configuration instead of
that context, so enabling one silently took the strategy to **zero trades**; and the exact-engine path
raised a `NameError` the moment one was enabled, invisible because `and` short-circuits. The fix makes
activity depend on the context that produces the votes, which is what stops the class from recurring.
The lesson is #74's, sharpened: **an indicator that emits nothing is not a quiet indicator — check
that your feature has ever actually run.**
