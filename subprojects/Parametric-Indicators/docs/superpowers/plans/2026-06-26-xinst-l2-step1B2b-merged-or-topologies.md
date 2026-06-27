# Cross-Instrument L2 — Step 1·Part B2b: MERGED + OR-confirm-boost topologies

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use `- [ ]`.

**Goal:** Add the two remaining gate topologies the optimizer can choose — **MERGED** (pool NQ + contributor confirm *counts* toward one K) and **OR-confirm-boost** (a contributor's confirm can rescue a bar NQ didn't confirm) — alongside the existing **SEPARATE-AND**, by exposing NQ's confirm count and combining components per topology.

**Architecture:** Add `engine._nq_components(l1, l2_params)` returning the raw NQ gate ingredients `(vol_gate, veto, confirm_mask, confirm_count_entry, k_eff, n_confirmers)`; refactor `l2_gate_components` to DELEGATE to it (its `(vol_gate, veto, confirm)` return stays byte-identical — the logbook caller is unaffected). Replace `run_l2`'s gate construction (`_l2_gate_masks` + `_apply_contributors`) with one topology-aware `engine._l2_eligibility(l1, l2_params)` that combines NQ components with enabled contributors. Veto is always any-OR. Per topology the CONFIRM combines differently; a contributor with NO confirm source (sentinel count) contributes nothing in any topology, so **no enabled confirm/veto contributor ⇒ the NQ gate exactly** (byte-parity).

**Tech Stack:** Python 3, numpy. Reuse B1 `gate.contributor_gate_masks` + the runner committee functions.

## Global Constraints
- **No enabled contributor (absent/empty/all-disabled) ⇒ byte-identical L2 under EVERY topology ⇒ golden 6/6.** Pinned L2 baseline = **162 trades / −490.25** (config `_P` from B2). It must hold for `separate_and`, `merged`, AND `or_boost` when no contributor is enabled.
- `l2_gate_components(l1, l2_params)` return signature `(vol_gate, veto, confirm)` UNCHANGED (logbook.py:152 depends on it).
- NQ confirm count reconstruction must match `runner.confirm_mask` exactly: `confirm_mask[i] = (count[i-1] >= k_eff)` for i≥1, `confirm_mask[0] = True`; `k_eff = min(k, #confirmers)`; 0 confirmers ⇒ all-True.
- Veto is any-OR in all topologies. A contributor whose `confirm_count` is all-`NO_CONFIRM_CONSTRAINT` (no confirm source) adds no confirm in any topology.

**Files:** Modify `optimize/l2/engine.py`; Test `optimize/l2/contributors/test_contrib_topologies.py`; update `optimize/l2/contributors/test_contrib_wiring.py` (its `_apply_contributors` test → `_l2_eligibility`).

---

### Task 1: `_nq_components` + delegate `l2_gate_components` (no behavior change)

**Interfaces:** Produces `engine._nq_components(l1, l2_params) -> (vol_gate:bool[n], veto:bool[n], confirm:bool[n], cc_entry:int64[n], k_eff:int, n_confirmers:int)`. `confirm == runner.confirm_mask`; `cc_entry[i]` = #confirms at bar i-1 (idx0=0).

