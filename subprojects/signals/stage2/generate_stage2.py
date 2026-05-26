"""Stage 2 — reverse-signal window extractor.

Reads a Stage 1 CSV (one row per (candle, level pair)), collapses per-candle
state by the rule:

    candle_state =
        'long'  if any row for the candle has signal == 'long'
        'short' if any row for the candle has signal == 'short'
        'hold'  otherwise

then linearly scans the candle stream for reverse signals (long → ... → short
or short → ... → long, holds permitted between). For each closed window emits
one row with anchor/reverse candle data (incl. matching box_ids as semicolon-
joined strings), window high/low, direction-aware tp/sl, and the count of
hold candles strictly between the endpoints.

The tp/sl formula is keyed to the **anchor candle's color**:

    green anchor (close > open):  tp = window_high − first_close
                                  sl = first_close − window_low
    red anchor   (close < open):  tp = first_close − window_low
                                  sl = window_high − first_close

A doji anchor (close == open) cannot occur — Stage 1's color rule makes any
doji candle a 'hold', so it never becomes an anchor.

See subproject_signals_stage2_round3_FINAL.md for the locked spec.

Usage:
    python3 subprojects/signals/stage2/generate_stage2.py --preset full
    python3 subprojects/signals/stage2/generate_stage2.py --preset 2025 --out /tmp/x.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator, List

import pandas as pd

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

_OUT_COLS = [
    'first_datetime', 'first_open', 'first_high', 'first_low', 'first_close',
    'first_signal', 'first_box_id', 'first_box_type',
    'last_datetime', 'last_open', 'last_high', 'last_low', 'last_close',
    'last_signal', 'last_box_id', 'last_box_type',
    'window_high', 'window_low',
    'tp', 'sl',
    'holds_between',
]


def _box_id_to_type(box_id_str: str) -> str:
    """Strip the date suffix from each ';'-separated box_id component, keeping
    the first 4 characters as the box "type". Order, count, and duplicates
    are preserved (no dedup) — this is a per-component slice of the parent
    box_id column.

    Examples:
        'M-IH_2025-01-02'                                     -> 'M-IH'
        'M-IH_2025-01-02;W-RL_2025-01-02'                     -> 'M-IH;W-RL'
        'M-RH_2026-05-19;W-IL_2026-05-19;W-RL_2026-05-19'     -> 'M-RH;W-IL;W-RL'
        ''                                                     -> ''
    """
    if not box_id_str:
        return ''
    return ';'.join(part[:4] for part in box_id_str.split(';'))


def _collapse_to_candle_stream(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse Stage 1's per-(candle, level-pair) rows to one row per candle.

    Returned columns: datetime, open, high, low, close, candle_state, state_box_ids.

    candle_state is one of 'long' / 'short' / 'hold'. A candle is 'long' if any
    of its Stage 1 rows is 'long'; same for 'short'. Otherwise 'hold'. The
    color rule guarantees long and short cannot both appear for the same candle.

    state_box_ids is a semicolon-joined string of all box_ids whose Stage 1
    signal matches the candle's state, sorted alphabetically. Empty string for
    hold candles. Used to populate first_box_id / last_box_id in the output.
    """
    cols = ['datetime', 'open', 'high', 'low', 'close', 'candle_state', 'state_box_ids']
    if signals_df.empty:
        return pd.DataFrame(columns=cols)

    def _aggregate(group: pd.DataFrame) -> pd.Series:
        sigs = set(group['signal'])
        if 'long' in sigs and 'short' in sigs:
            raise ValueError(
                "Stage 2 invariant violated: candle has both long and short rows. "
                "This contradicts the Stage 1 color rule."
            )
        if 'long' in sigs:
            state = 'long'
        elif 'short' in sigs:
            state = 'short'
        else:
            state = 'hold'

        if state == 'hold':
            box_ids = ''
        else:
            matching = group.loc[group['signal'] == state, 'box_id']
            unique_sorted = sorted({b for b in matching if pd.notna(b)})
            box_ids = ';'.join(unique_sorted)

        first = group.iloc[0]
        return pd.Series({
            'open':          float(first['open']),
            'high':          float(first['high']),
            'low':           float(first['low']),
            'close':         float(first['close']),
            'candle_state':  state,
            'state_box_ids': box_ids,
        })

    grouped = (
        signals_df.groupby('datetime', sort=True, group_keys=False)
        .apply(_aggregate, include_groups=False)
        .reset_index()
    )
    return grouped[cols]


