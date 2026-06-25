# Optimizer cap_1min Search + wsh6/l2v3 Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `cap_1min` as a searched optimizer dimension (L1 + L2), then run `wsh6` (L1) and `l2v3` (L2) on 4h/non-split with doubled trials, exposing both champions as side-by-side dashboard presets.

**Architecture:** Add `trial.suggest_int("cap_1min", 0, 1440)` to the L1 `objective` and L2 `suggest_l2_params`; thread it through `core.backtest_metrics → fast_backtest` (the one missing wire); count it in `search_dims`; clamp it in the warm-start `_native_seed`. Run L1 then L2 (L2 scored on the wsh6 L1's residuals via an L1-params override). No production file is overwritten; golden stays green.

**Tech Stack:** Python 3 (Optuna NSGA-III, numpy/pandas), remote AMD/Postgres fleet via `remote_wsi.sh`.

## Global Constraints

- **Side-by-side, never overwrite.** `wsh6`/`l2v3` champions go to NEW result files + presets; frozen production L1/L2 and `perf/check_golden.py` stay ✅.
- **Decisions:** trials **double** (`--trials-per-dim 200`); `cap_1min` range **0..1440**; **bars** cap only; **4h non-split**; launched on the **remote** fleet.
- **`cap_1min=0` (off) must reproduce the prior champion exactly** — warm-start seeds it at 0.
- Interpreter `python3`; run from `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.
- Commit footer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task O1: Count cap_1min as a search dimension

**Files:** Modify `optimize/optimizer.py:128-137` (`search_dims`) + add a module constant · Test: `optimize/test_cap_search.py` (NEW)

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_cap_search.py
import sys
from pathlib import Path
_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from optimize import optimizer as OPT


def test_cap_1min_is_a_counted_dimension():
    assert OPT.CAP_1MIN_MAX == 1440
    d = OPT.search_dims(split_sltp=False)
    assert d["base_int"] == 3                      # cooldown, k, cap_1min
    assert d["total"] == sum(v for k, v in d.items() if k != "total")
    # doubled budget reflects the extra dim
    assert OPT.recommended_trials(False, per_dim=200) == d["total"] * 200
```

- [ ] **Step 2: Run → FAIL** `python3 -m pytest optimize/test_cap_search.py::test_cap_1min_is_a_counted_dimension -q` (AttributeError: CAP_1MIN_MAX / base_int==2)

- [ ] **Step 3: Implement.** Near the top of `optimize/optimizer.py` (by `DD_LIMIT_MAX`/`TRIALS_PER_DIM`) add:

```python
CAP_1MIN_MAX = 1440   # max searched max-hold in traded 1-min bars (~1 trading day); 0 = off
```

In `search_dims` (line 135) change `base_int=2` → `base_int=3` and update the docstring's "integer (cooldown, k)=2" → "(cooldown, k, cap_1min)=3".

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit** `git add optimize/optimizer.py optimize/test_cap_search.py && git commit -m "feat(opt): count cap_1min as a search dimension (CAP_1MIN_MAX=1440)" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`

---

### Task O2: Suggest cap_1min in the L1 objective + warm-start clamp

**Files:** Modify `optimize/optimizer.py:308-321` (`objective`), `:209-221` (`_native_seed`) · Test: `optimize/test_cap_search.py`

**Interfaces:** Produces — every L1 trial's params dict has `cap_1min: int`; `_native_seed(box, ...)` carries `cap_1min` (0 when absent).

- [ ] **Step 1: Write the failing test**

```python
def test_native_seed_carries_cap_1min():
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    box0 = {"sl_soft": 100, "sl_hard": 150, "tp": 120, "gate_pct": 0, "dd_limit": 0,
            "cooldown": 0, "flip": False, "k": 1}
    s0 = OPT._native_seed(box0, {}, split_sltp=False, b=b)
    assert s0["cap_1min"] == 0                                   # absent → 0 (reproduces prior champ)
    s1 = OPT._native_seed({**box0, "cap_1min": 5000}, {}, split_sltp=False, b=b)
    assert s1["cap_1min"] == OPT.CAP_1MIN_MAX                    # clamped to bound
```

- [ ] **Step 2: Run → FAIL** (`KeyError: 'cap_1min'`)

- [ ] **Step 3: Implement.** In `objective`, after the `k_rule = ...` line (318), add:

```python
        cap_1min = trial.suggest_int("cap_1min", 0, CAP_1MIN_MAX)
```

and add `cap_1min=cap_1min` to the `params = dict(...)` (line 319-321).

In `_native_seed`, add to the `seed = dict(...)` block (after `k=int(box["k"])`, line 220):

```python
        cap_1min=max(0, min(CAP_1MIN_MAX, int(box.get("cap_1min", 0)))),
```

- [ ] **Step 4: Run → PASS** (`python3 -m pytest optimize/test_cap_search.py -q`)

- [ ] **Step 5: Commit** `git add optimize/optimizer.py optimize/test_cap_search.py && git commit -m "feat(opt): L1 objective searches cap_1min + warm-start clamp" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`

---

### Task O3: Thread cap_1min through core.backtest_metrics → fast_backtest

**Files:** Modify `optimize/core.py:63-122` · Test: `optimize/test_cap_search.py`

**Interfaces:** Consumes — params dict may carry `cap_1min`. Produces — `backtest_metrics` honors it (TIME_CAP exits appear).

- [ ] **Step 1: Write the failing test**

```python
def test_backtest_metrics_honors_cap_1min():
    from optimize import core, data as data_mod, timeframes as TF
    from optimize.fast_engine import signals_to_int
    from optimize import signals as sig_mod
    df_dec, df1, box, vf, n_split = data_mod.load_inputs("4h")
    si = signals_to_int(sig_mod.decision_signals(df_dec, box))
    p = {"sl_soft": 149.8, "sl_hard": 178.4, "tp": 120.2, "gate_pct": 0, "dd_limit": 0,
         "cooldown": 0, "flip": False, "window": "full", "indicators": [], "k": 1,
         "ind_1min": False, "cap_1min": 5}                       # tight cap → many TIME_CAP exits
    m = core.backtest_metrics(df_dec, df1, box, vf, n_split, p, TF.get("4h").bar_td, sig_int=si)
    assert any(t.get("exit_reason") == "TIME_CAP" for t in m["trades"])
```

- [ ] **Step 2: Run → FAIL** (no TIME_CAP — cap not threaded)

- [ ] **Step 3: Implement.** In `backtest_metrics`, after the `_split = {...}` block (line 70), add:

```python
    cap_1min = int(params.get("cap_1min", 0) or 0)
```

and add `cap_1min=cap_1min` to the `fast_backtest(...)` call (the one ending `..., sl_soft, sl_hard, tp, flip, **_split)`):

```python
        sl_soft, sl_hard, tp, flip, cap_1min=cap_1min, **_split)
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit** `git add optimize/core.py optimize/test_cap_search.py && git commit -m "feat(opt): thread cap_1min through backtest_metrics → fast_backtest" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`

---

### Task O4: L2 searches cap_1min + run against a candidate L1

**Files:** Modify `optimize/l2/optimize.py:36-51` (`suggest_l2_params`), `:54-59` (`run` signature + L1 load) · Test: `optimize/test_cap_search.py`

**Interfaces:** Produces — `suggest_l2_params` returns `cap_1min`; `l2.optimize.run(..., l1_params=None)` scores L2 on `run_l1_cached(tf, params=l1_params)` when given.

- [ ] **Step 1: Write the failing test**

```python
def test_l2_suggest_includes_cap_1min():
    import optuna
    from optimize.l2 import optimize as L2O
    from indicators import library
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    fixed = {"sl_soft": 100.0, "sl_hard_delta": 20.0, "tp": 120.0, "gate_pct": 0.0,
             "dd_limit": 0.0, "cooldown": 0, "flip": False, "k": 1, "cap_1min": 90,
             **{f"en_{k}": False for k in library.REGISTRY}}
    t = optuna.trial.FixedTrial(fixed)
    p = L2O.suggest_l2_params(t, b, cap=10)
    assert p["cap_1min"] == 90
```

- [ ] **Step 2: Run → FAIL** (`KeyError: 'cap_1min'`)

- [ ] **Step 3: Implement.** In `suggest_l2_params`, after `k_rule = trial.suggest_int("k", 1, 5)` add:

```python
    cap_1min = trial.suggest_int("cap_1min", 0, OPT.CAP_1MIN_MAX)
```

and add `cap_1min=int(cap_1min)` to the returned `dict(...)`.

In `run(...)`, add a parameter `l1_params: dict | None = None` to the signature, and change the L1 load:

```python
    l1 = payload.run_l1_cached(tf) if l1_params is None else payload.run_l1_cached(tf, params=l1_params)
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit** `git add optimize/l2/optimize.py optimize/test_cap_search.py && git commit -m "feat(opt): L2 searches cap_1min + run against a candidate L1 (l1_params override)" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`

---

### Task O5: Regression gate (existing suites + golden)

**Files:** none (verification)

- [ ] **Step 1: Run the optimizer + engine suites + golden**

```bash
python3 -m pytest optimize/test_cap_search.py optimize/test_fast_parity.py -q 2>&1 | tail -3
python3 perf/check_golden.py 2>&1 | tail -2
```
Expected: all pass; `FAST-PARITY OK ✓`; `✅ ALL GOLDEN BASELINES MATCH` (cap-default path unchanged; no production file touched).

- [ ] **Step 2: Plan dry-run shows the new dimension + doubled budget**

```bash
python3 optimize/optimizer.py 4h --plan --auto-trials --trials-per-dim 200 2>&1 | tail -15
```
Expected: the plan prints `base_int=3` and a total-dim count one higher than before, with `trials = total × 200`.

- [ ] **Step 3: Commit (if any doc/notes)** — no code change; skip if nothing to add.

---

### Task R1: Launch the L1 round (wsh6) on the remote fleet

**Files:** none (operational). **Prereq:** O1–O5 committed + green.

- [ ] **Step 1: Confirm remote access + read the launcher**

```bash
cat remote_wsi.sh | sed -n '1,60p'        # confirm SSH host/env + the run subcommand + prefix var
```
Identify: the SSH target, how the study prefix is set (`WSH_PREFIX` / `--study-prefix`), and how `--trials-per-dim`/`--auto-trials` are passed. STOP and ask if no reachable remote.

- [ ] **Step 2: Dry-run the plan on the server (acceptance)**

Launch the server-side `--plan` for `wsh6`, 4h, non-split, `--trials-per-dim 200`; confirm the reported trial target (~10.6k) and that `cap_1min` is in the space. (Exact command per Step 1's reading of `remote_wsi.sh`.)

- [ ] **Step 3: Launch L1 wsh6 (background watchdog)**

Run the `remote_wsi.sh` run subcommand with `WSH_PREFIX=wsh6`, tf `4h`, non-split, `--auto-trials --trials-per-dim 200`, NSGA-III, warm-start on. It runs on the Postgres fleet to the trial target.

- [ ] **Step 4: Monitor to completion**

Poll trial count / Pareto progress (the script's status path). Acceptance: study `wsh6_4h` reaches the target trials with a feasible Pareto front; the warm-started champion (cap=0) is present (guarantees ≥ prior).

---

### Task R2: Extract wsh6 → run L2 (l2v3) against it → register presets

**Files:** Create `optimize/results/wsh6_champions_full.json`, `optimize/results/l2v3_4h_champion.json`; Modify `presets.py` (register both as importable presets)

- [ ] **Step 1: Extract the wsh6 L1 champion** via the existing report/extract path (`report_wsi.py` or the study→champion exporter) into `optimize/results/wsh6_champions_full.json`. Record its `cap_1min`.

- [ ] **Step 2: Launch L2 l2v3 against the wsh6 L1**

```bash
python3 -m optimize.l2.optimize --trials <2x-rec> --tf 4h --prefix l2v3   # with l1_params = wsh6 champion
```
(Use the `l1_params` override so L2 scores on the wsh6 residuals, NOT the frozen production L1.) Run to target; extract champion → `optimize/results/l2v3_4h_champion.json`.

- [ ] **Step 3: Register both as side-by-side dashboard presets** in `presets.py` (mirror how the existing one-click champions are listed — a `wshlean_*`-style entry for `wsh6` and an L2 profile entry for `l2v3`), so they appear selectable in the dashboard alongside the current presets. Do NOT touch `wsh_lean_4h_champion.json` or the production L2 default.

- [ ] **Step 4: Commit** `git add optimize/results/wsh6_champions_full.json optimize/results/l2v3_4h_champion.json presets.py && git commit -m "feat(opt): wsh6 (L1+cap) + l2v3 (L2+cap) champions as side-by-side presets" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`

---

### Task R3: Before/after report + dashboard check

**Files:** Create `docs/reports/2026-06-25-cap1min-wsh6-l2v3.md`

- [ ] **Step 1: Build the before/after table** — current champion vs `wsh6`/`l2v3` on full-period AND 2026 OOS: P/L, max-DD, win%, n_taken, and the chosen `cap_1min`. Note whether the cap improved PnL / shrank DD as intended.
- [ ] **Step 2: Golden re-confirm** `python3 perf/check_golden.py 2>&1 | tail -2` → still ✅ (no production overwrite).
- [ ] **Step 3: Dashboard check (Playwright/manual)** — both new presets load, populate the L1/L2 forms (incl. their cap_1min), and Run produces results. The old presets still work unchanged.
- [ ] **Step 4: Commit** the report.

---

## Completion

After R3, announce: "I'm using the finishing-a-development-branch skill to complete this work." and present merge/PR/keep options (work is on `dev`).
