# M2 Walk-Forward Validation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline), task-by-task. Steps use `- [ ]` checkboxes.

**Goal:** Validate whether M2's single-split OOS edge survives an expanding-window quarterly walk-forward (θ selected on train, scored on the next test quarter), for the two lead configs, and record a ✅/❌ verdict.

**Architecture:** One new module `research/kalman_fusion/m2_walkforward.py` (quarter folds, window-scored P/L, train-θ selection, walk-forward driver) + `run_m2_wf.py` CLI. Reuses M2's `trend_z`/`policy`, the Phase-1 `rig.run_book`, `ceiling.eligible_dropped`, `metrics.payoff_ratio`. Off the production path; golden untouched.

**Tech Stack:** Python 3, numpy, pandas, pytest.

## Global Constraints

- **Off the production path:** only `research/kalman_fusion/` files. Golden 6/6 byte-identical (verified last task).
- **Causal folds:** each fold's train is strictly before its test quarter; θ is chosen on train only.
- **No wide search:** run only the two lead configs (`4h·filter`, `combined·redirect`) — walk-forward exists to kill multiple-comparisons risk, not add it.
- **Metric:** the walk-forward compares **M2 test-quarter P/L vs the champion's same-quarter P/L**; win-rate reported against the 57.5% breakeven.
- Local single-process compute (cheap, reuses `fast_backtest`). Run tests from the subproject root.

## File structure

| File | Responsibility |
|---|---|
| `research/kalman_fusion/m2_walkforward.py` | `quarter_folds`, `window_stats`, `select_theta_train`, `evaluate_quarter`, `walk_forward` |
| `research/kalman_fusion/run_m2_wf.py` | CLI: run the two configs, print per-fold table + verdict |
| `research/kalman_fusion/test_m2_wf.py` | TDD: fold causality, window partition == full, θ train-only, aggregate |

---

### Task 1: `quarter_folds` + `window_stats`

**Files:**
- Create: `research/kalman_fusion/m2_walkforward.py`, `research/kalman_fusion/test_m2_wf.py`

**Interfaces:**
- `quarter_folds(C) -> list[dict]` — one dict per test quarter (3rd unique quarter onward): `{q:int, q_start:int, q_end:int}` (bar-index bounds; train is implied `[0, q_start)`).
- `window_stats(C, z, theta, mode, lo, hi) -> dict` — run the policy book, keep trades whose **entry bar index** is in `[lo, hi)`, return `{pnl, n, win, payoff}`.

- [ ] **Step 1: Write the failing tests**

```python
# research/kalman_fusion/test_m2_wf.py
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z
from research.kalman_fusion.m2_walkforward import quarter_folds, window_stats


def test_quarter_folds_causal_expanding():
    C = cp.load_champion("4h")
    folds = quarter_folds(C)
    assert len(folds) >= 3
    starts = [f["q_start"] for f in folds]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)   # strictly expanding
    for f in folds:
        assert 0 < f["q_start"] < f["q_end"] <= C["n"]                    # train non-empty, precedes test


def test_window_partition_equals_full():
    # for a FIXED theta, the per-quarter windows partition the full book's total P/L.
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    full = window_stats(C, z, 1e9, "redirect", 0, C["n"])                 # theta=inf → champion book, whole span
    # sum over contiguous quarter windows == full
    d = C["d"]["Date"]; key = (d.dt.year * 10 + ((d.dt.month - 1) // 3 + 1)).to_numpy()
    tot = 0.0
    for k in sorted(set(key.tolist())):
        idx = np.where(key == k)[0]
        tot += window_stats(C, z, 1e9, "redirect", int(idx[0]), int(idx[-1] + 1))["pnl"]
    assert abs(tot - full["pnl"]) < 1e-6
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2_wf.py -v` → FAIL (no module).

- [ ] **Step 3: Implement**

