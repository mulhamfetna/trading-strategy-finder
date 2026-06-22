# Flip Semantics → Reverse-Entry-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `flip=True` mean "reverse the entry direction only," after which the normal exit logic (`hard-SL > hard-TP > soft-SL`) applies to the entered direction — so logs/boxes read literally with no mental reversal.

**Architecture:** Delete the separate "flipped" exit branch in both engines (`engine.py`, `optimize/fast_engine.py`); keep only the entry-direction reversal. A flipped trade then becomes byte-identical to a normal trade on the reversed signal. Retire the two flip-dependent parity anchors (L2, combined) pending a fresh re-optimization; surface an "entry flipped" badge in the UI.

**Tech Stack:** Python 3 (stdlib + numpy + pandas), pytest, vanilla-JS frontend (`frontend/dashboard.html`, lightweight-charts).

**Spec:** `docs/superpowers/specs/2026-06-22-flip-semantics-reverse-entry-only-design.md`

## Global Constraints

- **L1 anchor must stay byte-identical:** `optimize/l2/test_parity_anchor.py::test_l1_anchor` = `149989` P/L · `255` trades · `15491` max DD. This is the guard that the change is surgical.
- **Engine math only changes for `flip=True`.** `flip=False` paths must be untouched (no normal-mode regression).
- **Both engines change together** so `optimize/test_fast_parity.py` (engine↔fast trade-for-trade) stays green.
- **No new dependencies.** Engine is stdlib+numpy+pandas only.
- **Commit per task.** Stage *specific* files only (never `git add -A` — the tree carries chmod noise). `*.html` is gitignored → use `git add -f` for `frontend/dashboard.html`.
- **Commit message footer:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Visuals = embedded Mermaid only**, never ASCII art.
- **Run commands from** `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.

---

### Task 1: Failing invariant + behavioral test for the new flip semantics

**Files:**
- Create: `optimize/test_flip_equivalence.py`

**Interfaces:**
- Consumes: `optimize.data.load_inputs(tf) -> (df, df1, box, vf, n)`; `optimize.signals.decision_signals(df, box)`; `optimize.fast_engine.{fast_backtest, signals_to_int}`; `engine.{SimpleStrategy, SimpleStrategyParams}`. (All already exist and are used identically in `optimize/test_fast_parity.py`.)
- Produces: the regression lock that Tasks 2–3 must turn green. Encodes the invariant `fast_backtest(flip=True, S) == fast_backtest(flip=False, ¬S)` trade-for-trade, plus the behavioral guard that a `flip=True` engine run produces normal-mode exit reasons.

- [ ] **Step 1: Write the failing test**

Create `optimize/test_flip_equivalence.py`:

```python
"""Invariant lock for the NEW flip semantics (spec 2026-06-22): flip = reverse entry direction ONLY,
then the normal exit logic (hard-SL > hard-TP > soft-SL) applies to the ENTERED direction.

Proves:
  (A) fast_backtest(flip=True, signal=S) == fast_backtest(flip=False, signal=¬S)  trade-for-trade.
  (B) an engine flip=True run yields normal-mode exit reasons: NO 'TAKE_PROFIT_SOFT', and soft
      stop-losses are live again (>=1 'STOP_LOSS_SOFT').
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data, signals  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int  # noqa: E402
from engine import SimpleStrategy, SimpleStrategyParams  # noqa: E402

_TF = "4h"
CASES = [(30, 40, 60, 60), (30, 40, 60, 0), (100, 160, 200, 50), (60, 120, 150, 70)]


@pytest.fixture(scope="module")
def inputs():
    df, df1, box, vf, n = data.load_inputs(_TF)
    sig = signals_to_int(signals.decision_signals(df, box))
    return df, df1, box, vf, n, sig


def _key(t):
    return (pd.Timestamp(t["entry_time"]), t["direction"], t["exit_reason"],
            pd.Timestamp(t["exit_time"]), round(float(t["pnl_points"]), 6))


@pytest.mark.parametrize("ss,sh,tp,gp", CASES)
def test_flip_equals_reversed_signal(inputs, ss, sh, tp, gp):
    df, df1, box, vf, n, sig = inputs
    DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
    MD = df1["Date"].to_numpy(); MH = df1["High"].to_numpy(float)
    ML = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float)
    gate = None if gp <= 0 else (vf <= float(np.percentile(vf[:n], gp)))
    flipped = fast_backtest(DD, DC, sig, gate, MD, MH, ML, MC, ss, sh, tp, True)
    reversed_ = fast_backtest(DD, DC, (-sig).astype(sig.dtype), gate, MD, MH, ML, MC, ss, sh, tp, False)
    assert len(flipped) == len(reversed_)
    assert [_key(t) for t in flipped] == [_key(t) for t in reversed_]


def test_flip_engine_uses_normal_exit_reasons(inputs):
    df, df1, box, *_ = inputs
    sp = SimpleStrategyParams(sl_soft_points=30, sl_hard_points=40, tp_soft_points=60,
                              tp_hard_points=60, data_path_4h="", data_path_1min="",
                              box_data_path="", flip_entry_direction=True)
    E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=None)
    reasons = [t.get("exit_reason") for t in E0]
    assert "TAKE_PROFIT_SOFT" not in reasons, "flip must no longer produce soft take-profits"
    assert reasons.count("STOP_LOSS_SOFT") >= 1, "soft stop-loss must be live again under flip"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest optimize/test_flip_equivalence.py -q`
Expected: **FAIL** — `test_flip_equals_reversed_signal` fails (old flip branch uses `hard-TP > hard-SL > soft-TP`, so trades/reasons differ from the reversed-signal normal run) and `test_flip_engine_uses_normal_exit_reasons` fails (old engine flip produces `TAKE_PROFIT_SOFT` and zero `STOP_LOSS_SOFT`).

- [ ] **Step 3: Commit the failing test**

```bash
git add optimize/test_flip_equivalence.py
git commit -m "test(engine): lock new flip semantics — flip=True(S) == flip=False(¬S) [RED]

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Remove the flip exit-branch in `fast_engine.py`

**Files:**
- Modify: `optimize/fast_engine.py:109,113,122-125` (and the inline comment at `:94`)

**Interfaces:**
- Consumes: the test from Task 1.
- Produces: `fast_backtest` with a single exit model. `soft_breach` always tests the soft-**SL** line; the candidate `order` is always `[(t_slh, R_SL_HARD), (t_tph, R_TP_HARD), (t_soft, R_SL_SOFT)]`. The `flip` arg now only affects entry direction (`d = -raw if flip else raw`, line 80 — unchanged).

- [ ] **Step 1: Edit the soft-breach lines**

Replace lines 109 and 113. **Old:**
```python
            soft_breach = (cl <= sls_line) if not flip else (cl >= tps_line)
```
```python
            soft_breach = (cl >= sls_line) if not flip else (cl <= tps_line)
```
**New** (respectively):
```python
            soft_breach = cl <= sls_line   # soft stop-loss (long); flip only reverses entry, not this
```
```python
            soft_breach = cl >= sls_line   # soft stop-loss (short); flip only reverses entry, not this
```

- [ ] **Step 2: Edit the candidate-priority assembly**

Replace lines 122–125. **Old:**
```python
        # assemble candidates with their priority, pick earliest (tie → priority order)
        if not flip:
            order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line), (t_soft, R_SL_SOFT, None)]
        else:
            order = [(t_tph, R_TP_HARD, tph_line), (t_slh, R_SL_HARD, slh_line), (t_soft, R_TP_SOFT, None)]
```
**New:**
```python
        # assemble candidates with their priority, pick earliest (tie → priority order).
        # Single exit model regardless of flip: hard-SL > hard-TP > soft-SL on the ENTERED direction.
        # `flip` only reverses entry (d = -raw above); it no longer swaps "soft" to the TP side.
        order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line), (t_soft, R_SL_SOFT, None)]
```

- [ ] **Step 3: Fix the now-stale inline comment at line 94**

**Old:**
```python
            sls_line, tps_line = ep - sls, ep + tpv           # soft on SL side (normal) / TP side (flip)
```
**New:**
```python
            sls_line, tps_line = ep - sls, ep + tpv           # soft-SL line used; tps_line kept (unused, == hard TP)
```
(Do **not** touch line 98 — the short-side mirror — its trailing comment is already neutral. `tps_line` stays computed but unused; harmless.)

- [ ] **Step 4: Run the engine↔fast parity script (both modes still consistent)**

Run: `python3 optimize/test_fast_parity.py 4h`
Expected: every line `OK`, final `FAST-PARITY OK ✓`, exit code 0. *(This passes only after Task 3 too if the engine flip case is exercised — but the script compares engine vs fast for the SAME params; the flip cases will now BOTH still need the engine edit. Expect the two flip cases to FAIL here and pass after Task 3. The non-flip cases must be OK now.)*

- [ ] **Step 5: Commit**

```bash
git add optimize/fast_engine.py
git commit -m "feat(engine): fast_engine flip = reverse-entry-only (drop soft-TP branch)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Remove the flip exit-branch in `engine.py`

**Files:**
- Modify: `engine.py:290-293` (docstring), `engine.py:319-362` (exit logic)

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: `SimpleStrategy._walk_exit_for_4h` with a single exit model identical to the old normal branch, applied to `d` (the entered/post-flip direction). The flip entry reversal at `engine.py:411` and the trade-dict `'flip'` field at `:516` are **unchanged**.

- [ ] **Step 1: Update the helper docstring (lines 290-293)**

**Old:**
```python
        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit
            on the currently open trade. Dispatches to the normal or
            flipped exit model based on `flip`."""
