"""ISOLATED per-drop signal generation (Stage 1 + Stage 2) on a −1 business-day SHIFTED box.

Generic version of isolated_nq2024_signals.py: works on ANY self-contained NQ data drop that
follows the layout  <drop>/<boxs>/<sub>/NQ_full_data.csv  +  <drop>/<candles>/<sub>/<prefix>_<TF>.csv.
Pass the paths on the CLI; nothing is hardcoded to one drop.

>>> STRICTLY ISOLATED <<<
NEVER touches the committed NQ/ES/ETF bundles or the registry (instruments.py). The ONLY shared
code reused is the FROZEN Stage 1 / Stage 2 rule engine (imported read-only by file path), so the
signal methodology is byte-identical to the approved pipeline.

Two phases (run separately for staged reporting, or together):
  --shift-only   : load the RAW box, shift Date back ONE BUSINESS DAY (Mon→Fri · Tue→Mon ·
                   Wed→Tue · Thu→Wed · Fri→Thu; weekends the only holidays), assert clean
                   (no weekend / no collision / all backward — NO silent fallback), write
                   shifted_boxes/<token>_full_data_shifted.csv. Idempotent (reads raw each time).
  (default)      : shift (as above) THEN run Stage 1 + Stage 2 for every TF at the given preset,
                   validate (5 invariants), and package <token>_SIGNALS_DELIVERY/ (+ .zip).

Example (2026 last-20-days drop):
  python3 subprojects/all-stocks-signals/isolated_drop_signals.py \
      --token NQ2026L20 --preset 2026 \
      --box 2026_last_20_days_data/NQ-2026-last-20-days-boxs/NQ-5-6-2026/NQ_full_data.csv \
      --candle-dir 2026_last_20_days_data/NQ-2026-last-20-days-candles/NQ-5-6-2026_Continuous_Data \
      --prefix NQ-5-6-2026
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

TIMEFRAMES = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']
_SHIFTED_DIR = os.path.join(_HERE, 'shifted_boxes')
_OUT_ROOT = os.path.join(_HERE, 'output_drops')


def _load_frozen(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SIGNALS_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g1 = _load_frozen('drop_stage1', 'generate_stage1.py')
g2 = _load_frozen('drop_stage2', os.path.join('stage1_0_reverse_signals', 'generate_stage2.py'))


def shift_box(token: str, raw_box: str) -> pd.DataFrame:
    """Load the raw box, shift Date back 1 business day, assert clean, save + return it."""
    box = pd.read_csv(raw_box)
    old = pd.to_datetime(box['Date']).dt.normalize()
    new = old - pd.offsets.BDay(1)
    assert new.dt.dayofweek.max() <= 4, "shift produced a weekend date"
    assert not new.duplicated().any(), "shift produced duplicate dates (collision)"
    assert (new < old).all(), "some dates not moved backward"
    box = box.copy()
    box['Date'] = new
    os.makedirs(_SHIFTED_DIR, exist_ok=True)
    out = os.path.join(_SHIFTED_DIR, f'{token}_full_data_shifted.csv')
    box.to_csv(out, index=False)
    print(f"  [shift] {token}: {len(box)} box rows  −1 BDay")
    print(f"          before {old.min().date()} .. {old.max().date()}  ->  "
          f"after {new.min().date()} .. {new.max().date()}")
    print(f"          saved -> {os.path.relpath(out, _REPO_ROOT)}")
    return box.set_index('Date', drop=False)


def stage1_for_preset(candles_csv: str, box_idx: pd.DataFrame, preset: str) -> pd.DataFrame:
    candles = load_data(candles_csv)
    if preset != 'full':
        candles = candles[candles['Date'].dt.year == int(preset)].reset_index(drop=True)
    rows = list(g1._emit_rows(candles, box_idx))
    return pd.DataFrame(rows, columns=g1._OUT_COLS).sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False], kind='mergesort', na_position='last',
    ).reset_index(drop=True)


def generate(token, preset, candle_dir, prefix, box_idx, timeframes) -> list:
    summary = []
    for tf in timeframes:
        candles_csv = os.path.join(candle_dir, f'{prefix}_{tf}.csv')
        if not os.path.exists(candles_csv):
            print(f"  SKIP {tf}: missing {candles_csv}", file=sys.stderr); continue
        tf_dir = os.path.join(_OUT_ROOT, token, tf)
        nh_dir = os.path.join(tf_dir, 'no_holds'); bd_dir = os.path.join(tf_dir, 'by_direction')
        os.makedirs(nh_dir, exist_ok=True); os.makedirs(bd_dir, exist_ok=True)
        s1 = stage1_for_preset(candles_csv, box_idx, preset)
        s1.to_csv(os.path.join(tf_dir, f'signals_{token}_{tf}_{preset}.csv'), index=False)
        nh = s1[s1['signal'].isin(['long', 'short'])].reset_index(drop=True)
        nh.to_csv(os.path.join(nh_dir, f'signals_{token}_{tf}_{preset}_no_holds.csv'), index=False)
        rev = g2.generate(s1)
        rev.to_csv(os.path.join(tf_dir, f'reverse_signals_{token}_{tf}_{preset}.csv'), index=False)
        rev[rev['first_signal'] == 'long'].reset_index(drop=True).to_csv(
            os.path.join(bd_dir, f'long_to_short_{token}_{tf}_{preset}.csv'), index=False)
        rev[rev['first_signal'] == 'short'].reset_index(drop=True).to_csv(
            os.path.join(bd_dir, f'short_to_long_{token}_{tf}_{preset}.csv'), index=False)
        d = s1['signal'].value_counts().to_dict()
        summary.append(dict(instrument=token, timeframe=f'{token}_{tf}', preset=preset,
                            signal_rows=len(s1), long=int(d.get('long', 0)),
                            short=int(d.get('short', 0)), hold=int(d.get('hold', 0)),
                            no_hold_rows=len(nh), reverse_windows=len(rev)))
        print(f"  {token} {tf:4s} {preset}: signals={len(s1):>8,}  "
              f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
              f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    pd.DataFrame(summary).to_csv(os.path.join(_OUT_ROOT, token, 'SUMMARY.csv'), index=False)
    return summary


def validate(token, preset, box_idx, timeframes) -> list:
    box_dates = set(box_idx['Date'].dt.date.astype(str)); errs = []
    for tf in timeframes:
        base = os.path.join(_OUT_ROOT, token, tf)
        if not os.path.isdir(base):
            continue
        a = pd.read_csv(os.path.join(base, f'signals_{token}_{tf}_{preset}.csv'))
        nh = pd.read_csv(os.path.join(base, 'no_holds', f'signals_{token}_{tf}_{preset}_no_holds.csv'))
        rev = pd.read_csv(os.path.join(base, f'reverse_signals_{token}_{tf}_{preset}.csv'))
        l2s = pd.read_csv(os.path.join(base, 'by_direction', f'long_to_short_{token}_{tf}_{preset}.csv'))
        s2l = pd.read_csv(os.path.join(base, 'by_direction', f'short_to_long_{token}_{tf}_{preset}.csv'))
        vc = a['signal'].value_counts(); tag = f"{token} {tf} {preset}"
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


def package(token, preset, timeframes) -> None:
    src = os.path.join(_OUT_ROOT, token)
    dst = os.path.join(_REPO_ROOT, f'{token}_SIGNALS_DELIVERY')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst); n = 0
    for tf in timeframes:
        tf_dir = os.path.join(src, tf)
        if not os.path.isdir(tf_dir):
            continue
        name = f'{token}_{tf}_{preset}.csv'
        for s, d in [
            (f'signals_{token}_{tf}_{preset}.csv', os.path.join('1_all_signals', name)),
            (os.path.join('no_holds', f'signals_{token}_{tf}_{preset}_no_holds.csv'), os.path.join('2_holds_dropped', name)),
            (f'reverse_signals_{token}_{tf}_{preset}.csv', os.path.join('3_reverse_signals', name)),
            (os.path.join('by_direction', f'long_to_short_{token}_{tf}_{preset}.csv'), os.path.join('4_reverse_by_direction', 'long_to_short', name)),
            (os.path.join('by_direction', f'short_to_long_{token}_{tf}_{preset}.csv'), os.path.join('4_reverse_by_direction', 'short_to_long', name)),
        ]:
            sp = os.path.join(tf_dir, s); dp = os.path.join(dst, d)
            os.makedirs(os.path.dirname(dp), exist_ok=True); shutil.copy2(sp, dp); n += 1
    shutil.copy2(os.path.join(src, 'SUMMARY.csv'), os.path.join(dst, 'SUMMARY.csv'))
    with open(os.path.join(dst, 'README.md'), 'w') as f:
        tfs = ' '.join(f'{token}_{tf}' for tf in timeframes)
        f.write(f"""# {token} Signals — Delivery Bundle (preset {preset}, BOX-SHIFTED −1 business day)

