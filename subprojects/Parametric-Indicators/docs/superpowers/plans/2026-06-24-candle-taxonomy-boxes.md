# Candle Taxonomy Boxes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-node counter "box" (count + dollars) for a complete candle-classification tree (L1 / L2 / Combined) on the dashboard, derived purely from the existing causal log.

**Architecture:** A new pure module `optimize/l2/taxonomy.py` computes flat count/dollar dicts from `CausalResult.log` (no engine touch). `payload.build_view_payload` attaches the dict under `meta.taxonomy`. `frontend/dashboard.html` renders a new "📊 Candle taxonomy" card group per tab using the existing `DB.card`/`grp` markup. Correctness is enforced by reconciliation-invariant tests; the golden gate proves no existing number moved.

**Tech Stack:** Python 3 (numpy, pandas, dataclasses), vanilla JS dashboard, pytest, Playwright (`/usr/bin/google-chrome-stable`).

## Global Constraints

- **No engine/behaviour change.** `engine.py`, `optimize/fast_engine.py`, `logbook.run_causal`, ledgers, and all existing box values stay byte-identical. `perf/check_golden.py` must report ✅ ALL MATCH after every compute/payload task.
- **Log-first only.** Every count/dollar derives from `result.log` rows. No re-running engines, no new engine fields.
- **Python interpreter is `python3`** (not `python`). Activate the venv if present: `[ -d .venv ] && source .venv/bin/activate`.
- **Run all commands from** `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.
- **Parity anchors (do not change):** L1 `n_taken=255`, `pnl≈149989`; L2 (l2v2) `n_taken=34`, `pnl≈25383`.
- **Field facts (from `logbook.py`):** every `LogRow.box_cause == cause[i]` ∈ {None(bar 0), `box_silence`, `vol_gated`, `vetoed`, `confirm<K`, `would_enter`}. L1 entry rows have `box_cause=="would_enter"`. Breaker-skipped rows have `reason=="breaker_locked"`. `l2_reason` ∈ {None, `entered`, `vol_gated`, `vetoed`, `confirm<K`, `passed`} and is set on exactly the bars L2 evaluated (L1's `vetoed∪vol_gated` drops while L1 flat). L2 force-close exit rows have `exit_reason=="L1-entry"`.
- **Dollar rule:** non-trading leaves carry count only; `passed_skipped` carries summed `would_be_pnl`; entered/exit leaves carry summed `pnl`.
- **Commit message footer:** end every commit with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task B0: `taxonomy.py` scaffold + L1 partition invariant

**Files:**
- Create: `optimize/l2/taxonomy.py`
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Consumes: `logbook.run_causal(l1_params, l2_params, tf) -> CausalResult` (has `.log`, `.n`); `payload.l1_default_params("4h")`, `payload.PERMISSIVE`.
- Produces: `taxonomy.taxonomy_l1(result) -> dict[str, dict]` where each value is `{"count": int}` or `{"count": int, "pnl": float}`, plus a top-level `"n_classified": int`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_taxonomy.py
"""Candle taxonomy boxes — counts + dollars derived strictly from the causal log."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import json
from optimize.l2 import logbook, payload, taxonomy

_TF = "4h"


def _l1_res():
    return logbook.run_causal(payload.l1_default_params(_TF), dict(payload.PERMISSIVE), _TF)


def test_l1_partition_covers_every_classified_bar():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    leaves = ["no_box_signal", "gate_rejected", "indicator_veto",
              "indicator_no_confirm", "passed_all_gates"]
    total = sum(t[k]["count"] for k in leaves)
    assert total == res.n - 1                 # bar 0 has cause None
    assert t["n_classified"] == res.n - 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_partition_covers_every_classified_bar -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.taxonomy'`

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/taxonomy.py
"""Candle-classification taxonomy boxes — per-node {count, pnl?} derived STRICTLY from the per-candle
causal log (CausalResult.log). No engine touch; additive instrumentation only.

L1 tree (partition by box_cause over all rows; bar 0 has cause None and is excluded):
  no_box_signal(box_silence) | gate_rejected(vol_gated) | indicator_veto(vetoed)
  | indicator_no_confirm(confirm<K) | passed_all_gates(would_enter)
The passed_all_gates bucket splits into entered / passed_skipped(breaker_locked) / passed_in_position.
entered's trades split by exit_reason; TIME_CAP splits into win/loss.
"""
from __future__ import annotations


