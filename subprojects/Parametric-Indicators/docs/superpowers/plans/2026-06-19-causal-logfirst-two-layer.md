# Causal, Log-First Two-Layer System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the two-layer backtest so a single causal pass over candles produces ONE complete per-candle log (the single source of truth), and every dashboard box, chart and CSV is derived from that log — for the L1-only view, the L2-only view, and a combined view whose boxes show max(L1,L2)+layer-tag and whose charts gray (not hide) the opposite layer.

**Architecture:** A causal engine streams decision candles in time order. At each candle L1 decides first; if L1 is a non-entry **and the (single, shared) account is flat**, L2 re-evaluates the same candle with its own settings. One position at a time, L1 priority (an L1 entry force-closes an open L2 trade). Each candle emits a `LogRow` with: decision, owning layer, reason, full indicator status, and running financials. A pure aggregator computes every box from the log; payload builders serialize per-view chart data from the log. The legacy two-pass path (`l1_runner`/`engine`/`metrics`) stays until the new path is proven byte-for-byte equal to it.

**Tech Stack:** Python stdlib + numpy + pandas (engine/aggregator), `optimize.fast_engine.fast_backtest` (unchanged sub-bar exit math), stdlib `http.server` (`server.py`), vanilla JS + lightweight-charts 4.1.3 + `frontend/dashboard_common.js` (dashboards).

## Global Constraints

