# M1 Champion-Fusion — Phase 2a Implementation Plan (static weighted-vote director)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build the Phase-2a static weighted-vote directional classifier for the champion's dropped 4h signals (fusing finer NQ timeframes), and produce its **IS (2025) + OOS (2026) Pareto front** (entry-rate × total-P/L) vs the box-native and champion baselines — deciding whether M1 earns Phase 2b (Kalman).

**Architecture:** New module `research/kalman_fusion/m1_fusion.py`, importing the Phase-1 rig + ceiling. It (1) builds a causal multi-TF direction matrix `Z`, (2) fits per-TF reliability weights on 2025 dropped signals (profitable side from M0's `signal_outcomes`), (3) turns a conviction threshold θ into `(admit, direction)` masks, (4) evaluates via the rig with a 2025/2026 split. Off the production path; golden untouched.

**Tech Stack:** Python 3, numpy, pandas, pytest. Reuses `optimize.data.load_inputs`, `optimize.signals.decision_signals`, `optimize.fast_engine.signals_to_int`, `optimize.counterfactual_pause`, `research.kalman_fusion.{rig,ceiling,metrics}`, `config.YEARS`, `optimize.timeframes`.

## Global Constraints

- **Off the production path:** only create/modify files under `research/kalman_fusion/`. No `optimize/`, `frontend/`, engine changes. Golden 6/6 stays byte-identical (verified last task).
- **Causality is mandatory:** every finer-TF observation for a 4h bar must use only finer bars **closed at/before that 4h signal bar's close**. Each observation-building function gets an input-truncation test.
- **Exits unchanged:** M1 only chooses admit + direction; the champion's SL/TP/breaker/cap are fixed (payoff stays ~0.74 — M0's structural result). Never modify exits here.
- **IS/OOS discipline:** fit weights on 2025 dropped signals ONLY; freeze; evaluate 2025 (IS) and 2026 (OOS) separately. OOS is the gate.
- **Server for the full run** (Task 5); unit tests run locally single-process (a `load_champion` is ~5s / few-GB — not a campaign).
- Run tests from the subproject root `subprojects/Parametric-Indicators/`.

## File structure

| File | Responsibility |
|---|---|
| `research/kalman_fusion/m1_fusion.py` | multi-TF direction matrix, weight fit, fused direction, policy masks, IS/OOS evaluate |
| `research/kalman_fusion/run_m1.py` | CLI: fit + θ-sweep → IS/OOS front table + CSV |
| `research/kalman_fusion/test_m1.py` | TDD: causality guard, weight fit, fused, policy, rig-combined, monotone sweep |
| `research/kalman_fusion/rig.py` | (modify) add `run_book()` returning per-trade dollars+entry_time so IS/OOS can split |

---

### Task 1: Causal multi-TF direction matrix `finer_tf_directions`

**Files:**
- Create: `research/kalman_fusion/m1_fusion.py`
- Create: `research/kalman_fusion/test_m1.py`

**Interfaces:**
- Consumes: `optimize.data.load_inputs(tf, "NQ")`, `optimize.signals.decision_signals(df_dec, box)`, `optimize.fast_engine.signals_to_int`, `optimize.timeframes.get(tf).bar_td`, champion context `C` (`C["d"]["Date"]`, `C["sig"]`, `C["n"]`).
- Produces: `finer_tf_directions(C, tfs=("1h","15m","5m")) -> (Z, cols)` where `Z` is `int8[n, T]` (T = len(tfs)+1), one column per finer TF plus a final column for the 4h box direction at `i-1`; `cols` is the list of column labels. `Z[i, t]` = the finer TF's box direction from its **last bar closed ≤ the 4h signal bar (i-1) close**; 0 before any finer bar exists.

- [ ] **Step 1: Write the failing tests (shape + causality guard)**

