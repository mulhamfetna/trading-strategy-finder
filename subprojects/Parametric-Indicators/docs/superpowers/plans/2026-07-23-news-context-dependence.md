# News CONTEXT-dependence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Measure whether the surprise→direction relationship differs by market context, on the same 882-release
ledger the pooled null used.

**Architecture:** A self-contained package `research/news_context/` that edits no production file. It loads the
committed ALFRED ledger, computes forward returns from the research-only 16-year frame, attaches three causal
context labels, and bootstraps the *difference* in Spearman correlation between buckets against a shuffled-label
control.

**Tech Stack:** Python 3, numpy, pandas, scipy. No new dependencies.

## Global Constraints

- **No production file may be modified.** `optimize/data.py`, `engine.py`, `study_surprise.py` are read-only.
- **Every parameter required and printed** — `K`, horizons, MA length, seeds, draws. No `dict.get(k, default)`.
- **Spearman is the primary statistic**, Pearson reported alongside (fat tails).
- **The decisive quantity is the DIFFERENCE between buckets**, bootstrapped, never overlapping per-bucket CIs.
- **Shuffled-label control is mandatory** before any positive claim; **power up front** before any null claim.
- **Bonferroni over 3 splits × 4 horizons = 12 tests.**
- **Compute on the server; all outputs scp'd back to local and committed.**
- Horizons: **5, 15, 30, 60** minutes (matching `study_surprise.py`).

---

## File Structure

| File | Responsibility |
|---|---|
| `research/news_context/__init__.py` | Package marker |
| `research/news_context/ledger.py` | Load committed surprise ledger + compute forward returns |
| `research/news_context/contexts.py` | C1/C2/C3 causal label functions |
| `research/news_context/stats.py` | Spearman/Pearson, bootstrapped difference, shuffle control, power |
| `research/news_context/run_study.py` | CLI, parameter echo, CSV output |
| `tests/test_news_context_contexts.py` | Task 2 tests |
| `tests/test_news_context_stats.py` | Task 3 tests |

Working dir: `/mnt/data/projects/trading/.worktrees/research-news-context/subprojects/Parametric-Indicators`

---

## Task 1: Ledger + outcomes

**Files:** Create `research/news_context/__init__.py`, `research/news_context/ledger.py`

**Interfaces:** Produces `load_ledger() -> pd.DataFrame` (the committed 882-row cache) and
`attach_returns(sur, df1, horizons) -> pd.DataFrame` adding `ret_{h}` columns (points, close[08:29] →
close[08:30+h]), NaN where price is missing.

- [ ] **Step 1: Implement**

```python
# research/news_context/__init__.py
"""News CONTEXT-dependence study (2026-07-23). Read-only: edits no production module."""
```

```python
# research/news_context/ledger.py
"""The 882-release surprise ledger + causal forward returns.

The ledger is the COMMITTED artifact optimize/fundamentals/surprises_cache.csv -- the exact data behind the
pooled directional null (-0.004, n=882, 99% power), so conditional results are comparable to it directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

_LEDGER = Path(__file__).resolve().parents[1] / "optimize" / "fundamentals" / "surprises_cache.csv"


def load_ledger(path: Path | None = None) -> pd.DataFrame:
    """One row per release: Date, event, actual, expected, raw_surprise, surprise_z."""
    p = Path(path) if path is not None else _LEDGER
    if not p.exists():
        raise FileNotFoundError(f"surprise ledger not found: {p}")
    d = pd.read_csv(p, parse_dates=["Date"])
    need = {"Date", "event", "surprise_z"}
    missing = need - set(d.columns)
    if missing:
        raise ValueError(f"ledger missing columns: {sorted(missing)}")
    return d.sort_values("Date").reset_index(drop=True)


def attach_returns(sur: pd.DataFrame, df1: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame:
    """Add ret_{h} = close[T+h] - close[T-1] in points, where T is the release minute.

    Anchored at close[08:29] so the entire measured move is AFTER the print (matches study_surprise.py).
    NaN when either the anchor or the horizon bar is absent from the price frame.
    """
    if not len(horizons):
        raise ValueError("horizons must be non-empty")
    px = df1.set_index("Date")["Close"]
    out = sur.copy()
    for h in horizons:
        vals = np.full(len(out), np.nan)
        for i, ts in enumerate(out["Date"]):
            a = px.get(ts - pd.Timedelta(minutes=1), np.nan)
            b = px.get(ts + pd.Timedelta(minutes=h), np.nan)
            if not (np.isnan(a) or np.isnan(b)):
                vals[i] = float(b) - float(a)
        out[f"ret_{h}"] = vals
    return out
```

