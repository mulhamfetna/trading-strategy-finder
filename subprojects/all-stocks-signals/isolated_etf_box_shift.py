"""WS-AS.8 — ISOLATED ETF box-shift + re-export (QQQ & SQQQ × RTH & ETH ONLY).

>>> STRICTLY ISOLATED <<<
This script is self-contained on purpose. It NEVER references NQ or ES — only the four
ETF instruments — and it does NOT import the shared driver (generate_signals.py) or the
shared registry (instruments.py); the four ETF paths are hardcoded below. The ONLY shared
code it reuses is the FROZEN Stage 1 / Stage 2 rule engine, imported read-only by file
path, so the signal methodology is identical to the approved pipeline. Nothing here can
alter the NQ/ES outputs.

What it does, per ETF instrument:
  1. Load the instrument's box `_full_data.csv`.
  2. Shift every box `Date` BACK BY ONE BUSINESS DAY (weekends are the only holidays):
         new_Date = old_Date - 1 business day      (pandas BDay)
     which is exactly the requested map:
         Monday -> Friday (prev wk) · Tuesday -> Monday · Wednesday -> Tuesday
         Thursday -> Wednesday · Friday -> Thursday
     Verified on this data: weekday-only, 0 post-shift duplicate dates (clean bijection).
     The shifted box is saved to shifted_boxes/<TOKEN>_full_data_shifted.csv (audit trail).
     A hard assertion fails loudly if the shift ever produces a collision or a non-business
     new date (NO silent fallback).
  3. Re-run Stage 1 + Stage 2 against the SHIFTED box for all 7 TF × 3 presets, writing to
     an isolated tree output_shifted/<TOKEN>/..., then validate (5 invariants) and package
     <TOKEN>_SIGNALS_DELIVERY/ (replacing the ETF bundles; NQ/ES bundles untouched).

Usage:
    python3 subprojects/all-stocks-signals/isolated_etf_box_shift.py
    python3 subprojects/all-stocks-signals/isolated_etf_box_shift.py --instruments QQQ-RTH
    python3 subprojects/all-stocks-signals/isolated_etf_box_shift.py --no-package   # gen+validate only
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
_ALL = os.path.join(_REPO_ROOT, 'ALL_STOCKS')
sys.path.insert(0, _REPO_ROOT)
from src.data.loader import load_data  # noqa: E402

TIMEFRAMES = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']
PRESETS = ['full', '2025', '2026']

# --- the FOUR ETF instruments only (hardcoded; NQ/ES deliberately absent) ---------------
ETF = {
    'QQQ-RTH':  dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'ETF', 'QQQ_Data', 'RTH'),
                     prefix='QQQ_RTH',  box=os.path.join(_ALL, 'BOXS', 'ETF', 'RTH', 'QQQ', 'QQQ_full_data.csv')),
    'QQQ-ETH':  dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'ETF', 'QQQ_Data', 'ETH'),
                     prefix='QQQ_ETH',  box=os.path.join(_ALL, 'BOXS', 'ETF', 'ETH', 'QQQ', 'QQQ_full_data.csv')),
    'SQQQ-RTH': dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'ETF', 'SQQQ_Data', 'RTH'),
                     prefix='SQQQ_RTH', box=os.path.join(_ALL, 'BOXS', 'ETF', 'RTH', 'SQQQ', 'SQQQ_full_data.csv')),
    'SQQQ-ETH': dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'ETF', 'SQQQ_Data', 'ETH'),
                     prefix='SQQQ_ETH', box=os.path.join(_ALL, 'BOXS', 'ETF', 'ETH', 'SQQQ', 'SQQQ_full_data.csv')),
}

_SHIFTED_DIR = os.path.join(_HERE, 'shifted_boxes')
_OUT_ROOT = os.path.join(_HERE, 'output_shifted')


def _load_frozen(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SIGNALS_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g1 = _load_frozen('etf_stage1', 'generate_stage1.py')
g2 = _load_frozen('etf_stage2', os.path.join('stage1_0_reverse_signals', 'generate_stage2.py'))


def shift_box(token: str) -> pd.DataFrame:
    """Load the ETF box, shift Date back 1 business day, assert clean, save + return it."""
    box = pd.read_csv(ETF[token]['box'])
    old = pd.to_datetime(box['Date']).dt.normalize()
    new = old - pd.offsets.BDay(1)
    # loud invariants (no silent fallback)
    assert new.dt.dayofweek.max() <= 4, f"{token}: shift produced a weekend date"
    assert not new.duplicated().any(), f"{token}: shift produced duplicate dates (collision)"
    assert (new < old).all(), f"{token}: some dates not moved backward"
    box = box.copy()
    box['Date'] = new
    os.makedirs(_SHIFTED_DIR, exist_ok=True)
    out = os.path.join(_SHIFTED_DIR, f'{token}_full_data_shifted.csv')
    box.to_csv(out, index=False)
    print(f"  [{token}] shifted box -> {os.path.relpath(out, _REPO_ROOT)}  "
          f"(Date {new.min().date()} .. {new.max().date()})")
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


def generate(token: str, box_idx: pd.DataFrame) -> list:
    cfg = ETF[token]
    summary = []
    for tf in TIMEFRAMES:
        candles_csv = os.path.join(cfg['candle_dir'], f"{cfg['prefix']}_{tf}.csv")
        if not os.path.exists(candles_csv):
            print(f"  SKIP {token} {tf}: missing {candles_csv}", file=sys.stderr); continue
        tf_dir = os.path.join(_OUT_ROOT, token, tf)
        nh_dir = os.path.join(tf_dir, 'no_holds')
        bd_dir = os.path.join(tf_dir, 'by_direction')
        os.makedirs(nh_dir, exist_ok=True); os.makedirs(bd_dir, exist_ok=True)
        for preset in PRESETS:
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
            print(f"  {token:9s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
                  f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
                  f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    pd.DataFrame(summary).to_csv(os.path.join(_OUT_ROOT, token, 'SUMMARY.csv'), index=False)
    return summary


def validate(token: str, box_idx: pd.DataFrame) -> list:
    box_dates = set(box_idx['Date'].dt.date.astype(str))
    errs = []
    for tf in TIMEFRAMES:
        base = os.path.join(_OUT_ROOT, token, tf)
        for p in PRESETS:
            a = pd.read_csv(os.path.join(base, f'signals_{token}_{tf}_{p}.csv'))
            nh = pd.read_csv(os.path.join(base, 'no_holds', f'signals_{token}_{tf}_{p}_no_holds.csv'))
            rev = pd.read_csv(os.path.join(base, f'reverse_signals_{token}_{tf}_{p}.csv'))
            l2s = pd.read_csv(os.path.join(base, 'by_direction', f'long_to_short_{token}_{tf}_{p}.csv'))
            s2l = pd.read_csv(os.path.join(base, 'by_direction', f'short_to_long_{token}_{tf}_{p}.csv'))
            vc = a['signal'].value_counts(); tag = f"{token} {tf} {p}"
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


def package(token: str) -> None:
    src = os.path.join(_OUT_ROOT, token)
    dst = os.path.join(_REPO_ROOT, f'{token}_SIGNALS_DELIVERY')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    n = 0
    for tf in TIMEFRAMES:
        tf_dir = os.path.join(src, tf)
        for p in PRESETS:
            name = f'{token}_{tf}_{p}.csv'
            for s, d in [
                (f'signals_{token}_{tf}_{p}.csv', os.path.join('1_all_signals', name)),
                (os.path.join('no_holds', f'signals_{token}_{tf}_{p}_no_holds.csv'), os.path.join('2_holds_dropped', name)),
                (f'reverse_signals_{token}_{tf}_{p}.csv', os.path.join('3_reverse_signals', name)),
                (os.path.join('by_direction', f'long_to_short_{token}_{tf}_{p}.csv'), os.path.join('4_reverse_by_direction', 'long_to_short', name)),
                (os.path.join('by_direction', f'short_to_long_{token}_{tf}_{p}.csv'), os.path.join('4_reverse_by_direction', 'short_to_long', name)),
            ]:
                sp = os.path.join(tf_dir, s); dp = os.path.join(dst, d)
                os.makedirs(os.path.dirname(dp), exist_ok=True); shutil.copy2(sp, dp); n += 1
    shutil.copy2(os.path.join(src, 'SUMMARY.csv'), os.path.join(dst, 'SUMMARY.csv'))
    with open(os.path.join(dst, 'README.md'), 'w') as f:
        f.write(_readme(token))
    archive = shutil.make_archive(dst, 'zip', root_dir=_REPO_ROOT, base_dir=f'{token}_SIGNALS_DELIVERY')
    print(f"  [{token}] packaged {n} CSVs -> {os.path.basename(dst)}  + {os.path.basename(archive)}")


def _readme(token: str) -> str:
    tfs = ' '.join(f'{token}_{tf}' for tf in TIMEFRAMES)
    return f"""# {token} Signals — Delivery Bundle (BOX-SHIFTED −1 business day)

