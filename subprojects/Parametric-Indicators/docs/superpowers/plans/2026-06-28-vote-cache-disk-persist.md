# Disk-persistent indicator-vote cache — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist item 1's in-process indicator-vote memo to disk so the cold `ifvg`(74.5s)/`breaker`(25s) computes are paid once-ever and shared across all worker processes + watchdog respawns.

**Architecture:** A new `optimize/vote_cache.py` module provides a versioned, content-signed, atomic-write disk store. `core._cached_votes` (L1 fold path) and `engine._committee_votes` (L2 path) consult it on an in-memory-memo miss and persist after a compute. Result-neutral by construction (stores/reloads the exact array).

**Tech Stack:** Python, NumPy. No new dependencies.

## Global Constraints

- **Result-neutral:** golden `perf/check_golden.py` must stay **6/6** byte-identical (4h $142,203/214, 2h $91,996/262, 1h $99,172/315, 15m $77,098/654, 5m $23,926/332, 2m $29,777/276) and the L2 suite (78 tests) must pass. The disk cache stores/reloads the exact computed array; the only failure mode is staleness, closed by the versioned + content-signed key.
- **Best-effort:** any cache read/write error must be swallowed and fall back to compute — the cache never fails a run (mirrors the §4.4 candidate-L1 disk cache).
- **Test isolation:** tests point the cache at a tmp dir via `vote_cache.set_cache_dir(...)` and clear it, so golden never reads a cross-run/cross-version cache.
- Run from `subprojects/Parametric-Indicators`. Python is `python3`. No secrets in commits.

---

### Task 1: `optimize/vote_cache.py` — the disk store

**Files:**
- Create: `optimize/vote_cache.py`
- Test: `optimize/test_vote_cache.py` (create)

**Interfaces:**
- Produces:
  - `CACHE_VERSION: str` — bump on any indicator vote-math change.
  - `set_cache_dir(path) -> None` — override the cache directory (tests).
  - `_clear_disk_cache() -> None` — remove all cached files (test seam).
  - `disk_key(slice_sig: tuple, use1: bool, key: str, mode: str, params_tuple: tuple) -> str` — 32-char hex stem.
  - `get(dkey: str) -> np.ndarray | None` — cached array or None (best-effort).
  - `put(dkey: str, arr: np.ndarray) -> None` — atomic best-effort persist.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_vote_cache.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import vote_cache as vc


def test_round_trip_identity(tmp_path):
    vc.set_cache_dir(tmp_path); vc._clear_disk_cache()
    arr = np.array([1, -1, 0, 1, 0, -1], dtype=np.int8)
    k = vc.disk_key(("sig",), True, "ifvg", "confirm", ())
    assert vc.get(k) is None                       # cold
    vc.put(k, arr)
    got = vc.get(k)
    assert got is not None and np.array_equal(got, arr) and got.dtype == arr.dtype


def test_key_isolation():
    base = ("sigA",)
    k1 = vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 5),))
    k2 = vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 6),))   # diff params
    k3 = vc.disk_key(("sigB",), True, "breaker", "confirm", (("swing_l", 5),))  # diff slice
    k4 = vc.disk_key(base, False, "breaker", "confirm", (("swing_l", 5),))  # diff use1
    assert len({k1, k2, k3, k4}) == 4
    # version participates in the key
    old = vc.CACHE_VERSION
    try:
        vc.CACHE_VERSION = "DIFFERENT"
        assert vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 5),)) != k1
    finally:
        vc.CACHE_VERSION = old


def test_best_effort_no_raise(tmp_path):
    vc.set_cache_dir(tmp_path / "does/not/exist/yet")    # put() must create it; get() on missing → None
    assert vc.get(vc.disk_key(("s",), True, "x", "m", ())) is None
    vc.put(vc.disk_key(("s",), True, "x", "m", ()), np.zeros(3, np.int8))  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_vote_cache.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimize.vote_cache'`

- [ ] **Step 3: Implement `optimize/vote_cache.py`**