- [ ] **Step 2: Commit**

```bash
git add research/news_context/__init__.py research/news_context/ledger.py
git commit -m "feat(news-context): ledger loader + causal forward returns"
```

---

## Task 2: The three causal context labels

**Files:** Create `research/news_context/contexts.py`, Test `tests/test_news_context_contexts.py`

**Interfaces:** Produces
`label_c1_policy_regime(sur, ret_col, k) -> np.ndarray` (values `"POS"`, `"NEG"`, `""` for unlabelled),
`label_c2_vol_regime(sur, regime_csv) -> np.ndarray` (`"CALM"`, `"TURBULENT"`, `""`),
`label_c3_trend(sur, df1, ma_days) -> np.ndarray` (`"UP"`, `"DOWN"`, `""`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_news_context_contexts.py
"""Context labels must be CAUSAL -- computed only from information available before the release."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.news_context.contexts import (            # noqa: E402
    label_c1_policy_regime, label_c2_vol_regime, label_c3_trend,
)


def _sur(n=100, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "Date": pd.date_range("2015-01-02 08:30", periods=n, freq="7D"),
        "surprise_z": rng.normal(0, 1, n),
        "ret_30": rng.normal(0, 10, n),
    })


def test_c1_first_k_are_unlabelled():
    s = _sur(100)
    lab = label_c1_policy_regime(s, "ret_30", k=40)
    assert (lab[:40] == "").all(), "the first k releases cannot have a trailing window"
    assert set(np.unique(lab[40:])) <= {"POS", "NEG"}


def test_c1_is_causal_future_cannot_change_a_past_label():
    s = _sur(100)
    full = label_c1_policy_regime(s, "ret_30", k=40)
    truncated = label_c1_policy_regime(s.iloc[:60].copy(), "ret_30", k=40)
    # labels for the first 60 rows must be identical -- later data must not leak backwards
    assert list(full[:60]) == list(truncated)


def test_c1_detects_a_planted_sign_flip():
    n = 120
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1, n)
    ret = np.empty(n)
    ret[:60] = z[:60] * 10 + rng.normal(0, 1, 60)     # positive relationship
    ret[60:] = -z[60:] * 10 + rng.normal(0, 1, 60)    # flipped
    s = pd.DataFrame({"Date": pd.date_range("2015-01-02 08:30", periods=n, freq="7D"),
                      "surprise_z": z, "ret_30": ret})
    lab = label_c1_policy_regime(s, "ret_30", k=30)
    assert lab[59] == "POS"        # trailing window still all-positive
    assert lab[-1] == "NEG"        # trailing window now all-flipped


def test_c1_k_must_be_positive():
    with pytest.raises(ValueError):
        label_c1_policy_regime(_sur(50), "ret_30", k=0)


def test_c3_trend_up_and_down(tmp_path):
    dates = pd.date_range("2015-01-01", periods=400, freq="D")
    df1 = pd.DataFrame({"Date": dates, "Close": np.arange(400, dtype=float) + 100})  # strictly rising
    s = pd.DataFrame({"Date": [dates[300] + pd.Timedelta(hours=8)], "surprise_z": [0.0]})
    lab = label_c3_trend(s, df1, ma_days=50)
    assert lab[0] == "UP"      # rising series is always above its trailing MA

    df1_down = pd.DataFrame({"Date": dates, "Close": (400 - np.arange(400)).astype(float) + 100})
    lab2 = label_c3_trend(s, df1_down, ma_days=50)
    assert lab2[0] == "DOWN"


def test_c2_maps_regimes_to_two_buckets(tmp_path):
    csv = tmp_path / "r.csv"
    pd.DataFrame({"date": pd.date_range("2015-01-01", periods=10, freq="D"),
                  "regime": [0, 0, 1, 1, 2, 2, 3, 3, 0, 3],
                  "n_regimes": 4}).to_csv(csv, index=False)
    s = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01 08:30", "2015-01-08 08:30",
                                              "2015-01-10 08:30"]),
                      "surprise_z": [0.0, 0.0, 0.0]})
    lab = label_c2_vol_regime(s, csv)
    assert lab[0] == "CALM"          # regime 0 -> below median
    assert lab[1] == "CALM"          # 2015-01-08 -> regime 0
    assert lab[2] == "TURBULENT"     # 2015-01-10 -> regime 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_news_context_contexts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.news_context.contexts'`

- [ ] **Step 3: Implement**

```python
# research/news_context/contexts.py
"""The three PRE-REGISTERED context splits. All causal: computable at 08:29 on the release morning.

Exactly three, fixed in the spec before any number was seen. A wider sweep would re-enter the
multiple-comparisons trap Exp 43's Bonferroni correction already caught this project in.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

UNLABELLED = ""


def label_c1_policy_regime(sur: pd.DataFrame, ret_col: str, k: int) -> np.ndarray:
    """C1 (PRIMARY) -- 'good news is good' vs 'good news is bad', from the market's own recent behaviour.

    For release i, take the STRICTLY PRIOR k releases and compute the Spearman correlation between their
    surprise and their forward return. Positive => the market has lately been treating good news as good.

    Deliberately NOT a hard-coded 2022 break: that would borrow the answer from the literature. This proxy
    is knowable in real time, so a positive result would be actionable rather than hindsight.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    z = sur["surprise_z"].to_numpy(dtype=float)
    r = sur[ret_col].to_numpy(dtype=float)
    n = len(sur)
    out = np.full(n, UNLABELLED, dtype=object)
    for i in range(k, n):
        zz, rr = z[i - k:i], r[i - k:i]
        ok = ~np.isnan(zz) & ~np.isnan(rr)
        if ok.sum() < 3:
            continue
        rho = spearmanr(zz[ok], rr[ok]).statistic
        if np.isnan(rho):
            continue
        out[i] = "POS" if rho > 0 else "NEG"
    return out


def label_c2_vol_regime(sur: pd.DataFrame, regime_csv: Path) -> np.ndarray:
    """C2 -- calm vs turbulent, reusing the causal HMM daily labels from the regime-edge workstream."""
    reg = pd.read_csv(regime_csv, parse_dates=["date"])
    m = dict(zip(reg["date"].dt.normalize(), reg["regime"]))
    med = float(np.median(reg["regime"].to_numpy(dtype=float)))
    out = np.full(len(sur), UNLABELLED, dtype=object)
    for i, ts in enumerate(sur["Date"]):
        g = m.get(pd.Timestamp(ts).normalize())
        if g is None:
            continue
        out[i] = "CALM" if float(g) <= med else "TURBULENT"
    return out


def label_c3_trend(sur: pd.DataFrame, df1: pd.DataFrame, ma_days: int) -> np.ndarray:
    """C3 -- is price above or below its trailing ma_days moving average at the release?

    The MA uses only bars STRICTLY BEFORE the release timestamp.
    """
    if ma_days < 2:
        raise ValueError(f"ma_days must be >= 2, got {ma_days}")
    px = df1[["Date", "Close"]].copy()
    px["day"] = pd.DatetimeIndex(px["Date"]).normalize()
    daily = px.groupby("day")["Close"].last().sort_index()
    ma = daily.rolling(ma_days).mean()

    out = np.full(len(sur), UNLABELLED, dtype=object)
    for i, ts in enumerate(sur["Date"]):
        day = pd.Timestamp(ts).normalize()
        prior = daily.index[daily.index < day]
        if len(prior) == 0:
            continue
        last = prior[-1]
        m, c = ma.get(last, np.nan), daily.get(last, np.nan)
        if np.isnan(m) or np.isnan(c):
            continue
        out[i] = "UP" if c > m else "DOWN"
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_news_context_contexts.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add research/news_context/contexts.py tests/test_news_context_contexts.py
git commit -m "feat(news-context): three pre-registered causal context labels"
```

---

## Task 3: Statistics — difference, shuffle control, power

**Files:** Create `research/news_context/stats.py`, Test `tests/test_news_context_stats.py`

**Interfaces:** Produces
`assoc(z, r) -> dict` (spearman + pearson + n),
`bucket_delta(z, r, labels, a, b) -> float`,
`shuffle_control(z, r, labels, a, b, draws, rng) -> tuple[float, float]` (p-value, |Δ| percentile),
`min_detectable_rho(n_a, n_b, power, alpha) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_news_context_stats.py
"""The difference statistic, the shuffled-label control, and the power floor."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.news_context.stats import (               # noqa: E402
    assoc, bucket_delta, min_detectable_rho, shuffle_control,
)


