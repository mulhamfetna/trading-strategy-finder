# Multi-timeframe Layer Fusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the dashboard/backtester trade two timeframes of one instrument at once — a primary layer (e.g. 1h) with priority and a secondary layer (e.g. 4h) that enters on its own profile only while the primary is flat.

**Architecture:** The secondary, in the new `independent` L2 mode, is simply a full L1 run on its own timeframe. A new isolated fusion module (`optimize/l2/mtf.py`) merges the two layers' trade ledgers on a **master grid = the finer timeframe**, applying the existing primary-priority + force-close arbitration. Today's residual-manager L2 path is left byte-for-byte unchanged and stays the default, so the golden gate never moves.

**Tech Stack:** Python 3 (numpy, pandas, dataclasses), the existing `optimize/l2` engine, the stdlib `http.server` backend (`server.py`), vanilla-JS dashboard (`frontend/dashboard.html`), pytest, Playwright (Python).

## Global Constraints

- Same instrument for both layers — per-layer applies to **timeframe only** (spec §2 #1).
- **Single shared position, 1 contract**, owner-arbitrated; never two simultaneous open trades (spec §2 #5).
- **Primary preempts:** a primary entry strictly inside a secondary trade force-closes the secondary at that bar's close, reason `"L1-entry"`, P/L recomputed honestly (spec §3; reuse `engine.force_close_on_l1_entry`).
- Secondary fires on its **own full profile** gated to "primary flat" (spec §3 #3).
- **Additive:** `l2_mode` defaults to `"residual"` everywhere; omitting `l2_mode`/`l2_tf` is **byte-identical to today** (spec §6). `perf/check_golden.py` (6 TFs) must stay green.
- Master grid = the **finer** of the two timeframes; coarser layer aligned by epoch time (spec §4).
- Bad `l2_tf` (not in `l2payload._TF_SET`) ⇒ HTTP 400, like the existing instrument/tf validation (spec §6).
- Point value via `instruments.point_value(instrument)`; never hardcode 20/50.

## File Structure

- **Create** `optimize/l2/mtf.py` — fusion core. `LayerView` dataclass, `master_grid(primary, secondary)`, `run_dual_tf(primary, secondary, pv) -> DualResult`. One responsibility: merge two layers' ledgers on a master grid with primary priority. No I/O, no data loading — pure over its inputs (trivially unit-testable).
- **Modify** `optimize/l2/logbook.py` — `run_causal(...)` gains `l2_mode="residual", l2_tf=None`. When `independent`, run the secondary as its own L1, build `LayerView`s, call `mtf.run_dual_tf`, and emit the per-candle log on the master grid. Default path untouched.
- **Modify** `optimize/l2/payload.py` — `build_view_payload(..., l2_mode="residual", l2_tf=None)`; thread into `_run_causal_memo` (key includes `(l2_mode, l2_tf)`); the `l2` view in independent mode = the secondary's standalone run.
- **Modify** `server.py` — `/api/causal_backtest` reads + validates `l2_mode`/`l2_tf`, threads them in.
- **Modify** `frontend/dashboard.html` — L2 group gets a **Mode** selector + a conditionally-shown **L2 timeframe** dropdown; `run()` threads `l2_mode`/`l2_tf`.
- **Create** `optimize/l2/test_mtf.py` — fusion unit tests (synthetic `LayerView`s).
- **Create** `tests/e2e_dashboard_mtf.py` — Playwright for the new controls + a fused 1h+4h run.

## Interfaces (defined once, used across tasks)

```python
# optimize/l2/mtf.py
@dataclass
class LayerView:
    dates: np.ndarray   # df_dec["Date"].to_numpy() — decision-bar timestamps (datetime64), ascending
    close: np.ndarray   # df_dec["Close"].to_numpy(float)
    ledger: list        # taken trade dicts: entry_idx,int; entry_price,float; exit_time,datetime64;
                        #   exit_price,float; direction,'long'|'short'; exit_reason,str; pnl_points,float; pnl,float
    state: np.ndarray   # bool per decision bar, True = in-position (L1Result.state_timeline)
    bar_td: object      # pandas Timedelta — the bar duration (L1Result.bar_td)

@dataclass
class DualResult:
    master_dates: np.ndarray      # the finer layer's `dates`
    master_close: np.ndarray      # the finer layer's `close`
    ledger: list                  # combined trades, each = trade dict + "owner" in {"L1","L2"}, sorted by entry_idx (master grid)
    prim_state: np.ndarray        # primary in-position, on master grid (bool)
    sec_state: np.ndarray         # secondary (admitted) in-position, on master grid (bool)

def master_grid(primary: LayerView, secondary: LayerView) -> tuple[LayerView, LayerView]:
    """Return (finer, coarser) by bar_td (primary wins ties)."""

def run_dual_tf(primary: LayerView, secondary: LayerView, pv: float) -> DualResult: ...
```

---

### Task 1: Fusion module skeleton + master-grid selection

**Files:**
- Create: `optimize/l2/mtf.py`
- Test: `optimize/l2/test_mtf.py`

**Interfaces:**
- Produces: `LayerView`, `DualResult`, `master_grid(primary, secondary)` (signatures above).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_mtf.py
import numpy as np, pandas as pd
from optimize.l2 import mtf

def _lv(bar_minutes, n=4):
    dates = np.array([np.datetime64("2025-01-01T00:00") + np.timedelta64(bar_minutes*i, "m") for i in range(n)])
    return mtf.LayerView(dates=dates, close=np.arange(n, dtype=float),
                         ledger=[], state=np.zeros(n, bool), bar_td=pd.Timedelta(minutes=bar_minutes))

def test_master_grid_picks_finer_as_first():
    one_h, four_h = _lv(60), _lv(240)
    finer, coarser = mtf.master_grid(one_h, four_h)       # primary=1h, secondary=4h
    assert finer.bar_td == pd.Timedelta(minutes=60)
    assert coarser.bar_td == pd.Timedelta(minutes=240)

def test_master_grid_primary_wins_tie():
    a, b = _lv(60), _lv(60)
    finer, _ = mtf.master_grid(a, b)
    assert finer is a
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: FAIL (`ModuleNotFoundError: optimize.l2.mtf` / `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/mtf.py
"""Multi-timeframe layer fusion (spec docs/superpowers/specs/2026-06-30-multi-timeframe-layer-fusion-design.md).
The secondary layer is a full L1 run on its own timeframe; here we merge two layers' trade ledgers on a master
grid (the finer timeframe) under primary priority. Pure over its inputs — no data loading, no I/O."""
from dataclasses import dataclass
import numpy as np


@dataclass
class LayerView:
    dates: np.ndarray
    close: np.ndarray
    ledger: list
    state: np.ndarray
    bar_td: object


@dataclass
class DualResult:
    master_dates: np.ndarray
    master_close: np.ndarray
    ledger: list
    prim_state: np.ndarray
    sec_state: np.ndarray


def master_grid(primary: LayerView, secondary: LayerView):
    """(finer, coarser) by bar_td; primary wins ties (so its own grid is the master when equal)."""
    return (primary, secondary) if primary.bar_td <= secondary.bar_td else (secondary, primary)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/mtf.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): fusion module skeleton + master-grid selection"
```

---

### Task 2: Remap a layer's ledger onto the master grid

**Files:**
- Modify: `optimize/l2/mtf.py`
- Test: `optimize/l2/test_mtf.py`

**Interfaces:**
- Produces: `_remap_to_master(layer: LayerView, master: LayerView) -> list` — returns copies of `layer.ledger` trades with `entry_idx` re-pointed to the master bar whose timestamp matches the trade's entry timestamp (`layer.dates[entry_idx]`), found by `np.searchsorted(master.dates, ts, side="left")`. `exit_time`/`exit_price`/`pnl_points`/`pnl`/`direction` are carried unchanged.
- Produces: `_state_on_master(layer, master) -> np.ndarray` — boolean in-position projected onto master bars by epoch time (a master bar is in-position iff its timestamp falls in some trade's `[entry_ts, exit_time)`).

- [ ] **Step 1: Write the failing test**

```python
def test_remap_aligns_coarse_entry_to_master_bar():
    # master = 1h grid (4 bars @ 00:00,01:00,02:00,03:00); coarse trade entered at 02:00
    one_h = _lv(60)
    four_h = _lv(240)
    four_h.dates = np.array([np.datetime64("2025-01-01T02:00")])      # single coarse bar at 02:00
    four_h.close = np.array([10.0])
    four_h.ledger = [dict(entry_idx=0, entry_price=10.0, direction="long",
                          exit_time=np.datetime64("2025-01-01T03:00"), exit_price=12.0,
                          exit_reason="tp", pnl_points=2.0, pnl=40.0)]
    out = mtf._remap_to_master(four_h, one_h)
    assert out[0]["entry_idx"] == 2          # 02:00 is master bar index 2
    assert out[0]["pnl"] == 40.0             # carried unchanged

def test_state_on_master_marks_open_window():
    one_h = _lv(60)                                   # 00:00..03:00
    coarse = _lv(240); coarse.dates = np.array([np.datetime64("2025-01-01T01:00")])
    coarse.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                          exit_time=np.datetime64("2025-01-01T03:00"), exit_price=1.0,
                          exit_reason="tp", pnl_points=0.0, pnl=0.0)]
    st = mtf._state_on_master(coarse, one_h)
    assert list(st) == [False, True, True, False]     # open over [01:00, 03:00)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: FAIL (`AttributeError: module 'optimize.l2.mtf' has no attribute '_remap_to_master'`).

- [ ] **Step 3: Write minimal implementation**

```python
def _remap_to_master(layer: LayerView, master: LayerView) -> list:
    out = []
    for t in layer.ledger:
        ts = layer.dates[int(t["entry_idx"])]
        j = int(np.searchsorted(master.dates, ts, side="left"))
        j = min(j, len(master.dates) - 1)
        tt = dict(t); tt["entry_idx"] = j
        out.append(tt)
    return out


def _state_on_master(layer: LayerView, master: LayerView) -> np.ndarray:
    st = np.zeros(len(master.dates), dtype=bool)
    for t in layer.ledger:
        e_ts = layer.dates[int(t["entry_idx"])]
        x_ts = np.datetime64(t["exit_time"])
        lo = int(np.searchsorted(master.dates, e_ts, side="left"))
        hi = int(np.searchsorted(master.dates, x_ts, side="left"))
        hi = max(hi, lo + 1)                              # entry bar always occupied
        st[lo:hi] = True
    return st
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/mtf.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): remap a layer's ledger + in-position state onto the master grid"
```

---

### Task 3: `run_dual_tf` — primary-priority fusion with force-close

**Files:**
- Modify: `optimize/l2/mtf.py`
- Test: `optimize/l2/test_mtf.py`

**Interfaces:**
- Consumes: `_remap_to_master`, `_state_on_master`, `master_grid`, and `engine.force_close_on_l1_entry(cand, l1_entries, dec_dates, dec_close, pv)`.
- Produces: `run_dual_tf(primary, secondary, pv) -> DualResult` — primary trades kept verbatim (owner `"L1"`); secondary trades remapped to master, **dropped if the primary is in-position at the secondary entry bar**, otherwise **force-closed** at the first primary entry strictly inside the trade (reusing `engine.force_close_on_l1_entry`), `pnl` recomputed as `pnl_points * pv` for truncated trades; admitted secondary trades get owner `"L2"`. Combined ledger sorted by master `entry_idx`.

- [ ] **Step 1: Write the failing test**

```python
def test_dual_tf_secondary_fills_gap_then_primary_preempts():
    # master = 1h, 6 bars 00:00..05:00. Primary: one trade entering at 03:00.
    prim = _lv(60, n=6)
    prim.ledger = [dict(entry_idx=3, entry_price=3.0, direction="long",
                        exit_time=np.datetime64("2025-01-01T05:00"), exit_price=5.0,
                        exit_reason="tp", pnl_points=2.0, pnl=40.0)]
    prim.state = np.array([False, False, False, True, True, False])
    # Secondary (4h): one trade entering at 01:00, would exit 05:00 — but primary enters at 03:00.
    sec = _lv(240, n=2); sec.dates = np.array([np.datetime64("2025-01-01T01:00"),
                                               np.datetime64("2025-01-01T04:00")])
    sec.close = np.array([1.0, 4.0])
    sec.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                       exit_time=np.datetime64("2025-01-01T05:00"), exit_price=5.0,
                       exit_reason="tp", pnl_points=4.0, pnl=200.0)]
    sec.state = np.array([True, True])
    res = mtf.run_dual_tf(prim, sec, pv=50.0)
    owners = {t["owner"]: t for t in res.ledger}
    assert set(owners) == {"L1", "L2"}
    assert owners["L1"]["entry_idx"] == 3
    # secondary entered 01:00 (primary flat), force-closed at primary entry 03:00 (master close 3.0)
    l2 = owners["L2"]
    assert l2["entry_idx"] == 1
    assert l2["exit_reason"] == "L1-entry"
    assert l2["exit_price"] == 3.0
    assert l2["pnl"] == (3.0 - 1.0) * 50.0            # honest recompute: 100.0

def test_dual_tf_drops_secondary_when_primary_already_open():
    prim = _lv(60, n=4)
    prim.ledger = [dict(entry_idx=0, entry_price=0.0, direction="long",
                        exit_time=np.datetime64("2025-01-01T03:00"), exit_price=3.0,
                        exit_reason="tp", pnl_points=3.0, pnl=150.0)]
    prim.state = np.array([True, True, True, False])
    sec = _lv(240, n=1); sec.dates = np.array([np.datetime64("2025-01-01T01:00")])
    sec.close = np.array([1.0])
    sec.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                       exit_time=np.datetime64("2025-01-01T02:00"), exit_price=2.0,
                       exit_reason="tp", pnl_points=1.0, pnl=50.0)]
    sec.state = np.array([True])
    res = mtf.run_dual_tf(prim, sec, pv=50.0)
    assert [t["owner"] for t in res.ledger] == ["L1"]   # secondary dropped (primary open at 01:00)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: FAIL (`AttributeError: ... 'run_dual_tf'`).

