import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import core, vote_cache
from optimize.l2 import payload
from indicators import library


def test_disk_warm_after_memo_clear_is_identical(tmp_path):
    vote_cache.set_cache_dir(tmp_path); vote_cache._clear_disk_cache(); core._clear_caches()
    l1 = payload.run_l1_cached("4h")
    d, d1, box, bt = l1.df_dec, l1.df1, l1.box, l1.bar_td
    from indicators import runner
    src = runner.indicator_source_1min(d, d1, bt)
    inds = library.from_specs([{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                "params": {"fast": 20, "slow": 50}}])
    v1 = core._cached_votes(d, d1, box, inds, src, bt)            # cold: computes + persists
    arr1 = next(iter(v1.values())).copy()
    core._clear_caches()                                         # simulate a fresh process (memo gone)
    assert not core._VOTE_MEMO                                   # in-memory empty
    v2 = core._cached_votes(d, d1, box, inds, src, bt)           # must HIT disk
    arr2 = next(iter(v2.values()))
    assert np.array_equal(arr1, arr2)                            # byte-identical from disk
    # and the disk file exists for this config
    dkey = vote_cache.disk_key(core._slice_sig(d, d1, bt), True, "ema_trend", "confirm",
                               (("fast", 20), ("slow", 50)))
    assert vote_cache.get(dkey) is not None
