"""Full-candles driver — Stage 1 + Stage 2 signals for ALL timeframes.

Previously the signal pipeline only ran on the 4h candle file. The new
`Full_Canldes_Data/` drop ships seven timeframes (1m, 2m, 5m, 15m, 1h, 2h, 4h)
covering the same 2025-01-01 → 2026-05-19 range, against the SAME boxes
(`data/full_data/NQ_full_data.csv`). This script regenerates, per timeframe and
per preset (full / 2025 / 2026), the exact three artifacts the project already
defines — using the EXACT same code paths so nothing can drift:

  1. all-signals      signals_<TF>_<preset>.csv
         the Stage 1 per-(candle, box) labelling incl. `hold` rows.
         Produced via generate_stage1._emit_rows (the frozen Stage 1 rule).

  2. holds-dropped    no_holds/signals_<TF>_<preset>_no_holds.csv
         the same rows filtered to signal ∈ {long, short}. A pure view of (1).

  3. reverse-signals  reverse_signals_<TF>_<preset>.csv  (+ by_direction/)
         the Stage 2 reverse-window extractor (window_high = max high,
         window_low = min low, direction-aware tp/sl, holds-between count).
         Produced via generate_stage2.generate (the frozen Stage 2 rule).

Preset split matches the original exactly: the year files were split on the
candle's calendar year (2025 rows ⊎ 2026 rows = full rows), and Stage 2 ran
independently on each preset's own Stage 1 stream (so a window straddling the
year boundary exists only in `full`). We reproduce that by year-filtering the
candle stream before Stage 1 and running Stage 2 per preset.

Boxes are timeframe-independent (weekly/monthly levels keyed to the box-date),
so every timeframe reuses the single unified box CSV. The candle→box-date
mapping (hour >= 18 → +1 day) is hour-based and therefore identical for every
timeframe.

Usage:
    python3 subprojects/signals/full_candles/generate_full_candles.py
    python3 subprojects/signals/full_candles/generate_full_candles.py --timeframes NQ_4h NQ_1h
    python3 subprojects/signals/full_candles/generate_full_candles.py --presets full
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from typing import List, Optional

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_SIGNALS_ROOT = os.path.abspath(os.path.join(_HERE, '..'))          # subprojects/signals
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))  # project root
sys.path.insert(0, _REPO_ROOT)

from src.data.loader import load_data  # noqa: E402


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Import the FROZEN generators by file path (they live in dirs that aren't packages
# from here). Reusing their functions guarantees byte-identical methodology.
g1 = _load_module('stage1_gen', os.path.join(_SIGNALS_ROOT, 'generate_stage1.py'))
g2 = _load_module(
    'stage2_gen',
    os.path.join(_SIGNALS_ROOT, 'stage1_0_reverse_signals', 'generate_stage2.py'),
)

_DATA_DIR = os.path.join(
    _REPO_ROOT, 'Full_Canldes_Data', 'drive-download-20260602T124702Z-3-001'
)
_BOX_CSV = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_full_data.csv')

_TIMEFRAMES = ['NQ_1m', 'NQ_2m', 'NQ_5m', 'NQ_15m', 'NQ_1h', 'NQ_2h', 'NQ_4h']
_PRESETS = ['full', '2025', '2026']


def _load_boxes() -> pd.DataFrame:
    box_df = pd.read_csv(_BOX_CSV)
    box_df['Date'] = pd.to_datetime(box_df['Date']).dt.normalize()
    return box_df.set_index('Date', drop=False)


def stage1_for_preset(candles_csv: str, box_df: pd.DataFrame, preset: str) -> pd.DataFrame:
    """Stage 1 dataframe for one preset.

    Mirrors generate_stage1.generate() exactly (same _emit_rows, same columns,
    same sort) but year-filters the candle stream first — which is what the
    original per-year input files encoded.
    """
    candles = load_data(candles_csv)
    if preset != 'full':
        year = int(preset)
        candles = candles[candles['Date'].dt.year == year].reset_index(drop=True)
    rows = list(g1._emit_rows(candles, box_df))
    df = pd.DataFrame(rows, columns=g1._OUT_COLS).sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False],
        kind='mergesort',
        na_position='last',
    ).reset_index(drop=True)
    return df


def write_reverse(rev: pd.DataFrame, tf_dir: str, tf: str, preset: str) -> List[str]:
    """Write the unified reverse file + the two by_direction splits (Stage 2 layout)."""
    paths = []
    unified = os.path.join(tf_dir, f'reverse_signals_{tf}_{preset}.csv')
    rev.to_csv(unified, index=False)
    paths.append(unified)

    by_dir = os.path.join(tf_dir, 'by_direction')
    os.makedirs(by_dir, exist_ok=True)
    l2s = rev[rev['first_signal'] == 'long'].reset_index(drop=True)
    s2l = rev[rev['first_signal'] == 'short'].reset_index(drop=True)
    l2s_path = os.path.join(by_dir, f'long_to_short_{tf}_{preset}.csv')
    s2l_path = os.path.join(by_dir, f'short_to_long_{tf}_{preset}.csv')
    l2s.to_csv(l2s_path, index=False)
    s2l.to_csv(s2l_path, index=False)
    paths += [l2s_path, s2l_path]
    return paths


def run_timeframe(tf: str, presets: List[str], out_root: str) -> List[dict]:
    candles_csv = os.path.join(_DATA_DIR, f'{tf}.csv')
    if not os.path.exists(candles_csv):
        print(f"  SKIP {tf}: candle CSV not found ({candles_csv})", file=sys.stderr)
        return []
    box_df = _load_boxes()
    tf_dir = os.path.join(out_root, tf)
    no_holds_dir = os.path.join(tf_dir, 'no_holds')
    os.makedirs(no_holds_dir, exist_ok=True)

    summary = []
    for preset in presets:
        s1 = stage1_for_preset(candles_csv, box_df, preset)

        # 1. all-signals mirror
        all_path = os.path.join(tf_dir, f'signals_{tf}_{preset}.csv')
        s1.to_csv(all_path, index=False)

        # 2. holds-dropped mirror (only long/short)
        nh = s1[s1['signal'].isin(['long', 'short'])].reset_index(drop=True)
        nh_path = os.path.join(no_holds_dir, f'signals_{tf}_{preset}_no_holds.csv')
        nh.to_csv(nh_path, index=False)

        # 3. reverse-signals (max high / min low + tp/sl) via the frozen Stage 2
        rev = g2.generate(s1)
        write_reverse(rev, tf_dir, tf, preset)

        dist = s1['signal'].value_counts().to_dict()
        row = dict(
            timeframe=tf, preset=preset,
            signal_rows=len(s1),
            long=int(dist.get('long', 0)),
            short=int(dist.get('short', 0)),
            hold=int(dist.get('hold', 0)),
            no_hold_rows=len(nh),
            reverse_windows=len(rev),
        )
        summary.append(row)
        print(f"  {tf:7s} {preset:5s}: signals={len(s1):>7,}  "
              f"L/S/H={row['long']}/{row['short']}/{row['hold']}  "
              f"no_holds={len(nh):>5,}  reverse={len(rev):>4,}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description='Full-candles signal + reverse-signal generator')
    ap.add_argument('--timeframes', nargs='+', default=_TIMEFRAMES,
                    help='Subset of timeframes (default: all 7).')
    ap.add_argument('--presets', nargs='+', default=_PRESETS,
                    choices=_PRESETS, help='Subset of presets (default: full 2025 2026).')
    ap.add_argument('--out-root', default=_HERE, help='Output root (default: this dir).')
    args = ap.parse_args()

    if not os.path.exists(_BOX_CSV):
        print(f"ERROR: box CSV not found: {_BOX_CSV}", file=sys.stderr)
        return 2

    print(f"box CSV : {_BOX_CSV}")
    print(f"data dir: {_DATA_DIR}")
    print(f"out root: {args.out_root}\n")

    all_summary: List[dict] = []
    for tf in args.timeframes:
        print(f"[{tf}]")
        all_summary += run_timeframe(tf, args.presets, args.out_root)

    if all_summary:
        summ = pd.DataFrame(all_summary)
        summ_path = os.path.join(args.out_root, 'SUMMARY.csv')
        summ.to_csv(summ_path, index=False)
        print(f"\nwrote summary -> {summ_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