- [ ] **Step 3: Write minimal implementation**

```python
from optimize.l2 import engine as _engine


def run_dual_tf(primary: LayerView, secondary: LayerView, pv: float) -> DualResult:
    finer, _ = master_grid(primary, secondary)
    master = finer
    prim_state = _state_on_master(primary, master)
    # primary trades, verbatim, on the master grid
    prim_trades = _remap_to_master(primary, master)
    for t in prim_trades:
        t["owner"] = "L1"
    # secondary candidates on the master grid: drop any whose entry bar has the primary in-position
    sec_cand = [t for t in _remap_to_master(secondary, master)
                if not prim_state[int(t["entry_idx"])]]
    # force-close each at the first primary entry strictly inside the trade (reuse the oracle helper)
    prim_entries = [int(t["entry_idx"]) for t in prim_trades]
    sec_fc = _engine.force_close_on_l1_entry(sec_cand, prim_entries, master.dates, master.close, pv)
    for t in sec_fc:
        t["owner"] = "L2"
        t["pnl"] = float(t["pnl_points"]) * pv          # honest recompute after any truncation
    ledger = sorted(prim_trades + sec_fc, key=lambda t: int(t["entry_idx"]))
    sec_view = LayerView(dates=master.dates, close=master.close, ledger=sec_fc,
                         state=np.zeros(len(master.dates), bool), bar_td=master.bar_td)
    sec_state = _state_on_master(sec_view, master)
    return DualResult(master_dates=master.dates, master_close=master.close, ledger=ledger,
                      prim_state=prim_state, sec_state=sec_state)
```