def test_assoc_finds_a_planted_monotone_relationship():
    z = np.linspace(-3, 3, 200)
    r = 5 * z                       # perfectly monotone
    a = assoc(z, r)
    assert a["spearman"] == pytest.approx(1.0, abs=1e-9)
    assert a["n"] == 200


def test_bucket_delta_detects_a_planted_sign_flip():
    rng = np.random.default_rng(0)
    z = rng.normal(0, 1, 400)
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    r = np.empty(400)
    r[:200] = z[:200] * 10
    r[200:] = -z[200:] * 10
    d = bucket_delta(z, r, lab, "A", "B")
    assert d > 1.5, "a +1 vs -1 correlation flip must produce a delta near 2"


def test_shuffle_control_rejects_a_planted_flip():
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1, 400)
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    r = np.empty(400)
    r[:200] = z[:200] * 10
    r[200:] = -z[200:] * 10
    p, _pct = shuffle_control(z, r, lab, "A", "B", draws=200, rng=np.random.default_rng(2))
    assert p < 0.01, "a real flip must beat shuffled labels"


def test_shuffle_control_passes_pure_noise():
    rng = np.random.default_rng(3)
    z = rng.normal(0, 1, 400)
    r = rng.normal(0, 1, 400)          # no relationship at all
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    p, _pct = shuffle_control(z, r, lab, "A", "B", draws=200, rng=np.random.default_rng(4))
    assert p > 0.05, "noise must NOT be called significant"


