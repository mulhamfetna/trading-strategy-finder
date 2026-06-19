# L2 Optimizer (round 1, option-3 validation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `optimize/l2/optimize.py` — an NSGA-III optimizer that searches L2 profiles over the frozen L1's dropped signals, scored **full-period in-sample (2025) with an OOS holdout (2026)** (option-3 validation), persisted under a new study prefix `l2v1`; then a tiny local smoke run, gating the heavy server run.

**Architecture:** Reuse the existing `optimize/optimizer.py` machinery (NSGA-III sampler, indicator search space, DD≤25%·P/L feasibility constraint, Optuna RDB store) but swap the objective: instead of L1 walk-forward, score the **standalone L2 book** via cached `run_l1` + `run_l2` + `metrics.score`, restricted to a bar window. In-sample = 2025 (`bars [0, n_split)`), OOS = 2026 (`bars [n_split, N)`); the OOS slice is scored only **after** the search (analysis), per spec §7. One additive change to `engine.run_l2` (a `bar_mask`) makes windowing clean.

**Tech Stack:** Python 3, Optuna (NSGA-III), the built `optimize/l2/` package (`l1_runner`, `engine`, `metrics`, `payload`), `optimize/optimizer.py` helpers, `optimize/storage.py`, pytest.

## Global Constraints

- **L1 frozen / golden:** no edits to `engine.py` (the root L1 engine), `optimize/fast_engine.py`, `optimize/core.py`, `indicators/*`. `python3 perf/check_golden.py` must print **6/6 MATCH** after every task (run from subproject root `/mnt/data/projects/trading/subprojects/Parametric-Indicators`). Only `optimize/l2/*` is touched.
- **Validation = option 3 (full-period + OOS holdout).** In-sample = 2025 = `bars [0, n_split)`; OOS = 2026 = `bars [n_split, N)` (`n_split` from `run_l1_cached("4h").n_split`, = 1534 on the current bundle, N=2119). OOS is scored **after** the search only.
- **Objective (3, all maximised):** `(in-sample L2 P/L, −in-sample L2 max_dd, in-sample L2 win-rate)` with the **DD ≤ 25%·P/L** feasibility constraint (`OPT.DD_PNL_CAP = 0.25`), computed on the **standalone L2 book**. (No "median fold" — single in-sample window.)
- **`min_trades` floor:** prune any trial whose in-sample L2 trade count `< min_trades` (default **5**; revisit if too strict on the sparse set).
- **Search space (spec §7):** L2 indicator subset + per-indicator params + `k`; `gate_pct ∈ [0,100]`; `sl_soft`/`sl_hard`(=sl_soft+delta)/`tp` from the 4h bounds (`OPT._BOUNDS`); `dd_limit ∈ [0, OPT.DD_LIMIT_MAX]`; `cooldown ∈ [0, cap]`; `flip ∈ {False,True}`. Indicators evaluated on the **1-minute frame** (`ind_1min=True`, matching the lean L1 regime). Direction is indicator/flip-driven (implicit reverse).
- **Study isolation:** prefix **`l2v1`**, study name `l2v1_4h`. Postgres for the real run (`WSH_STORAGE_URL`), sqlite for local smoke. **Never reuse an L1 prefix.**
- **Timeframe: 4h only.**
- **Server run is GATED:** build + a tiny *local* sqlite smoke only; the heavy `l2v1` Postgres/server study launches on the user's explicit go.
- **Commit only at the step that says so; stage explicitly by path** (never `git add -A`). Branch `dev`. Never stage repo-root secrets, `notes.md`, `frontend/data.js`, or the pre-existing modified files.

---

### Task 1: `engine.run_l2` — add `bar_mask` windowing

**Files:**
- Modify: `optimize/l2/engine.py` (`run_l2` signature + gate)
- Test: `optimize/l2/test_engine.py` (append)