ETF bundle regenerated with the box `Date` shifted **back one business day** (weekends
skipped): Monday→Friday, Tuesday→Monday, Wednesday→Tuesday, Thursday→Wednesday,
Friday→Thursday. Produced by the ISOLATED script
`subprojects/all-stocks-signals/isolated_etf_box_shift.py` — NQ/ES are unaffected.

Timeframes: `{tfs}` · Presets: `full` `2025` `2026`.
Folders/schemas identical to the standard delivery (see any `NQ`/`ES` bundle README):
1_all_signals (10 cols), 2_holds_dropped (10), 3_reverse_signals (21),
4_reverse_by_direction/{{long_to_short,short_to_long}}, SUMMARY.csv.

Shifted box used: `shifted_boxes/{token}_full_data_shifted.csv`.
Stage 1 / Stage 2 rule engine is the frozen one (reused read-only) — only the box dates differ.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description='ISOLATED ETF box-shift + re-export (ETFs only)')
    ap.add_argument('--instruments', nargs='+', default=list(ETF.keys()), choices=list(ETF.keys()))
    ap.add_argument('--no-package', action='store_true', help='generate + validate only (no bundle)')
    args = ap.parse_args()

    assert all(t in ETF for t in args.instruments), "this script handles ETF instruments ONLY"
    print(f"ISOLATED ETF box-shift (−1 business day) for: {', '.join(args.instruments)}")
    print("NQ & ES are NOT touched by this script.\n")
    all_err = []
    for token in args.instruments:
        print(f"[{token}]")
        box_idx = shift_box(token)
        generate(token, box_idx)
        errs = validate(token, box_idx)
        if errs:
            print(f"  [{token}] VALIDATION FAILED ({len(errs)}):")
            for e in errs:
                print("     ", e)
        else:
            print(f"  [{token}] validation OK — 21 cells × 5 invariants")
        all_err += errs
        if not errs and not args.no_package:
            package(token)
    print(f"\n{'PASS' if not all_err else 'FAIL'}: {len(all_err)} validation errors")
    return 1 if all_err else 0


if __name__ == '__main__':
    raise SystemExit(main())
