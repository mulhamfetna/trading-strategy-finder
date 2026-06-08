"""WS-AS.1 — instrument registry: the no-mix contract + coverage guarantees."""
import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE)
from instruments import REGISTRY, TOKENS, TIMEFRAMES  # noqa: E402

EXPECTED = {'NQ', 'ES', 'QQQ-RTH', 'QQQ-ETH', 'SQQQ-RTH', 'SQQQ-ETH'}


def test_exactly_six_expected_tokens():
    assert set(TOKENS) == EXPECTED


@pytest.mark.parametrize('tok', sorted(EXPECTED))
def test_all_candle_files_exist(tok):
    inst = REGISTRY[tok]
    for tf in TIMEFRAMES:
        assert os.path.isfile(inst.candle_csv(tf)), f"missing {tok} {tf}: {inst.candle_csv(tf)}"


@pytest.mark.parametrize('tok', sorted(EXPECTED))
def test_box_file_exists(tok):
    assert os.path.isfile(REGISTRY[tok].box_csv)


@pytest.mark.parametrize('tok', sorted(EXPECTED))
def test_box_range_covers_candles(tok):
    """No-mix + coverage: the instrument's own box dates must span its candle dates."""
    inst = REGISTRY[tok]
    box = pd.read_csv(inst.box_csv, usecols=['Date'])
    bmin, bmax = pd.to_datetime(box['Date']).min(), pd.to_datetime(box['Date']).max()
    c = pd.read_csv(inst.candle_csv('4h'), usecols=['datetime'])
    cdt = pd.to_datetime(c['datetime'])
    assert bmin.normalize() <= cdt.min().normalize()
    assert bmax.normalize() >= cdt.max().normalize()


def test_tokens_unique_no_rth_eth_collision():
    # RTH and ETH variants must produce distinct filename tokens
    assert len({REGISTRY[t].token for t in TOKENS}) == len(TOKENS)
    assert 'QQQ-RTH' in TOKENS and 'QQQ-ETH' in TOKENS
