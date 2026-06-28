import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from optimize import core, vote_cache
from optimize.l2 import engine, payload
from indicators import library


def test_l2_disk_warm_after_memo_clear(tmp_path):
    vote_cache.set_cache_dir(tmp_path); vote_cache._clear_disk_cache()
    l1 = payload.run_l1_cached("4h")
    if hasattr(l1, "_l2_vote_memo"):
        del l1._l2_vote_memo                                     # fresh in-memory memo
    src = engine._cached_1min_source(l1)
    inds = library.from_specs([{"key": "macd", "enabled": True, "mode": "confirm",
                                "params": {"fast": 12, "slow": 26, "signal": 9}}])
    v1 = engine._committee_votes(l1, inds, src)                  # cold: computes + persists
    arr1 = next(iter(v1.values())).copy()
    del l1._l2_vote_memo                                         # simulate a fresh process
    v2 = engine._committee_votes(l1, inds, src)                  # must HIT disk
    assert np.array_equal(arr1, next(iter(v2.values())))
    dkey = vote_cache.disk_key(core._slice_sig(l1.df_dec, l1.df1, l1.bar_td), True, "macd", "confirm",
                               (("fast", 12), ("signal", 9), ("slow", 26)))
    assert vote_cache.get(dkey) is not None
