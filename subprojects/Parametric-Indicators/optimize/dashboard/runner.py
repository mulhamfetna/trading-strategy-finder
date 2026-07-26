"""Control-plane-OWNED optimizer runner (#28).

Drives `optimize/optimizer.py` as a subprocess the control plane owns (`Popen`, its own process
group) — the opposite of the fire-and-forget `remote_wsi.sh` launch (detached `setsid` workers). Because
the plane holds the handle it can: stream live stdout, STOP for real (kill the group), and give each
distinct selection its OWN study (so runs actually execute instead of reusing a target-met study).

Pure helpers (`validate`, `study_prefix`, `build_command`) are unit-tested; the process lifecycle is
tested with a fake command so no real optimizer runs.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent.parent                        # Parametric-Indicators root (cwd for the child)


def _python() -> str:
    """The interpreter to run the optimizer with. On the server, the venv from REMOTE_VENV; tests may
    pin WSH_RUNNER_PYTHON; otherwise the current interpreter."""
    p = os.environ.get("WSH_RUNNER_PYTHON")
    if p:
        return p
    venv = os.environ.get("REMOTE_VENV")
    if venv and (Path(venv) / "bin" / "python3").exists():
        return str(Path(venv) / "bin" / "python3")
    return sys.executable


# ── pure helpers ────────────────────────────────────────────────────────────────────────────────
def validate(cfg: dict) -> list[str]:
    """Return the list of missing/invalid mandatory fields. Empty ⇒ OK to run."""
    missing = []
    if not cfg.get("instrument"):
        missing.append("instrument")
    tfs = cfg.get("timeframes") or ([cfg["timeframe"]] if cfg.get("timeframe") else [])
    if not tfs:
        missing.append("timeframe")
    if cfg.get("trials_mode", "auto") == "one" and not int(cfg.get("trials") or 0):
        missing.append("trials")
    im = cfg.get("indicator_mode", "all")
    if im == "only" and not cfg.get("only_indicators"):
        missing.append("only_indicators")
    if im == "exclude" and not cfg.get("exclude_indicators"):
        missing.append("exclude_indicators")
    return missing


def study_prefix(cfg: dict) -> str:
    """A stable prefix unique to this SELECTION (instrument + indicators + knobs). Two different configs
    ⇒ two different studies ⇒ a fresh run each time (never silently reuses a target-met study)."""
    canon = {
        "inst": cfg.get("instrument", "NQ"),
        "only": sorted(cfg.get("only_indicators") or []),
        "excl": sorted(cfg.get("exclude_indicators") or []),
        "mode": cfg.get("indicator_mode", "all"),
        "split": bool(cfg.get("split_sltp")),
        "ref": cfg.get("reference") or "",
        "maxen": int(cfg.get("max_enabled") or 0),
        "ind1min": bool(cfg.get("ind_1min", True)),
        "sampler": cfg.get("sampler") or "nsga3",
        "cold": bool(cfg.get("cold_start")),
        "dd": str(cfg.get("dd_cap") or ""),
    }
    h = hashlib.sha1(json.dumps(canon, sort_keys=True).encode()).hexdigest()[:8]
    return f"cc{h}"


def study_name(cfg: dict, tf: str) -> str:
    """Mirror optimizer.py: f'{prefix}_{tf}{_study_suffix(instrument)}' (suffix empty for NQ)."""
    inst = str(cfg.get("instrument", "NQ"))
    return f"{study_prefix(cfg)}_{tf}" + ("" if inst == "NQ" else f"_{inst}")


def target_trials(cfg: dict) -> int:
    from optimize import optimizer as OPT
    if cfg.get("trials_mode") == "one" and cfg.get("trials"):
        return int(cfg["trials"])
    return OPT.recommended_trials(bool(cfg.get("split_sltp")),
                                  int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM)))


def build_command(cfg: dict, tf: str) -> list[str]:
    """The optimizer.py argv equivalent to this cfg (mirrors remote_wsi.sh IND_ARGS)."""
    cmd = [_python(), "-u", "optimize/optimizer.py", str(tf), "--folds", "5", "--min-trades", "5",
           "--study-prefix", study_prefix(cfg)]
    mode = cfg.get("trials_mode", "auto")
    if mode == "one" and int(cfg.get("trials") or 0):
        cmd += ["--trials", str(int(cfg["trials"]))]
    elif mode == "per":
        n = int((cfg.get("per_trials") or {}).get(f"{cfg.get('instrument')}:{tf}", 0))
        cmd += (["--trials", str(n)] if n else ["--auto-trials"])
    else:
        cmd += ["--auto-trials"]
    if cfg.get("ind_1min", True):
        cmd.append("--ind-1min")
    if cfg.get("split_sltp"):
        cmd.append("--split-sltp")
    if cfg.get("sampler"):
        cmd += ["--sampler", str(cfg["sampler"])]
    if cfg.get("exclude_indicators"):
        cmd += ["--exclude-indicators", ",".join(map(str, cfg["exclude_indicators"]))]
    if cfg.get("only_indicators"):
        cmd += ["--only-indicators", ",".join(map(str, cfg["only_indicators"]))]
    if cfg.get("reference"):
        cmd += ["--reference", str(cfg["reference"])]
    if cfg.get("max_enabled"):
        cmd += ["--max-enabled", str(int(cfg["max_enabled"]))]
    if cfg.get("cold_start"):
        cmd.append("--no-warm-start")
    if cfg.get("dd_cap") not in (None, ""):
        cmd += ["--dd-pnl-cap", str(cfg["dd_cap"])]
    inst = str(cfg.get("instrument", "NQ"))
    if inst != "NQ":
        cmd += ["--instrument", inst]
    return cmd


def _child_env(cfg: dict) -> dict:
    env = dict(os.environ)                       # inherits WSH_DATA_BASE/WSG_DATA_ROOT/WSH_STORAGE_URL from dashboard.env
    env["WSI_INSTRUMENT"] = str(cfg.get("instrument", "NQ"))
    return env


# ── owned run manager (single active run) ─────────────────────────────────────────────────────────
class RunManager:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.study = self.tf = self.prefix = None
        self.cfg: dict | None = None
        self.target = 0
        self.lines: collections.deque = collections.deque(maxlen=2000)
        self._total = 0                              # monotonic count of lines ever produced (for SSE cursor)
        self._reader: threading.Thread | None = None

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, cfg: dict) -> dict:
        missing = validate(cfg)
        if missing:
            return {"ok": False, "errors": missing,
                    "detail": "missing required fields: " + ", ".join(missing)}
        if self.running():
            return {"ok": False, "detail": f"a run is already active (study {self.study}); stop it first"}
        tf = str((cfg.get("timeframes") or [cfg.get("timeframe")])[0])
        cmd = build_command(cfg, tf)
        self.prefix = study_prefix(cfg)
        self.study = study_name(cfg, tf)
        self.tf, self.cfg, self.target = tf, cfg, target_trials(cfg)
        self.lines.clear()
        self._total = 0
        self.proc = subprocess.Popen(cmd, cwd=str(_PI), env=_child_env(cfg),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1, start_new_session=True)
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()
        return {"ok": True, "study": self.study, "tf": tf, "pid": self.proc.pid,
                "target": self.target, "command": " ".join(cmd)}

    def _pump(self):
        try:
            for line in self.proc.stdout:            # blocks until the child writes / closes
                self.lines.append(line.rstrip("\n"))
                self._total += 1
        except Exception:
            pass

    def lines_since(self, cursor: int) -> tuple[int, list[str]]:
        """Return (new_cursor, new_lines) for absolute cursor `cursor` — drives the SSE log stream
        without duplicating or skipping even as the bounded buffer drops old lines."""
        first = self._total - len(self.lines)        # absolute index of lines[0]
        start = max(0, cursor - first)
        return self._total, list(self.lines)[start:]

    def stop(self) -> dict:
        if self.proc is None:
            return {"ok": True, "detail": "nothing running"}
        if self.proc.poll() is not None:
            return {"ok": True, "detail": f"already exited (rc={self.proc.returncode})"}
        try:
            pgid = os.getpgid(self.proc.pid)
            os.killpg(pgid, signal.SIGTERM)          # real stop: signal the whole owned group
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
            return {"ok": True, "detail": "stopped"}
        except ProcessLookupError:
            return {"ok": True, "detail": "already gone"}

    def state(self) -> dict:
        rc = None if self.proc is None else self.proc.poll()
        return {"running": self.running(), "study": self.study, "tf": self.tf,
                "prefix": self.prefix, "pid": (self.proc.pid if self.proc else None),
                "returncode": rc, "target": self.target, "log_lines": len(self.lines)}

    def tail(self, n: int = 300) -> list[str]:
        return list(self.lines)[-n:]

    def done_count(self) -> int:
        """Completed-trial count for the active study, via the existing trial_count.py (store-aware)."""
        if not self.prefix or not self.tf:
            return 0
        try:
            r = subprocess.run([_python(), "optimize/trial_count.py", self.tf, "--prefix", self.prefix],
                               cwd=str(_PI), env=_child_env(self.cfg or {}),
                               capture_output=True, text=True, timeout=20)
            return int("".join(ch for ch in r.stdout if ch.isdigit()) or 0)
        except Exception:
            return 0


_MGR = RunManager()
