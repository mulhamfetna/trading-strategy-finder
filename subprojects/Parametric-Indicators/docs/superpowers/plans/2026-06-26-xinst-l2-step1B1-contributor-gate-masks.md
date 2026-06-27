# Cross-Instrument L2 — Step 1·Part B1: Contributor Gate-Mask Producer (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add `optimize/l2/contributors/gate.py` exposing `contributor_gate_masks(cfg, l1) -> (veto: bool[n], confirm_count: int64[n])` — the single per-contributor producer Part B2 will AND/pool into `engine.l2_gate_components`. Still UNWIRED from the engine.

**Architecture:** Pure new file + tests, reusing Part A (`registry/loader/align/state/votes`) and NQ's 1-min machinery (`runner.indicator_source_1min`/`_vote_from_1min`) by import. The committee runs 1-min-sourced (I2 seam) so it matches NQ resolution; signal + committee channels combine into one entry-bar-aligned `(veto, confirm_count)`. A disabled/absent contributor is a pure no-op via identity fills (T3) + a `NO_CONFIRM_CONSTRAINT` sentinel.

**Tech Stack:** Python 3, numpy, pandas, pytest. Reuse existing machinery by import; no new deps.

## Global Constraints
- **Contributors-OFF ⇒ byte-identical ⇒ golden 6/6.** This plan touches NO engine file (`engine.py`/`l1_runner.py`/`runner.py`/`payload.py`/`indicators/*`); it adds only `optimize/l2/contributors/gate.py` + its test. Golden is trivially unaffected.
- **Causal / no look-ahead.** The 1-min seam composes `align.align_decbars` (last-closed, searchsorted side=right−1) with `runner._decbar_1min_index` (last 1-min candle in-window). A disabled contributor and an absent bar must never inject a constraint.
- **Identity (T3):** a CONFIRM source missing ⇒ does not block (sentinel/`+0`); a VETO source missing ⇒ does not veto (`False`). `confirm_count` with ZERO confirm sources ⇒ all-`NO_CONFIRM_CONSTRAINT` (mirrors runner `K_eff=0 ⇒ all-True`).
- **M1:** committee specs are one-enabled-per-key; assert it.
- Reuse NQ machinery by import, never copy.

### cfg schema (one contributor; forward-compatible with B3 search space)
```python
cfg = {
  "token": "ES", "enabled": True, "tf": "4h",
  "state_def": "touch",            # "touch" | "traversal"
  "k_es": 1,                        # carried for B2 (gate topology); unused in B1
  "signal": {"encoding": "none",   # "none" | "stance" | "truthtable"
             "mode": "both",        # stance only: "confirm"|"veto"|"both"
             "table": {}},          # truthtable only: {(nq_dir,es_state): "confirm"|"veto"|"ignore"}
  "committee": [ {"key": "ema_trend", "enabled": True, "mode": "confirm", "params": {...}}, ... ],
}
```
Truth-table keys are `(nq_dir, es_state)` string tuples per `votes._DIR_STR`/`_ST_STR` (e.g. `("long","short")`).

**Confirmed interfaces (read from source 2026-06-26):**
- `votes.committee_veto_mask(votes_d, inds, n) -> bool[n]` (SHIFTED, idx0=False); `votes.committee_confirm_count(votes_d, inds, n) -> int64[n]` (UNSHIFTED); `votes.signal_stance(nq_box_dir, nq_es_state, mode) -> (cvote:bool[n], veto:bool[n])` (SHIFTED); `votes.signal_truthtable(nq_box_dir, nq_es_state, table) -> (cvote, veto)` (SHIFTED).
- `align.align_decbars(nq_dates, es_dates, bar_td) -> int64[n]`; `align.gather_to_nq(es_series, j, fill=0)`.
- `state.touch_state(df_dec, delivery)`; `state.traversal_state(df_dec, box_csv, tick_threshold)`.
- `loader.load_contributor_inputs(token, tf) -> ContributorInputs(df_dec, df1, box, delivery, tick_threshold, ...)`; `registry.get_contributor(token) -> Contributor(.box_csv, .tick_threshold)`.
- `runner.indicator_source_1min(df_dec, df1, bar_td) -> (ctx_1m, j_idx)`; `runner._vote_from_1min(ind, ctx_1m, j_idx, box_dir) -> int8[len(j_idx)]` (j<0 ⇒ neutral); `library.from_specs(specs) -> [Indicator]` (each `.key`, `.config.enabled`, `.config.mode`).
- `l1` exposes `df_dec, df1, box, vf, n_split, bar_td, sig_int` (`sig_int` = NQ box dir int8 = `nq_box_dir`).

