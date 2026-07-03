# Intra-Candle Entry for Vetoed Signals — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a box signal that was **vetoed** (but passed the vol-gate) stay **armed** and enter **mid-candle** at the first 1-minute bar where the full gate re-opens (`¬veto ∧ #confirm ≥ K`) while flat — measured on the current champion across a wait-window sweep.

**Architecture:** Additive, flag-gated (default OFF ⇒ byte-identical champion). Reuse `engine.py`'s carry-mode arming loop, **inverting** the "live veto aborts" step into "arm the vetoed signal." A new pure helper in `indicators/runner.py` exposes the **per-1-minute-bar** gate (reusing the `cdir1/vdir1` directions `_vote_from_1min` already computes but currently discards after sampling at decision-bar closes). A new resolver walks the candle's 1-min bars and returns the first qualifying flat bar. A study harness runs the champion with the flag on across `N ∈ {30,60,120,240}`.

**Tech Stack:** Python, numpy, pandas, pytest. Exact engine = `engine.py`; indicator layer = `indicators/runner.py` + `indicators/base.py`; study path = `strategy.py`.

## Global Constraints

- **Default OFF ⇒ golden 6/6 byte-identical.** Gate: `python3 perf/check_golden.py` must print all 6 timeframes MATCH after every task. New params default to the no-op value.
- **Causal — no look-ahead.** The gate at 1-min bar `t` uses only indicator values on 1-min bars `≤ t`.
- **Off the production path.** No change to the fast optimizer engine (`optimize/fast_engine.py`) in Phase 1.
- **TDD, frequent commits.** One test cycle per task; commit at the end of each.
- **Scope = vetoed AND vol-passed signals only.** Direction preserved (box-native). One armed signal at a time.
- **Constants:** direction ints/labels from `indicators/base.py` — `CONFIRM, VETO, HOLD, BOTH`; box direction int is `+1` long / `-1` short (see `runner._vote_from_1min`).
- **Anchor:** NQ 4h champion ($142,203 / 214; also wsh6cold $153,321).

---

### Task 1: Add the flag + wait-window params to `BacktestParams`

**Files:**
- Modify: `engine.py` (the `BacktestParams` dataclass, currently ends at `eod_margin_min` ~line 97)
- Test: `optimize/test_intracandle_params.py` (create)

**Interfaces:**
- Produces: `BacktestParams.intracandle_veto_entry: bool = False`, `BacktestParams.intracandle_max_wait: int = 240`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_intracandle_params.py
from engine import BacktestParams

