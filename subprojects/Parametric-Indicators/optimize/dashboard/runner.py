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
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import run_spec as RS              # noqa: E402 — the ONE invocation builder (#91)


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


def _explicit_trials(cfg: dict, tf: str) -> int | None:
    """The explicit trial count this cfg pins, or None for auto. Handles BOTH the raw Run cfg
    (trials_mode/trials/per_trials) AND a queue.expand()-ed cell (auto_trials + trials)."""
    if "auto_trials" in cfg:                          # already-expanded cell (from the fleet/queue)
        return None if cfg["auto_trials"] else (int(cfg.get("trials") or 0) or None)
    mode = cfg.get("trials_mode", "auto")
    if mode == "one":
        return int(cfg.get("trials") or 0) or None
    if mode == "per":
        return int((cfg.get("per_trials") or {}).get(f"{cfg.get('instrument')}:{tf}", 0)) or None
    return None


def target_trials(cfg: dict, tf: str = "4h") -> int:
    from optimize import optimizer as OPT
    n = _explicit_trials(cfg, tf)
    if n is not None:
        return n
    return OPT.recommended_trials(bool(cfg.get("split_sltp")),
                                  int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM)))


def spec_for(cfg: dict, tf: str) -> "RS.RunSpec":
    """The RunSpec this cfg launches — the single description both the preview and the launch use."""
    return RS.from_cfg(cfg, tf, study_prefix=study_prefix(cfg))


def build_command(cfg: dict, tf: str) -> list[str]:
    """The optimizer.py argv this cfg executes.

    Delegates to run_spec.build_argv — the ONE place an invocation is constructed (#91). This used to
    hand-build the argv while `control.preview_command` hand-built a DIFFERENT one for display; measured
    across four configurations, the two diverged on all four. There is now nothing to keep in sync.
    """
    return RS.build_argv(RS.from_cfg(cfg, tf, study_prefix=study_prefix(cfg)),
                         python=_python(), unbuffered=True)


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
        self.tf, self.cfg, self.target = tf, cfg, target_trials(cfg, tf)
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
            os.killpg(pgid, signal.SIGTERM)          # graceful stop of the whole owned group
            try:
                self.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                pass
            # Sweep the group with SIGKILL so fold/loky worker stragglers don't linger after Stop.
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
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
        """FINISHED-trial count (complete+pruned+fail) for the active study — progress toward the total-trial
        target, so the bar reaches 100% even when trials are pruned. Via trial_count.py --finished."""
        if not self.prefix or not self.tf:
            return 0
        try:
            r = subprocess.run([_python(), "optimize/trial_count.py", self.tf, "--prefix", self.prefix, "--finished"],
                               cwd=str(_PI), env=_child_env(self.cfg or {}),
                               capture_output=True, text=True, timeout=20)
            return int("".join(ch for ch in r.stdout if ch.isdigit()) or 0)
        except Exception:
            return 0


_MGR = RunManager()


# ── fleet: the Launch-matrix queue as OWNED runs (#36) ────────────────────────────────────────────
# One owned optimizer subprocess per (instrument, timeframe) cell — same live/stop guarantees as the
# single Run button, just many at once, capped so the box isn't oversubscribed.
_FLEET: list[dict] = []                          # [{run: RunManager|None, item: {...}}]


def _worker_cap() -> int:
    return max(1, (os.cpu_count() or 4) - 2)      # leave 2 cores for OS/Postgres (mirrors remote_wsi guard)


def fleet_launch(cfg: dict) -> list[dict]:
    """Expand instruments×timeframes and launch ONE owned run per cell, up to the worker cap. Cells beyond
    the cap are 'deferred' (surfaced, never silently dropped — relaunch after the running ones finish)."""
    from optimize.dashboard import queue as q
    global _FLEET
    fleet_stop()                                  # stop any prior fleet first
    _FLEET = []
    cap = _worker_cap()
    for i, c in enumerate(q.expand(cfg)):
        item = {"instrument": c.get("instrument"), "timeframe": c.get("timeframe"), "state": "pending"}
        if i >= cap:
            item.update(state="deferred",
                        detail=f"exceeds worker cap ({cap}); relaunch after the running cells finish")
            _FLEET.append({"run": None, "item": item})
            continue
        r = RunManager()
        res = r.start(c)
        if res.get("ok"):
            item.update(state="running", study=res.get("study"), target=res.get("target"))
        else:
            item.update(state="failed", detail=res.get("detail", ""))
            r = None
        _FLEET.append({"run": r, "item": item})
    return fleet_state()


