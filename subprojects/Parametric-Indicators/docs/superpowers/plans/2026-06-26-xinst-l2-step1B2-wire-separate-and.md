# Cross-Instrument L2 — Step 1·Part B2: Wire Contributors into the L2 Gate (SEPARATE-AND topology)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline) or subagent-driven-development. Steps use `- [ ]`.

**Goal:** Wire `contributors.gate.contributor_gate_masks` into `engine.run_l2` so an enabled ES contributor tightens the L2 gate via the SEPARATE-AND topology — `l2_gate &= ~contrib_veto & (contrib_confirm_count >= k_es)` — with absent/disabled contributors a pure no-op (byte-identical L2).

**Architecture:** One small, guarded edit to `optimize/l2/engine.py` `run_l2` (insert a `_apply_contributors` call right after the base `l2_gate` is built) + a `_apply_contributors` helper. SEPARATE-AND only ANDs sub-gates, so it can only REMOVE L2 trades (ON entries ⊆ OFF entries) — never add — and the sentinel (`NO_CONFIRM_CONSTRAINT >= any k_es`) + all-False veto make a disabled contributor the identity. MERGED / OR-confirm-boost (which need NQ's confirm *count*) are Part B2b.

**Tech Stack:** Python 3, numpy. Reuse B1's `gate.contributor_gate_masks` by import.

## Global Constraints
- **No `contributors` key ⇒ byte-identical L2 ⇒ golden 6/6.** The new code runs ONLY when `l2_params["contributors"]` is truthy; the existing path is untouched. golden (L1) is trivially unaffected; an L2-parity test pins the no-contributors path.
- A **disabled** contributor (`enabled=False`, or the absent block) is the identity (no AND).
- SEPARATE-AND can only tighten: ON entries are a SUBSET of OFF entries.
- Causality already proven in B1 (gate masks are entry-aligned + look-ahead-guarded).

**Files:** Modify `optimize/l2/engine.py` (`run_l2` ~line 110 + new `_apply_contributors`); Test `optimize/l2/contributors/test_contrib_wiring.py`.

**Confirmed seam (read 2026-06-26):** `run_l2` (engine.py:92) builds `l2_gate = dropped_mask & l1_flat & _l2_gate_masks(l1, l2_params)` at line 110, then optionally `& bar_mask`. `l2_gate_components` returns `(vol_gate, veto, confirm:bool)`. `gate.contributor_gate_masks(cfg, l1) -> (veto:bool[n], confirm_count:int64[n])`, entry-aligned, `NO_CONFIRM_CONSTRAINT=np.int64(1<<30)`.

---

### Task 1: Pin the L2-parity baseline + the no-op guard

**Interfaces:** Produces nothing new yet (baseline-only); locks the numbers Task 2 must preserve.

- [ ] **Step 1: capture baseline (one-off, before any edit)** — run, record `n_taken` and rounded total pnl for a fixed config on the frozen L1:
```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
python3 -c "
from optimize.l2 import payload, engine
import numpy as np
l1 = payload.run_l1_cached('4h')
P = {'sl_soft':140.0,'sl_hard':200.0,'tp':200.0,'gate_pct':0.0,'dd_limit':0.0,'cooldown':0,'flip':False,
     'k':1,'ind_1min':True,'indicators':[{'key':'ema_trend','enabled':True,'mode':'confirm','params':{'fast':20,'slow':50}}]}
r = engine.run_l2(l1, P)
print('BASELINE n_taken=', len(r.ledger), 'pnl=', round(sum(t['pnl_points'] for t in r.ledger),4))
"
```
Record the printed `n_taken` and `pnl` — call them `BASE_N` and `BASE_PNL`. Use them VERBATIM in the test below.

- [ ] **Step 2: write the failing test** — `optimize/l2/contributors/test_contrib_wiring.py` (substitute the captured `BASE_N`/`BASE_PNL`):
```python
import sys
from pathlib import Path
_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import numpy as np
from optimize.l2 import payload, engine

_P = {"sl_soft": 140.0, "sl_hard": 200.0, "tp": 200.0, "gate_pct": 0.0, "dd_limit": 0.0,
      "cooldown": 0, "flip": False, "k": 1, "ind_1min": True,
      "indicators": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                      "params": {"fast": 20, "slow": 50}}]}
BASE_N = 0      # <-- replace with captured value
BASE_PNL = 0.0  # <-- replace with captured value


def _n_pnl(r):
    return len(r.ledger), round(sum(t["pnl_points"] for t in r.ledger), 4)


def test_no_contributors_is_byte_identical_baseline():
    l1 = payload.run_l1_cached("4h")
    assert _n_pnl(engine.run_l2(l1, _P)) == (BASE_N, BASE_PNL)            # absent block
    assert _n_pnl(engine.run_l2(l1, {**_P, "contributors": []})) == (BASE_N, BASE_PNL)  # empty
    assert _n_pnl(engine.run_l2(l1, {**_P, "contributors": [
        {"token": "ES", "enabled": False}]})) == (BASE_N, BASE_PNL)      # explicitly disabled
```
- [ ] **Step 3: run, expect PASS already** (no edit yet — the absent/empty/disabled paths must already equal baseline; this is the regression net BEFORE wiring). `python3 -m pytest optimize/l2/contributors/test_contrib_wiring.py -q`. If the disabled-block case errors (KeyError on `contributors`), that's expected to fail → proceed to Task 2 which makes it pass; otherwise it passes trivially.
- [ ] **Step 4: commit** — `test(l2-contrib/wiring): pin L2-parity baseline (no-contributors == BASE)`

---

### Task 2: Wire SEPARATE-AND into run_l2

**Interfaces:** Produces `engine._apply_contributors(l1, l2_params, l2_gate) -> np.ndarray`; `run_l2` honors `l2_params["contributors"]` + `l2_params["contributor_topology"]` (default `"separate_and"`).

- [ ] **Step 1: write the failing test** — append to `test_contrib_wiring.py`:
```python
def _es_on(topology="separate_and"):
    return {**_P, "contributor_topology": topology, "contributors": [
        {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
         "signal": {"encoding": "stance", "mode": "both"},
         "committee": [{"key": "cci", "enabled": True, "mode": "veto",
                        "params": {"n": 20, "threshold": 100}}]}]}


def test_separate_and_only_tightens_entries_subset():
    l1 = payload.run_l1_cached("4h")
    off = {int(t["entry_idx"]) for t in engine.run_l2(l1, _P).ledger}
    on = {int(t["entry_idx"]) for t in engine.run_l2(l1, _es_on()).ledger}
    assert on <= off                      # SEPARATE-AND can only remove L2 entries, never add
    assert len(on) <= BASE_N


def test_unsupported_topology_raises():
    l1 = payload.run_l1_cached("4h")
    import pytest
    with pytest.raises(ValueError, match="topology"):
        engine.run_l2(l1, _es_on(topology="merged"))   # B2b adds merged/or_boost
```
- [ ] **Step 2: run, expect fail** (separate_and not wired ⇒ `on == off`, or contributors ignored).
- [ ] **Step 3: implement** — in `optimize/l2/engine.py`, insert after the `l2_gate = dropped_mask & l1_flat & _l2_gate_masks(l1, l2_params)` line (≈110):
```python
    l2_gate = _apply_contributors(l1, l2_params, l2_gate)   # cross-instrument sub-gate (no-op if none)
```
and add the helper (above `run_l2`):
```python
def _apply_contributors(l1, l2_params: dict, l2_gate: np.ndarray) -> np.ndarray:
    """AND each ENABLED cross-instrument contributor's sub-gate into the L2 gate. Topology
    'separate_and': sub = ~contrib_veto & (contrib_confirm_count >= k_es). Absent/disabled contributors
    are the identity (sentinel confirm_count >= any k_es, all-False veto) ⇒ byte-identical contributor-free
    L2. MERGED / OR-confirm-boost are Part B2b."""
    contribs = l2_params.get("contributors")
    if not contribs:
        return l2_gate
    from optimize.l2.contributors import gate as contrib_gate
    topo = str(l2_params.get("contributor_topology", "separate_and"))
    out = l2_gate
    for cfg in contribs:
        if not cfg.get("enabled"):
            continue
        cveto, ccount = contrib_gate.contributor_gate_masks(cfg, l1)
        if topo == "separate_and":
            k_es = int(cfg.get("k_es", 1))
            out = out & (~cveto) & (ccount >= k_es)
        else:
            raise ValueError(f"unsupported contributor_topology {topo!r} (B2b adds merged/or_boost)")
    return out
```
- [ ] **Step 4: run, expect pass** — the 3 wiring tests + the Task-1 parity test all green.
- [ ] **Step 5: commit** — `feat(l2-engine): wire contributors into run_l2 (SEPARATE-AND topology, no-op when absent)`

---

### Task 3: Regression — full suite + golden

- [ ] **Step 1:** `python3 -m pytest optimize/l2/ -q` (all green, incl. the existing L2 + contributors suites).
- [ ] **Step 2:** `python3 perf/check_golden.py` → **6/6 MATCH** (L1 untouched; the run_l2 edit is guarded).
- [ ] **Step 3: commit** if any test-only fixes were needed — `test(l2): B2 regression green (suite + golden 6/6)`.

---

## Definition of done for B2
An enabled ES contributor tightens the L2 gate via SEPARATE-AND; no-contributors L2 is byte-identical (pinned baseline); golden 6/6. **Next:** B2b — MERGED (pool NQ+contrib confirm counts; requires exposing NQ's confirm count from `l2_gate_components`) + OR-confirm-boost + the `contributor_topology` selector; then B3 — the `es_*`/`contributors` namespaced search space in `suggest_l2_params`.
