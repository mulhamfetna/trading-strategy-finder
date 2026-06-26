# optimize/l2/contributors/test_contrib_signal.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.l2.contributors import votes


def test_signal_stance_confirm_mode_agrees_with_box():
    # bars: box dir and ES state per signal bar; verdicts appear at the NEXT bar (entry-bar alignment).
    nq_box = np.array([1, -1, 1, 0], dtype=np.int8)    # long, short, long, hold
    es_st = np.array([1,  1, -1, 1], dtype=np.int8)    # ES: long, long, short, long
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="confirm")
    # signal-bar would_confirm = ES agrees with box: bar0 long==long True; bar1 short vs ES-long False;
    # bar2 long vs ES-short False; bar3 box hold ⇒ False. Shift to entry bar (out[idx]=@idx-1), idx0=False.
    assert list(cvote) == [False, True, False, False]
    assert not veto.any()                              # confirm-only mode ⇒ no veto channel (identity)


def test_signal_stance_both_mode_vetoes_opposition():
    nq_box = np.array([1, 1], dtype=np.int8)
    es_st = np.array([-1, -1], dtype=np.int8)          # ES opposes the long box
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="both")
    assert list(veto) == [False, True]                 # opposition vetoes (shifted to entry bar)
    assert not cvote.any()


def test_signal_stance_veto_mode_has_no_confirm_channel():
    nq_box = np.array([1, 1], dtype=np.int8)
    es_st = np.array([1, 1], dtype=np.int8)            # ES agrees, but mode=veto ⇒ no confirm emitted
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="veto")
    assert not cvote.any()                             # confirm channel identity-off
    assert not veto.any()                              # agreement never vetoes


def test_signal_truthtable_six_cells():
    # asymmetric example (Spec §5a-ii): "ES-hold vetoes NQ-short but is ignored for NQ-long"
    table = {
        ("long", "long"): "confirm", ("long", "short"): "veto",  ("long", "hold"): "ignore",
        ("short", "long"): "veto",   ("short", "short"): "confirm", ("short", "hold"): "veto",
    }
    # signal bars cover all 6 directional cells (+ a HOLD box bar that must be ignored)
    nq_box = np.array([1,  1,  1, -1, -1, -1, 0], dtype=np.int8)
    es_st = np.array([1, -1,  0,  1, -1,  0, 1], dtype=np.int8)
    cvote, veto = votes.signal_truthtable(nq_box, es_st, table)
    # per signal bar verdicts: confirm, veto, ignore, veto, confirm, veto, (box hold) ignore
    # shifted to entry bar (out[idx]=@idx-1; idx0 identity)
    assert list(cvote) == [False, True, False, False, False, True, False]
    assert list(veto) == [False, False, True, False, True, False, True]


def test_truthtable_missing_cell_and_hold_box_default_ignore():
    nq_box = np.array([0, 1], dtype=np.int8)           # bar0 HOLD box; bar1 long with empty table
    es_st = np.array([1, 1], dtype=np.int8)
    cvote, veto = votes.signal_truthtable(nq_box, es_st, table={})
    assert not cvote.any() and not veto.any()          # nothing specified ⇒ pure identity


def test_signal_masks_compatible_with_l2_gate_shape_and_off_is_identity():
    """Part-B compatibility: ES masks are bool, length n, and an all-ignore ES voter leaves
    vol_gate & ~veto & confirm BYTE-IDENTICAL — the contributors-OFF parity invariant (Spec §8.1)."""
    n = 10
    rng = np.random.default_rng(0)
    nq_box = rng.choice([-1, 0, 1], size=n).astype(np.int8)
    es_st = np.zeros(n, dtype=np.int8)                 # all hold ⇒ no agreement/opposition
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="both")
    assert cvote.dtype == bool and veto.dtype == bool and len(cvote) == len(veto) == n
    # emulate the engine gate; ES OFF must not change it
    vol_gate = rng.random(n) > 0.3
    nq_veto = rng.random(n) > 0.7
    nq_confirm = rng.random(n) > 0.2
    base = vol_gate & ~nq_veto & nq_confirm
    with_es = vol_gate & ~(nq_veto | veto) & nq_confirm  # OR ES veto into NQ veto (a MERGED topology)
    assert np.array_equal(base, with_es)               # ES all-hold ⇒ veto all-False ⇒ no change