def fleet_state() -> list[dict]:
    out = []
    for e in _FLEET:
        it = dict(e["item"])
        r = e["run"]
        if r is not None:
            st = r.state()
            it["running"] = st["running"]
            it["returncode"] = st["returncode"]
            it["target"] = st["target"]
            if st["running"]:
                it["done"] = r.done_count()
            elif it.get("state") == "running":       # transitioned running → done since last poll
                it["state"] = "finished" if st["returncode"] == 0 else "stopped"
        out.append(it)
    return out


def fleet_stop() -> dict:
    n = sum(1 for e in _FLEET if e["run"] is not None and (e["run"].stop() or True))
    return {"ok": True, "stopped": n}


# ── detached orphans: cc-runs still alive after a control-plane restart (#46) ──────────────────────
# start_new_session=True detaches owned optimizer children from the control plane, so a restart loses
# the handle. We recover them by scanning the process table for cc-prefixed optimizer runs.
import re as _re


def _parse_ps(text: str) -> list[dict]:
    """Parse `ps -eo pid,pgid,args` output → cc-prefixed optimizer runs [{pid,pgid,study,prefix,tf,instrument}]."""
    runs = []
    for line in text.splitlines():
        if "optimize/optimizer.py" not in line or "--study-prefix cc" not in line:
            continue
        toks = line.split()
        try:
            pid, pgid = int(toks[0]), int(toks[1])
        except (ValueError, IndexError):
            continue
        m = _re.search(r"--study-prefix (cc\w+)", line)
        prefix = m.group(1) if m else None
        tf = next((toks[i + 1] for i, t in enumerate(toks) if t.endswith("optimizer.py") and i + 1 < len(toks)), None)
        mi = _re.search(r"--instrument (\w+)", line)
        inst = mi.group(1) if mi else "NQ"
        study = (f"{prefix}_{tf}" + ("" if inst == "NQ" else f"_{inst}")) if (prefix and tf) else None
        runs.append({"pid": pid, "pgid": pgid, "prefix": prefix, "tf": tf, "instrument": inst, "study": study})
    return runs


def scan_cc_runs() -> list[dict]:
    try:
        out = subprocess.run(["ps", "-eo", "pid,pgid,args"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    return _parse_ps(out)


def _owned_pids() -> set:
    pids = set()
    if _MGR.proc is not None:
        pids.add(_MGR.proc.pid)
    for e in _FLEET:
        r = e.get("run")
        if r is not None and r.proc is not None:
            pids.add(r.proc.pid)
    return pids


def detached_runs() -> list[dict]:
    """cc-optimizer processes alive but NOT owned by this control plane (orphans from a restart)."""
    owned = _owned_pids()
    return [r for r in scan_cc_runs() if r["pid"] not in owned]


def stop_all() -> dict:
    """Stop the owned primary run AND kill any detached orphans, so the UI's Stop always clears runs."""
    _MGR.stop()
    killed = 0
    for r in detached_runs():
        try:
            os.killpg(r["pgid"], signal.SIGKILL)
            killed += 1
        except (ProcessLookupError, PermissionError):
            pass
    return {"ok": True, "detail": f"stopped owned run + {killed} detached orphan(s)"}


def done_count_for(prefix: str, tf: str) -> int:
    """Completed-trial count for a study by prefix+tf (store-aware) — used for detached-orphan progress."""
    if not prefix or not tf:
        return 0
    try:
        r = subprocess.run([_python(), "optimize/trial_count.py", tf, "--prefix", prefix, "--finished"],
                           cwd=str(_PI), env=_child_env({}), capture_output=True, text=True, timeout=20)
        return int("".join(c for c in r.stdout if c.isdigit()) or 0)
    except Exception:
        return 0
