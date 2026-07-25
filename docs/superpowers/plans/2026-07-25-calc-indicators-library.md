# Calc-Indicator Library Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ~125 faithful, single-OHLCV "calc" technical indicators as confirm/veto votes, auto-wired into backtester, dashboard, and optimizer.

**Architecture:** Each indicator = a vectorized numpy primitive + a thin `Indicator`/`StanceIndicator` subclass producing per-bar confirm/veto directions + one `REGISTRY`/`SCHEMA` entry. Because `fast_engine` and `engine.py` both consume the shared folded vote mask, and the optimizer loops the whole `REGISTRY`, an indicator written once auto-propagates to all three surfaces with structural parity.

**Tech Stack:** Python 3, numpy, pandas (fixtures/oracle only), pytest. TA-Lib + pandas-ta are **dev/test-only** oracles — never imported at runtime.

**Spec:** `docs/superpowers/specs/2026-07-25-calc-indicators-library-design.md`

## Global Constraints

- **Working dir:** `subprojects/Parametric-Indicators/` (the project root for this work). All paths below are relative to it unless noted.
- **No silent defaults.** Never `params.get(k, default)` to substitute a *strategy* value silently; missing required params raise `IndicatorParamError`. (Convenience defaults matching the SCHEMA default are allowed for optional tuning params, mirroring existing classes.)
- **No runtime TA-Lib.** TA-Lib / pandas-ta appear only in `requirements-dev.txt` and `tests/`/`scripts/`. A runtime `import talib` is a plan violation.
- **Parity is mandatory.** After any batch, `optimize/test_indicator_parity.py` must pass for every registered key.
- **Causal only.** No indicator may read `x[i+1]` for bar `i`. Warm-up bars vote NEUTRAL (handled by `base.Indicator.vote`).
- **One class + one key per named indicator** (families NOT collapsed) — approved 2026-07-25.
- **Branch cadence:** one feature branch per school phase (`feat/extra-ind-<school>`) → tests + parity green → merge to `dev`. Commit after every task.
- **Vote-rule conventions** (defined in Task F2, used throughout):
  - *Stance* indicator → `votes.stance_directions(stance)` where `stance ∈ {+1,-1,0}`.
  - *Zone* indicator → `votes.band_directions(v, lower, upper, mid)` (mean-reversion zones around `mid`).
  - *Magnitude veto* (unbounded vol/quant) → `votes.magnitude_veto(value, ref, threshold)`: veto BOTH sides where `value/ref < threshold` (low-activity chop veto; the box strategy is vol-seeking).
  - *Bounded veto* (e.g. choppiness, ADX) → veto BOTH sides on the indicator's natural threshold.

---

## PHASE F — Framework (do first; blocks all school phases)

### Task F1: Per-school registry aggregation

Refactor `library.py` so schools live in their own modules and merge into `REGISTRY`/`SCHEMA`. This keeps `library.py` from ballooning to 125 classes.

**Files:**
- Create: `indicators/calc/__init__.py` (empty package marker)
- Create: `indicators/lib_ma.py`, `indicators/lib_trend.py`, `indicators/lib_osc.py`, `indicators/lib_vol.py`, `indicators/lib_volume.py`, `indicators/lib_levels.py`, `indicators/lib_bw.py`, `indicators/lib_quant.py` — each starts as: `CLASSES = ()` and `SCHEMA = {}`.
- Modify: `indicators/library.py` (REGISTRY/SCHEMA construction, ~314-378)
- Test: `indicators/test_registry_merge.py`

**Interfaces:**
- Produces: each `lib_<school>` module exports `CLASSES: tuple[type[Indicator], ...]` and `SCHEMA: dict[str, dict]`. `library.REGISTRY` and `library.SCHEMA` include every school module's contributions plus the existing built-ins.

- [ ] **Step 1: Write the failing test**

```python
# indicators/test_registry_merge.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators import library

def test_every_registry_key_has_schema_and_vice_versa():
    assert set(library.REGISTRY) == set(library.SCHEMA), (
        set(library.REGISTRY) ^ set(library.SCHEMA))

def test_school_modules_merge_in():
    # built-ins still present after refactor
    for k in ("ema_trend", "rsi", "adx"):
        assert k in library.REGISTRY and k in library.SCHEMA
```

- [ ] **Step 2: Run to verify current state**