**Files:** Create `optimize/l2/contributors/gate.py`; Test `optimize/l2/contributors/test_contrib_gate.py`.

---

### Task 1: Skeleton — sentinel, key-uniqueness, disabled no-op

**Interfaces:**
- Produces: `NO_CONFIRM_CONSTRAINT: np.int64`; `contributor_gate_masks(cfg: dict, l1) -> (np.ndarray[bool], np.ndarray[int64])`; `_assert_unique_keys(specs) -> None`.

- [ ] **Step 1: failing test** — `optimize/l2/contributors/test_contrib_gate.py`
```python
import sys
from pathlib import Path
from types import SimpleNamespace
_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import numpy as np
import pandas as pd
import pytest
from optimize.l2.contributors import gate


def _fake_l1(n=5):
    dates = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    return SimpleNamespace(df_dec=pd.DataFrame({"Date": dates}),
                           df1=pd.DataFrame({"Date": dates}),
                           bar_td=pd.Timedelta("4h"),
                           sig_int=np.array([1, -1, 0, 1, -1], dtype=np.int8)[:n])


def test_disabled_contributor_is_noop():
    l1 = _fake_l1()
    veto, cc = gate.contributor_gate_masks({"token": "ES", "enabled": False}, l1)
    assert veto.dtype == bool and not veto.any()
    assert cc.dtype == np.int64 and (cc == gate.NO_CONFIRM_CONSTRAINT).all()
    assert len(veto) == len(cc) == 5


def test_assert_unique_keys_raises_on_dup():
    with pytest.raises(ValueError, match="duplicate"):
        gate._assert_unique_keys([{"key": "macd", "enabled": True},
                                  {"key": "macd", "enabled": True}])
    gate._assert_unique_keys([{"key": "macd", "enabled": True},
                              {"key": "cci", "enabled": True}])  # no raise
```
- [ ] **Step 2: run, expect fail** — `python3 -m pytest optimize/l2/contributors/test_contrib_gate.py -q` → ImportError/fail.
- [ ] **Step 3: implement** — `optimize/l2/contributors/gate.py`
```python
"""Part B1 — unified per-contributor gate-mask producer. Given a contributor cfg + the L1 run, emit
(veto, confirm_count) aligned to NQ decision bars: the single producer Part B2 ANDs/pools into
engine.l2_gate_components. UNWIRED from the engine (no engine import) ⇒ golden trivially 6/6. The
committee is 1-min-sourced (matches NQ resolution, I2); identity fills make a disabled/absent
contributor a pure no-op (T3); committee keys are one-enabled-per-key (M1)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from indicators import library, runner                               # noqa: E402
from optimize.l2.contributors import align, loader, registry, state, votes  # noqa: E402

# A confirm_count so large any K passes ⇒ B2 reads it as "no confirm constraint" (mirrors runner
# K_eff=0 ⇒ all-True identity). Never reached by a real count (max ≈ 18 committee + 1 signal).
NO_CONFIRM_CONSTRAINT = np.int64(1 << 30)


def _assert_unique_keys(specs) -> None:
    keys = [s["key"] for s in specs if s.get("enabled")]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate enabled committee keys: {sorted(keys)}")


def contributor_gate_masks(cfg: dict, l1):
    """(veto: bool[n], confirm_count: int64[n]), n=len(l1.df_dec). Disabled ⇒
    (all-False, all-NO_CONFIRM_CONSTRAINT) = pure no-op."""
    n = len(l1.df_dec)
    if not cfg.get("enabled"):
        return np.zeros(n, dtype=bool), np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    raise NotImplementedError  # Task 2/3 fill the enabled path
```
- [ ] **Step 4: run, expect pass** — same pytest cmd → 2 passed.
- [ ] **Step 5: commit** — `git add optimize/l2/contributors/gate.py optimize/l2/contributors/test_contrib_gate.py && git commit -m "feat(l2-contrib/gate): B1 skeleton — sentinel, key-uniqueness, disabled no-op"`

---

### Task 2: Committee channel (1-min seam, I2) + look-ahead guard

**Interfaces:**
- Consumes: Task 1 skeleton; `runner.indicator_source_1min`/`_vote_from_1min`; `align.align_decbars`/`gather_to_nq`; `votes.committee_veto_mask`/`committee_confirm_count`; `library.from_specs`.
- Produces: the enabled-path committee branch inside `contributor_gate_masks` (and a private `_committee_masks(cfg, l1, es, j_dec, nq_box_dir, n) -> (veto, cc_entry, n_confirmers)`).

