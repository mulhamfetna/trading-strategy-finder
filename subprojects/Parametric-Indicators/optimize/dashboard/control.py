"""Dashboard control seam — the ONLY module that talks to remote_wsi.sh + the Optuna store.

Pure functions returning JSON-serializable dicts; NEVER imports the scoring engine (no golden impact).
All shell calls go through `_run_remote` so they are mockable in tests. The FastAPI app and the Telegram
bot are thin presenters over this module.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent.parent                          # Parametric-Indicators root
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import optimizer as OPT               # SAMPLER_CHOICES, search_dims, recommended_trials, print_plan
from optimize import instruments as INST            # TOKENS (tradeable instrument list)
from optimize import run_spec as RS                 # the ONE invocation builder (#91)
from indicators import library                      # schema()

_REMOTE = _PI / "optimize" / "server" / "remote_wsi.sh"
_BOUNDS = _PI / "optimize" / "sl_tp_bounds.json"
_RESULTS_DIR = _PI / "optimize" / "results"
_BUNDLES_DIR = _HERE / "bundles"
_LOGS_DIR = Path(os.environ.get("WSH_LOGS_DIR", str(_PI / "optimize" / "server" / "server_logs")))
TIMEFRAMES = ["4h", "2h", "1h", "15m", "5m", "2m"]


# ── shell seam ──────────────────────────────────────────────────────────────────────────────────
def _run_remote(args: list[str], timeout: int = 120) -> dict:
    """Invoke `bash remote_wsi.sh <args>`. Returns {ok, code, stdout, stderr}. Mocked in tests."""
    proc = subprocess.run(["bash", str(_REMOTE), *args], capture_output=True, text=True, timeout=timeout)
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


# ── config / plan ───────────────────────────────────────────────────────────────────────────────
def config() -> dict:
    """Everything the UI needs to render the control panel: samplers, engines, per-TF bounds, indicator
    schema, presets. No side effects."""
    bounds = json.loads(_BOUNDS.read_text()) if _BOUNDS.exists() else {}
    try:
        import presets
        pl = [{"id": s["id"], "label": s["label"]} for s in presets.strategies()]
    except Exception:
        pl = []
    return {"samplers": list(OPT.SAMPLER_CHOICES), "engines": ["single", "two_stage"],
            "stage_b": ["cmaes", "gp"], "timeframes": TIMEFRAMES, "instruments": list(INST.TOKENS),
            "bounds": bounds, "indicators": library.schema().get("indicators", []), "presets": pl,
            "trials_per_dim": OPT.TRIALS_PER_DIM,
            "optuna_port": int(os.environ.get("DASH_OPTUNA_PORT", 8082))}   # live Pareto/graphs (separate tunnel)


def _scope(cfg: dict) -> tuple[tuple, tuple]:
    """(only_inds, exclude_inds) as the UI selected them.

    THE BUG THIS FIXES. `plan()` and `preview_command()` computed the search size from the WHOLE
    registry while the very same cfg passed `--only-indicators` to the launched command. Selecting the
    original 18 indicators showed "471 dims / 47,100 trials" and launched `--trials 47100` for a search
    that could only ever touch **59 dimensions / 5,900 trials** — an 8x over-budget, i.e. ~20 hours per
    study instead of ~45 minutes.

    This is the same defect fixed in the CLI's --auto-trials path (#2), which I missed here: the fix went
    in at `main()` and the control plane builds its own budget. The control plane is the path a HUMAN
    actually uses, so this was the copy that mattered.
    """
    return (tuple(cfg.get("only_indicators") or ()), tuple(cfg.get("exclude_indicators") or ()))


def plan(cfg: dict) -> dict:
    """Acceptance preview: search dimensions → recommended (∝-dimension) trial budget + the exact
    optimizer command the run will execute (so the UI shows what the launch actually does)."""
    split = bool(cfg.get("split_sltp", False))
    per_dim = int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM))
    only, excl = _scope(cfg)
    # #95: the cross-instrument contributor block was invisible to this plan. It is a SECOND
    # full-registry search that roughly DOUBLES the space, so a contributor run was previewed — and
    # launched — at about half the budget its own search space needs.
    ctoks = tuple(cfg.get("contributors") or ())
    cexcl = tuple(cfg.get("contrib_exclude") or ())
    dims = OPT.search_dims(split, only_inds=only, exclude_inds=excl,
                           contrib_tokens=ctoks, contrib_exclude=cexcl)
    n_scoped = len(OPT.searchable_indicators(only, excl))
    return {"dims": dims["total"], "breakdown": dims, "trials_per_dim": per_dim,
            "recommended_trials": OPT.recommended_trials(split, per_dim, only_inds=only, exclude_inds=excl,
                                                         contrib_tokens=ctoks, contrib_exclude=cexcl),
            # so the UI can SHOW the scope it is charging for, rather than the user inferring it
            "indicators_searched": n_scoped, "indicators_total": len(library.REGISTRY),
            "command": preview_command(cfg)}


def preview_command(cfg: dict) -> str:
    """Render the EXACT optimizer.py invocation this cfg will execute.

    Delegates to `run_spec.build_argv` — the same function `runner.build_command` uses (#91), so the
    displayed command and the executed one are the same call and cannot disagree. This previously
    hand-built its own string ("mirrors remote_wsi.sh's IND_ARGS construction exactly"), and measured
    across four configurations it diverged from the runner on all four: it showed `--trials N` while the
    run used `--auto-trials`, and omitted the `--study-prefix` entirely, so an operator could not tell
    which study their run would write to.

    Representative of the FIRST selected timeframe; a matrix launches one such command per
    (instrument, tf).
    """
    from optimize.dashboard import runner as _runner          # local: avoids an import cycle
    tfs = cfg.get("timeframes") or ([cfg["timeframe"]] if cfg.get("timeframe") else ["4h"])
    spec = RS.from_cfg(cfg, str(tfs[0]), study_prefix=_runner.study_prefix(cfg))
    return " ".join(RS.build_argv(spec))


# ── lifecycle: start / stop(pause) / resume ──────────────────────────────────────────────────────
def _apply_env(cfg: dict) -> None:
    """Translate a UI config into the env remote_wsi.sh reads. Only sets keys present in cfg.
    NOTE: remote_wsi.sh consumes WSH_SAMPLER / WSH_PREFIX / WSH_SPLIT / WSH_CONFIRM. WSH_ENGINE / WSH_STAGE_B
    are recorded for the (follow-up) two-stage launch path; v1 runs the single-study path end-to-end."""
    for key, env in {"sampler": "WSH_SAMPLER", "engine": "WSH_ENGINE",
                     "stage_b": "WSH_STAGE_B", "prefix": "WSH_PREFIX"}.items():
        if cfg.get(key) not in (None, ""):
            os.environ[env] = str(cfg[key])
    os.environ["WSH_SPLIT"] = "1" if cfg.get("split_sltp") else ""
    os.environ["WSH_CONFIRM"] = "1"                # UI already showed the plan + user accepted → skip prompt
    # Control-center run parameters (#23). Absent keys are left unset ⇒ remote_wsi.sh omits the flag
    # ⇒ byte-identical to a bare launch. List-valued selections are comma-joined for --only/--exclude.
    for key, env in {"only_indicators": "WSH_ONLY", "exclude_indicators": "WSH_EXCLUDE"}.items():
        if cfg.get(key):
            os.environ[env] = ",".join(str(x) for x in cfg[key])
    for key, env in {"reference": "WSH_REFERENCE", "max_enabled": "WSH_MAXENABLED",
                     "instrument": "WSH_INSTRUMENT", "dd_cap": "WSH_DD_CAP"}.items():
        if cfg.get(key) not in (None, ""):
            os.environ[env] = str(cfg[key])
    if cfg.get("timeframes"):
        os.environ["WSH_TFS"] = " ".join(str(t) for t in cfg["timeframes"])
    os.environ["WSH_IND1MIN"] = "1" if cfg.get("ind_1min", True) else "0"   # default ON (backward-compat)
    os.environ["WSH_NOWARM"] = "1" if cfg.get("cold_start") else ""         # cold ⇒ --no-warm-start


def start(cfg: dict) -> dict:
    """Launch a run via remote_wsi.sh. Two paths:
      • engine=two_stage → `two-stage <tfs>` (P3 decomposition: finite in-memory studies, run directly,
        NOT through the watchdog — it has no trial-count target so the respawn loop would never stop).
      • engine=single (default) → `run [trials]` (NSGA-III watchdog path; idempotent relaunch continues
        from target − completed)."""
    _apply_env(cfg)
    if str(cfg.get("engine", "single")) == "two_stage":
        args = ["two-stage"]
        tfs = cfg.get("timeframes") or ([cfg["timeframe"]] if cfg.get("timeframe") else [])
        if tfs:
            args.append(" ".join(str(t) for t in tfs))   # remote_wsi.sh `two-stage` reads a space-list TF arg
        r = _run_remote(args)
        return {"ok": r["ok"], "launched": "launcher-started" in r["stdout"],
                "engine": "two_stage", "detail": r["stdout"][-400:]}
    args = ["run"]
    if cfg.get("trials") and not cfg.get("auto_trials"):
        args.append(str(int(cfg["trials"])))
    r = _run_remote(args)
    return {"ok": r["ok"], "launched": "launcher-started" in r["stdout"],
            "engine": "single", "detail": r["stdout"][-400:]}


def stop() -> dict:
    """Pause = stop the workers; completed trials persist in the store (resume continues from there)."""
    r = _run_remote(["stop"])
    return {"ok": r["ok"], "detail": (r["stdout"] + r["stderr"])[-400:]}


def resume(cfg: dict) -> dict:
    """Resume = relaunch with the same target/prefix; the watchdog runs the remaining trials."""
    return start(cfg)


# ── status ──────────────────────────────────────────────────────────────────────────────────────
def status() -> dict:
    """Per-TF study state from `remote_wsi.sh stats --json` (complete/running/fail/pruned)."""
    r = _run_remote(["stats", "--json"])
    try:
        data = json.loads(r["stdout"])
    except Exception:
        return {"ok": False, "studies": [], "running": False, "n_studies": 0, "raw": r["stdout"][-400:]}
    data["ok"] = r["ok"]
    studies = data.get("studies", [])
    # Normalized top-level flags the UI drives buttons + health off of. A run is "running" if ANY
    # study still has worker processes (`running` = live worker count from `stats --json`).
    data["running"] = any(int(s.get("running", s.get("workers", 0)) or 0) > 0 for s in studies)
    data["n_studies"] = len(studies)
    return data


# ── health ────────────────────────────────────────────────────────────────────────────────────────
def health() -> dict:
    """Host + run health for the control panel's health strip. Runs on the same box as the optimizer,
    so psutil reflects the server. Every field degrades to None if unavailable (psutil missing, no server)."""
    h = {"cpu_pct": None, "mem_pct": None, "workers": None, "n_studies": 0, "running": False}
    try:
        import psutil
        h["cpu_pct"] = round(psutil.cpu_percent(interval=0.0), 1)
        h["mem_pct"] = round(psutil.virtual_memory().percent, 1)
    except Exception:
        pass
    st = status()
    studies = st.get("studies", [])
    h["n_studies"] = len(studies)
    h["running"] = bool(st.get("running"))
    w = sum(int(s.get("running", s.get("workers", 0)) or 0) for s in studies)
    h["workers"] = w or None
    return h


def study_progress(tf: str, target: int | None = None) -> dict:
    """Completed-trial count + target for one timeframe's study, read defensively from `status()`
    (the live `stats --json` shape varies). Returns {done, target}."""
    done, tgt = 0, int(target or 0)
    for st in status().get("studies", []):
        name = str(st.get("tf") or st.get("name") or "")
        if name == str(tf) or name.endswith(str(tf)):
            done = int(st.get("complete", st.get("done", st.get("n_complete", 0))) or 0)
            if not target:
                tgt = int(st.get("target", st.get("recommended", st.get("n_trials", 0))) or 0)
            break
    return {"done": done, "target": tgt}


# ── logs (SSE source) ─────────────────────────────────────────────────────────────────────────────
def _log_path(tf: str) -> Path:
    return _LOGS_DIR / f"{tf}.log"


def tail_logs(tf: str, n: int = 200) -> str:
    p = _log_path(tf)
    if not p.exists():
        return ""
    return "\n".join(p.read_text(errors="replace").splitlines()[-n:])


def follow_logs(tf: str):
    """Generator yielding new log lines (for SSE). Polls the file from the current end."""
    p = _log_path(tf)
    pos = p.stat().st_size if p.exists() else 0
    while True:
        if p.exists():
            with p.open(errors="replace") as f:
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
            if chunk:
                for line in chunk.splitlines():
                    yield line
        time.sleep(1.0)


# ── data bundle (full | lite) ─────────────────────────────────────────────────────────────────────
def build_bundle(mode: str = "full", stamp: str | None = None) -> str:
    """Build a .tar.gz of optimizer artifacts. 'full' adds a pg_dump of the studies; 'lite' omits it.
    `stamp` is passed by the caller (no time.* in the pure path needed, but tolerated). Returns tar path."""
    if mode not in ("full", "lite"):
        raise ValueError(f"mode must be full|lite, got {mode!r}")
    _BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = stamp or "bundle"
    out = _BUNDLES_DIR / f"optimizer_{mode}_{stamp}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        if _RESULTS_DIR.exists():
            tar.add(_RESULTS_DIR, arcname="results")
        if _LOGS_DIR.exists():
            tar.add(_LOGS_DIR, arcname="logs")
        if mode == "full":
            dump = _BUNDLES_DIR / f"studies_{stamp}.sql"
            url = os.environ.get("WSH_STORAGE_URL", "")
            if url.startswith("postgres"):
                subprocess.run(["pg_dump", "--dbname", url.replace("+psycopg2", ""), "-f", str(dump)],
                               check=False, timeout=600)
                if dump.exists():
                    tar.add(dump, arcname="studies.sql")
                    dump.unlink()
    return str(out)
