import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
import pytest
from optimize.l2.contributors import combine, gate


def _inputs(n=8):
    rng = np.arange(n)
    vol = np.ones(n, bool)
    veto = (rng % 7 == 0)                 # already-combined veto (caller OR-s contributor vetoes in)
    nq_confirm = (rng % 2 == 0)
    nq_cc = (rng % 3).astype(np.int64)
    ccount = ((rng + 1) % 4).astype(np.int64)
    return vol, veto, nq_confirm, nq_cc, ccount


def test_separate_and_matches_manual():
    vol, veto, nqc, nqcc, cc = _inputs()
    parsed = [(cc, 2, True)]
    out = combine.combine_eligibility(vol, veto, nqc, nqcc, 1, 2, parsed, "separate_and")
    expect = vol & ~veto & (nqc & (cc >= 2))
    assert np.array_equal(out, expect)


def test_or_boost_and_merged_and_sentinel_noop():
    vol, veto, nqc, nqcc, cc = _inputs()
    sent = np.full(len(cc), gate.NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    for topo in ("separate_and", "merged", "or_boost"):
        base = combine.combine_eligibility(vol, veto, nqc, nqcc, 1, 2, [], topo)
        with_sent = combine.combine_eligibility(vol, veto, nqc, nqcc, 1, 2, [(sent, 3, False)], topo)
        assert np.array_equal(base, with_sent), f"sentinel changed {topo}"


def test_bad_topology_raises():
    vol, veto, nqc, nqcc, cc = _inputs()
    with pytest.raises(ValueError):
        combine.combine_eligibility(vol, veto, nqc, nqcc, 1, 2, [(cc, 1, True)], "nope")
