import importlib.util
import os

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(_HERE, '..', 'onboard_stock.py')


def _load():
    spec = importlib.util.spec_from_file_location('onboard_stock', _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_onboard_registry_covers_es_gc_si():
    m = _load()
    assert {'ES', 'GC', 'SI'} <= set(m.ONBOARD)


def test_shift_is_clean_backward_bijection():
    m = _load()
    for tok in ('ES', 'GC', 'SI'):
        box = m.shift_box(tok)                       # runs the shift + asserts internally
        d = pd.to_datetime(box['Date'])
        assert d.dt.dayofweek.max() <= 4             # no weekend date produced
        assert not d.duplicated().any()              # no collision
        raw = pd.to_datetime(pd.read_csv(m.ONBOARD[tok]['box'])['Date']).dt.normalize()
        assert (d < raw.values).all()                # every date strictly moved backward


def test_shifted_box_file_written():
    m = _load()
    for tok in ('ES', 'GC', 'SI'):
        m.shift_box(tok)
        out = os.path.join(_HERE, '..', 'shifted_boxes', f'{tok}_full_data_shifted.csv')
        assert os.path.exists(out), f'shifted box not written for {tok}'