```python
# research/kalman_fusion/m2_walkforward.py
"""M2 walk-forward validation: expanding-window quarterly. theta selected on train, scored on the next test
quarter, vs the champion's same-quarter trades. Reuses M2 policy + Phase-1 rig. Off the production path."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion import rig
from research.kalman_fusion.m2_trend import policy
from research.kalman_fusion.ceiling import eligible_dropped
from research.kalman_fusion.metrics import payoff_ratio


def _quarter_key(dates):
    return (dates.dt.year * 10 + ((dates.dt.month - 1) // 3 + 1)).to_numpy()


def quarter_folds(C):
    key = _quarter_key(C["d"]["Date"])
    uniq = sorted(set(key.tolist()))
    folds = []
    for k in uniq:
        if sum(1 for u in uniq if u < k) < 2:        # need >= 2 prior quarters of train
            continue
        idx = np.where(key == k)[0]
        folds.append({"q": int(k), "q_start": int(idx[0]), "q_end": int(idx[-1] + 1)})
    return folds


def _entry_bar_idx(C, book):
    dec = C["d"]["Date"].to_numpy("datetime64[ns]")
    et = np.array([np.datetime64(t["entry_time"]) for t in book], dtype="datetime64[ns]")
    return np.searchsorted(dec, et, side="left")     # entry_time == a decision-bar date → exact index


def window_stats(C, z, theta, mode, lo, hi) -> dict:
    admit, direction = policy(C, z, theta, mode)
    book = rig.run_book(C, admit, direction)
    if not book:
        return {"pnl": 0.0, "n": 0, "win": 0.0, "payoff": 0.0}
    idx = _entry_bar_idx(C, book)
    pnls = np.array([book[k]["pnl"] for k in range(len(book)) if lo <= idx[k] < hi], dtype=float)
    n = int(pnls.size)
    return {"pnl": float(pnls.sum()), "n": n,
            "win": (float((pnls > 0).sum()) / n if n else 0.0), "payoff": payoff_ratio(pnls)}
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2_wf.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/m2_walkforward.py subprojects/Parametric-Indicators/research/kalman_fusion/test_m2_wf.py
git commit -m "research(kalman): M2 walk-forward quarter folds + window-scored stats"
```

---

### Task 2: `select_theta_train` + `evaluate_quarter` + `walk_forward`

**Files:**
- Modify: `research/kalman_fusion/m2_walkforward.py`, `research/kalman_fusion/test_m2_wf.py`

**Interfaces:**
- `select_theta_train(C, z, mode, train_hi) -> float` — θ\* = argmax of `window_stats` P/L over `[0, train_hi)`, sweeping the |z|-quantile grid built from **train** dropped signals (`i < train_hi`).
- `evaluate_quarter(C, z, theta, mode, q_start, q_end) -> (m2, champ)` — M2 window stats vs champion (θ=∞) window stats for that quarter.
- `walk_forward(C, z, mode) -> dict` — `{rows:[{q, theta, m2, champ}], sum_m2_pnl, sum_champ_pnl, folds_m2_wins, n_folds}`.

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m2_wf.py
from research.kalman_fusion.m2_walkforward import select_theta_train, evaluate_quarter, walk_forward


def test_evaluate_quarter_champion_is_theta_inf():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    f = quarter_folds(C)[0]
    m2_inf, champ = evaluate_quarter(C, z, 1e9, "redirect", f["q_start"], f["q_end"])
    assert m2_inf == champ                              # theta=inf admits nothing ⇒ M2==champion

def test_select_theta_uses_train_only():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"].copy()
    f = quarter_folds(C)[0]
    th0 = select_theta_train(C, z, "redirect", f["q_start"])
    z[f["q_end"] - 1] = 999.0                           # perturb a TEST-quarter signal's z
    th1 = select_theta_train(C, z, "redirect", f["q_start"])
    assert th0 == th1                                   # θ* depends on train only

def test_walk_forward_aggregate_shape():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    wf = walk_forward(C, z, "redirect")
    assert wf["n_folds"] == len(quarter_folds(C))
    assert len(wf["rows"]) == wf["n_folds"]
    assert 0 <= wf["folds_m2_wins"] <= wf["n_folds"]
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2_wf.py -k "evaluate_quarter or select_theta or walk_forward" -v` → FAIL.

- [ ] **Step 3: Implement**

```python
# append to research/kalman_fusion/m2_walkforward.py
def select_theta_train(C, z, mode, train_hi) -> float:
    idxs_tr = [i for i in eligible_dropped(C)["idxs"] if i < train_hi]
    if not idxs_tr:
        return 1e9
    grid = list(np.quantile(np.abs(z[idxs_tr]), [0.0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95])) + [1e9]
    best_th, best_pnl = 1e9, -1e18
    for th in grid:
        pnl = window_stats(C, z, float(th), mode, 0, train_hi)["pnl"]
        if pnl > best_pnl:
            best_pnl, best_th = pnl, float(th)
    return best_th


def evaluate_quarter(C, z, theta, mode, q_start, q_end):
    m2 = window_stats(C, z, theta, mode, q_start, q_end)
    champ = window_stats(C, z, 1e9, mode, q_start, q_end)     # theta=inf ⇒ champion book only
    return m2, champ


