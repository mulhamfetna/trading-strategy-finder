# M2 Trend-State Kalman — Implementation Plan (vanilla)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline), task-by-task. Steps use `- [ ]` checkboxes.

**Goal:** Build the vanilla Kalman price/trend-state director for the champion's dropped 4h signals and produce its **IS (2025) / OOS (2026) Pareto fronts** (entry-rate × total-P/L) for `{4h, 1m, combined} × {re-direct, trend-filter}`, vs the champion + box-native references — deciding whether M2 earns adaptive relatives or the study redirects to M3.

**Architecture:** Two new modules under `research/kalman_fusion/`: `kalman_trend.py` (reusable 2-state local-level+trend filter → per-bar velocity z-score, causal) and `m2_trend.py` (per-4h-bar z per frame + combined, θ-sweep policy in two modes, IS/OOS evaluation). Reuses the Phase-1 rig + M1's `eligible_dropped`. Equal-weight z (no fitting). Off the production path; golden untouched.

**Tech Stack:** Python 3, numpy, pandas, pytest. Reuses `optimize.counterfactual_pause`, `research.kalman_fusion.{rig,ceiling,metrics}`, `config.YEARS`, champion `C["d"]` (4h) + `C["d1"]` (1-min).

## Global Constraints

- **Off the production path:** only `research/kalman_fusion/` files. No engine/frontend changes. Golden 6/6 stays byte-identical (verified last task).
- **Causal only:** the Kalman is a forward filter (predict→update); the filtered estimate at bar `t` uses observations ≤ `t`. Both the filter and the 4h/1m alignment get input-truncation tests.
- **No fitting:** frames combine equal-weight; the only knob is θ (swept). `q=1e-5, r=1.0` fixed defaults.
- **Exits fixed:** M2 only chooses admit + direction (payoff stays ~0.74). The bar is the 57.5% breakeven win-rate.
- **IS/OOS:** split by entry-year (2025 IS / 2026 OOS); OOS is the gate.
- **Server for the full run** (Task 5); unit tests run locally single-process.
- Run tests from the subproject root.

## File structure

| File | Responsibility |
|---|---|
| `research/kalman_fusion/kalman_trend.py` | 2-state local-level+trend Kalman → `velocity_z` |
| `research/kalman_fusion/m2_trend.py` | per-frame + combined z, θ-sweep policy (2 modes), IS/OOS eval |
| `research/kalman_fusion/run_m2.py` | CLI: sweep modes × frames × θ → IS/OOS fronts + CSV |
| `research/kalman_fusion/test_m2.py` | TDD: filter synthetic + causality, alignment causality, policy modes, high-θ=champion, monotone |

---

### Task 1: `kalman_trend.velocity_z` (2-state local-level+trend filter)

**Files:**
- Create: `research/kalman_fusion/kalman_trend.py`
- Create: `research/kalman_fusion/test_m2.py`

**Interfaces:**
- Produces: `velocity_z(log_prices, q=1e-5, r=1.0) -> (z, velocity, var)` — arrays length `len(log_prices)`; `velocity[t]` = filtered trend slope using only obs ≤ t; `var[t]` = its posterior variance; `z = velocity/sqrt(max(var,1e-12))`.

- [ ] **Step 1: Write the failing tests**

```python
# research/kalman_fusion/test_m2.py
import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.kalman_trend import velocity_z


def test_velocity_positive_on_uptrend():
    y = np.linspace(0.0, 10.0, 500)          # steady up-trend (slope +10/499)
    z, vel, var = velocity_z(y)
    assert z.shape == y.shape
    assert vel[-1] > 0 and z[-1] > 3.0        # clearly positive trend, high z
    yf = np.full(400, 5.0)                    # flat
    zf, velf, _ = velocity_z(yf)
    assert abs(velf[-1]) < 1e-2 and abs(zf[-1]) < 1.0

def test_filter_is_causal():
    rng = np.arange(600, dtype=float)
    y = np.log(1000.0 + rng + np.sin(rng / 7.0))
    _, vfull, _ = velocity_z(y)
    _, vtrunc, _ = velocity_z(y[:400])
    assert np.allclose(vtrunc, vfull[:400], atol=0, rtol=0)   # forward filter → past unchanged
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2.py -k velocity_positive -v` → FAIL (no module).

