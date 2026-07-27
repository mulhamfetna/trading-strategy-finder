"""Result-neutral instrumentation of the indicator vote cache (issue #54, Task 1).

`Probe` monkeypatches three call sites and only COUNTS/TIMES them — it never alters the arrays that flow
through, so a run with the probe installed produces byte-identical votes to one without it:

  * ``vote_cache.get``  — a non-None return is a DISK-CACHE HIT (bytes_read); a None return is a MISS.
  * ``vote_cache.put``  — an array persisted (bytes_written).
  * ``indicators.runner._ind_vote`` — a genuine COLD COMPUTE of one indicator's vote array; we accumulate
    wall-clock and per-indicator counts (keyed by ``ind.key``) so Task 2 can rank the costliest indicators.

The in-process ``core._VOTE_MEMO`` hits bypass ``vote_cache.get`` entirely, so this measures the DISK
cache's hit-rate and the true cold-compute cost — exactly the cold/warm/I-O split Task 2 needs.

Usage (single process — the baseline runner installs it around one study slice):

    p = Probe(); p.install()
    ...run the sweep...
    p.uninstall()
    profile = p.snapshot()
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Probe:
    hits: int = 0
    misses: int = 0
    cold_seconds: float = 0.0
    cold_computes: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    per_indicator: dict = field(default_factory=dict)  # ind.key -> {"computes": int, "cold_seconds": float}
    _installed: bool = False
    _orig: dict = field(default_factory=dict)

    # -- lifecycle ---------------------------------------------------------------------------------
    def install(self) -> "Probe":
        if self._installed:
            return self
        from optimize import vote_cache
        from indicators import runner

        self._orig = {
            "get": vote_cache.get,
            "put": vote_cache.put,
            "ind_vote": runner._ind_vote,
        }
        _orig_get, _orig_put, _orig_vote = (
            self._orig["get"], self._orig["put"], self._orig["ind_vote"],
        )

        def get_wrapper(dkey):
            arr = _orig_get(dkey)
            if arr is None:
                self.misses += 1
            else:
                self.hits += 1
                self.bytes_read += int(getattr(arr, "nbytes", 0))
            return arr

        def put_wrapper(dkey, arr):
            try:
                self.bytes_written += int(np.asarray(arr).nbytes)
            except Exception:
                pass
            return _orig_put(dkey, arr)

        def vote_wrapper(ind, ctx, bdir, src=None):
            t0 = time.perf_counter()
            out = _orig_vote(ind, ctx, bdir, src)
            dt = time.perf_counter() - t0
            self.cold_seconds += dt
            self.cold_computes += 1
            key = getattr(ind, "key", getattr(getattr(ind, "config", None), "key", "?"))
            slot = self.per_indicator.setdefault(key, {"computes": 0, "cold_seconds": 0.0})
            slot["computes"] += 1
            slot["cold_seconds"] += dt
            return out

        vote_cache.get = get_wrapper
        vote_cache.put = put_wrapper
        runner._ind_vote = vote_wrapper
        self._installed = True
        return self

    def uninstall(self) -> "Probe":
        if not self._installed:
            return self
        from optimize import vote_cache
        from indicators import runner

        vote_cache.get = self._orig["get"]
        vote_cache.put = self._orig["put"]
        runner._ind_vote = self._orig["ind_vote"]
        self._installed = False
        return self

    def __enter__(self):
        return self.install()

    def __exit__(self, *_exc):
        self.uninstall()
        return False

    # -- reporting ---------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        total = self.hits + self.misses
        top = sorted(self.per_indicator.items(), key=lambda kv: -kv[1]["cold_seconds"])
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (self.hits / total) if total else 0.0,
            "cold_seconds": round(self.cold_seconds, 6),
            "cold_computes": self.cold_computes,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "per_indicator": {
                k: {"computes": v["computes"], "cold_seconds": round(v["cold_seconds"], 6)}
                for k, v in top
            },
        }
