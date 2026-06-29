# Instrument selector (NQ / ES) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an instrument dropdown (NQ, ES) to the dashboard and the single-layer backtester so a run is `(instrument, timeframe)`; non-NQ uses that instrument's candles/boxes/economics with a price-scaled permissive default, while NQ stays byte-identical.

**Architecture:** A new `optimize/instruments.py` facade (token set + economics + path resolver + price-scale) reusing the existing `all-stocks-signals/instruments.py` registry. Thread an optional `instrument="NQ"` arg down `data → l1_runner → engine → logbook → payload`, with payload's L1/causal caches keyed by instrument. NQ keeps its existing inline data path (golden-safe). Frontends add a `<select id="inst_select">`.

**Tech Stack:** Python (stdlib http.server, pandas, numpy), vanilla JS. No new dependencies.

## Global Constraints

- **Golden is sacred:** `python3 perf/check_golden.py` must print **6/6 MATCH** (4h $142,203/214, 2h $91,996/262, 1h $99,172/315, 15m $77,098/654, 5m $23,926/332, 2m $29,777/276) after every engine-touching task. NQ with `instrument="NQ"` (the default) must be byte-identical.
- **Instrument set:** exactly `("NQ","ES")`, default `"NQ"`. Unknown instrument → HTTP 400. ETFs are out of scope.
- **Point values:** NQ $20/pt, ES $50/pt (`POINT_VALUE` table). ES data = the same files the L2 ES-contributor already loads.
- **No cross-instrument cache bleed:** payload's `_L1_CACHE`, `_L1_CUSTOM_CACHE`, the disk L1 cache files, and `_CAUSAL_MEMO` must key on instrument.
- Run from `subprojects/Parametric-Indicators`. Python `python3`. No secrets in commits.

---

## Phase A — Backend (engine runs NQ + ES)

### Task A1: `optimize/instruments.py` — registry facade + economics

**Files:**
- Create: `optimize/instruments.py`
- Test: `optimize/test_instruments.py` (create)

**Interfaces:**
- Produces: `TOKENS: tuple[str,...]`, `POINT_VALUE: dict[str,float]`, `is_valid(token)->bool`,
  `point_value(token)->float`, `resolve_paths(token, tf)->tuple[str,str,str]` (dec_csv, min_csv, box_csv),
  `scale_factor(token)->float`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_instruments.py
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import instruments as I
from optimize import data as D


def test_tokens_and_point_values():
    assert I.TOKENS == ("NQ", "ES")
    assert I.point_value("NQ") == 20.0 and I.point_value("ES") == 50.0
    assert I.is_valid("NQ") and I.is_valid("ES") and not I.is_valid("QQQ-RTH")


def test_resolve_paths_nq_matches_current_data_module():
    dec, mn, box = I.resolve_paths("NQ", "4h")
    assert dec == str(D._RAW / "NQ_4h.csv")
    assert mn == str(D._RAW / "NQ_1m.csv")
    assert box == str(D._BOX_CSV)


def test_resolve_paths_es_exists_on_disk():
    dec, mn, box = I.resolve_paths("ES", "4h")
    assert os.path.exists(dec) and os.path.exists(mn) and os.path.exists(box)
    assert "ES" in dec


def test_scale_factor():
    assert I.scale_factor("NQ") == 1.0
    sf = I.scale_factor("ES")
    assert 0.0 < sf < 1.0           # ES (~6508) is a fraction of NQ (~23861)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_instruments.py -q`
Expected: FAIL — `No module named 'optimize.instruments'`.

- [ ] **Step 3: Create `optimize/instruments.py`**

```python
"""Parametric-Indicators instrument facade — the single place instrument identity + economics live for the
engine. Reuses the cross-subproject no-mix registry (subprojects/all-stocks-signals/instruments.py, the same
one optimize/l2/contributors/registry.py loads) and adds the point-value economics that registry lacks.

NQ resolves to the engine's EXISTING data paths (optimize/data._RAW / _BOX_CSV) so NQ stays byte-identical;
ES resolves through the registry (ALL_STOCKS/...). Default token is "NQ" everywhere."""
from __future__ import annotations

import functools
import importlib.util
import os
import sys
from pathlib import Path

import config                                   # noqa: E402 (top-level module on sys.path)
from optimize import timeframes as TF           # noqa: E402

# Mirror optimize/data.py's constants WITHOUT importing it (data.py imports this module → avoid a cycle).
_BASE = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_RAW = _BASE / TF.RAW_DIR
_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"
_INST_PATH = _BASE / "subprojects" / "all-stocks-signals" / "instruments.py"

TOKENS: tuple[str, ...] = ("NQ", "ES")                       # ETFs deferred (spec §1 scope note)
POINT_VALUE: dict[str, float] = {"NQ": 20.0, "ES": 50.0}


def _load_registry():
    """Load the no-mix registry by file path (mirrors contributors/registry._load_instruments)."""
    spec = importlib.util.spec_from_file_location("ass_instruments", _INST_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ass_instruments"] = mod         # required for Python 3.14 dataclass module lookup
    spec.loader.exec_module(mod)
    return mod.REGISTRY


_REGISTRY = _load_registry()


def is_valid(token: str) -> bool:
    return token in TOKENS


def point_value(token: str) -> float:
    return POINT_VALUE.get(token, POINT_VALUE["NQ"])


def resolve_paths(token: str, tf: str) -> tuple[str, str, str]:
    """(decision_csv, minute_csv, box_csv) for token+tf. NQ → the engine's existing paths (byte-identical);
    ES → the ALL_STOCKS registry."""
    if token == "NQ":
        return (str(_RAW / f"NQ_{tf}.csv"), str(_RAW / "NQ_1m.csv"), str(_BOX_CSV))
    inst = _REGISTRY[token]
    return (inst.candle_csv(tf), inst.candle_csv("1m"), inst.box_csv)


@functools.lru_cache(maxsize=None)
def _ref_price(token: str) -> float:
    import pandas as pd
    dec_csv, _, _ = resolve_paths(token, "4h")
    df = pd.read_csv(dec_csv)
    col = "close" if "close" in df.columns else df.columns[4]
    return float(df[col].median())


def scale_factor(token: str) -> float:
    """inst_ref / NQ_ref (median 4h close). 1.0 for NQ. Used to price-scale the non-NQ permissive default."""
    if token == "NQ":
        return 1.0
    return _ref_price(token) / _ref_price("NQ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest optimize/test_instruments.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/instruments.py optimize/test_instruments.py
git commit -m "feat(instrument): optimize/instruments.py — NQ/ES registry facade + economics + scale_factor"
```

