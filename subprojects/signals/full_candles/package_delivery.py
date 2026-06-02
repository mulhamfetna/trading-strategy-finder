"""Package the full-candles outputs into a delivery-ready, LOGICALLY-organised clone.

The generated tree (`full_candles/<TF>/...`) is organised *technically* — grouped by
the source data file (timeframe), then split into signals / no_holds / reverse /
by_direction. That layout mirrors how the pipeline runs, not how a recipient reads it.

This script builds a totally isolated CLONE in the project ROOT, organised *logically*
— grouped by what each file IS (the product), with timeframe + preset encoded in the
filename. Nothing is moved; the technical tree is left untouched.

Logical layout produced:

    NQ_SIGNALS_DELIVERY/
        README.md
        SUMMARY.csv
        1_all_signals/        <TF>_<preset>.csv   (every candle×box, incl. hold)
        2_holds_dropped/      <TF>_<preset>.csv   (long/short only)
        3_reverse_signals/    <TF>_<preset>.csv   (reverse windows: max-high/min-low + tp/sl)
        4_reverse_by_direction/
            long_to_short/    <TF>_<preset>.csv
            short_to_long/    <TF>_<preset>.csv

A zip of the whole folder is written next to it for one-file handoff.

Usage:
    python3 subprojects/signals/full_candles/package_delivery.py
"""
from __future__ import annotations

import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))
_SRC = _HERE                                   # full_candles/ (technical tree)
_DELIVERY_NAME = 'NQ_SIGNALS_DELIVERY'
_DST = os.path.join(_REPO_ROOT, _DELIVERY_NAME)

_TIMEFRAMES = ['NQ_1m', 'NQ_2m', 'NQ_5m', 'NQ_15m', 'NQ_1h', 'NQ_2h', 'NQ_4h']
_PRESETS = ['full', '2025', '2026']


def _copy(src: str, dst: str) -> bool:
    if not os.path.exists(src):
        print(f"  MISSING {src}", file=sys.stderr)
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def build() -> int:
    if os.path.exists(_DST):
        shutil.rmtree(_DST)
    os.makedirs(_DST)

    n = 0
    for tf in _TIMEFRAMES:
        tf_dir = os.path.join(_SRC, tf)
        for preset in _PRESETS:
            name = f'{tf}_{preset}.csv'
            # 1. all signals
            n += _copy(os.path.join(tf_dir, f'signals_{tf}_{preset}.csv'),
                       os.path.join(_DST, '1_all_signals', name))
            # 2. holds dropped
            n += _copy(os.path.join(tf_dir, 'no_holds', f'signals_{tf}_{preset}_no_holds.csv'),
                       os.path.join(_DST, '2_holds_dropped', name))
            # 3. reverse signals
            n += _copy(os.path.join(tf_dir, f'reverse_signals_{tf}_{preset}.csv'),
                       os.path.join(_DST, '3_reverse_signals', name))
            # 4. reverse by direction
            n += _copy(os.path.join(tf_dir, 'by_direction', f'long_to_short_{tf}_{preset}.csv'),
                       os.path.join(_DST, '4_reverse_by_direction', 'long_to_short', name))
            n += _copy(os.path.join(tf_dir, 'by_direction', f'short_to_long_{tf}_{preset}.csv'),
                       os.path.join(_DST, '4_reverse_by_direction', 'short_to_long', name))

    # carry the summary + a delivery README
    _copy(os.path.join(_SRC, 'SUMMARY.csv'), os.path.join(_DST, 'SUMMARY.csv'))
    _write_readme()

    print(f"copied {n} CSVs into {_DST}")

    # one-file handoff: zip the whole delivery folder
    archive = shutil.make_archive(_DST, 'zip', root_dir=_REPO_ROOT, base_dir=_DELIVERY_NAME)
    print(f"wrote archive -> {archive}")
    return 0


def _write_readme() -> None:
    readme = f"""# NQ Signals — Delivery Bundle

Logically-organised clone of the full-candles signal outputs. Grouped by **what each
file is** (the product), with **timeframe** and **preset** encoded in the filename —
`<TIMEFRAME>_<PRESET>.csv`, e.g. `NQ_15m_2025.csv`.

Timeframes: `NQ_1m NQ_2m NQ_5m NQ_15m NQ_1h NQ_2h NQ_4h`
Presets:    `full` (2025-01-01 → 2026-05-19), `2025`, `2026`

## Folders

| Folder | Contents |
|---|---|
| `1_all_signals/`          | Every (candle × box) pair labelled `long`/`short`/`hold`. The complete signal stream. |
| `2_holds_dropped/`        | The same rows with all `hold`s removed — only `long`/`short` signals. |
| `3_reverse_signals/`      | Reverse windows (long→…→short or short→…→long). Each row carries `window_high` (**max high**), `window_low` (**min low**), direction-aware `tp`/`sl`, and `holds_between`. |
| `4_reverse_by_direction/long_to_short/` | Reverse windows that opened `long`. |
| `4_reverse_by_direction/short_to_long/` | Reverse windows that opened `short`. |
| `SUMMARY.csv`             | Row/window counts for every (timeframe, preset). |

## Column schemas

**`1_all_signals` & `2_holds_dropped`** (10 cols):
`datetime, open, high, low, close, volume, signal, box_id, box_upper, box_lower`

**`3_reverse_signals` & `4_reverse_by_direction`** (21 cols):
`first_datetime, first_open, first_high, first_low, first_close, first_signal,
first_box_id, first_box_type, last_datetime, last_open, last_high, last_low,
last_close, last_signal, last_box_id, last_box_type, window_high, window_low,
tp, sl, holds_between`

## Provenance

Generated by the frozen Stage 1 + Stage 2 rules (identical methodology to the original
4h pipeline — the 4h outputs here are byte-identical to the committed originals). Full
data-flow documentation: `subprojects/signals/full_candles/docs/PIPELINE.md`.
"""
    with open(os.path.join(_DST, 'README.md'), 'w') as f:
        f.write(readme)


if __name__ == '__main__':
    raise SystemExit(build())