```python
"""Disk-persistent indicator-vote cache (item 3). Persists the per-(slice, config) vote arrays computed by
core._cached_votes / engine._committee_votes so the cold ifvg/breaker computes are paid ONCE EVER and shared
across worker processes + watchdog respawns. Sits BEHIND the in-process memos; result-neutral by construction
(stores/reloads the exact array). Atomic best-effort write mirrors the L1 disk cache (payload §4.4)."""
from __future__ import annotations
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
import numpy as np

# BUMP whenever any indicator's vote math changes — guards against a stale array (old code) loading.
CACHE_VERSION = "vc1"
_DIR = Path(tempfile.gettempdir()) / "wsh_vote_cache"


def set_cache_dir(path) -> None:
    global _DIR
    _DIR = Path(path)


def _clear_disk_cache() -> None:
    shutil.rmtree(_DIR, ignore_errors=True)


def disk_key(slice_sig, use1, key, mode, params_tuple) -> str:
    raw = repr((CACHE_VERSION, slice_sig, bool(use1), key, mode, params_tuple))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _file(dkey: str) -> Path:
    return _DIR / f"vote_{dkey}.npy"


def get(dkey: str):
    """Cached vote array, or None on miss / any error (best-effort)."""
    f = _file(dkey)
    try:
        if f.exists():
            return np.load(f, allow_pickle=False)
    except Exception:
        pass
    return None


def put(dkey: str, arr) -> None:
    """Atomically persist a vote array; best-effort — never raises into the run."""
    tmp = None
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(_DIR), suffix=".tmp", delete=False) as tf:
            np.save(tf, np.asarray(arr), allow_pickle=False)
            tmp = Path(tf.name)
        os.replace(tmp, _file(dkey))                 # atomic on one filesystem
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink()
            except Exception:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_vote_cache.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add optimize/vote_cache.py optimize/test_vote_cache.py
git commit -m "feat(perf): vote_cache — versioned atomic disk store for indicator votes"
```

---

### Task 2: Wire the disk cache into `core._cached_votes` (L1 fold path)

**Files:**
- Modify: `optimize/core.py` (`_cached_votes`)
- Test: `optimize/test_core_vote_disk.py` (create)

**Interfaces:**
- Consumes: `vote_cache.disk_key/get/put` (Task 1), existing `core._slice_sig`, `core._VOTE_MEMO`.
- Produces: no signature change — `_cached_votes(d, d1, box, inds, src, bar_duration)` now persists/loads votes.

- [ ] **Step 1: Write the failing test (cross-process reuse: clear in-memory memo, disk stays warm)**

```python
# optimize/test_core_vote_disk.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import core, vote_cache
from optimize.l2 import payload
from indicators import library


def test_disk_warm_after_memo_clear_is_identical(tmp_path):
    vote_cache.set_cache_dir(tmp_path); vote_cache._clear_disk_cache(); core._clear_caches()
    l1 = payload.run_l1_cached("4h")
    d, d1, box, bt = l1.df_dec, l1.df1, l1.box, l1.bar_td
    from indicators import runner
    src = runner.indicator_source_1min(d, d1, bt)
    inds = library.from_specs([{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                "params": {"fast": 20, "slow": 50}}])
    v1 = core._cached_votes(d, d1, box, inds, src, bt)            # cold: computes + persists
    arr1 = next(iter(v1.values())).copy()
    core._clear_caches()                                         # simulate a fresh process (memo gone)
    assert not core._VOTE_MEMO                                   # in-memory empty
    v2 = core._cached_votes(d, d1, box, inds, src, bt)           # must HIT disk
    arr2 = next(iter(v2.values()))
    assert np.array_equal(arr1, arr2)                            # byte-identical from disk
    # and the disk file exists for this config
    dkey = vote_cache.disk_key(core._slice_sig(d, d1, bt), True, "ema_trend", "confirm",
                               (("fast", 20), ("slow", 50)))
    assert vote_cache.get(dkey) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_core_vote_disk.py -q`