- [ ] **Step 1: failing test** — append to `test_contrib_gate.py`. Builds a tiny synthetic ES via monkeypatching `loader.load_contributor_inputs`, one always-long indicator, asserts the committee confirms only NQ-long bars and is entry-shifted; plus a look-ahead guard (shifting ES 1-min tail later must not change earlier NQ-bar masks).
```python
def _synth_es(n=6):
    d = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    df_dec = pd.DataFrame({"Date": d, "Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5})
    df1 = df_dec.copy()
    return SimpleNamespace(df_dec=df_dec, df1=df1, box=None, delivery=None, tick_threshold=0.75)


def test_committee_confirm_is_entry_shifted_and_oriented(monkeypatch):
    from optimize.l2.contributors import loader as _loader
    es = _synth_es()
    monkeypatch.setattr(_loader, "load_contributor_inputs", lambda token, tf="4h": es)
    l1 = _fake_l1(6)
    # one enabled ema_trend confirm indicator
    cfg = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch",
           "signal": {"encoding": "none"},
           "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                          "params": {"fast": 1, "slow": 2}}]}
    veto, cc = gate.contributor_gate_masks(cfg, l1)
    assert len(veto) == len(cc) == 6
    assert cc.dtype == np.int64 and veto.dtype == bool
    assert cc[0] in (0, gate.NO_CONFIRM_CONSTRAINT)   # idx0 entry-shift identity / no future leak
    assert (cc < gate.NO_CONFIRM_CONSTRAINT).any()    # at least one real confirm source ⇒ real counts
```
(The exact per-bar confirm pattern is computed from the engine machinery — assert structure + the look-ahead guard rather than guessing values; refine the asserted values against the first run.)
- [ ] **Step 2: run, expect fail** (NotImplementedError).
- [ ] **Step 3: implement** — replace the `raise NotImplementedError` and add the committee branch:
```python
    token = cfg["token"]; tf = cfg.get("tf", "4h")
    es = loader.load_contributor_inputs(token, tf)
    bar_td = l1.bar_td
    nq_box_dir = np.asarray(l1.sig_int, dtype=np.int8)
    j_dec = align.align_decbars(l1.df_dec["Date"].to_numpy(),
                                es.df_dec["Date"].to_numpy(), bar_td)   # NQ-decbar -> ES-decbar idx

    com_veto, com_cc_entry, n_confirmers = _committee_masks(cfg, l1, es, j_dec, nq_box_dir, n, bar_td)

    veto = com_veto
    if n_confirmers == 0:
        confirm_count = np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    else:
        confirm_count = com_cc_entry
    return veto, confirm_count


def _committee_masks(cfg, l1, es, j_dec, nq_box_dir, n, bar_td):
    com_specs = [s for s in cfg.get("committee", []) if s.get("enabled")]
    _assert_unique_keys(com_specs)
    if not com_specs:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=np.int64), 0
    inds = library.from_specs(com_specs)
    es_ctx1, j_es1 = runner.indicator_source_1min(es.df_dec, es.df1, bar_td)
    j_nq = align.gather_to_nq(j_es1, j_dec, fill=-1)        # NQ-decbar -> ES-1min idx (causal)
    votes_d = {ind.key: runner._vote_from_1min(ind, es_ctx1, j_nq, nq_box_dir) for ind in inds}
    com_veto = votes.committee_veto_mask(votes_d, inds, n)          # already entry-shifted
    cc_raw = votes.committee_confirm_count(votes_d, inds, n)        # UNshifted
    cc_entry = np.zeros(n, dtype=np.int64); cc_entry[1:] = cc_raw[:-1]   # shift to entry bar
    n_confirmers = len([i for i in inds if i.config.enabled and i.config.mode in ("confirm", "both")])
    return com_veto, cc_entry, n_confirmers
```
- [ ] **Step 4: run, expect pass.** Refine the test's asserted values to the first run's structure (keep the look-ahead guard strict).
- [ ] **Step 5: commit** — `feat(l2-contrib/gate): committee channel via 1-min seam + entry-shift + look-ahead guard`

---

### Task 3: Signal channel + combine (both encodings)