def _scan_windows(candles: pd.DataFrame) -> Iterator[dict]:
    """Yield one dict per closed reverse window over the candle-level stream."""
    if candles.empty:
        return

    rows = candles.reset_index(drop=True)
    n = len(rows)
    i = 0

    # Skip leading holds.
    while i < n and rows.at[i, 'candle_state'] == 'hold':
        i += 1
    if i >= n:
        return

    anchor_idx = i
    i += 1

    while i < n:
        state = rows.at[i, 'candle_state']
        if state == 'hold':
            i += 1
            continue

        anchor_state = rows.at[anchor_idx, 'candle_state']
        if state == anchor_state:
            # Same-state repeat: discard the open window, restart anchor here.
            anchor_idx = i
            i += 1
            continue

        # Opposite state: close window from anchor_idx through i (inclusive).
        window = rows.iloc[anchor_idx : i + 1]
        anchor = window.iloc[0]
        reverse = window.iloc[-1]
        window_high = float(window['high'].max())
        window_low = float(window['low'].min())
        first_open = float(anchor['open'])
        first_close = float(anchor['close'])
        holds_between = int((window['candle_state'].iloc[1:-1] == 'hold').sum()) if len(window) > 2 else 0

        # Direction-aware tp/sl keyed to anchor candle color.
        # The Stage 1 color rule guarantees an anchor is never doji
        # (close == open) — doji candles are always 'hold'.
        if first_close > first_open:
            # green anchor → long state
            tp = window_high - first_close
            sl = first_close - window_low
        else:
            # red anchor → short state (first_close < first_open)
            tp = first_close - window_low
            sl = window_high - first_close

        first_box_id = anchor['state_box_ids']
        last_box_id  = reverse['state_box_ids']

        yield {
            'first_datetime':  anchor['datetime'],
            'first_open':      first_open,
            'first_high':      float(anchor['high']),
            'first_low':       float(anchor['low']),
            'first_close':     first_close,
            'first_signal':    anchor['candle_state'],
            'first_box_id':    first_box_id,
            'first_box_type':  _box_id_to_type(first_box_id),
            'last_datetime':   reverse['datetime'],
            'last_open':       float(reverse['open']),
            'last_high':       float(reverse['high']),
            'last_low':        float(reverse['low']),
            'last_close':      float(reverse['close']),
            'last_signal':     reverse['candle_state'],
            'last_box_id':     last_box_id,
            'last_box_type':   _box_id_to_type(last_box_id),
            'window_high':     window_high,
            'window_low':      window_low,
            'tp':              tp,
            'sl':              sl,
            'holds_between':   holds_between,
        }

        # The reverse candle becomes the next window's anchor.
        anchor_idx = i
        i += 1

    # Loop ended with an open anchor and no reverse → drop silently (E2).


def generate(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Produce the Stage 2 dataframe from a Stage 1 dataframe."""
    candles = _collapse_to_candle_stream(signals_df)
    rows = list(_scan_windows(candles))
    df = pd.DataFrame(rows, columns=_OUT_COLS)
    df = df.sort_values(
        by=['first_datetime'],
        kind='mergesort',
    ).reset_index(drop=True)
    return df


def generate_from_csv(signals_csv: str) -> pd.DataFrame:
    df = pd.read_csv(signals_csv)
    return generate(df)


def write_outputs(df: pd.DataFrame, stage2_dir: str, preset: str) -> List[str]:
    """Write the unified file + the two direction-split files for one preset.

    Returns the list of paths written.
    """
    paths = []
    unified = os.path.join(stage2_dir, f'reverse_signals_{preset}.csv')
    df.to_csv(unified, index=False)
    paths.append(unified)

    by_dir = os.path.join(stage2_dir, 'by_direction')
    os.makedirs(by_dir, exist_ok=True)
    l2s = df[df['first_signal'] == 'long'].reset_index(drop=True)
    s2l = df[df['first_signal'] == 'short'].reset_index(drop=True)
    l2s_path = os.path.join(by_dir, f'long_to_short_{preset}.csv')
    s2l_path = os.path.join(by_dir, f'short_to_long_{preset}.csv')
    l2s.to_csv(l2s_path, index=False)
    s2l.to_csv(s2l_path, index=False)
    paths.append(l2s_path)
    paths.append(s2l_path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description='Stage 2 reverse-signal extractor')
    parser.add_argument('--preset', choices=['full', '2025', '2026'], default='full')
    parser.add_argument('--signals-csv', default=None, help='Override Stage 1 CSV path.')
    parser.add_argument('--out-dir', default=None, help='Override stage2 output directory.')
    args = parser.parse_args()

    signals_csv = args.signals_csv or os.path.join(
        _REPO_ROOT, 'subprojects', 'signals', f'signals_{args.preset}.csv'
    )
    if not os.path.exists(signals_csv):
        print(f"ERROR: signals CSV not found: {signals_csv}", file=sys.stderr)
        return 2

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(__file__))
    df = generate_from_csv(signals_csv)
    paths = write_outputs(df, out_dir, args.preset)

    by_dir = df['first_signal'].value_counts().to_dict()
    print(f"wrote {len(df)} reverse windows for preset {args.preset}")
    print(f"  by direction: {by_dir}")
    for p in paths:
        print(f"  -> {p}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