---

### Task A2: `optimize/data.py` — instrument-parametric data loading

**Files:**
- Modify: `optimize/data.py:39-54` (`load_box`, `load_inputs`)
- Test: `optimize/test_instruments.py` (add a loading test)

**Interfaces:**
- Consumes: `instruments.resolve_paths` (A1).
- Produces: `data.load_inputs(tf_name, instrument="NQ")`, `data.load_box(instrument="NQ")`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/test_instruments.py
def test_load_inputs_es_distinct_from_nq():
    nq_dec, _, _, _, _ = D.load_inputs("4h")              # default NQ
    es_dec, _, es_box, _, _ = D.load_inputs("4h", instrument="ES")
    # different instruments → different candle frames + a non-empty ES box
    assert len(es_dec) > 0 and len(es_box) > 0
    assert nq_dec["Close"].median() != es_dec["Close"].median()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_instruments.py::test_load_inputs_es_distinct_from_nq -q`
Expected: FAIL — `load_inputs() got an unexpected keyword argument 'instrument'`.

- [ ] **Step 3: Edit `optimize/data.py`** — replace lines 39-54:

```python
def load_box(instrument: str = "NQ") -> pd.DataFrame:
    """Load the box-level frame, indexed by normalized Date (same shape as strategy.py). NQ uses the existing
    _BOX_CSV (byte-identical); other instruments resolve through the registry."""
    if instrument == "NQ":
        box_csv = str(_BOX_CSV)
    else:
        from optimize import instruments
        box_csv = instruments.resolve_paths(instrument, "4h")[2]
    c = pd.read_csv(box_csv)
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    return c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def load_inputs(tf_name: str, instrument: str = "NQ"):
    """Return (df_dec, df1, box, vf, n_split) for the given decision timeframe + instrument. NQ keeps the
    existing inline paths (golden-safe); other instruments resolve through optimize.instruments."""
    tf = TF.get(tf_name)
    if instrument == "NQ":
        dec_csv, min_csv = str(_RAW / f"NQ_{tf.name}.csv"), str(_RAW / "NQ_1m.csv")
    else:
        from optimize import instruments
        dec_csv, min_csv, _ = instruments.resolve_paths(instrument, tf.name)
    df_dec = load_data(dec_csv).sort_values("Date").reset_index(drop=True)
    df1 = load_data(min_csv).sort_values("Date").reset_index(drop=True)
    box = load_box(instrument)
    vf = vol_forecast(df_dec, df1, bar_minutes=tf.minutes)
    n_split = int((df_dec["Date"].dt.year == config.YEARS[0]).sum())
    return df_dec, df1, box, vf, n_split
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_instruments.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Golden gate (NQ default path unchanged)**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
git add optimize/data.py optimize/test_instruments.py
git commit -m "feat(instrument): data.load_inputs/load_box accept instrument= (NQ inline; ES via registry)"
```

---

### Task A3: `l1_runner` + `engine` — per-instrument point value

**Files:**
- Modify: `optimize/l2/l1_runner.py` (L1Result dataclass +`instrument` field; `run_l1` signature + pv + load_inputs call)
- Modify: `optimize/l2/engine.py:210` (pv from `l1.instrument`)
- Modify: `optimize/l2/payload.py:32` (bump `_L1_CACHE_VER`)
- Test: `optimize/l2/test_instrument_engine.py` (create)

**Interfaces:**
- Consumes: `instruments.point_value` (A1), `data.load_inputs(tf, instrument)` (A2).
- Produces: `l1_runner.run_l1(tf="4h", params=None, instrument="NQ")` returning an `L1Result` with a new
  `instrument: str` field; `engine.run_l2` reads pv from `l1.instrument`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_instrument_engine.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import l1_runner
from optimize import instruments


def _es_perm():
    sf = instruments.scale_factor("ES")
    return {"indicators": [], "k": 1, "gate_pct": 0, "flip": False, "ind_1min": False, "cooldown": 0,
            "sl_soft": 149.8 * sf, "sl_hard": 167.1 * sf, "tp": 120.2 * sf, "dd_limit": 0.0}


def test_run_l1_es_carries_instrument_and_pv():
    r = l1_runner.run_l1("4h", params=_es_perm(), instrument="ES")
    assert r.instrument == "ES"
    # ES book exists and its $ pnl uses pv=50 (sanity: non-empty ledger)
    assert len(r.df_dec) > 0


def test_run_l1_nq_default_instrument():
    r = l1_runner.run_l1("4h")
    assert r.instrument == "NQ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py -q`
Expected: FAIL — `run_l1() got an unexpected keyword argument 'instrument'` / no `instrument` attr.