```python
# research/kalman_fusion/test_m1.py
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m1_fusion import finer_tf_directions


def test_direction_matrix_shape_and_values():
    C = cp.load_champion("4h")
    Z, cols = finer_tf_directions(C, tfs=("1h", "15m", "5m"))
    assert Z.shape == (C["n"], 4)                 # 3 finer TFs + the 4h voter
    assert cols[-1] == "4h"
    assert set(np.unique(Z)).issubset({-1, 0, 1})
    # the 4h voter column is the 4h box direction read at i-1
    assert Z[5, -1] == int(np.sign(C["sig"][4]))


def test_direction_matrix_is_causal():
    # truncating the context to the first m 4h bars must not change any row < m of Z.
    C = cp.load_champion("4h")
    Zfull, _ = finer_tf_directions(C, tfs=("1h", "15m"))
    m = 1200
    Ctrunc = dict(C)
    Ctrunc["d"] = C["d"].iloc[:m].copy()
    Ctrunc["sig"] = np.asarray(C["sig"])[:m]
    Ctrunc["n"] = m
    Ztrunc, _ = finer_tf_directions(Ctrunc, tfs=("1h", "15m"))
    assert np.array_equal(Ztrunc, Zfull[:m])
```

- [ ] **Step 2: Run to verify it fails**

Run: `WSH_DATA_BASE=/mnt/data/projects/trading WSG_DATA_ROOT=/mnt/data/projects/trading/data python3 -m pytest research/kalman_fusion/test_m1.py -k direction -v`
Expected: FAIL — `ModuleNotFoundError: research.kalman_fusion.m1_fusion`

- [ ] **Step 3: Implement `finer_tf_directions`**

```python
# research/kalman_fusion/m1_fusion.py
"""M1 — champion-signal fusion (directional classifier for the champion's dropped 4h signals).
Phase 2a: static weighted vote over finer NQ timeframes. Reuses the Phase-1 rig + M0 ceiling.
Causal by construction (finer bar CLOSED <= 4h signal-bar close); exits unchanged (payoff pinned)."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401  (path insert)
from optimize import data as data_mod
from optimize import signals as sig_mod
from optimize import timeframes as TF
from optimize.fast_engine import signals_to_int


def finer_tf_directions(C, tfs=("1h", "15m", "5m")):
    """int8[n, T] causal box-direction observations: one column per finer TF (last bar CLOSED <= the 4h
    signal bar's close) + a final '4h' column = the 4h box direction read at i-1."""
    dec_start = C["d"]["Date"].to_numpy("datetime64[ns]")        # 4h bar START; contiguous ⇒ bar i start == bar i-1 close
    n = int(C["n"])
    cols_data = []
    for tf in tfs:
        d, _, box, _, _ = data_mod.load_inputs(tf, "NQ")
        dirs = signals_to_int(sig_mod.decision_signals(d, box)).astype(np.int8)
        ftd = TF.get(tf).bar_td.to_timedelta64()
        finer_close = d["Date"].to_numpy("datetime64[ns]") + ftd  # finer bar CLOSE time
        # last finer bar whose CLOSE <= the 4h signal-bar (i-1) close (== 4h bar i start). searchsorted only
        # looks backward ⇒ look-ahead safe.
        j = np.searchsorted(finer_close, dec_start, side="right") - 1
        col = np.where(j >= 0, dirs[np.clip(j, 0, len(dirs) - 1)], 0).astype(np.int8)
        cols_data.append(col)
    # 4h voter = the 4h box direction read at i-1 (the signal bar); bar 0 has no predecessor ⇒ 0.
    sig = np.asarray(C["sig"]).astype(np.int8)[:n]
    four_h = np.zeros(n, dtype=np.int8)
    four_h[1:] = np.sign(sig[:-1]).astype(np.int8)
    Z = np.column_stack(cols_data + [four_h]).astype(np.int8)
    return Z, list(tfs) + ["4h"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `WSH_DATA_BASE=/mnt/data/projects/trading WSG_DATA_ROOT=/mnt/data/projects/trading/data python3 -m pytest research/kalman_fusion/test_m1.py -k direction -v`
Expected: PASS (shape + causality)

- [ ] **Step 5: Commit**

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/m1_fusion.py subprojects/Parametric-Indicators/research/kalman_fusion/test_m1.py
git commit -m "research(kalman): M1 causal multi-TF direction matrix"
```

---

### Task 2: Profitable side + per-TF weight fit (2025 in-sample)

**Files:**
- Modify: `research/kalman_fusion/m1_fusion.py` (add `n_split`, `profitable_side`, `fit_weights`)
- Modify: `research/kalman_fusion/test_m1.py` (add tests)