def test_intracandle_params_default_off():
    p = BacktestParams(sl_soft_points=1, sl_hard_points=2, tp_hard_points=3,
                       data_path_4h="x", data_path_1min="y", box_data_path="z")
    assert p.intracandle_veto_entry is False      # default OFF ⇒ parity
    assert p.intracandle_max_wait == 240          # one 4h candle of 1-min bars
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_intracandle_params.py -q`
Expected: FAIL — `AttributeError: 'BacktestParams' object has no attribute 'intracandle_veto_entry'`

- [ ] **Step 3: Add the fields** (append at the END of the dataclass so positional construction is unaffected)

```python
    # Intra-candle entry for vetoed signals (Phase 1). OFF ⇒ byte-identical (golden-locked).
    intracandle_veto_entry: bool = False   # arm a vetoed (vol-passed) signal, enter mid-candle when the gate re-opens
    intracandle_max_wait:   int  = 240     # max 1-min bars to wait inside the candle (N); 240 ≈ one 4h candle
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_intracandle_params.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add engine.py optimize/test_intracandle_params.py
git commit -m "feat(engine): add intracandle_veto_entry flag + max_wait param (default off)"
```

---

### Task 2: Per-1-minute-bar gate arrays in `runner.py`

**Files:**
- Modify: `indicators/runner.py` (add `intracandle_gate_arrays`; refactor `_vote_from_1min` to expose `cdir1/vdir1` via a small shared helper `_dirs_1min`)
- Test: `indicators/test_intracandle_gate.py` (create)

**Interfaces:**
- Produces: `runner.intracandle_gate_arrays(df_dec, df1, box, indicators, k, bar_td) -> dict` returning `{+1: bool[len(df1)], -1: bool[len(df1)]}` — `gate_open[d][t] = (no veto-capable ind vetoes dir d at 1-min bar t) AND (#confirm-capable inds confirming dir d at t ≥ k_eff)`, with `k_eff = min(k, #confirm-capable-enabled)`. Causal (each `t` uses only 1-min data ≤ t). Warm-up bars per indicator are forced non-voting (mirrors `_vote_from_1min`).

- [ ] **Step 1: Write the failing test** (causality + semantics on a tiny synthetic indicator set)

```python
# indicators/test_intracandle_gate.py
import numpy as np, pandas as pd
from indicators import runner
from optimize import counterfactual_pause as cp

def test_gate_arrays_shape_and_causal():
    C = cp.load_champion("4h")
    inds = C["ctx"].champ_indicators()          # enabled champion indicators (see note in Step 3)
    g = runner.intracandle_gate_arrays(C["d"], C["d1"], C["box"], inds, C["K"], C["bar_td"])
    n1 = len(C["d1"])
    assert set(g.keys()) == {+1, -1}
    assert g[+1].shape == (n1,) and g[+1].dtype == bool
    # causality: truncating the 1-min frame past bar m leaves gate[:m] unchanged
    m = n1 // 2
    Ct_d1 = C["d1"].iloc[:m].copy()
    g_tr = runner.intracandle_gate_arrays(C["d"], Ct_d1, C["box"], inds, C["K"], C["bar_td"])
    assert np.array_equal(g[+1][:m], g_tr[+1][:m])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest indicators/test_intracandle_gate.py -q`
Expected: FAIL — `AttributeError: module 'indicators.runner' has no attribute 'intracandle_gate_arrays'` (and/or `champ_indicators` missing — resolve per Step 3).

- [ ] **Step 3: Implement** — factor the direction computation out of `_vote_from_1min`, then aggregate per direction.

```python
# indicators/runner.py  (near _vote_from_1min)
def _dirs_1min(ind, ctx_1m):
    """(cdir1, vdir1) over ALL 1-min bars, warm-up forced to 0. Extracted from _vote_from_1min."""
    if getattr(ind, "_supports_signal_at", False):
        cdir1, vdir1 = ind.directions(ctx_1m)          # full series (no signal_at ⇒ every bar)
    else:
        cdir1, vdir1 = ind.directions(ctx_1m)
    cdir1 = np.asarray(cdir1).copy(); vdir1 = np.asarray(vdir1).copy()
    w = min(int(ind.warmup_bars()), len(cdir1))
    if w > 0:
        cdir1[:w] = 0; vdir1[:w] = 0
    return cdir1, vdir1

def intracandle_gate_arrays(df_dec, df1, box, indicators, k, bar_td):
    """Per-1-min-bar full-gate booleans per direction (+1 long / -1 short). Causal; reuses 1-min directions."""
    from .base import CONFIRM, VETO, HOLD, BOTH   # BOTH matches either direction
    ctx_1m = market_context(df1)
    n1 = len(df1)
    confirmers = [i for i in indicators if i.config.enabled and i.config.mode in ("confirm", "both")]
    vetoers    = [i for i in indicators if i.config.enabled and i.config.mode in ("veto", "both")]
    k_eff = min(int(k), len(confirmers))
    out = {}
    for d in (+1, -1):
        conf = np.zeros(n1, dtype=np.int64); veto = np.zeros(n1, dtype=bool)
        for ind in confirmers:
            c, _ = _dirs_1min(ind, ctx_1m)
            conf += ((c == d) | (c == BOTH)).astype(np.int64)
        for ind in vetoers:
            _, v = _dirs_1min(ind, ctx_1m)
            veto |= ((v == d) | (v == BOTH))
        out[d] = (~veto) & (conf >= k_eff) if k_eff > 0 else (~veto)
    return out
```

Also add a small accessor the test uses (or replace the test line to build indicators the same way `counterfactual_pause` does):

```python
# optimize/counterfactual_pause.py — expose the enabled champion indicators on the ctx bundle
# In load_champion(), after `inds = library.from_specs(...)`, add to the returned dict:  indicators=inds
```
Update the test's `inds = C["ctx"].champ_indicators()` to `inds = C["indicators"]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest indicators/test_intracandle_gate.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add indicators/runner.py indicators/test_intracandle_gate.py optimize/counterfactual_pause.py
git commit -m "feat(runner): per-1-min-bar full-gate arrays (causal, reuse 1-min directions)"
```

---

### Task 3: The intra-candle veto resolver (pure)

**Files:**
- Create: `indicators/intracandle.py`
- Test: `indicators/test_intracandle_resolver.py`

**Interfaces:**
- Consumes: `intracandle_gate_arrays` (Task 2).
- Produces: `intracandle.build_resolver(gate_by_dir, min_start, max_wait) -> resolver`, where
  `resolver(direction_int, start_e, sub_len, is_flat) -> (fill_offset:int, )| None`. `direction_int` ∈ {+1,-1};
  `start_e` = global 1-min index of the candle's first bar; `sub_len` = #1-min bars in the candle; `is_flat(offset)`
  returns whether the engine is flat at that bar. Returns the **first offset** `o < min(max_wait, sub_len)` where
  `gate_by_dir[direction_int][start_e + o]` is True **and** `is_flat(o)`; else `None`.

- [ ] **Step 1: Write the failing test**

```python
# indicators/test_intracandle_resolver.py
import numpy as np
from indicators.intracandle import build_resolver

def _gate(n, true_at, d=+1):
    a = np.zeros(n, dtype=bool); a[true_at] = True
    return {+1: a if d == +1 else np.zeros(n, bool), -1: a if d == -1 else np.zeros(n, bool)}

def test_enters_first_qualifying_flat_bar():
    g = _gate(100, [40], d=+1)                     # gate opens at global bar 40
    r = build_resolver(g, min_start=0, max_wait=240)
    # candle starts at global 10; gate opens at offset 30; flat everywhere
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: True) == (30,)

