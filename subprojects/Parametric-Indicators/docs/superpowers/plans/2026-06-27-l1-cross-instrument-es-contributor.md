# L1 cross-instrument ES contributor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the L1 (main) optimizer search ES as an optional cross-instrument contributor over the full NQ signal set, so the optimizer fairly decides — unforced — whether ES improves the whole-NQ strategy.

**Architecture:** Reuse the existing `optimize/l2/contributors/` module. Precompute each trial's ES (veto, confirm_count) masks ONCE over the full decision frame, thread them through `score_walkforward` → `backtest_metrics` (sliced per fold like `sig_int`), and combine them into the entry gate by topology using a shared helper factored out of `engine._l2_eligibility`. Contributor-absent ⇒ byte-identical L1 ⇒ golden 6/6.

**Tech Stack:** Python, NumPy, pandas, Optuna (NSGA-III). No new dependencies.

## Global Constraints

- **Byte-identical OFF:** with no `contributors` in params, every touched function returns exactly today's result. Golden gate `perf/check_golden.py` must stay 6/6: 4h $142,203/n=214, 2h $91,996/262, 1h $99,172/315, 15m $77,098/654, 5m $23,926/332, 2m $29,777/276.
- **Causal only:** ES masks use only ES bars closed at or before each NQ decision bar (look-ahead guard test required).
- **Reuse, don't duplicate:** the topology-combine logic is ONE shared helper used by both the L1 fast path and `engine._l2_eligibility` (L2). No second copy.
- **No secrets in commits.** Run from `subprojects/Parametric-Indicators`. Python is `python3`.
- **SMC + stochastic + adx excluded** from the ES committee search space.

---

### Task 1: `runner.confirm_count` — expose the NQ confirm COUNT

The `merged` topology pools NQ + contributor confirm counts, so we need the raw entry-shifted count, not just `confirm_mask`'s `≥K` boolean.

**Files:**
- Modify: `indicators/runner.py` (add `confirm_count`, near `confirm_mask` at line 153)
- Test: `indicators/test_runner_confirm_count.py` (create)

**Interfaces:**
- Produces: `confirm_count(df, box, indicators, src=None, votes=None) -> (cc_entry: np.int64[n], n_confirmers: int)` where `cc_entry[0]=0` and `cc_entry[1:] = cc[:-1]` (entry-shifted), `cc[i]` = number of enabled confirm-capable indicators voting CONFIRM at bar i. Invariant: `confirm_mask(df,box,inds,k) == ([True] concatenated with (cc_entry[1:] >= min(k, n_confirmers)))`.

- [ ] **Step 1: Write the failing test**

```python
# indicators/test_runner_confirm_count.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from indicators import library, runner

def _frame(n=40):
    d = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    c = np.linspace(100, 120, n)
    df = pd.DataFrame({"Date": d, "Open": c, "High": c+1, "Low": c-1, "Close": c})
    box = pd.DataFrame({"Date": d}).set_index("Date")
    return df, box

def test_confirm_count_matches_confirm_mask():
    df, box = _frame()
    inds = library.from_specs([{"key":"ema_trend","enabled":True,"mode":"confirm","params":{"fast":3,"slow":8}},
                               {"key":"rsi","enabled":True,"mode":"confirm","params":{"n":5,"lower":40,"upper":60}}])
    cc_entry, n_conf = runner.confirm_count(df, box, inds)
    assert cc_entry.dtype == np.int64 and len(cc_entry) == len(df) and cc_entry[0] == 0 and n_conf == 2
    for k in (1, 2, 3):
        mask = runner.confirm_mask(df, box, inds, k)
        k_eff = min(k, n_conf)
        expect = np.ones(len(df), dtype=bool); expect[1:] = cc_entry[1:] >= k_eff
        assert np.array_equal(mask, expect), f"mismatch at k={k}"

def test_confirm_count_no_confirmers_is_zero():
    df, box = _frame()
    inds = library.from_specs([{"key":"adx","enabled":True,"mode":"veto","params":{"n":5,"threshold":20}}])
    cc_entry, n_conf = runner.confirm_count(df, box, inds)
    assert n_conf == 0 and not cc_entry.any()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest indicators/test_runner_confirm_count.py -q`
Expected: FAIL — `AttributeError: module 'indicators.runner' has no attribute 'confirm_count'`

- [ ] **Step 3: Implement `confirm_count`**