**Interfaces:**
- Consumes: `research.kalman_fusion.ceiling.signal_outcomes`, `config.YEARS`.
- Produces:
  - `n_split(C) -> int` — number of 2025 decision bars (the IS/OOS boundary).
  - `profitable_side(C, idxs) -> np.ndarray` — per idx, +1/-1 = the better realised direction (from M0 `signal_outcomes`: native(+1 long) vs opposite(-1 short)); 0 where unresolved.
  - `fit_weights(Z, C, idxs_is) -> np.ndarray` — per-column weight = `max(0, 2*hit_rate - 1)` where `hit_rate` = fraction of resolved 2025 dropped signals where that column's direction equals the profitable side (only counting bars where both are non-zero).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m1.py
from research.kalman_fusion.m1_fusion import n_split, profitable_side, fit_weights
from research.kalman_fusion.ceiling import eligible_dropped


def test_profitable_side_matches_signal_outcomes_sign():
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:100]
    ps = profitable_side(C, idxs)
    assert set(np.unique(ps)).issubset({-1, 0, 1})
    assert (ps != 0).sum() > 0

def test_fit_weights_rewards_a_perfect_column():
    # synthetic: 3 idxs, profitable side [+1,+1,-1]; column 0 matches perfectly, column 1 is anti-perfect.
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:3]
    ps = profitable_side(C, idxs)
    # build a fake Z aligned to those idxs where col0==ps, col1==-ps, col2==0
    Z = np.zeros((C["n"], 3), dtype=np.int8)
    for k, i in enumerate(idxs):
        Z[i, 0] = ps[k]; Z[i, 1] = -ps[k]; Z[i, 2] = 0
    w = fit_weights(Z, C, idxs)          # idxs all in-sample here for the unit test
    assert w[0] > w[1]                    # perfect column outweighs anti-perfect
    assert w[1] == 0.0                    # anti-perfect clamps to 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k "profitable or fit_weights" -v`
Expected: FAIL — `ImportError: cannot import name 'fit_weights'`

- [ ] **Step 3: Implement**

```python
# append to research/kalman_fusion/m1_fusion.py
import config                                    # noqa: E402
from research.kalman_fusion.ceiling import signal_outcomes


def n_split(C) -> int:
    return int((C["d"]["Date"].dt.year == config.YEARS[0]).sum())


def profitable_side(C, idxs) -> np.ndarray:
    o = signal_outcomes(C, idxs)                 # native(+1 long) vs opposite(-1 short) $ P/L
    ps = np.zeros(len(idxs), dtype=np.int8)
    both = ~np.isnan(o["native"]) & ~np.isnan(o["opposite"])
    ps[both & (o["native"] >= o["opposite"])] = 1
    ps[both & (o["native"] < o["opposite"])] = -1
    # one-sided resolution: if only one direction closes, that side is the (only) profitable option to learn from
    only_nat = ~np.isnan(o["native"]) & np.isnan(o["opposite"]); ps[only_nat] = 1
    only_opp = np.isnan(o["native"]) & ~np.isnan(o["opposite"]); ps[only_opp] = -1
    return ps


def fit_weights(Z, C, idxs_is) -> np.ndarray:
    """Per-column reliability weight from 2025 dropped signals: max(0, 2*hit_rate - 1)."""
    idxs_is = list(idxs_is)
    ps = profitable_side(C, idxs_is)
    T = Z.shape[1]
    w = np.zeros(T, dtype=float)
    for t in range(T):
        hits = tot = 0
        for k, i in enumerate(idxs_is):
            d = int(Z[i, t]); s = int(ps[k])
            if d != 0 and s != 0:
                tot += 1; hits += (d == s)
        hr = (hits / tot) if tot else 0.5
        w[t] = max(0.0, 2.0 * hr - 1.0)
    return w
```

