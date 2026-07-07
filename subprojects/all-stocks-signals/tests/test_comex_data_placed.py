import os

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
_ALL = os.path.join(_ROOT, 'ALL_STOCKS')
TFS = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']


def test_candles_present_and_shaped():
    for tok in ('GC', 'SI'):
        for tf in TFS:
            p = os.path.join(_ALL, 'CANDLES', 'COMEX', f'{tok}_Continuous_Data', f'{tok}_{tf}.csv')
            assert os.path.exists(p), f'missing {p}'
            df = pd.read_csv(p, nrows=5)
            assert list(df.columns) == ['datetime', 'open', 'high', 'low', 'close', 'volume'], f'{p} cols'


def test_boxes_present_and_shaped():
    # The frozen Stage 1 engine reads box columns BY NAME, so the SET of columns must match NQ's
    # (column order may differ between data vendors — that is fine and irrelevant to lookups).
    nq_box = os.path.join(_ALL, 'BOXS', 'CME', 'NQ', 'NQ_full_data.csv')
    nq_cols = set(pd.read_csv(nq_box, nrows=1).columns)
    for tok in ('GC', 'SI'):
        p = os.path.join(_ALL, 'BOXS', 'COMEX', tok, f'{tok}_full_data.csv')
        assert os.path.exists(p), f'missing {p}'
        cols = set(pd.read_csv(p, nrows=1).columns)
        assert cols == nq_cols, f'{p} column set must match NQ box: missing {nq_cols - cols}, extra {cols - nq_cols}'
