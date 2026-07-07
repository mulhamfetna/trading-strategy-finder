# L2 Intra-Candle Entry Timing for Vetoed Signals (E3a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enter L2's **veto-dropped** candidates mid-candle when L1's veto clears (within L2's own wait window `N`) instead of at the 4h candle close, using L2's own exits — isolating the intra-candle feature's drawdown in L2 while L1 stays the frozen champion.

**Architecture:** Reuse `fast_backtest`'s already-parity-locked intra-candle path. In `run_l2`, when `l2_intracandle` is on, split L2's eligible gate into the **vol-gated** subset (normal candle-close entry, `gate=True`) and the **vetoed** subset (`gate=False`, passed instead as the intra-candle veto-mask), and hand `fast_backtest` the L1-champion intra-candle gate + L2's `N`. No new engine code; no new `DroppedSignal` field.

**Tech Stack:** Python, numpy, pytest. L2 subsystem = `optimize/l2/`; reuses `optimize/core._cached_ic_gate`, `indicators/library`, `optimize/fast_engine.fast_backtest`.

## Global Constraints

- **Additive + default OFF ⇒ byte-identical.** `l2_intracandle` defaults False; off ⇒ `run_l2` builds the exact same `l2_gate` and passes no intra-candle args ⇒ L2 ledger unchanged. Gate: `python3 -m pytest optimize/l2/test_parity_anchor.py -q` green (L2 **$25,383 / 34 / $7,136 DD**; combined **$175,372 / 289 / $14,342 DD**), and `python3 perf/check_golden.py` 6/6.
- **L1 frozen/untouched.** No change to `l1_runner.run_l1`'s L1 engine path; the L1-champion intra-candle gate is built read-only from `l1.params["indicators"]`.
- **Scope = vetoed candidates only.** The vol-gated stream is unchanged (vol gate is per-candle, can't clear mid-candle). No separate force-close (reuse L2's existing L1-priority).
- **Reuse the memoised gate.** `core._cached_ic_gate(df1, inds, k)` == `runner.intracandle_gate_arrays` (locked by `optimize/test_intracandle_parity.py::test_cached_ic_gate_matches_runner_and_memoises`).
- **Constants:** direction ints LONG=1/SHORT=−1 (`fast_engine`); NQ point value $20; anchor NQ 4h.
- TDD, frequent commits.

---

### Task 1: L2 schema — add `l2_intracandle` + `l2_intracandle_max_wait`

**Files:**
- Modify: `optimize/l2/payload.py` (`validate_layer_params`, ~:189-224)
- Test: `optimize/l2/test_intracandle_schema.py` (create)

**Interfaces:**
- Produces: validated params gain `l2_intracandle: bool` (default `False`) and `l2_intracandle_max_wait: int` (default `240`). Absent ⇒ defaults ⇒ round-trip unchanged.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_intracandle_schema.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2.payload import validate_layer_params

def test_intracandle_defaults_off():
    p = validate_layer_params({"sl_soft": 30, "sl_hard": 40, "tp": 60})
    assert p["l2_intracandle"] is False
    assert p["l2_intracandle_max_wait"] == 240

def test_intracandle_roundtrip():
    p = validate_layer_params({"sl_soft": 30, "sl_hard": 40, "tp": 60,
                               "l2_intracandle": True, "l2_intracandle_max_wait": 60})
    assert p["l2_intracandle"] is True and p["l2_intracandle_max_wait"] == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_intracandle_schema.py -q`
Expected: FAIL — `KeyError: 'l2_intracandle'`

- [ ] **Step 3: Implement** — in `validate_layer_params`, where the other scalar fields are assembled into the returned dict (near the `cap_1min`/`cap_mode` handling ~:189-198), add:

```python
        out["l2_intracandle"] = bool(raw.get("l2_intracandle", False))
        out["l2_intracandle_max_wait"] = int(raw.get("l2_intracandle_max_wait", 240) or 240)
```
(Use the same source dict the function reads other scalars from — match the local variable name for the incoming params and the output dict in that function; `raw`/`out` above are placeholders for those two locals.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_intracandle_schema.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_intracandle_schema.py
git commit -m "feat(l2): l2_intracandle + max_wait schema fields (default off)"
```

---