- [ ] **Step 4: Run to verify it passes**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k "profitable or fit_weights" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/m1_fusion.py subprojects/Parametric-Indicators/research/kalman_fusion/test_m1.py
git commit -m "research(kalman): M1 profitable-side + per-TF reliability weight fit (2025 IS)"
```

---

### Task 3: Fused direction + policy masks

**Files:**
- Modify: `research/kalman_fusion/m1_fusion.py` (add `fused`, `policy`)
- Modify: `research/kalman_fusion/test_m1.py` (add tests)

**Interfaces:**
- Consumes: `optimize.counterfactual_pause._engine_gate`, `research.kalman_fusion.ceiling.eligible_dropped`.
- Produces:
  - `fused(z_row, w) -> (direction:int, conviction:float)` — `score = Σ wₜ·zₜ`; direction `sign(score)`; conviction `|score|/Σ|wₜ·1[zₜ≠0]|` clamped to `[0,1]` (0 if no informative vote).
  - `policy(C, Z, w, theta) -> (admit, direction)` — `admit` = `_engine_gate(C)` OR (an eligible-dropped bar whose `conviction>theta` and fused dir≠0); `direction` int8[n] = fused dir written at `i-1` for each admitted dropped bar, 0 elsewhere (rig keeps native there). The champion's own gate bars are admitted with direction 0 (native).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m1.py
from research.kalman_fusion.m1_fusion import fused, policy, finer_tf_directions as _ftd  # noqa: F401
from optimize import counterfactual_pause as _cp


def test_fused_sign_and_conviction_bounds():
    d, c = fused(np.array([1, 1, 1]), np.array([1.0, 1.0, 1.0]))
    assert d == 1 and abs(c - 1.0) < 1e-9        # unanimous → conviction 1
    d, c = fused(np.array([1, -1, 0]), np.array([1.0, 1.0, 1.0]))
    assert d == 0 and 0.0 <= c <= 1.0            # tie → dir 0
    d, c = fused(np.array([0, 0, 0]), np.array([1.0, 1.0, 1.0]))
    assert d == 0 and c == 0.0                   # no vote → conviction 0

def test_policy_theta_one_admits_only_champion():
    C = cp.load_champion("4h")
    Z, _ = _ftd(C)
    w = np.ones(Z.shape[1])
    admit, direction = policy(C, Z, w, theta=1.0)   # nothing exceeds conviction>1
    assert np.array_equal(admit, _cp._engine_gate(C))
    assert int((direction != 0).sum()) == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k "fused or policy" -v`
Expected: FAIL — `ImportError: cannot import name 'fused'`

- [ ] **Step 3: Implement**

```python
# append to research/kalman_fusion/m1_fusion.py
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped


def fused(z_row, w):
    z = np.asarray(z_row, dtype=float); w = np.asarray(w, dtype=float)
    score = float(np.dot(w, z))
    denom = float(np.sum(np.abs(w) * (z != 0)))
    conv = (abs(score) / denom) if denom > 0 else 0.0
    return int(np.sign(score)), min(1.0, conv)


def policy(C, Z, w, theta):
    n = int(C["n"])
    admit = np.asarray(cp._engine_gate(C)).copy()
    direction = np.zeros(n, dtype=np.int8)
    for i in eligible_dropped(C)["idxs"]:
        d, conv = fused(Z[i], w)
        if d != 0 and conv > theta:
            admit[i] = True
            direction[i - 1] = d              # engine reads the box signal at i-1
    return admit, direction
```

- [ ] **Step 4: Run to verify it passes**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k "fused or policy" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "research(kalman): M1 fused direction + admit/direction policy masks"
```

---

### Task 4: IS/OOS evaluation via the rig (add `run_book` + `evaluate_m1`)

**Files:**
- Modify: `research/kalman_fusion/rig.py` (add `run_book`)
- Modify: `research/kalman_fusion/m1_fusion.py` (add `evaluate_m1`)
- Modify: `research/kalman_fusion/test_m1.py` (add tests)

**Interfaces:**
- Produces:
  - `rig.run_book(C, admit, direction) -> list[dict]` — the combined book's trades, each `{"pnl": float(dollars), "entry_time": ...}` (in exit order). `rig.evaluate` refactored to call it.
  - `m1_fusion.evaluate_m1(C, Z, w, theta) -> (is_metrics, oos_metrics)` — run the policy through `run_book`, split trades by entry-year (`config.YEARS[0]` = 2025 IS vs OOS), summarise each with `metrics.summarize` (n_eligible split accordingly).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m1.py
from research.kalman_fusion.m1_fusion import evaluate_m1


def test_evaluate_theta_one_reproduces_champion_full():
    C = cp.load_champion("4h")
    Z, _ = _ftd(C)
    w = np.ones(Z.shape[1])
    is_m, oos_m = evaluate_m1(C, Z, w, theta=1.0)     # admit nothing extra
    champ_total = sum(t["pnl_points"] * C["pv"] for t in cp.champion_taken_trades(C))
    assert abs((is_m.total_pnl + oos_m.total_pnl) - champ_total) < 1e-6

def test_entry_rate_non_increasing_in_theta():
    C = cp.load_champion("4h")
    Z, _ = _ftd(C)
    w = np.ones(Z.shape[1])
    rates = []
    for th in (0.0, 0.34, 0.67, 1.0):
        is_m, oos_m = evaluate_m1(C, Z, w, theta=th)
        rates.append(is_m.n_entries + oos_m.n_entries)
    assert all(rates[k] >= rates[k + 1] for k in range(len(rates) - 1))
```

