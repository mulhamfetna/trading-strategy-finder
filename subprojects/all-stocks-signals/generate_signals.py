"""WS-AS driver — Stage 1 + Stage 2 signals for ANY instrument, all timeframes/presets.

A config-driven generalization of `subprojects/signals/full_candles/generate_full_candles.py`.
It reuses the FROZEN generators verbatim (no math change):
  - Stage 1 : signals.generate_stage1._emit_rows   (BoxLookup hour>=18 roll, weekly+monthly)
  - Stage 2 : signals.stage1_0_reverse_signals.generate_stage2.generate

Decisions D1/D2 = "follow NQ logic uniformly", so every instrument uses the identical code
path; only the instrument's candle dir / box CSV / output token differ (see instruments.py).
With instrument NQ this reproduces the committed NQ_SIGNALS_DELIVERY byte-for-byte (AS.4 gate).

Per (instrument, timeframe, preset) it writes the same 5 artifacts the project defines, into a
technical tree `<out_root>/<token>/<TF>/...`; package_delivery.py then lays them into the
logical <token>_SIGNALS_DELIVERY/ bundle.

Usage:
    python3 subprojects/all-stocks-signals/generate_signals.py --instruments NQ
    python3 subprojects/all-stocks-signals/generate_signals.py            # all 6
    python3 subprojects/all-stocks-signals/generate_signals.py --instruments ES --timeframes 4h 1h
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from typing import List

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_SIGNALS_ROOT = os.path.abspath(os.path.join(_HERE, '..', 'signals'))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, _HERE)

from src.data.loader import load_data  # noqa: E402
from instruments import REGISTRY, TOKENS, TIMEFRAMES, PRESETS, Instrument  # noqa: E402


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Import the FROZEN generators by file path — reusing their functions guarantees the
# byte-identical methodology (same roll, same levels, same sort).
g1 = _load_module('stage1_gen', os.path.join(_SIGNALS_ROOT, 'generate_stage1.py'))
g2 = _load_module('stage2_gen',
                  os.path.join(_SIGNALS_ROOT, 'stage1_0_reverse_signals', 'generate_stage2.py'))


def load_boxes(box_csv: str) -> pd.DataFrame:
    box_df = pd.read_csv(box_csv)
    box_df['Date'] = pd.to_datetime(box_df['Date']).dt.normalize()
    return box_df.set_index('Date', drop=False)


def stage1_for_preset(candles_csv: str, box_df: pd.DataFrame, preset: str) -> pd.DataFrame:
    """Stage 1 for one preset — mirrors generate_full_candles.stage1_for_preset exactly:
    year-filter the candle stream, then the frozen _emit_rows + the frozen sort."""
    candles = load_data(candles_csv)
    if preset != 'full':
        candles = candles[candles['Date'].dt.year == int(preset)].reset_index(drop=True)
    rows = list(g1._emit_rows(candles, box_df))
    return pd.DataFrame(rows, columns=g1._OUT_COLS).sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False], kind='mergesort', na_position='last',
    ).reset_index(drop=True)


def write_reverse(rev: pd.DataFrame, tf_dir: str, token: str, tf: str, preset: str) -> None:
    rev.to_csv(os.path.join(tf_dir, f'reverse_signals_{token}_{tf}_{preset}.csv'), index=False)
    by_dir = os.path.join(tf_dir, 'by_direction')
    os.makedirs(by_dir, exist_ok=True)
    rev[rev['first_signal'] == 'long'].reset_index(drop=True).to_csv(
        os.path.join(by_dir, f'long_to_short_{token}_{tf}_{preset}.csv'), index=False)
    rev[rev['first_signal'] == 'short'].reset_index(drop=True).to_csv(
        os.path.join(by_dir, f'short_to_long_{token}_{tf}_{preset}.csv'), index=False)


def run_instrument(inst: Instrument, timeframes: List[str], presets: List[str],
                   out_root: str) -> List[dict]:
    box_df = load_boxes(inst.box_csv)
    summary = []
    for tf in timeframes:
        candles_csv = inst.candle_csv(tf)
        if not os.path.exists(candles_csv):
            print(f"  SKIP {inst.token} {tf}: candle CSV not found ({candles_csv})", file=sys.stderr)
            continue
        tf_dir = os.path.join(out_root, inst.token, tf)
        nh_dir = os.path.join(tf_dir, 'no_holds')
        os.makedirs(nh_dir, exist_ok=True)
        for preset in presets:
            s1 = stage1_for_preset(candles_csv, box_df, preset)
            s1.to_csv(os.path.join(tf_dir, f'signals_{inst.token}_{tf}_{preset}.csv'), index=False)
            nh = s1[s1['signal'].isin(['long', 'short'])].reset_index(drop=True)
            nh.to_csv(os.path.join(nh_dir, f'signals_{inst.token}_{tf}_{preset}_no_holds.csv'),
                      index=False)
            rev = g2.generate(s1)
            write_reverse(rev, tf_dir, inst.token, tf, preset)

            dist = s1['signal'].value_counts().to_dict()
            row = dict(instrument=inst.token, timeframe=f'{inst.token}_{tf}', preset=preset,
                       signal_rows=len(s1), long=int(dist.get('long', 0)),
                       short=int(dist.get('short', 0)), hold=int(dist.get('hold', 0)),
                       no_hold_rows=len(nh), reverse_windows=len(rev))
            summary.append(row)
            print(f"  {inst.token:9s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
                  f"L/S/H={row['long']}/{row['short']}/{row['hold']}  "
                  f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description='All-stocks signal + reverse-signal generator')
    ap.add_argument('--instruments', nargs='+', default=TOKENS, choices=TOKENS)
    ap.add_argument('--timeframes', nargs='+', default=TIMEFRAMES, choices=TIMEFRAMES)
    ap.add_argument('--presets', nargs='+', default=PRESETS, choices=PRESETS)
    ap.add_argument('--out-root', default=os.path.join(_HERE, 'output'))
    args = ap.parse_args()

    os.makedirs(args.out_root, exist_ok=True)
    print(f"out root: {args.out_root}\n")
    all_summary: List[dict] = []
    for tok in args.instruments:
        inst = REGISTRY[tok]
        print(f"[{tok}]  boxes={inst.box_csv}")
        inst_summary = run_instrument(inst, args.timeframes, args.presets, args.out_root)
        all_summary += inst_summary
        if inst_summary:
            pd.DataFrame(inst_summary).to_csv(
                os.path.join(args.out_root, inst.token, 'SUMMARY.csv'), index=False)

    if all_summary:
        pd.DataFrame(all_summary).to_csv(os.path.join(args.out_root, 'SUMMARY_ALL.csv'), index=False)
        print(f"\nwrote combined summary -> {os.path.join(args.out_root, 'SUMMARY_ALL.csv')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
