"""ISOLATED NQ-2024 signal generation (Stage 1 + Stage 2) on the −1 business-day SHIFTED box.

>>> STRICTLY ISOLATED <<<
Self-contained on purpose. It targets ONLY the 2024 NQ data drop (separate from the registry's
2025/2026 NQ candles) and NEVER touches the committed NQ/ES/ETF bundles. It does NOT import the
shared registry (instruments.py); the 2024 candle dir + raw box path are hardcoded below. The ONLY
shared code reused is the FROZEN Stage 1 / Stage 2 rule engine (imported read-only by file path),
so the signal methodology is byte-identical to the approved pipeline.

What it does:
  1. Load the RAW 2024 box (2024_data/NQ2024-Boxs/NQ2024/NQ_full_data.csv) — pristine schema.
  2. Shift every box Date BACK ONE BUSINESS DAY (the frozen WS-AS.8 map; weekends are the only
     holidays): Mon→Fri · Tue→Mon · Wed→Tue · Thu→Wed · Fri→Thu. Loud asserts (no weekend,
     no collision, all backward) — NO silent fallback. Saved to shifted_boxes/ for audit.
  3. For each of 7 TFs run frozen Stage 1 (_emit_rows + frozen sort) and Stage 2 (generate) against
     the SHIFTED box, preset "2024" (year-filter == 2024), writing the standard 5 artifacts into an
     isolated tree output_nq2024/NQ2024/<TF>/..., validate (5 invariants), and package
     NQ2024_SIGNALS_DELIVERY/ (+ .zip). Folders/schemas identical to any NQ/ES bundle.

Usage:
    python3 subprojects/all-stocks-signals/isolated_nq2024_signals.py
    python3 subprojects/all-stocks-signals/isolated_nq2024_signals.py --timeframes 4h 1h
    python3 subprojects/all-stocks-signals/isolated_nq2024_signals.py --no-package
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_SIGNALS_ROOT = os.path.abspath(os.path.join(_HERE, '..', 'signals'))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _REPO_ROOT)
from src.data.loader import load_data  # noqa: E402

TOKEN = 'NQ2024'
PRESET = '2024'
TIMEFRAMES = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']

_CANDLE_DIR = os.path.join(_REPO_ROOT, '2024_data', 'NQ2024_Candles', 'NQ2024_Continuous_Data')
_CANDLE_PREFIX = 'NQ2024'
_RAW_BOX = os.path.join(_REPO_ROOT, '2024_data', 'NQ2024-Boxs', 'NQ2024', 'NQ_full_data.csv')

_SHIFTED_DIR = os.path.join(_HERE, 'shifted_boxes')
_OUT_ROOT = os.path.join(_HERE, 'output_nq2024')


def _load_frozen(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SIGNALS_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g1 = _load_frozen('nq2024_stage1', 'generate_stage1.py')
g2 = _load_frozen('nq2024_stage2', os.path.join('stage1_0_reverse_signals', 'generate_stage2.py'))


def shift_box() -> pd.DataFrame:
    """Load the raw 2024 box, shift Date back 1 business day, assert clean, save + return it."""
    box = pd.read_csv(_RAW_BOX)
    old = pd.to_datetime(box['Date']).dt.normalize()
    new = old - pd.offsets.BDay(1)
    assert new.dt.dayofweek.max() <= 4, "shift produced a weekend date"
    assert not new.duplicated().any(), "shift produced duplicate dates (collision)"
    assert (new < old).all(), "some dates not moved backward"
    box = box.copy()
    box['Date'] = new
    os.makedirs(_SHIFTED_DIR, exist_ok=True)
    out = os.path.join(_SHIFTED_DIR, f'{TOKEN}_full_data_shifted.csv')
    box.to_csv(out, index=False)
    print(f"  shifted box -> {os.path.relpath(out, _REPO_ROOT)}  "
          f"({new.min().date()} .. {new.max().date()}, {len(box)} rows)")
    return box.set_index('Date', drop=False)


def stage1_for_preset(candles_csv: str, box_idx: pd.DataFrame) -> pd.DataFrame:
    candles = load_data(candles_csv)
    candles = candles[candles['Date'].dt.year == int(PRESET)].reset_index(drop=True)
    rows = list(g1._emit_rows(candles, box_idx))
    return pd.DataFrame(rows, columns=g1._OUT_COLS).sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False], kind='mergesort', na_position='last',
    ).reset_index(drop=True)


def generate(box_idx: pd.DataFrame, timeframes) -> list:
    summary = []
    for tf in timeframes:
        candles_csv = os.path.join(_CANDLE_DIR, f'{_CANDLE_PREFIX}_{tf}.csv')
        if not os.path.exists(candles_csv):
            print(f"  SKIP {tf}: missing {candles_csv}", file=sys.stderr); continue
        tf_dir = os.path.join(_OUT_ROOT, TOKEN, tf)
        nh_dir = os.path.join(tf_dir, 'no_holds')
        bd_dir = os.path.join(tf_dir, 'by_direction')
        os.makedirs(nh_dir, exist_ok=True); os.makedirs(bd_dir, exist_ok=True)
        s1 = stage1_for_preset(candles_csv, box_idx)
        s1.to_csv(os.path.join(tf_dir, f'signals_{TOKEN}_{tf}_{PRESET}.csv'), index=False)
        nh = s1[s1['signal'].isin(['long', 'short'])].reset_index(drop=True)
        nh.to_csv(os.path.join(nh_dir, f'signals_{TOKEN}_{tf}_{PRESET}_no_holds.csv'), index=False)
        rev = g2.generate(s1)
        rev.to_csv(os.path.join(tf_dir, f'reverse_signals_{TOKEN}_{tf}_{PRESET}.csv'), index=False)
        rev[rev['first_signal'] == 'long'].reset_index(drop=True).to_csv(
            os.path.join(bd_dir, f'long_to_short_{TOKEN}_{tf}_{PRESET}.csv'), index=False)
        rev[rev['first_signal'] == 'short'].reset_index(drop=True).to_csv(
            os.path.join(bd_dir, f'short_to_long_{TOKEN}_{tf}_{PRESET}.csv'), index=False)
        d = s1['signal'].value_counts().to_dict()
        summary.append(dict(instrument=TOKEN, timeframe=f'{TOKEN}_{tf}', preset=PRESET,
                            signal_rows=len(s1), long=int(d.get('long', 0)),
                            short=int(d.get('short', 0)), hold=int(d.get('hold', 0)),
                            no_hold_rows=len(nh), reverse_windows=len(rev)))
        print(f"  {TOKEN} {tf:4s} {PRESET}: signals={len(s1):>8,}  "
              f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
              f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    pd.DataFrame(summary).to_csv(os.path.join(_OUT_ROOT, TOKEN, 'SUMMARY.csv'), index=False)
    return summary


def validate(box_idx: pd.DataFrame, timeframes) -> list:
    box_dates = set(box_idx['Date'].dt.date.astype(str))
    errs = []
    for tf in timeframes:
        base = os.path.join(_OUT_ROOT, TOKEN, tf)
        if not os.path.isdir(base):
            continue
        a = pd.read_csv(os.path.join(base, f'signals_{TOKEN}_{tf}_{PRESET}.csv'))
        nh = pd.read_csv(os.path.join(base, 'no_holds', f'signals_{TOKEN}_{tf}_{PRESET}_no_holds.csv'))
        rev = pd.read_csv(os.path.join(base, f'reverse_signals_{TOKEN}_{tf}_{PRESET}.csv'))
        l2s = pd.read_csv(os.path.join(base, 'by_direction', f'long_to_short_{TOKEN}_{tf}_{PRESET}.csv'))
        s2l = pd.read_csv(os.path.join(base, 'by_direction', f'short_to_long_{TOKEN}_{tf}_{PRESET}.csv'))
        vc = a['signal'].value_counts(); tag = f"{TOKEN} {tf} {PRESET}"
        if vc.get('long', 0) + vc.get('short', 0) + vc.get('hold', 0) != len(a): errs.append(f"{tag}: counts")
        if len(nh) != vc.get('long', 0) + vc.get('short', 0): errs.append(f"{tag}: no_hold")
        if (nh['signal'] == 'hold').any(): errs.append(f"{tag}: hold in no_holds")
        if len(l2s) + len(s2l) != len(rev): errs.append(f"{tag}: partition")
        ids = a['box_id'].dropna().astype(str)
        if len(ids):
            bad = set(ids.str.rsplit('_', n=1).str[-1].unique()) - box_dates
            if bad: errs.append(f"{tag}: box_id outside SHIFTED index e.g. {list(bad)[:3]}")
        if len(rev) > len(nh): errs.append(f"{tag}: reverse>no_hold")
    return errs


def package(timeframes) -> None:
    src = os.path.join(_OUT_ROOT, TOKEN)
    dst = os.path.join(_REPO_ROOT, f'{TOKEN}_SIGNALS_DELIVERY')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    n = 0
    for tf in timeframes:
        tf_dir = os.path.join(src, tf)
        if not os.path.isdir(tf_dir):
            continue
        name = f'{TOKEN}_{tf}_{PRESET}.csv'
        for s, d in [
            (f'signals_{TOKEN}_{tf}_{PRESET}.csv', os.path.join('1_all_signals', name)),
            (os.path.join('no_holds', f'signals_{TOKEN}_{tf}_{PRESET}_no_holds.csv'), os.path.join('2_holds_dropped', name)),
            (f'reverse_signals_{TOKEN}_{tf}_{PRESET}.csv', os.path.join('3_reverse_signals', name)),
            (os.path.join('by_direction', f'long_to_short_{TOKEN}_{tf}_{PRESET}.csv'), os.path.join('4_reverse_by_direction', 'long_to_short', name)),
            (os.path.join('by_direction', f'short_to_long_{TOKEN}_{tf}_{PRESET}.csv'), os.path.join('4_reverse_by_direction', 'short_to_long', name)),
        ]:
            sp = os.path.join(tf_dir, s); dp = os.path.join(dst, d)
            os.makedirs(os.path.dirname(dp), exist_ok=True); shutil.copy2(sp, dp); n += 1
    shutil.copy2(os.path.join(src, 'SUMMARY.csv'), os.path.join(dst, 'SUMMARY.csv'))
    with open(os.path.join(dst, 'README.md'), 'w') as f:
        f.write(_readme(timeframes))
    archive = shutil.make_archive(dst, 'zip', root_dir=_REPO_ROOT, base_dir=f'{TOKEN}_SIGNALS_DELIVERY')
    print(f"  packaged {n} CSVs -> {os.path.basename(dst)}  + {os.path.basename(archive)}")


def _readme(timeframes) -> str:
    tfs = ' '.join(f'{TOKEN}_{tf}' for tf in timeframes)
    return f"""# {TOKEN} Signals — Delivery Bundle (2024, BOX-SHIFTED −1 business day)

