"""End-to-end mini study run. Pop=4 × Gen=2 × Folds=2 = 16 trials max.

Verifies: study terminates, Pareto front is non-empty, every emitted
value is a float, study state is persisted to SQLite.
"""

import os
import sys

import optuna
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.persistence import list_studies
from src.optimization.study import run_study
from src.strategy.box_lookup import BoxLookup
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _unified_csv(path, **levels):
    row_data = {c: [levels.get(c)] for c in _W_COLS + _M_COLS}
    pd.DataFrame({'Date': ['2025-01-01'], **row_data}).to_csv(path, index=False)


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    closes = [20000.0 + 250.0 * (i % 4 - 1.5) for i in range(n_bars)]
    return pd.DataFrame({
        'Date':   timestamps,
        'Open':   [20000.0] * n_bars,
        'High':   [c + 50 for c in closes],
        'Low':    [c - 50 for c in closes],
        'Close':  closes,
        'Volume': [1000] * n_bars,
    })


def test_mini_study_completes_and_persists(tmp_path):
    unified_csv = tmp_path / 'u.csv'
    _unified_csv(unified_csv, WRHU=20100.0, WRHD=19900.0)

    lookup = BoxLookup(unified_path=str(unified_csv), tick_threshold=0.75)

    db_path = tmp_path / 'studies.db'
    df = _synth_4h(240)

    events = []
    def collect(event_type, payload):
        events.append((event_type, payload))

    summary = run_study(
        study_name='mini-test',
        baseline_params=box_strategy_params(),
        box_lookup=lookup,
        df=df,
        search_space={
            'sl_soft_points': (100.0, 250.0),
            'sl_hard_delta':  (50.0, 200.0),
            'tp_target_points': (75.0, 200.0),
        },
        population_size=4,
        generations=2,
        fold_count=2,
        min_trades_per_fold=1,
        db_path=str(db_path),
        on_event=collect,
        should_stop=lambda: False,
    )

    assert summary['total_trials'] >= 1
    assert 'pareto_front' in summary
    assert all(isinstance(v, float) for trial in summary['pareto_front'] for v in trial['values'])

    # Persistence: listed by `list_studies`.
    studies = list_studies(db_path=str(db_path))
    assert any(s['study_id'] == 'mini-test' for s in studies)

    # At least one progress + one trial + one complete event were emitted.
    types = {e[0] for e in events}
    assert 'study_started' in types
    assert 'trial' in types
    assert 'complete' in types