> Note: `force_close_on_l1_entry` truncates but does not set `pnl`; we recompute `pnl = pnl_points * pv` for every secondary trade (unchanged trades keep the same value, truncated ones get the honest figure). No cross-layer breaker is applied — each layer already applied its own in `run_l1_cached`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/mtf.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): run_dual_tf — primary-priority fusion with force-close + honest P/L"
```

---

### Task 4: `run_causal` independent mode → log on the master grid

**Files:**
- Modify: `optimize/l2/logbook.py:133` (`run_causal` signature + a branch)
- Test: `optimize/l2/test_mtf.py`

**Interfaces:**
- Consumes: `mtf.LayerView`, `mtf.run_dual_tf`, `payload.run_l1_cached`, `payload.validate_layer_params`, and the existing `LogRow`/`CausalResult`.
- Produces: `run_causal(l1_params, l2_params, tf, instrument, bar_mask=None, *, l2_mode="residual", l2_tf=None) -> CausalResult`. `l2_mode="residual"` ⇒ **exact current behavior** (signature-compatible; new kwargs are keyword-only and default to today's path). `l2_mode="independent"` ⇒ build the log from `mtf.run_dual_tf` on the master grid, with `position_owner` ∈ {L1,L2}.

- [ ] **Step 1: Write the failing test**

```python
def test_run_causal_independent_mode_combines_two_tfs():
    from optimize.l2 import logbook, payload
    l1p = payload.l1_default_params("1h")          # primary = 1h champion
    l2p = payload.l1_default_params("4h")          # secondary = 4h (a full profile)
    res = logbook.run_causal(l1p, l2p, tf="1h", instrument="NQ",
                             l2_mode="independent", l2_tf="4h")
    owners = {r.position_owner for r in res.log if r.decision == "entry"}
    assert owners <= {"L1", "L2"} and "L1" in owners
    # master grid = finer tf (1h) → n == number of 1h decision bars
    assert res.n == len(payload.run_l1_cached("1h", params=l1p, instrument="NQ").df_dec)
    # no master bar is owned by BOTH layers at once (single shared position)
    import numpy as np
    both = [r for r in res.log if r.decision == "entry"]
    idxs = [r.i for r in both]
    assert len(idxs) == len(set(idxs))             # one entry per master bar at most

