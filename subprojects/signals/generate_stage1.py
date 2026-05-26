"""Stage 1 — per-(candle, box) signal extractor.

For each 4h candle in the chosen dataset preset, emit one row per active
box level pair on the candle's mapped box-date row. Each row is labelled
`long`, `short`, or `hold` based on candle color + range-touch + close
vs box edges. See subproject_signals_stage1_round5_FINAL.md for the spec.

Usage:
    python3 subprojects/signals/generate_stage1.py --preset 2026
    python3 subprojects/signals/generate_stage1.py --preset full --out /tmp/x.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator, List, Tuple

import pandas as pd

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _REPO_ROOT)

from src.data.loader import load_data
from src.strategy.box_lookup import (
    _WEEKLY_LEVELS,
    _MONTHLY_LEVELS,
    BoxLookup,
)

_LEVEL_PAIRS: List[Tuple[str, str, str]] = _WEEKLY_LEVELS + _MONTHLY_LEVELS

_PRESET_PATHS = {
    'full': ('data/full_data/NQ_4h.csv',      'data/full_data/NQ_full_data.csv'),
    '2025': ('data/2025_data/NQ_4h_2025.csv', '2025_data/NQ_full_data_2025.csv'),
    '2026': ('data/2026_data/NQ_4h_2026.csv', '2026_data/NQ_full_data_2026.csv'),
}

_OUT_COLS = [
    'datetime', 'open', 'high', 'low', 'close', 'volume',
    'signal', 'box_id', 'box_upper', 'box_lower',
]


def _resolve_box_paths(preset: str) -> Tuple[str, str]:
    """Resolve (candles_4h, boxes) CSV paths for a preset. Boxes filename
    varies by year; check both `NQ_full_data_{year}.csv` and
    `NQ_full_data.csv` inside the preset directory."""
    if preset == 'full':
        return (
            os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_4h.csv'),
            os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_full_data.csv'),
        )
    sub = f'{preset}_data'
    candles = os.path.join(_REPO_ROOT, 'data', sub, f'NQ_4h_{preset}.csv')
    boxes_yr = os.path.join(_REPO_ROOT, 'data', sub, f'NQ_full_data_{preset}.csv')
    boxes_pl = os.path.join(_REPO_ROOT, 'data', sub, 'NQ_full_data.csv')
    boxes = boxes_yr if os.path.exists(boxes_yr) else boxes_pl
    return candles, boxes


def _emit_rows(
    candles_df: pd.DataFrame,
    box_df_indexed: pd.DataFrame,
) -> Iterator[dict]:
    """Yield one dict per output row across all candles."""
    for _, candle in candles_df.iterrows():
        ts        = pd.Timestamp(candle['Date'])
        open_     = float(candle['Open'])
        high      = float(candle['High'])
        low       = float(candle['Low'])
        close     = float(candle['Close'])
        volume    = int(candle['Volume']) if not pd.isna(candle['Volume']) else 0
        candle_iso = ts.isoformat()

        if close > open_:
            color = 'green'
        elif close < open_:
            color = 'red'
        else:
            color = 'none'

        box_date = BoxLookup._candle_to_box_date(ts)
        try:
            row = box_df_indexed.loc[box_date]
        except KeyError:
            row = None

        active: List[Tuple[str, float, float]] = []
        if row is not None:
            box_date_iso = box_date.date().isoformat()
            for upper_col, lower_col, label in _LEVEL_PAIRS:
                if upper_col not in row.index or lower_col not in row.index:
                    continue
                u = row[upper_col]
                l = row[lower_col]
                if pd.isna(u) or pd.isna(l):
                    continue
                active.append((label, float(u), float(l)))

        if not active:
            yield {
                'datetime':  candle_iso,
                'open':      open_,
                'high':      high,
                'low':       low,
                'close':     close,
                'volume':    volume,
                'signal':    'hold',
                'box_id':    None,
                'box_upper': None,
                'box_lower': None,
            }
            continue

        for label, b_upper, b_lower in active:
            touched = (low <= b_upper) and (high >= b_lower)
            if not touched:
                signal = 'hold'
            elif color == 'green' and close > b_upper:
                signal = 'long'
            elif color == 'red' and close < b_lower:
                signal = 'short'
            else:
                signal = 'hold'

            box_id = f"{label.replace(' ', '_')}_{box_date.date().isoformat()}"
            yield {
                'datetime':  candle_iso,
                'open':      open_,
                'high':      high,
                'low':       low,
                'close':     close,
                'volume':    volume,
                'signal':    signal,
                'box_id':    box_id,
                'box_upper': b_upper,
                'box_lower': b_lower,
            }


def generate(candles_csv: str, boxes_csv: str) -> pd.DataFrame:
    """Produce the Stage 1 dataframe from the two input CSVs."""
    candles_df = load_data(candles_csv)
    box_df = pd.read_csv(boxes_csv)
    box_df['Date'] = pd.to_datetime(box_df['Date']).dt.normalize()
    box_df = box_df.set_index('Date', drop=False)

    rows = list(_emit_rows(candles_df, box_df))
    df = pd.DataFrame(rows, columns=_OUT_COLS)
    df = df.sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False],
        kind='mergesort',
        na_position='last',
    ).reset_index(drop=True)
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description='Stage 1 signal extractor')
    parser.add_argument('--preset', choices=['full', '2025', '2026'], default='2026')
    parser.add_argument('--out', default=None, help='Output CSV path (overrides default).')
    args = parser.parse_args()

    candles_csv, boxes_csv = _resolve_box_paths(args.preset)
    if not os.path.exists(candles_csv):
        print(f"ERROR: candles CSV not found: {candles_csv}", file=sys.stderr)
        return 2
    if not os.path.exists(boxes_csv):
        print(f"ERROR: boxes CSV not found: {boxes_csv}", file=sys.stderr)
        return 2

    out_path = args.out or os.path.join(
        os.path.dirname(__file__), f'signals_{args.preset}.csv'
    )

    df = generate(candles_csv, boxes_csv)
    df.to_csv(out_path, index=False)

    by_signal = df['signal'].value_counts().to_dict()
    print(f"wrote {len(df)} rows to {out_path}")
    print(f"  candles in: {candles_csv}")
    print(f"  boxes  in: {boxes_csv}")
    print(f"  by signal: {by_signal}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