def _box(count, pnl=None):
    return {"count": int(count)} if pnl is None else {"count": int(count), "pnl": round(float(pnl), 2)}


def taxonomy_l1(result) -> dict:
    log = result.log

    def cnt(pred):
        return sum(1 for r in log if pred(r))

    no_box_signal = cnt(lambda r: r.box_cause == "box_silence")
    gate_rejected = cnt(lambda r: r.box_cause == "vol_gated")
    indicator_veto = cnt(lambda r: r.box_cause == "vetoed")
    indicator_no_confirm = cnt(lambda r: r.box_cause == "confirm<K")
    passed_all_gates = cnt(lambda r: r.box_cause == "would_enter")

    out = {
        "no_box_signal": _box(no_box_signal),
        "gate_rejected": _box(gate_rejected),
        "indicator_veto": _box(indicator_veto),
        "indicator_no_confirm": _box(indicator_no_confirm),
        "passed_all_gates": _box(passed_all_gates),
        "n_classified": int(result.n - 1),
    }
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_partition_covers_every_classified_bar -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(taxonomy): L1 partition buckets + n_classified invariant

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B1: L1 `passed_all_gates` sub-split (entered / passed_skipped / passed_in_position)

**Files:**
- Modify: `optimize/l2/taxonomy.py` (extend `taxonomy_l1`)
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Produces: `taxonomy_l1` now also returns `entered` (count+pnl), `passed_skipped` (count+would_be_pnl), `passed_in_position` (count).

- [ ] **Step 1: Write the failing test**

```python
def test_l1_passed_branch_splits_and_reconciles():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    # entered anchors to the known parity numbers
    assert t["entered"]["count"] == 255
    assert round(t["entered"]["pnl"]) == 149989
    # the three sub-buckets exactly partition passed_all_gates
    assert (t["entered"]["count"] + t["passed_skipped"]["count"]
            + t["passed_in_position"]["count"]) == t["passed_all_gates"]["count"]
    # passed_skipped carries counterfactual would-be $ (key present)
    assert "pnl" in t["passed_skipped"]
    assert "pnl" not in t["passed_in_position"]   # count-only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_passed_branch_splits_and_reconciles -q`
Expected: FAIL with `KeyError: 'entered'`

- [ ] **Step 3: Write minimal implementation**

Insert into `taxonomy_l1`, before the `out = {...}` return, after `passed_all_gates` is computed:

```python
    l1_entries = [r for r in log if r.layer == "L1" and r.decision == "entry"]
    entered = len(l1_entries)
    entered_pnl = sum(r.pnl for r in l1_entries)

    skipped_rows = [r for r in log if r.reason == "breaker_locked"]   # would_enter & flat, breaker/cooldown
    passed_skipped = len(skipped_rows)
    skipped_pnl = sum((r.would_be_pnl or 0.0) for r in skipped_rows)

    passed_in_position = passed_all_gates - entered - passed_skipped  # would_enter while a trade was open
```

and add these three keys to the `out` dict (before `"n_classified"`):