def test_min_detectable_rho_shrinks_with_n():
    small = min_detectable_rho(50, 50)
    large = min_detectable_rho(2000, 2000)
    assert large < small
    assert 0 < large < 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_news_context_stats.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# research/news_context/stats.py
"""Association, the between-bucket DIFFERENCE, the shuffled-label control, and the power floor."""
from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy.stats import norm, pearsonr, spearmanr


def assoc(z: np.ndarray, r: np.ndarray) -> dict:
    """Spearman (primary) and Pearson (reported alongside).

    Spearman leads because these tails are fat: on gold, Pearson was blind (-0.012) to a real -0.193 rank
    relationship. Reporting only Pearson here would repeat that error.
    """
    z = np.asarray(z, dtype=float)
    r = np.asarray(r, dtype=float)
    ok = ~np.isnan(z) & ~np.isnan(r)
    z, r = z[ok], r[ok]
    if len(z) < 3:
        return {"spearman": float("nan"), "pearson": float("nan"), "n": int(len(z))}
    return {"spearman": float(spearmanr(z, r).statistic),
            "pearson": float(pearsonr(z, r)[0]),
            "n": int(len(z))}


def bucket_delta(z: np.ndarray, r: np.ndarray, labels: np.ndarray, a: str, b: str) -> float:
    """rho(bucket a) - rho(bucket b), on Spearman. This is THE quantity the verdict turns on."""
    labels = np.asarray(labels, dtype=object)
    ra = assoc(z[labels == a], r[labels == a])["spearman"]
    rb = assoc(z[labels == b], r[labels == b])["spearman"]
    return float(ra - rb)