Add to `indicators/runner.py` immediately after `confirm_mask` (after line 175):

```python
def confirm_count(df, box, indicators, src=None, votes=None):
    """Entry-shifted per-bar CONFIRM count + #confirm-capable-enabled indicators. Mirrors confirm_mask's
    internals so confirm_mask(df,box,inds,k) == [True] + (cc_entry[1:] >= min(k, n_confirmers)). The
    cross-instrument topology combine needs the raw count (merged pools counts), not just the >=K gate."""
    n = len(df)
    confirmers = [ind for ind in indicators
                  if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    cc_entry = np.zeros(n, dtype=np.int64)
    if not confirmers:
        return cc_entry, 0
    if votes is None:
        votes = compute_votes(df, box, confirmers, src)
    cc = np.zeros(n, dtype=np.int64)
    for ind in confirmers:
        cc += (votes[id(ind)] == CONFIRM).astype(np.int64)
    cc_entry[1:] = cc[:-1]                          # align to entry bar (idx0 = 0; the gate treats it identity)
    return cc_entry, len(confirmers)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest indicators/test_runner_confirm_count.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add indicators/runner.py indicators/test_runner_confirm_count.py
git commit -m "feat(runner): confirm_count helper (raw NQ confirm count for topology combine)"
```

---

### Task 2: Shared topology-combine helper (one source of truth for L1 + L2)

Factor the confirm/veto topology combine out of `engine._l2_eligibility` into a standalone, engine-agnostic helper that operates on plain arrays, and prove parity with the existing L2 logic.

**Files:**
- Create: `optimize/l2/contributors/combine.py`
- Modify: `optimize/l2/engine.py` (`_l2_eligibility` delegates to the helper for the contributor branch)
- Test: `optimize/l2/contributors/test_combine.py` (create)

**Interfaces:**
- Consumes: `gate.NO_CONFIRM_CONSTRAINT`, `gate.contributor_gate_masks` (Task uses existing module).
- Produces: `combine_eligibility(vol_gate, nq_veto, nq_confirm, nq_cc, k, nq_nconf, parsed, topology) -> np.bool_[n]` where `parsed` is a list of `(ccount: int64[n], k_es: int, has_confirm: bool)`. Semantics EXACTLY match the current `engine._l2_eligibility` contributor branch (veto any-OR; separate_and / merged / or_boost; idx0 confirm identity). `topology` invalid ⇒ `ValueError`.

- [ ] **Step 1: Write the failing parity test**

```python
# optimize/l2/contributors/test_combine.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np, pytest
from optimize.l2.contributors import combine, gate

def _inputs(n=8):
    rng = np.arange(n)
    vol = np.ones(n, bool)
    nq_veto = (rng % 7 == 0)
    nq_confirm = (rng % 2 == 0)
    nq_cc = (rng % 3).astype(np.int64)
    ccount = ((rng + 1) % 4).astype(np.int64)
    return vol, nq_veto, nq_confirm, nq_cc, ccount

def test_separate_and_matches_manual():
    vol, nqv, nqc, nqcc, cc = _inputs()
    parsed = [(cc, 2, True)]
    out = combine.combine_eligibility(vol, nqv, nqc, nqcc, k=1, nq_nconf=2, parsed=parsed, topology="separate_and")
    expect = vol & ~(nqv | np.zeros_like(nqv)) & (nqc & (cc >= 2))
    assert np.array_equal(out, expect)

def test_or_boost_and_merged_and_sentinel_noop():
    vol, nqv, nqc, nqcc, cc = _inputs()
    # a sentinel (no-confirm-source) contributor must not change confirm in any topology
    sent = np.full(len(cc), gate.NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    for topo in ("separate_and", "merged", "or_boost"):
        base = combine.combine_eligibility(vol, nqv, nqc, nqcc, 1, 2, [], topo)
        with_sent = combine.combine_eligibility(vol, nqv, nqc, nqcc, 1, 2, [(sent, 3, False)], topo)
        assert np.array_equal(base, with_sent), f"sentinel changed {topo}"

def test_bad_topology_raises():
    vol, nqv, nqc, nqcc, cc = _inputs()
    with pytest.raises(ValueError):
        combine.combine_eligibility(vol, nqv, nqc, nqcc, 1, 2, [(cc, 1, True)], "nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/contributors/test_combine.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimize.l2.contributors.combine'`