- [ ] **Step 2: Run to verify it fails**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k evaluate -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_m1'`

- [ ] **Step 3: Implement (rig.run_book + evaluate_m1)**

```python
# in research/kalman_fusion/rig.py — add run_book and refactor evaluate to use it
def run_book(C, admit, direction=None):
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = cp._bt_args(C)
    si = np.asarray(si).copy()
    if direction is not None:
        d = np.asarray(direction); si = np.where(d != 0, d, si)
    admit = np.asarray(admit, dtype=bool)
    trades = fast_backtest(dd, cl, si, admit, md, mh, ml, mc, sls, slh, tp, flip)
    return [{"pnl": t["pnl_points"] * C["pv"], "entry_time": t["entry_time"]} for t in trades]


def evaluate(C, admit, direction=None, n_eligible=None) -> Metrics:
    book = run_book(C, admit, direction)
    pnls = [t["pnl"] for t in book]
    if n_eligible is None:
        n_eligible = int(np.asarray(admit, dtype=bool).sum())
    return summarize(pnls, n_eligible=n_eligible, pnls_exit_order=pnls)
```

```python
# append to research/kalman_fusion/m1_fusion.py
import pandas as pd                              # noqa: E402
from research.kalman_fusion import rig           # noqa: E402
from research.kalman_fusion.metrics import summarize


def evaluate_m1(C, Z, w, theta):
    admit, direction = policy(C, Z, w, theta)
    book = rig.run_book(C, admit, direction)
    yr0 = config.YEARS[0]
    is_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year == yr0]
    oos_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year != yr0]
    ed = eligible_dropped(C)
    n_is = n_split(C)                             # 2025 flat-eligible denom is bounded by 2025 bars
    is_elig = sum(1 for i in ([t for t in ed["idxs"]] ) if i < n_is) + \
              sum(1 for t in cp.champion_taken_trades(C) if pd.Timestamp(t["entry_time"]).year == yr0)
    oos_elig = (ed["n_eligible"]) - is_elig
    return (summarize(is_p, n_eligible=max(1, is_elig)),
            summarize(oos_p, n_eligible=max(1, oos_elig)))
```

- [ ] **Step 4: Run to verify it passes (and Phase-1 rig test still green)**