def test_run_causal_residual_default_unchanged():
    from optimize.l2 import logbook, payload
    l1p, l2p = payload.l1_default_params("4h"), dict(payload.PERMISSIVE)
    a = logbook.run_causal(l1p, l2p, tf="4h", instrument="NQ")
    b = logbook.run_causal(l1p, l2p, tf="4h", instrument="NQ", l2_mode="residual")
    assert a.n == b.n and len(a.log) == len(b.log)
    assert [(r.layer, r.decision, r.pnl) for r in a.log] == [(r.layer, r.decision, r.pnl) for r in b.log]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -k run_causal -q`
Expected: FAIL (`TypeError: run_causal() got an unexpected keyword argument 'l2_mode'`).

- [ ] **Step 3: Write minimal implementation**

Change the `run_causal` signature (logbook.py:133) and add an early branch BEFORE the existing residual body:

```python
def run_causal(l1_params: dict, l2_params: dict, tf: str = "4h", instrument: str = "NQ",
               bar_mask=None, *, l2_mode: str = "residual", l2_tf: str | None = None) -> CausalResult:
    l1p = payload.validate_layer_params(l1_params)
    l2p = payload.validate_layer_params(l2_params)
    if l2_mode == "independent":
        return _run_causal_independent(l1p, l2p, tf, instrument, l2_tf or tf)
    # ----- existing residual path below, unchanged -----
    use_frozen = (instrument == "NQ" and tf == "4h" and l1p == payload.l1_default_params(tf))
    ...