- **Single shared account.** One open position at a time. L2 opens only when the account is flat AND L1 returned a non-entry on that candle; an L1 entry force-closes an open L2 trade (L1 priority). L2 never acts on `open_trade` non-entries.
- **Logs are the single source of truth.** Every box/streak/total/PnL/DD shown anywhere is computed by aggregating the per-candle log — never from a parallel metric path.
- **Causality (no look-ahead).** Decisions at candle *i* use only information available at/before *i*. The vol-gate threshold uses only the in-sample reference segment percentile; indicators are causal; trade exits resolve forward on 1-min bars (that is the trade playing out, not look-ahead).
- **Additive only.** Never remove an existing box, log field, event type, chart, or CSV column without explicit permission, a verbose description, and a before/after sample. The new log MUST be a superset of today's event fields (`ENTRY/WIN/LOSS/LOCK/UNLOCK/SKIP/NOENTRY{reason}/WARMUP/WARMED`, plus `indicators[]`, prices, P/L, equity, DD).
- **Combined boxes — each box has its OWN combination rule (NOT uniform max).** Computed from the log:
  - **P/L** → sum (L1 + L2).
  - **max drawdown** → RECOMPUTED from the merged L1+L2 equity curve (NOT summed — the true combined DD is smaller than L1 DD + L2 DD because the layers rarely bottom out on the same bar).
  - **win rate** and **profit factor** → RECOMPUTED from the combined trade set (percentages/ratios can't be summed or maxed).
  - **streak boxes** (no-entry streak, box-silence, position-hold, gate non-entry, indicator non-entry) → max(L1,L2), tagged with the producing layer.
  - **trades** → sum (L1 and L2 trades are disjoint by single-account construction — no overlap). **breaker locks** → sum.
  - **warmup period** → max (tagged). **indicator requirement** → max (tagged).
  - **totals group (cumulative candle counts)** → NOT shown in combined (deferred — double-counting edge cases); stays ONLY in the individual L1/L2 views.
  - Layer tag appears only on the **max-type** boxes (streaks, warmup, indicator requirement); sum/recomputed boxes carry no single-layer tag.
- **Graph view semantics.** Separated L1 view: show L1 entries/positions, flat elsewhere, L2 not drawn. Separated L2 view: mirror. Combined view: both drawn, flat only where BOTH idle; the toggle grays (de-emphasizes) the opposite layer, never hides it.
- **Parity anchor.** The frozen lean champion must still reproduce L1 P/L **$149,989 / 255 trades / max-DD $15,491**; the promoted extend L2 champion must reproduce L2 **$78,391 / 80 / $8,961**. `perf/check_golden.py` must stay **6/6**.
- **Run/verify locally** (per project decision); the AMD server is only for the parallel optimizer.

---

## File Structure

| File | Responsibility |
|---|---|
| `optimize/l2/AUDIT_causality.md` (create) | Written evidence of the look-ahead/timing audit (Phase A). |
| `optimize/l2/test_causality.py` (create) | Automated guards: gate threshold uses only reference segment; shifting future bars never changes a past decision. |
| `optimize/l2/logbook.py` (create) | `LogRow` dataclass + `run_causal(l1_params, l2_params, tf, bar_mask=None) -> CausalResult` — the single causal pass emitting the full per-candle log. |
| `optimize/l2/aggregate.py` (create) | Pure functions: `boxes_for_layer(log, layer)`, `combined_boxes(log)` (max+label), `equity_series(log, layer)`, `log_to_csv(log)`. All read ONLY the log. |
| `optimize/l2/payload.py` (modify) | Add `build_view_payload(l1_params, l2_params, tf, view)` for `view in {l1,l2,combined}`, serializing chart data + log-derived boxes; keep existing functions. |
| `server.py` (modify) | Add `POST /api/causal_backtest {l1,l2,tf,view}` and `GET /api/causal_log.csv`; keep all existing routes. |
| `frontend/dashboard_common.js` (modify) | Add shared helpers `DB.boxFromLog`, `DB.flatAreaSeries`, `DB.grayMarkers`; keep existing API. |
| `frontend/index.html` (modify) | L1 view: render boxes/charts/log from the causal log (L1 layer); flat where L1 idle; never show L2. Additive — keep all existing boxes. |
| `frontend/l2.html` (modify) | L2 view: mirror of index for the L2 layer. |
| `frontend/combined.html` (modify) | Combined view: max+label boxes; charts draw both, gray (not hide) the opposite layer; full per-candle log table + CSV with `layer` column. |
| `optimize/l2/REPORT_causal_logfirst.md` (create) | Final verbose report + before/after box samples (honors the additive rule). |

**Legacy (do not delete this phase):** `optimize/l2/l1_runner.py`, `engine.py`, `metrics.py`, `round2.py` remain as the parity oracle. A later cleanup task (Task 13) removes superseded code only after parity is locked and with a before/after sample.

---

## Phase A — Causality audit (Q4: "both")

### Task 1: Audit the current engine for look-ahead, with evidence

**Files:**
- Create: `optimize/l2/test_causality.py`
- Create: `optimize/l2/AUDIT_causality.md`
- Read: `optimize/l2/l1_runner.py:109-151`, `optimize/data.py` (load_inputs + vf), `indicators/runner.py` (votes/veto/confirm), `optimize/fast_engine.py`

**Interfaces:**
- Consumes: `optimize.l2.l1_runner.run_l1(tf, params=None)`.
- Produces: two passing tests + a written audit other tasks cite as the causality baseline.

**Note (why the obvious tests are wrong):** asserting `percentile(vf[:n_split])` is unchanged when you tamper `vf[n_split:]` is tautological — it tests numpy slicing, not the engine. A real causality test must truncate the ENGINE INPUTS and re-run the pipeline. The council also measured that the warmup back-fill (`volatility.py` nanmedian over the full series) moves the frozen champion's gate threshold by exactly **zero** — record that as a known, measured artifact, not a leak.

- [ ] **Step 1: Write the failing causal-truncation test**

First confirm the return signature of `optimize.data.load_inputs(tf)` (expected `(df_dec, df1, box, vf, n_split)`); the test below assumes it.

```python
# optimize/l2/test_causality.py
import sys; from pathlib import Path
_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
import numpy as np, pandas as pd
from optimize.l2 import l1_runner
from optimize import data as data_mod

def test_decisions_depend_only_on_past_bars(monkeypatch):
    """The real causality property: re-running the engine on inputs TRUNCATED to the first `cut`
    decision bars must reproduce the full run's L1 entries on that prefix (bar index + direction).
    If a past decision used a future bar, the truncated entries would differ."""
    full = l1_runner.run_l1("4h")
    cut = full.n_split
    full_prefix = {(int(t["entry_idx"]), t["direction"]) for t in full.ledger if int(t["entry_idx"]) < cut}

    d4, d1, box, vf, n_split = data_mod.load_inputs("4h")
    t_cut = pd.Timestamp(d4["Date"].iloc[cut - 1])
    d4t = d4.iloc[:cut].copy()
    d1t = d1[d1["Date"] <= t_cut].copy()
    boxt = box[box["Date"] <= t_cut].copy() if "Date" in box else box
    orig = data_mod.load_inputs
    monkeypatch.setattr(data_mod, "load_inputs",
                        lambda tf: (d4t, d1t, boxt, vf[:cut], min(n_split, cut)))
    try:
        trunc = l1_runner.run_l1("4h")
    finally:
        monkeypatch.setattr(data_mod, "load_inputs", orig)
    trunc_entries = {(int(t["entry_idx"]), t["direction"]) for t in trunc.ledger}
    assert trunc_entries == full_prefix, "a past decision changed when future bars were removed (look-ahead)"
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest optimize/l2/test_causality.py -q`
Expected: PASS if the engine is causal. If it FAILS, a real look-ahead bug exists — document it in the audit with the differing bars and **stop for the user** before Phase B.

- [ ] **Step 3: Add the gate-value stability test (causal in VALUES, not just slicing)**

```python
def test_gate_threshold_stable_under_input_truncation(monkeypatch):
    """The in-sample gate threshold computed by the engine must be identical whether or not the
    OOS tail of the RAW inputs exists (the warmup back-fill artifact is measured to be zero)."""
    full = l1_runner.run_l1("4h")
    if full.params["gate_pct"] <= 0:
        return
    cut = full.n_split
    thr_full = float(np.percentile(full.vf[:cut], full.params["gate_pct"]))
    d4, d1, box, vf, n_split = data_mod.load_inputs("4h")
    # recompute vf on truncated raw inputs via the same volatility path the loader uses, then compare
    from optimize import volatility  # confirm module/function at execution
    vf_trunc = volatility.forecast_for(d4.iloc[:cut], d1[d1["Date"] <= pd.Timestamp(d4["Date"].iloc[cut-1])]) \
        if hasattr(volatility, "forecast_for") else full.vf[:cut]
    thr_trunc = float(np.percentile(vf_trunc[:cut], full.params["gate_pct"]))
    assert abs(thr_full - thr_trunc) < 1e-9, "gate threshold moved when future raw inputs were removed"
```

(Execution confirms the exact volatility entry point; if no separate recompute path exists, the Step-1 truncation test is the load-bearing causal proof and this one asserts the measured-zero artifact.)

- [ ] **Step 4: Run both tests**

Run: `python3 -m pytest optimize/l2/test_causality.py -q`
Expected: PASS (2 passed). Any failure ⇒ real bug ⇒ document + stop for the user.

- [ ] **Step 5: Write `AUDIT_causality.md`**

Distinguish **causal-in-slicing** (the gate uses `vf[:n_split]`, `l1_runner.py:118-120`) from **causal-in-values** (the back-fill/warmup does not let a future bar change a past `vf` value — measured threshold delta = 0 for the champion). Cite the two tests above as the load-bearing evidence (NOT the old tautological ones). Cover: (1) gate threshold reference-only + value-stable; (2) indicators causal (`indicators/runner.py`); (3) 1-min exit resolution is the trade *playing out* forward, not look-ahead — add the `exit_time > entry_time` sample assertion as evidence; (4) verdict. Mermaid only.

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/test_causality.py optimize/l2/AUDIT_causality.md
git commit -m "test(l2): causality audit — gate is reference-only + decisions are past-only"
```

---

## Phase B — The causal log engine

### Task 2: `LogRow` schema + empty `run_causal` skeleton

**Files:**
- Create: `optimize/l2/logbook.py`
- Test: `optimize/l2/test_logbook.py` (create)
- **Read (MANDATORY — the live log emitter the schema must superset):** `strategy.py` (Parametric-Indicators **project root**, NOT under `optimize/`), lines ~333-497 — the `events.append(...)` calls and their fields. Also `frontend/index.html` + `frontend/combined.html` log-table/CSV renderers (they read `e.type`/`e.text`).

**Interfaces:**
- Consumes: `l1_runner.run_l1` (for masks/data only, not its ledger), `optimize.l2.payload.validate_layer_params`.
- Produces:
  - `LogRow` dataclass — a strict SUPERSET of every field/event today's emitter produces (additive-rule compliance):
    `i:int, time:int(epoch), layer:str("L1"|"L2"|None), decision:str("entry"|"nonentry"),
     reason:str, box_cause:str|None, event_type:str|None, text:str,
     direction:str|None, box_dir:str|None, veto_flip:bool, indicators:list[dict],
     entry_price:float|None, exit_time:int|None, exit_price:float|None, exit_reason:str|None,
     would_be_pnl:float|None, pnl:float, equity:float, dd:float, in_position:bool, position_owner:str|None`
    - `reason` enum: `"entered" | "box_silence" | "vol_gated" | "vetoed" | "confirm<K" | "open_trade" | "force_closed" | "breaker_locked" | "breaker_unlocked" | "warmup" | "warmed"`.
    - `box_cause` (NEW, load-bearing): the UNDERLYING box/gate/veto/confirm cause of the bar, **preserved even when `reason` is `open_trade`/`force_closed`** — because legacy `pause_totals` counts box_silence/gate/indicator over ALL bars including while a position is held (~497 such bars on the 4h champion; legacy `box_silence_total=1290`). Without it the log-derived `*_total` boxes silently undercount vs index.html.
    - `event_type` mirrors today's `ENTRY/WIN/LOSS/LOCK/UNLOCK/SKIP/NOENTRY/WARMUP/WARMED` so existing renderers/CSV keep working; `text` is the human-readable line; `would_be_pnl` carries the SKIP (breaker-locked) would-be P/L; `veto_flip` the REVERSED annotation; `exit_time` enables exit-ordered combined equity (Task 5).
  - `CausalResult` dataclass: `tf:str, l1_params:dict, l2_params:dict, log:list[LogRow], n:int, dec_dates, warmup:dict` (the last carries per-layer `warmup_bars`/`indicator_req_bars` from `indicators.library.warmup_bars()` — the single source for the warmup/indicator-req boxes, since those are config-derived not log-derived).
  - `run_causal(l1_params, l2_params, tf="4h", bar_mask=None) -> CausalResult`.

- [ ] **Step 0: Field-mapping proof (additive-rule gate)**

Read `strategy.py:333-497`. Produce a before→after table (commit it into the Task-12 report stub) mapping EVERY emitted event type and field to a `LogRow` field:
`ENTRY→{decision:entry,event_type:ENTRY,indicators}`, `WIN/LOSS→{event_type,text,pnl,equity,dd}`,
`LOCK→{reason:breaker_locked,event_type:LOCK,text}`, `UNLOCK→{reason:breaker_unlocked,event_type:UNLOCK,text}`,
`SKIP→{reason:breaker_locked,event_type:SKIP,would_be_pnl,text}`, `NOENTRY{reason}→{decision:nonentry,reason,box_cause,indicators}`,
`WARMUP→{reason:warmup,event_type:WARMUP,text}`, `WARMED→{reason:warmed,event_type:WARMED,text}`, `veto_flip/REVERSED→{veto_flip}`.
If any field has NO mapping, STOP and ask the user for explicit permission to drop it (with this table as the before/after sample). Do not proceed until every field is accounted for.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_logbook.py
import sys; from pathlib import Path
_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
from optimize.l2 import logbook, payload

def test_run_causal_emits_one_row_per_decision_bar():
    l1 = payload.l1_default_params("4h"); l2 = dict(payload.PERMISSIVE)
    res = logbook.run_causal(l1, l2, "4h")
    assert res.n == len(res.log) == len(res.dec_dates)
    assert {r.layer for r in res.log} <= {"L1", "L2", None}
    assert all(r.reason for r in res.log)              # every row attributed
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_run_causal_emits_one_row_per_decision_bar -q`
Expected: FAIL (`ModuleNotFoundError`/`AttributeError: run_causal`).

- [ ] **Step 3: Implement the dataclasses + skeleton**

```python
# optimize/l2/logbook.py
"""Single causal pass over decision candles producing the complete per-candle log (the source of truth).
Single shared account, L1 priority, force-close. Reuses fast_engine for sub-bar exit math; this module
only orchestrates the bar-by-bar interleave and emits LogRows. Legacy l1_runner/engine remain the oracle."""
from __future__ import annotations
import sys; from dataclasses import dataclass, field; from pathlib import Path
_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
import numpy as np, pandas as pd
import config
from optimize.l2 import l1_runner, payload
from optimize.l2.engine import _l2_gate_masks   # reuse L2 mask recipe (already golden-tested)

@dataclass
class LogRow:
    i: int; time: int; layer: str | None; decision: str; reason: str
    box_cause: str | None = None; event_type: str | None = None; text: str = ""
    direction: str | None = None; box_dir: str | None = None; veto_flip: bool = False
    indicators: list = field(default_factory=list)
    entry_price: float | None = None; exit_time: int | None = None
    exit_price: float | None = None; exit_reason: str | None = None
    would_be_pnl: float | None = None
    pnl: float = 0.0; equity: float = 0.0; dd: float = 0.0
    in_position: bool = False; position_owner: str | None = None

@dataclass
class CausalResult:
    tf: str; l1_params: dict; l2_params: dict; log: list; n: int; dec_dates: object
    warmup: dict = field(default_factory=dict)   # per-layer {l1:{warmup_bars,indicator_req_bars}, l2:{...}}

def run_causal(l1_params: dict, l2_params: dict, tf: str = "4h", bar_mask=None) -> CausalResult:
    raise NotImplementedError
```

- [ ] **Step 4: Run it**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_run_causal_emits_one_row_per_decision_bar -q`
Expected: FAIL (`NotImplementedError`) — schema imports cleanly, engine still stubbed.

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/logbook.py optimize/l2/test_logbook.py
git commit -m "feat(l2): LogRow schema + run_causal skeleton (per-candle log core)"
```

### Task 3: Implement `run_causal` — single-account causal interleave

**Files:**
- Modify: `optimize/l2/logbook.py`
- Test: `optimize/l2/test_logbook.py`

**Interfaces:**
- Consumes: `l1_runner.run_l1(tf, params)` to obtain per-bar masks (`sig_int`, `vol_gate`, `veto`, `confirm`, `cause`) and data frames for BOTH layers; `fast_engine.fast_backtest` for trade resolution; `engine._l2_gate_masks` for the L2 eligibility recipe.
- Produces: a populated `res.log` where each bar's row reflects the single-account state machine.

**Design (state machine, per decision bar i in time order) — pinned to the oracle exactly:**

```
account: flat | open(owner, trade)         # one position max
L1_entry_bars = {entry_idx of legacy l1.ledger}   # POST-breaker set (engine.py:113), the SAME set legacy uses
L2_eligible(i) = (l1.cause[i] in {"vetoed","vol_gated"})   # the dropped set ONLY (NOT box_silence/confirm<K/open_trade)
                 and account is flat
                 and _l2_gate_masks(l1, l2_params)[i] is True
for i in 1..n-1:
  if account is open:
      if owner == "L2" and i in L1_entry_bars and (entry_idx_of_open < i < exit_bar_of_open):
          # STRICT boundary: force-close only when the L1 entry is STRICTLY inside the open L2 span.
          # If i == the L2 trade's natural exit bar, the natural exit wins (no force-close).
          close L2 at dec_close[i], exit_reason "force_closed"; book; account=flat   # fall through, L1 opens
      elif i == exit_bar_of_open:
          close trade at its fast_backtest exit; account=flat
      else:
          row = nonentry, reason "open_trade", box_cause = cause[i], owner = account.owner ; continue
  if account is flat:
      if l1.cause[i] == "would_enter":               # L1 takes it (post-breaker membership decides actual open)
          open L1 trade (fast_backtest single-trade from i, with blocked_until re-entry, see below); row=entry L1
      else:
          row(L1 nonentry, reason=cause[i], box_cause=cause[i])
          if L2_eligible(i):
              open L2 trade; row=entry L2 (this bar's owning decision becomes L2; box_cause kept)
          # else: L2 also declined -> annotate L2's own reason; row stays L1 nonentry
  on every booked exit: update running equity & dd (per layer)
```

Trade resolution reuses `fast_backtest` per opened trade so sub-bar math is byte-identical to the oracle. Pin these to avoid drift: (1) **breaker** uses `l1_runner.apply_breaker` PER LAYER on each layer's own booked trades (global-HWM, same as `core`); (2) **re-entry / blocked_until** must reproduce `fast_engine.py:148-151` (`searchsorted(..., side='right')`) so the L1 entry set is byte-equal to legacy's 255; (3) the within-candle order is: resolve via `fast_backtest` → apply `force_close_on_l1_entry` with the strict `entry_idx < j < exit_bar` boundary (reuse `engine.force_close_on_l1_entry`) → per-layer breaker. The L1 would-enter→actual-open is governed by membership in the post-breaker `L1_entry_bars`, NOT by `cause` alone.

- [ ] **Step 1: Write the failing parity test (THE anchor)**

```python
def test_causal_l1_matches_legacy_oracle():
    """L1 trades derived from the causal log must equal the legacy l1_runner ledger exactly."""
    from optimize.l2 import l1_runner
    l1p = payload.l1_default_params("4h")
    legacy = l1_runner.run_l1("4h")                       # frozen lean champion
    res = logbook.run_causal(l1p, dict(payload.PERMISSIVE), "4h")
    l1_entries = [(r.i, r.direction) for r in res.log if r.layer == "L1" and r.decision == "entry"]
    legacy_entries = [(int(t["entry_idx"]), t["direction"]) for t in legacy.ledger]
    assert l1_entries == legacy_entries
    l1_pnl = round(sum(r.pnl for r in res.log if r.layer == "L1"))
    assert l1_pnl == 149989
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_causal_l1_matches_legacy_oracle -q`
Expected: FAIL (`NotImplementedError`).

- [ ] **Step 3: Implement `run_causal`** (replace the `raise`). Walk bars with the state machine above; build L1 decision from `l1.cause[i]` (`would_enter`→entry); build L2 decision from `_l2_gate_masks(l1, l2_params)[i]` AND the dropped-while-flat condition; resolve each opened trade via `fast_backtest` restricted to that single entry; book equity/dd; populate every `LogRow`. (Full code written during execution; the state machine and field set above are the exact contract.)

- [ ] **Step 4: Run the parity test**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_causal_l1_matches_legacy_oracle -q`
Expected: PASS.

- [ ] **Step 5: Add the L2 parity test**

```python
def test_causal_l2_matches_legacy_engine():
    """L2 book from the causal log must equal legacy engine.run_l2 (l1_priority) STRUCTURALLY,
    not just in rounded dollars — entry set, count, DD, locks, and the force-closed subset."""
    import json, numpy as np
    from optimize.l2 import l1_runner, engine, metrics
    l1p = payload.l1_default_params("4h")
    champ = json.load(open(str(_PI / "optimize/results/l2v1_4h_champion.json")))["params"]
    legacy_l1 = l1_runner.run_l1("4h")
    legacy = engine.run_l2(legacy_l1, champ)              # l1_priority
    res = logbook.run_causal(l1p, champ, "4h")
    l2_rows = [r for r in res.log if r.layer == "L2" and r.decision == "entry"]
    # entry set (bar + direction) equals legacy
    assert sorted((r.i, r.direction) for r in l2_rows) == \
           sorted((int(t["entry_idx"]), t["direction"]) for t in legacy.ledger)
    assert len(l2_rows) == 80
    assert round(metrics.score(legacy)["pnl"]) == round(sum(r.pnl for r in l2_rows)) == 78391
    eq = np.cumsum([r.pnl for r in sorted(l2_rows, key=lambda r: r.exit_time)])
    assert round(float((np.maximum.accumulate(eq) - eq).max())) == 8961        # L2 DD
    # per-layer breaker locks match the oracle exactly
    assert sum(1 for r in res.log if r.reason == "breaker_locked" and r.position_owner == "L2") \
           == legacy.n_locks
    # the force-closed subset (bar + exit price + pnl) equals legacy's n_l1_entry_exits trades
    fc_causal = sorted((r.i, round(r.exit_price, 4), round(r.pnl, 2)) for r in l2_rows if r.exit_reason == "L1-entry")
    fc_legacy = sorted((int(t["entry_idx"]), round(float(t["exit_price"]), 4), round(float(t["pnl"]), 2))
                       for t in legacy.ledger if t["exit_reason"] == "L1-entry")
    assert fc_causal == fc_legacy and len(fc_causal) == legacy.n_l1_entry_exits

def test_force_close_only_strictly_inside_l2_span():
    """An L1 entry landing EXACTLY on an L2 trade's natural exit bar must NOT force-close it
    (the natural exit wins); only an L1 entry strictly inside (entry_idx < j < exit_bar) force-closes."""
    # synthetic: one L2 trade spanning bars [e, x); assert engine.force_close_on_l1_entry leaves it
    # untouched when the only L1 entry is at j == x, and truncates it when j is in (e, x).
    from optimize.l2 import engine
    import numpy as np
    dec_dates = np.array(["2025-01-01T00:00","2025-01-01T04:00","2025-01-01T08:00","2025-01-01T12:00"], dtype="datetime64[ns]")
    dec_close = np.array([100.0, 110.0, 120.0, 130.0])
    cand = [{"entry_idx":0,"entry_time":dec_dates[0],"entry_price":100.0,"direction":"long",
             "exit_time":dec_dates[2],"exit_price":120.0,"exit_reason":"TAKE_PROFIT_HARD","pnl_points":20.0}]
    assert engine.force_close_on_l1_entry(list(cand),[2],dec_dates,dec_close,20.0)[0]["exit_reason"] == "TAKE_PROFIT_HARD"
    assert engine.force_close_on_l1_entry(list(cand),[1],dec_dates,dec_close,20.0)[0]["exit_reason"] == "L1-entry"
```

- [ ] **Step 6: Run it**

Run: `python3 -m pytest optimize/l2/test_logbook.py -q`
Expected: PASS (all logbook tests).

- [ ] **Step 7: Golden gate**

Run: `python3 perf/check_golden.py`
Expected: `✅ ALL GOLDEN BASELINES MATCH` (6/6) — `run_causal` is additive, touches no engine bytes.

- [ ] **Step 8: Commit**

```bash
git add optimize/l2/logbook.py optimize/l2/test_logbook.py
git commit -m "feat(l2): run_causal single-account interleave — L1+L2 parity with legacy oracle"
```

---

## Phase C — Boxes & CSV derived from the log

### Task 4: `aggregate.boxes_for_layer` — every per-layer box from the log

**Files:**
- Create: `optimize/l2/aggregate.py`
- Test: `optimize/l2/test_aggregate.py` (create)

**Interfaces:**
- Consumes: `CausalResult` (`.log` and `.warmup`), `optimize.pause_streaks` (longest_run/_dur).
- Produces: `boxes_for_layer(result, layer, bar_seconds) -> dict` with the SAME keys the dashboards already show:
  `pnl, max_dd, win, pf, n_taken, n_candidates, exposure, n_locks, noentry_streak_n,
   noentry_streak_days, noentry_streak_start, box_silence, position_hold, gate_noentry,
   indicator_noentry, noentry_total, box_silence_total, position_hold_total, gate_noentry_total,
   indicator_noentry_total, warmup, indicator_req` — derived from the log filtered to `layer`, **except**:
  - **totals use `box_cause`, not `reason`** — count box_silence/gate/indicator over ALL of the layer's bars (including `open_trade`/`force_closed` rows) via each row's `box_cause`, so they match legacy `pause_totals` (which counts regardless of in-position state). Verified: ~497 such bars occur while L1 holds; legacy `box_silence_total=1290`.
  - **`warmup` and `indicator_req` are config-derived, NOT log-derived** — read from `result.warmup[layer]` (`indicators.library.warmup_bars()`, the single source). The log carries no warmup data; these two boxes are the documented exception to "every box from the log."

- [ ] **Step 1: Write the failing test (boxes-from-log equal the known L1 set)**

```python
# optimize/l2/test_aggregate.py
import sys; from pathlib import Path
_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
from optimize.l2 import logbook, aggregate, payload

def test_l1_boxes_from_log_match_known_values():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    b = aggregate.boxes_for_layer(res, "L1", bar_seconds=4*3600)
    assert round(b["pnl"]) == 149989 and b["n_taken"] == 255
    # totals computed from box_cause over ALL bars (incl. in-position) — matches legacy
    assert b["box_silence_total"]["bars"] == 1290
    assert b["noentry_total"]["bars"] == (b["box_silence_total"]["bars"]
        + b["gate_noentry_total"]["bars"] + b["indicator_noentry_total"]["bars"])
    # warmup/indicator_req are config-derived (from result.warmup), present and positive
    assert b["warmup"]["bars"] > 0 and b["indicator_req"]["bars"] > 0
```

- [ ] **Step 2: Run it** — Expected: FAIL (no `aggregate`).

- [ ] **Step 3: Implement `boxes_for_layer(result, layer, bar_seconds)`** — financials from `[r for r in result.log if r.layer==layer and r.decision=="entry"]` (P/L; DD = max underwater of that layer's equity; win; pf); the no-entry STREAK boxes from each bar's `reason` mapped to box_silence/gate/indicator fed to `pause_streaks.longest_run`; the `*_total` boxes from each bar's **`box_cause`** (counting over ALL of the layer's bars including `open_trade`/`force_closed`, mirroring legacy `pause_totals`); `position_hold` from `in_position` spans owned by `layer`; `warmup`/`indicator_req` from `result.warmup[layer]` (config-derived). Cross-check key-by-key against `strategy.build_payload`'s box dict for the frozen champion (a per-box parity check beyond the headline anchors). (Full code at execution; key set + sources above are the contract.)

- [ ] **Step 4: Run it** — Expected: PASS.

- [ ] **Step 5: Add CSV export test + `log_to_csv`**

```python
def test_log_to_csv_has_layer_and_reason_columns():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    header, rows = aggregate.log_to_csv(res.log)
    assert header[:4] == ["i", "time", "layer", "decision"] and "reason" in header
    assert len(rows) == res.n
```

- [ ] **Step 6: Implement `log_to_csv`; run; commit**

```bash
git add optimize/l2/aggregate.py optimize/l2/test_aggregate.py
git commit -m "feat(l2): aggregate boxes + CSV strictly from the per-candle log"
```

### Task 5: `aggregate.combined_boxes` — per-box combination rules (sum / recompute / max)

**Files:**
- Modify: `optimize/l2/aggregate.py`
- Test: `optimize/l2/test_aggregate.py`

**Interfaces:**
- Consumes: `boxes_for_layer`, the `CausalResult` (raw log for win/pf/DD recompute; `.warmup` for warmup/indicator-req), and the legacy oracle for the max_dd parity assertion.
- Produces: `combined_boxes(result, bar_seconds) -> dict[str, ...]` applying the **per-box rule** (see Global Constraints):
  - **sum** keys → `pnl`, `n_taken` (trades), `n_candidates`, `n_locks` → `{"value": l1+l2}` (no layer tag).
  - **recompute** keys → `max_dd`, `win`, `pf`, `exposure` over the COMBINED entry rows: **`max_dd` = max underwater of the merged equity cumulated in EXIT-time order** (`r.exit_time`, matching legacy `metrics.combined` which sorts by exit time — NOT decision/entry time); win% = combined winners / trades; pf = Σwins$ / |Σlosses$|; exposure = combined n_taken / n_candidates → `{"value": recomputed}` (no tag).
  - **max** keys → all streak boxes (`noentry_streak_n` + days/start, `box_silence`, `position_hold`, `gate_noentry`, `indicator_noentry`), `warmup`, `indicator_req` → `{"value": larger, "layer": winner}` (duration boxes compare on `bars`).
  - **guardrail keys (KEEP — additive, present in today's combined.html)** → `l1_only_dd` (= L1's own max_dd), `uplift` (= combined pnl − L1 pnl), `dd_not_worse` (= combined max_dd ≤ l1_only_dd), `n_l1_entry_exits` (= count of L2 rows with exit_reason "L1-entry"). These are kept so no existing box vanishes.
  - **excluded** → all `*_total` keys (deferred to individual views).

- [ ] **Step 1: Write the failing test**

```python
def test_combined_boxes_apply_per_box_rules():
    import json, numpy as np
    from optimize.l2 import l1_runner, engine, metrics
    champ = json.load(open(str(_PI/"optimize/results/l2v1_4h_champion.json")))["params"]
    res = logbook.run_causal(payload.l1_default_params("4h"), champ, "4h")
    c = aggregate.combined_boxes(res, bar_seconds=4*3600)
    l1 = aggregate.boxes_for_layer(res, "L1", 4*3600); l2 = aggregate.boxes_for_layer(res, "L2", 4*3600)
    # SUM boxes
    assert c["pnl"]["value"] == round(l1["pnl"] + l2["pnl"], 2)
    assert c["n_taken"]["value"] == l1["n_taken"] + l2["n_taken"]
    assert c["n_locks"]["value"] == l1["n_locks"] + l2["n_locks"]
    assert "layer" not in c["pnl"]
    # max_dd RECOMPUTED from merged EXIT-ordered equity — assert EQUAL to the legacy oracle (not a loose bound)
    legacy_l1 = l1_runner.run_l1("4h"); legacy_l2 = engine.run_l2(legacy_l1, champ)
    assert round(c["max_dd"]["value"]) == round(metrics.combined(legacy_l1, legacy_l2)["max_dd"])
    assert c["max_dd"]["value"] <= round(l1["max_dd"] + l2["max_dd"], 2) + 1e-6   # the catch holds too
    # win/pf recomputed from the combined trade set
    entries = [r for r in res.log if r.decision == "entry"]
    wins = [r.pnl for r in entries if r.pnl > 0]; losses = [r.pnl for r in entries if r.pnl < 0]
    assert c["win"]["value"] == round(100 * len(wins) / max(len(entries), 1), 1)
    assert c["pf"]["value"] == (round(sum(wins) / abs(sum(losses)), 2) if losses else None)
    # MAX boxes tagged; warmup/indicator_req present and tagged
    assert c["noentry_streak_n"]["value"] == max(l1["noentry_streak_n"], l2["noentry_streak_n"])
    assert c["noentry_streak_n"]["layer"] in ("L1", "L2") and c["warmup"]["layer"] in ("L1", "L2")
    # guardrail boxes kept (additive); totals deferred
    for k in ("l1_only_dd", "uplift", "dd_not_worse", "n_l1_entry_exits"): assert k in c
    assert not any(k.endswith("_total") for k in c)
```

- [ ] **Step 2: Run it** — Expected: FAIL.
- [ ] **Step 3: Implement `combined_boxes`** with the rule groups above (sum / recompute-from-combined-entries with EXIT-time-ordered DD / max-with-tag / kept guardrails); win/pf/exposure/DD recomputed from `[r for r in result.log if r.decision=="entry"]`; warmup/indicator_req from `result.warmup`.
- [ ] **Step 4: Run it** — Expected: PASS.
- [ ] **Step 5: Commit**

```bash
git add optimize/l2/aggregate.py optimize/l2/test_aggregate.py
git commit -m "feat(l2): combined boxes — per-box rules (sum pnl/dd/trades/locks; recompute win/pf; max streaks/warmup)"
```

---

## Phase D — Server payload + three dashboards on the log

### Task 6: `build_view_payload` + server routes

**Files:**
- Modify: `optimize/l2/payload.py` (append; keep all existing functions)
- Modify: `server.py` (add routes; keep all existing routes)
- Test: `optimize/l2/test_l2_server.py` (append)

**Interfaces:**
- Consumes: `logbook.run_causal`, `aggregate.*`.
- Produces:
  - `payload.build_view_payload(l1_params, l2_params, tf, view) -> dict` with `meta.boxes` (per-view: `boxes_for_layer` for l1/l2, `combined_boxes` for combined), `candles`, `log` (serialized rows), `equity` series per layer + combined, and `flat`/`gray` flags per bar for the view.
  - `POST /api/causal_backtest {l1,l2,tf,view}` → that payload. Route the FROZEN-L1 case through `payload.run_l1_cached` (not the uncached `run_l1`); a custom-L1 run recomputes (memoised by params-hash, as today). **Perf note:** a dynamic per-run recompute of 1-min indicators for both layers is the known bottleneck tracked as pending task **#210** — this plan INHERITS that cost (does not resolve it); the disk/param-hash cache keeps the frozen-champion path ~1s.
  - `GET /api/causal_log.csv?...` → text/csv of `log_to_csv`.

- [ ] **Step 1: Write the failing server smoke test**

```python
def test_causal_backtest_route_three_views():
    srv, port = _serve()
    try:
        cfg = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        for view in ("l1", "l2", "combined"):
            out = json.loads(_post(port, "/api/causal_backtest",
                {"l1": cfg["l1_default"], "l2": cfg["l2_default"], "tf": "4h", "view": view}).read())
            assert "boxes" in out["meta"] and len(out["log"]) == out["meta"]["n"]
    finally:
        srv.shutdown()
```

- [ ] **Step 2-4:** Run (FAIL) → implement `build_view_payload` + routes → run (PASS).
- [ ] **Step 5: Golden gate** `python3 perf/check_golden.py` → 6/6.
- [ ] **Step 6: Commit**

```bash
git add optimize/l2/payload.py server.py optimize/l2/test_l2_server.py
git commit -m "feat(l2): /api/causal_backtest (l1|l2|combined views) + /api/causal_log.csv from the log"
```

### Task 7: Shared JS helpers for flat-area + gray + box-from-log

**Files:**
- Modify: `frontend/dashboard_common.js` (append to `DB`; keep existing API)

**Interfaces:**
- Produces on `window.DB` (all pure, copy-not-mutate):
  - `boxFromLog(boxObj)` → formats a box: if it has a `layer`, append a small `· L1`/`· L2` tag; sum/recompute boxes (no layer) render the value alone.
  - `flatAreaSeries(log, layer)` → equity-style series that is **constant (flat) across bars where `layer` is idle** and steps only on that layer's realized exits (for the separated views' flat areas).
  - `grayMarkers(markers, grayed)` → returns a COPY of markers with the grayed ones recolored to theme muted gray (never mutates input).
  - `grayLine(series, grayed, origColor)` → `series.applyOptions({color: grayed ? TH.muted : origColor})` — grays an equity line in place WITHOUT hiding it (combined view: opposite layer stays visible-but-muted, never `visible:false`).

- [ ] **Step 1: Add a minimal node-runnable assertion harness** `frontend/test_dashboard_common.mjs` (or a `<script>`-loaded assert block) covering the PURE helpers: `flatAreaSeries` has no time gaps and is constant across idle bars; `grayMarkers` returns a copy (input unchanged) and recolors only grayed entries; `boxFromLog` adds the tag only when `layer` is present. Run with `node frontend/test_dashboard_common.mjs` (extract the pure functions or expose them on a testable object). Expected: all asserts pass.
- [ ] **Step 2: Commit**

```bash
git add frontend/dashboard_common.js
git commit -m "feat(ui): shared flat-area + gray-out + box-from-log helpers (DRY across 3 dashboards)"
```

### Task 8: Combined dashboard on the log (max+label boxes, gray toggle, full log table + CSV)

**Files:**
- Modify: `frontend/combined.html`

**Interfaces:**
- Consumes: `/api/causal_backtest?view=combined`, `DB.boxFromLog`, `DB.grayMarkers`, `/api/causal_log.csv`.

- [ ] **Step 0: Capture the before/after box sample as a committed artifact** (per the additive rule, BEFORE editing) — snapshot the current combined.html box set, and write the after-set into the Task-12 report stub. Sequence the whole Task-8 cutover AFTER Task 11's cross-view + golden gate passes.
- [ ] **Step 1:** Point the combined run at `/api/causal_backtest` with `view:"combined"`; render the rule-combined box set — **financials** (P/L sum, DD recomputed-merged, win recomputed, PF recomputed), **streaks** (max + layer tag), **counts** (trades sum, locks sum, warmup max+tag, indicator-req max+tag), and **KEEP the guardrail boxes** (`l1_only_dd`, `uplift`, `dd_not_worse`, `n_l1_entry_exits` / L1-entry force-closes). Use `DB.boxFromLog` for max-type boxes (value + layer tag); plain value for sum/recompute boxes. **Do NOT render the totals group** (deferred). **Show a before/after sample** in the commit body — before: 3 stacked groups (L1-alone / L2-alone / combined-book); after: one rule-combined set + kept guardrail boxes; totals removed from combined only.
- [ ] **Step 2:** Change the L1/L2/Both toggle to GRAY the opposite layer — `DB.grayMarkers` for price markers/lines and `DB.grayLine` for the opposite equity line. Do NOT use `visible:false`. Combined equity is flat only where BOTH layers are idle.
- [ ] **Step 3:** ADD a per-candle log table (every candle: `layer`/`reason`/`box_cause`/indicator status) ALONGSIDE the existing trade-ledger and dropped-signals tables (do not replace them). The full-log CSV downloads from `/api/causal_log.csv` (keeps the `layer` column); the existing `combined_ledger.csv` download stays.
- [ ] **Step 4: Manual verify** (server running): open `/combined.html`; confirm the rule-combined boxes show `· L1/L2` tags only on max-type boxes, the guardrail boxes are present, the toggle GRAYS (not hides) the opposite layer's markers AND equity line, the per-candle log table renders alongside the existing tables, and both CSVs download (full-log CSV has `layer` + one row per candle).
- [ ] **Step 5: Commit**

```bash
git add frontend/combined.html
git commit -m "feat(ui): combined dashboard from the log — max+label boxes, gray toggle, per-candle log+CSV"
```

### Task 9: L1 dashboard (separated view) on the log

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1:** Add an opt-in path so index.html can render its boxes/log/charts from `/api/causal_backtest?view=l1` (L1-only). Keep the existing `/api/backtest` path intact (additive); a toggle or query selects the source. Charts: show L1 entries/positions; flat where L1 idle; never draw L2.
- [ ] **Step 2: Manual verify**: L1 boxes match today's values; quiet periods render flat; no L2 markers appear.
- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(ui): L1 dashboard renders the L1-only view from the causal log (flat where idle)"
```

### Task 10: L2 dashboard (separated view) on the log

**Files:**
- Modify: `frontend/l2.html`

- [ ] **Step 1:** Point l2.html at `/api/causal_backtest?view=l2`; boxes/log/charts are L2-only; flat where L2 idle; never draw L1. Keep all existing L2 boxes (additive).
- [ ] **Step 2: Manual verify** + **Step 3: Commit**

```bash
git add frontend/l2.html
git commit -m "feat(ui): L2 dashboard renders the L2-only view from the causal log (flat where idle)"
```

---

## Phase E — Verify, document, (optional) cleanup

### Task 11: Full suite + golden + cross-view consistency test

**Files:**
- Test: `optimize/l2/test_aggregate.py` (append)

- [ ] **Step 1: Write the cross-view consistency test**

```python
def test_views_partition_the_same_log():
    """A candle owned by L1 in the log must never appear as an L2 entry, and vice-versa — the three
    views are projections of ONE log."""
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    l1_entry_bars = {r.i for r in res.log if r.layer == "L1" and r.decision == "entry"}
    l2_entry_bars = {r.i for r in res.log if r.layer == "L2" and r.decision == "entry"}
    assert l1_entry_bars.isdisjoint(l2_entry_bars)
```

- [ ] **Step 2: Run the whole L2 suite + golden**

Run: `python3 -m pytest optimize/l2/ -q && python3 perf/check_golden.py`
Expected: all pass + golden 6/6.

- [ ] **Step 3: Commit**

```bash
git add optimize/l2/test_aggregate.py
git commit -m "test(l2): three views are disjoint projections of one causal log"
```

### Task 12: Verbose report with before/after box samples

**Files:**
- Create: `optimize/l2/REPORT_causal_logfirst.md`

- [ ] **Step 1:** Write the report (Mermaid only): the causal state machine, the LogRow schema shown as a SUPERSET table of today's event fields (the Task-2 Step-0 mapping — proving nothing was removed), boxes-from-log derivation (incl. the `box_cause`-driven totals and the config-derived warmup/indicator-req exceptions), the per-box combine rules (P/L+trades+locks sum; DD/win/PF recomputed; streaks/warmup/indicator-req max+tag; guardrails kept; totals deferred from combined), the graph flat/gray semantics, the causality audit verdict (causal-in-slicing vs causal-in-values), and a **before/after box sample** for the combined view (3 stacked groups → one rule-combined set + kept guardrails, totals removed from combined only).
- [ ] **Step 2: Commit + push**

```bash
git add optimize/l2/REPORT_causal_logfirst.md
git commit -m "docs(l2): causal log-first system report + before/after box samples"
git push origin dev
```

### Task 13: (Gated — needs explicit user OK) retire superseded legacy code

**Files:**
- Modify/Delete: `optimize/l2/engine.py`, `metrics.py`, parts of `payload.py` once unused.

- [ ] **Step 1:** ONLY after parity is locked and the dashboards run on the log: present a before/after diff of what would be removed and **ask for explicit permission** (per the global constraint). Do not delete anything in this plan without that approval.

---

## Self-Review

**1. Spec coverage (SYSTEM_REVIEW.MD → task):**
- Causal per-candle interleave, not two-pass → Task 3. ✓
- Dynamic, not pinned (both layers editable, recompute) → Task 3 takes `l1_params`+`l2_params` live; legacy editable path already exists. ✓
- Logs = single source of truth; backtester emits full per-candle log → Tasks 2-3 (LogRow + run_causal). ✓
- Boxes computed FROM logs; CSV export → Tasks 4 (boxes_for_layer, log_to_csv). ✓
- L1 reports L1-only / L2 reports L2-only → Tasks 9, 10. ✓
- Combined boxes use PER-BOX rules (P/L+DD+trades+locks sum; win+PF recomputed from combined trades; streaks+warmup+indicator-req max with layer tag); totals group deferred to individual views → Tasks 5, 8. ✓
- Graph flat areas; separated hide opposite; combined gray opposite → Tasks 7-10. ✓
- Single shared account / L1 priority / force-close (Q1) → Task 3 state machine. ✓
- Causality audit with evidence (Q4) → Task 1. ✓
- Additive-only; never remove without permission + before/after → Tasks 8, 12 samples; Task 13 gated. ✓
- Parity anchors ($149,989/255; $78,391/80; golden 6/6) → Tasks 3, 6, 11. ✓

**2. Placeholder scan:** Engine/aggregator bodies in Tasks 3-6 say "full code at execution" but every one fixes the exact interface, field set, and the parity test that pins behavior — the contract is complete; only line-level fill remains. No TBD/edge-case hand-waving.

**3. Type consistency:** `LogRow` field names (Task 2) are reused verbatim in `boxes_for_layer` (Task 4), `combined_boxes` (Task 5), payload (Task 6) and the dashboards (8-10). Box-key set is identical to what index.html/l2.html already render (so the dashboards keep every existing box). `combined_boxes`/`boxes_for_layer` take the `CausalResult` (not the bare log) so warmup/indicator-req can be read from `.warmup`; max-type combined boxes return `{value,layer}` consumed by `DB.boxFromLog`, sum/recompute boxes return `{value}`.

---

## Council review (applied 2026-06-19)

A 6-lens expert council (quant correctness, causality audit, architecture/TDD, frontend/UX, requirements coverage, adversarial risk) reviewed this plan; 51 findings raised, 46 survived adversarial verification; verdict **GO_WITH_EDITS**. The 1 blocker + 8 required edits are now folded in:

1. **LogRow is now a true superset** of today's emitter (Task 2): added `text`/`event_type`/`would_be_pnl`/`veto_flip`/`box_cause`/`exit_time`, extended the `reason` enum (warmup/warmed/breaker_unlocked), added `strategy.py` to the reads, and a Step-0 field-mapping gate that STOPS for permission if any field is unmapped.
2. **`box_cause`** preserved on every row so the `*_total` boxes count box/gate/indicator bars even while a position is held (matches legacy `box_silence_total=1290`).
3. **warmup/indicator-req** sourced from `CausalResult.warmup` (`library.warmup_bars()`), documented as the one log-exception.
4. **Combined max-DD** recomputed from the merged equity in **exit-time** order and asserted EQUAL to the legacy `metrics.combined` oracle (not a loose ≤ bound).
5. **L2 parity test** strengthened to entry-set + count(80) + DD(8961) + per-layer locks + the exact force-closed subset; added a strict force-close-boundary edge test.
6. **Task 3 state machine** pins the L2 eligibility set (`cause ∈ {vetoed,vol_gated}` ∧ flat ∧ `_l2_gate_masks`), the post-breaker L1 entry set, strict force-close boundary, and `blocked_until` re-entry reproduction.
7. **Causality tests** replaced with a real input-truncation test (+ value-stability) instead of the tautological ones; audit reframed (causal-in-slicing vs in-values; warmup back-fill measured to move the threshold by 0).
8. **Frontend additivity**: combined keeps the 4 guardrail boxes, grays (not hides) the opposite layer's markers AND equity line, and ADDS the per-candle log table alongside the existing tables; both CSVs retained; before/after sample captured as a committed artifact before edits.

Deferred nice-to-haves (non-blocking, noted in tasks): combined `exposure` is a blended fill-rate (documented, not dropped); L2 no-entry taxonomy specifics; `#210` 1-min recompute perf is INHERITED not resolved (cache keeps the frozen path ~1s).