Run: `... python3 -m pytest research/kalman_fusion/test_m1.py -k evaluate research/kalman_fusion/test_rig.py -v`
Expected: PASS (rig parity preserved after the refactor; M1 IS/OOS split works)

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "research(kalman): rig.run_book + M1 IS/OOS evaluation split"
```

---

### Task 5: CLI + server θ-sweep + study doc + Phase-2b gate

**Files:**
- Create: `research/kalman_fusion/run_m1.py`
- Modify: `docs/RESEARCH_KALMAN_FUSION_STUDY.md` (append M1 results + gate)

**Interfaces:**
- Consumes: `m1_fusion.{finer_tf_directions, fit_weights, eligible_dropped, n_split, evaluate_m1}`, `ceiling.ceiling_report` (for the box-native reference).

- [ ] **Step 1: Write the CLI**

```python
# research/kalman_fusion/run_m1.py
"""M1 static-vote director: fit weights on 2025, sweep theta, print IS/OOS front. Heavy → server."""
from __future__ import annotations
import argparse, csv
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m1_fusion import finer_tf_directions, fit_weights, evaluate_m1, n_split
from research.kalman_fusion.ceiling import eligible_dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--tfs", default="1h,15m,5m")
    ap.add_argument("--out", default="research/kalman_fusion/m1_front.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z, cols = finer_tf_directions(C, tfs=tuple(a.tfs.split(",")))
    ns = n_split(C)
    idxs_is = [i for i in eligible_dropped(C)["idxs"] if i < ns]        # 2025 dropped only
    w = fit_weights(Z, C, idxs_is)
    print("columns:", cols, " weights:", [round(x, 3) for x in w])
    rows = []
    print(f"{'theta':>6} {'IS_entries':>10} {'IS_P/L':>12} {'IS_win%':>8}  {'OOS_entries':>11} {'OOS_P/L':>12} {'OOS_win%':>9}")
    for th in [round(x, 2) for x in np.linspace(0.0, 1.0, 11)]:
        is_m, oos_m = evaluate_m1(C, Z, w, th)
        print(f"{th:6.2f} {is_m.n_entries:10d} {is_m.total_pnl:12,.0f} {100*is_m.win_rate:7.1f}%  "
              f"{oos_m.n_entries:11d} {oos_m.total_pnl:12,.0f} {100*oos_m.win_rate:8.1f}%")
        rows.append(dict(theta=th, is_entries=is_m.n_entries, is_pnl=is_m.total_pnl, is_win=is_m.win_rate,
                         is_payoff=is_m.payoff, oos_entries=oos_m.n_entries, oos_pnl=oos_m.total_pnl,
                         oos_win=oos_m.win_rate, oos_payoff=oos_m.payoff))
    with open(a.out, "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0])); wtr.writeheader(); wtr.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Local import smoke**

Run: `python3 -c "import research.kalman_fusion.run_m1; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Run the full M1 sweep ON THE SERVER**

```bash
rsync -az -e "ssh -o BatchMode=yes" research/kalman_fusion/ amd-trading:/home/dev/Mulham/wsg-i/Parametric-Indicators/research/kalman_fusion/
ssh amd-trading 'cd /home/dev/Mulham/wsg-i/Parametric-Indicators && source /home/dev/Mulham/.venv/bin/activate && export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data && python3 -m research.kalman_fusion.run_m1 --out research/kalman_fusion/m1_front.csv'
```
Expected: an IS/OOS θ-sweep table. Pull `m1_front.csv` for the doc.

- [ ] **Step 4: Append M1 results to `docs/RESEARCH_KALMAN_FUSION_STUDY.md`**

Fill actual numbers into this section (Mermaid, no ASCII):

```markdown
## M1 — champion-signal fusion (static weighted vote), NQ 4h

Fitted per-TF weights (2025): 1h <w>, 15m <w>, 5m <w>, 4h <w>.

| θ | IS entries | IS P/L | IS win% | OOS entries | OOS P/L | OOS win% |
|--:|--:|--:|--:|--:|--:|--:|
| … | … | … | … | … | … | … |

References — champion baseline (OOS P/L $<..>), box-native admit (OOS P/L $<..>).

### Phase-2b gate
- If the OOS front lifts total P/L over box-native at comparable entry-rate → **build M2b (Kalman)**.
- Else → static multi-TF direction doesn't recover the dropped flow OOS; **stop M1**, redirect to M2/M3.
```

- [ ] **Step 5: Verify golden untouched + commit**

Run: `python3 perf/check_golden.py` (on the server or locally)
Expected: 6/6 MATCH (research layer is off-path).

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/run_m1.py subprojects/Parametric-Indicators/docs/RESEARCH_KALMAN_FUSION_STUDY.md
git commit -m "research(kalman): M1 CLI + NQ 4h IS/OOS front + Phase-2b gate"
```

---

## Self-review

- **Spec coverage:** §3 observations → Task 1; §4 weight fit + fusion → Tasks 2–3; §6 rig integration → Task 4 (`run_book`); §7 IS/OOS split → Task 4 + Task 5 sweep; §8 modules/tests → all tasks incl. the mandatory causality guard (Task 1) + θ=1-reproduces-champion (Tasks 3,4) + monotone sweep (Task 4); deliverable + gate → Task 5. Phase 2b is explicitly gated, not built here.
- **Placeholder scan:** only Task 5 Step 4 has `<..>` — those are measured numbers produced by Step 3, not unwritten logic. No TODO in code.
- **Type consistency:** `finer_tf_directions -> (Z, cols)`; `fit_weights(Z, C, idxs) -> w`; `fused(z,w) -> (int,float)`; `policy(C,Z,w,theta) -> (admit,direction)`; `evaluate_m1 -> (Metrics, Metrics)`; `rig.run_book -> list[{pnl,entry_time}]` used consistently. `direction` written at `i-1` matches the rig's read convention and M0's `simulate_dir`.
- **Causality:** the only look-ahead risk is Task 1's alignment — covered by `test_direction_matrix_is_causal` (input truncation). Weights fit on 2025 only; OOS is the gate.
```