- [ ] **Step 3: Implement**

```python
# research/kalman_fusion/kalman_trend.py
"""Reusable 2-state local-level+trend Kalman (constant-velocity). Forward filter → causal per-bar velocity
+ its variance → a unitless z-score trend strength. No fitting; q/r are fixed knobs."""
from __future__ import annotations
import numpy as np


def velocity_z(log_prices, q=1e-5, r=1.0):
    y = np.asarray(log_prices, dtype=float)
    n = y.size
    vel = np.zeros(n); var = np.zeros(n)
    if n == 0:
        return np.zeros(0), vel, var
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([1.0, 0.0])
    # continuous white-noise-acceleration process covariance (dt=1), scaled by q
    Q = q * np.array([[1.0 / 3.0, 1.0 / 2.0], [1.0 / 2.0, 1.0]])
    x = np.array([y[0], 0.0]); P = np.eye(2)
    for t in range(n):
        x = F @ x; P = F @ P @ F.T + Q                       # predict
        S = float(H @ P @ H + r)                             # innovation variance
        K = (P @ H) / S                                      # gain
        x = x + K * (y[t] - float(H @ x))                    # update
        P = P - np.outer(K, H) @ P
        vel[t] = x[1]; var[t] = P[1, 1]
    z = vel / np.sqrt(np.maximum(var, 1e-12))
    return z, vel, var
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2.py -k "velocity_positive or filter_is_causal" -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/kalman_trend.py subprojects/Parametric-Indicators/research/kalman_fusion/test_m2.py
git commit -m "research(kalman): M2 2-state local-level+trend Kalman (velocity_z)"
```

---

### Task 2: `m2_trend.trend_z` — per-frame + combined z, causal

**Files:**
- Create: `research/kalman_fusion/m2_trend.py`
- Modify: `research/kalman_fusion/test_m2.py`

**Interfaces:**
- Consumes: `kalman_trend.velocity_z`, champion `C["d"]["Close"]` (4h), `C["d1"]["Close"]`+`C["d1"]["Date"]` (1-min), `C["d"]["Date"]` (4h bar starts).
- Produces: `trend_z(C, frames=("4h","1m"), q=1e-5, r=1.0) -> dict[str, np.ndarray]` — length-`n` arrays keyed by each frame + `"combined"` (equal-weight sum). Each frame's value at 4h bar `i` = that frame's z **as of the signal bar `i-1` close** (4h: `z_4h[i-1]`; 1m: last 1-min bar closed ≤ the 4h bar `i` start).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m2.py
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z


def test_trend_z_shape_and_keys():
    C = cp.load_champion("4h")
    z = trend_z(C, frames=("4h", "1m"))
    assert set(z) == {"4h", "1m", "combined"}
    assert all(v.shape == (C["n"],) for v in z.values())
    assert np.allclose(z["combined"], z["4h"] + z["1m"])