```

Add the new builder (uses the same `LogRow` fields and per-layer equity write-back as the residual path):

```python
from optimize.l2 import mtf
from optimize import instruments as _instruments


def _layerview(l1result):
    return mtf.LayerView(dates=l1result.df_dec["Date"].to_numpy(),
                         close=l1result.df_dec["Close"].to_numpy(float),
                         ledger=l1result.ledger, state=np.asarray(l1result.state_timeline, bool),
                         bar_td=l1result.bar_td)


def _run_causal_independent(l1p, l2p, tf, instrument, l2_tf) -> CausalResult:
    pv = float(_instruments.point_value(instrument))
    prim = payload.run_l1_cached(tf, params=l1p, instrument=instrument)
    sec  = payload.run_l1_cached(l2_tf, params=l2p, instrument=instrument)
    dual = mtf.run_dual_tf(_layerview(prim), _layerview(sec), pv)
    dates, n = dual.master_dates, len(dual.master_dates)
    by_idx = {int(t["entry_idx"]): t for t in dual.ledger}
    log: list[LogRow] = []
    for i in range(n):
        ts = _epoch(dates[i]); t = by_idx.get(i)
        if t is not None:
            owner = t["owner"]
            log.append(LogRow(i=i, time=ts, layer=owner, decision="entry", reason="entered",
                              event_type="ENTRY", direction=t["direction"],
                              entry_price=float(t["entry_price"]), exit_time=_epoch(t["exit_time"]),
                              exit_price=float(t["exit_price"]), exit_reason=t["exit_reason"],
                              pnl=float(t["pnl"]), in_position=True, position_owner=owner,
                              text=_row_text(owner, "entry", "entered", t["direction"], None,
                                             t["exit_reason"], float(t["pnl"]))))
        else:
            inpos = bool(dual.prim_state[i] or dual.sec_state[i])
            owner = "L1" if dual.prim_state[i] else ("L2" if dual.sec_state[i] else None)
            reason = "open_trade" if inpos else "box_silence"
            log.append(LogRow(i=i, time=ts, layer=owner, decision="nonentry", reason=reason,
                              event_type="NOENTRY", in_position=inpos, position_owner=owner,
                              text=_row_text(owner, "nonentry", reason, None, None, None, 0.0)))
    for lyr in ("L1", "L2"):                                  # per-layer equity + underwater dd (same as residual path)
        rows = sorted([r for r in log if r.layer == lyr and r.decision == "entry"], key=lambda r: r.exit_time)
        eq = peak = 0.0
        for r in rows:
            eq += r.pnl; peak = max(peak, eq); r.equity = round(eq, 2); r.dd = round(peak - eq, 2)
    return CausalResult(tf=tf, l1_params=l1p, l2_params=l2p, log=log, n=n, dec_dates=dates,
                        warmup={"l1": _warmup_for(l1p), "l2": _warmup_for(l2p)},
                        counts={"l1": {"n_locks": int(prim.n_locks), "n_skipped": int(prim.n_skipped_breaker)},
                                "l2": {"n_locks": int(sec.n_locks), "n_skipped": int(sec.n_skipped_breaker)}})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Run the golden gate (residual path must be untouched)**