```
**New:**
```python
        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit on the currently open
            trade. Single exit model regardless of `flip`: hard-SL > hard-TP > soft-SL on the
            ENTERED direction. `flip` only reverses entry direction (see entry logic below)."""
```

- [ ] **Step 2: Replace the dual-branch exit logic (lines 319-362) with the single normal model**

**Old (319-362):**
```python
                if not flip:
                    # NORMAL mode: hard SL > hard TP > soft SL.
                    if d == 'long':
                        if m_low <= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_high >= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_close <= ss:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                    else:  # short
                        if m_high >= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_low <= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_close >= ss:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                else:
                    # FLIPPED mode: hard TP > hard SL > soft TP (Q-A: symmetric flip).
                    if d == 'long':
                        if m_high >= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_low <= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_close >= ts_:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'TAKE_PROFIT_SOFT', m_close
                    else:  # short
                        if m_low <= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_high >= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_close <= ts_:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'TAKE_PROFIT_SOFT', m_close
```
**New:**
```python
                # Single exit model (flip or not): hard-SL > hard-TP > soft-SL on the ENTERED
                # direction. `flip` only reverses entry direction; it no longer swaps "soft" to the
                # TP side. (ts_ stays computed at entry but unused — soft-TP is inactive, as before.)
                if d == 'long':
                    if m_low <= sh:
                        exit_reason, fill = 'STOP_LOSS_HARD', sh
                    elif m_high >= th:
                        exit_reason, fill = 'TAKE_PROFIT_HARD', th
                    elif m_close <= ss:
                        soft_consec_count += 1
                        resets_counter = False
                        if soft_consec_count >= 2:
                            exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                else:  # short
                    if m_high >= sh:
                        exit_reason, fill = 'STOP_LOSS_HARD', sh
                    elif m_low <= th:
                        exit_reason, fill = 'TAKE_PROFIT_HARD', th
                    elif m_close >= ss:
                        soft_consec_count += 1
                        resets_counter = False
                        if soft_consec_count >= 2:
                            exit_reason, fill = 'STOP_LOSS_SOFT', m_close
```

- [ ] **Step 3: Run the new invariant test → GREEN**

Run: `python3 -m pytest optimize/test_flip_equivalence.py -q`
Expected: **PASS** (4 parametrized equivalence cases + behavioral test).

- [ ] **Step 4: Run the engine↔fast parity script → all OK**

Run: `python3 optimize/test_fast_parity.py 4h`
Expected: every line `OK` (including the two flip cases now), `FAST-PARITY OK ✓`, exit 0.

- [ ] **Step 5: Verify L1 anchor is byte-identical (no normal-mode regression)**

Run: `python3 -m pytest optimize/l2/test_parity_anchor.py::test_l1_anchor optimize/l2/test_parity_anchor.py::test_frozen_default_guard optimize/l2/test_parity_anchor.py::test_run_l1_window_matches_build_payload -q`
Expected: **PASS** (L1 `149989/255/15491` unchanged; window + frozen-guard green).

- [ ] **Step 6: Commit**

```bash
git add engine.py
git commit -m "feat(engine): SimpleStrategy flip = reverse-entry-only (drop soft-TP branch)

flip=True(S) now == flip=False(¬S) trade-for-trade in both engines; soft stop-loss
is live again under flip. L1 anchor (149989/255/15491) byte-identical. Closes the
'impossible -5k' phantom: the orange soft-SL line is enforced again.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Retire the flip-dependent parity anchors (L2 + combined)

**Files:**
- Modify: `optimize/l2/test_parity_anchor.py:51-65` (mark `test_l2_anchor` + `test_combined_anchor` xfail)

**Interfaces:**
- Consumes: Task 3 (the L2 champion `l2v1_4h_champion.json` is `flip=true`, so its numbers now legitimately change).
- Produces: an honest test file — L1 still locked; L2/combined marked `xfail(strict=False)` with a reason pointing at the spec + the `l2v2` re-opt that will re-lock them.

- [ ] **Step 1: Add xfail markers**

Insert a marker line directly above each of the two test functions (`test_l2_anchor` at line 51, `test_combined_anchor` at line 59). **Old:**
```python
def test_l2_anchor(causal):
```
**New:**
```python
@pytest.mark.xfail(reason="flip semantics changed 2026-06-22 (reverse-entry-only); l2v1 champion is "
                          "flip=true so its $78,391/80/$8,961 numbers move. Re-lock after the l2v2 "
                          "re-optimization. See docs/superpowers/specs/2026-06-22-flip-semantics-"
                          "reverse-entry-only-design.md §5.", strict=False)
def test_l2_anchor(causal):
```
And **Old:**
```python
def test_combined_anchor(causal):
```
**New:**
```python
@pytest.mark.xfail(reason="depends on the L2 (flip=true) champion; combined $228,380/335/$20,303 move "
                          "with the 2026-06-22 flip-semantics change. Re-lock after l2v2 re-opt. See "
                          "the flip-semantics design spec §5.", strict=False)
def test_combined_anchor(causal):
```

- [ ] **Step 2: Run the anchor file**

Run: `python3 -m pytest optimize/l2/test_parity_anchor.py -q`
Expected: `test_l1_anchor`, `test_frozen_default_guard`, and the 6 window params **PASS**; `test_l2_anchor` + `test_combined_anchor` report **xfail** (not fail). Summary line shows `xfailed`.

- [ ] **Step 3: Run the broader L2 suite for collateral breakage**

Run: `python3 -m pytest optimize/l2/ -q`
Expected: green except the two expected xfails. If any *other* test hardcodes the old L2/combined numbers (e.g. `test_aggregate.py`, `test_logbook.py`, `test_payload.py`), note the failure and add the same xfail marker with the same reason — do **not** edit the expected numbers (they get re-locked after re-opt). Record any such file in the commit message.

- [ ] **Step 4: Commit**

```bash
git add optimize/l2/test_parity_anchor.py
git commit -m "test(l2): xfail L2+combined anchors pending l2v2 re-opt (flip semantics change)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: "Entry flipped" badge in the dashboard

**Files:**
- Modify: `frontend/dashboard.html` (CSS block near line 21; the per-layer summary/header render; the ledger `direction` cell renderer near lines 347-360)

**Interfaces:**
- Consumes: the per-run `flip` value already in the form (`#l1_flip` / `#l2_flip`, read at line 168 via `collectLayer`) and the `layer` column on each ledger row. `flip` is layer-global, so every entry in a flipped layer is the reverse of its box signal — the badge can be derived without engine plumbing.
- Produces: a visible `⇄ flipped` badge wherever a flipped layer's results are shown, with a tooltip explaining the box signaled the opposite direction.

- [ ] **Step 1: Locate the exact render anchors**

Run: `grep -nE "function render|summary|sumHTML|kpi|metaRow|function tbl|direction|collectLayer|requestFor|lastReq|state\." frontend/dashboard.html | head -40`
Identify (a) where a run's summary/header for a layer is built, and (b) the ledger row renderer (the `direction` column). Capture the variable that holds the current run's request/flip per layer (e.g. the object returned by `collectLayer`, or a stored `state`/`lastReq`). Record the precise variable names before editing.

- [ ] **Step 2: Add the badge CSS**

After line 22 (the `.layerbadge` rules), add:
```css
  .flipbadge{display:inline-block;margin-left:6px;padding:0 5px;border-radius:3px;font-size:11px;
    font-weight:700;color:#111;background:var(--orange);cursor:help;}
```

- [ ] **Step 3: Render the badge in the layer summary/header**

Where the layer summary/header HTML is assembled (from Step 1), append — when that layer's request `flip === true` — the span:
```js
`<span class="flipbadge" title="Entries are REVERSED from the box signal: a box short entered long, and vice-versa. SL/TP read normally for the entered direction.">⇄ flipped</span>`
```
Use the layer's own flip flag (L1 uses `#l1_flip`, L2 uses `#l2_flip`; for the Combined tab render the badge per layer it applies to).

- [ ] **Step 4: Annotate the ledger `direction` cell**

In the row renderer (near lines 347-360), for the `direction` column, when the row's layer was flipped this run, render the entered direction plus a derived box-signal hint:
```js
if(c[0]==='direction'){
  const opp = v==='long' ? 'short' : 'long';
  return flippedLayer ? `<td class="l">${v} <span class="flipbadge" title="box signaled ${opp} → entered ${v}">⇄</span></td>`
                      : `<td class="l">${v}</td>`;
}
```
where `flippedLayer` is computed from the row's `layer` value against the per-layer flip flags captured in Step 1. (If the existing renderer has no per-column hook for `direction`, add one alongside the `layer` branch at line 350/360.)

- [ ] **Step 5: Manual smoke test**

Run: `python3 server.py` (serves `http://localhost:8200/`), open the L2 tab (champion is `flip=true`), run a backtest. Confirm: the `⇄ flipped` badge appears in the L2 summary, the ledger `direction` cells show `long ⇄` / `short ⇄` with the tooltip, and the orange soft-SL line now produces `STOP_LOSS_SOFT` rows (no more `TAKE_PROFIT_SOFT`). Switch the Direction selector to `normal` and confirm the badge disappears. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add -f frontend/dashboard.html
git commit -m "feat(dash): 'entry flipped' badge — flip is now reverse-entry-only, shown to the reader

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Docs — update the flip rule everywhere + audit report

**Files:**
- Modify: `docs/VECTORIZATION.md:50`, `docs/WS-I_MEGADOC.md:173`, `MASTER.md` (flip dictionary entry)
- Create: `optimize/l2/REPORT_flip_semantics.md`

**Interfaces:**
- Consumes: the implemented change (Tasks 2–3).
- Produces: documentation consistent with the new single exit model; a committed audit/decision trail with a Mermaid before/after.

- [ ] **Step 1: Fix the engine-box doc lines**

In `docs/VECTORIZATION.md:50` and `docs/WS-I_MEGADOC.md:173`, replace the text `flip: TP/SL priority swapped, soft on the TP side.` with:
```
flip: reverses ENTRY direction only; exits use the normal model (hard-SL > hard-TP > soft-SL) on the entered direction.
```
(Preserve each file's surrounding box-drawing/indentation.)

- [ ] **Step 2: Update the `flip` dictionary entry in `MASTER.md`**

Find the `flip` term in the §5 dictionary (run `grep -n "flip" MASTER.md`). Set its definition to: *"`flip` — reverse the box signal's entry direction (long↔short). Exits then follow the normal model on the entered direction; soft = stop-loss. (Changed 2026-06-22 from the old 'soft swaps to TP side' rule — see `optimize/l2/REPORT_flip_semantics.md`.)"*

- [ ] **Step 3: Write the audit/decision report**

Create `optimize/l2/REPORT_flip_semantics.md` with: the problem (phantom soft-SL / "impossible −5k"), the old vs new rule (a Mermaid before/after — reuse the diagram from the spec §1), the invariant `flip=True(S) ≡ flip=False(¬S)`, the blast radius table (L1 safe; L2/combined retired pending `l2v2`; WS-I 1h/2h champion stats now **stale** → regenerate later), and the verification (`test_flip_equivalence.py`, `test_fast_parity.py`, L1 anchor green).

- [ ] **Step 4: Commit**

```bash
git add docs/VECTORIZATION.md docs/WS-I_MEGADOC.md MASTER.md optimize/l2/REPORT_flip_semantics.md
git commit -m "docs: flip = reverse-entry-only — update rule everywhere + audit report

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Final verification sweep + push

**Files:** none (verification + push)

- [ ] **Step 1: Full relevant test sweep**

Run:
```bash
python3 -m pytest optimize/test_flip_equivalence.py optimize/l2/test_parity_anchor.py -q
python3 optimize/test_fast_parity.py 4h
```
Expected: invariant tests PASS; L1 anchor + window + frozen-guard PASS; L2/combined xfailed; `FAST-PARITY OK ✓`.

- [ ] **Step 2: Confirm clean, intentional staging only**

Run: `git status --short` and `git log --oneline -6`. Confirm only the intended files changed (no chmod-noise sweep) and the six task commits are present.

- [ ] **Step 3: Push to `dev`**

Run: `git push origin dev`
Expected: fast-forward push of the task commits.

---

## Follow-on (separate workstream, NOT in this plan)

**`l2v2` re-optimization (user choice b).** Under the new semantics, re-run the L2 optimizer with a fresh prefix `l2v2` on the AMD/Postgres optimizer (`wsh-pg`) → new L2 champion `optimize/results/l2v2_4h_champion.json` → **re-lock** `test_l2_anchor` + `test_combined_anchor` with the new numbers (remove the xfail markers). Also regenerate the stale WS-I 1h/2h (`flip=true`) champion stats in `wsi_champions_full.json`. This is the heavy step teed up by §5 of the spec; launch it explicitly when ready.

## Self-Review

- **Spec coverage:** §1 change → Tasks 2,3. §2 approach (Option 1) → Tasks 2,3. §3 blast radius → Task 4 (anchors) + Task 6 (WS-I stale note). §4 tests → Tasks 1,3,4. §5 re-opt → Follow-on. §6 frontend+docs → Tasks 5,6. §7 out-of-scope respected (no 4-line-model change, no L1 touch). §8 order matches Tasks 1→7. ✓
- **Placeholder scan:** all code steps carry exact code; the only "locate" step (Task 5 Step 1) is an explicit grep to pin frontend variable names before concrete edits whose code is given. No TBD/TODO. ✓
- **Type consistency:** `fast_backtest` signature, `signals_to_int`, `SimpleStrategyParams` fields, exit-reason string literals (`STOP_LOSS_SOFT`/`TAKE_PROFIT_SOFT`), and the `_key` tuple match the existing code read from `test_fast_parity.py` and the engines. ✓