def shuffle_control(z: np.ndarray, r: np.ndarray, labels: np.ndarray, a: str, b: str,
                    draws: int, rng: np.random.Generator) -> Tuple[float, float]:
    """THE dumb control: reshuffle the context labels and see how often chance beats the real split.

    Any split of 882 numbers produces SOME spread. This asks whether the spread produced by the REAL
    context is larger than the spread produced by a meaningless one. Returns (p_value, percentile).
    """
    labels = np.asarray(labels, dtype=object)
    keep = (labels == a) | (labels == b)
    zz, rr, ll = z[keep], r[keep], labels[keep]
    real = abs(bucket_delta(zz, rr, ll, a, b))
    if np.isnan(real):
        return (float("nan"), float("nan"))

    hits = 0
    null = np.empty(draws)
    for i in range(draws):
        perm = rng.permutation(ll)
        d = abs(bucket_delta(zz, rr, perm, a, b))
        null[i] = d
        if not np.isnan(d) and d >= real:
            hits += 1
    p = (hits + 1) / (draws + 1)          # +1 so p is never exactly 0
    pct = float((null[~np.isnan(null)] < real).mean() * 100.0)
    return (float(p), pct)


def min_detectable_rho(n_a: int, n_b: int, power: float = 0.80, alpha: float = 0.05) -> float:
    """Smallest |delta rho| detectable at `power`, via the Fisher-z variance of a correlation difference.

    Reported BEFORE interpreting any null: a null that could not have detected a tradeable effect is not
    evidence of absence. This project already retracted a workstream for reporting a null at 12% power.
    """
    if n_a < 4 or n_b < 4:
        return float("nan")
    se = np.sqrt(1.0 / (n_a - 3) + 1.0 / (n_b - 3))
    need_z = (norm.ppf(1 - alpha / 2) + norm.ppf(power)) * se
    return float(np.tanh(need_z))        # back from Fisher-z to correlation units
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_news_context_stats.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add research/news_context/stats.py tests/test_news_context_stats.py
git commit -m "feat(news-context): bucket delta, shuffled-label control, power floor"
```

---

## Task 4: CLI runner

**Files:** Create `research/news_context/run_study.py`

- [ ] **Step 1: Implement**

```python
# research/news_context/run_study.py
"""Run the news CONTEXT-dependence study. SERVER ONLY (needs the 16-year 1-minute frame).

  python3 -m research.news_context.run_study --k 40 --horizons 5,15,30,60 \
      --ma-days 50 --draws 1000 --seed 20260723
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parents[2]
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from optimize.fundamentals.extended_data import load_1m_extended     # noqa: E402
from research.news_context.contexts import (                          # noqa: E402
    label_c1_policy_regime, label_c2_vol_regime, label_c3_trend,
)
from research.news_context.ledger import attach_returns, load_ledger  # noqa: E402
from research.news_context.stats import (                             # noqa: E402
    assoc, bucket_delta, min_detectable_rho, shuffle_control,
)

_REGIME_CSV = _PROJ.parent / "regime-edge" / "data" / "nq_daily_regime.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True, help="C1 trailing window in releases")
    ap.add_argument("--horizons", required=True)
    ap.add_argument("--ma-days", type=int, required=True)
    ap.add_argument("--draws", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", default="results/news_context")
    a = ap.parse_args()
    hs = [int(x) for x in a.horizons.split(",")]

    print("=" * 72)
    print("NEWS CONTEXT-DEPENDENCE -- parameters actually used")
    print(f"  C1 trailing k    : {a.k} releases")
    print(f"  horizons (min)   : {hs}")
    print(f"  C3 MA days       : {a.ma_days}")
    print(f"  shuffle draws    : {a.draws}")
    print(f"  seed             : {a.seed}")
    print(f"  regime csv       : {_REGIME_CSV}")
    n_tests = 3 * len(hs)
    print(f"  tests            : 3 splits x {len(hs)} horizons = {n_tests}")
    print(f"  Bonferroni alpha : {0.05 / n_tests:.5f}")
    print("=" * 72)

    sur = load_ledger()
    print(f"\nledger: {len(sur)} releases {sur['Date'].min().date()} -> {sur['Date'].max().date()}")
    df1 = load_1m_extended("NQ")
    print(f"price : {len(df1):,} 1-min bars {df1['Date'].min()} -> {df1['Date'].max()}")

    sur = attach_returns(sur, df1, hs)
    for h in hs:
        print(f"  ret_{h}: {int(sur[f'ret_{h}'].notna().sum())} priced releases")

    rows = []
    alpha_bonf = 0.05 / n_tests
    for h in hs:
        rc = f"ret_{h}"
        splits = {
            "C1_policy_regime": (label_c1_policy_regime(sur, rc, a.k), "POS", "NEG"),
            "C2_vol_regime":    (label_c2_vol_regime(sur, _REGIME_CSV), "CALM", "TURBULENT"),
            "C3_trend":         (label_c3_trend(sur, df1, a.ma_days), "UP", "DOWN"),
        }
        z = sur["surprise_z"].to_numpy(float)
        r = sur[rc].to_numpy(float)
        pooled = assoc(z, r)
        print(f"\n[h={h}] POOLED spearman={pooled['spearman']:+.4f} "
              f"pearson={pooled['pearson']:+.4f} n={pooled['n']}")

        for name, (lab, A, B) in splits.items():
            aa = assoc(z[lab == A], r[lab == A])
            bb = assoc(z[lab == B], r[lab == B])
            d = bucket_delta(z, r, lab, A, B)
            p, pct = shuffle_control(z, r, lab, A, B, a.draws, np.random.default_rng(a.seed))
            mde = min_detectable_rho(aa["n"], bb["n"])
            sig = (not np.isnan(p)) and p < alpha_bonf
            print(f"  {name:18s} {A}: rho={aa['spearman']:+.4f} n={aa['n']:4d} | "
                  f"{B}: rho={bb['spearman']:+.4f} n={bb['n']:4d} | "
                  f"delta={d:+.4f} shuffle_p={p:.4f} MDE={mde:.4f} "
                  f"{'*** BEATS CONTROL' if sig else 'no'}")
            rows.append({"horizon": h, "split": name, "bucket_a": A, "bucket_b": B,
                         "rho_a": aa["spearman"], "n_a": aa["n"],
                         "rho_b": bb["spearman"], "n_b": bb["n"],
                         "delta": d, "shuffle_p": p, "shuffle_pct": pct,
                         "mde_rho": mde, "bonferroni_alpha": alpha_bonf,
                         "beats_control": sig,
                         "pooled_spearman": pooled["spearman"], "pooled_n": pooled["n"]})

    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(outdir / "context_dependence.csv", index=False)
    n_sig = sum(1 for x in rows if x["beats_control"])
    print(f"\n[VERDICT INPUT] {n_sig}/{len(rows)} tests beat the shuffled control at "
          f"Bonferroni alpha={alpha_bonf:.5f}")
    print(f"wrote {outdir}/context_dependence.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify it imports**

Run: `python3 -m research.news_context.run_study --help`
Expected: argparse help listing all required args

- [ ] **Step 3: Commit**

---

## Task 5: Server run + pull outputs local + report

- [ ] **Step 1** Push branch; on server create worktree `~/Mulham/news-context`, pull.
- [ ] **Step 2** Run with `--k 40 --horizons 5,15,30,60 --ma-days 50 --draws 1000 --seed 20260723`.
- [ ] **Step 3** **scp `results/news_context/*.csv` back to local and `git add -f`** (local is the source of truth).
- [ ] **Step 4** If any test beats the control, re-run the temporal split (first half vs second half) before
      claiming anything.
- [ ] **Step 5** Write `docs/superpowers/NEWS-CTX-01-context-dependence-results.md` in house format and commit.