Run: `pytest indicators/test_registry_merge.py -v`
Expected: PASS for built-ins (guards the refactor doesn't drop them).

- [ ] **Step 3: Refactor `library.py` REGISTRY/SCHEMA to merge school modules**

```python
# library.py — replace the REGISTRY = {...} and after SCHEMA = {...} literal blocks
from . import lib_ma, lib_trend, lib_osc, lib_vol, lib_volume, lib_levels, lib_bw, lib_quant
_SCHOOLS = (lib_ma, lib_trend, lib_osc, lib_vol, lib_volume, lib_levels, lib_bw, lib_quant)

_BUILTINS = (EMATrend, SMATrend, MACD, VWAPTrend, KeltnerTrend, OBVTrend, CCIBreakout,
             RSIZone, StochasticZone, MFIZone, BollingerVeto, ADXVeto,
             StructureTrend, OrderBlock, FVGConfirm, IFVGConfirm, BreakerBlock, CISDConfirm)
REGISTRY = {c.key: c for c in (*_BUILTINS, *(c for m in _SCHOOLS for c in m.CLASSES))}
# SCHEMA literal for built-ins stays; then merge school schemas:
for _m in _SCHOOLS:
    for _k, _v in _m.SCHEMA.items():
        if _k in SCHEMA:
            raise KeyError(f"duplicate indicator key {_k!r}")
        SCHEMA[_k] = _v
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest indicators/test_registry_merge.py indicators/test_runner_confirm_count.py -v`
Expected: PASS (built-ins intact, empty school modules merge as no-ops).

- [ ] **Step 5: Commit**

```bash
git add indicators/calc/__init__.py indicators/lib_*.py indicators/library.py indicators/test_registry_merge.py
git commit -m "refactor(indicators): per-school registry aggregation scaffolding"
```

### Task F2: Vote-rule helpers (band + magnitude-veto)

**Files:**
- Modify: `indicators/votes.py`
- Test: `indicators/test_votes_helpers.py`

**Interfaces:**
- Produces:
  - `band_directions(v, lower, upper, mid) -> (cdir, vdir)` — generalizes `rsi_directions`; `rsi_directions(r,lo,up)` becomes `band_directions(r,lo,up,50.0)`.
  - `magnitude_veto(value, ref, threshold) -> (cdir, vdir)` — `cdir=0`; `vdir=BOTH` where `value/ref < threshold` (and both finite), else 0.
  - `both_veto(mask) -> (cdir, vdir)` — `vdir=BOTH` where `mask`, else 0; `cdir=0`.

- [ ] **Step 1: Write the failing test**

```python
# indicators/test_votes_helpers.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from indicators import votes
from indicators.base import BOTH

def test_band_directions_matches_rsi_at_mid_50():
    r = np.array([np.nan, 25.0, 45.0, 50.0, 55.0, 80.0])
    c1, v1 = votes.band_directions(r, 30, 70, 50.0)
    c2, v2 = votes.rsi_directions(r, 30, 70)
    assert np.array_equal(c1, c2) and np.array_equal(v1, v2)

def test_magnitude_veto_flags_low_ratio_both_sides():
    val = np.array([1.0, 1.0, 1.0]); ref = np.array([2.0, 1.0, np.nan])
    c, v = votes.magnitude_veto(val, ref, threshold=0.8)  # 0.5<0.8 → veto; 1.0 no; nan no
    assert v[0] == BOTH and v[1] == 0 and v[2] == 0 and not c.any()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest indicators/test_votes_helpers.py -v`
Expected: FAIL (`band_directions`/`magnitude_veto` undefined).

- [ ] **Step 3: Implement helpers in `votes.py`**

```python
from .base import BOTH  # add import

def band_directions(v, lower, upper, mid=50.0):
    x = np.asarray(v, dtype=float)
    cdir = np.zeros(len(x), dtype=np.int8); vdir = np.zeros(len(x), dtype=np.int8)
    valid = ~np.isnan(x)
    over = valid & (x >= upper); under = valid & (x <= lower)
    bull = valid & ~over & ~under & (x > mid); bear = valid & ~over & ~under & (x < mid)
    long_z = under | bull; short_z = over | bear
    cdir[long_z] = 1; vdir[long_z] = -1; cdir[short_z] = -1; vdir[short_z] = 1
    return cdir, vdir

def rsi_directions(rsi_vals, lower=30.0, upper=70.0):   # keep name; delegate
    return band_directions(rsi_vals, lower, upper, 50.0)

def magnitude_veto(value, ref, threshold):
    a = np.asarray(value, dtype=float); b = np.asarray(ref, dtype=float)
    cdir = np.zeros(len(a), dtype=np.int8); vdir = np.zeros(len(a), dtype=np.int8)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = a / b
    veto = np.isfinite(ratio) & (ratio < float(threshold))
    vdir[veto] = BOTH
    return cdir, vdir

def both_veto(mask):
    m = np.asarray(mask, dtype=bool)
    cdir = np.zeros(len(m), dtype=np.int8); vdir = np.zeros(len(m), dtype=np.int8)
    vdir[m] = BOTH
    return cdir, vdir
```

- [ ] **Step 4: Run tests (helpers + existing RSI users)**

Run: `pytest indicators/test_votes_helpers.py indicators/test_runner_confirm_count.py -v`
Expected: PASS (RSI behavior byte-identical via delegation).

- [ ] **Step 5: Commit**

```bash
git add indicators/votes.py indicators/test_votes_helpers.py
git commit -m "feat(indicators): generalized band + magnitude-veto vote helpers"
```

### Task F3: Offline oracle harness + dev deps + shared fixture

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/oracle/__init__.py`, `tests/oracle/fixture.py`, `scripts/gen_oracle.py`
- Test: `tests/oracle/test_fixture_deterministic.py`

**Interfaces:**
- Produces: `tests.oracle.fixture.ohlcv(n=300)` → deterministic dict of numpy arrays `{open,high,low,close,volume}` (fixed seed, no `Date.now`). Used by every indicator reference test.
- `scripts/gen_oracle.py` prints TA-Lib/pandas-ta reference values for a named indicator on the fixture, for pasting into tests when a bespoke assertion is easier than importing the oracle in-test.

- [ ] **Step 1: Write the failing test**

```python
# tests/oracle/test_fixture_deterministic.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from tests.oracle.fixture import ohlcv

def test_fixture_is_deterministic_and_valid():
    a, b = ohlcv(300), ohlcv(300)
    for k in ("open", "high", "low", "close", "volume"):
        assert np.array_equal(a[k], b[k])
    assert np.all(a["high"] >= a["low"])
    assert np.all(a["high"] >= a["close"]) and np.all(a["close"] >= a["low"])
    assert np.all(a["volume"] > 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/oracle/test_fixture_deterministic.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement fixture + dev deps + oracle script**

```python
# tests/oracle/fixture.py
import numpy as np
def ohlcv(n=300):
    rng = np.random.default_rng(20260725)          # fixed seed → deterministic
    ret = rng.normal(0, 0.01, n)
    close = 100.0 * np.exp(np.cumsum(ret))
    spread = np.abs(rng.normal(0, 0.4, n)) + 0.1
    high = close + spread; low = close - spread
    openp = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum.reduce([high, openp, close]); low = np.minimum.reduce([low, openp, close])
    volume = rng.integers(500, 5000, n).astype(float)
    return {"open": openp, "high": high, "low": low, "close": close, "volume": volume}
```

```text
# requirements-dev.txt
-r requirements.txt
pandas-ta==0.3.14b0
TA-Lib==0.4.28   ; platform_system != "Windows"
```

```python
# scripts/gen_oracle.py — usage: python scripts/gen_oracle.py rsi 14
import sys, numpy as np, pandas_ta as ta, pandas as pd
sys.path.insert(0, ".")
from tests.oracle.fixture import ohlcv
d = ohlcv(300); name = sys.argv[1]; args = [int(a) for a in sys.argv[2:]]
s = pd.DataFrame(d)
print(getattr(ta, name)(**{"close": s.close, "high": s.high, "low": s.low, "volume": s.volume},
                        length=args[0] if args else None).tail(10).to_string())
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/oracle/test_fixture_deterministic.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt tests/oracle scripts/gen_oracle.py
git commit -m "test(indicators): deterministic OHLCV fixture + offline oracle harness"
```

### Task F4: Parity auto-sweep over the whole registry

**Files:**
- Modify: `optimize/test_indicator_parity.py`

**Interfaces:**
- Consumes: `library.REGISTRY`, `library.SCHEMA` (each key's default params).
- Produces: a parametrized test asserting fast_engine == engine.py for each registered key enabled alone at its SCHEMA defaults.

- [ ] **Step 1: Add the parametrized sweep test**

```python
import pytest
from indicators import library

@pytest.mark.parametrize("key", sorted(library.REGISTRY))
def test_single_indicator_parity(key):
    meta = library.SCHEMA[key]
    params = {p["name"]: p["default"] for p in meta["params"]}
    spec = [{"key": key, "enabled": True, "mode": meta["mode"], "params": params}]
    # existing helper in this file that runs both engines on the same data with `spec`
    fast, slow = run_both_engines(spec)          # reuse the file's existing harness
    assert fast == slow, f"parity broke for {key}"
```

- [ ] **Step 2: Run (built-ins only for now)**

Run: `pytest optimize/test_indicator_parity.py -v`
Expected: PASS for the 18 built-ins (empty schools add nothing yet). If `run_both_engines` differs in name, adapt to the file's existing harness function.

- [ ] **Step 3: Commit**

```bash
git add optimize/test_indicator_parity.py
git commit -m "test(indicators): parity auto-sweep over full registry"
```

### Task F5: Optimizer K-cap knob (`--max-enabled`)

**Files:**
- Modify: `optimize/optimizer.py` (`_suggest_indicators` ~56-73; `search_dims` ~194-201; CLI arg parsing)
- Test: `optimize/test_max_enabled_cap.py`

**Interfaces:**
- Consumes: trial + `max_enabled: int | None`.
- Produces: `_suggest_indicators(trial, ..., max_enabled=None)` — when set, at most `max_enabled` keys may be `enabled=True`; excess enables (lowest trial-param order) are forced False (repair, keeps NSGA rectangular).

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_max_enabled_cap.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna
from optimize import optimizer

def test_max_enabled_caps_active_indicators():
    def obj(trial):
        specs = optimizer._suggest_indicators(trial, max_enabled=3)
        n_on = sum(1 for s in specs if s["enabled"])
        trial.set_user_attr("n_on", n_on)
        return float(n_on)
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    st.optimize(obj, n_trials=50)
    assert max(t.user_attrs["n_on"] for t in st.trials) <= 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest optimize/test_max_enabled_cap.py -v`
Expected: FAIL (`max_enabled` kwarg unsupported / cap not enforced).

- [ ] **Step 3: Implement the cap (repair after suggestion)**

```python
def _suggest_indicators(trial, exclude=(), only=(), prefix="", max_enabled=None):
    specs = []
    for key in library.REGISTRY:
        # ... existing per-key enable/param suggestion unchanged ...
        specs.append(spec)
    if max_enabled is not None:
        on = [s for s in specs if s.get("enabled")]
        for s in on[int(max_enabled):]:      # deterministic order = REGISTRY order
            s["enabled"] = False
    return specs
```

Wire `--max-enabled` into the CLI and pass through to `_suggest_indicators`; add it to `search_dims`' docstring note (does not change dim count, only feasible region).

- [ ] **Step 4: Run test to verify pass**

Run: `pytest optimize/test_max_enabled_cap.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/optimizer.py optimize/test_max_enabled_cap.py
git commit -m "feat(optimizer): --max-enabled cap on simultaneously-active indicators"
```

---

## EXEMPLARS — the exact TDD cycle each indicator follows

Every school-phase indicator is one task following the matching exemplar below. A task = (1) write primitive + oracle test → fail → implement → pass; (2) write the `Indicator` subclass + append its `CLASSES`/`SCHEMA` entry; (3) run the parity sweep for that key; (4) commit. The manifest rows give the deltas (formula, params, warmup, vote rule).

### EXEMPLAR-S (Stance) — `wma`

- [ ] **Primitive test** (`indicators/calc/ma.py` ← `wma`):

```python
# tests/oracle/test_ma_wma.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from indicators.calc.ma import wma
from tests.oracle.fixture import ohlcv

def test_wma_matches_pandas_oracle():
    x = ohlcv(300)["close"]; n = 10
    w = np.arange(1, n + 1)
    oracle = pd.Series(x).rolling(n).apply(lambda s: np.dot(s, w) / w.sum(), raw=True).to_numpy()
    got = wma(x, n)
    m = ~np.isnan(oracle)
    assert np.allclose(got[m], oracle[m], atol=1e-9)
    assert np.isnan(got[:n - 1]).all()   # causal warm-up
```

- [ ] **Primitive** (`indicators/calc/ma.py`):

```python
import numpy as np
def wma(x, n):
    x = np.asarray(x, dtype=float); w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(x), np.nan)
    denom = w.sum()
    for i in range(n - 1, len(x)):
        out[i] = np.dot(x[i - n + 1:i + 1], w) / denom
    return out
```
*(vectorize later via `np.convolve` if profiling flags it; correctness first.)*

- [ ] **Class + registry** (`indicators/lib_ma.py`):

```python
import numpy as np
from .base import Indicator, MarketContext
from .library import StanceIndicator   # or import StanceIndicator from where defined
from . import calc, votes

class WMATrend(StanceIndicator):
    key = "wma"
    def stance(self, ctx):
        p = self.config.params
        f = calc.ma.wma(ctx.close, int(p.get("fast", 20)))
        s = calc.ma.wma(ctx.close, int(p.get("slow", 50)))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(ctx.close > f) & (f > s)] = 1
        st[(ctx.close < f) & (f < s)] = -1
        return st
    def warmup_bars(self):
        p = self.config.params
        return max(int(p.get("fast", 20)), int(p.get("slow", 50)))

CLASSES = (WMATrend,)
SCHEMA = {"wma": {"label": "WMA trend", "mode": "confirm",
                  "params": [{"name": "fast", "default": 20, "min": 2, "max": 400, "step": 1},
                             {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1}]}}
```

- [ ] **Parity + commit:** `pytest optimize/test_indicator_parity.py -k wma -v` → PASS; commit.

### EXEMPLAR-Z (Zone) — `williams_r`

Primitive `williams_r(high,low,close,n) = -100*(HHₙ-close)/(HHₙ-LLₙ)` (range −100..0). Oracle: `pandas_ta.willr`. Class extends `Indicator`, `directions` = `votes.band_directions(wr, lower=-80, upper=-20, mid=-50.0)`. SCHEMA params: `n(14,2..100,1)`, `lower(-80,-99..-51,1)`, `upper(-20,-49..-1,1)`, mode `both`, warmup `n`.

### EXEMPLAR-V (Veto) — `choppiness`

Primitive `choppiness(high,low,close,n) = 100*log10(Σ(TR,n)/(maxHighₙ-minLowₙ))/log10(n)` (0..100). Class extends `Indicator`; `directions` = `votes.both_veto(chop >= threshold)` (high chop = no-trend → veto both). SCHEMA: `n(14,2..100,1)`, `threshold(61.8,30..80,0.1)`, mode `veto`, warmup `n`. Oracle: `pandas_ta.chop`.

---

## PHASE 1 — Moving averages (`lib_ma.py`, 19) — pattern S

Each row: primitive in `calc/ma.py`, class `<Name>Trend(StanceIndicator)` with fast/slow cross (like `wma`) unless noted. Default params `fast(20,2..400,1) slow(50,2..400,1)` unless noted; warmup `max(fast,slow)`; mode `confirm`. Oracle in parens.

| key | primitive formula | param notes (oracle) |
|---|---|---|
| `wma` | see EXEMPLAR-S | (pandas rolling) |
| `rma` | already in classic (`classic.rma`) — reuse | (Wilder) |
| `dema` | `2*ema(x,n) - ema(ema(x,n),n)` | single `n(20)` (ta.dema) |
| `tema` | `3e - 3*ema(e,n) + ema(ema(e,n),n)`, `e=ema(x,n)` | single `n` (ta.tema) |
| `tma` | `sma(sma(x, ⌈n/2⌉), ⌊n/2⌋+1)` | single `n` (ta.trima) |
| `hma` | `wma(2*wma(x,n/2) - wma(x,n), √n)` | single `n` (ta.hma) |
| `kama` | Kaufman adaptive: ER=|Δn|/Σ|Δ1|; sc=(ER*(2/3−2/31)+2/31)²; recursive | `n(10) fast(2) slow(30)` (ta.kama) |
| `vidya` | CMO-scaled EMA: `α=2/(n+1)*|CMO|`; recursive | `n(14)` (ta.vidya-equiv) |
| `alma` | Gaussian-weighted: `w_k=exp(-(k-m)²/(2s²))`, `m=offset*(n-1)`, `s=n/sigma` | `n(9) offset(0.85,0..1,0.05) sigma(6,1..12,0.5)` (ta.alma) |
| `zlema` | `ema(x + (x - x[lag]), n)`, `lag=(n-1)//2` | single `n` (ta.zlma) |
| `lsma` | rolling linear-reg endpoint value, window `n` | single `n(14)` (ta.linreg) |
| `t3` | Tillson: 6 cascaded EMAs w/ volume-factor `v` | `n(10) v(0.7,0..1,0.05)` (ta.t3) |
| `mcginley` | `md = md + (x-md)/(k*n*(x/md)⁴)`, `k=0.6`; recursive | single `n(14)` (ta.-) |
| `sine_wma` | weights `sin(π*(k+1)/(n+1))` normalized | single `n(20)` |
| `vwma` | `Σ(x*vol,n)/Σ(vol,n)` | single `n(20)` (ta.vwma) |
| `evwma` | elastic VWMA: `e = e*(V-vol)/V + x*vol/V`, `V=Σ(vol,n)`; recursive | single `n(20)` |
| `gmma` | ribbon: short group `{3,5,8,10,12,15}` all above long `{30,35,40,45,50,60}` EMAs → +1; all below → −1 | no params; warmup 60 |
| `ma_envelope` | stance = sign(close − sma(close,n)); veto when |close/sma−1|>pct | `n(20) pct(2.5%,0.1..10,0.1)` mode both |
| `ma_displaced` | sign(close − sma(close,n) shifted `d` bars forward-in-past) | `n(20) d(5,1..50,1)` |

## PHASE 2 — Trend / directional (`lib_trend.py`, 24)

Primitives in `calc/trend.py`. Pattern letter in col.

| key | pat | primitive / vote rule | params (oracle) |
|---|---|---|---|
| `ppo` | S | `100*(ema_f-ema_s)/ema_s`; stance=sign(ppo − ema(ppo,signal)) | `fast(12) slow(26) signal(9)` (ta.ppo) |
| `apo` | S | `ema_f-ema_s`; stance=sign | `fast(12) slow(26)` (ta.apo) |
| `di_cross` | S | +DI/−DI from `classic.adx` internals; stance=sign(+DI − −DI) | `n(14)` (ta.plus/minus_di) |
| `aroon` | S | up=100*(n−sinceHigh)/n, dn=100*(n−sinceLow)/n; sign(up−dn) | `n(25,2..200,1)` (ta.aroon) |
| `aroon_osc` | S | `up−dn`; stance=sign | `n(25)` (ta.aroon) |
| `psar` | S | Wilder Parabolic SAR recursion; stance=sign(close − sar) | `step(0.02,0.01..0.2,0.01) max(0.2,0.05..0.5,0.01)` (ta.psar) |
| `vortex` | S | VI+=Σ|H−L_prev|/ΣTR, VI−=Σ|L−H_prev|/ΣTR; sign(VI+−VI−) | `n(14,2..100,1)` (ta.vortex) |
| `supertrend` | S | ATR bands w/ trend flip recursion; stance=trend dir | `n(10,2..100,1) m(3.0,1..8,0.5)` (ta.supertrend) |
| `trix` | S | `roc1(ema(ema(ema(log?close,n),n),n))*1e4`; sign(trix−signal) | `n(15) signal(9)` (ta.trix) |
| `kst` | S | weighted sum of 4 smoothed ROCs; sign(kst−signal) | fixed roc/sma windows; `signal(9)` (ta.kst) |
| `coppock` | S | `wma(roc(c,11)+roc(c,14), 10)`; stance=sign | fixed (ta.coppock) |
| `dpo` | S | `close − sma(close,n) shifted (n/2+1)`; stance=sign | `n(20,2..200,1)` (ta.dpo) |
| `trend_intensity` | S | `TII = 100*Σ(dev>0)/Σ|dev|` around sma(n); band vs 50 | `n(60)` band both |
| `linreg_slope` | S | rolling OLS slope over `n`; stance=sign(slope) | `n(14,2..200,1)` (ta.linreg slope) |
| `linreg_channel` | V | veto both when |close−reg|>k*σ over `n` (extended) | `n(100) k(2.0)` both |
| `chandelier` | V | long-stop=HHₙ−m*ATR, short-stop=LLₙ+m*ATR; veto side broken | `n(22) m(3.0)` veto |
| `chande_kroll` | V | Chande-Kroll stop bands; veto broken side | `n(10) m(1.0) p(9)` veto |
| `qqe` | S | smoothed-RSI + ATR-of-RSI trailing; stance=RSI vs trail | `n(14) sf(5) f(4.236)` (ta.qqe) |
| `elder_ray` | S | bull=H−ema(n), bear=L−ema(n); +1 bull>0&rising, −1 bear<0&falling | `n(13,2..100,1)` |
| `elder_impulse` | S | ema slope AND macd-hist slope agree → that side | `n(13) macd(12,26,9)` |
| `asi` | S | Wilder Accumulation Swing Index cumulative; stance=sign(ΔASI) | `limit(3.0,0.5..10,0.5)` |
| `expma` | S | dual EMA cross (China EXPMA); sign(ema_f−ema_s) | `fast(12) slow(50)` |
| `dma` | S | `ddd=sma(c,f)−sma(c,s)`, `ama=sma(ddd,m)`; sign(ddd−ama) | `f(10) s(50) m(10)` |
| `bbi` | S | `(sma3+sma6+sma12+sma24)/4`; stance=sign(close−bbi) | no params; warmup 24 |

## PHASE 3 — Momentum / oscillator (`lib_osc.py`, 23)

Primitives in `calc/osc.py`. Zone (Z) → `votes.band_directions`; S → sign stance.

| key | pat | primitive / rule | params (oracle) |
|---|---|---|---|
| `rsi_cutler` | Z | RSI with SMA (not Wilder) smoothing | `n(14) lower(30) upper(70)` |
| `rsi_connors` | Z | `(RSI(3)+RSI(streak,2)+PctRank(roc1,100))/3` | `lower(20) upper(80)` (ta.-) |
| `stoch_rsi` | Z | stochastic of RSI(n) over `k`, %K/%D | `n(14) k(14) d(3) lower(20) upper(80)` (ta.stochrsi) |
| `kdj` | Z | stochastic K,D + J=3K−2D; band on K | `n(9) lower(20) upper(80)` |
| `williams_r` | Z | EXEMPLAR-Z | `n(14) lower(-80) upper(-20)` |
| `momentum` | S | `close − close[n]`; sign | `n(10,1..200,1)` |
| `roc` | S | `100*(close/close[n]−1)`; sign | `n(9,1..200,1)` (ta.roc) |
| `cmo` | Z | `100*(Σup−Σdn)/(Σup+Σdn)` over n; band mid 0 | `n(14) lower(-50) upper(50)` (ta.cmo) |
| `ultimate_osc` | Z | Williams UO weighted 7/14/28 | `lower(30) upper(70)` (ta.uo) |
| `tsi` | S | `100*ema(ema(Δc,r),s)/ema(ema(|Δc|,r),s)`; sign(tsi−signal) | `r(25) s(13) signal(13)` (ta.tsi) |
| `rvgi` | S | `(c−o)/(h−l)` smoothed / range smoothed; sign(rvi−signal) | `n(14) signal(4)` (ta.rvgi) |
| `smi` | Z | Blau stochastic momentum index; band mid 0 | `n(14) smooth(3) lower(-40) upper(40)` |
| `rmi` | Z | RSI-like with momentum lag `m` | `n(14) m(5) lower(30) upper(70)` |
| `cmo_chande_dmi` | Z | dynamic-period RSI (period scaled by vol) | `n(14) lower(30) upper(70)` |
| `fisher` | S | Fisher transform of normalized price; sign(fish−fish[1]) | `n(9,2..100,1)` (ta.fisher) |
| `derivative_osc` | S | `ema(ema(rsi,5? )..)` DiNapoli; sign vs signal | `rsi_n(14) s1(5) s2(3) signal(9)` |
| `ergodic_osc` | S | TSI variant (Blau ergodic); sign(erg−signal) | `r(32) s(5) signal(5)` |
| `wavetrend` | Z | LazyBear WT: ema of (ap−esa)/(0.015*d); band mid 0 | `n1(10) n2(21) lower(-60) upper(60)` |
| `disparity` | S | `100*(close/sma(close,n)−1)`; sign | `n(14,2..200,1)` |
| `balance_of_power` | S | `(close−open)/(high−low)` smoothed; sign | `n(14)` (ta.bop) |
| `pgo` | Z | Pretty Good Osc `(close−sma)/ema(TR,n)`; band mid 0 | `n(14) lower(-3) upper(3)` |
| `psy` | Z | psychological line `100*Σ(up,n)/n`; band vs 50 | `n(12) lower(25) upper(75)` |
| `bias` | S | `100*(close−sma(close,n))/sma(close,n)`; sign | `n(6,2..200,1)` |

## PHASE 4 — Volatility (`lib_vol.py`, 18)

Primitives in `calc/vol.py`. Magnitude-veto (MV) → `votes.magnitude_veto(value, ref=ema(value,m), threshold)`; bounded veto (BV) → `votes.both_veto`.

| key | pat | primitive / rule | params |
|---|---|---|---|
| `atr_norm` | MV | `atr(n)/close`; veto low-vol via magnitude_veto | `n(14) m(50) threshold(0.8,0.2..1.5,0.05)` |
| `donchian` | S | mid=(HHₙ+LLₙ)/2; stance=sign(close−mid) | `n(20,2..200,1)` |
| `starc` | V | STARC bands sma±m*ATR; veto broken side | `n(15) m(2.0)` |
| `accel_bands` | V | Price Headley accel bands; veto broken side | `n(20) f(4.0)` |
| `proj_bands` | V | Mickey Jordan projection bands (slope-projected H/L) | `n(14)` |
| `stddev` | MV | rolling std(close,n) (ddof=0); magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `hist_vol` | MV | annualized std of log-returns over n; magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `parkinson` | MV | `√(Σ(ln(H/L)²)/(4n·ln2))`; magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `garman_klass` | MV | GK range estimator; magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `rogers_satchell` | MV | RS estimator; magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `yang_zhang` | MV | YZ overnight+open-close estimator; magnitude_veto | `n(20) m(50) threshold(0.8)` |
| `chaikin_vol` | MV | `roc(ema(H−L,n), roc_n)`; magnitude_veto vs 0-centered → use both_veto when < −thr | `n(10) roc_n(10) threshold(-10)` |
| `rvi_dorsey` | Z | Relative Volatility Index (RSI of stddev); band | `n(14) lower(30) upper(70)` |
| `mass_index` | BV | `Σ(ema(H−L,9)/ema(ema(H−L,9),9), n)`; veto both when >27 (reversal bulge) | `n(25) threshold(27,20..35,0.5)` |
| `ulcer` | MV | ulcer index (RMS drawdown, n); magnitude_veto low | `n(14) m(50) threshold(0.8)` |
| `choppiness` | BV | EXEMPLAR-V | `n(14) threshold(61.8)` |
| `vol_ratio` | MV | `atr(n_fast)/atr(n_slow)`; magnitude_veto | `n_fast(5) n_slow(20) threshold(0.8)` |
| `ttm_squeeze` | BV | veto both when Bollinger(n,2) inside Keltner(n,1.5) (squeeze on) | `n(20)` |

## PHASE 5 — Volume (`lib_volume.py`, 18)

Primitives in `calc/volume.py`. Mostly Stance = sign of the flow line vs its own smoothing.

| key | pat | primitive / rule | params |
|---|---|---|---|
| `ad_line` | S | cumulative `((c−l)−(h−c))/(h−l)*vol`; sign(ad − sma(ad,n)) | `n(20)` (ta.ad) |
| `cmf` | S | `Σ(mfv,n)/Σ(vol,n)`; sign | `n(20,2..200,1)` (ta.cmf) |
| `chaikin_osc` | S | `ema(ad,3)−ema(ad,10)`; sign | `fast(3) slow(10)` (ta.adosc) |
| `pvt` | S | cumulative `roc1*vol`; sign(pvt − sma(pvt,n)) | `n(20)` (ta.pvt) |
| `tvi` | S | Trade Volume Index (tick-rule proxy on close Δ) | `min_tick(0.01) n(20)` |
| `nvi` | S | Negative Volume Index; sign(nvi − ema(nvi,255)) | `n(255)` (ta.nvi) |
| `pvi` | S | Positive Volume Index; sign(pvi − ema(pvi,255)) | `n(255)` (ta.pvi) |
| `eom` | S | Arms Ease of Movement smoothed; sign | `n(14,2..200,1)` (ta.eom) |
| `force_index` | S | `ema(Δc*vol, n)`; sign | `n(13,2..200,1)` (ta.efi) |
| `klinger` | S | Klinger VO (ema34−ema55 of volume-force); sign(kvo−signal) | `fast(34) slow(55) signal(13)` (ta.kvo) |
| `vol_osc` | S | `100*(ema(vol,f)−ema(vol,s))/ema(vol,s)`; sign | `fast(5) slow(20)` |
| `vzo` | Z | `100*ema(sign(Δc)*vol,n)/ema(vol,n)`; band mid 0 | `n(14) lower(-40) upper(40)` |
| `demand_index` | S | Sibbet demand index; sign | `n(20)` |
| `twiggs_mf` | S | Twiggs money flow (Wilder-smoothed AD/vol); sign | `n(21)` |
| `wvad` | S | `Σ((c−o)/(h−l)*vol, n)`; sign | `n(20)` |
| `bw_mfi` | S | `(h−l)/vol` regime → green/fade/fake/squat stance | no params; warmup 1 |
| `anchored_vwap` | S | VWAP anchored at each session start (reuse `classic.vwap`); sign(close−avwap) | uses `ctx.session_id`; no params |
| `volume_ratio_asia` | Z | China VR `100*Σ(up-vol)/Σ(dn-vol)` over n; band vs 100 | `n(26) lower(70) upper(150)` |

## PHASE 6 — Ichimoku / pivots / Bill Williams (`lib_levels.py` + `lib_bw.py`, 15)

Primitives: `calc/levels.py`. Pivots computed on prior-session OHLC (needs `ctx.session_id`; if absent, prior-day via a rolling daily group — reuse the project's session mapping).

| key | pat | primitive / rule | params |
|---|---|---|---|
| `ichimoku_tk_cross` | S | sign(Tenkan − Kijun), Tenkan=(HH9+LL9)/2, Kijun=(HH26+LL26)/2 | `t(9) k(26)` |
| `ichimoku_cloud` | S | +1 close>max(spanA,spanB), −1 close<min; spans shifted +26 (causal read of past span) | `t(9) k(26) b(52)` |
| `ichimoku_chikou` | S | sign(close − close[26]) (Chikou vs price) | `lag(26)` |
| `pivot_floor` | S | PP=(H+L+C)/3 prior session; stance=sign(close−PP) | no params |
| `pivot_woodie` | S | PP=(H+L+2C)/4; sign(close−PP) | no params |
| `pivot_camarilla` | S | R/S=C±range*1.1/k; stance vs C-pivot | no params |
| `pivot_fib` | S | PP + fib(0.382/0.618) of range; sign(close−PP) | no params |
| `pivot_demark` | S | DeMark X-based pivot per close vs open rule; sign(close−PP) | no params |
| `cpr` | S | central pivot range (PP, BC, TC); +1 above TC, −1 below BC | no params |
| `alligator` | S | 3 smoothed displaced MAs (13/8/5 shift 8/5/3); aligned → that side | fixed; warmup 21 |
| `fractals` | S | Williams 5-bar fractal; +1 after up-fractal broken, −1 down | `n(2,1..10,1)` |
| `awesome_osc` | S | `sma(median,5)−sma(median,34)`; sign | fixed (ta.ao) |
| `accel_osc` | S | `AO − sma(AO,5)`; sign | fixed |
| `gator` | S | |jaw−teeth| & |teeth−lips| expanding → trend side | fixed |
| `elliott_wave_osc` | S | `sma(median,5)−sma(median,34)`; sign (EWO) | fixed |

## PHASE 7 — Cycles / DeMark / quant Tier-1 (`lib_quant.py`, 8)

Primitives: `calc/quant.py`.

| key | pat | primitive / rule | params |
|---|---|---|---|
| `zscore` | Z | `(close−sma(close,n))/std(close,n)`; band mid 0 | `n(20) lower(-2) upper(2)` |
| `hurst_exp` | BV | rolling R/S Hurst over n; veto both when H<0.5 (mean-reverting = chop) | `n(100) threshold(0.5,0.3..0.7,0.01)` |
| `dfa` | BV | detrended fluctuation α over n; veto both when α<0.5 | `n(100) threshold(0.5)` |
| `autocorr` | BV | lag-1 autocorrelation over n; veto both when |ρ|<threshold (no structure) | `n(50) threshold(0.1,0..0.5,0.01)` |
| `demarker` | Z | DeMark DeMarker (DeMax/DeMin) over n; band | `n(14) lower(0.3) upper(0.7)` |
| `td_rei` | Z | TD Range Expansion Index over 5; band mid 0 | `lower(-40) upper(40)` |
| `linreg_r2` | BV | rolling R² of OLS(close~t,n); veto both when R²<threshold (no trend) | `n(20) threshold(0.2,0..0.9,0.01)` |
| `efficiency_ratio` | S | Kaufman ER `|Δn|/Σ|Δ1|` signed by Δn; +1 if ER>thr & up, −1 if ER>thr & down | `n(10) threshold(0.3,0..1,0.05)` |

---

## Self-review notes (author)

- **Spec coverage:** §2 architecture → Phase F. §3 modules → F1. §4 build manifest → Phases 1–7 (19+24+23+18+18+15+8 = 125). §6 K-cap → F5; masks/MAP-Elites already exist (reuse, no task); adopt-gate is a runtime research discipline enforced when a study is *evaluated*, not a code task. §7 verification → F3 (oracle), F4 (parity sweep), per-task parity `-k <key>`. §5 Tier-2 → out of scope (documented in spec).
- **Placeholder scan:** every task has real code or an exact formula + oracle. Manifest rows carry the precise formula, params (default/min/max/step), warmup, and vote rule — a skilled dev implements each by cloning the matching exemplar and swapping the formula.
- **Type consistency:** all classes are `StanceIndicator` (needs `stance()`) or `Indicator` (needs `directions()`); every module exports `CLASSES`/`SCHEMA` merged by F1; vote helpers `band_directions`/`magnitude_veto`/`both_veto` defined in F2 and referenced by name thereafter.
- **Known follow-ups during execution:** confirm the exact name of `test_indicator_parity.py`'s existing two-engine harness fn (Task F4 Step 2) and adapt; profile-vectorize the O(n·window) primitive loops only if the optimizer flags them (recurrence notes in `optimize/RESEARCH_indicator_recurrence_relations.md`).