- [ ] **Step 3: Add the `instrument` field to L1Result** — in `optimize/l2/l1_runner.py`, after the
  `skipped_would_be` field line (end of the dataclass, ~line 131):

```python
    instrument: str = "NQ"      # which instrument this L1 ran on (NQ default; drives point value + data paths)
```

- [ ] **Step 4: Thread instrument through `run_l1`** — edit `optimize/l2/l1_runner.py`:

Change the signature (line 135):
```python
def run_l1(tf: str = "4h", params: dict | None = None, instrument: str = "NQ") -> L1Result:
```
Change the load line (140):
```python
    df_dec, df1, box, vf, n_split = data_mod.load_inputs(tf, instrument)
```
Change the pv line (188):
```python
    pv = float(instruments.point_value(instrument))
```
Add the import near the top of the file (with the other `from optimize ...` imports):
```python
from optimize import instruments               # noqa: E402
```
Add `instrument=instrument` to the `return L1Result(...)` call (line 203-208), e.g. append it to the kwargs:
```python
                    votes_by_bar=_votes_by_bar(votes, inds, n), skipped_would_be=skipped_would_be,
                    instrument=instrument)
```

- [ ] **Step 5: Point value in `engine.run_l2`** — edit `optimize/l2/engine.py:210`:

```python
    pv = float(instruments.point_value(getattr(l1, "instrument", "NQ")))
```
Add the import at the top of `engine.py` (with its other `from optimize ...` imports):
```python
from optimize import instruments               # noqa: E402
```

- [ ] **Step 6: Bump the L1 cache version** — edit `optimize/l2/payload.py:32` (the L1Result schema changed):

```python
_L1_CACHE_VER = "v4-instrument"
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py -q`
Expected: PASS (2 passed).

- [ ] **Step 8: Golden gate**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH (NQ pv=20, default instrument; cache recomputes once under the new version).

- [ ] **Step 9: Commit**

```bash
git add optimize/l2/l1_runner.py optimize/l2/engine.py optimize/l2/payload.py optimize/l2/test_instrument_engine.py
git commit -m "feat(instrument): l1_runner/engine use per-instrument point value; L1Result.instrument; cache v4"
```

---

### Task A4: `payload` + `logbook` — instrument-keyed caches + threading

**Files:**
- Modify: `optimize/l2/payload.py` (`_l1_cache_file`, `_l1_custom_cache_file`, `run_l1_cached`,
  `_run_causal_memo`, `build_view_payload` — instrument arg + cache keys + use-frozen gate)
- Modify: `optimize/l2/logbook.py:133-140` (`run_causal` instrument arg + use_frozen gate)
- Test: `optimize/l2/test_instrument_engine.py` (add a cache-isolation test)

**Interfaces:**
- Consumes: `l1_runner.run_l1(tf, params, instrument)` (A3).
- Produces: `payload.run_l1_cached(tf, use_disk=True, params=None, instrument="NQ")`,
  `payload.build_view_payload(l1_params, l2_params, tf="4h", view="combined", instrument="NQ", l1_engine=None)`,
  `logbook.run_causal(l1_params, l2_params, tf="4h", instrument="NQ", bar_mask=None)`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_instrument_engine.py
from optimize.l2 import payload

