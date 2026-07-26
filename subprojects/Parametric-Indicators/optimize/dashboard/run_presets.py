"""Saved run-config presets for the control center (named optimizer configs). JSON-file store.
Distinct from the top-level `presets` module (strategy/playbook presets)."""
from __future__ import annotations

import json
import os
from pathlib import Path

_STORE = Path(os.environ.get("WSH_RUN_PRESETS", str(Path.home() / ".wsh" / "run_presets.json")))


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text()) if _STORE.exists() else {}
    except Exception:
        return {}


def _save_all(d: dict) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, sort_keys=True))


def save(name: str, cfg: dict) -> None:
    d = _load()
    d[name] = cfg
    _save_all(d)


def list_names() -> list[str]:
    return sorted(_load())


def get(name: str):
    return _load().get(name)


def delete(name: str) -> None:
    d = _load()
    if d.pop(name, None) is not None:
        _save_all(d)