**Interfaces:**
- Consumes: existing `run_l2(l1, l2_params)`.
- Produces: `run_l2(l1, l2_params, bar_mask=None) -> L2Result` — when `bar_mask` (per-decision-bar bool, length N) is given, L2 may open **only** where `bar_mask` is True (AND-ed into the gate). Default `None` ⇒ unchanged behaviour.

- [ ] **Step 1: Write the failing test (append to `test_engine.py`)**

```python
def test_run_l2_bar_mask_restricts_entries_to_window():
    r = l1_runner.run_l1("4h")
    n = len(r.df_dec)
    cut = r.n_split                       # 2025 / 2026 split
    import numpy as np
    in_mask = np.zeros(n, dtype=bool); in_mask[:cut] = True
    permissive = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
                  "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}
    full = engine.run_l2(r, dict(permissive))
    win = engine.run_l2(r, dict(permissive), bar_mask=in_mask)
    assert all(int(t["entry_idx"]) < cut for t in win.ledger), "windowed L2 opened outside the mask"
    assert len(win.ledger) <= len(full.ledger)
    assert len(win.ledger) > 0            # 2025 has dropped signals
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_engine.py::test_run_l2_bar_mask_restricts_entries_to_window -v`
Expected: FAIL — `run_l2() got an unexpected keyword argument 'bar_mask'`.

- [ ] **Step 3: Add `bar_mask` to `run_l2`**

In `optimize/l2/engine.py`, change the signature and AND the mask into the gate:

```python
def run_l2(l1, l2_params: dict, bar_mask=None) -> L2Result:
    d, d1 = l1.df_dec, l1.df1
    n = len(d)
    dec_dates = d["Date"].to_numpy()
    dec_close = d["Close"].to_numpy(float)
    pv = float(config.NQ_POINT_VALUE)

    dropped_mask = np.zeros(n, dtype=bool)
    for ds in l1.dropped_signals:
        dropped_mask[int(ds["idx"])] = True
    l1_flat = ~l1.state_timeline
    l2_gate = dropped_mask & l1_flat & _l2_gate_masks(l1, l2_params)
    if bar_mask is not None:                                  # window L2 to a bar range (in-sample / OOS)
        l2_gate = l2_gate & np.asarray(bar_mask, dtype=bool)[:n]
```