Run: `cd subprojects/Parametric-Indicators && python perf/check_golden.py`
Expected: all 6 TFs PASS (no change).

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/logbook.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): run_causal independent mode — fused log on the master grid (residual default unchanged)"
```

---

### Task 5: Thread `l2_mode`/`l2_tf` through `build_view_payload` + memo

**Files:**
- Modify: `optimize/l2/payload.py` (`build_view_payload` signature ~line 513; `_run_causal_memo` key)
- Test: `optimize/l2/test_mtf.py`

**Interfaces:**
- Consumes: `run_causal(..., l2_mode=, l2_tf=)`.
- Produces: `build_view_payload(l1_params, l2_params, tf="4h", view="combined", instrument="NQ", l1_engine=None, *, l2_mode="residual", l2_tf=None)`. Memo key includes `(l2_mode, l2_tf)`. In `independent` mode the `l2` view = the secondary's standalone run; `combined` = the fused result.

- [ ] **Step 1: Write the failing test**

```python
def test_build_view_payload_independent_combined_has_both_owners():
    from optimize.l2 import payload
    l1p, l2p = payload.l1_default_params("1h"), payload.l1_default_params("4h")
    out = payload.build_view_payload(l1p, l2p, tf="1h", view="combined", instrument="NQ",
                                     l2_mode="independent", l2_tf="4h")
    owners = {r.get("position_owner") for r in out["log"] if r.get("decision") == "entry"}
    assert "L1" in owners
    assert out["meta"]["n"] == len(out["log"])

