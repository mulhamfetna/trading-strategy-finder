# Cross-Instrument L2 — Step 1·Part B3: Contributor Search Space

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use `- [ ]`.

**Goal:** Make the cross-instrument contributor config OPTIMIZER-SEARCHABLE — add a namespaced `contributors` block + `contributor_topology` to `suggest_l2_params`, opt-in via `contrib_tokens` so existing L2 runs are byte-identical.

**Architecture:** Add a `prefix=""` arg to `optimizer._suggest_indicators` (default unchanged) so a contributor's committee uses `es_`-namespaced Optuna params. Add `optimize/l2/optimize._suggest_contributor(trial, token)` building the gate cfg (enabled, state_def, signal encoding/mode/table, committee, k_es). `suggest_l2_params(trial, b, cap, contrib_tokens=())` appends `contributor_topology` + `contributors` ONLY when `contrib_tokens` is non-empty. `run`/CLI gain `--contributors ES`.

**Tech Stack:** Python 3, Optuna. Additive; opt-in.

## Global Constraints
- **Opt-in:** `contrib_tokens=()` (default) ⇒ `suggest_l2_params` output has NO `contributors`/`contributor_topology` keys ⇒ existing L2 search byte-identical.
- `_suggest_indicators(..., prefix="")` with `prefix=""` is byte-identical to today (same Optuna param names).
- The produced cfg matches B1's gate schema exactly (so `engine.run_l2` accepts it).

**Files:** Modify `optimize/optimizer.py` (`_suggest_indicators`); `optimize/l2/optimize.py` (`suggest_l2_params`, `run`, CLI); Test `optimize/l2/contributors/test_contrib_search.py`.

---

### Task 1: `prefix` arg on `_suggest_indicators`

**Interfaces:** Produces `optimizer._suggest_indicators(trial, exclude=(), only=(), prefix="") -> [specs]` — Optuna names `f"{prefix}en_{key}"`, `f"{prefix}{key}_{param}"`.

- [ ] **Step 1: failing test** — `optimize/l2/contributors/test_contrib_search.py`:
```python
import sys
from pathlib import Path
_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import optuna
from optimize import optimizer as OPT


def test_suggest_indicators_prefix_namespaces_param_names():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t, prefix="es_")
    names = set(t.params)
    assert "es_en_ema_trend" in names and "es_ema_trend_fast" in names
    assert "en_ema_trend" not in names           # the default namespace is untouched
```
- [ ] **Step 2: run, expect fail** (`prefix` is not a kwarg / TypeError).
- [ ] **Step 3: implement** — in `optimize/optimizer.py` `_suggest_indicators`, add `prefix=""` to the signature and prepend it to BOTH suggest names:
```python
def _suggest_indicators(trial, exclude=(), only=(), prefix=""):
    ...
        enabled = trial.suggest_categorical(f"{prefix}en_{key}", [False, True])
        params = {p["name"]: _suggest_param(trial, f"{prefix}{key}_{p['name']}", p) for p in meta["params"]}
    ...
```
(Only those two f-strings change; the disabled-branch + return are unchanged.)
- [ ] **Step 4: run, expect pass.** Also add + run a guard that `prefix=""` is unchanged:
```python
def test_prefix_default_is_unchanged():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t)
    assert "en_ema_trend" in t.params and "es_en_ema_trend" not in t.params
```
- [ ] **Step 5: commit** — `feat(opt): _suggest_indicators gains prefix= for namespaced committees (default unchanged)`

---

### Task 2: `_suggest_contributor` + opt-in `contrib_tokens` in `suggest_l2_params`

**Interfaces:** Produces `l2opt._suggest_contributor(trial, token) -> cfg dict` (B1 gate schema); `l2opt.suggest_l2_params(trial, b, cap, contrib_tokens=()) -> dict` (adds `contributor_topology` + `contributors` iff `contrib_tokens`).

