# Optimizer Control Center — P1 (control + settings + progress/ETA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.
> **Worktree:** create an isolated worktree off `dev` first (superpowers:using-git-worktrees) — e.g. `.worktrees/optimizer-control-center`. All paths below are under `subprojects/Parametric-Indicators/`.

**Goal:** Configure, launch, watch (progress + ETA), and stop a full optimization run entirely from a Vue GUI — no terminal.

**Architecture:** Extend the existing FastAPI control plane (`optimize/dashboard/app.py` + `control.py`, :8350) with a few endpoints, and add a Vue+Vite SPA (`optimize/dashboard/web/`) it serves. Reuse `remote_wsi.sh`, `wsh-pg`, the VPN-only bind. Issue #23, part of #22.

**Tech Stack:** Python 3 / FastAPI / uvicorn (existing); Vue 3 + Vite (new SPA); pytest (backend); the optimizer CLI (`optimize/optimizer.py`) flags `--only-indicators --exclude-indicators --reference --max-enabled --instrument --auto-trials --trials --split-sltp --sampler --ind-1min`.

## Global Constraints
- **VPN-only:** every service binds the private/VPN IP, never `0.0.0.0`/public (inherit v1 spec §3.0). Do not change the bind model.
- **No optimizer-engine change:** golden `perf/check_golden.py` 6/6 + full indicator parity stay byte-identical. P1 only adds control-plane endpoints + a frontend + a cfg→CLI mapping.
- **Follow the existing cfg pattern:** new run parameters flow through `control.py` (`_apply_env`/`start`) the same way `instrument`/`trials`/`timeframes` already do.
- **Every backend change is TDD** (pytest under `optimize/dashboard/`). Frontend tasks end in a `vite build` + a served-page smoke check.
- **Commit after each task.** Branch `feat/occ-p1-<area>` per task-group; merge to `dev` per phase (auto-merge when green, per the repo's standing rule); PRs reference #23.

---

## PHASE A — Backend prerequisites (TDD)

### Task A1: `schema()` emits a `family` per indicator
**Files:** Modify `indicators/library.py` (`schema()` ~383) · Test `indicators/test_schema_family.py`

**Interfaces:** Produces: `library.schema()["indicators"][i]["family"]` ∈ the school name (`ma|oscillator|trend|volatility|volume|levels|bill_williams|quant|dsp|cross_series`) or `builtin` for the 18 originals.

- [ ] **Step 1 — failing test**
```python
# indicators/test_schema_family.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators import library
def test_every_indicator_has_a_family():
    inds = library.schema()["indicators"]
    assert all("family" in i for i in inds)
    fams = {i["family"] for i in inds}
    assert {"ma", "oscillator", "trend", "cross_series"} <= fams
    # families partition the registry
    assert len(inds) == len(library.REGISTRY)
```
- [ ] **Step 2** Run → FAIL (`KeyError family`).
- [ ] **Step 3 — implement:** build a key→family map from the `lib_<school>` modules and the builtin set, and add `"family"` to each schema row.
```python
# library.py — after SCHEMA is assembled
_FAMILY = {"lib_ma": "ma", "lib_osc": "oscillator", "lib_trend": "trend", "lib_vol": "volatility",
           "lib_volume": "volume", "lib_levels": "levels", "lib_bw": "bill_williams",
           "lib_quant": "quant", "lib_dsp": "dsp", "lib_tier2": "dsp", "lib_xseries": "cross_series"}
_KEY_FAMILY = {}
for _m in _SCHOOLS:
    _fam = _FAMILY.get(_m.__name__.rsplit(".", 1)[-1], "other")
    for _k in _m.SCHEMA:
        _KEY_FAMILY[_k] = _fam
def schema():
    inds = [dict(key=k, family=_KEY_FAMILY.get(k, "builtin"), **SCHEMA[k]) for k in REGISTRY]
    return {"indicators": inds, "modes": list(MODES), "retrace_units": list(RETRACE_UNITS),
            "retrace_default": {"amount": 0.0, "unit": "atr_mult"}, "wait_default": 0, "k_default": 1,
            "gen_params": [{"name": "swing_l", "default": 2, "min": 1, "max": 20, "step": 1},
                           {"name": "golf_n", "default": 3, "min": 1, "max": 50, "step": 1}]}
```
- [ ] **Step 4** Run → PASS. Also run `indicators/test_registry_merge.py` (schema shape unchanged otherwise).
- [ ] **Step 5** Commit `feat(indicators): schema() tags each indicator with its family (#23)`.

### Task A2: cfg → optimizer mapping for indicator/reference/K-cap selection
**Files:** Modify `optimize/dashboard/control.py` (`start`/`_apply_env`) · `remote_wsi.sh` (pass-through) · Test `optimize/dashboard/test_control_cfg.py`

**Interfaces:** Consumes `cfg` keys `only_indicators: list[str]`, `exclude_indicators: list[str]`, `reference: str|None`, `max_enabled: int|None`. Produces: the launched command/env includes `--only-indicators a,b` / `--exclude-indicators` / `--reference ES` / `--max-enabled K` (following the existing instrument/trials pattern).

- [ ] **Step 1 — failing test** (assert the arg/env builder includes the new flags):
```python
# optimize/dashboard/test_control_cfg.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import control
def test_cfg_maps_indicator_selection_to_flags(monkeypatch):
    seen = {}
    monkeypatch.setattr(control, "_run_remote", lambda args, timeout=120: seen.setdefault("args", args) or {"ok": True})
    control.start({"timeframe": "4h", "instrument": "NQ",
                   "only_indicators": ["rsi", "macd"], "reference": "ES", "max_enabled": 3})
    flat = " ".join(seen["args"])
    assert "--only-indicators" in flat and "rsi,macd" in flat
    assert "--reference" in flat and "ES" in flat
    assert "--max-enabled" in flat and "3" in flat
```
- [ ] **Step 2** Run → FAIL.
- [ ] **Step 3 — implement:** in `control.start`, append the flags when present (mirror the existing `trials`/`engine` handling); if `remote_wsi.sh` is the launcher, pass them via the same env/arg channel it already uses for instrument/trials (add env vars `WSH_ONLY`/`WSH_EXCLUDE`/`WSH_REFERENCE`/`WSH_MAXENABLED` consumed by `remote_wsi.sh` → appended to the `optimizer.py` call). Keep absent-key behavior byte-identical.
- [ ] **Step 4** Run → PASS.
- [ ] **Step 5** Commit `feat(dashboard): wire indicator/reference/K-cap selection into the launch cfg (#23)`.

### Task A3: `/api/live/progress` — trials done/target + rate + ETA
**Files:** Modify `optimize/dashboard/app.py` · New `optimize/dashboard/progress.py` · Test `optimize/dashboard/test_progress.py`

**Interfaces:** Produces `GET /api/live/progress?study=<name>` → `{done, target, rate_per_min, eta_seconds, feasible, elapsed_seconds}`. `progress.compute_eta(samples, target)` is the pure, testable core (`samples` = list of `(t_epoch, done)`).

- [ ] **Step 1 — failing test** (pure ETA math, no optuna needed):
```python
# optimize/dashboard/test_progress.py
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import progress
def test_eta_from_trailing_rate():
    # 100 trials in 100s ⇒ 1/s ⇒ 60/min; target 400 ⇒ 300 remaining ⇒ 300s
    r = progress.compute_eta([(1000.0, 100), (1100.0, 200)], target=400)
    assert abs(r["rate_per_min"] - 60.0) < 1e-6
    assert abs(r["eta_seconds"] - 300.0) < 1e-6
def test_eta_none_when_no_progress():
    r = progress.compute_eta([(1000.0, 50), (1100.0, 50)], target=400)
    assert r["eta_seconds"] is None      # rate 0 ⇒ unknown ETA
```
- [ ] **Step 2** Run → FAIL.
- [ ] **Step 3 — implement** `progress.compute_eta` (rate from last-vs-first sample; eta=remaining/rate, None if rate≤0), and the endpoint that reads the optuna study trial count (from `wsh-pg`, reuse the study-open helper the optimizer uses) + the run target (from `stats --json`), keeps a small rolling sample buffer, and returns the dict.
- [ ] **Step 4** Run → PASS.
- [ ] **Step 5** Commit `feat(dashboard): /api/live/progress with trailing-rate ETA (#23)`.

### Task A4: `/api/presets` CRUD (saved configs)
**Files:** Modify `app.py` · New `optimize/dashboard/presets.py` (JSON-file store) · Test `test_presets.py`

**Interfaces:** `presets.save(name, cfg)`, `list()`, `get(name)`, `delete(name)` over a JSON file (`~/.wsh/presets.json` or a configured path). Endpoints `GET/POST/DELETE /api/presets[/{name}]`.

- [ ] **Step 1 — failing test** (CRUD roundtrip against a tmp path):
```python
def test_preset_roundtrip(tmp_path, monkeypatch):
    from optimize.dashboard import presets
    monkeypatch.setattr(presets, "_STORE", tmp_path / "p.json")
    presets.save("nq-warm", {"instrument": "NQ", "reference": "ES"})
    assert "nq-warm" in presets.list_names()
    assert presets.get("nq-warm")["reference"] == "ES"
    presets.delete("nq-warm")
    assert "nq-warm" not in presets.list_names()
```
- [ ] **Step 2-4** FAIL → implement the JSON store + endpoints → PASS.
- [ ] **Step 5** Commit `feat(dashboard): saved-preset CRUD (#23)`.

### Task A5: `/api/queue` — instruments×timeframes matrix expansion
**Files:** Modify `app.py` · New `optimize/dashboard/queue.py` · Test `test_queue.py`

**Interfaces:** `queue.expand(cfg)` → ordered list of per-study configs from `{instruments:[...], timeframes:[...], trials_mode, trials, per_trials}`. Endpoint `POST /api/queue` enqueues + launches them sequentially (each via `control.start`), `GET /api/queue` returns per-item status.

- [ ] **Step 1 — failing test** (pure expansion):
```python
def test_matrix_expands_to_per_study_configs():
    from optimize.dashboard import queue
    got = queue.expand({"instruments": ["NQ", "ES"], "timeframes": ["4h", "1h"],
                        "trials_mode": "one", "trials": 5000})
    keys = {(c["instrument"], c["timeframe"], c["trials"]) for c in got}
    assert keys == {("NQ","4h",5000),("NQ","1h",5000),("ES","4h",5000),("ES","1h",5000)}
```
- [ ] **Step 2-4** FAIL → implement `expand` (also handles `trials_mode ∈ {auto, one, per}`; `auto` sets `auto_trials=True`) + the queue runner + status → PASS.
- [ ] **Step 5** Commit `feat(dashboard): run-queue matrix expansion + sequential launch (#23)`.

---

## PHASE B — Vue SPA scaffold

### Task B1: Vite+Vue app served by the control plane
**Files:** Create `optimize/dashboard/web/` (Vite scaffold: `package.json`, `vite.config.js`, `index.html`, `src/main.js`, `src/App.vue`) · Modify `app.py` (serve `web/dist` as static) · `run_dashboard.sh` (build step)

- [ ] **Step 1** Scaffold: `npm create vite@latest web -- --template vue` (in `optimize/dashboard/`), set `vite.config.js` `base: './'` and `build.outDir: 'dist'`.
- [ ] **Step 2** `App.vue`: a 3-column shell — `<ControlPanel/> <SettingsPanel/> <ReportingPanel/>` (stubs for now), a top bar with connection status.
- [ ] **Step 3** `app.py`: mount `web/dist` at `/` (FastAPI `StaticFiles`), keep `/api/*` above it.
- [ ] **Step 4 — verify:** `npm --prefix web run build` succeeds; start the control plane; `curl -s localhost:8350/ | grep -q '<div id="app"'` (served). Record the command in `run_dashboard.sh`.
- [ ] **Step 5** Commit `feat(dashboard): Vue SPA scaffold served by the control plane (#23)`.

### Task B2: API client + config load
**Files:** Create `web/src/api.js` · `web/src/store.js` (reactive run-config)

- [ ] **Step 1** `api.js`: thin `fetch` wrappers for every endpoint (`config, plan, run, resume, stop, liveProgress, presets, queue`); SSE helper for logs/progress.
- [ ] **Step 2** On mount, `GET /api/config` (bounds, samplers, engines, **indicator schema with families**, instruments, tfs) into the store; render nothing hard-coded.
- [ ] **Step 3 — verify:** load the page against a running control plane → the store is populated (a temporary `<pre>{{config}}</pre>` shows 165 indicators + families). Remove the debug block.
- [ ] **Step 4** Commit `feat(dashboard): api client + config bootstrap (#23)`.

---

## PHASE C — Control panel

### Task C1: Start / Stop / Resume
**Files:** Create `web/src/components/ControlPanel.vue`
- [ ] Buttons wired to `POST /api/{run,resume,stop}` with the current store cfg; disabled-state reflects `GET /api/status` (idle/running). Verify: click Start against a `--plan`-style dry study → status flips to running; Stop → idle. Commit.

### Task C2: Progress bar + live ETA
**Files:** `ControlPanel.vue` (+ `web/src/components/ProgressBar.vue`)
- [ ] Poll `GET /api/live/progress` every ~3s while running; render a bar (`done/target`), `rate/min`, **ETA** (humanized), feasible count, elapsed. Verify against a live study: the bar advances and ETA decreases. Commit.

### Task C3: Health strip + filtered log tail
**Files:** `web/src/components/HealthStrip.vue`, `LogTail.vue`
- [ ] Health: `GET /api/status` (extend to include cpu/mem/workers/db-size/study-count). Log: subscribe to the existing progress/log SSE; a filter dropdown (all/errors/pruned/feasible) client-side. Verify: logs stream + filter works. Commit.

---

## PHASE D — Settings panel

### Task D1: Indicator + family selector
**Files:** `web/src/components/IndicatorPicker.vue`
- [ ] From the store's schema: a searchable list grouped by **family** with a family-level checkbox (select/deselect the whole school) + per-indicator toggles. Emits `{only_indicators|exclude_indicators}` (mode toggle: "only these" vs "all except"). Verify: selecting the `oscillator` family checks its 23 rows; the emitted list matches. Commit.

### Task D2: Instruments × timeframes matrix
**Files:** `web/src/components/RunMatrix.vue`
- [ ] Multi-select instruments (from config) × multi-select timeframes → a visual grid of the studies that will launch. Emits `{instruments, timeframes}`. Verify: 2×3 selection shows 6 cells. Commit.

### Task D3: Run knobs (trials three-way + the rest)
**Files:** `web/src/components/RunKnobs.vue`
- [ ] Trials: radio **auto / one-count / per-(inst,tf)** (per shows a small grid of counts). Plus: warm/cold (+ champion picker stub → filled in P3), 1-min vs decision-TF, sampler/engine, split-SL/TP, dd-cap, **reference** (instrument dropdown), **K-cap** (number). Each binds to the store cfg. Verify: the store cfg reflects each control. Commit.

### Task D4: Config → command preview
**Files:** `web/src/components/CommandPreview.vue`
- [ ] Debounced `POST /api/plan` with the current cfg → render the dims/trials plan **and** the exact `remote_wsi.sh`/`optimizer.py` command (extend `/api/plan` to also return the command string). Copyable. Verify: changing indicators/instruments updates the preview. Commit.

### Task D5: Saved presets UI
**Files:** `web/src/components/Presets.vue`
- [ ] List/save/apply/delete presets (`/api/presets`); "Save current" captures the store cfg; "Apply" loads it. Verify: save → reload page → apply restores the cfg. Commit.

### Task D6: Run queue + budget guard
**Files:** `web/src/components/QueueControls.vue`
- [ ] "Launch matrix" → `POST /api/queue` (expand + sequential launch); per-item status list. Budget guard inputs (max-trials / max-wallclock) included in cfg and enforced by the queue runner (auto-stop). Verify: a 2-study matrix launches and reports per-item progress. Commit.

---

## PHASE E — Integration + guardrails

### Task E1: End-to-end from the UI
- [ ] Manual acceptance (documented in the PR): open the SPA over VPN → pick indicators (a family + a few individuals) + instruments×tf + trials + warm/cold + reference → **Launch** → watch progress+ETA → **Stop**. Capture a screenshot/gif. No terminal used.

### Task E2: Guardrails green
- [ ] `perf/check_golden.py` → 6/6. `optimize/test_indicator_parity.py 4h` → 0 mismatch (unaffected — no engine change). Confirm every dashboard service still binds the private/VPN IP only (grep the bind; no `0.0.0.0`). Backend unit tests (A1–A5) green.
- [ ] Update the workstream tracker + close #23 via the phase PR (merge to `dev`).

---

## Self-review notes (author)
- **Spec coverage (P1 slice):** control panel → C1–C3; settings (indicators+families, matrix, trials three-way, warm/cold, 1min, sampler, split, dd-cap, reference, K-cap, command preview, presets, queue, budget guard) → A1–A2, D1–D6; progress/ETA → A3,C2; VPN bind → E2. P2 (live figures) + P3 (leaderboard/reports/compare/adopt-gate) are explicitly separate plans.
- **Placeholders:** backend tasks carry runnable tests; frontend tasks specify file, component responsibility, bound endpoint, and a concrete verify step (frontend is component-spec + smoke, not unit-TDD).
- **Types:** cfg keys (`only_indicators/exclude_indicators/reference/max_enabled/instruments/timeframes/trials_mode/trials/per_trials/engine/sampler/split_sltp/ind_1min/warm_start`) are consistent across A2/A5/D3/D4; `compute_eta` returns `{done,target,rate_per_min,eta_seconds,feasible,elapsed_seconds}` used by C2.
- **Execution note:** confirm the exact channel `remote_wsi.sh` uses to pass flags to `optimizer.py` (env vs args) in A2 and follow it; do the VPN bind-IP check (E2) before any public exposure.