Expected: FAIL — the disk file assertion fails (votes aren't persisted yet).

- [ ] **Step 3: Modify `core._cached_votes` to consult the disk cache on a memo miss**

Replace the body of `_cached_votes` in `optimize/core.py` with:

```python
def _cached_votes(d, d1, box, inds, src, bar_duration):
    """runner.compute_votes drop-in (dict keyed by id(ind)) with a per-(slice, config) memo, backed by a
    disk cache (vote_cache) so cold computes (ifvg/breaker) persist across processes + respawns. Returned
    arrays are read-only downstream (veto/confirm masks copy), so sharing them is safe. Result-neutral."""
    from indicators import runner
    from optimize import vote_cache
    base = _slice_sig(d, d1, bar_duration)
    use1 = src is not None
    ctx = bdir = None                                    # built lazily, only on a real (memo+disk) miss
    out = {}
    for ind in inds:
        if not ind.config.enabled:
            continue
        c = ind.config
        params_t = tuple(sorted(c.params.items()))
        key = (base, use1, ind.key, c.mode, params_t)
        v = _VOTE_MEMO.get(key)
        if v is None:
            dkey = vote_cache.disk_key(base, use1, ind.key, c.mode, params_t)
            v = vote_cache.get(dkey)
            if v is None:
                if ctx is None:
                    from indicators.runner import market_context, box_direction_int
                    ctx = market_context(d); bdir = box_direction_int(d, box)
                v = runner._ind_vote(ind, ctx, bdir, src)
                vote_cache.put(dkey, v)
            _VOTE_MEMO[key] = v
        out[id(ind)] = v
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_core_vote_disk.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Golden gate (clear the default vote cache first so no dev-time stale array is read)**

Run: `python3 -c "from optimize import vote_cache; vote_cache._clear_disk_cache()" && python3 perf/check_golden.py`
Expected: 6/6 MATCH

- [ ] **Step 6: Commit**

```bash
git add optimize/core.py optimize/test_core_vote_disk.py
git commit -m "feat(perf): back core._cached_votes with the disk vote cache (cross-process reuse)"
```

---

### Task 3: Wire the disk cache into `engine._committee_votes` (L2 path)

**Files:**
- Modify: `optimize/l2/engine.py` (`_committee_votes`)
- Test: `optimize/l2/test_engine_vote_disk.py` (create)

**Interfaces:**
- Consumes: `vote_cache.disk_key/get/put` (Task 1), `core._slice_sig` (for the L1-frame signature), the per-l1 `_l2_vote_memo`.
- Produces: no signature change — `_committee_votes(l1, inds, src)` now persists/loads votes.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_engine_vote_disk.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from optimize import core, vote_cache
from optimize.l2 import engine, payload
from indicators import library


def test_l2_disk_warm_after_memo_clear(tmp_path):
    vote_cache.set_cache_dir(tmp_path); vote_cache._clear_disk_cache()
    l1 = payload.run_l1_cached("4h")
    if hasattr(l1, "_l2_vote_memo"):
        del l1._l2_vote_memo                                     # fresh in-memory memo
    src = engine._cached_1min_source(l1)
    inds = library.from_specs([{"key": "macd", "enabled": True, "mode": "confirm",
                                "params": {"fast": 12, "slow": 26, "signal": 9}}])
    v1 = engine._committee_votes(l1, inds, src)                  # cold: computes + persists
    arr1 = next(iter(v1.values())).copy()
    del l1._l2_vote_memo                                         # simulate a fresh process
    v2 = engine._committee_votes(l1, inds, src)                  # must HIT disk
    assert np.array_equal(arr1, next(iter(v2.values())))
    dkey = vote_cache.disk_key(core._slice_sig(l1.df_dec, l1.df1, l1.bar_td), True, "macd", "confirm",
                               (("fast", 12), ("signal", 9), ("slow", 26)))
    assert vote_cache.get(dkey) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_engine_vote_disk.py -q`
Expected: FAIL — disk file assertion fails (not persisted yet).

- [ ] **Step 3: Modify `engine._committee_votes` to consult the disk cache**

Replace the body of `_committee_votes` in `optimize/l2/engine.py` with:

```python
def _committee_votes(l1, inds, src) -> dict:
    """compute_votes drop-in (dict keyed by id(ind)) with a per-l1 in-memory memo, backed by the disk cache
    (vote_cache) keyed on the L1's frozen-frame signature so cold ifvg/breaker votes persist across processes
    + respawns. Returned arrays are read-only downstream (masks copy). Result-neutral."""
    enabled = [ind for ind in inds if ind.config.enabled]
    if not enabled:
        return {}
    from optimize import vote_cache
    from optimize.core import _slice_sig
    memo = getattr(l1, "_l2_vote_memo", None)
    if memo is None:
        memo = {}
        try:
            l1._l2_vote_memo = memo
        except Exception:
            memo = None                                   # read-only l1 → compute without in-memory caching
    use1 = src is not None
    base = _slice_sig(l1.df_dec, l1.df1, l1.bar_td)        # L1-frame signature for the disk key
    ctx = bdir = None                                     # built lazily, only on a real (memo+disk) miss
    out = {}
    for ind in enabled:
        c = ind.config
        params_t = tuple(sorted(c.params.items()))
        sig = (use1, ind.key, c.mode, params_t)           # in-memory key (per-l1; no slice needed)
        v = memo.get(sig) if memo is not None else None
        if v is None:
            dkey = vote_cache.disk_key(base, use1, ind.key, c.mode, params_t)
            v = vote_cache.get(dkey)
            if v is None:
                if ctx is None:
                    ctx = runner.market_context(l1.df_dec)
                    bdir = runner.box_direction_int(l1.df_dec, l1.box)
                v = runner._ind_vote(ind, ctx, bdir, src)
                vote_cache.put(dkey, v)
            if memo is not None:
                memo[sig] = v
        out[id(ind)] = v
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_engine_vote_disk.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: L2 suite + golden**

Run: `python3 -c "from optimize import vote_cache; vote_cache._clear_disk_cache()" && python3 -m pytest optimize/l2/test_payload.py optimize/l2/test_parity_anchor.py optimize/l2/contributors/ -q && python3 perf/check_golden.py`
Expected: L2 tests pass (78); golden 6/6 MATCH

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/engine.py optimize/l2/test_engine_vote_disk.py
git commit -m "feat(perf): back engine._committee_votes with the disk vote cache (L2 cross-process reuse)"
```

---

### Task 4: Aggregate deep-test gate + doc note

**Files:**
- Modify: `docs/PERFORMANCE.md` (a §9.6 note: votes are disk-persisted across processes/respawns)

- [ ] **Step 1: Run the aggregate gates**

Run: `python3 -c "from optimize import vote_cache; vote_cache._clear_disk_cache()" && python3 -m pytest optimize/test_vote_cache.py optimize/test_core_vote_disk.py optimize/l2/test_engine_vote_disk.py optimize/l2/ -q && python3 perf/check_golden.py`
Expected: all green; golden 6/6 MATCH.

- [ ] **Step 2: Add the doc note**

Append to `docs/PERFORMANCE.md` §9 a short subsection: the per-config indicator votes are now **disk-persisted** (`optimize/vote_cache.py`, versioned + content-signed, atomic best-effort) behind the in-process memos, so the cold `ifvg`/`breaker` computes are paid once-ever and shared across workers + watchdog respawns; result-neutral (golden 6/6), the remaining lever after item 1's per-process memoization (§7.4).

- [ ] **Step 3: Commit**

```bash
git add docs/PERFORMANCE.md
git commit -m "docs(perf): note disk-persistent vote cache (votes shared across processes/respawns)"
```

---

## Self-Review

**Spec coverage:** §3 architecture → Tasks 2,3 (disk tier behind both memos). §4 key (version+slice+config) → Task 1 `disk_key` + Tasks 2/3 callers; both-call-sites slice_sig → Task 2 uses fold `(d,d1)`, Task 3 uses `l1.df_dec/df1`. §5 storage/atomic/best-effort → Task 1 `put`/`get`. §6 public surface → Task 1. §7 testing (round-trip, cross-process reuse, key isolation, best-effort, golden+L2) → Tasks 1 (round-trip/isolation/best-effort), 2 (core cross-process + golden), 3 (L2 cross-process + suite + golden), 4 (aggregate). §8 out-of-scope respected (no source cache, no selectivity, no eviction).

**Placeholder scan:** none — every step has real code/commands.

**Type consistency:** `disk_key(slice_sig, use1, key, mode, params_tuple) -> str` (Task 1) called identically in Tasks 2/3. `get -> np.ndarray|None`, `put(dkey, arr)`. `core._slice_sig(d, d1, bar_td)` reused in Task 3 (import path `from optimize.core import _slice_sig`). `params_tuple = tuple(sorted(c.params.items()))` consistent across both call sites and the tests. No new cycle: `optimize.l2.engine` → `optimize.core` is one-directional (core does not import l2).