def test_build_view_payload_default_is_residual():
    from optimize.l2 import payload
    l1p, l2p = payload.l1_default_params("4h"), dict(payload.PERMISSIVE)
    a = payload.build_view_payload(l1p, l2p, tf="4h", view="combined", instrument="NQ")
    b = payload.build_view_payload(l1p, l2p, tf="4h", view="combined", instrument="NQ", l2_mode="residual")
    assert a["meta"]["n"] == b["meta"]["n"] and len(a["log"]) == len(b["log"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -k build_view_payload -q`
Expected: FAIL (`TypeError: ... unexpected keyword argument 'l2_mode'`).

- [ ] **Step 3: Write minimal implementation**

In `payload.py`, update `_run_causal_memo` to key on mode/tf and forward them, and add the kwargs to `build_view_payload`, forwarding to `_run_causal_memo`. Example for the memo (adjust to the existing cache dict):

```python
def _run_causal_memo(l1p, l2p, tf, instrument, l2_mode="residual", l2_tf=None):
    key = (_hash_params(l1p), _hash_params(l2p), tf, instrument, l2_mode, l2_tf)
    hit = _CAUSAL_MEMO.get(key)
    if hit is None:
        hit = logbook.run_causal(l1p, l2p, tf, instrument, l2_mode=l2_mode, l2_tf=l2_tf)
        _CAUSAL_MEMO[key] = hit
    return hit
```

In `build_view_payload`, add `*, l2_mode="residual", l2_tf=None` to the signature and pass them into the `_run_causal_memo(l1p, l2p, tf, instrument, l2_mode, l2_tf)` call(s). For `view == "l2"` in independent mode, return the secondary's standalone payload by recursing with the secondary as the L1 of a residual run: `build_view_payload(l2_params, dict(PERMISSIVE), l2_tf, "l1", instrument, l1_engine=None)` (its own 4h strategy, for inspection).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): thread l2_mode/l2_tf through build_view_payload + memo; l2 view = secondary standalone"
```

---

### Task 6: Server API — accept + validate `l2_mode`/`l2_tf`

**Files:**
- Modify: `server.py` (`/api/causal_backtest` handler, ~line 252-263)
- Test: `optimize/l2/test_mtf.py` (call the handler logic via the existing test client pattern in `optimize/l2/test_l2_server.py`)

**Interfaces:**
- Consumes: `build_view_payload(..., l2_mode=, l2_tf=)`, `l2payload._TF_SET`.
- Produces: `/api/causal_backtest` reads `body["l2_mode"]` (default `"residual"`) and `body["l2_tf"]`; if `l2_mode=="independent"` and `l2_tf` not in `_TF_SET` ⇒ 400 `{"error": ...}`; else forwards both to `build_view_payload`.

- [ ] **Step 1: Write the failing test** (mirror `optimize/l2/test_l2_server.py`'s request helper)

```python
def test_api_causal_backtest_independent_mode(l2_client):     # reuse the fixture style in test_l2_server.py
    body = {"l1": __import__("optimize.l2.payload", fromlist=["x"]).l1_default_params("1h"),
            "l2": __import__("optimize.l2.payload", fromlist=["x"]).l1_default_params("4h"),
            "tf": "1h", "instrument": "NQ", "view": "combined",
            "l2_mode": "independent", "l2_tf": "4h"}
    status, out = l2_client("/api/causal_backtest", body)
    assert status == 200 and out["meta"]["n"] == len(out["log"])

def test_api_causal_backtest_bad_l2_tf_400(l2_client):
    body = {"l1": {}, "l2": {}, "tf": "1h", "view": "combined",
            "l2_mode": "independent", "l2_tf": "9q"}
    status, out = l2_client("/api/causal_backtest", body)
    assert status == 400 and "9q" in out["error"]
```

(If `test_l2_server.py` has no reusable client fixture, add a small `l2_client` fixture in `optimize/l2/test_mtf.py` that constructs the handler and posts JSON, copying the pattern already used there.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -k api_causal -q`
Expected: FAIL (400 not returned / `l2_mode` ignored).

- [ ] **Step 3: Write minimal implementation** (in the `/api/causal_backtest` branch)

```python
            l2_mode = body.get("l2_mode", "residual")
            l2_tf = body.get("l2_tf")
            if l2_mode == "independent" and l2_tf not in l2payload._TF_SET:
                return self._send(400, json.dumps({"error": f"unknown l2_tf {l2_tf!r}; known {list(l2payload._TF_SET)}"}))
            out = l2payload.build_view_payload(body.get("l1") or {}, body.get("l2") or {},
                                               body.get("tf", "4h"), body.get("view", "combined"),
                                               instrument=body.get("instrument", "NQ"),
                                               l2_mode=l2_mode, l2_tf=l2_tf)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2/test_mtf.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py optimize/l2/test_mtf.py
git commit -m "feat(mtf): /api/causal_backtest accepts l2_mode + l2_tf (bad l2_tf → 400)"
```

---

### Task 7: Dashboard — L2 Mode selector + L2-timeframe dropdown + run() threading

**Files:**
- Modify: `frontend/dashboard.html` (L2 settings group near line 103-107; `run()` near line 578-583)
- Test: `tests/e2e_dashboard_mtf.py`

**Interfaces:**
- Consumes: `/api/causal_backtest` with `l2_mode`/`l2_tf`.
- Produces: a `#l2_mode` select (`residual`|`independent`) and a `#l2_tf` select (the 6 TFs), the latter shown only when mode is `independent`; `run()` includes `l2_mode` + (when independent) `l2_tf` in the L2 + combined fetch bodies.

- [ ] **Step 1: Write the failing Playwright test**

```python
# tests/e2e_dashboard_mtf.py — follows tests/e2e_dashboard_instrument.py's server+browser harness
def test_mtf_mode_reveals_l2_tf_and_runs(page, base_url):
    page.goto(base_url)
    assert page.locator("#l2_mode").count() == 1
    assert not page.locator("#l2_tf").is_visible()             # hidden in residual (default)
    page.select_option("#l2_mode", "independent")
    assert page.locator("#l2_tf").is_visible()                 # revealed
    page.select_option("#tf_select", "1h")                     # primary = 1h
    page.select_option("#l2_tf", "4h")                         # secondary = 4h
    page.click("#run")
    page.wait_for_selector("text=done", timeout=120000)
    page.click("#tab_combined") if page.locator("#tab_combined").count() else None
    assert page.locator("#ledger tbody tr").count() > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python -m pytest tests/e2e_dashboard_mtf.py -q`
Expected: FAIL (`#l2_mode` not found).

- [ ] **Step 3: Write minimal implementation**

Add to the L2 settings group (after the L2 profile select, ~line 107):

```html
        <div class="fld"><label title="Residual = manage L1's dropped signals on the same frame. Independent timeframe = run L2 as its own strategy on its own timeframe, entering only when L1 is flat (primary-priority).">L2 mode</label>
          <select id="l2_mode"><option value="residual">Residual (same frame)</option><option value="independent">Independent timeframe</option></select></div>
        <div class="fld" id="l2_tf_fld" style="display:none"><label title="secondary timeframe (the 4h in a 1h+4h fusion)">L2 timeframe</label>
          <select id="l2_tf"><option>4h</option><option>2h</option><option>1h</option><option>15m</option><option>5m</option><option>2m</option></select></div>
```

Add a toggle listener (near the other selector listeners):

```javascript
$('l2_mode').addEventListener('change', ()=>{ $('l2_tf_fld').style.display = $('l2_mode').value==='independent' ? '' : 'none'; });
```

In `run()`, compute the mode and add to the L2 + combined bodies (leave the L1 fetch as-is):

```javascript
    const l2mode=$('l2_mode').value, l2tf=$('l2_tf').value;
    const ext = l2mode==='independent' ? {l2_mode:l2mode, l2_tf:l2tf} : {};
    DB.status('running L2 (2/3)…');
    const l2   = await grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, instrument:inst, view:'l2', ...ext})));
    DB.status('running combined (3/3)…');
    const comb = await grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, instrument:inst, view:'combined', ...ext})));
```

- [ ] **Step 4: Verify the inline JS still parses**

Run: extract inline `<script>` and `node --check` it (the snippet used earlier in this session). Expected: OK.

- [ ] **Step 5: Run the Playwright test to verify it passes**

Run: `cd subprojects/Parametric-Indicators && python -m pytest tests/e2e_dashboard_mtf.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/dashboard.html tests/e2e_dashboard_mtf.py
git commit -m "feat(mtf): dashboard L2 mode selector + L2-timeframe dropdown; run() threads l2_mode/l2_tf"
```

---

### Task 8: Full regression + docs touch-up

**Files:**
- Modify: `docs/INSTRUMENT_WORKSTREAM_MEGADOC.md` (note the new MTF capability) or add a short `docs/MTF_LAYER_FUSION.md`.

- [ ] **Step 1: Run the full L2 + golden suite**

Run: `cd subprojects/Parametric-Indicators && python -m pytest optimize/l2 -q && python perf/check_golden.py`
Expected: all green; golden 6/6 unchanged.

- [ ] **Step 2: Write a short capability doc** (`docs/MTF_LAYER_FUSION.md`) — 1 Mermaid diagram of the fusion + the API/UI surface + the "default=residual, golden-safe" note. (Mirror the embedded-Mermaid convention used in the other docs.)

- [ ] **Step 3: Commit**

```bash
git add docs/MTF_LAYER_FUSION.md docs/INSTRUMENT_WORKSTREAM_MEGADOC.md
git commit -m "docs(mtf): document the multi-timeframe layer-fusion capability"
```

---

## Self-Review

**1. Spec coverage:**
- §2 #1 same-stock/per-tf → Task 4/5/7 use one `instrument`, separate `l2_tf`. ✓
- §2 #2 primary preempts → Task 3 reuses `force_close_on_l1_entry`. ✓
- §2 #3 secondary own profile → Task 4 runs secondary as full `run_l1_cached`. ✓
- §2 #4 additive, default residual → Tasks 4/5/6 default `l2_mode="residual"`; golden run in Tasks 4 & 8. ✓
- §2 #5 single position → Task 3 drops secondary when primary open + force-close; Task 4 test asserts ≤1 entry/bar. ✓
- §4 master grid finer tf → Task 1 `master_grid`; Tasks 2-4 build on it. ✓
- §6 API + 400 → Task 6. ✓
- §7 UI → Task 7. ✓
- §9 tests → Tasks 1-7 each TDD; golden in 4 & 8; Playwright in 7. ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases"; every code step has real code. The only soft spot is Task 6's fixture ("if no reusable client fixture, add one copying the pattern") — acceptable because it points at a concrete existing file (`test_l2_server.py`) to copy.

**3. Type consistency:** `LayerView`/`DualResult` fields are used identically across Tasks 1-4; `run_dual_tf(primary, secondary, pv)`, `run_causal(..., l2_mode=, l2_tf=)`, `build_view_payload(..., l2_mode=, l2_tf=)` signatures match between definition and call sites; `owner` ∈ {"L1","L2"} consistent; `position_owner` reused from the existing `LogRow`.