- [ ] **Step 1: failing test** — append to `test_contrib_search.py`:
```python
def _b_cap():
    b = OPT._load_json(OPT._BOUNDS)["4h"]
    cap = int(OPT._load_json(OPT._CAPS)["4h"]["cooldown_cap"])
    return b, cap


def test_suggest_l2_params_contributor_block_optin():
    from optimize.l2 import optimize as l2opt
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap, contrib_tokens=["ES"])
    assert p["contributor_topology"] in ("separate_and", "merged", "or_boost")
    assert len(p["contributors"]) == 1
    c = p["contributors"][0]
    assert c["token"] == "ES" and c["state_def"] in ("touch", "traversal")
    assert c["signal"]["encoding"] in ("none", "stance", "truthtable")
    assert len(c["committee"]) == len(list(__import__("indicators.library", fromlist=["REGISTRY"]).REGISTRY))
    assert isinstance(c["k_es"], int) and 1 <= c["k_es"] <= 5
    assert len(c["signal"]["table"]) == 6


def test_suggest_l2_params_no_tokens_is_backward_compatible():
    from optimize.l2 import optimize as l2opt
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap)
    assert "contributors" not in p and "contributor_topology" not in p
```
- [ ] **Step 2: run, expect fail** (`contrib_tokens` not a kwarg).
- [ ] **Step 3: implement** — in `optimize/l2/optimize.py`, add `_suggest_contributor` and extend `suggest_l2_params`:
```python
def _suggest_contributor(trial, token: str) -> dict:
    """Searchable cross-instrument contributor cfg (B1 gate schema): master enable, state definition,
    composite signal voter (both encodings searched), the full namespaced indicator committee, and k_es."""
    pre = f"{token.lower()}_"
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial, prefix=pre)]
    enc = trial.suggest_categorical(f"{pre}sig_enc", ["none", "stance", "truthtable"])
    mode = trial.suggest_categorical(f"{pre}sig_mode", ["confirm", "veto", "both"])
    table = {(d, s): trial.suggest_categorical(f"{pre}tt_{d}_{s}", ["confirm", "veto", "ignore"])
             for d in ("long", "short") for s in ("long", "short", "hold")}
    return {"token": token, "enabled": bool(trial.suggest_categorical(f"{pre}enabled", [False, True])),
            "tf": "4h", "state_def": trial.suggest_categorical(f"{pre}state", ["touch", "traversal"]),
            "k_es": int(trial.suggest_int(f"{pre}k_es", 1, 5)),
            "signal": {"encoding": enc, "mode": mode, "table": table},
            "committee": specs}
```
and at the END of `suggest_l2_params` (before `return`), thread `contrib_tokens` through the signature and append:
```python
def suggest_l2_params(trial, b: dict, cap: int, contrib_tokens=()) -> dict:
    ...
    params = dict(...)              # existing
    if contrib_tokens:
        params["contributor_topology"] = trial.suggest_categorical(
            "contributor_topology", ["separate_and", "merged", "or_boost"])
        params["contributors"] = [_suggest_contributor(trial, tok) for tok in contrib_tokens]
    return params
```
- [ ] **Step 4: run, expect pass.** Then a run_l2 smoke (the suggested cfg is engine-valid):
```python
def test_suggested_contributor_runs_in_engine():
    from optimize.l2 import optimize as l2opt, payload, engine
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap, contrib_tokens=["ES"])
    l1 = payload.run_l1_cached("4h")
    r = engine.run_l2(l1, p)            # must not raise; produces a valid ledger
    assert isinstance(r.ledger, list)
```
- [ ] **Step 5: thread `contrib_tokens` into `run` + CLI** — `run(..., contrib_tokens=())` passes it to `suggest_l2_params` inside `objective`; add `--contributors` (comma-split) to `main()` → `run(contrib_tokens=...)`. Run the search-test file + `optimize/l2/contributors/` suite.
- [ ] **Step 6: commit** — `feat(l2-opt): searchable contributor block + topology + k_es (opt-in via --contributors)`

---

### Task 3: Regression — contributors + cap suites + golden
- [ ] `python3 -m pytest optimize/l2/contributors/ optimize/test_cap_search.py -q` (green).
- [ ] `python3 perf/check_golden.py` → **6/6 MATCH** (search-space change can't affect the engine path).
- [ ] commit any fixes — `test: B3 regression green`.

## Definition of done for B3
`suggest_l2_params(..., contrib_tokens=["ES"])` emits a searchable, engine-valid contributor block (both signal encodings, full namespaced committee, k_es, topology); `contrib_tokens=()` is byte-identical to today; the L2 optimizer `run`/CLI can launch a cross-instrument search via `--contributors ES`. **Next (Step 1 tail):** dashboard manual test → speed (the candidate-L1/ES per-trial cost) → run the cross-instrument optimizer (does ES help NQ's L2?).