def walk_forward(C, z, mode) -> dict:
    rows = []; sm = sc = 0.0; wins = 0
    folds = quarter_folds(C)
    for f in folds:
        th = select_theta_train(C, z, mode, f["q_start"])
        m2, champ = evaluate_quarter(C, z, th, mode, f["q_start"], f["q_end"])
        rows.append({"q": f["q"], "theta": th, "m2": m2, "champ": champ})
        sm += m2["pnl"]; sc += champ["pnl"]; wins += int(m2["pnl"] > champ["pnl"])
    return {"rows": rows, "sum_m2_pnl": sm, "sum_champ_pnl": sc,
            "folds_m2_wins": wins, "n_folds": len(folds)}
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2_wf.py -k "evaluate_quarter or select_theta or walk_forward" -v` → PASS.

- [ ] **Step 5: Commit** — `git add -u && git commit -m "research(kalman): M2 walk-forward train-theta selection + driver"`

---

### Task 3: CLI + run + study doc + verdict + golden

**Files:**
- Create: `research/kalman_fusion/run_m2_wf.py`
- Modify: `docs/RESEARCH_KALMAN_FUSION_STUDY.md`

- [ ] **Step 1: Write the CLI**

```python
# research/kalman_fusion/run_m2_wf.py
"""M2 walk-forward: expanding quarterly, theta-on-train, per-fold test vs champion. Two lead configs."""
from __future__ import annotations
import argparse
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z
from research.kalman_fusion.m2_walkforward import walk_forward

CONFIGS = [("4h", "filter"), ("combined", "redirect")]


def _q(k):  # 20253 -> "2025Q3"
    return f"{k // 10}Q{k % 10}"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tf", default="4h"); a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z = trend_z(C, frames=("4h", "1m"))
    for frame, mode in CONFIGS:
        wf = walk_forward(C, Z[frame], mode)
        print(f"\n== M2 walk-forward: frame={frame} mode={mode} ==")
        print(f"{'quarter':8} {'theta':>8} {'M2_P/L':>11} {'M2_n':>5} {'M2_win%':>8}  {'champ_P/L':>11} {'champ_n':>7} {'M2>champ':>8}")
        for r in wf["rows"]:
            m2, ch = r["m2"], r["champ"]
            print(f"{_q(r['q']):8} {r['theta']:8.4f} {m2['pnl']:11,.0f} {m2['n']:5d} {100*m2['win']:7.1f}%  "
                  f"{ch['pnl']:11,.0f} {ch['n']:7d} {str(m2['pnl'] > ch['pnl']):>8}")
        print(f"  AGGREGATE: M2 ${wf['sum_m2_pnl']:,.0f} vs champion ${wf['sum_champ_pnl']:,.0f} "
              f"| M2 beats champ in {wf['folds_m2_wins']}/{wf['n_folds']} folds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Local import smoke** — `python3 -c "import research.kalman_fusion.run_m2_wf; print('ok')"` → `ok`.

- [ ] **Step 3: Run the walk-forward**

```bash
WSH_DATA_BASE=/mnt/data/projects/trading WSG_DATA_ROOT=/mnt/data/projects/trading/data python3 -m research.kalman_fusion.run_m2_wf
```
Expected: per-fold tables + the `AGGREGATE` line + `folds M2 wins` count for each config.

- [ ] **Step 4: Append the walk-forward result + verdict to `docs/RESEARCH_KALMAN_FUSION_STUDY.md`** (fill measured numbers; Mermaid, no ASCII):

```markdown
### M2 walk-forward validation (expanding quarterly, θ-on-train)

| config | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 | aggregate M2 vs champ | folds won |
|---|--:|--:|--:|--:|--:|--:|
| 4h·filter | … | … | … | … | $… vs $… | …/4 |
| combined·redirect | … | … | … | … | $… vs $… | …/4 |

**Verdict:** <✅ edge holds — M2 beats the champion in a majority of folds above breakeven / ❌ single-split was
optimistic — M2 wins only N/4>. → <proceed to M2b + dashboard wiring / harden further / shelve>.
```

- [ ] **Step 5: Verify golden + commit**

Run: `python3 perf/check_golden.py` (server) → 6/6 MATCH.
```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/run_m2_wf.py subprojects/Parametric-Indicators/docs/RESEARCH_KALMAN_FUSION_STUDY.md
git commit -m "research(kalman): M2 walk-forward run + verdict"
```

---

## Self-review

- **Spec coverage:** §2 scheme → `quarter_folds` (Task 1); §3 per-fold → `select_theta_train`+`evaluate_quarter` (Task 2); §4 verdict → `walk_forward` aggregate + Task 3 doc; §5 modules/tests → all (fold causality, window-partition, θ-train-only, aggregate). Two lead configs only (Task 3).
- **Placeholder scan:** only Task 3 Step-4 `…`/`<…>` = measured numbers/verdict from Step 3. No code TODO.
- **Type consistency:** `quarter_folds -> list[{q,q_start,q_end}]`; `window_stats -> {pnl,n,win,payoff}`; `select_theta_train -> float`; `evaluate_quarter -> (dict,dict)`; `walk_forward -> {rows,sum_*,folds_m2_wins,n_folds}` used consistently in the CLI.
- **Causality:** folds train-before-test (`quarter_folds` test); θ selected on `[0,train_hi)` only (`select_theta_train` test perturbs a test-quarter z and asserts θ* unchanged). Champion baseline = θ=∞ (admits nothing).
```