### Task 2: `run_l2` — intra-candle timing for the vetoed stream

**Files:**
- Modify: `optimize/l2/engine.py` (`run_l2`, :198-235)
- Test: `optimize/l2/test_intracandle_engine.py` (create)

**Interfaces:**
- Consumes: `l1.dropped_signals` (`[{idx, reason}]`, reason ∈ {"veto","vol_gate"}), `l1.params["indicators"]`, `l1.params["k"]`, `l1.df1`; `core._cached_ic_gate`; `l2_params["l2_intracandle"]`, `["l2_intracandle_max_wait"]`.
- Behaviour: `l2_intracandle` **off** ⇒ identical ledger. **On** ⇒ vetoed candidates enter at the first 1-min bar L1's veto clears within `N` (skipped if never), vol-gated candidates unchanged.

- [ ] **Step 1: Write the failing tests** (parity off, and on-changes-vetoed)

```python
# optimize/l2/test_intracandle_engine.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from optimize.l2 import l1_runner, engine
from optimize.l2.payload import validate_layer_params

L2 = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=0, dd_limit=0, cooldown=0, k=1,
          flip=False, ind_1min=False, indicators=[])

def _run(over):
    l1 = l1_runner.run_l1("4h")
    p = validate_layer_params({**L2, **over})
    return engine.run_l2(l1, p).ledger

def test_off_is_identical():
    base = _run({"l2_intracandle": False})
    again = _run({"l2_intracandle": False})
    assert [t["entry_time"] for t in base] == [t["entry_time"] for t in again]
    assert len(base) > 0

def test_on_moves_vetoed_entries():
    off = _run({"l2_intracandle": False})
    on = _run({"l2_intracandle": True, "l2_intracandle_max_wait": 240})
    # some entry_times differ (vetoed candidates now enter mid-candle, not at the 4h close)
    assert {t["entry_time"] for t in on} != {t["entry_time"] for t in off}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest optimize/l2/test_intracandle_engine.py -q`
Expected: `test_off_is_identical` PASS (no-op path), `test_on_moves_vetoed_entries` FAIL (flag ignored ⇒ sets equal).

- [ ] **Step 3: Implement** — in `run_l2`, after `l2_gate` is built (:216-218) and before the `fast_backtest` call (:226), split the gate and prepare intra-candle args when the flag is on:

```python
    ic_kwargs = {}
    if l2_params.get("l2_intracandle"):
        from optimize.core import _cached_ic_gate
        from indicators import library
        veto_reason = np.zeros(n, dtype=bool)
        for ds in l1.dropped_signals:
            if ds["reason"] == "veto":
                veto_reason[int(ds["idx"])] = True
        veto_ic = l2_gate & veto_reason               # vetoed candidates → intra-candle
        l2_gate = l2_gate & ~veto_reason               # vol-gated (+non-veto) → normal candle-close entry
        inds = library.from_specs([s for s in l1.params["indicators"] if s.get("enabled")])
        ic_kwargs = dict(
            intracandle_gate_by_dir=_cached_ic_gate(l1.df1, inds, int(l1.params["k"])),
            intracandle_veto_mask=veto_ic,
            intracandle_vol_gate=veto_ic,              # True exactly at vetoed IC candidates (vol-passed)
            intracandle_max_wait=int(l2_params.get("l2_intracandle_max_wait", 240)))
```

Then pass `**ic_kwargs` into the `fast_backtest(...)` call (add it to the existing kwargs). Off ⇒ `ic_kwargs` empty ⇒ call byte-identical.

