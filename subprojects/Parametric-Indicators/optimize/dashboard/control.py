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
            "stage_b": ["cmaes", "gp"], "timeframes": TIMEFRAMES, "bounds": bounds,
            "indicators": library.schema().get("indicators", []), "presets": pl,
            "trials_per_dim": OPT.TRIALS_PER_DIM}


def plan(cfg: dict) -> dict:
    """Acceptance preview: search dimensions → recommended (∝-dimension) trial budget."""
    split = bool(cfg.get("split_sltp", False))
    per_dim = int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM))
    dims = OPT.search_dims(split)
    return {"dims": dims["total"], "breakdown": dims, "trials_per_dim": per_dim,
            "recommended_trials": OPT.recommended_trials(split, per_dim)}


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


def start(cfg: dict) -> dict:
    """Launch a run via remote_wsi.sh (single-study path; sampler/prefix/split from cfg). Idempotent
    relaunch is safe — the watchdog continues from target − completed."""
    _apply_env(cfg)
    args = ["run"]
    if cfg.get("trials") and not cfg.get("auto_trials"):
        args.append(str(int(cfg["trials"])))
    r = _run_remote(args)
    return {"ok": r["ok"], "launched": "launcher-started" in r["stdout"], "detail": r["stdout"][-400:]}


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
        return {"ok": False, "studies": [], "raw": r["stdout"][-400:]}
    data["ok"] = r["ok"]
    return data


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