NQ 2024 signals generated with the box `Date` shifted **back one business day** (weekends
skipped): Monday→Friday, Tuesday→Monday, Wednesday→Tuesday, Thursday→Wednesday, Friday→Thursday.
Produced by the ISOLATED script `subprojects/all-stocks-signals/isolated_nq2024_signals.py`
on the separate 2024 data drop. The committed NQ/ES/ETF bundles are unaffected.

Timeframes: `{tfs}` · Preset: `{PRESET}` (single year).
Folders/schemas identical to the standard delivery (see any `NQ`/`ES` bundle README):
1_all_signals (10 cols), 2_holds_dropped (10), 3_reverse_signals (21),
4_reverse_by_direction/{{long_to_short,short_to_long}}, SUMMARY.csv.

Shifted box used: `shifted_boxes/{TOKEN}_full_data_shifted.csv`
(from raw `2024_data/NQ2024-Boxs/NQ2024/NQ_full_data.csv`).
Stage 1 / Stage 2 rule engine is the frozen one (reused read-only) — only the box dates differ.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description='ISOLATED NQ-2024 signal generation (shifted box)')
    ap.add_argument('--timeframes', nargs='+', default=TIMEFRAMES, choices=TIMEFRAMES)
    ap.add_argument('--no-package', action='store_true', help='generate + validate only (no bundle)')
    args = ap.parse_args()

    print(f"ISOLATED NQ-2024 signals (−1 business-day shifted box) — TFs: {', '.join(args.timeframes)}")
    print("Committed NQ/ES/ETF bundles are NOT touched.\n")
    box_idx = shift_box()
    generate(box_idx, args.timeframes)
    errs = validate(box_idx, args.timeframes)
    if errs:
        print(f"  VALIDATION FAILED ({len(errs)}):")
        for e in errs:
            print("     ", e)
    else:
        print(f"  validation OK — {len(args.timeframes)} cells × 5 invariants")
    if not errs and not args.no_package:
        package(args.timeframes)
    print(f"\n{'PASS' if not errs else 'FAIL'}: {len(errs)} validation errors")
    return 1 if errs else 0


if __name__ == '__main__':
    raise SystemExit(main())