def test_waits_until_flat():
    g = _gate(100, [40, 45], d=+1)                 # gate open at offsets 30 and 35
    r = build_resolver(g, min_start=0, max_wait=240)
    # not flat until offset 33 ⇒ first flat gate-open bar is offset 35
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: o >= 33) == (35,)

def test_expires_past_max_wait():
    g = _gate(100, [40], d=+1)                     # gate open at offset 30
    r = build_resolver(g, min_start=0, max_wait=20) # N=20 < 30 ⇒ never reached
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: True) is None

def test_direction_isolated():
    g = _gate(100, [40], d=+1)                     # only LONG gate open
    r = build_resolver(g, min_start=0, max_wait=240)
    assert r(-1, start_e=10, sub_len=50, is_flat=lambda o: True) is None  # short never qualifies
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest indicators/test_intracandle_resolver.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'indicators.intracandle'`

- [ ] **Step 3: Implement**

```python
# indicators/intracandle.py
"""Phase-1 intra-candle veto-entry resolver. Pure: given per-1-min-bar gate arrays, find the first bar
inside the candle where the gate is open AND the engine is flat, within the wait window N. Causal by
construction (gate arrays are a forward series; we only read the current candle's bars)."""
from __future__ import annotations

def build_resolver(gate_by_dir, min_start, max_wait):
    def resolver(direction_int, start_e, sub_len, is_flat):
        gate = gate_by_dir[int(direction_int)]
        limit = min(int(max_wait), int(sub_len))
        for o in range(limit):
            g = start_e + o
            if g < min_start or g >= len(gate):
                continue
            if gate[g] and is_flat(o):
                return (o,)
        return None
    return resolver
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest indicators/test_intracandle_resolver.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add indicators/intracandle.py indicators/test_intracandle_resolver.py
git commit -m "feat(intracandle): pure resolver — first flat gate-open bar within N"
```

---

### Task 4: Wire the resolver into `engine.py` (arm vetoed signals; carry across the exit walk)

**Files:**
- Modify: `engine.py` — the `backtest` entry loop (arm block ~lines 444-473; the drop-at-`:460` inversion) and the exit-walk carry.
- Test: `optimize/test_intracandle_engine.py`

**Interfaces:**
- Consumes: `BacktestParams.intracandle_veto_entry`, `.intracandle_max_wait` (Task 1); `intracandle.build_resolver` (Task 3); `runner.intracandle_gate_arrays` (Task 2).
- Behaviour: when `params.intracandle_veto_entry` is **True**, a bar that would today be dropped as `veto` is instead **armed** (direction = box-native, D6); across the candle's 1-min bars the engine enters at the first bar where the gate is open (Task 2/3) **and** `open_trade is None` (D3); if a prior trade is open, the armed signal **persists across the exit walk** and retries once flat, within `N`. A new box signal (next candle) supersedes. **Flag False ⇒ the `:460` code path is unchanged.**

- [ ] **Step 1: Write the failing tests** (behavioural, on the champion)

```python
# optimize/test_intracandle_engine.py
import numpy as np
from optimize import counterfactual_pause as cp   # champion loader
import strategy                                    # exact-engine study path

