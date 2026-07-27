"""Task 1 gate: the cache probe COUNTS without changing arrays (result-neutral)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Parametric-Indicators root

import numpy as np

from optimize import vote_cache
from optimize.perf.cache_probe import Probe


def test_probe_counts_hits_and_misses_without_changing_arrays(tmp_path):
    vote_cache.set_cache_dir(tmp_path)
    vote_cache._clear_disk_cache()
    p = Probe().install()
    try:
        dkey = vote_cache.disk_key(("sig",), True, "rsi", "confirm", (("n", 14),))
        arr = np.arange(10, dtype=np.int8)
        assert vote_cache.get(dkey) is None          # miss (nothing stored yet)
        vote_cache.put(dkey, arr)
        got = vote_cache.get(dkey)                    # hit
    finally:
        p.uninstall()
    snap = p.snapshot()
    assert snap["misses"] == 1
    assert snap["hits"] == 1
    assert snap["hit_rate"] == 0.5
    assert snap["bytes_written"] == arr.nbytes
    assert np.array_equal(got, arr)                  # result-neutral: exact array round-trips


def test_uninstall_restores_originals(tmp_path):
    vote_cache.set_cache_dir(tmp_path)
    orig_get = vote_cache.get
    p = Probe().install()
    assert vote_cache.get is not orig_get            # patched
    p.uninstall()
    assert vote_cache.get is orig_get                # restored exactly
