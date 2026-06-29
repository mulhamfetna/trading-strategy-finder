# Instrument-aware optimizer (NQ / ES) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let both optimizers run on a chosen instrument (NQ/ES) at a chosen timeframe, producing per-instrument champions that feed the dashboard's instrument default; NQ stays byte-identical, and a short ES run produces a first real ES champion.

**Architecture:** Thread an optional `instrument="NQ"` through both optimizers' `run()`/`main()`, reusing the engine's already-instrument-aware `load_inputs`/`run_l1_cached`/`point_value`. Apply one naming rule everywhere — `suf = "" if instrument=="NQ" else f"_{instrument}"` — to study names, DB files, pareto CSVs, and champion files, so all NQ artifacts are preserved. Scale the NQ point-denominated search bounds by the instrument price ratio for non-NQ. The champion-extraction tools and the dashboard read the suffixed ES champion file.

**Tech Stack:** Python (Optuna, pandas, numpy), bash (remote runner). No new dependencies.

## Global Constraints

- **NQ unchanged:** with `instrument="NQ"` (the default) every study name, DB file, champion path, pv, and search bound is byte-identical to today. Existing NQ studies/champions must remain readable/resumable.
- **Naming rule (verbatim):** `suf = "" if instrument == "NQ" else f"_{instrument}"`. Study `{prefix}_{tf}{suf}`; DB `wsh_{tf}{suf}.db`; pareto `{tf}_wsi_pareto{suf}.csv`; L1 champions `wsh4_champions_full{suf}.json`; L2 champion `{prefix}_{tf}{suf}_champion.json`.
- **pv:** scoring uses `instruments.point_value(instrument)` (NQ 20, ES 50). `pv=None` ⇒ `backtest_metrics` keeps its `config.NQ_POINT_VALUE` default (NQ-identical).
- **Instrument set:** `instruments.TOKENS == ("NQ","ES")`; bad instrument → hard error.
- **Golden 6/6** must stay byte-identical (engine untouched).
- Run from `subprojects/Parametric-Indicators`. Python `python3`. No secrets in commits.

---

## Phase A — L1 optimizer instrument wiring

### Task A1: `folds.score_walkforward` — pv pass-through

**Files:**
- Modify: `optimize/folds.py:49-50` (signature) + `:83-84` (the `backtest_metrics` call)
- Test: `optimize/test_folds_instrument.py` (create)