def _run(intracandle, N=240):
    # strategy.run_champion_exact returns (trades, summary); added in Task 6's harness OR inline here.
    return strategy.run_champion_exact("4h", intracandle_veto_entry=intracandle, intracandle_max_wait=N)

def test_off_is_champion_parity():
    base, _ = _run(False)
    assert len(base) == 214            # champion trade count (NQ 4h)

def test_on_adds_entries():
    base, _ = _run(False)
    more, _ = _run(True, N=240)
    assert len(more) >= len(base)      # rescued vetoed signals can only ADD entries
    # every base trade still present (same entry_time set ⊆), extras are new
    base_keys = {t["entry_time"] for t in base}
    assert base_keys.issubset({t["entry_time"] for t in more})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest optimize/test_intracandle_engine.py -q`
Expected: FAIL — `AttributeError: module 'strategy' has no attribute 'run_champion_exact'` (added in Task 6) — so implement Task 6's harness entry first if executing strictly in order, OR stub `run_champion_exact` minimally here. (Note for executor: Tasks 4 and 6 share this harness; build the thin `run_champion_exact` wrapper as the first step of Task 4.)

- [ ] **Step 3: Implement — (a) build the gate + resolver once, (b) invert the arm, (c) carry across exits**

(a) In the engine setup (where `df_1min` arrays are pre-extracted, ~line 244), when `self.params.intracandle_veto_entry` and an `intracandle_gate_by_dir` was supplied, build the resolver:

```python
        self._ic_resolver = None
        if self.params.intracandle_veto_entry and intracandle_gate_by_dir is not None:
            from indicators.intracandle import build_resolver
            self._ic_resolver = build_resolver(intracandle_gate_by_dir, min_start=0,
                                               max_wait=self.params.intracandle_max_wait)
```

Add `intracandle_gate_by_dir=None` to the `backtest(...)` signature (after `signals=`), passed by `strategy.py` (Task 6).

(b) At the veto-drop point (`engine.py:460`, `if armed is not None and vetoed and not veto_as_flip: armed = None`), guard the abort so that under the flag a vetoed **vol-passed** directional signal ARMS instead:

```python
                    if armed is not None and vetoed and not veto_as_flip:
                        if self._ic_resolver is not None and in_scope and gated:
                            # INVERT: arm the vetoed signal for intra-candle re-entry (box-native dir)
                            armed = {'dir': signal, 'sidx': idx - 1,
                                     'sclose': float(d4_close[idx - 1]), 'vflip': False, 'ic': True}
                        else:
                            armed = None                  # original behaviour (flag off) — parity
```

(`gated` here is the vol-gate ∧ … pass; a vol-gated signal is not `gated`, so it never arms ⇒ enforces "vetoed AND vol-passed", D5.)

(c) Replace the fill for an `ic` armed signal to use the intra-candle resolver over the window, with `is_flat` = the engine being flat at that offset. Because the exit walk for a prior open trade runs in the same window, the armed dict must **survive** the exit walk (do not clear `armed` when an exit closes mid-window). Concretely, where the resolver is invoked (~line 465):

```python
                    if armed.get('ic'):
                        start_e = int(start_1m[idx])
                        sub_len = int(start_1m[idx + 1]) - start_e
                        hit = self._ic_resolver(+1 if armed['dir'] == 'long' else -1,
                                                start_e, sub_len,
                                                is_flat=lambda o: open_trade is None)  # flat at this bar
                        if hit is None:
                            continue                      # keep armed (or expire past N) → next bar
                        o = hit[0]
                        entry_ts = pd.Timestamp(df_1min['Date'].to_numpy()[start_e + o])
                        entry_px = float(df_1min['Close'].to_numpy()[start_e + o])
                        edir, sidx, vflip = armed['dir'], armed['sidx'], False
                        armed = None
                    else:
                        # ... existing non-ic resolver path unchanged ...