**Interfaces:**
- Consumes: Task 2; `state.touch_state`/`traversal_state`; `registry.get_contributor`; `votes.signal_stance`/`signal_truthtable`.
- Produces: `_signal_masks(cfg, es, j_dec, nq_box_dir, n) -> (cvote, veto, has_confirm)` and the full combine in `contributor_gate_masks`.

- [ ] **Step 1: failing test** — a cfg with a stance signal voter (mode="both") on a synthetic ES state asserts: veto channel ORs committee+signal; confirm_count adds the signal confirm; a truthtable cfg with one "confirm" cell produces a real confirm source; a cfg with NO confirm sources (signal mode="veto", committee all-veto) ⇒ confirm_count all-sentinel.
- [ ] **Step 2: run, expect fail.**
- [ ] **Step 3: implement** — add the signal branch + combine:
```python
    sig_cvote, sig_veto, sig_has_confirm = _signal_masks(cfg, es, j_dec, nq_box_dir, n)
    veto = com_veto | sig_veto
    n_confirm_sources = n_confirmers + (1 if sig_has_confirm else 0)
    if n_confirm_sources == 0:
        confirm_count = np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    else:
        confirm_count = com_cc_entry + sig_cvote.astype(np.int64)
    return veto, confirm_count


def _signal_masks(cfg, es, j_dec, nq_box_dir, n):
    enc = cfg.get("signal", {}).get("encoding", "none")
    if enc == "none":
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), False
    sd = cfg.get("state_def", "touch")
    if sd == "touch":
        es_state = state.touch_state(es.df_dec, es.delivery)
    else:
        c = registry.get_contributor(cfg["token"])
        es_state = state.traversal_state(es.df_dec, c.box_csv, c.tick_threshold)
    nq_es_state = align.gather_to_nq(es_state, j_dec, fill=0)        # NQ-decbar -> ES state (hold fill)
    sig = cfg["signal"]
    if enc == "stance":
        mode = sig["mode"]
        cvote, veto = votes.signal_stance(nq_box_dir, nq_es_state, mode)
        return cvote, veto, mode in ("confirm", "both")
    if enc == "truthtable":
        table = {tuple(k) if isinstance(k, list) else k: v for k, v in sig["table"].items()}
        cvote, veto = votes.signal_truthtable(nq_box_dir, nq_es_state, table)
        return cvote, veto, any(v == "confirm" for v in table.values())
    raise ValueError(f"invalid signal encoding {enc!r}")
```
- [ ] **Step 4: run, expect pass** (refine asserted values to first run).
- [ ] **Step 5: commit** — `feat(l2-contrib/gate): signal channel (stance+truthtable) + veto/confirm combine`

---

### Task 4: Real-ES integration smoke + golden-safety

- [ ] **Step 1: failing test** — load the real frozen NQ L1 (`payload.run_l1_cached("4h")`) as `l1`, run a cfg enabling the ES committee (a couple of real indicators) + a stance signal; assert shapes (`len == len(l1.df_dec)`), dtypes, that veto is bool / confirm_count int64, that `confirm_count.min() >= 0`, and that a fully-disabled cfg still returns the sentinel no-op. Also assert `gate` does NOT import `engine` (golden-safety): `assert "optimize.l2.engine" not in sys.modules` is too strong; instead `import inspect; assert "engine" not in inspect.getsource(gate)` for the engine module.
- [ ] **Step 2: run, expect fail** (until the real-data wiring is exercised).
- [ ] **Step 3: implement** — no new product code expected; fix any real-data edge surfaced (e.g. ES delivery/box path resolution under the frozen l1). 
- [ ] **Step 4: run full suite** — `python3 -m pytest optimize/l2/contributors/ -q` (all green) and confirm golden still 6/6 (`python3 perf/check_golden.py`) — must be unchanged since no engine file was touched.
- [ ] **Step 5: commit** — `test(l2-contrib/gate): real-ES smoke + golden-safety; B1 done`

---

## Definition of done for B1
`contributor_gate_masks(cfg, l1)` returns entry-bar-aligned `(veto: bool[n], confirm_count: int64[n])` for ES: 1-min-sourced committee + both signal encodings, causal (look-ahead-guarded), identity-when-disabled (sentinel), keys unique. Full `contributors/` suite green; golden 6/6 unchanged. **Next:** B2 wires `(veto, confirm_count)` into `engine.l2_gate_components` with the optimizer-chosen topology (MERGED | SEPARATE-AND with `k_es` | OR-confirm-boost) — where contributors-OFF ⇒ golden 6/6 becomes a LIVE test; then B3 adds the `es_*` namespaced search space to `suggest_l2_params`.