- [ ] **Step 1: failing test** — `optimize/l2/contributors/test_contrib_topologies.py`:
```python
import sys
from pathlib import Path
_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import numpy as np
from optimize.l2 import payload, engine

_P = {"sl_soft": 140.0, "sl_hard": 200.0, "tp": 200.0, "gate_pct": 0.0, "dd_limit": 0.0,
      "cooldown": 0, "flip": False, "k": 2, "ind_1min": True,
      "indicators": [{"key": "ema_trend", "enabled": True, "mode": "confirm", "params": {"fast": 20, "slow": 50}},
                     {"key": "macd", "enabled": True, "mode": "confirm", "params": {"fast": 12, "slow": 26, "signal": 9}}]}


def test_nq_components_confirm_count_reconstructs_mask():
    l1 = payload.run_l1_cached("4h")
    vol_gate, veto, confirm, cc, k_eff, ncf = engine._nq_components(l1, _P)
    n = len(confirm)
    rebuilt = np.ones(n, dtype=bool)
    rebuilt[1:] = (cc[1:] >= k_eff)               # cc is already entry-shifted; idx0 identity True
    assert k_eff == 2 and ncf == 2
    assert np.array_equal(rebuilt, confirm)        # count reconstructs runner.confirm_mask exactly


def test_l2_gate_components_unchanged_after_delegation():
    l1 = payload.run_l1_cached("4h")
    vg, vt, cf = engine.l2_gate_components(l1, _P)
    vg2, vt2, cf2, _, _, _ = engine._nq_components(l1, _P)
    assert np.array_equal(vg, vg2) and np.array_equal(vt, vt2) and np.array_equal(cf, cf2)
```
- [ ] **Step 2: run, expect fail** (`_nq_components` undefined).
- [ ] **Step 3: implement** — add `_nq_components` (copy `l2_gate_components`'s body, additionally compute the entry-shifted confirm count + k_eff + n_confirmers), and make `l2_gate_components` delegate:
```python
def _nq_components(l1, l2_params: dict):
    """NQ's raw gate ingredients for topology pooling. Superset of l2_gate_components: also returns the
    entry-shifted confirm COUNT, k_eff, and #confirmers. confirm == runner.confirm_mask exactly."""
    from indicators.base import CONFIRM
    d, d1, box = l1.df_dec, l1.df1, l1.box
    n = len(d)
    gate_pct = float(l2_params.get("gate_pct", 0.0))
    K = int(l2_params.get("k", 1))
    vol_gate = np.ones(n, dtype=bool)
    if gate_pct > 0:
        seed = l1.vf_seed if l1.vf_seed is not None else l1.vf[:l1.n_split]
        gthr = gate_threshold(seed, len(seed), gate_pct)
        vol_gate = l1.vf[:n] <= gthr
    veto = np.zeros(n, dtype=bool)
    confirm = np.ones(n, dtype=bool)
    cc_entry = np.zeros(n, dtype=np.int64); k_eff = 0; n_confirmers = 0
    specs = [s for s in l2_params.get("indicators", []) if s.get("enabled")]
    if specs:
        inds = library.from_specs(specs)
        src = runner.indicator_source_1min(d, d1, l1.bar_td) if l2_params.get("ind_1min") else None
        votes = runner.compute_votes(d, box, inds, src=src)
        veto = np.asarray(runner.veto_mask(d, box, inds, src=src, votes=votes), dtype=bool)[:n]
        confirm = np.asarray(runner.confirm_mask(d, box, inds, K, src=src, votes=votes), dtype=bool)[:n]
        confirmers = [i for i in inds if i.config.enabled and i.config.mode in ("confirm", "both")]
        n_confirmers = len(confirmers)
        k_eff = min(K, n_confirmers)
        if k_eff > 0:
            cc = np.zeros(n, dtype=np.int64)
            for ind in confirmers:
                cc += (votes[id(ind)] == CONFIRM).astype(np.int64)
            cc_entry[1:] = cc[:-1]                 # entry-shift (confirms read at idx-1); idx0=0
    return vol_gate, veto, confirm, cc_entry, k_eff, n_confirmers


def l2_gate_components(l1, l2_params: dict):
    """(vol_gate, veto, confirm) — unchanged public shape (logbook attribution). Delegates to
    _nq_components so the count path and this share one source of truth."""
    vol_gate, veto, confirm, _, _, _ = _nq_components(l1, l2_params)
    return vol_gate, veto, confirm
```
(Delete the old body of `l2_gate_components`.)
- [ ] **Step 4: run, expect pass** + quick `pytest optimize/l2/contributors/test_contrib_topologies.py optimize/l2/contributors/test_contrib_wiring.py -q`.
- [ ] **Step 5: commit** — `refactor(l2-engine): _nq_components superset (+confirm count); l2_gate_components delegates (byte-identical)`

---

### Task 2: `_l2_eligibility` topology combiner + rewire run_l2

**Interfaces:** Produces `engine._l2_eligibility(l1, l2_params) -> bool[n]` (= vol_gate & ~veto & confirm, contributor-combined per topology). `run_l2` builds `l2_gate = dropped_mask & l1_flat & _l2_eligibility(l1, l2_params)`. `_apply_contributors` is removed.

- [ ] **Step 1: failing test** — append to `test_contrib_topologies.py`. Pin the no-contributor byte-parity under all 3 topologies, plus per-topology behavior + a disabled-contributor identity:
```python
def _n_pnl(r):
    return len(r.ledger), round(sum(t["pnl_points"] for t in r.ledger), 4)


def _es(topology, k_es=1, mode="both", enabled=True):
    return {**_P, "contributor_topology": topology, "contributors": [
        {"token": "ES", "enabled": enabled, "tf": "4h", "state_def": "touch", "k_es": k_es,
         "signal": {"encoding": "stance", "mode": mode}, "committee": []}]}


def test_disabled_contributor_byte_parity_all_topologies():
    l1 = payload.run_l1_cached("4h")
    base = _n_pnl(engine.run_l2(l1, _P))
    for topo in ("separate_and", "merged", "or_boost"):
        assert _n_pnl(engine.run_l2(l1, _es(topo, enabled=False))) == base   # disabled => identity


def test_merged_pools_confirm_or_boost_rescues_gate_level():
    l1 = payload.run_l1_cached("4h")
    n = len(l1.df_dec)
    sep = engine._l2_eligibility(l1, _es("separate_and", k_es=1, mode="both"))
    mer = engine._l2_eligibility(l1, _es("merged", k_es=1, mode="both"))
    org = engine._l2_eligibility(l1, _es("or_boost", k_es=1, mode="both"))
    base = engine._l2_eligibility(l1, _P)
    assert sep.shape == mer.shape == org.shape == (n,)
    assert bool((sep <= base).all())              # separate-AND only tightens the gate
    assert bool((base <= org).all())              # or-boost only loosens the confirm side (>= base) ...
    # (veto can still tighten or_boost; assert at least that or_boost differs from separate where it should)
    assert not np.array_equal(sep, org)


def test_unsupported_topology_raises():
    import pytest
    l1 = payload.run_l1_cached("4h")
    with pytest.raises(ValueError, match="topology"):
        engine.run_l2(l1, _es("nonsense"))
```
(Refine the or_boost ≥ base assertion against the first run — or_boost loosens *confirm* but veto still ANDs; if the ES stance has a veto channel, drop the global `base<=org` and assert the confirm-only effect via a veto-free `mode="confirm"` cfg. Keep the disabled-parity + separate-tightens + raises asserts strict.)
- [ ] **Step 2: run, expect fail** (`_l2_eligibility` undefined / merged-or unsupported).
- [ ] **Step 3: implement** — add `_l2_eligibility` (the combiner below), change `run_l2` line ~133 to `l2_gate = dropped_mask & l1_flat & _l2_eligibility(l1, l2_params)`, and DELETE `_apply_contributors`:
```python
def _l2_eligibility(l1, l2_params: dict) -> np.ndarray:
    """NQ eligibility (vol_gate & ~veto & confirm) combined with enabled cross-instrument contributors
    per topology (Spec §6). Veto = any-OR. CONFIRM: separate_and = NQ ∧ each (count>=k_es); merged =
    pooled count >= min(k, #sources); or_boost = NQ ∨ any (count>=k_es). A contributor with no confirm
    source (sentinel count) adds no confirm in any topology ⇒ no enabled contributor ⇒ the NQ gate."""
    vol_gate, nq_veto, nq_confirm, nq_cc, k_eff, nq_nconf = _nq_components(l1, l2_params)
    n = len(vol_gate)
    contribs = [c for c in (l2_params.get("contributors") or []) if c.get("enabled")]
    if not contribs:
        return vol_gate & ~nq_veto & nq_confirm
    from optimize.l2.contributors import gate as cg
    topo = str(l2_params.get("contributor_topology", "separate_and"))
    veto = nq_veto.copy()
    parsed = []
    for cfg in contribs:
        cveto, ccount = cg.contributor_gate_masks(cfg, l1)
        veto |= cveto
        has_confirm = not bool((ccount == cg.NO_CONFIRM_CONSTRAINT).all())
        parsed.append((ccount, int(cfg.get("k_es", 1)), has_confirm))
    if topo == "separate_and":
        confirm = nq_confirm.copy()
        for ccount, k_es, _ in parsed:
            confirm = confirm & (ccount >= k_es)              # sentinel => True => no-op
    elif topo == "merged":
        pooled = nq_cc.copy(); n_sources = nq_nconf
        for ccount, _k, has in parsed:
            if has:
                pooled = pooled + ccount; n_sources += 1
        k_m = min(int(l2_params.get("k", 1)), n_sources)
        confirm = np.ones(n, dtype=bool)
        if k_m > 0:
            confirm[1:] = pooled[1:] >= k_m                   # idx0 identity True; pooled entry-shifted
    elif topo == "or_boost":
        boost = np.zeros(n, dtype=bool)
        for ccount, k_es, has in parsed:
            if has:
                boost |= (ccount >= k_es)
        confirm = nq_confirm | boost
    else:
        raise ValueError(f"unsupported contributor_topology {topo!r}")
    return vol_gate & ~veto & confirm
```
- [ ] **Step 4: run** — fix the no-contributor merged/or byte-parity if it trips (the `min(k,#sources)`/idx0 logic). Update `test_contrib_wiring.py`: replace the `engine._apply_contributors(...)` call in `test_separate_and_gate_is_a_subset_of_base` with `out = engine._l2_eligibility(l1, _es_on())` and `base = engine._l2_eligibility(l1, _P)`, asserting `(out <= base).all()` and `(~out).sum() > 0`. Run both contributor test files green.
- [ ] **Step 5: commit** — `feat(l2-engine): merged + or-boost topologies via _l2_eligibility; remove _apply_contributors`

---

### Task 3: Regression — L2 suite + golden
- [ ] **Step 1:** `python3 -m pytest optimize/l2/ -q` (all green).
- [ ] **Step 2:** `python3 perf/check_golden.py` → **6/6 MATCH**.
- [ ] **Step 3: commit** any test-only fixes — `test(l2): B2b regression green (suite + golden 6/6)`.

## Definition of done for B2b
All three topologies (`separate_and` | `merged` | `or_boost`) selectable via `contributor_topology`; no-enabled-contributor is byte-identical under each (162 baseline); golden 6/6. **Next:** B3 — `contributors`/`es_*` + `contributor_topology` + `k_es` namespaced search space in `suggest_l2_params`.