> **Executor note (nuance to verify):** `fast_backtest`'s intra-candle path uses the POST-flip direction for the `intracandle_gate_by_dir[d]` lookup. With L2 `flip=True` the gate is read for the flipped side. If a parity/behaviour test shows this is wrong for L2's intent (enter when the veto clears for the BOX side), pass the box-direction gate explicitly; otherwise accept `fast_backtest`'s behaviour. The champion L2 (l2v2) uses reverse-entry — confirm the sweep (Task 4) still improves.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest optimize/l2/test_intracandle_engine.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/engine.py optimize/l2/test_intracandle_engine.py
git commit -m "feat(l2): intra-candle entry timing for the vetoed stream (default off)"
```

---

### Task 3: Parity anchors + golden (the hard guarantee)

**Files:** none (verification only).

- [ ] **Step 1: L2 anchors**

Run: `python3 -m pytest optimize/l2/test_parity_anchor.py -q`
Expected: PASS — L2 $25,383 / 34 / $7,136; combined $175,372 / 289 / $14,342 (the l2v2 champion sets no `l2_intracandle` key ⇒ off ⇒ unchanged).

- [ ] **Step 2: Golden**

Run: `python3 perf/check_golden.py`
Expected: `✅ ALL GOLDEN BASELINES MATCH` (6/6). If any mismatch — STOP; the `l2_intracandle`-off path leaked.

- [ ] **Step 3: Commit** (marker)

```bash
git commit --allow-empty -m "test(l2): parity anchors + golden 6/6 with l2_intracandle off"
```

---

### Task 4: Champion-first N-sweep of the combined book

**Files:**
- Create: `research/intracandle/l2_sweep.py`
- Test: `research/intracandle/test_l2_sweep_smoke.py`

**Interfaces:**
- Consumes: `l1_runner.run_l1`, `engine.run_l2`, `optimize.l2.metrics.combined`, `l2_default_params` (the l2v2 champion).
- Produces: `sweep(tf="4h", Ns=(30,60,120,240))` → rows `{N, combined_pnl, combined_n, combined_dd, l2_n, l2_pnl}`; baseline (l2_intracandle off) + per-N on.

- [ ] **Step 1: Write the failing smoke test**

```python
# research/intracandle/test_l2_sweep_smoke.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.intracandle.l2_sweep import sweep

def test_sweep_rows():
    rows = sweep("4h", Ns=(60,))
    assert rows[0]["N"] == 60
    assert "combined_pnl" in rows[0] and "combined_dd" in rows[0]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest research/intracandle/test_l2_sweep_smoke.py -q`
Expected: FAIL — `ModuleNotFoundError: research.intracandle.l2_sweep`

- [ ] **Step 3: Implement**

```python
# research/intracandle/l2_sweep.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from optimize.l2 import l1_runner, engine, metrics
from optimize.l2.payload import validate_layer_params, l2_default_params

def _dd(pnls):
    a = np.asarray(pnls, float); eq = np.cumsum(a); pk = np.maximum.accumulate(eq)
    return float((pk - eq).max()) if a.size else 0.0

def _combined(l1, l2res):
    c = metrics.combined(l1.ledger, l2res.ledger)          # merged book (exit-time order)
    pnls = [t.get("pnl", t["pnl_points"] * 20.0) for t in c["trades"]] if isinstance(c, dict) else []
    return c, pnls

def sweep(tf="4h", Ns=(30, 60, 120, 240)):
    l1 = l1_runner.run_l1(tf)
    base = dict(l2_default_params(tf))
    rows = []
    for N in Ns:
        p = validate_layer_params({**base, "l2_intracandle": True, "l2_intracandle_max_wait": N})
        r = engine.run_l2(l1, p)
        c, pnls = _combined(l1, r)
        rows.append({"N": N, "l2_n": len(r.ledger),
                     "l2_pnl": float(sum(t["pnl_points"] * 20.0 for t in r.ledger)),
                     "combined_pnl": float(c.get("pnl", 0.0)) if isinstance(c, dict) else 0.0,
                     "combined_n": int(c.get("n", 0)) if isinstance(c, dict) else 0,
                     "combined_dd": float(c.get("max_dd", _dd(pnls))) if isinstance(c, dict) else _dd(pnls)})
    return rows

if __name__ == "__main__":
    import json
    print("baseline combined (l2_intracandle OFF): $175,372 / 289 / $14,342")
    for r in sweep():
        print(json.dumps(r))
