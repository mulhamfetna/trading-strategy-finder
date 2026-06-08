"""WS-AS.2/AS.4 — NQ parity: the new driver reproduces the committed NQ_SIGNALS_DELIVERY
byte-for-byte. This is the correctness anchor for the whole generalization. Uses 4h + 1h
(fast) per preset; the full 7-TF gate is run manually (verify_nq_parity.sh)."""
import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _HERE)
import generate_signals as gs  # noqa: E402
from instruments import REGISTRY  # noqa: E402

_DELIVERY = os.path.join(_REPO, 'NQ_SIGNALS_DELIVERY')
pytestmark = pytest.mark.skipif(not os.path.isdir(_DELIVERY),
                                reason='committed NQ_SIGNALS_DELIVERY not present')


def _stage1(tf, preset):
    inst = REGISTRY['NQ']
    box = gs.load_boxes(inst.box_csv)
    return gs.stage1_for_preset(inst.candle_csv(tf), box, preset)


@pytest.mark.parametrize('tf', ['4h', '1h'])
@pytest.mark.parametrize('preset', ['full', '2025', '2026'])
def test_all_signals_match_committed(tf, preset):
    got = _stage1(tf, preset)
    ref = pd.read_csv(os.path.join(_DELIVERY, '1_all_signals', f'NQ_{tf}_{preset}.csv'))
    pd.testing.assert_frame_equal(got.reset_index(drop=True), ref.reset_index(drop=True),
                                  check_dtype=False)


@pytest.mark.parametrize('tf', ['4h', '1h'])
@pytest.mark.parametrize('preset', ['full', '2025', '2026'])
def test_reverse_match_committed(tf, preset):
    s1 = _stage1(tf, preset)
    got = gs.g2.generate(s1)
    ref = pd.read_csv(os.path.join(_DELIVERY, '3_reverse_signals', f'NQ_{tf}_{preset}.csv'))
    pd.testing.assert_frame_equal(got.reset_index(drop=True), ref.reset_index(drop=True),
                                  check_dtype=False)
