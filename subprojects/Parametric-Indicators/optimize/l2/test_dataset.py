import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, dataset


def test_dataset_consistency_with_l1():
    r = l1_runner.run_l1("4h")
    ds = dataset.build_dataset(r)

    assert len(ds) == len(r.dropped_signals)
    assert ds.n_veto == sum(1 for d in r.dropped_signals if d["reason"] == "veto")
    assert ds.n_vol_gate == sum(1 for d in r.dropped_signals if d["reason"] == "vol_gate")
    assert ds.n_veto + ds.n_vol_gate == len(ds)

    # every signal carries the box direction and a flat-at-idx flag consistent with the L1 timeline
    for s in ds.signals:
        assert s.box_dir in ("long", "short")
        assert s.reason in ("veto", "vol_gate")
        assert s.l1_flat_at_idx == (not bool(r.state_timeline[s.idx]))

    # flat_candidates is the subset L2 is actually allowed to open on
    flat = ds.flat_candidates()
    assert len(flat) <= len(ds)
    assert all(s.l1_flat_at_idx for s in flat)
    print(f"[lean-4h dataset] total={len(ds)} veto={ds.n_veto} vol_gate={ds.n_vol_gate} "
          f"flat_candidates={len(flat)}")