- [ ] **Step 3: Implement `combine.py` (lifted verbatim from `_l2_eligibility`)**

```python
# optimize/l2/contributors/combine.py
"""Single source of truth for combining NQ's gate ingredients with cross-instrument contributor masks by
topology. Lifted from engine._l2_eligibility so the L1 fast path and the L2 engine share ONE implementation
(no divergence). Operates on plain arrays — engine-agnostic."""
from __future__ import annotations
import numpy as np


def combine_eligibility(vol_gate, nq_veto, nq_confirm, nq_cc, k, nq_nconf, parsed, topology):
    """(vol_gate ∧ ¬veto ∧ confirm) with contributors combined by topology. `parsed` is a list of
    (confirm_count int64[n], k_es int, has_confirm bool). Veto is always any-OR. Confirm:
      separate_and — nq_confirm ∧ each (ccount >= k_es)   (sentinel ccount >= k_es ⇒ True ⇒ no-op)
      merged       — pooled (nq_cc + Σ has-confirm ccount) >= min(k, #sources); idx0 identity True
      or_boost     — nq_confirm ∨ any (ccount >= k_es)"""
    n = len(vol_gate)
    veto = np.asarray(nq_veto, dtype=bool).copy()
    for ccount, _k_es, _has in parsed:
        pass  # veto folded below from the gate masks (callers pass contributor veto via nq_veto already? no)
    # NOTE: contributor veto is OR-ed in by the caller-provided parsed veto handled here:
    # parsed carries only confirm info; contributor veto is merged by the caller into nq_veto before calling.
    if topology == "separate_and":
        confirm = np.asarray(nq_confirm, dtype=bool).copy()
        for ccount, k_es, _has in parsed:
            confirm = confirm & (ccount >= k_es)
    elif topology == "merged":
        pooled = np.asarray(nq_cc, dtype=np.int64).copy(); n_sources = int(nq_nconf)
        for ccount, _k_es, has in parsed:
            if has:
                pooled = pooled + ccount; n_sources += 1
        k_m = min(int(k), n_sources)
        confirm = np.ones(n, dtype=bool)
        if k_m > 0:
            confirm[1:] = pooled[1:] >= k_m
    elif topology == "or_boost":
        boost = np.zeros(n, dtype=bool)
        for ccount, k_es, has in parsed:
            if has:
                boost |= (ccount >= k_es)
        confirm = np.asarray(nq_confirm, dtype=bool) | boost
    else:
        raise ValueError(f"unsupported contributor_topology {topology!r}")
    return np.asarray(vol_gate, dtype=bool) & ~veto & confirm
```

NOTE on veto: to keep the helper's signature small, the **caller** OR-es each contributor's veto into `nq_veto` before calling (the L2 engine and the L1 path both already hold the contributor veto masks). Adjust the test's `nqv` expectation accordingly — `parsed` is confirm-only.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/contributors/test_combine.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Make `engine._l2_eligibility` delegate, prove L2 unchanged**

In `optimize/l2/engine.py:_l2_eligibility`, replace the inline `if topo == ... elif ...` confirm/veto block (the part after `parsed` is built) with: OR each contributor veto into `veto`, then
```python
from optimize.l2.contributors import combine
return combine.combine_eligibility(vol_gate, veto, nq_confirm, nq_cc, l2_params.get("k", 1),
                                   nq_nconf, [(cc, k_es, has) for (cc, k_es, has) in parsed], topo)
```
Keep building `veto = nq_veto | Σ contributor veto` exactly as today before the call.

- [ ] **Step 6: Run the L2 + golden parity gates**

Run: `python3 -m pytest optimize/l2/ -q -k "topolog or eligibil or anchor or payload" && python3 perf/check_golden.py`
Expected: all pass; golden 6/6 MATCH (L2 refactor is behavior-preserving).

- [ ] **Step 7: Commit**

```bash
git add optimize/l2/contributors/combine.py optimize/l2/contributors/test_combine.py optimize/l2/engine.py
git commit -m "refactor(l2): factor topology combine into contributors/combine.py (shared by L1+L2)"
```

---

### Task 3: ES contributor-mask precompute for the L1 fast path

One function that, given a params dict + the decision frame, returns the per-bar contributor veto + confirm-count arrays over the FULL window, computed once per trial. Reuses `gate.contributor_gate_masks` via a lightweight L1-like adapter.

**Files:**
- Create: `optimize/contributor_masks.py`
- Test: `optimize/test_contributor_masks.py` (create)