```

> **Executor note (the delicate D3 part):** the current loop clears `armed` on supersede and on veto-abort. Ensure an `ic` armed signal is (i) NOT cleared while a prior `open_trade` is still open within the same candle, and (ii) cleared when a NEW box signal fires (next candle) or `N` bars elapse. If the current single-pass-per-decision-bar structure can't express "retry within the same candle after a mid-candle exit," add a minimal inner retry: after an exit closes at 1-min offset `x`, re-invoke `self._ic_resolver` with a `min_offset=x+1` restriction. Add a focused test `test_waits_until_flat` mirroring Task 3 but end-to-end.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest optimize/test_intracandle_engine.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add engine.py optimize/test_intracandle_engine.py
git commit -m "feat(engine): arm vetoed signals for intra-candle entry (flag-gated, carry across exits)"
```

---

### Task 5: Golden parity gate (the hard guarantee)

**Files:** none (verification only).

- [ ] **Step 1: Run the golden gate** (flag defaults OFF everywhere)

Run: `python3 perf/check_golden.py`
Expected: `✅ ALL GOLDEN BASELINES MATCH` — all 6 TFs byte-identical (4h $142,203/214, 2h $91,996/262, 1h $99,172/315, 15m $77,098/654, 5m $23,926/332, 2m $29,777/276).

- [ ] **Step 2: If any mismatch — STOP and fix.** A mismatch means the flag-off path diverged; the arm inversion or gate build leaked into the default path. Re-check the `else: armed = None` guard (Task 4b).

- [ ] **Step 3: Commit** (no-op marker if clean)

```bash
git commit --allow-empty -m "test(golden): 6/6 byte-identical with intracandle flag off"
```

---

### Task 6: Study harness — champion N-sweep + metrics table

**Files:**
- Modify: `strategy.py` (add `run_champion_exact(tf, intracandle_veto_entry=False, intracandle_max_wait=240)` — thin wrapper over the existing `build_layer` → `engine.backtest` path, building `intracandle_gate_by_dir` via `runner.intracandle_gate_arrays` and passing it + the params).
- Create: `research/intracandle/run_sweep.py` (CLI), `research/intracandle/__init__.py`
- Test: `research/intracandle/test_sweep_smoke.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a metrics table per `N ∈ {30,60,120,240}`: `entries_total`, `entries_added`, `win_rate_added`, `payoff`, `total_pnl`, `median_hold_min`, `max_dd`, and the **breakeven check** (`win_rate_added > 0.575`).

- [ ] **Step 1: Write the failing smoke test**

```python
# research/intracandle/test_sweep_smoke.py
from research.intracandle.run_sweep import sweep

def test_sweep_returns_rows_for_each_N():
    rows = sweep("4h", Ns=(60,))
    r = rows[0]
    assert r["N"] == 60
    assert r["entries_added"] >= 0
    assert 0.0 <= r["win_rate_added"] <= 1.0
    assert "breakeven_ok" in r
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest research/intracandle/test_sweep_smoke.py -q`
Expected: FAIL — `ModuleNotFoundError: research.intracandle.run_sweep`

- [ ] **Step 3: Implement** `sweep()` — run the champion OFF once (baseline) then ON per N; diff the trade sets; compute metrics (reuse `research/kalman_fusion/metrics.py` `payoff_ratio`, `max_drawdown`).

```python
# research/intracandle/run_sweep.py
import numpy as np, pandas as pd
import strategy
from research.kalman_fusion.metrics import payoff_ratio, max_drawdown

def _metrics(trades, base_keys, pv=20.0):
    pnls = np.array([t["pnl_points"] * pv for t in trades], float)
    added = [t for t in trades if t["entry_time"] not in base_keys]
    ap = np.array([t["pnl_points"] * pv for t in added], float)
    holds = [ (pd.Timestamp(t["exit_time"]) - pd.Timestamp(t["entry_time"])).total_seconds()/60 for t in trades ]
    wr_added = float((ap > 0).mean()) if ap.size else 0.0
    return {"entries_total": len(trades), "entries_added": len(added),
            "win_rate_added": wr_added, "breakeven_ok": wr_added > 0.575,
            "payoff": payoff_ratio(pnls), "total_pnl": float(pnls.sum()),
            "median_hold_min": float(np.median(holds)) if holds else 0.0,
            "max_dd": max_drawdown(pnls)}