def test_trend_z_is_causal():
    C = cp.load_champion("4h")
    zf = trend_z(C, frames=("4h",))["4h"]
    m = 1400
    Ct = dict(C); Ct["d"] = C["d"].iloc[:m].copy(); Ct["sig"] = np.asarray(C["sig"])[:m]; Ct["n"] = m
    zt = trend_z(Ct, frames=("4h",))["4h"]
    assert np.allclose(zt, zf[:m])
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2.py -k trend_z -v` → FAIL (no module).

- [ ] **Step 3: Implement**

```python
# research/kalman_fusion/m2_trend.py
"""M2 — Kalman trend-state director for the champion's dropped 4h signals. Continuous price (4h + 1-min
frames, equal-weight z, NO fitting). Two decision modes (re-direct / trend-filter). Reuses Phase-1 rig +
M0 eligibility. Causal; exits fixed (payoff pinned)."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.kalman_trend import velocity_z

_MIN = np.timedelta64(1, "m")


def trend_z(C, frames=("4h", "1m"), q=1e-5, r=1.0):
    n = int(C["n"]); out = {}
    if "4h" in frames:
        z4, _, _ = velocity_z(np.log(C["d"]["Close"].to_numpy(float)), q, r)
        col = np.zeros(n); col[1:] = z4[:n - 1]              # z as of the signal bar i-1
        out["4h"] = col
    if "1m" in frames:
        d1 = C["d1"]
        z1, _, _ = velocity_z(np.log(d1["Close"].to_numpy(float)), q, r)
        m1_close = d1["Date"].to_numpy("datetime64[ns]") + _MIN     # 1-min bar close
        dec_start = C["d"]["Date"].to_numpy("datetime64[ns]")[:n]   # 4h bar i start == bar i-1 close
        j = np.searchsorted(m1_close, dec_start, side="right") - 1  # last 1-min closed ≤ signal close
        out["1m"] = np.where(j >= 0, z1[np.clip(j, 0, len(z1) - 1)], 0.0)
    out["combined"] = sum(out[f] for f in frames)
    return out
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2.py -k trend_z -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/m2_trend.py subprojects/Parametric-Indicators/research/kalman_fusion/test_m2.py
git commit -m "research(kalman): M2 per-frame + combined causal trend z (4h + 1m)"
```

---

### Task 3: `m2_trend.policy` — re-direct / trend-filter masks

**Files:**
- Modify: `research/kalman_fusion/m2_trend.py`, `research/kalman_fusion/test_m2.py`

**Interfaces:**
- Consumes: `counterfactual_pause._engine_gate`, `ceiling.eligible_dropped`, `C["sig"]`.
- Produces: `policy(C, z, theta, mode) -> (admit, direction)`. `mode ∈ {"redirect","filter"}`. `admit` = `_engine_gate(C)` ∪ {dropped bars with `|z[i]|>theta` (and, for filter, `sign(z[i])==sign(box_dir[i-1])≠0`)}; `direction[i-1]` = `sign(z[i])` (redirect) or `box_dir[i-1]` (filter); 0 elsewhere.

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m2.py
from research.kalman_fusion.m2_trend import policy
from optimize import counterfactual_pause as _cp


def test_policy_high_theta_reproduces_champion():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    admit, direction = policy(C, z, theta=1e9, mode="redirect")
    assert np.array_equal(admit, _cp._engine_gate(C))
    assert int((direction != 0).sum()) == 0

def test_redirect_flips_and_filter_skips_on_disagreement():
    C = cp.load_champion("4h")
    ed_idx = [i for i in __import__("research.kalman_fusion.ceiling", fromlist=["eligible_dropped"])
              .eligible_dropped(C)["idxs"]]
    i = ed_idx[0]
    box = int(np.sign(C["sig"][i - 1]))
    z = np.zeros(C["n"]); z[i] = -5.0 * (box if box != 0 else 1)   # trend OPPOSES the box direction
    a_r, d_r = policy(C, z, theta=1.0, mode="redirect")
    a_f, d_f = policy(C, z, theta=1.0, mode="filter")
    assert a_r[i] and d_r[i - 1] == int(np.sign(z[i]))            # re-direct admits + flips
    assert not a_f[i]                                             # filter skips the disagreement
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2.py -k "policy_high_theta or redirect_flips" -v` → FAIL (no `policy`).

- [ ] **Step 3: Implement**

```python
# append to research/kalman_fusion/m2_trend.py
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped


def policy(C, z, theta, mode):
    n = int(C["n"])
    admit = np.asarray(cp._engine_gate(C)).copy()
    direction = np.zeros(n, dtype=np.int8)
    box = np.sign(np.asarray(C["sig"]).astype(int))
    for i in eligible_dropped(C)["idxs"]:
        if abs(z[i]) <= theta:
            continue
        zdir = int(np.sign(z[i]))
        if zdir == 0:
            continue
        if mode == "redirect":
            admit[i] = True; direction[i - 1] = zdir
        elif mode == "filter":
            bdir = int(box[i - 1])
            if bdir != 0 and zdir == bdir:
                admit[i] = True; direction[i - 1] = bdir
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return admit, direction
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2.py -k "policy_high_theta or redirect_flips" -v` → PASS.

- [ ] **Step 5: Commit** — `git add -u && git commit -m "research(kalman): M2 policy (re-direct / trend-filter)"`

---

### Task 4: `m2_trend.evaluate_m2` — IS/OOS + monotone sweep

**Files:**
- Modify: `research/kalman_fusion/m2_trend.py`, `research/kalman_fusion/test_m2.py`

**Interfaces:**
- Consumes: `rig.run_book`, `ceiling.eligible_dropped`, `metrics.summarize`, `config.YEARS`, `m1_fusion.n_split`.
- Produces: `evaluate_m2(C, z, theta, mode) -> (is_metrics, oos_metrics)` — policy → `run_book` → split trades by entry-year → summarise each (eligibility denom split like M1).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_m2.py
from research.kalman_fusion.m2_trend import evaluate_m2


def test_evaluate_high_theta_is_champion():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    is_m, oos_m = evaluate_m2(C, z, theta=1e9, mode="redirect")
    champ = sum(t["pnl_points"] * C["pv"] for t in cp.champion_taken_trades(C))
    assert abs((is_m.total_pnl + oos_m.total_pnl) - champ) < 1e-6

def test_entry_rate_non_increasing_in_theta_m2():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    rates = []
    for th in (0.0, 1.0, 2.0, 1e9):
        is_m, oos_m = evaluate_m2(C, z, theta=th, mode="redirect")
        rates.append(is_m.n_entries + oos_m.n_entries)
    assert all(rates[k] >= rates[k + 1] for k in range(len(rates) - 1))
```

- [ ] **Step 2: Run to verify it fails** — `... pytest research/kalman_fusion/test_m2.py -k evaluate_high_theta -v` → FAIL.

- [ ] **Step 3: Implement**

```python
# append to research/kalman_fusion/m2_trend.py
import pandas as pd
import config
from research.kalman_fusion import rig
from research.kalman_fusion.metrics import summarize
from research.kalman_fusion.m1_fusion import n_split


def evaluate_m2(C, z, theta, mode):
    admit, direction = policy(C, z, theta, mode)
    book = rig.run_book(C, admit, direction)
    yr0 = config.YEARS[0]
    is_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year == yr0]
    oos_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year != yr0]
    ed = eligible_dropped(C); ns = n_split(C)
    is_elig = sum(1 for i in ed["idxs"] if i < ns) + \
              sum(1 for t in cp.champion_taken_trades(C) if pd.Timestamp(t["entry_time"]).year == yr0)
    oos_elig = ed["n_eligible"] - is_elig
    return (summarize(is_p, n_eligible=max(1, is_elig)),
            summarize(oos_p, n_eligible=max(1, oos_elig)))
```

- [ ] **Step 4: Run to verify it passes** — `... pytest research/kalman_fusion/test_m2.py -k "evaluate_high_theta or entry_rate_non_increasing_in_theta_m2" -v` → PASS.

- [ ] **Step 5: Commit** — `git add -u && git commit -m "research(kalman): M2 IS/OOS evaluate + monotone sweep"`

---

### Task 5: CLI + server sweep + study doc + gate

**Files:**
- Create: `research/kalman_fusion/run_m2.py`
- Modify: `docs/RESEARCH_KALMAN_FUSION_STUDY.md`

- [ ] **Step 1: Write the CLI**

```python
# research/kalman_fusion/run_m2.py
"""M2 trend-state sweep: for each frame-config × mode, sweep theta → IS/OOS front. Heavy → server."""
from __future__ import annotations
import argparse, csv
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z, evaluate_m2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--out", default="research/kalman_fusion/m2_front.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z = trend_z(C, frames=("4h", "1m"))
    thetas = [round(x, 2) for x in np.linspace(0.0, 3.0, 13)] + [1e9]
    rows = []
    for frame in ("4h", "1m", "combined"):
        for mode in ("redirect", "filter"):
            print(f"\n== frame={frame} mode={mode} ==")
            print(f"{'theta':>7} {'IS_ent':>7} {'IS_P/L':>12} {'IS_win%':>8}  {'OOS_ent':>8} {'OOS_P/L':>12} {'OOS_win%':>9}")
            for th in thetas:
                is_m, oos_m = evaluate_m2(C, Z[frame], th, mode)
                print(f"{th:7.2f} {is_m.n_entries:7d} {is_m.total_pnl:12,.0f} {100*is_m.win_rate:7.1f}%  "
                      f"{oos_m.n_entries:8d} {oos_m.total_pnl:12,.0f} {100*oos_m.win_rate:8.1f}%")
                rows.append(dict(frame=frame, mode=mode, theta=th, is_entries=is_m.n_entries,
                                 is_pnl=is_m.total_pnl, is_win=is_m.win_rate, oos_entries=oos_m.n_entries,
                                 oos_pnl=oos_m.total_pnl, oos_win=oos_m.win_rate, oos_payoff=oos_m.payoff))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Local import smoke** — `python3 -c "import research.kalman_fusion.run_m2; print('ok')"` → `ok`.

- [ ] **Step 3: Run the full sweep ON THE SERVER**

```bash
rsync -az -e "ssh -o BatchMode=yes" research/kalman_fusion/ amd-trading:/home/dev/Mulham/wsg-i/Parametric-Indicators/research/kalman_fusion/
ssh amd-trading 'cd /home/dev/Mulham/wsg-i/Parametric-Indicators && source /home/dev/Mulham/.venv/bin/activate && export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data && python3 -m research.kalman_fusion.run_m2 --out research/kalman_fusion/m2_front.csv'
```
Expected: six IS/OOS front tables. Pull `m2_front.csv`.

- [ ] **Step 4: Append M2 results + gate to `docs/RESEARCH_KALMAN_FUSION_STUDY.md`** (fill measured numbers; Mermaid, no ASCII):

```markdown
## M2 — Kalman trend-state director, NQ 4h

Best OOS point per config (vs champion OOS +$28,899, box-native OOS $<..>, breakeven win 57.5%):

| frame | mode | θ* | OOS entries | OOS P/L | OOS win% |
|---|---|--:|--:|--:|--:|
| … | … | … | … | … | … |

### Gate
- If some config's OOS front lifts total P/L over box-native at comparable entry-rate AND clears ~57.5% win →
  **build M2b (adaptive-Q/R + EKF/UKF relatives)**.
- Else → continuous trend doesn't recover the dropped flow either; **stop M2**, redirect to **M3** (regime +
  exits — the only lever that moves payoff off 0.74).
```

- [ ] **Step 5: Verify golden + commit**

Run: `python3 perf/check_golden.py` (server) → 6/6 MATCH.
```bash
git add subprojects/Parametric-Indicators/research/kalman_fusion/run_m2.py subprojects/Parametric-Indicators/docs/RESEARCH_KALMAN_FUSION_STUDY.md
git commit -m "research(kalman): M2 CLI + NQ 4h IS/OOS fronts + gate"
```

---

## Self-review

- **Spec coverage:** §2 estimator → Task 1; §3 frames/combine → Task 2; §4 modes → Task 3; §5 IS/OOS → Task 4; §6 modules/tests → all (incl. two mandatory causality guards: filter Task 1, alignment Task 2); deliverable + gate → Task 5. Adaptive relatives explicitly gated, not built.
- **Placeholder scan:** only Task 4 Step-4 `<..>` = measured numbers from Step 3. No code TODO.
- **Type consistency:** `velocity_z -> (z,vel,var)`; `trend_z -> dict[str,array]`; `policy(C,z,θ,mode) -> (admit,direction)`; `evaluate_m2 -> (Metrics,Metrics)`; `direction` written at `i-1` (rig read convention, matches M0/M1). `n_split` imported from `m1_fusion`.
- **Causality:** filter is forward-only (Task 1 truncation test); 1m/4h alignment backward-searchsorted (Task 2 truncation test); no fit → θ is the only knob (chosen on the front); OOS is the gate.
```
