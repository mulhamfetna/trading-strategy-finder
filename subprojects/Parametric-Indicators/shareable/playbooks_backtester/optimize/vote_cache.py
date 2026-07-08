"""Disk-persistent indicator-vote cache (item 3). Persists the per-(slice, config) vote arrays computed by
core._cached_votes / engine._committee_votes so the cold ifvg/breaker computes are paid ONCE EVER and shared
across worker processes + watchdog respawns. Sits BEHIND the in-process memos; result-neutral by construction
(stores/reloads the exact array). Atomic best-effort write mirrors the L1 disk cache (payload §4.4)."""
from __future__ import annotations
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
import numpy as np

# BUMP whenever any indicator's vote math changes — guards against a stale array (old code) loading.
CACHE_VERSION = "vc1"
_DIR = Path(tempfile.gettempdir()) / "wsh_vote_cache"


def set_cache_dir(path) -> None:
    global _DIR
    _DIR = Path(path)


def _clear_disk_cache() -> None:
    shutil.rmtree(_DIR, ignore_errors=True)


def disk_key(slice_sig, use1, key, mode, params_tuple) -> str:
    raw = repr((CACHE_VERSION, slice_sig, bool(use1), key, mode, params_tuple))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _file(dkey: str) -> Path:
    return _DIR / f"vote_{dkey}.npy"


def get(dkey: str):
    """Cached vote array, or None on miss / any error (best-effort)."""
    f = _file(dkey)
    try:
        if f.exists():
            return np.load(f, allow_pickle=False)
    except Exception:
        pass
    return None


def put(dkey: str, arr) -> None:
    """Atomically persist a vote array; best-effort — never raises into the run."""
    tmp = None
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(_DIR), suffix=".tmp", delete=False) as tf:
            np.save(tf, np.asarray(arr), allow_pickle=False)
            tmp = Path(tf.name)
        os.replace(tmp, _file(dkey))                 # atomic on one filesystem
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink()
            except Exception:
                pass