def sweep(tf="4h", Ns=(30,60,120,240)):
    base, _ = strategy.run_champion_exact(tf, intracandle_veto_entry=False)
    base_keys = {t["entry_time"] for t in base}
    rows = []
    for N in Ns:
        more, _ = strategy.run_champion_exact(tf, intracandle_veto_entry=True, intracandle_max_wait=N)
        m = _metrics(more, base_keys); m["N"] = N; rows.append(m)
    return rows

if __name__ == "__main__":
    import json
    for r in sweep():
        print(json.dumps(r))
```

- [ ] **Step 4: Run the smoke test + the real sweep**

Run: `python3 -m pytest research/intracandle/test_sweep_smoke.py -q` → PASS
Run: `python3 -m research.intracandle.run_sweep` → prints one JSON row per N.

- [ ] **Step 5: Commit**

```bash
git add strategy.py research/intracandle/
git commit -m "feat(intracandle): champion N-sweep study harness + metrics"
```

---

### Task 7: Dashboard toggle (D0 — checkbox under the time-cap control)

**Files:**
- Modify: `frontend/dashboard.html` (add a checkbox directly under the existing time-cap / `cap_mode` control), `server.py` (thread `intracandle_veto_entry` + `intracandle_max_wait` into the params it builds).
- Test: manual (UI) + `server.py` param round-trip if a test harness exists.

**Interfaces:**
- Consumes: `BacktestParams` fields (Task 1). Default OFF ⇒ dashboard reproduces the champion unchanged.

- [ ] **Step 1:** Locate the time-cap control in `frontend/dashboard.html` (`grep -n "cap_mode\|time.cap\|cap_1min" frontend/dashboard.html`) and add directly beneath it:

```html
<label title="Arm vetoed signals and enter mid-candle when the gate re-opens">
  <input type="checkbox" id="intracandle_veto_entry"> In-candle entry (vetoed)
  <input type="number" id="intracandle_max_wait" value="240" min="1" max="240" style="width:5em"> bars
</label>
```

- [ ] **Step 2:** In `server.py`, where `BacktestParams(...)` (or the params dict) is built for a run, read the two fields from the request payload (default `False` / `240`) and pass them through. `grep -n "cap_mode\|BacktestParams\|cap_1min" server.py` to find the site.

- [ ] **Step 3:** Verify round-trip — start the dashboard, load NQ 4h champion, confirm **checkbox OFF reproduces $142,203 / 214** exactly; toggling ON changes the entry count. (Restart `server.py` — backend change; see the dashboard-restart rule.)

- [ ] **Step 4: Commit**

```bash
git add frontend/dashboard.html server.py
git commit -m "feat(dashboard): in-candle vetoed-entry toggle under time-cap (default off)"
```

---

## Self-Review

**Spec coverage:** D0 → Task 1 (param) + Task 7 (checkbox). D1 → Task 2 (full-gate arrays). D2/D7 → Task 1 (N) + Task 6 (sweep). D3 → Task 4c (carry across exits, `is_flat`). D4 → Task 3/4 (immediate fill at qualifying bar close, no retrace). D5 → Task 4b (`gated` ⇒ vol-passed only). D6 → Task 4b (`dir=signal`, box-native). D8 → arm is single `armed` slot; supersede unchanged. D9 → Tasks 6 (champion study) gates Phase 2. Golden → Task 5. ✅ all covered.

**Placeholder scan:** none — every code/test step has concrete content. The one executor judgment call (D3 inner-retry) is flagged with a concrete fallback (`min_offset=x+1`).

**Type consistency:** `intracandle_gate_arrays` returns `{+1,-1}`→bool arrays (Task 2), consumed by `build_resolver(gate_by_dir, …)` (Task 3), invoked with `+1 if dir=='long' else -1` (Task 4). `run_champion_exact(tf, intracandle_veto_entry=, intracandle_max_wait=)` consistent across Tasks 4 & 6. ✅

## Verification (end-to-end)

1. `python3 perf/check_golden.py` → 6/6 MATCH (flag off).
2. `python3 -m pytest optimize/test_intracandle_params.py indicators/test_intracandle_gate.py indicators/test_intracandle_resolver.py optimize/test_intracandle_engine.py research/intracandle/test_sweep_smoke.py -q` → all pass.
3. `python3 -m research.intracandle.run_sweep` → metrics table; read off entries-added, win-rate-of-added vs 57.5% breakeven, and median hold-time per N.
4. Go/no-go to Phase 2 (optimizer/fast-engine) = added entries clear breakeven at held-or-better payoff on the champion.