def test_no_cross_instrument_cache_bleed():
    p = _es_perm()
    nq = payload.build_view_payload(p, payload.l2_default_params(), "4h", "l2", instrument="NQ")
    es = payload.build_view_payload(p, payload.l2_default_params(), "4h", "l2", instrument="ES")
    # identical params+tf+view but different instrument → different books (no cache bleed)
    assert nq["meta"]["n"] != es["meta"]["n"] or nq["log"] != es["log"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py::test_no_cross_instrument_cache_bleed -q`
Expected: FAIL — `build_view_payload() got an unexpected keyword argument 'instrument'`.

- [ ] **Step 3: Instrument-key the cache filenames** — edit `optimize/l2/payload.py`:

`_l1_cache_file` (lines 35-38):
```python
def _l1_cache_file(tf: str, instrument: str = "NQ") -> Path:
    h = hashlib.sha256((_L1_CACHE_VER + instrument + json.dumps(l1_runner._lean_params(tf), sort_keys=True,
                                                                default=str)).encode()).hexdigest()[:16]
    return _DISK_CACHE / f"l1_{instrument}_{tf}_{_L1_CACHE_VER}_{h}.pkl"
```
`_l1_custom_cache_file` (lines 41-45):
```python
def _l1_custom_cache_file(tf: str, h: str, instrument: str = "NQ") -> Path:
    return _DISK_CACHE / f"l1custom_{instrument}_{tf}_{_L1_CACHE_VER}_{h}.pkl"
```

- [ ] **Step 4: Thread instrument through `run_l1_cached`** — edit the whole function (lines 94-149).
  Signature:
```python
def run_l1_cached(tf: str = "4h", use_disk: bool = True, params: dict | None = None, instrument: str = "NQ"):
```
In the **custom branch** (params is not None): key by instrument and pass it down. Change:
```python
        key = (instrument, tf, h)                                  # was (tf, h)
        ...
        cf = _l1_custom_cache_file(tf, h, instrument)              # was (tf, h)
        ...
        r = l1_runner.run_l1(tf, params=validate_layer_params(params), instrument=instrument)  # add instrument
```
In the **frozen branch** (params is None — NQ only by construction): key by instrument and pass it down.
Change:
```python
    if (instrument, tf) in _L1_CACHE:                              # was: if tf in _L1_CACHE
        return _L1_CACHE[(instrument, tf)]
    cf = _l1_cache_file(tf, instrument)                            # was _l1_cache_file(tf)
    ...
            _L1_CACHE[(instrument, tf)] = r                        # both assignment sites
    ...
    r = l1_runner.run_l1(tf, instrument=instrument)                # was run_l1(tf)
    _L1_CACHE[(instrument, tf)] = r
```
(Apply the `_L1_CACHE[(instrument, tf)]` key at all three places the function currently uses `_L1_CACHE[tf]`,
and the `_L1_CUSTOM_CACHE[key]` sites already use the local `key`, now `(instrument, tf, h)`.)

- [ ] **Step 5: Thread instrument through `_run_causal_memo`** — edit `optimize/l2/payload.py:72-83`:

```python
def _run_causal_memo(l1p: dict, l2p: dict, tf: str, instrument: str = "NQ"):
    from optimize.l2 import logbook
    key = (instrument, tf, hashlib.sha256(json.dumps([l1p, l2p], sort_keys=True, default=str).encode()).hexdigest()[:16])
    r = _CAUSAL_MEMO.get(key)
    if r is None:
        if len(_CAUSAL_MEMO) >= _CAUSAL_MEMO_MAX:
            _CAUSAL_MEMO.pop(next(iter(_CAUSAL_MEMO)))
        r = _CAUSAL_MEMO[key] = logbook.run_causal(l1p, l2p, tf, instrument)
    return r
```

- [ ] **Step 6: Thread instrument through `build_view_payload`** — edit `optimize/l2/payload.py:465-499`.
  Signature:
```python
def build_view_payload(l1_params: dict, l2_params: dict, tf: str = "4h", view: str = "combined",
                       instrument: str = "NQ", l1_engine: dict | None = None) -> dict:
```
In the `view == "l1" and l1_engine` branch: pass instrument to the memo + run_l1_cached, and gate the frozen
fast path on NQ:
```python
        res = _run_causal_memo(l1p, dict(PERMISSIVE), tf, instrument)
        ...
        _l1u = (run_l1_cached(tf, instrument=instrument)
                if (instrument == "NQ" and l1p == l1_default_params(tf))
                else run_l1_cached(tf, params=l1p, instrument=instrument))
```
In the main branch (lines 496-501):
```python
    res = _run_causal_memo(l1p, l2p, tf, instrument)
    l1 = (run_l1_cached(tf, instrument=instrument)
          if (instrument == "NQ" and l1p == l1_default_params(tf))
          else run_l1_cached(tf, params=l1p, instrument=instrument))
```

- [ ] **Step 7: Thread instrument through `logbook.run_causal`** — edit `optimize/l2/logbook.py:133-140`:

```python
def run_causal(l1_params: dict, l2_params: dict, tf: str = "4h", instrument: str = "NQ", bar_mask=None) -> CausalResult:
    l1p = payload.validate_layer_params(l1_params)
    l2p = payload.validate_layer_params(l2_params)
    # frozen default → cached oracle; else custom L1. Frozen path is NQ+4h only (lean champion is NQ-4h).
    use_frozen = (instrument == "NQ" and tf == "4h" and l1p == payload.l1_default_params(tf))
    l1 = payload.run_l1_cached(tf, instrument=instrument) if use_frozen else payload.run_l1_cached(tf, params=l1p, instrument=instrument)
```

- [ ] **Step 8: Run the cache-isolation test + the A3 tests**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py -q`
Expected: PASS (3 passed).

- [ ] **Step 9: Golden gate + L2 server suite (4h causal path unchanged)**

Run: `python3 perf/check_golden.py && python3 -m pytest optimize/l2/test_l2_server.py optimize/l2/test_tf_defaults.py -q`
Expected: golden 6/6 MATCH; tests PASS.

- [ ] **Step 10: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/logbook.py optimize/l2/test_instrument_engine.py
git commit -m "feat(instrument): instrument-keyed L1/causal caches + thread instrument through payload/logbook"
```

---

### Task A5: per-instrument defaults (scaled-permissive for ES)

**Files:**
- Modify: `optimize/l2/payload.py` (add `instrument_l1_default`, `instrument_l2_default`)
- Test: `optimize/l2/test_instrument_engine.py` (add a defaults test)

**Interfaces:**
- Consumes: `instruments.scale_factor` (A1), existing `l1_default_params`/`l2_default_params`/`PERMISSIVE`.
- Produces: `payload.instrument_l1_default(instrument, tf)->dict`, `payload.instrument_l2_default(instrument)->dict`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_instrument_engine.py
def test_instrument_defaults_scaled():
    nq = payload.instrument_l1_default("NQ", "4h")
    assert nq == payload.l1_default_params("4h")            # NQ unchanged
    es = payload.instrument_l1_default("ES", "4h")
    sf = instruments.scale_factor("ES")
    assert abs(es["sl_soft"] - 149.8 * sf) < 1e-6           # point-fields scaled
    assert es["indicators"] == [] and es["gate_pct"] == 0   # permissive, scale-free fields untouched
    assert payload.instrument_l2_default("NQ") == payload.l2_default_params()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py::test_instrument_defaults_scaled -q`
Expected: FAIL — `module 'optimize.l2.payload' has no attribute 'instrument_l1_default'`.

- [ ] **Step 3: Implement** — add to `optimize/l2/payload.py` (after `l2_default_params`):

```python
def _scaled_permissive(instrument: str) -> dict:
    """The PERMISSIVE anchor with point-denominated fields scaled to the instrument's price (scale-free
    fields untouched). Gives non-NQ a runnable, sane default; the user tunes from there."""
    from optimize import instruments
    sf = instruments.scale_factor(instrument)
    p = dict(PERMISSIVE)
    for f in ("sl_soft", "sl_hard", "tp", "dd_limit"):
        if p.get(f) is not None:
            p[f] = round(float(p[f]) * sf, 4)
    return validate_layer_params(p)


def instrument_l1_default(instrument: str = "NQ", tf: str = "4h") -> dict:
    """L1 default for an instrument. NQ → the real per-TF champion (unchanged); non-NQ → scaled-permissive."""
    if instrument == "NQ":
        return l1_default_params(tf)
    return _scaled_permissive(instrument)


def instrument_l2_default(instrument: str = "NQ") -> dict:
    """L2 default. NQ → the promoted L2 champion / permissive; non-NQ → scaled-permissive (no L2 champion)."""
    if instrument == "NQ":
        return l2_default_params()
    return _scaled_permissive(instrument)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_instrument_engine.py::test_instrument_defaults_scaled -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_instrument_engine.py
git commit -m "feat(instrument): per-instrument defaults — NQ champion / non-NQ price-scaled permissive"
```

---

### Task A6: dashboard API — `?instrument=` on `combined_config` + `causal_backtest`

**Files:**
- Modify: `server.py` (`/api/combined_config` branch; `/api/causal_backtest` POST branch)
- Test: `optimize/l2/test_l2_server.py` (add an instrument test)

**Interfaces:**
- Consumes: `instruments.is_valid`/`point_value` (A1), `payload.instrument_l1_default`/`instrument_l2_default`
  (A5), `payload.build_view_payload(..., instrument=)` (A4).
- Produces: `GET /api/combined_config?tf=&instrument=` (per-instrument defaults + label + point_value; bad
  instrument → 400); `POST /api/causal_backtest` honoring body `instrument`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_l2_server.py
def test_combined_config_per_instrument():
    srv, port = _serve()
    try:
        import urllib.request, urllib.error
        nq = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        es = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?instrument=ES").read())
        assert nq.get("instrument", "NQ") == "NQ" and es["instrument"] == "ES"
        assert es["point_value"] == 50.0 and nq["point_value"] == 20.0
        assert es["l1_default"]["sl_soft"] != nq["l1_default"]["sl_soft"]   # scaled
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?instrument=QQQ")
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_l2_server.py::test_combined_config_per_instrument -q`
Expected: FAIL — `?instrument=ES` returns NQ defaults / no `instrument` key / no 400.

- [ ] **Step 3: Edit the `/api/combined_config` branch in `server.py`** (the `tf`-aware block). Replace it with:

```python
        if path == "/api/combined_config":
            from indicators import library
            from optimize import instruments as _inst
            tf = q.get("tf", ["4h"])[0]
            inst = q.get("instrument", ["NQ"])[0]
            if tf not in l2payload._TF_SET:
                return self._send(400, json.dumps({"error": f"unknown tf {tf!r}; known {list(l2payload._TF_SET)}"}))
            if not _inst.is_valid(inst):
                return self._send(400, json.dumps({"error": f"unknown instrument {inst!r}; known {list(_inst.TOKENS)}"}))
            tf_lbl = "🍃 WS lean 4h champion" if (inst == "NQ" and tf == "4h") else (
                f"🏆 WS champion {tf}" if inst == "NQ" else f"⚙ {inst} permissive (scaled) {tf}")
            return self._send(200, json.dumps({
                "indicator_schema": library.schema(),
                "l1_default": l2payload.instrument_l1_default(inst, tf),
                "l2_default": l2payload.instrument_l2_default(inst),
                "l1_profiles": l2payload.load_l1_profiles(),
                "l2_profiles": l2payload.load_l2_profiles(),
                "tf": tf, "instrument": inst, "point_value": _inst.point_value(inst),
                "l1_label": tf_lbl, "l2_label": "🔁 L2 (extend champion)"}))
```

- [ ] **Step 4: Edit the `/api/causal_backtest` POST branch** (line 238-239) to thread instrument:

```python
                out = l2payload.build_view_payload(body.get("l1") or {}, body.get("l2") or {},
                                                   body.get("tf", "4h"), body.get("view", "combined"),
                                                   instrument=body.get("instrument", "NQ"))
```

- [ ] **Step 5: Run the server test + the existing combined-config tests**

Run: `python3 -m pytest optimize/l2/test_l2_server.py::test_combined_config_per_instrument optimize/l2/test_l2_server.py::test_combined_config_per_tf optimize/l2/test_l2_server.py::test_causal_routes_smoke -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Per-instrument backend smoke (curl)**

Run:
```bash
nohup python3 server.py --port 8240 >/tmp/inst.log 2>&1 & sleep 8
curl -s "http://localhost:8240/api/combined_config?instrument=ES" | python3 -c "import sys,json;d=json.load(sys.stdin);print('ES cfg: pv=',d['point_value'],'sl_soft=',d['l1_default']['sl_soft'],'label=',d['l1_label'])"
BODY="$(curl -s 'http://localhost:8240/api/combined_config?instrument=ES&tf=4h' | python3 -c "import sys,json;c=json.load(sys.stdin);print(json.dumps({'l1':c['l1_default'],'l2':c['l2_default'],'tf':'4h','instrument':'ES','view':'l2'}))")"
curl -s -X POST http://localhost:8240/api/causal_backtest -H 'Content-Type: application/json' -d "$BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print('ES causal: n=',d['meta']['n'],'view=',d['meta']['view'])"
pkill -f "server.py --port 8240"
```
Expected: prints ES pv=50.0, a scaled sl_soft (~40), and a non-empty ES causal run.

- [ ] **Step 7: Golden gate (final Phase-A parity check)**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 8: Commit**

```bash
git add server.py optimize/l2/test_l2_server.py
git commit -m "feat(instrument): /api/combined_config?instrument= + causal_backtest instrument (NQ default, bad→400)"
```

---

## Phase B — Dashboard (`frontend/dashboard.html`)

### Task B1: instrument selector + wiring

**Files:**
- Modify: `frontend/dashboard.html` (header select; `loadConfig(instrument, tf)`; run POSTs; `collectES`)
- Test: `tests/e2e_dashboard_instrument.py` (create — Playwright E2E)

**Interfaces:**
- Consumes: `GET /api/combined_config?tf=&instrument=` (A6), `POST /api/causal_backtest` body `instrument`.
- Produces: `$('inst_select').value` is the run instrument; `loadConfig(inst, tf)` re-fetches per (inst, tf).

- [ ] **Step 1: Add the instrument select to the header** — in `frontend/dashboard.html`, inside `.hdr-right`,
  immediately **before** the `<label class="tfsel" ...>` (the TF selector), insert:

```html
    <label class="instsel" title="instrument — switches the candles/boxes/economics">
      <select id="inst_select">
        <option value="NQ" selected>NQ</option><option value="ES">ES</option>
      </select></label>
```

- [ ] **Step 2: Make `loadConfig` instrument-aware** — replace the `loadConfig` function (added by the TF
  selector) with:

```javascript
async function loadConfig(inst, tf){
  const r=await fetch('/api/combined_config?instrument='+encodeURIComponent(inst)+'&tf='+encodeURIComponent(tf));
  if(!r.ok) throw new Error('config HTTP '+r.status);
  const c=await r.json();
  DB.buildPanel($('l1_indpanel'),c.indicator_schema,DB.markDirty);
  DB.buildPanel($('l2_indpanel'),c.indicator_schema,DB.markDirty);
  DB.buildPanel($('l2_es_indpanel'),c.indicator_schema,DB.markDirty);
  fillDropdown('l1',{[c.l1_label||'L1 champion']:c.l1_default, ...(c.l1_profiles||{})});
  fillDropdown('l2',{[c.l2_label||'L2 champion']:c.l2_default, ...(c.l2_profiles||{})});
  setLayer('l1',c.l1_default); setLayer('l2',c.l2_default);
  DB.mathify(document.querySelector('aside'));
}
```

- [ ] **Step 3: Update the init + change handlers** — in the boot IIFE, replace the TF-selector init/handler
  block with one that passes both selectors and reloads on either change:

```javascript
  const reload=async()=>{ try{ await loadConfig($('inst_select').value,$('tf_select').value);
    DB.markDirty(); DB.status('switched to '+$('inst_select').value+' '+$('tf_select').value+' — click Run'); }
    catch(e){ DB.showErr('config reload failed: '+e.message); } };
  $('tf_select').addEventListener('change',reload);
  $('inst_select').addEventListener('change',reload);
  try{
    await loadConfig($('inst_select').value,$('tf_select').value);
    DB.markDirty(); DB.status('ready · best L1 + best L2 loaded · click Run');
  }catch(e){ DB.markDirty(); DB.showErr(`Cannot reach backend — start server.py then reload. (${e.message})`); }
```

- [ ] **Step 4: Thread instrument into the three run POSTs** — in `run()`, replace the `const tf=...` +
  Promise.all block with:

```javascript
    const tf=$('tf_select').value, inst=$('inst_select').value;
    const [l1,l2,comb]=await Promise.all([
      grab(fetch('/api/backtest_causal', J({...l1lay, timeframe:tf, instrument:inst}))),
      grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, instrument:inst, view:'l2'}))),
      grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, instrument:inst, view:'combined'}))),
    ]);
```

- [ ] **Step 5: JS parse check**

Run:
```bash
cd frontend && node -e "const fs=require('fs');const h=fs.readFileSync('dashboard.html','utf8');
const m=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)];let blk=m.map(x=>x[1]).join('\n').replace(/await /g,'').replace(/^const TH=DB.*/m,'const DB={TH:{},\$:()=>({value:\"NQ\"}),specsOf:()=>[],applySpecsTo:()=>{},buildPanel:()=>{},markDirty:()=>{},markClean:()=>{},status:()=>{},showErr:()=>{},mathify:()=>{},dt:()=>{},toCSV:()=>{},downloadCSV:()=>{}};');
new Function(blk); console.log('JS parse OK');"
```
Expected: `JS parse OK`

- [ ] **Step 6: Playwright E2E** — create `tests/e2e_dashboard_instrument.py` (mirrors
  `tests/e2e_dashboard_tf_selector.py`):

```python
"""Headless-browser E2E for the combined dashboard's INSTRUMENT selector.
Run: python3 server.py --port 8231 &  ;  PORT=8231 python3 tests/e2e_dashboard_instrument.py"""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8231"); BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)

def grab(posts, r):
    if r.method == "POST" and (r.url.endswith("/api/causal_backtest") or r.url.endswith("/api/backtest_causal")):
        try: posts.append({"url": r.url.rsplit("/", 1)[-1], "body": json.loads(r.post_data)})
        except Exception: pass

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page(); posts = []
    pg.on("request", lambda r: grab(posts, r))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#inst_select", state="attached")
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }", timeout=60000)
    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")

    check("init: inst == NQ", val("#inst_select") == "NQ", f"(got {val('#inst_select')!r})")
    nq_slsoft = float(val("#l1_sl_soft"))
    check("init: NQ sl_soft == 149.8", abs(nq_slsoft - 149.8) < 1e-6, f"(got {nq_slsoft})")

    pg.select_option("#inst_select", "ES")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to ES')", timeout=60000)
    es_slsoft = float(val("#l1_sl_soft"))
    check("switch ES: sl_soft scaled down (< NQ)", 0 < es_slsoft < nq_slsoft, f"(got {es_slsoft})")

    posts.clear(); pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=120000)
    insts = [pp["body"].get("instrument") for pp in posts]
    check("run ES: all 3 POSTs carry instrument=ES", insts == ["ES", "ES", "ES"], f"(got {insts})")
    br.close()

print("\n" + ("ALL E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
```

- [ ] **Step 7: Run the live E2E**

Run:
```bash
nohup python3 server.py --port 8231 >/tmp/inste2e.log 2>&1 & sleep 8
PORT=8231 python3 tests/e2e_dashboard_instrument.py; rc=$?
pkill -f "server.py --port 8231"; exit $rc
```
Expected: `ALL E2E CHECKS PASSED`.

- [ ] **Step 8: Commit**

```bash
git add frontend/dashboard.html tests/e2e_dashboard_instrument.py
git commit -m "feat(dashboard): instrument selector (NQ/ES) — re-fetch config + thread instrument into runs + E2E"
```

---

## Phase C — Backtester (`frontend/index.html` + the single-layer L1 path)

### Task C1: `strategy.py` + `/api/config` + `/api/backtest` instrument plumbing

**Files:**
- Modify: `strategy.py` (`load_inputs`/`get_bundle` instrument arg + pv)
- Modify: `server.py` (`/api/config` instrument; `/api/backtest` body instrument)
- Test: `tests/test_instrument_strategy.py` (create)

**Interfaces:**
- Consumes: `instruments.resolve_paths`/`point_value` (A1).
- Produces: `strategy.get_bundle(timeframe, instrument="NQ")`; `/api/config?instrument=`; `/api/backtest`
  honoring body `instrument`.

- [ ] **Step 1: Inspect the current `strategy.py` data-load + `get_bundle`**

Run: `grep -n "def load_inputs\|def get_bundle\|def build_payload\|NQ_\|NQ_POINT_VALUE\|def load_year_bundle\|DATA_ROOT" strategy.py`
Expected: shows the per-year `NQ_*` hardcoding (`load_inputs`/`load_year_bundle` ~lines 26-55) + `get_bundle`
+ the `NQ_POINT_VALUE` usage. (Read those exact lines before editing — they set the precise anchors.)

- [ ] **Step 2: Write the failing test**

```python
# tests/test_instrument_strategy.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strategy

def test_get_bundle_accepts_instrument():
    nq = strategy.get_bundle("4h")               # default NQ
    es = strategy.get_bundle("4h", instrument="ES")
    assert nq is not None and es is not None     # both build without error
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_instrument_strategy.py -q`
Expected: FAIL — `get_bundle() got an unexpected keyword argument 'instrument'`.

- [ ] **Step 4: Thread instrument through `strategy.py`**

Edit `strategy.load_inputs`/`load_year_bundle` to resolve candle+box paths via
`optimize.instruments.resolve_paths(instrument, tf)` for non-NQ (keep NQ on the existing per-year
`config.DATA_ROOT/<yr>_data/NQ_*` paths so NQ is byte-identical), add an `instrument="NQ"` parameter to
`get_bundle`, and replace the `config.NQ_POINT_VALUE` usages on this path with
`instruments.point_value(instrument)`. (Exact line edits per Step-1 anchors; mirror Task A2/A3's NQ-inline /
non-NQ-via-registry split.)

*Note for the implementer:* `strategy.py` loads **per-year** files (`NQ_4h_<yr>.csv`), while the registry
exposes **all-history** files (`ES_4h.csv`). For ES, load the single all-history file and skip the per-year
concatenation (the registry has no per-year ES split). Confirm the all-history ES candle columns
(`datetime,open,high,low,close,volume`) load via `loader.load_data` (they do — verified identical to NQ).

- [ ] **Step 5: Edit `server.py` `/api/config`** — add the instrument param + per-instrument point value:

```python
        if path == "/api/config":
            from indicators import library
            from optimize import timeframes as TF
            from optimize import instruments as _inst
            import presets
            inst = q.get("instrument", ["NQ"])[0]
            if not _inst.is_valid(inst):
                return self._send(400, json.dumps({"error": f"unknown instrument {inst!r}; known {list(_inst.TOKENS)}"}))
            return self._send(200, json.dumps({
                "preset": config.WINNER, "dd_cap": config.DD_CAP, "pv": _inst.point_value(inst),
                "instrument": inst, "instruments": list(_inst.TOKENS),
                "strategies": presets.strategies(),
                "bounds": {"sl_soft": [1, None], "sl_hard": [1, None], "tp": [1, None],
                           "long_sl_soft": [1, None], "long_sl_hard": [1, None], "long_tp": [1, None],
                           "short_sl_soft": [1, None], "short_sl_hard": [1, None], "short_tp": [1, None],
                           "gate_pct": [0, 100], "dd_limit": [0, None], "cooldown": [0, None],
                           "dd_cap": [1, None], "pv": [0.01, None]},
                "windows": ["full", "full+20d", "2024", "2025", "2026", "2026+20d"],
                "timeframes": list(reversed(list(TF.TIMEFRAMES))), "default_timeframe": "4h",
                "indicator_schema": library.schema()}))
```

- [ ] **Step 6: Edit `server.py` `/api/backtest`** — thread instrument into the bundle (line 258):

```python
            bundle = strategy.get_bundle((params or {}).get("timeframe"), (params or {}).get("instrument", "NQ"))
```

- [ ] **Step 7: Run tests + golden**

Run: `python3 -m pytest tests/test_instrument_strategy.py -q && python3 perf/check_golden.py`
Expected: test PASS; golden 6/6 MATCH (NQ default path unchanged).

- [ ] **Step 8: Commit**

```bash
git add strategy.py server.py tests/test_instrument_strategy.py
git commit -m "feat(instrument): strategy.py + /api/config + /api/backtest accept instrument (NQ default, bad→400)"
```

---

### Task C2: `index.html` instrument selector

**Files:**
- Modify: `frontend/index.html` (instrument select; config fetch; backtest POST; point-value display)

**Interfaces:**
- Consumes: `GET /api/config?instrument=` (C1), `POST /api/backtest` body `instrument`.

- [ ] **Step 1: Inspect index.html's config-load + run POST + point-value usage**

Run: `grep -n "api/config\|api/backtest\|timeframe\|pv\b\|point\|fetch(\|<select" frontend/index.html | head -40`
Expected: shows where `/api/config` is fetched, where `pv` is consumed (PnL display), and the `/api/backtest`
POST body. (Read those exact lines before editing.)

- [ ] **Step 2: Add an instrument `<select id="inst_select">`** near the existing timeframe control (use the
  same option markup as Task B1 Step 1: `NQ`, `ES`). On change → re-fetch `/api/config?instrument=` (so `pv`
  + bounds refresh) and mark dirty.

- [ ] **Step 3: Thread instrument into the `/api/config` fetch and the `/api/backtest` POST body** — add
  `instrument: $('inst_select').value` (or the page's element accessor) to the backtest POST JSON, and append
  `?instrument=`+value to the config fetch URL. Reuse the page's existing config-load function (factor it if
  it's inline, mirroring the `loadConfig` pattern).

- [ ] **Step 4: JS parse check**

Run: `cd frontend && node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const m=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)];new Function(m.map(x=>x[1]).join('\n').replace(/await /g,'').replace(/import .*/g,''));console.log('parse OK')" 2>&1 | tail -3`
Expected: `parse OK` (if the page uses ES modules/imports that break this check, instead load it in the
browser via Step 5 and confirm no console error).

- [ ] **Step 5: Live smoke (server + an ES backtest)**

Run:
```bash
nohup python3 server.py --port 8232 >/tmp/idx.log 2>&1 & sleep 8
curl -s "http://localhost:8232/api/config?instrument=ES" | python3 -c "import sys,json;d=json.load(sys.stdin);print('ES /api/config pv=',d['pv'],'instrument=',d['instrument'])"
curl -s -X POST http://localhost:8232/api/backtest -H 'Content-Type: application/json' -d '{"timeframe":"4h","instrument":"ES","sl_soft":40,"sl_hard":45,"tp":33,"gate_pct":0,"dd_limit":0,"cooldown":0,"flip":false,"window":"full","k":1,"indicators":[]}' | python3 -c "import sys,json;d=json.load(sys.stdin);print('ES backtest n=',d['meta']['summary']['n_taken'],'pnl=',d['meta']['summary']['pnl'])"
pkill -f "server.py --port 8232"
```
Expected: ES `pv=50.0`; a non-empty ES backtest summary.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat(backtester): index.html instrument selector (NQ/ES) — config refetch + thread instrument into runs"
```

---

## Self-Review

**Spec coverage:** §3 set+economics → A1 (`TOKENS`/`POINT_VALUE`/`resolve_paths`/`scale_factor`). §4.1 module → A1.
§4.2 threading → A2 (data), A3 (l1_runner/engine pv + L1Result.instrument), A4 (payload/logbook + instrument-keyed
caches + use-frozen gate). §4.3 per-instrument defaults → A5. §4.4 API → A6 (dashboard routes), C1 (`/api/config`
+ `/api/backtest`). §4.5 frontends → B1 (dashboard), C2 (index). §6 phasing → A/B/C. §7 testing → A1 unit, A2
load test, A4 cache-isolation, A5 defaults, A6 server+curl smoke, B1 Playwright E2E, golden after every
engine task. §8 out-of-scope respected (no ETFs in TOKENS, no per-instrument champions, vote_cache/core memo
explicitly deferred with the optimizer).

**Placeholder scan:** Phase A + B steps carry complete code. Phase C, Tasks C1-Step4 / C2-Steps 2-3, give
precise edit intent + exact anchors-to-read (`grep` step first) rather than full code, because `strategy.py`
and `index.html` weren't read line-for-line during planning; the Step-1 inspection in each makes the anchors
explicit before editing. This is deliberate (those two files are the least-touched and most variable), not a
TODO — all signatures (`get_bundle(timeframe, instrument="NQ")`, `instrument` POST/query keys) are pinned.

**Type consistency:** `instrument: str = "NQ"` default is used identically across `data.load_inputs`,
`l1_runner.run_l1`, `engine.run_l2` (via `l1.instrument`), `payload.run_l1_cached`/`build_view_payload`,
`logbook.run_causal`, and the API. `instruments.resolve_paths(token, tf)->(dec,min,box)`,
`point_value(token)->float`, `scale_factor(token)->float` defined in A1 and consumed unchanged in A2/A3/A5/C1.
`instrument_l1_default(instrument, tf)` / `instrument_l2_default(instrument)` defined in A5, consumed in A6.
`_L1_CACHE` keyed `(instrument, tf)`, `_L1_CUSTOM_CACHE` keyed `(instrument, tf, h)`, `_CAUSAL_MEMO` keyed
`(instrument, tf, hash)` — consistent across A4. Frontend `$('inst_select').value` is the single instrument
source in B1 (config reload + 3 run POSTs) and C2.