```python
        "entered": _box(entered, entered_pnl),
        "passed_skipped": _box(passed_skipped, skipped_pnl),
        "passed_in_position": _box(passed_in_position),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_passed_branch_splits_and_reconciles -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(taxonomy): L1 passed-gates split (entered/skipped/in-position) + reconcile

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B2: L1 exit leaves + TIME_CAP win/loss

**Files:**
- Modify: `optimize/l2/taxonomy.py` (extend `taxonomy_l1`)
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Produces: `taxonomy_l1` now also returns `tp_exit`, `sl_soft_exit`, `sl_hard_exit`, `time_cap_exit`, `time_cap_win`, `time_cap_loss` (all count+pnl).

- [ ] **Step 1: Write the failing test**

```python
def test_l1_exit_leaves_partition_entries_and_timecap_winloss():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    exits = ["tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit"]
    assert sum(t[k]["count"] for k in exits) == t["entered"]["count"]
    assert round(sum(t[k]["pnl"] for k in exits), 2) == t["entered"]["pnl"]
    # TIME_CAP win/loss partition the TIME_CAP bucket
    assert t["time_cap_win"]["count"] + t["time_cap_loss"]["count"] == t["time_cap_exit"]["count"]
    assert round(t["time_cap_win"]["pnl"] + t["time_cap_loss"]["pnl"], 2) == t["time_cap_exit"]["pnl"]
    assert all(r >= 0 for r in [t["time_cap_win"]["pnl"]] if t["time_cap_win"]["count"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_exit_leaves_partition_entries_and_timecap_winloss -q`
Expected: FAIL with `KeyError: 'tp_exit'`

- [ ] **Step 3: Write minimal implementation**

Add a module-level helper after `_box`:

```python
_EXIT_KEYS = {"TAKE_PROFIT_HARD": "tp_exit", "STOP_LOSS_SOFT": "sl_soft_exit",
              "STOP_LOSS_HARD": "sl_hard_exit", "TIME_CAP": "time_cap_exit"}


def _exit_boxes(entries: list) -> dict:
    """{tp_exit, sl_soft_exit, sl_hard_exit, time_cap_exit, time_cap_win, time_cap_loss} from entry rows."""
    out = {v: _box(0, 0.0) for v in _EXIT_KEYS.values()}
    agg = {k: [0, 0.0] for k in _EXIT_KEYS}
    tcw = [0, 0.0]
    tcl = [0, 0.0]
    for r in entries:
        k = r.exit_reason
        if k in agg:
            agg[k][0] += 1
            agg[k][1] += r.pnl
        if k == "TIME_CAP":
            (tcw if r.pnl > 0 else tcl)[0] += 1
            (tcw if r.pnl > 0 else tcl)[1] += r.pnl
    for k, name in _EXIT_KEYS.items():
        out[name] = _box(agg[k][0], agg[k][1])
    out["time_cap_win"] = _box(tcw[0], tcw[1])
    out["time_cap_loss"] = _box(tcl[0], tcl[1])
    return out
```

Then in `taxonomy_l1`, merge the exit boxes into `out` before returning (the `l1_entries` list already exists from B1):

```python
    out.update(_exit_boxes(l1_entries))
```

(Place `out.update(...)` after the `out = {...}` literal and before `return out`. Move `return out` to the end.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l1_exit_leaves_partition_entries_and_timecap_winloss -q`
Expected: PASS

- [ ] **Step 5: Run the golden gate (no existing number moved)**

Run: `python3 perf/check_golden.py 2>&1 | tail -3`
Expected: `✅ ALL GOLDEN BASELINES MATCH — results unchanged.`

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(taxonomy): L1 exit leaves + TIME_CAP win/loss split

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B3: L2 tree + universe reconciliation

**Files:**
- Modify: `optimize/l2/taxonomy.py` (add `taxonomy_l2`)
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Consumes: `_exit_boxes` (from B2); the L2 champion at `optimize/results/l2v2_4h_champion.json`.
- Produces: `taxonomy.taxonomy_l2(result) -> dict` with keys `l2_evaluated`, `gate_rejected`, `indicator_veto`, `indicator_no_confirm`, `passed_no_open`, `entered`, the exit leaves (incl `l1_entry_exit`), and `forwarded_but_l1_in_position`.

- [ ] **Step 1: Write the failing test**

```python
def _l2_res():
    champ = json.load(open(str(_PI / "optimize/results/l2v2_4h_champion.json")))["params"]
    return logbook.run_causal(payload.l1_default_params(_TF), champ, _TF)


def test_l2_tree_partitions_and_reconciles_to_l1_drops():
    res = _l2_res()
    t = taxonomy.taxonomy_l2(res)
    # L2 entered anchors to the l2v2 parity number
    assert t["entered"]["count"] == 34
    # L2 decision partition sums to evaluated
    parts = ["gate_rejected", "indicator_veto", "indicator_no_confirm", "passed_no_open", "entered"]
    assert sum(t[k]["count"] for k in parts) == t["l2_evaluated"]["count"]
    # exits partition entered (L2 has the extra L1-entry force-close leaf)
    exits = ["tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit", "l1_entry_exit"]
    assert sum(t[k]["count"] for k in exits) == t["entered"]["count"]
    # universe reconciles to L1's forwarded vetoed+vol_gated drops
    l1_drops = sum(1 for r in res.log if r.box_cause in ("vetoed", "vol_gated"))
    assert t["l2_evaluated"]["count"] + t["forwarded_but_l1_in_position"]["count"] == l1_drops
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l2_tree_partitions_and_reconciles_to_l1_drops -q`
Expected: FAIL with `AttributeError: module 'optimize.l2.taxonomy' has no attribute 'taxonomy_l2'`

- [ ] **Step 3: Write minimal implementation**

Append to `optimize/l2/taxonomy.py`:

```python
_L2_REASON = {"vol_gated": "gate_rejected", "vetoed": "indicator_veto",
              "confirm<K": "indicator_no_confirm", "passed": "passed_no_open", "entered": "entered"}


def taxonomy_l2(result) -> dict:
    log = result.log
    l2_entries = [r for r in log if r.layer == "L2" and r.decision == "entry"]

    out = {name: _box(0) for name in ("gate_rejected", "indicator_veto",
                                      "indicator_no_confirm", "passed_no_open")}
    parts = {k: 0 for k in _L2_REASON}
    for r in log:
        if r.l2_reason in parts:
            parts[r.l2_reason] += 1
    for reason, name in _L2_REASON.items():
        if name == "entered":
            continue
        out[name] = _box(parts[reason])

    entered_pnl = sum(r.pnl for r in l2_entries)
    out["entered"] = _box(len(l2_entries), entered_pnl)
    out["l2_evaluated"] = _box(sum(parts.values()))

    exits = _exit_boxes(l2_entries)
    fc = [r for r in l2_entries if r.exit_reason == "L1-entry"]
    exits["l1_entry_exit"] = _box(len(fc), sum(r.pnl for r in fc))
    out.update(exits)

    l1_drops = sum(1 for r in log if r.box_cause in ("vetoed", "vol_gated"))
    out["forwarded_but_l1_in_position"] = _box(l1_drops - out["l2_evaluated"]["count"])
    out["n_classified"] = int(out["l2_evaluated"]["count"])
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_l2_tree_partitions_and_reconciles_to_l1_drops -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(taxonomy): L2 tree (l2_reason partition + L1-entry exit) + universe reconcile

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B4: Combined taxonomy (additive roll-up)

**Files:**
- Modify: `optimize/l2/taxonomy.py` (add `taxonomy_combined`)
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Produces: `taxonomy.taxonomy_combined(result) -> {"l1": <l1 dict>, "l2": <l2 dict>, "combined_exits": {leaf: {count, pnl}}}`.

- [ ] **Step 1: Write the failing test**

```python
def test_combined_exits_are_additive_over_layers():
    res = _l2_res()
    t = taxonomy.taxonomy_combined(res)
    l1, l2 = t["l1"], t["l2"]
    for k in ("tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit",
              "time_cap_win", "time_cap_loss", "entered"):
        assert t["combined_exits"][k]["count"] == l1[k]["count"] + l2[k]["count"]
        assert round(t["combined_exits"][k]["pnl"], 2) == round(l1[k]["pnl"] + l2[k]["pnl"], 2)
    # L1-entry force-close exists only on L2 → combined == L2's
    assert t["combined_exits"]["l1_entry_exit"]["count"] == l2["l1_entry_exit"]["count"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_combined_exits_are_additive_over_layers -q`
Expected: FAIL with `AttributeError: ... has no attribute 'taxonomy_combined'`

- [ ] **Step 3: Write minimal implementation**

Append to `optimize/l2/taxonomy.py`:

```python
_COMBINED_LEAVES = ("entered", "tp_exit", "sl_soft_exit", "sl_hard_exit",
                    "time_cap_exit", "time_cap_win", "time_cap_loss", "l1_entry_exit")


def taxonomy_combined(result) -> dict:
    l1 = taxonomy_l1(result)
    l2 = taxonomy_l2(result)
    comb = {}
    for k in _COMBINED_LEAVES:
        a = l1.get(k, {"count": 0, "pnl": 0.0})
        b = l2.get(k, {"count": 0, "pnl": 0.0})
        comb[k] = _box(a["count"] + b["count"], a.get("pnl", 0.0) + b.get("pnl", 0.0))
    return {"l1": l1, "l2": l2, "combined_exits": comb}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_combined_exits_are_additive_over_layers -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(taxonomy): combined view = L1 + L2 sub-trees + additive exit roll-up

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B5: Wire `taxonomy` into the view payload

**Files:**
- Modify: `optimize/l2/payload.py:355-366` (L1-unified path) and `optimize/l2/payload.py:411-414` (general path)
- Test: `optimize/l2/test_payload.py`

**Interfaces:**
- Consumes: `taxonomy.taxonomy_l1/_l2/_combined`.
- Produces: every view payload has `meta.taxonomy` (L1/L2 → flat dict; combined → `{l1, l2, combined_exits}`).

- [ ] **Step 1: Write the failing test**

Add to `optimize/l2/test_payload.py`:

```python
def test_view_payload_carries_taxonomy():
    from optimize.l2 import payload
    p = payload.build_view_payload(payload.l1_default_params("4h"), dict(payload.PERMISSIVE),
                                   "4h", view="l1")
    tax = p["meta"]["taxonomy"]
    assert tax["entered"]["count"] == 255
    assert tax["n_classified"] == p["meta"]["n"] - 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_payload.py::test_view_payload_carries_taxonomy -q`
Expected: FAIL with `KeyError: 'taxonomy'`

- [ ] **Step 3: Write minimal implementation**

In `optimize/l2/payload.py`, line 350 import block, add `taxonomy`:

```python
    from optimize.l2 import logbook, aggregate, charts, taxonomy  # inline: avoid circular import
```

In the L1-unified path (after `base["meta"]["boxes"] = ...` near line 363), add:

```python
        base["meta"]["taxonomy"] = taxonomy.taxonomy_l1(res)
```

In the general-path return `meta` dict (line 412), add a `taxonomy` key:

```python
        "meta": {"view": view, "n": res.n, "boxes": boxes,
                 "taxonomy": (taxonomy.taxonomy_combined(res) if view == "combined"
                              else taxonomy.taxonomy_l2(res) if view == "l2"
                              else taxonomy.taxonomy_l1(res)),
                 "dropped_counts": {"veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                                    "total": len(ds), "flat_candidates": len(ds.flat_candidates())}},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_payload.py::test_view_payload_carries_taxonomy -q`
Expected: PASS

- [ ] **Step 5: Run full L2 suite + golden**

Run: `python3 -m pytest optimize/l2/ -q 2>&1 | tail -3 && python3 perf/check_golden.py 2>&1 | tail -2`
Expected: all pass; `✅ ALL GOLDEN BASELINES MATCH`

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_payload.py
git commit -m "feat(taxonomy): attach meta.taxonomy to every view payload

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B6: Dashboard card group (3 tabs)

**Files:**
- Modify: `frontend/dashboard.html` (add `boxesTaxonomy`; append it at the render site line 317)
- Test: manual + Playwright (Task B7)

**Interfaces:**
- Consumes: `D.meta.taxonomy` (shape per view, from B5). `DB.card(value, label, cls)` → `<div class="card"><div class="v cls">value</div><div class="k">label</div></div>`; `grp(title)` → `<div class="cardgrp">title</div>`; `DB.money(n)`.

- [ ] **Step 1: Add the taxonomy renderer**

In `frontend/dashboard.html`, after `boxesCombined` (line ~290), add. The dollar is shown in the label (no CSS change needed); count is the card value:

```javascript
// ── candle taxonomy (count + $) — flat L1/L2 dict, or combined {l1,l2,combined_exits} ──────────
function _txCard(node, label){ if(!node) return DB.card('—', label);
  const d = (node.pnl!==undefined) ? (' · '+DB.money(node.pnl)) : '';
  const cls = (node.pnl!==undefined) ? (node.pnl>=0?'pos':'neg') : '';
  return DB.card((node.count||0).toLocaleString(), label+d, cls); }
function _txL1(t, pfx){ return (
  grp(pfx+' — every candle')+
  _txCard(t.no_box_signal,'no box signal')+
  _txCard(t.gate_rejected,'box signal · gate-rejected')+
  _txCard(t.indicator_veto,'box signal · indicator veto')+
  _txCard(t.indicator_no_confirm,'box signal · no confirm (<K)')+
  _txCard(t.passed_all_gates,'box signal · passed all gates')+
  grp(pfx+' — passed gates ▸')+
  _txCard(t.entered,'entered (trade)')+
  _txCard(t.passed_skipped,'passed · skipped (breaker/cooldown)')+
  _txCard(t.passed_in_position,'passed · already in position')+
  grp(pfx+' — entered ▸ exits')+
  _txCard(t.tp_exit,'take-profit')+
  _txCard(t.sl_soft_exit,'stop-loss soft')+
  _txCard(t.sl_hard_exit,'stop-loss hard')+
  _txCard(t.time_cap_exit,'time-cap (max hold)')+
  grp(pfx+' — time-cap ▸ win/loss')+
  _txCard(t.time_cap_win,'time-cap win')+
  _txCard(t.time_cap_loss,'time-cap loss')); }
function _txL2(t){ return (
  grp('🔁 L2 — of L1’s forwarded drops')+
  _txCard(t.l2_evaluated,'evaluated by L2')+
  _txCard(t.gate_rejected,'gate-rejected')+
  _txCard(t.indicator_veto,'indicator veto')+
  _txCard(t.indicator_no_confirm,'no confirm (<K)')+
  _txCard(t.passed_no_open,'passed · no open')+
  _txCard(t.forwarded_but_l1_in_position,'forwarded · L1 in position')+
  grp('🔁 L2 — entered ▸ exits')+
  _txCard(t.entered,'entered (trade)')+
  _txCard(t.tp_exit,'take-profit')+
  _txCard(t.sl_soft_exit,'stop-loss soft')+
  _txCard(t.sl_hard_exit,'stop-loss hard')+
  _txCard(t.time_cap_exit,'time-cap (max hold)')+
  _txCard(t.l1_entry_exit,'L1-entry force-close')+
  grp('🔁 L2 — time-cap ▸ win/loss')+
  _txCard(t.time_cap_win,'time-cap win')+
  _txCard(t.time_cap_loss,'time-cap loss')); }
function boxesTaxonomy(tax, view){ if(!tax) return '';
  if(view==='l1') return _txL1(tax,'🍃 L1');
  if(view==='l2') return _txL2(tax);
  const ce=tax.combined_exits||{};
  return _txL1(tax.l1||{},'🍃 L1')+_txL2(tax.l2||{})+
    grp('Σ combined — entered ▸ exits (L1+L2)')+
    _txCard(ce.entered,'entered (trade)')+
    _txCard(ce.tp_exit,'take-profit')+
    _txCard(ce.sl_soft_exit,'stop-loss soft')+
    _txCard(ce.sl_hard_exit,'stop-loss hard')+
    _txCard(ce.time_cap_exit,'time-cap (max hold)')+
    _txCard(ce.l1_entry_exit,'L1-entry force-close')+
    _txCard(ce.time_cap_win,'time-cap win')+
    _txCard(ce.time_cap_loss,'time-cap loss'); }
```

- [ ] **Step 2: Append the group at the render site**

In `frontend/dashboard.html` line 317, change:

```javascript
  $('cards').innerHTML = view==='l1'?boxesL1(b):view==='l2'?boxesL2(b,dc,tr):boxesCombined(b);
```

to:

```javascript
  $('cards').innerHTML = (view==='l1'?boxesL1(b):view==='l2'?boxesL2(b,dc,tr):boxesCombined(b))
    + boxesTaxonomy(D.meta.taxonomy, view);
```

- [ ] **Step 3: Manual smoke (server + curl payload key present)**

```bash
pkill -f "server.py --port 8200" 2>/dev/null; true
```

```bash
nohup python3 server.py --port 8200 >/tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/srv.log 2>&1 & disown
```

Then verify the page loads (HTTP 200):

```bash
sleep 3; curl -s -o /dev/null -w "HTTP %{code}\n" http://localhost:8200/
```

Expected: `HTTP 200`. (Full UI assertion happens in B7.)

- [ ] **Step 4: Commit**

```bash
git add frontend/dashboard.html
git commit -m "feat(taxonomy): dashboard candle-taxonomy card group (L1/L2/combined tabs)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task B7: Browser verification (Playwright, all three tabs)

**Files:**
- Create: `/tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/verify_taxonomy.cjs`
- Modify: none (verification only)

**Interfaces:**
- Consumes: a running server on `:8200` (from B6 Step 3) and `VIEWS[v].meta.taxonomy` populated after a Run.

- [ ] **Step 1: Write the verification script**

```javascript
// verify_taxonomy.cjs
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome-stable' });
  const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://localhost:8200/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForFunction(() => typeof VIEWS !== 'undefined' && document.querySelector('#run'), { timeout: 30000 });
  await p.click('#run');
  await p.waitForFunction(() => VIEWS.l1 && VIEWS.l2 && VIEWS.combined, { timeout: 180000 });
  // assert the card group exists and a sentinel number matches the payload
  const res = await p.evaluate(() => {
    const tax = VIEWS.l1.meta.taxonomy;
    const cardsText = document.querySelector('#cards').innerText;
    return {
      hasGroup: cardsText.includes('every candle'),
      entered: tax.entered.count,
      enteredShown: cardsText.includes(tax.entered.count.toLocaleString()),
      nClassified: tax.n_classified,
      n: VIEWS.l1.meta.n,
    };
  });
  console.log('taxonomy check:', JSON.stringify(res));
  console.log('pageerrors:', errs.length ? JSON.stringify(errs) : 'none');
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(2); });
```

- [ ] **Step 2: Run it**

```bash
node /tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/verify_taxonomy.cjs
```

Expected: `taxonomy check: {"hasGroup":true,"entered":255,"enteredShown":true,"nClassified":...,"n":...}` with `nClassified == n-1`, and `pageerrors: none`.

- [ ] **Step 3: Stop the server**

```bash
pkill -f "server.py --port 8200" 2>/dev/null; true
```

- [ ] **Step 4: Commit (verification note only — no source change; skip if nothing to add)**

No commit required unless the script revealed a fix.

---

### Task B8: Docs + golden re-confirm

**Files:**
- Modify: `docs/LOG_FIELDS.md`, `docs/PNL_EXPLAINED.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Document the taxonomy in `docs/LOG_FIELDS.md`**

Append a section after the TIME_CAP section:

```markdown
## Candle taxonomy boxes (2026-06-24)

A per-node counter set classifies every candle, derived purely from this log (no engine change).
L1 partitions all bars (except bar 0) by `box_cause`:
`no_box_signal(box_silence) | gate_rejected(vol_gated) | indicator_veto(vetoed) |
indicator_no_confirm(confirm<K) | passed_all_gates(would_enter)`. The `passed_all_gates` bucket
splits into `entered` (a trade), `passed_skipped` (`reason==breaker_locked`), and
`passed_in_position` (a qualified signal while a trade was already open). `entered` trades split by
`exit_reason` (tp/sl-soft/sl-hard/time-cap), and TIME_CAP splits win/loss. L2 mirrors this from its
own `l2_reason` over the L1 drops it was forwarded (`vetoed∪vol_gated`, L1-flat), adding the
`l1_entry_exit` force-close leaf and a `forwarded_but_l1_in_position` reconciliation box. Each box
carries a count; trading leaves also carry summed $ (realized; `passed_skipped` uses `would_be_pnl`).
Computed in `optimize/l2/taxonomy.py`, surfaced at `meta.taxonomy`, rendered as the
"📊 Candle taxonomy" dashboard group. Invariants locked in `optimize/l2/test_taxonomy.py`.
```

- [ ] **Step 2: Add a one-line pointer in `docs/PNL_EXPLAINED.md`**

After the TIME_CAP note paragraph, add:

```markdown
The dashboard's "📊 Candle taxonomy" boxes classify every candle (count + $) straight from this
log — see `docs/LOG_FIELDS.md` § Candle taxonomy boxes and `optimize/l2/taxonomy.py`.
```

- [ ] **Step 3: Final gate — full L2 suite + golden**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py optimize/l2/test_payload.py optimize/l2/test_aggregate.py -q 2>&1 | tail -3 && python3 perf/check_golden.py 2>&1 | tail -2`
Expected: all pass; `✅ ALL GOLDEN BASELINES MATCH`

- [ ] **Step 4: Commit**

```bash
git add docs/LOG_FIELDS.md docs/PNL_EXPLAINED.md
git commit -m "docs(taxonomy): document candle taxonomy boxes + log derivation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Completion

After B8, announce: "I'm using the finishing-a-development-branch skill to complete this work." and present the merge/PR/keep options (work is on `dev`).