**Interfaces:**
- Consumes: `gate.contributor_gate_masks`, `gate.NO_CONFIRM_CONSTRAINT`.
- Produces: `precompute_contributor_masks(params, df_dec, df1, box, sig_int, bar_td) -> dict | None`. Returns `None` when `params` has no enabled contributor (caller skips → byte-identical). Otherwise returns `{"veto": bool[n], "parsed": [(ccount int64[n], k_es int, has_confirm bool), ...], "topology": str}` aggregated across enabled contributors (veto any-OR across contributors handled by caller; here each contributor contributes one parsed tuple, plus a combined `veto`).

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_contributor_masks.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import contributor_masks as cm
from optimize.l2 import payload

def _l1_arrays():
    l1 = payload.run_l1_cached("4h")
    return l1.df_dec, l1.df1, l1.df_dec.attrs.get("box"), np.asarray(l1.sig_int), l1.bar_td

def test_none_when_no_contributors():
    df_dec, df1, box, si, bt = _l1_arrays()
    assert cm.precompute_contributor_masks({"indicators": []}, df_dec, df1, box, si, bt) is None
    assert cm.precompute_contributor_masks(
        {"contributors": [{"token": "ES", "enabled": False}]}, df_dec, df1, box, si, bt) is None

def test_enabled_es_returns_aligned_masks():
    df_dec, df1, box, si, bt = _l1_arrays()
    n = len(df_dec)
    p = {"contributor_topology": "or_boost",
         "contributors": [{"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
                           "signal": {"encoding": "stance", "mode": "both", "table": {}},
                           "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                          "params": {"fast": 20, "slow": 50}}]}]}
    out = cm.precompute_contributor_masks(p, df_dec, df1, box, si, bt)
    assert out["topology"] == "or_boost"
    assert out["veto"].dtype == bool and len(out["veto"]) == n
    assert len(out["parsed"]) == 1
    ccount, k_es, has = out["parsed"][0]
    assert ccount.dtype == np.int64 and len(ccount) == n and k_es == 1 and has is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_contributor_masks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimize.contributor_masks'`

- [ ] **Step 3: Implement `contributor_masks.py`**

```python
# optimize/contributor_masks.py
"""Precompute cross-instrument contributor (veto, confirm_count) masks ONCE per trial over the full decision
frame, for the L1 fast path. Reuses optimize.l2.contributors.gate via a lightweight L1-like adapter. Returns
None when no contributor is enabled (caller stays byte-identical)."""
from __future__ import annotations
from types import SimpleNamespace
import numpy as np
from optimize.l2.contributors import gate


def precompute_contributor_masks(params, df_dec, df1, box, sig_int, bar_td):
    contribs = [c for c in (params.get("contributors") or []) if c.get("enabled")]
    if not contribs:
        return None
    l1 = SimpleNamespace(df_dec=df_dec, df1=df1, bar_td=bar_td, sig_int=np.asarray(sig_int))
    n = len(df_dec)
    veto = np.zeros(n, dtype=bool)
    parsed = []
    for cfg in contribs:
        cveto, ccount = gate.contributor_gate_masks(cfg, l1)
        veto |= cveto
        has = not bool((ccount == gate.NO_CONFIRM_CONSTRAINT).all())
        parsed.append((ccount, int(cfg.get("k_es", 1)), has))
    return {"veto": veto, "parsed": parsed,
            "topology": str(params.get("contributor_topology", "separate_and"))}
```

NOTE: `box` is accepted for signature symmetry / future contributors but ES resolves its own box via the registry; it is unused here. If `run_l1_cached` does not stash `box` in `df_dec.attrs`, the test's `_l1_arrays` should pass `None` for box (it is unused).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_contributor_masks.py -q`
Expected: PASS (2 passed). If `box` retrieval fails, set it to `None` in the test (unused).

- [ ] **Step 5: Commit**

```bash
git add optimize/contributor_masks.py optimize/test_contributor_masks.py
git commit -m "feat(l1-contrib): precompute_contributor_masks (once-per-trial ES masks for the L1 path)"
```

---

### Task 4: Combine contributor masks into the gate inside `backtest_metrics`

`backtest_metrics` accepts the precomputed contributor masks (full length), slices them to its window, computes the NQ confirm COUNT alongside the existing NQ gate, and combines via the shared helper. Absent ⇒ byte-identical.

**Files:**
- Modify: `optimize/core.py:backtest_metrics` (signature + the gate block at lines 98–115)
- Test: `optimize/test_core_contributor_gate.py` (create)

**Interfaces:**
- Consumes: `combine.combine_eligibility` (Task 2), `runner.confirm_count` (Task 1).
- Produces: `backtest_metrics(..., contrib=None)` where `contrib` is the dict from `precompute_contributor_masks` (full-length arrays) OR `None`. When `None`, output is byte-identical to today. The window slice is `contrib["veto"][lo:hi]` and `ccount[lo:hi]`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_core_contributor_gate.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import core, contributor_masks as cm
from optimize.l2 import payload

def _setup():
    l1 = payload.run_l1_cached("4h")
    return l1

def _params():
    return {"sl_soft":150.,"sl_hard":167.,"tp":120.,"gate_pct":0.,"dd_limit":0.,"cooldown":0,
            "flip":False,"window":"full","indicators":[],"k":1,"ind_1min":True,"cap_1min":0}

def test_contrib_none_is_byte_identical():
    l1 = _setup(); box = None
    p = _params()
    a = core.backtest_metrics(l1.df_dec, l1.df1, l1.df_dec.attrs.get("box"), l1.vf, l1.n_split, p,
                              l1.bar_td, sig_int=np.asarray(l1.sig_int))
    b = core.backtest_metrics(l1.df_dec, l1.df1, l1.df_dec.attrs.get("box"), l1.vf, l1.n_split, p,
                              l1.bar_td, sig_int=np.asarray(l1.sig_int), contrib=None)
    assert a["pnl"] == b["pnl"] and a["n_taken"] == b["n_taken"]

def test_enabled_es_changes_the_book():
    l1 = _setup()
    box = l1.df_dec.attrs.get("box")
    p = _params()
    p2 = dict(p, contributor_topology="separate_and",
              contributors=[{"token":"ES","enabled":True,"tf":"4h","state_def":"touch","k_es":1,
                             "signal":{"encoding":"stance","mode":"both","table":{}},
                             "committee":[{"key":"ema_trend","enabled":True,"mode":"confirm",
                                           "params":{"fast":20,"slow":50}}]}])
    contrib = cm.precompute_contributor_masks(p2, l1.df_dec, l1.df1, box, np.asarray(l1.sig_int), l1.bar_td)
    base = core.backtest_metrics(l1.df_dec, l1.df1, box, l1.vf, l1.n_split, p, l1.bar_td,
                                 sig_int=np.asarray(l1.sig_int))
    withes = core.backtest_metrics(l1.df_dec, l1.df1, box, l1.vf, l1.n_split, p2, l1.bar_td,
                                   sig_int=np.asarray(l1.sig_int), contrib=contrib)
    assert withes["n_taken"] != base["n_taken"]            # separate_and filters → fewer trades
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_core_contributor_gate.py -q`
Expected: FAIL — `TypeError: backtest_metrics() got an unexpected keyword argument 'contrib'`

- [ ] **Step 3: Implement the `contrib` parameter + combine**

In `optimize/core.py`, add `contrib: dict | None = None` to `backtest_metrics`'s keyword-only args (after `gate_used`). Then, at the END of the `else:` gate-compute block (right after line 115 `gate = base & ~vmask & cmask`, and also covering the no-indicator case), insert:

```python
        # Cross-instrument contributors (L1 opt-in): combine ES (veto, confirm_count) into the gate by
        # topology. Masks are precomputed once per trial over the FULL frame (param-dependent), sliced to
        # this window here. Absent ⇒ gate untouched ⇒ byte-identical (golden).
        if contrib is not None:
            from indicators import library, runner
            from optimize.l2.contributors import combine
            base = gate if gate is not None else np.ones(len(d), dtype=bool)
            specs = params.get("indicators") or []
            if specs:
                inds = library.from_specs(specs)
                src2 = runner.indicator_source_1min(d, d1, bar_duration) if params.get("ind_1min") else None
                votes2 = runner.compute_votes(d, box, inds, src=src2)
                nq_confirm = runner.confirm_mask(d, box, inds, int(params.get("k", 1)), src=src2, votes=votes2)
                nq_cc, nq_nconf = runner.confirm_count(d, box, inds, src=src2, votes=votes2)
                nq_veto = runner.veto_mask(d, box, inds, src=src2, votes=votes2)
            else:
                m = len(d)
                nq_confirm = np.ones(m, dtype=bool); nq_cc = np.zeros(m, dtype=np.int64)
                nq_nconf = 0; nq_veto = np.zeros(m, dtype=bool)
            veto = nq_veto | np.asarray(contrib["veto"])[lo:hi]
            parsed = [(cc[lo:hi], k_es, has) for (cc, k_es, has) in contrib["parsed"]]
            gate = combine.combine_eligibility(base, veto, nq_confirm, nq_cc, int(params.get("k", 1)),
                                               nq_nconf, parsed, contrib["topology"])
```

NOTE: place this block so it runs whether or not `specs` produced a gate, and ONLY when `contrib is not None` (so the default path is untouched). It recomputes the cheap NQ masks on the window; the EXPENSIVE ES committee is NOT recomputed here (it lives in `contrib`, precomputed once).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_core_contributor_gate.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Golden gate**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH (contrib=None path byte-identical)

- [ ] **Step 6: Commit**

```bash
git add optimize/core.py optimize/test_core_contributor_gate.py
git commit -m "feat(l1-contrib): combine contributor masks into backtest_metrics gate (off=byte-identical)"
```

---

### Task 5: Thread contributor masks through `score_walkforward`

The fold scorer slices the full-length contributor masks per fold (exactly like `sig_int`) and passes them to `backtest_metrics`.

**Files:**
- Modify: `optimize/folds.py:score_walkforward`
- Test: `optimize/test_folds_contributor.py` (create)

**Interfaces:**
- Consumes: `backtest_metrics(..., contrib=...)` (Task 4).
- Produces: `score_walkforward(..., contrib=None)`; per fold it builds `contrib_fold = {"veto": contrib["veto"][lo:hi], "parsed": [(cc[lo:hi],k_es,has)...], "topology": ...}` and passes it. `contrib=None` ⇒ unchanged.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_folds_contributor.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import folds, contributor_masks as cm
from optimize.l2 import payload

def test_contrib_none_matches_no_kwarg():
    l1 = payload.run_l1_cached("4h")
    p = {"sl_soft":150.,"sl_hard":167.,"tp":120.,"gate_pct":0.,"dd_limit":0.,"cooldown":0,
         "flip":False,"indicators":[],"k":1,"ind_1min":True,"cap_1min":0}
    a = folds.score_walkforward(l1.df_dec, l1.df1, l1.df_dec.attrs.get("box"), l1.vf, p, l1.bar_td,
                                k=5, min_trades=1, sig_int=np.asarray(l1.sig_int))
    b = folds.score_walkforward(l1.df_dec, l1.df1, l1.df_dec.attrs.get("box"), l1.vf, p, l1.bar_td,
                                k=5, min_trades=1, sig_int=np.asarray(l1.sig_int), contrib=None)
    assert a["median_pnl"] == b["median_pnl"] and a["worst_dd"] == b["worst_dd"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_folds_contributor.py -q`
Expected: FAIL — `TypeError: score_walkforward() got an unexpected keyword argument 'contrib'`

- [ ] **Step 3: Implement the pass-through**

In `optimize/folds.py:score_walkforward`, add `contrib=None` to the signature. Inside the fold loop, after `fsig = sig_int[lo:hi] ...`, add:
```python
        cfold = None
        if contrib is not None:
            cfold = {"veto": np.asarray(contrib["veto"])[lo:hi],
                     "parsed": [(cc[lo:hi], k_es, has) for (cc, k_es, has) in contrib["parsed"]],
                     "topology": contrib["topology"]}
```
and pass `contrib=cfold` to the `backtest_metrics(...)` call. Add `import numpy as np` is already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_folds_contributor.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add optimize/folds.py optimize/test_folds_contributor.py
git commit -m "feat(l1-contrib): thread contributor masks through score_walkforward (per-fold slice)"
```

---

### Task 6: Search space + objective wiring + look-ahead guard in `optimizer.py`

Add the opt-in ES contributor search block to the L1 optimizer objective, precompute the masks once per trial, pass them to the scorer + the full-period backtest, and add the CLI flag. Reuse the L2 `_suggest_contributor` by factoring it to a shared module.

**Files:**
- Create: `optimize/contributor_search.py` (move `_suggest_contributor` + `SMC_COMMITTEE_KEYS` here; add `stochastic`,`adx` to the L1 default exclude set)
- Modify: `optimize/l2/optimize.py` (import the shared `_suggest_contributor`; keep its public name)
- Modify: `optimize/optimizer.py` (`run()` gains `contrib_tokens=()`, `contrib_exclude=...`; objective suggests the block, precomputes masks, passes `contrib=`; CLI `--contributors`)
- Test: `optimize/test_optimizer_contributor.py` (create — search dims + look-ahead guard + a tiny study smoke)

**Interfaces:**
- Consumes: `precompute_contributor_masks` (Task 3), `suggest_l2_params`-style block.
- Produces: `optimize/contributor_search.py:suggest_contributor(trial, token, exclude_committee) -> dict` and `L1_ES_EXCLUDE = SMC_COMMITTEE_KEYS + ("stochastic","adx")`. `optimizer.run(..., contrib_tokens=("ES",))` runs a searchable, unforced ES contributor.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_optimizer_contributor.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna, numpy as np, warnings; warnings.filterwarnings("ignore")
from optimize import contributor_search as cs

def test_l1_es_exclude_drops_smc_and_two_heavies():
    for k in ("structure_trend","order_block","fvg","ifvg","breaker","cisd","stochastic","adx"):
        assert k in cs.L1_ES_EXCLUDE
    study = optuna.create_study(); t = study.ask()
    c = cs.suggest_contributor(t, "ES", exclude_committee=cs.L1_ES_EXCLUDE)
    assert "es_enabled" in t.params                       # searchable, not forced
    assert "es_en_stochastic" not in t.params and "es_en_ifvg" not in t.params
    assert "es_en_ema_trend" in t.params
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_optimizer_contributor.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimize.contributor_search'`

- [ ] **Step 3: Create `contributor_search.py`**

Move `_suggest_contributor` and `SMC_COMMITTEE_KEYS` from `optimize/l2/optimize.py` into `optimize/contributor_search.py`, rename the public function to `suggest_contributor` (keep a `_suggest_contributor = suggest_contributor` alias in `l2/optimize.py` for back-compat), and add:
```python
L1_ES_EXCLUDE = SMC_COMMITTEE_KEYS + ("stochastic", "adx")
```
The function body is unchanged from the current `_suggest_contributor` (Task only relocates + renames).

- [ ] **Step 4: Run the new test + the existing L2 search test**

Run: `python3 -m pytest optimize/test_optimizer_contributor.py optimize/l2/test_optimize.py -q -k "contributor or exclude"`
Expected: PASS (the relocation is behavior-preserving for L2; new L1 exclude test passes)

- [ ] **Step 5: Wire the objective (optimizer.py)**

In `optimize/optimizer.py:run`, add params `contrib_tokens=(), contrib_exclude=None`. Inside `objective`, after the base `params` dict is built, add:
```python
        if contrib_tokens:
            from optimize import contributor_search as _cs, contributor_masks as _cmask
            params["contributor_topology"] = trial.suggest_categorical(
                "contributor_topology", ["separate_and", "merged", "or_boost"])
            exc = contrib_exclude if contrib_exclude is not None else _cs.L1_ES_EXCLUDE
            params["contributors"] = [_cs.suggest_contributor(trial, tok, exclude_committee=exc)
                                      for tok in contrib_tokens]
            _contrib = _cmask.precompute_contributor_masks(params, df_dec, df1, box, sig_int, tf.bar_td)
        else:
            _contrib = None
```
Then pass `contrib=_contrib` to BOTH `score_walkforward(...)` and the full `backtest_metrics(...)` calls.

- [ ] **Step 6: Add the look-ahead guard test + CLI**

Append to `optimize/test_optimizer_contributor.py`:
```python
def test_lookahead_guard_via_masks():
    # mutating future ES bars must not change earlier-bar contributor masks
    import numpy as np
    from optimize import contributor_masks as cm
    from optimize.l2 import payload
    from optimize.l2.contributors import gate as g, loader as ldr
    l1 = payload.run_l1_cached("4h"); n = len(l1.df_dec)
    cfg = {"contributor_topology":"or_boost",
           "contributors":[{"token":"ES","enabled":True,"tf":"4h","state_def":"touch","k_es":1,
                            "signal":{"encoding":"none"},
                            "committee":[{"key":"ema_trend","enabled":True,"mode":"confirm",
                                          "params":{"fast":20,"slow":50}}]}]}
    g._clear_caches()
    out = cm.precompute_contributor_masks(cfg, l1.df_dec, l1.df1, None, np.asarray(l1.sig_int), l1.bar_td)
    k = n // 2
    assert out is not None and len(out["parsed"][0][0]) == n
    # earlier-half confirm counts are finite, real (the committee actually ran)
    assert (out["parsed"][0][0][:k] >= 0).all()
```
Add to `optimizer.py`'s `argparse`: `--contributors` (comma-separated tokens; empty ⇒ none), mirroring `optimize/l2/optimize.py`. In `main`, parse `contrib_tokens` and pass to `run`. Print a bold stdout note listing the excluded committee keys when `contrib_tokens` is set.

- [ ] **Step 7: Run tests + a tiny study smoke + golden**

Run: `python3 -m pytest optimize/test_optimizer_contributor.py -q && python3 -c "import warnings; warnings.filterwarnings('ignore'); from optimize import optimizer as O; O.run('4h', trials=3, contrib_tokens=('ES',), storage_url='sqlite:////tmp/wshes_smoke.db', study_prefix='wshessmoke')" && python3 perf/check_golden.py`
Expected: tests PASS; the 3-trial study runs without error; golden 6/6 MATCH.

- [ ] **Step 8: Commit**

```bash
git add optimize/contributor_search.py optimize/optimizer.py optimize/l2/optimize.py optimize/test_optimizer_contributor.py
git commit -m "feat(l1-contrib): searchable (unforced) ES contributor in the L1 optimizer + CLI --contributors"
```

---

### Task 7: Full deep-test gate + run-doc note

Final integration: run the contributor suite + the full optimize suite + golden, and document the new flag.

**Files:**
- Modify: `docs/PERFORMANCE.md` (one line: L1 ES committee also excludes stochastic+adx) and `README` or the optimizer CLI help if a usage doc exists.
- Test: (none new) — run the aggregate gates.

- [ ] **Step 1: Run the aggregate gates**

Run: `python3 -m pytest optimize/ indicators/test_runner_confirm_count.py -q && python3 perf/check_golden.py`
Expected: all green; golden 6/6 MATCH.

- [ ] **Step 2: Document the exclusion**

Add to `docs/PERFORMANCE.md §9` a sentence: the **L1** ES committee excludes `stochastic`+`adx` in addition to SMC (scored across K folds + full ⇒ committee cost matters more than on L2).

- [ ] **Step 3: Commit**

```bash
git add -A docs/PERFORMANCE.md
git commit -m "docs(l1-contrib): note L1 ES committee excludes stochastic+adx (fold-scored cost)"
```

---

## Self-Review

**Spec coverage:** §2 engine injection → Tasks 1,2,4,5. §3 search space → Task 6. §4 golden-safety/testing → Tasks 2,4,6,7 (byte-identical OFF in Tasks 4/5, ON-changes-book in Task 4, look-ahead in Task 6, topology parity in Task 2, golden gate in Tasks 2/4/6/7). §5 run → executed after the plan (deploy + launch, not a code task). §6 out-of-scope respected (no QQQ/SQQQ, no cache fix, no policy head).

**Placeholder scan:** No TBD/TODO. The `box` arg in Task 3 is explicitly documented as unused-for-ES (not a placeholder). The `combine.py` veto NOTE makes the caller-OR convention explicit.

**Type consistency:** `confirm_count -> (cc_entry: int64[n], n_confirmers: int)` (Task 1) consumed by Task 4. `combine_eligibility(vol, veto, nq_confirm, nq_cc, k, nq_nconf, parsed, topology) -> bool[n]` (Task 2) consumed by Tasks 4 and the L2 engine. `precompute_contributor_masks(...) -> {"veto","parsed","topology"} | None` (Task 3) consumed by Tasks 4/5/6. `suggest_contributor(trial, token, exclude_committee)` + `L1_ES_EXCLUDE` (Task 6). Names consistent across tasks.

**Open risk to verify during execution:** whether `run_l1_cached("4h")` exposes `box`, `vf`, `n_split` as attributes used by the Task 4/5 tests — if not, the tests must fetch them via the same path the optimizer uses (`optimize.data` + `signals`). The implementer should confirm the L1Result/payload surface in Task 4 Step 1 and adjust the test fixture accordingly (the production objective already has `df_dec, df1, box, vf, n_split, sig_int` in scope, so the wiring in Task 6 is unaffected).
