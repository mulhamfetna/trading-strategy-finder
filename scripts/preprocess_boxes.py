"""
One-time preprocessing: shift box Date columns by -2 calendar days.

Run once from repo root:
    python3 scripts/preprocess_boxes.py

Reads:  NQ_week_data.csv, NQ_month_data.csv
Writes: NQ_week_data_shifted.csv, NQ_month_data_shifted.csv
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
SHIFT = pd.Timedelta(days=2)


def shift_file(src: str, dst: str) -> None:
    df = pd.read_csv(ROOT / src, parse_dates=['Date'])
    original = df['Date'].copy()
    df['Date'] = df['Date'] - SHIFT
    out = ROOT / dst
    df.to_csv(out, index=False)
    print(f"{src} → {dst}  ({len(df)} rows, first date {original.iloc[0].date()} → {df['Date'].iloc[0].date()})")


if __name__ == '__main__':
    shift_file('NQ_week_data.csv',  'NQ_week_data_shifted.csv')
    shift_file('NQ_month_data.csv', 'NQ_month_data_shifted.csv')
    print("Done. Commit NQ_*_shifted.csv and never re-run this script.")
