"""Split the three data CSVs (4h candles, 1-min candles, unified box file)
into per-year files for 2025 and 2026.

Inputs (read from the repo root):
  - NQ_4h.csv          — 4h OHLCV, date column "datetime"
  - NQ_1m.csv          — 1-min OHLCV, date column "datetime"
  - NQ_full_data.csv   — 16-level box CSV, date column "Date"

Outputs (written next to the inputs):
  - NQ_4h_2025.csv, NQ_4h_2026.csv
  - NQ_1m_2025.csv, NQ_1m_2026.csv
  - NQ_full_data_2025.csv, NQ_full_data_2026.csv

The script does nothing else. It does not import strategy code, does not run
backtests, does not touch the engine, does not modify the originals.

Usage:
    python3 scripts/split_data_by_year.py
"""
from __future__ import annotations

import csv
import os
import sys
from typing import Iterable


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Each entry: (input filename, date column name, list of years to split into).
SPLITS = [
    ('NQ_4h.csv',         'datetime', ['2025', '2026']),
    ('NQ_1m.csv',         'datetime', ['2025', '2026']),
    ('NQ_full_data.csv',  'Date',     ['2025', '2026']),
]


def _output_path(input_filename: str, year: str) -> str:
    """`NQ_4h.csv` + `2025` → `NQ_4h_2025.csv`."""
    stem, ext = os.path.splitext(input_filename)
    return os.path.join(REPO_ROOT, f'{stem}_{year}{ext}')


def _split_one(input_filename: str, date_col: str, years: Iterable[str]) -> None:
    """Stream `input_filename` once, fan rows out into one output file per year.

    Streams row-by-row so memory stays flat even for `NQ_1m.csv` (~28 MB,
    hundreds of thousands of rows).
    """
    input_path = os.path.join(REPO_ROOT, input_filename)
    if not os.path.exists(input_path):
        print(f'  SKIP {input_filename}: file not found at {input_path}', file=sys.stderr)
        return

    out_paths = {year: _output_path(input_filename, year) for year in years}
    counts = {year: 0 for year in years}

    with open(input_path, 'r', newline='', encoding='utf-8') as fin:
        reader = csv.reader(fin)
        try:
            header = next(reader)
        except StopIteration:
            print(f'  SKIP {input_filename}: empty file', file=sys.stderr)
            return

        try:
            date_idx = header.index(date_col)
        except ValueError:
            raise SystemExit(
                f'{input_filename}: expected column "{date_col}" in header, got {header}'
            )

        writers = {}
        files = {}
        try:
            for year, path in out_paths.items():
                fout = open(path, 'w', newline='', encoding='utf-8')
                files[year] = fout
                w = csv.writer(fout)
                w.writerow(header)
                writers[year] = w

            for row in reader:
                if not row:
                    continue
                cell = row[date_idx]
                if len(cell) < 4:
                    continue
                year = cell[:4]
                w = writers.get(year)
                if w is None:
                    continue  # year not in our target set — drop the row
                w.writerow(row)
                counts[year] += 1
        finally:
            for fout in files.values():
                fout.close()

    for year, path in out_paths.items():
        print(f'  wrote {os.path.basename(path):28s}  {counts[year]:>9d} rows')


def main() -> int:
    print(f'Repo root: {REPO_ROOT}')
    for input_filename, date_col, years in SPLITS:
        print(f'\nSplitting {input_filename} by {date_col} → years {years}:')
        _split_one(input_filename, date_col, years)
    print('\nDone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