Signals generated with the box `Date` shifted **back one business day** (weekends skipped):
Mon→Fri, Tue→Mon, Wed→Tue, Thu→Wed, Fri→Thu. Produced by the ISOLATED script
`subprojects/all-stocks-signals/isolated_drop_signals.py`. Committed NQ/ES/ETF bundles unaffected.

Timeframes: `{tfs}` · Preset: `{preset}`.
Folders/schemas identical to the standard delivery: 1_all_signals (10 cols), 2_holds_dropped (10),
3_reverse_signals (21), 4_reverse_by_direction/{{long_to_short,short_to_long}}, SUMMARY.csv.
Shifted box: `shifted_boxes/{token}_full_data_shifted.csv`. Stage 1/2 engine is the frozen one.
""")
    archive = shutil.make_archive(dst, 'zip', root_dir=_REPO_ROOT, base_dir=f'{token}_SIGNALS_DELIVERY')
    print(f"  packaged {n} CSVs -> {os.path.basename(dst)}  + {os.path.basename(archive)}")


def main() -> int:
    ap = argparse.ArgumentParser(description='ISOLATED per-drop signal generation (shifted box)')
    ap.add_argument('--token', required=True, help='output token / delivery name')
    ap.add_argument('--preset', required=True, help="'full' or a year (year-filters candles)")
    ap.add_argument('--box', required=True, help='raw box CSV (NQ_full_data.csv)')
    ap.add_argument('--candle-dir', required=True, help='dir of <prefix>_<TF>.csv')
    ap.add_argument('--prefix', required=True, help='candle filename prefix')
    ap.add_argument('--timeframes', nargs='+', default=TIMEFRAMES, choices=TIMEFRAMES)
    ap.add_argument('--shift-only', action='store_true', help='phase 1: shift the box, then stop')
    ap.add_argument('--no-package', action='store_true')
    args = ap.parse_args()

    print(f"ISOLATED drop signals — token={args.token} preset={args.preset} "
          f"prefix={args.prefix} TFs={','.join(args.timeframes)}")
    box_idx = shift_box(args.token, os.path.join(_REPO_ROOT, args.box)
                        if not os.path.isabs(args.box) else args.box)
    if args.shift_only:
        print("PASS: shift-only complete"); return 0
    cdir = os.path.join(_REPO_ROOT, args.candle_dir) if not os.path.isabs(args.candle_dir) else args.candle_dir
    generate(args.token, args.preset, cdir, args.prefix, box_idx, args.timeframes)
    errs = validate(args.token, args.preset, box_idx, args.timeframes)
    if errs:
        print(f"  VALIDATION FAILED ({len(errs)}):")
        for e in errs:
            print("     ", e)
    else:
        print(f"  validation OK — {len(args.timeframes)} cells × 5 invariants")
    if not errs and not args.no_package:
        package(args.token, args.preset, args.timeframes)
    print(f"\n{'PASS' if not errs else 'FAIL'}: {len(errs)} validation errors")
    return 1 if errs else 0


if __name__ == '__main__':
    raise SystemExit(main())
