"""L2 dashboard backend — orchestration for the dashboard-inside-dashboard (frontend/l2.html).
Runs the cached frozen L1 (lean 4h) + a manual L2 profile, serializes a chart-ready payload, and
persists hand-tuned L2 profiles. server.py is a thin router over this module."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, metrics, dataset   # noqa: E402
from indicators import library                                # noqa: E402

_PROFILES = _PI / "profiles" / "l2_profiles.json"
_L1_CACHE: dict = {}

# Deterministic anchor profile (no indicators / no vol gate => take every flat dropped signal).
PERMISSIVE: dict = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
                    "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


class L2ParamError(ValueError):
    """Invalid L2 profile parameter — surfaced to the UI as HTTP 400 (never silently clamped)."""


def run_l1_cached(tf: str = "4h"):
    """Frozen L1 (lean champion), computed once per process (~38s first call, then instant)."""
    if tf not in _L1_CACHE:
        _L1_CACHE[tf] = l1_runner.run_l1(tf)
    return _L1_CACHE[tf]


def validate_l2_params(p: dict) -> dict:
    """Validate the focused L2 levers; return a clean engine-ready dict (window='full'). Raise on any
    bad/missing value (no silent fallback)."""
    if not isinstance(p, dict):
        raise L2ParamError("params must be an object")

    def num(key, lo=None, hi=None):
        if key not in p or p[key] is None:
            raise L2ParamError(f"missing {key}")
        try:
            v = float(p[key])
        except (TypeError, ValueError):
            raise L2ParamError(f"{key} must be a number")
        if lo is not None and v < lo:
            raise L2ParamError(f"{key} must be >= {lo}")
        if hi is not None and v > hi:
            raise L2ParamError(f"{key} must be <= {hi}")
        return v

    out = dict(
        sl_soft=num("sl_soft", 1e-6), sl_hard=num("sl_hard", 1e-6), tp=num("tp", 1e-6),
        gate_pct=num("gate_pct", 0, 100), dd_limit=num("dd_limit", 0),
        cooldown=int(num("cooldown", 0)), k=int(num("k", 1)),
        flip=bool(p.get("flip", False)), ind_1min=bool(p.get("ind_1min", False)),
        window="full",
    )
    inds = p.get("indicators", [])
    if not isinstance(inds, list):
        raise L2ParamError("indicators must be a list")
    try:
        library.from_specs([s for s in inds if s.get("enabled")])   # validates indicator params
    except Exception as e:
        raise L2ParamError(f"bad indicator config: {e}")
    out["indicators"] = inds
    return out


def load_l2_profiles() -> dict:
    if not _PROFILES.exists():
        return {}
    try:
        d = json.loads(_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l2_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise L2ParamError("profile name is required")
    validate_l2_params(preset)                       # reject garbage (no silent save)
    profs = load_l2_profiles()
    profs[name] = preset
    _PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES.write_text(json.dumps(profs, indent=1))
    return profs