```

> **Executor note:** confirm `metrics.combined(l1_ledger, l2_ledger)`'s exact return keys (`pnl`/`n`/`max_dd`/`trades`) against `optimize/l2/metrics.py:38-46` and adjust the `.get` field names to match; the smoke test only checks the row shape.

- [ ] **Step 4: Run the smoke test + the real sweep**

Run: `python3 -m pytest research/intracandle/test_l2_sweep_smoke.py -q` → PASS
Run: `python3 -m research.intracandle.l2_sweep` → prints baseline + one row per N.

- [ ] **Step 5: Commit**

```bash
git add research/intracandle/l2_sweep.py research/intracandle/test_l2_sweep_smoke.py
git commit -m "feat(l2): champion-first N-sweep of the combined book (intra-candle timing)"
```

---

### Task 5: L2 optimizer — search `N` under a new prefix `l2ic1`

**Files:**
- Modify: `optimize/l2/optimize.py` (`suggest_l2_params` ~:43-68; add `--intracandle` flag + default prefix)
- Test: `optimize/l2/test_intracandle_optimize.py`

**Interfaces:**
- Produces: when `--intracandle`, `suggest_l2_params` adds `l2_intracandle=True` (forced-on focused study) + `l2_intracandle_max_wait ∈ {30,60,120,240}`; off ⇒ search space unchanged. New study prefix `l2ic1`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_intracandle_optimize.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import optuna
from optimize.l2.optimize import suggest_l2_params

def test_intracandle_dims_added():
    def obj(trial):
        p = suggest_l2_params(trial, intracandle=True)
        assert p["l2_intracandle"] is True
        assert p["l2_intracandle_max_wait"] in (30, 60, 120, 240)
        return 0.0
    optuna.create_study().optimize(obj, n_trials=3)

def test_default_space_unchanged():
    def obj(trial):
        p = suggest_l2_params(trial)          # no intracandle
        assert "l2_intracandle_max_wait" not in p
        return 0.0
    optuna.create_study().optimize(obj, n_trials=2)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest optimize/l2/test_intracandle_optimize.py -q`
Expected: FAIL — `suggest_l2_params()` has no `intracandle` kwarg.

- [ ] **Step 3: Implement** — add an `intracandle: bool = False` kwarg to `suggest_l2_params`; at the end of the built params dict add:

```python
    if intracandle:
        params["l2_intracandle"] = True
        params["l2_intracandle_max_wait"] = trial.suggest_categorical(
            "l2_intracandle_max_wait", [30, 60, 120, 240])
```

Thread an `intracandle=False` param through `run()` (`optimize/l2/optimize.py:71`) into the `objective` closure, add a `--intracandle` CLI arg, and set the default study prefix to `l2ic1` when it's passed (leave `l2v1` otherwise).

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m pytest optimize/l2/test_intracandle_optimize.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/optimize.py optimize/l2/test_intracandle_optimize.py
git commit -m "feat(l2-opt): --intracandle search dim (N) under prefix l2ic1"
```

---

## Self-Review

**Spec coverage:** §3 timing toggle → Task 2. §4 schema+optimizer → Tasks 1,5. §5 golden-safety → Task 3. §7 champion-first sweep → Task 4; l2ic1 optimizer → Task 5; OOS = the L2 optimizer's existing 2025/2026 windows (Task 5 inherits). vol-gated unchanged + no force-close → Task 2 (only `reason=="veto"` split). ✅

**Placeholder scan:** the two "Executor note" items are concrete verification steps with a named fallback (flip-direction gate; `metrics.combined` key names) — not open TODOs. The `raw`/`out` locals in Task 1 Step 3 are explicitly flagged as stand-ins for the function's actual local names. No other placeholders.

**Type consistency:** `l2_intracandle`(bool)/`l2_intracandle_max_wait`(int) consistent across Tasks 1,2,4,5. `_cached_ic_gate(df1, inds, k)` returns `{+1,-1}` bool arrays (Task 2) as consumed by `fast_backtest`'s `intracandle_gate_by_dir` (parity-locked). ✅

## Verification (end-to-end)
1. `python3 -m pytest optimize/l2/test_intracandle_schema.py optimize/l2/test_intracandle_engine.py optimize/l2/test_intracandle_optimize.py research/intracandle/test_l2_sweep_smoke.py -q` → all pass.
2. `python3 -m pytest optimize/l2/test_parity_anchor.py -q` + `python3 perf/check_golden.py` → anchors + 6/6 (feature off).
3. `python3 -m research.intracandle.l2_sweep` → does any N beat combined $175,372 at ≤ $14,342 DD? → gate to the `l2ic1` server optimization (2026 OOS via the L2 optimizer windows).
