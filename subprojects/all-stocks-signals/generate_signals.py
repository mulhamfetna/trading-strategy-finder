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
import json
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


# decision-bar minutes per timeframe — used to turn box-pause bar counts into wall-clock time.
_TF_MIN = {'1m': 1, '2m': 2, '5m': 5, '15m': 15, '1h': 60, '2h': 120, '4h': 240}


def holds_dropped_col(s1: pd.DataFrame) -> List[int]:
    """For each kept long/short row (in 1_all_signals order), the count of consecutive 'hold'
    rows immediately preceding it — i.e. how many holds were DROPPED before this signal. Aligns
    1:1 with the no_holds frame (one value appended per long/short row)."""
    out: List[int] = []
    run = 0
    for sig in s1['signal'].to_numpy():
        if sig in ('long', 'short'):
            out.append(run); run = 0
        else:
            run += 1
    return out


def longest_hold_run(s1: pd.DataFrame) -> int:
    """Longest consecutive run of 'hold' rows in 1_all_signals (incl. a trailing run with no
    signal after it) — the longest box-only pause (no long/short produced)."""
    best = run = 0
    for sig in s1['signal'].to_numpy():
        if sig in ('long', 'short'):
            run = 0
        else:
            run += 1
            if run > best:
                best = run
    return best


def _bars_time(bars: int, tf: str) -> dict:
    mins = bars * _TF_MIN.get(tf, 0)
    return {'bars': int(bars), 'minutes': int(mins), 'hours': round(mins / 60.0, 2),
            'days': round(mins / 1440.0, 2)}


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
    pause = []        # per (tf, preset) box-pause sidecar entries
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
            # holds_dropped: how many consecutive 'hold' rows were removed right before each signal
            # (the box-silence run that preceded it). Aligns 1:1 with the no_holds rows.
            nh['holds_dropped'] = holds_dropped_col(s1)
            nh.to_csv(os.path.join(nh_dir, f'signals_{inst.token}_{tf}_{preset}_no_holds.csv'),
                      index=False)
            rev = g2.generate(s1)
            write_reverse(rev, tf_dir, inst.token, tf, preset)

            # box-pause sidecar: longest box-only pause (max hold run in 1_all_signals) and the
            # longest reverse-window pause (max holds_between in 3_reverse_signals).
            box_pause = longest_hold_run(s1)
            rev_pause = int(rev['holds_between'].max()) if len(rev) and 'holds_between' in rev else 0
            pause.append(dict(instrument=inst.token, tf=tf, preset=preset,
                              holds_dropped_total=int(nh['holds_dropped'].sum()),
                              longest_box_pause=_bars_time(box_pause, tf),
                              reverse={'longest_pause': _bars_time(rev_pause, tf)}))

            dist = s1['signal'].value_counts().to_dict()
            row = dict(instrument=inst.token, timeframe=f'{inst.token}_{tf}', preset=preset,
                       signal_rows=len(s1), long=int(dist.get('long', 0)),
                       short=int(dist.get('short', 0)), hold=int(dist.get('hold', 0)),
                       no_hold_rows=len(nh), reverse_windows=len(rev),
                       holds_dropped_total=int(nh['holds_dropped'].sum()),
                       longest_box_pause_bars=box_pause, reverse_longest_pause_bars=rev_pause)
            summary.append(row)
            print(f"  {inst.token:9s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
                  f"L/S/H={row['long']}/{row['short']}/{row['hold']}  "
                  f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    if pause:
        _write_pause_summary(inst.token, pause, os.path.join(out_root, inst.token))
    return summary


def _write_pause_summary(token: str, pause: List[dict], dst_dir: str) -> None:
    """Write the per-instrument box-pause sidecar (PAUSE_SUMMARY.json + readable .md)."""
    os.makedirs(dst_dir, exist_ok=True)
    with open(os.path.join(dst_dir, 'PAUSE_SUMMARY.json'), 'w') as f:
        json.dump({'instrument': token, 'cells': pause}, f, indent=2)
    lines = [f'# {token} — box-pause summary', '',
             'Longest **box-only** pause per (timeframe, preset): the max consecutive run of '
             '`hold` rows in `1_all_signals` (no `long`/`short` produced), plus the longest '
             'reverse-window pause (`holds_between`). `holds_dropped_total` = total `hold` rows '
             'removed to build `2_holds_dropped`.', '',
             '| TF | preset | holds dropped | longest box pause | reverse longest pause |',
             '|---|---|---|---|---|']
    for c in pause:
        bp, rp = c['longest_box_pause'], c['reverse']['longest_pause']
        lines.append(f"| {c['tf']} | {c['preset']} | {c['holds_dropped_total']:,} | "
                     f"{bp['bars']} bars · {bp['days']}d | {rp['bars']} bars · {rp['days']}d |")
    with open(os.path.join(dst_dir, 'PAUSE_SUMMARY.md'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


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