**Interfaces:**
- Produces: `score_walkforward(df_dec, df1, box, vf, params, bar_duration, k=5, min_trades=5, sig_int=None, contrib=None, pv=None)` — forwards `pv` to `backtest_metrics` only when not None (None ⇒ core's NQ default).

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_folds_instrument.py
import sys, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import folds


def test_score_walkforward_accepts_pv():
    assert "pv" in inspect.signature(folds.score_walkforward).parameters
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_folds_instrument.py -q`
Expected: FAIL — `pv` not in signature.

- [ ] **Step 3: Edit `optimize/folds.py`** — signature (line 49-50):

```python
def score_walkforward(df_dec, df1, box, vf, params, bar_duration,
                      k: int = 5, min_trades: int = 5, sig_int=None, contrib=None, pv=None) -> dict:
```

And the per-fold call (line 83-84) — forward pv only when provided (None ⇒ core's NQ default, byte-identical):

```python
        _pvkw = {} if pv is None else {"pv": pv}
        m = backtest_metrics(fdec, df1, box, fvf, len(fdec), p, bar_duration,
                             gate_ref_vf=gate_ref, sig_int=fsig, contrib=cfold, **_pvkw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_folds_instrument.py -q`
Expected: PASS.

- [ ] **Step 5: Run the existing fold suite (unchanged behavior)**

Run: `python3 -m pytest optimize/test_folds_contributor.py -q`
Expected: PASS (pv defaults to None ⇒ identical scoring).

- [ ] **Step 6: Commit**

```bash
git add optimize/folds.py optimize/test_folds_instrument.py
git commit -m "feat(optimizer): score_walkforward forwards pv to backtest_metrics (None=NQ default)"
```

---

### Task A2: optimizer naming + bounds-scaling helpers

**Files:**
- Modify: `optimize/optimizer.py` (`_db_for` instrument arg; add `_study_suffix`, `_bounds_for`)
- Test: `optimize/test_optimizer_instrument.py` (create)

**Interfaces:**
- Produces: `optimizer._study_suffix(instrument) -> str` (`""`/`"_ES"`); `optimizer._db_for(tf_name, study_name, instrument="NQ") -> Path` (resolves `wsh_{tf}{suf}.db`); `optimizer._bounds_for(b: dict, dd_limit_max: float, instrument: str) -> tuple[dict, float]` (NQ → unchanged; non-NQ → sl_soft/sl_hard/tp ranges + dd_limit_max scaled by `instruments.scale_factor`).

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_optimizer_instrument.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import optimizer as OPT
from optimize import instruments


def test_study_suffix():
    assert OPT._study_suffix("NQ") == ""
    assert OPT._study_suffix("ES") == "_ES"


def test_db_for_instrument_suffix():
    nq = OPT._db_for("4h", "wsh4_4h", "NQ")
    es = OPT._db_for("4h", "wsh4_4h_ES", "ES")
    assert nq.name == "wsh_4h.db"
    assert es.name == "wsh_4h_ES.db"


def test_bounds_scaled_for_es():
    b = {"sl_soft": [10.0, 200.0], "sl_hard": [10.0, 250.0], "tp": [10.0, 180.0]}
    nb, ndd = OPT._bounds_for(b, 5000.0, "NQ")
    assert nb == b and ndd == 5000.0                       # NQ unchanged
    sf = instruments.scale_factor("ES")
    eb, edd = OPT._bounds_for(b, 5000.0, "ES")
    assert abs(eb["sl_soft"][1] - 200.0 * sf) < 1e-6        # point bounds scaled
    assert abs(edd - 5000.0 * sf) < 1e-6                    # dd_limit max scaled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_optimizer_instrument.py -q`
Expected: FAIL — `_study_suffix`/`_bounds_for` missing; `_db_for` takes 2 args.

- [ ] **Step 3: Edit `optimize/optimizer.py`** — replace `_db_for` (line 96) signature + body's `per_tf`:

```python
def _study_suffix(instrument: str) -> str:
    """'' for NQ (back-compat), '_ES' etc. for other instruments — applied to study/DB/champion names."""
    return "" if instrument == "NQ" else f"_{instrument}"


def _bounds_for(b: dict, dd_limit_max: float, instrument: str):
    """NQ → (b, dd_limit_max) unchanged. Non-NQ → the point-denominated SL/TP bounds + the dollar dd_limit
    ceiling scaled by the instrument price ratio (mirrors the scaled-permissive dashboard default), so the
    search lives in the right magnitude for that instrument instead of NQ's point scale."""
    if instrument == "NQ":
        return b, dd_limit_max
    from optimize import instruments
    sf = instruments.scale_factor(instrument)
    sb = dict(b)
    for k in ("sl_soft", "sl_hard", "tp"):
        lo, hi = b[k]
        sb[k] = [float(lo) * sf, float(hi) * sf]
    return sb, dd_limit_max * sf


def _db_for(tf_name: str, study_name: str, instrument: str = "NQ") -> Path:
```

Then inside `_db_for`, change the `per_tf` line (was `_STUDIES / f"wsh_{tf_name}.db"`):

```python
    per_tf = _STUDIES / f"wsh_{tf_name}{_study_suffix(instrument)}.db"
```

(The legacy-shared-DB fallback below it is reached only for NQ studies that predate per-TF files; ES has none, so it creates the fresh isolated `wsh_{tf}_ES.db`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_optimizer_instrument.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/optimizer.py optimize/test_optimizer_instrument.py
git commit -m "feat(optimizer): _study_suffix + instrument-keyed _db_for + _bounds_for (NQ unchanged)"
```

---

### Task A3: optimizer `run()` + `main()` — thread instrument end-to-end

**Files:**
- Modify: `optimize/optimizer.py` (`run()` signature + body lines 318/329/360-361/367-368/393-394/420-421; `main()` argparse + `run()` call)
- Test: extend `optimize/test_optimizer_instrument.py`

**Interfaces:**
- Consumes: `_study_suffix`, `_bounds_for`, `_db_for(...,instrument)` (A2); `score_walkforward(...,pv=)` (A1); `data.load_inputs(tf,instrument)`, `instruments.point_value`/`is_valid` (engine feature).
- Produces: `run(tf_name, ..., instrument="NQ")`; CLI `--instrument`.

- [ ] **Step 1: Write the failing test (ES study name + cold start)**

```python
# add to optimize/test_optimizer_instrument.py
import inspect

def test_run_accepts_instrument():
    assert "instrument" in inspect.signature(OPT.run).parameters
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_optimizer_instrument.py::test_run_accepts_instrument -q`
Expected: FAIL — `instrument` not in `run` signature.

- [ ] **Step 3: Edit `run()` signature** (line 299-304) — add `instrument="NQ"` (last param):

```python
def run(tf_name: str, n_trials: int = 200, folds: int = 5, min_trades: int = 5,
        seed: int = 1, ind_1min: bool = False, study_prefix: str = "wsh3",
        split_sltp: bool = False, warm_start: bool = True, sampler: str = "nsga3",
        objective: str = "winrate", exclude_inds: tuple = (), only_inds: tuple = (),
        dd_pnl_cap: float = DD_PNL_CAP, contrib_tokens: tuple = (),
        contrib_exclude=None, instrument: str = "NQ") -> dict:
```

- [ ] **Step 4: Edit `run()` body** — six edits:

(a) After `b = bounds[tf_name]` (line 315), resolve pv + scaled bounds:
```python
    from optimize import instruments
    pv = float(instruments.point_value(instrument))
    b, _dd_limit_max = _bounds_for(b, DD_LIMIT_MAX, instrument)
```

(b) Data load (line 318):
```python
    df_dec, df1, box, vf, n_split = data_mod.load_inputs(tf_name, instrument)
```

(c) The dd_limit suggest inside `objective` (line 329) — use the scaled ceiling:
```python
        dd_limit = trial.suggest_float("dd_limit", 0.0, _dd_limit_max)
```

(d) Fold scoring (line 360-361) — pass pv:
```python
        r = score_walkforward(df_dec, df1, box, vf, params, tf.bar_td, k=folds,
                              min_trades=min_trades, sig_int=sig_int, contrib=_contrib, pv=pv)
```

(e) Full-period feasibility backtest (line 367-368) — pass pv:
```python
        full = backtest_metrics(df_dec, df1, box, vf, n_split, dict(params, window="full"),
                                tf.bar_td, sig_int=sig_int, contrib=_contrib, pv=pv)
```

(f) Study name + DB (line 393-394):
```python
    study_name = f"{study_prefix}_{tf_name}{_study_suffix(instrument)}"
    db_path = _db_for(tf_name, study_name, instrument)
```

(g) Warm-start gate (line 420) — non-NQ has no champions to seed and NQ seeds are wrong-scaled:
```python
    if warm_start and instrument == "NQ":
```

- [ ] **Step 5: Edit `main()`** — add the arg (after `--contributors`, line 507) and validate + thread it:

```python
    ap.add_argument("--instrument", default="NQ",
                    help="instrument to optimize (NQ default, or ES). Non-NQ studies/DBs/champions are "
                         "suffixed (_ES) so NQ artifacts are untouched; SL/TP bounds auto-scale by price.")
```
After `a = ap.parse_args()` (line 508), validate:
```python
    from optimize import instruments as _inst
    if not _inst.is_valid(a.instrument):
        print(f"unknown instrument {a.instrument!r}; known {list(_inst.TOKENS)}", flush=True); return 2
```
And the `run(...)` call (line 525-529) — add `instrument=a.instrument`:
```python
    run(a.timeframe, n_trials=n_trials, folds=a.folds, min_trades=a.min_trades,
        ind_1min=a.ind_1min, study_prefix=a.study_prefix, split_sltp=a.split_sltp,
        warm_start=not a.no_warm_start, sampler=a.sampler,
        objective=a.objective, exclude_inds=_excl, only_inds=_only, dd_pnl_cap=a.dd_pnl_cap,
        contrib_tokens=contrib_tokens, instrument=a.instrument)
```

- [ ] **Step 6: Run test + a tiny ES study smoke (study created under ES name)**

Run (`run()` returns `{"timeframe","n_trials","front","front_all","dur_s"}` — verify the ES-suffixed study/DB exist rather than reading a study object off the result):
```bash
python3 -m pytest optimize/test_optimizer_instrument.py -q
WSG_DATA_ROOT=/mnt/data/projects/trading/data python3 -c "
from optimize import optimizer as OPT
res = OPT.run('4h', n_trials=3, folds=3, min_trades=1, study_prefix='estest', warm_start=False,
              exclude_inds=('ifvg','breaker','cisd','structure_trend','order_block','fvg','stochastic','adx'),
              instrument='ES')
print('ES smoke n_trials:', res['n_trials'])
assert res['n_trials'] >= 1
db = OPT._db_for('4h', 'estest_4h_ES', 'ES'); print('ES db:', db.name)
assert db.name == 'wsh_4h_ES.db' and db.exists()
import optuna; from optimize import storage as st
s = optuna.load_study(study_name='estest_4h_ES', storage=st.storage_url(db))
print('OK — ES study', s.study_name, 'has', len(s.trials), 'trials')
"
```
Expected: tests PASS; smoke prints `ES db: wsh_4h_ES.db` and `OK — ES study estest_4h_ES has N trials`.

- [ ] **Step 7: Golden gate (engine + NQ optimizer path unchanged)**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 8: Commit**

```bash
git add optimize/optimizer.py optimize/test_optimizer_instrument.py
git commit -m "feat(optimizer): L1 run/main accept --instrument (data, pv, scaled bounds, study/db suffix, cold ES)"
```

---

## Phase B — champion extraction + dashboard

### Task B1: `report_wsi.py` — per-instrument study + pareto CSV

**Files:**
- Modify: `optimize/report_wsi.py` (`_INSTRUMENT` env; `_db_for` instrument; `export_tf` study name + CSV name)
- Test: `optimize/test_report_wsi_instrument.py` (create)

**Interfaces:**
- Produces: `report_wsi` honors `WSI_INSTRUMENT` (default NQ): reads study `{_PREFIX}_{tf}{suf}` from `wsh_{tf}{suf}.db`, writes `results/{tf}_wsi_pareto{suf}.csv`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_report_wsi_instrument.py
import sys, os, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_report_wsi_instrument_suffix(monkeypatch=None):
    os.environ["WSI_INSTRUMENT"] = "ES"
    import optimize.report_wsi as rw
    importlib.reload(rw)
    assert rw._SUF == "_ES"
    # the per-instrument DB resolves to the suffixed file name
    assert rw._db_for("4h", "wsh4_4h_ES").name == "wsh_4h_ES.db"
    os.environ["WSI_INSTRUMENT"] = "NQ"; importlib.reload(rw)
    assert rw._SUF == "" and rw._db_for("4h", "wsh4_4h").name == "wsh_4h.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_report_wsi_instrument.py -q`
Expected: FAIL — `_SUF` missing.

- [ ] **Step 3: Edit `optimize/report_wsi.py`** — after `_PREFIX = ...` (line 36) add:

```python
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"
```
In `_db_for` (line 54), change the `per_tf` resolution to include the suffix:
```python
    per_tf = _STUDIES / f"wsh_{tf}{_SUF}.db"
```
In `export_tf` (line 105 + 124):
```python
    study_name = f"{_PREFIX}_{tf}{_SUF}"
    ...
    with open(_RESULTS / f"{tf}_wsi_pareto{_SUF}.csv", "w", newline="") as f:
```
(Find `_db_for`'s `per_tf = _STUDIES / f"wsh_{tf}.db"` line — replace with the suffixed form above.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_report_wsi_instrument.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/report_wsi.py optimize/test_report_wsi_instrument.py
git commit -m "feat(optimizer): report_wsi honors WSI_INSTRUMENT (suffixed study/db/pareto CSV)"
```

---

### Task B2: `build_champions_from_pareto.py` — read per-instrument pareto

**Files:**
- Modify: `optimize/build_champions_from_pareto.py` (`champion_for` reads suffixed CSV via `WSI_INSTRUMENT`)
- Test: extend `optimize/test_report_wsi_instrument.py`

**Interfaces:**
- Produces: `build_champions_from_pareto` honors `WSI_INSTRUMENT`: `champion_for(tf)` reads `results/{tf}_wsi_pareto{suf}.csv`. Output path stays `sys.argv[1]` (caller picks `wsh4_champions_full_ES.json`).

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/test_report_wsi_instrument.py
def test_build_champions_reads_suffixed_csv(tmp_path):
    import os, importlib
    os.environ["WSI_INSTRUMENT"] = "ES"
    import optimize.build_champions_from_pareto as bc
    importlib.reload(bc)
    assert bc._SUF == "_ES"
    # champion_for points at the _ES pareto CSV name
    import optimize.build_champions_from_pareto as bc2
    assert "_ES.csv" in str(bc2._RESULTS / f"2h_wsi_pareto{bc2._SUF}.csv")
    os.environ["WSI_INSTRUMENT"] = "NQ"; importlib.reload(bc)
    assert bc._SUF == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_report_wsi_instrument.py::test_build_champions_reads_suffixed_csv -q`
Expected: FAIL — `_SUF` missing.

- [ ] **Step 3: Edit `optimize/build_champions_from_pareto.py`** — after `_RESULTS = ...` (line 28) add:

```python
import os
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"
```
In `champion_for` (line 43):
```python
    csv_path = _RESULTS / f"{tf}_wsi_pareto{_SUF}.csv"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_report_wsi_instrument.py -q`
Expected: PASS (3 passed total in file).

- [ ] **Step 5: Commit**

```bash
git add optimize/build_champions_from_pareto.py optimize/test_report_wsi_instrument.py
git commit -m "feat(optimizer): build_champions reads WSI_INSTRUMENT-suffixed pareto CSV"
```

---

### Task B3: dashboard reads the ES champion file (fallback to scaled-permissive)

**Files:**
- Modify: `optimize/l2/payload.py` (`instrument_l1_default`; add `_instrument_champions_path`)
- Test: `optimize/l2/test_instrument_champion_default.py` (create)

**Interfaces:**
- Consumes: `_champion_layer_params` (existing), `_scaled_permissive` (existing).
- Produces: `instrument_l1_default("ES", tf)` returns the optimized champion from `results/wsh4_champions_full_ES.json` when present (has `tf`), else scaled-permissive.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_instrument_champion_default.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import payload

_ES_CH = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full_ES.json"


def test_es_default_uses_champion_when_present(tmp_path, monkeypatch):
    # craft a tiny ES champion file at the real path the dashboard reads
    created = not _ES_CH.exists()
    if created:
        _ES_CH.write_text(json.dumps({"4h": {"box": {"sl_soft": 41.0, "sl_hard": 46.0, "tp": 33.0,
            "gate_pct": 50.0, "dd_limit": 1000.0, "cooldown": 0, "flip": False, "k": 1}, "indicators": {}}}))
    try:
        p = payload.instrument_l1_default("ES", "4h")
        assert p["sl_soft"] == 41.0 and p["ind_1min"] is True     # champion box, not scaled-permissive
    finally:
        if created:
            _ES_CH.unlink()


def test_es_default_falls_back_when_absent():
    # with no champion for a TF, ES falls back to scaled-permissive (indicators empty, gate 0)
    p = payload.instrument_l1_default("ES", "2m")
    if not _ES_CH.exists():
        assert p["indicators"] == [] and p["gate_pct"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_instrument_champion_default.py -q`
Expected: FAIL — `instrument_l1_default("ES","4h")` returns scaled-permissive (sl_soft ≈ 40.86, not 41.0).

- [ ] **Step 3: Edit `optimize/l2/payload.py`** — replace `instrument_l1_default` (line 389):

```python
def _instrument_champions_path(instrument: str) -> Path:
    """Per-instrument optimized-champions file (same naming the optimizer writes). NQ uses _WSH4_CHAMPS."""
    suf = "" if instrument == "NQ" else f"_{instrument}"
    return _WSH4_CHAMPS.with_name(f"wsh4_champions_full{suf}.json")


def instrument_l1_default(instrument: str = "NQ", tf: str = "4h") -> dict:
    """L1 default for an instrument. NQ → the real per-TF champion (unchanged). Non-NQ → that instrument's
    OPTIMIZED champion (results/wsh4_champions_full_<INST>.json) when present for the TF, else the
    price-scaled permissive default."""
    if instrument == "NQ":
        return l1_default_params(tf)
    cf = _instrument_champions_path(instrument)
    if cf.exists():
        try:
            champs = json.loads(cf.read_text())
            if tf in champs:
                return _champion_layer_params(tf, champs[tf])
        except Exception:
            pass                                          # malformed/partial → fall back
    return _scaled_permissive(instrument)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_instrument_champion_default.py optimize/l2/test_instrument_engine.py -q`
Expected: PASS (the engine tests still pass — ES falls back to scaled-permissive when no champion file).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_instrument_champion_default.py
git commit -m "feat(dashboard): instrument_l1_default reads optimized ES champion (fallback scaled-permissive)"
```

---

## Phase C — L2 optimizer instrument wiring

### Task C1: `l2/optimize.py` — instrument through run/main/_export_champion

**Files:**
- Modify: `optimize/l2/optimize.py` (`run()` line 71-79/106-107; `_export_champion` line 133-137; `main()` argparse + calls)
- Test: `optimize/l2/test_l2_optimize_instrument.py` (create)

**Interfaces:**
- Consumes: `payload.run_l1_cached(tf, params, instrument)`, `OPT._db_for(tf, name, instrument)`, `OPT._study_suffix` (A2).
- Produces: `l2.optimize.run(..., instrument="NQ")`; `_export_champion(..., instrument="NQ")` → `{prefix}_{tf}{suf}_champion.json`; CLI `--instrument`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_l2_optimize_instrument.py
import sys, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import optimize as l2opt


def test_run_and_export_accept_instrument():
    assert "instrument" in inspect.signature(l2opt.run).parameters
    assert "instrument" in inspect.signature(l2opt._export_champion).parameters


def test_export_champion_es_filename(tmp_path):
    champ = {"params": {"sl_soft": 40}, "in_sample": {"pnl": 1.0, "n": 5}, "oos": {"pnl": 1.0, "n": 5}}
    p = l2opt._export_champion(champ, "4h", tmp_path, prefix="l2v1", instrument="ES")
    assert p.name == "l2v1_4h_ES_champion.json"
    nq = l2opt._export_champion(champ, "4h", tmp_path, prefix="l2v1", instrument="NQ")
    assert nq.name == "l2v1_4h_champion.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_l2_optimize_instrument.py -q`
Expected: FAIL — `instrument` not in signatures.

- [ ] **Step 3: Edit `run()`** (line 71-74 signature; 79 + 106-107 body):

Signature — add `instrument="NQ"` (last param):
```python
def run(n_trials: int = 200, tf: str = "4h", study_prefix: str = "l2v1", seed: int = 1,
        min_trades: int = 5, sampler: str = "nsga3", storage_url: str | None = None,
        dd_pnl_cap: float = OPT.DD_PNL_CAP, l1_params: dict | None = None,
        contrib_tokens=(), contrib_exclude=SMC_COMMITTEE_KEYS, instrument: str = "NQ") -> dict:
```
L1 run (line 79) — pass instrument (pv flows through the L1Result into engine.run_l2):
```python
    l1 = (payload.run_l1_cached(tf, instrument=instrument) if l1_params is None
          else payload.run_l1_cached(tf, params=l1_params, instrument=instrument))
```
Study name + DB (line 106-107):
```python
    study_name = f"{study_prefix}_{tf}{OPT._study_suffix(instrument)}"
    url = storage_url or study_storage.storage_url(OPT._db_for(tf, study_name, instrument))
```

- [ ] **Step 4: Edit `_export_champion`** (line 133-137) — add instrument + suffix the filename:

```python
def _export_champion(champion: dict, tf: str, out_dir, prefix: str = "l2v1",
                     contrib_smc_excluded=(), instrument: str = "NQ") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{tf}{OPT._study_suffix(instrument)}_champion.json"
    rec = {"tf": tf, "prefix": prefix, "instrument": instrument, "params": champion["params"],
           "in_sample": champion["in_sample"], "oos": champion["oos"]}
```
(Keep the rest of the function body unchanged.)

- [ ] **Step 5: Edit `main()`** — add the arg (after `--out`, line 177) + thread it:

```python
    ap.add_argument("--instrument", default="NQ",
                    help="instrument to optimize L2 on (NQ default, or ES). Non-NQ studies/champions are "
                         "suffixed (_ES); L1 residuals + pv follow the instrument automatically.")
```
After `a = ap.parse_args()` (line 178), validate:
```python
    from optimize import instruments as _inst
    if not _inst.is_valid(a.instrument):
        print(f"unknown instrument {a.instrument!r}; known {list(_inst.TOKENS)}", flush=True); return 2
```
`run(...)` call (line 188-190) — add `instrument=a.instrument`:
```python
    res = run(n_trials=a.trials, tf=a.tf, study_prefix=a.prefix, seed=a.seed,
              min_trades=a.min_trades, sampler=a.sampler, storage_url=a.storage_url, l1_params=l1_params,
              contrib_tokens=contrib_tokens, contrib_exclude=contrib_exclude, instrument=a.instrument)
```
`_export_champion(...)` call (line 193-194) — add instrument:
```python
        p = _export_champion(res["champion"], a.tf, a.out, a.prefix,
                             contrib_smc_excluded=res.get("contrib_smc_excluded", ()), instrument=a.instrument)
```

- [ ] **Step 6: Run tests + the existing L2 optimize suite**

Run: `python3 -m pytest optimize/l2/test_l2_optimize_instrument.py optimize/l2/test_optimize.py -q`
Expected: PASS (NQ L2 path unchanged).

- [ ] **Step 7: Commit**

```bash
git add optimize/l2/optimize.py optimize/l2/test_l2_optimize_instrument.py
git commit -m "feat(optimizer): L2 run/main/_export_champion accept --instrument (suffixed; pv via L1Result)"
```

---

## Phase D — remote runner + launch the short ES run

### Task D1: `remote_wsi.sh` — honor `WSH_INSTRUMENT`

**Files:**
- Modify: `optimize/server/remote_wsi.sh` (pass `--instrument` to optimizer + `WSI_INSTRUMENT` to report)

**Interfaces:**
- Produces: `WSH_INSTRUMENT` (default NQ) → `--instrument` on the optimizer launch + `WSI_INSTRUMENT` exported for `report_wsi.py`. Unset/NQ ⇒ script behaves exactly as today.

- [ ] **Step 1: Inspect the exact launch + report lines**

Run: `grep -n "optimizer.py\|report_wsi.py\|PREFIX=\|WSH_PREFIX\|REMOTE_ENV\|--plan\|--trials" optimize/server/remote_wsi.sh`
Expected: shows the optimizer launch (`python3 -u optimize/optimizer.py "$tf" ...`), the `report_wsi.py` invocation, and the `REMOTE_ENV` export string. Read those exact lines before editing.

- [ ] **Step 2: Add the env var + thread it**

Near the other config vars (e.g. after `PREFIX=...`):
```bash
INSTRUMENT="${WSH_INSTRUMENT:-NQ}"          # NQ (default) or ES; non-NQ → suffixed studies/champions
INST_ARG=""; [ "$INSTRUMENT" != "NQ" ] && INST_ARG="--instrument $INSTRUMENT"
```
Append `$INST_ARG` to BOTH the `--plan` dry-run and the actual optimizer launch commands (the `python3 ... optimize/optimizer.py "$tf" ...` lines).
Export `WSI_INSTRUMENT` for the report step — add `export WSI_INSTRUMENT='$INSTRUMENT'` to the `REMOTE_ENV` string (alongside `WSI_STUDY_PREFIX`).

- [ ] **Step 3: Syntax check**

Run: `bash -n optimize/server/remote_wsi.sh && echo "bash syntax OK"`
Expected: `bash syntax OK`.

- [ ] **Step 4: Commit**

```bash
git add optimize/server/remote_wsi.sh
git commit -m "feat(optimizer): remote_wsi.sh honors WSH_INSTRUMENT (--instrument + WSI_INSTRUMENT)"
```

---

### Task D2: Launch a short ES L1 run → champion → dashboard (execution, not TDD)

**Files:**
- Creates (data, not committed unless desired): `optimize/results/4h_wsi_pareto_ES.csv`, `optimize/results/wsh4_champions_full_ES.json`

- [ ] **Step 1: Run a bounded ES L1 optimization at 4h (slow SMC excluded for speed)**

Run (inline; report wall-clock):
```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
time WSG_DATA_ROOT=/mnt/data/projects/trading/data python3 -u optimize/optimizer.py 4h \
  --instrument ES --trials 200 --folds 5 --min-trades 3 --study-prefix wsh4 --no-warm-start \
  --exclude-indicators ifvg,breaker,cisd,structure_trend,order_block,fvg,stochastic,adx 2>&1 | tail -20
```
Expected: study `wsh4_4h_ES` fills with ~200 trials (some feasible). (If 0 feasible, relax: add `--dd-pnl-cap 0.5` and/or `--min-trades 1`, re-run.)

- [ ] **Step 2: Extract the ES champion**

Run:
```bash
WSI_INSTRUMENT=ES WSI_STUDY_PREFIX=wsh4 python3 optimize/report_wsi.py 4h
WSI_INSTRUMENT=ES python3 optimize/build_champions_from_pareto.py optimize/results/wsh4_champions_full_ES.json 4h
```
Expected: writes `results/4h_wsi_pareto_ES.csv` then `results/wsh4_champions_full_ES.json` (1 timeframe).

- [ ] **Step 3: Verify the dashboard now uses the ES champion**

Run:
```bash
python3 -c "
from optimize.l2 import payload
p = payload.instrument_l1_default('ES','4h')
print('ES 4h default — sl_soft:', p['sl_soft'], 'gate_pct:', p['gate_pct'], 'n_indicators:', len(p['indicators']))
assert p['gate_pct'] != 0 or p['indicators'], 'expected an optimized champion, not bare permissive'
print('OK — dashboard ES default is the optimized champion')
"
```
Expected: prints the champion params + `OK` (gate_pct or indicators non-trivial — i.e. not the bare permissive).

- [ ] **Step 4: Live UI confirmation (optional but recommended)**

Run a fresh server, switch to ES/4h, confirm the L1 form loads the optimized champion (not sl_soft≈40.86 permissive):
```bash
nohup python3 server.py --port 8245 >/tmp/esopt.log 2>&1 & sleep 8
curl -s "http://localhost:8245/api/combined_config?instrument=ES&tf=4h" | python3 -c "import sys,json;d=json.load(sys.stdin);print('ES/4h L1 label:',d['l1_label'],'sl_soft:',d['l1_default']['sl_soft'])"
pkill -f "server.py --port 8245"
```
Expected: the ES default reflects the optimized champion.

- [ ] **Step 5: Commit the ES champion artifact (decide with the user)**

```bash
git add optimize/results/wsh4_champions_full_ES.json optimize/results/4h_wsi_pareto_ES.csv
git commit -m "data(optimizer): first ES 4h champion (short run) — feeds the dashboard ES default"
```

---

## Self-Review

**Spec coverage:** §3 naming → A2 (`_study_suffix`, `_db_for`), B1 (report_wsi `_SUF`), B2 (build_champions `_SUF`), B3 (`_instrument_champions_path`), C1 (L2 study + `_export_champion`). §4.1 L1 wiring → A1 (pv passthrough), A2 (helpers), A3 (run/main + bounds scaling + cold ES + warm-start gate). §4.2 extraction + dashboard → B1/B2/B3. §4.3 L2 → C1. §4.4 remote → D1. §4.5 launch → D2. §6 testing → A1 fold-suite, A2 naming/bounds units, A3 ES smoke + golden, B1/B2 path units, B3 champion-default + fallback, C1 export-name unit, D2 end-to-end. §7 out-of-scope respected (TOKENS NQ/ES; one short run; ES cold; NQ names unchanged).

**Placeholder scan:** none — every code step shows the code; D1-Step1 and A3-Step6 carry a "read/confirm" note (remote_wsi.sh lines + run() return shape) but the edits + commands are explicit.

**Type consistency:** `instrument: str = "NQ"` default is identical across `optimizer.run`, `l2.optimize.run`, `_db_for`, `_export_champion`. `_study_suffix(instrument)->str` defined in A2, reused in A3 + C1. `_SUF` module constant pattern reused in B1/B2 + `_instrument_champions_path` (B3). `score_walkforward(...,pv=None)` (A1) consumed by A3. `point_value`/`is_valid`/`scale_factor` from `optimize.instruments` (engine feature) used in A2/A3. Champion file `wsh4_champions_full_ES.json` written by D2 (build_champions out path) and read by B3 (`_instrument_champions_path`) — names match.