(The rest of `run_l2` is unchanged — `fast_backtest`, `force_close_on_l1_entry`, `apply_breaker`, labelling.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_engine.py -v`
Expected: all PASS (the 3 prior engine tests + the new one; default `bar_mask=None` keeps them unchanged).

- [ ] **Step 5: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/engine.py optimize/l2/test_engine.py
git commit -m "feat(l2): run_l2 bar_mask — window L2 entries to a bar range (in-sample/OOS)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `optimize/l2/optimize.py` — windowed scoring + param suggest

**Files:**
- Create: `optimize/l2/optimize.py`
- Test: `optimize/l2/test_optimize.py`

**Interfaces:**
- Consumes (Task 1): `engine.run_l2(l1, params, bar_mask=...)`; `payload.run_l1_cached`; `metrics.score`; `optimize.optimizer` as `OPT` (`_load_json`, `_CAPS`, `_BOUNDS`, `_suggest_indicators`, `DD_LIMIT_MAX`); `numpy`.
- Produces:
  - `WINDOWS(l1) -> dict` → `{"in": (0, n_split), "oos": (n_split, N)}`.
  - `score_window(l1, l2_params: dict, lo: int, hi: int) -> dict` (the `metrics.score` dict for L2 restricted to `[lo,hi)`).
  - `suggest_l2_params(trial, b: dict, cap: int) -> dict` (engine-ready L2 param dict from an Optuna trial).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_optimize.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import optimize as l2opt, l1_runner

PERMISSIVE = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
              "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


def test_windows_split_in_sample_and_oos():
    r = l1_runner.run_l1("4h")
    w = l2opt.WINDOWS(r)
    assert w["in"] == (0, r.n_split)
    assert w["oos"] == (r.n_split, len(r.df_dec))


def test_score_window_in_sample_vs_oos():
    r = l1_runner.run_l1("4h")
    w = l2opt.WINDOWS(r)
    s_in = l2opt.score_window(r, dict(PERMISSIVE), *w["in"])
    s_oos = l2opt.score_window(r, dict(PERMISSIVE), *w["oos"])
    for s in (s_in, s_oos):
        assert {"pnl", "max_dd", "n", "win"} <= set(s)
    assert s_in["n"] > 0 and s_oos["n"] > 0        # both periods have dropped signals
    # full == in + oos trade counts (windows partition the timeline; permissive takes all flat candidates)
    from optimize.l2 import engine
    full = engine.run_l2(r, dict(PERMISSIVE))
    assert s_in["n"] + s_oos["n"] == len(full.ledger)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError: cannot import name 'optimize'`.

> **Note on the partition assertion:** windows are disjoint and cover all bars, and a candidate's `entry_idx` lands in exactly one window, so `s_in["n"] + s_oos["n"] == full n` holds for the permissive profile (no gate to shift counts). For gated profiles the boundary trade attribution is still exact because `bar_mask` keys on `entry_idx`.

- [ ] **Step 3: Write `optimize/l2/optimize.py` (scoring + suggest only)**

```python
# optimize/l2/optimize.py
"""L2 optimizer (round 1) — NSGA-III over L2 profiles on the frozen L1's dropped signals, scored
full-period in-sample (2025) with an OOS holdout (2026) per spec option-3. Reuses optimize.optimizer's
sampler / indicator search space / feasibility constraint; persists under prefix l2v1."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import engine, metrics, payload          # noqa: E402
from optimize import optimizer as OPT                      # noqa: E402


def WINDOWS(l1) -> dict:
    """In-sample = first calendar segment (2025); OOS holdout = the rest (2026)."""
    n = len(l1.df_dec)
    return {"in": (0, int(l1.n_split)), "oos": (int(l1.n_split), n)}


def score_window(l1, l2_params: dict, lo: int, hi: int) -> dict:
    """metrics.score for the L2 book restricted to decision bars [lo, hi)."""
    n = len(l1.df_dec)
    mask = np.zeros(n, dtype=bool)
    mask[int(lo):int(hi)] = True
    return metrics.score(engine.run_l2(l1, l2_params, bar_mask=mask))


def suggest_l2_params(trial, b: dict, cap: int) -> dict:
    """Engine-ready L2 param dict from an Optuna trial — mirrors optimizer.objective's space (shared
    SL/TP; indicators on the 1-minute frame to match the lean L1 regime)."""
    sl_soft = trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
    delta = trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1]))
    tp = trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1]))
    gate_pct = trial.suggest_float("gate_pct", 0.0, 100.0)
    dd_limit = trial.suggest_float("dd_limit", 0.0, OPT.DD_LIMIT_MAX)
    cooldown = trial.suggest_int("cooldown", 0, cap)
    flip = trial.suggest_categorical("flip", [False, True])
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial)]
    k_rule = trial.suggest_int("k", 1, 5)
    return dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                dd_limit=dd_limit, cooldown=int(cooldown), flip=bool(flip), window="full",
                indicators=specs, k=int(k_rule), ind_1min=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py -v`
Expected: 2 PASS (`test_windows_*`, `test_score_window_*`).

- [ ] **Step 5: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/optimize.py optimize/l2/test_optimize.py
git commit -m "feat(l2): optimizer scoring core — WINDOWS (2025/2026), score_window, suggest_l2_params

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `optimize/l2/optimize.py` — the NSGA-III `run()` study

**Files:**
- Modify: `optimize/l2/optimize.py` (append `run()`)
- Test: `optimize/l2/test_optimize.py` (append)

**Interfaces:**
- Consumes (Task 2): `WINDOWS`, `score_window`, `suggest_l2_params`; `OPT.make_sampler`, `OPT._load_json`, `OPT._CAPS`, `OPT._BOUNDS`, `OPT.DD_PNL_CAP`; `optimize.storage` as `study_storage`; `optuna`, `json`.
- Produces: `run(n_trials=200, tf="4h", study_prefix="l2v1", seed=1, min_trades=5, sampler="nsga3", storage_url=None, dd_pnl_cap=OPT.DD_PNL_CAP) -> dict` returning `{study, n_trials, n_feasible, champion}` where `champion` (or `None`) = `{"params", "in_sample", "oos"}`.

- [ ] **Step 1: Write the failing test (append)**

```python
def test_run_small_study_smoke(tmp_path):
    db = tmp_path / "l2v1_smoke.db"
    res = l2opt.run(n_trials=8, study_prefix="l2v1smoke", seed=1, min_trades=1,
                    storage_url=f"sqlite:///{db}")
    assert res["n_trials"] >= 1
    assert "champion" in res
    if res["champion"] is not None:                # feasible winner found in the 8 trials
        c = res["champion"]
        assert {"pnl", "max_dd", "n", "win"} <= set(c["in_sample"])
        assert {"pnl", "max_dd", "n", "win"} <= set(c["oos"])
        assert "indicators" in c["params"] and c["params"]["ind_1min"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py::test_run_small_study_smoke -v`
Expected: FAIL — `AttributeError: module 'optimize.l2.optimize' has no attribute 'run'`.

- [ ] **Step 3: Append `run()` (+ `import optuna, json` at top)**

Add `import json` and `import optuna` to the imports, `from optimize import storage as study_storage`, then:

```python
def run(n_trials: int = 200, tf: str = "4h", study_prefix: str = "l2v1", seed: int = 1,
        min_trades: int = 5, sampler: str = "nsga3", storage_url: str | None = None,
        dd_pnl_cap: float = OPT.DD_PNL_CAP) -> dict:
    l1 = payload.run_l1_cached(tf)
    w = WINDOWS(l1)
    caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
    cap = int(caps[tf]["cooldown_cap"]); b = bounds[tf]
    print(f"[l2:{tf}] in-sample bars {w['in']}  OOS {w['oos']}  trials={n_trials}  min_trades={min_trades}",
          flush=True)

    def objective(trial):
        params = suggest_l2_params(trial, b, cap)
        s = score_window(l1, params, *w["in"])
        if s["n"] < min_trades:
            raise optuna.TrialPruned()
        pnl, dd, win = float(s["pnl"]), float(s["max_dd"]), float(s["win"])
        trial.set_user_attr("in_pnl", pnl); trial.set_user_attr("in_dd", dd)
        trial.set_user_attr("in_win", win); trial.set_user_attr("in_n", int(s["n"]))
        trial.set_user_attr("params", json.dumps(params))
        trial.set_user_attr("constraint", [float(dd - dd_pnl_cap * pnl)])   # feasible iff ≤ 0
        return pnl, -dd, win

    def _constraints(trial):
        return trial.user_attrs.get("constraint", [1.0])

    study_name = f"{study_prefix}_{tf}"
    url = storage_url or study_storage.storage_url(OPT._db_for(tf, study_name))
    storage = optuna.storages.RDBStorage(url=url, engine_kwargs=study_storage.engine_kwargs(url))
    study = optuna.create_study(study_name=study_name, storage=storage,
                                directions=["maximize", "maximize", "maximize"],
                                sampler=OPT.make_sampler(sampler, seed, _constraints, n_objectives=3),
                                load_if_exists=True)
    import warnings; warnings.filterwarnings("ignore")
    study.optimize(objective, n_trials=n_trials)

    feasible = [t for t in study.trials
                if t.values is not None and t.user_attrs.get("constraint", [1.0])[0] <= 0]
    champion = None
    if feasible:
        best = max(feasible, key=lambda t: t.values[0])     # highest in-sample P/L among feasible
        cp = json.loads(best.user_attrs["params"])
        champion = {"params": cp,
                    "in_sample": score_window(l1, cp, *w["in"]),
                    "oos": score_window(l1, cp, *w["oos"])}
        print(f"[l2:{tf}] champion in-sample P/L ${champion['in_sample']['pnl']:,.0f} "
              f"(n={champion['in_sample']['n']}) → OOS P/L ${champion['oos']['pnl']:,.0f} "
              f"(n={champion['oos']['n']})", flush=True)
    return {"study": study, "n_trials": len(study.trials), "n_feasible": len(feasible),
            "champion": champion}
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py::test_run_small_study_smoke -v`
Expected: PASS (slow — `run_l1` ~38s + 8 trials × `score_window`). The champion may be `None` if no feasible trial appears in 8 trials; the test allows that and only checks structure when present.

- [ ] **Step 5: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/optimize.py optimize/l2/test_optimize.py
git commit -m "feat(l2): NSGA-III run() — in-sample(2025) objective + OOS(2026) champion scoring, prefix l2v1

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: CLI + champion export

**Files:**
- Modify: `optimize/l2/optimize.py` (append `_export_champion` + `main()` + `__main__` guard)
- Test: `optimize/l2/test_optimize.py` (append a unit test for `_export_champion`)

**Interfaces:**
- Consumes (Task 3): `run()`.
- Produces: `_export_champion(champion: dict, tf: str, out_dir: Path) -> Path` (writes `l2v1_<tf>_champion.json`); `main()` (argparse CLI `python3 -m optimize.l2.optimize`).

- [ ] **Step 1: Write the failing test (append)**

```python
def test_export_champion_writes_json(tmp_path):
    champ = {"params": dict(PERMISSIVE),
             "in_sample": {"pnl": 1.0, "max_dd": 2.0, "n": 3, "win": 50.0},
             "oos": {"pnl": -1.0, "max_dd": 4.0, "n": 2, "win": 0.0}}
    p = l2opt._export_champion(champ, "4h", tmp_path)
    assert p.exists()
    import json as _j
    d = _j.loads(p.read_text())
    assert d["tf"] == "4h" and d["in_sample"]["n"] == 3 and d["oos"]["pnl"] == -1.0
    assert d["params"]["ind_1min"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py::test_export_champion_writes_json -v`
Expected: FAIL — `AttributeError: ... has no attribute '_export_champion'`.

- [ ] **Step 3: Append `_export_champion` + `main()`**

```python
def _export_champion(champion: dict, tf: str, out_dir) -> "Path":
    from pathlib import Path as _Path
    out_dir = _Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"l2v1_{tf}_champion.json"
    rec = {"tf": tf, "prefix": "l2v1", "params": champion["params"],
           "in_sample": champion["in_sample"], "oos": champion["oos"]}
    path.write_text(json.dumps(rec, indent=1))
    return path


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="L2 optimizer (round 1, option-3 validation)")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--prefix", default="l2v1")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--sampler", default="nsga3")
    ap.add_argument("--storage-url", default=None, help="override store (else WSH_STORAGE_URL / per-TF sqlite)")
    ap.add_argument("--out", default=str(_PI / "optimize" / "results"))
    a = ap.parse_args()
    res = run(n_trials=a.trials, tf=a.tf, study_prefix=a.prefix, seed=a.seed,
              min_trades=a.min_trades, sampler=a.sampler, storage_url=a.storage_url)
    print(f"[l2:{a.tf}] {res['n_trials']} trials · {res['n_feasible']} feasible", flush=True)
    if res["champion"] is not None:
        p = _export_champion(res["champion"], a.tf, a.out)
        print(f"[l2:{a.tf}] champion → {p}", flush=True)
    else:
        print(f"[l2:{a.tf}] no feasible champion (try more trials / lower --min-trades)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_optimize.py::test_export_champion_writes_json -v`
Expected: PASS.

- [ ] **Step 5: Golden gate + commit**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py` → 6/6.

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/optimize.py optimize/l2/test_optimize.py
git commit -m "feat(l2): optimizer CLI (python3 -m optimize.l2.optimize) + champion JSON export

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Local smoke run + build report (then GATE the server run)

**Files:**
- Create: `optimize/l2/UPDATE_l2_optimizer.md`
- Modify: `docs/superpowers/specs/2026-06-17-second-layer-nonentry-design.md:7` (status → optimizer built; server run pending)
- (Smoke writes `optimize/results/l2v1_4h_champion.json` + a local sqlite under `optimize/studies/` — both gitignored or noted, not necessarily committed)

- [ ] **Step 1: Run the full L2 suite + golden**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/ -q && python3 perf/check_golden.py`
Expected: all L2 tests PASS; golden 6/6.

- [ ] **Step 2: Local smoke study (sqlite, modest trials)**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m optimize.l2.optimize --trials 60 --min-trades 5 --storage-url "sqlite:///optimize/studies/l2v1_smoke.db"`
Expected: prints `N trials · M feasible` and, if M>0, a champion line `in-sample P/L … → OOS P/L …` + `champion → optimize/results/l2v1_4h_champion.json`. Record the in-sample-vs-OOS numbers (the key overfit read). If `0 feasible`, re-run with `--min-trades 3 --trials 120` and note it.

- [ ] **Step 3: Write `UPDATE_l2_optimizer.md`** (verbose Mermaid build report mirroring the other UPDATE docs): the architecture (cached L1 → NSGA-III over L2 params → in-sample score + DD constraint → OOS champion scoring), the module/test table, the smoke result (trials, feasible, champion in-sample vs OOS P/L/DD/win = the train-vs-OOS overfit read), and "Next: gated heavy `l2v1` server run + analysis". Fill real numbers from Step 2.

- [ ] **Step 4: Update the spec status line** (`2026-06-17-...-design.md` line 7) to note the optimizer is built + option-3 validation, server run pending.

- [ ] **Step 5: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/UPDATE_l2_optimizer.md docs/superpowers/specs/2026-06-17-second-layer-nonentry-design.md
git commit -m "docs(l2): optimizer build report + smoke (in-sample vs OOS); spec status -> optimizer built

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: GATE — present the heavy server-run command, do NOT launch**

Present to the user (do not execute without explicit go): the `l2v1` Postgres/server launch, e.g. on the AMD box —
`WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data WSH_STORAGE_URL=<pg.env URL> /home/dev/Mulham/.venv/bin/python3 -m optimize.l2.optimize --trials <N> --prefix l2v1` — with recommended `--trials` and a note that it reuses the parity-safe server env. Wait for the user's go.

---

## Spec coverage self-check

- §7 search space (indicators+K, gate_pct, SL/TP shrinkable, cooldown, dd_limit, implicit flip) → Task 2 `suggest_l2_params` (reuses `OPT._suggest_indicators` + bounds). ✅
- §7 objective (3-obj on standalone L2 book + DD≤25%·P/L constraint) → Task 3 `objective`/`_constraints`. (median-fold → single in-sample window per option-3.) ✅
- §7 validation = option 3 (full-period in-sample + OOS scored after) → Task 2 `WINDOWS` + Task 3 OOS champion scoring; `min_trades` floor in `objective`. ✅
- §7 study isolation (new prefix `l2v1`, Postgres for real run) → Task 3 `study_name=l2v1_4h`, `storage_url`/`WSH_STORAGE_URL`. ✅
- §7 timeframe 4h → default `tf="4h"` throughout. ✅
- §8 golden invariant (L1 untouched) → only `optimize/l2/*` changed; golden each task. ✅
- spec §10 build order item 3 (optimizer) → this plan; speed (#210) remains separate. ✅
- Heavy-run gating → Task 5 Step 6 (present command, await go). ✅

(Placeholder scan: none. Type consistency: `run_l2(...,bar_mask=)`, `WINDOWS`, `score_window`, `suggest_l2_params`, `run()`, `_export_champion`, the `champion` dict shape `{params,in_sample,oos}`, and the `score` keys `{pnl,max_dd,n,win}` are used identically across tasks and tests.)
