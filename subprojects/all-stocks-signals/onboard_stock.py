"""Reusable stock-onboarding pipeline — box shift (-1 workday) + signal generation.

GENERALIZED successor to isolated_etf_box_shift.py: instead of hardcoding one instrument family, it drives a
config table `ONBOARD` (token -> candle_dir / prefix / raw box), so ANY new stock is onboarded by adding one
entry. It reuses ONLY the FROZEN Stage 1 / Stage 2 signal engine (read-only, by file path), so the signal
methodology is identical to the approved pipeline for every instrument.

Per instrument it:
  1. shifts the box `Date` back one BUSINESS day (weekends skipped): Mon->Fri, Tue->Mon, Wed->Tue, Thu->Wed,
     Fri->Thu — with loud invariants (no weekend, no collision, all moved back). Saves
     shifted_boxes/<TOKEN>_full_data_shifted.csv (the file the backtester reads — see the registry).
  2. re-runs Stage 1 + Stage 2 against the SHIFTED box for 7 TF x 3 presets into output_shifted/<TOKEN>/...,
  3. validates (5 invariants) and packages <TOKEN>_SIGNALS_DELIVERY/.

NQ is deliberately absent: it is the frozen golden anchor and is NEVER shifted.

>>> HUMAN-GATE (see NEW_STOCK_ONBOARDING_SOP.md STEP 0) <<<
Before onboarding a NEW stock, confirm with the user whether to use THIS pipeline as-is or a modified one, and
confirm the contract point-value (full vs micro). Only then add its ONBOARD entry and run.

Usage:
    python3 subprojects/all-stocks-signals/onboard_stock.py                 # all in ONBOARD
    python3 subprojects/all-stocks-signals/onboard_stock.py --tokens GC SI  # subset
    python3 subprojects/all-stocks-signals/onboard_stock.py --no-package    # gen+validate only
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_SIGNALS_ROOT = os.path.abspath(os.path.join(_HERE, '..', 'signals'))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_ALL = os.path.join(_REPO_ROOT, 'ALL_STOCKS')
sys.path.insert(0, _REPO_ROOT)
from src.data.loader import load_data  # noqa: E402

TIMEFRAMES = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']
PRESETS = ['full', '2025', '2026']


def _cdir(*parts: str) -> str:
    return os.path.join(_ALL, 'CANDLES', *parts)


def _box(*parts: str) -> str:
    return os.path.join(_ALL, 'BOXS', *parts)


# --- instruments to onboard (NQ excluded on purpose: frozen anchor, never shifted) -----------------------------
# Each entry: candle_dir holds <prefix>_<TF>.csv ; box is the RAW (unshifted) _full_data.csv.
ONBOARD = {
    'ES': dict(candle_dir=_cdir('CME', 'ES_Continuous_Data'), prefix='ES',
               box=_box('CME', 'ES', 'ES_full_data.csv')),
    'GC': dict(candle_dir=_cdir('COMEX', 'GC_Continuous_Data'), prefix='GC',
               box=_box('COMEX', 'GC', 'GC_full_data.csv')),
    'SI': dict(candle_dir=_cdir('COMEX', 'SI_Continuous_Data'), prefix='SI',
               box=_box('COMEX', 'SI', 'SI_full_data.csv')),
    'HG': dict(candle_dir=_cdir('COMEX', 'HG_Continuous_Data'), prefix='HG',
               box=_box('COMEX', 'HG', 'HG_full_data.csv')),
    'CL': dict(candle_dir=_cdir('NYMEX', 'CL_Continuous_Data'), prefix='CL',
               box=_box('NYMEX', 'CL', 'CL_full_data.csv')),
    'NG': dict(candle_dir=_cdir('NYMEX', 'NG_Continuous_Data'), prefix='NG',
               box=_box('NYMEX', 'NG', 'NG_full_data.csv')),
    'RTY': dict(candle_dir=_cdir('CME', 'RTY_Continuous_Data'), prefix='RTY',
                box=_box('CME', 'RTY', 'RTY_full_data.csv')),
    'YM': dict(candle_dir=_cdir('CME', 'YM_Continuous_Data'), prefix='YM',
               box=_box('CME', 'YM', 'YM_full_data.csv')),
}

_SHIFTED_DIR = os.path.join(_HERE, 'shifted_boxes')
_OUT_ROOT = os.path.join(_HERE, 'output_shifted')


def _load_frozen(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SIGNALS_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g1 = _load_frozen('onboard_stage1', 'generate_stage1.py')
g2 = _load_frozen('onboard_stage2', os.path.join('stage1_0_reverse_signals', 'generate_stage2.py'))


def shifted_box_path(token: str) -> str:
    return os.path.join(_SHIFTED_DIR, f'{token}_full_data_shifted.csv')


def shift_box(token: str) -> pd.DataFrame:
    """Load the raw box, shift Date back 1 business day, assert clean, save + return it (indexed by Date)."""
    box = pd.read_csv(ONBOARD[token]['box'])
    old = pd.to_datetime(box['Date']).dt.normalize()
    new = old - pd.offsets.BDay(1)
    assert new.dt.dayofweek.max() <= 4, f"{token}: shift produced a weekend date"
    assert not new.duplicated().any(), f"{token}: shift produced duplicate dates (collision)"
    assert (new < old).all(), f"{token}: some dates not moved backward"
    box = box.copy()
    box['Date'] = new
    os.makedirs(_SHIFTED_DIR, exist_ok=True)
    out = shifted_box_path(token)
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
    cfg = ONBOARD[token]
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
            print(f"  {token:4s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
                  f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
                  f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    os.makedirs(os.path.join(_OUT_ROOT, token), exist_ok=True)
    pd.DataFrame(summary).to_csv(os.path.join(_OUT_ROOT, token, 'SUMMARY.csv'), index=False)
    return summary


def _load_shifted_box(token: str) -> pd.DataFrame:
    """Reload the already-written shifted box as a Date-indexed frame (for parallel workers)."""
    box = pd.read_csv(shifted_box_path(token))
    box['Date'] = pd.to_datetime(box['Date'])
    return box.set_index('Date', drop=False)


def _gen_unit(token: str, tf: str, preset: str) -> dict | None:
    """Generate the 5 signal files for ONE (token, tf, preset) unit. Module-level + picklable so it can run in a
    ProcessPoolExecutor. Reloads the shifted box itself (cheap) so no DataFrame crosses the process boundary.
    Byte-identical to the serial path — it writes the same files with the same content. Returns a summary row."""
    cfg = ONBOARD[token]
    candles_csv = os.path.join(cfg['candle_dir'], f"{cfg['prefix']}_{tf}.csv")
    if not os.path.exists(candles_csv):
        print(f"  SKIP {token} {tf} {preset}: missing {candles_csv}", file=sys.stderr)
        return None
    box_idx = _load_shifted_box(token)
    tf_dir = os.path.join(_OUT_ROOT, token, tf)
    nh_dir = os.path.join(tf_dir, 'no_holds')
    bd_dir = os.path.join(tf_dir, 'by_direction')
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
    print(f"  {token:4s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
          f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
          f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}", flush=True)
    return dict(instrument=token, timeframe=f'{token}_{tf}', preset=preset, signal_rows=len(s1),
                long=int(d.get('long', 0)), short=int(d.get('short', 0)), hold=int(d.get('hold', 0)),
                no_hold_rows=len(nh), reverse_windows=len(rev))


def generate_parallel(tokens: list, timeframes: list, jobs: int) -> None:
    """Shift each token's box (serial, fast), then fan (token, tf, preset) units across `jobs` processes.
    Writes a per-token SUMMARY.csv afterwards. Same outputs as the serial generate(), just concurrent."""
    for tok in tokens:
        shift_box(tok)                                   # writes shifted_boxes/<tok>_full_data_shifted.csv
    tasks = [(tok, tf, p) for tok in tokens for tf in timeframes for p in PRESETS]
    print(f"  parallel generate: {len(tasks)} (token,tf,preset) units across {jobs} workers", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for r in ex.map(_gen_unit_star, tasks):
            if r is not None:
                rows.append(r)
    for tok in tokens:
        os.makedirs(os.path.join(_OUT_ROOT, tok), exist_ok=True)
        pd.DataFrame([r for r in rows if r['instrument'] == tok]).to_csv(
            os.path.join(_OUT_ROOT, tok, 'SUMMARY.csv'), index=False)


def _gen_unit_star(args):
    return _gen_unit(*args)


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
        f.write(f"# {token} Signals — Delivery Bundle (BOX-SHIFTED -1 business day)\n\n"
                f"{token} regenerated with the box Date shifted back one business day (weekends skipped) by the "
                f"reusable pipeline onboard_stock.py. NQ is never shifted. "
                f"Timeframes {' '.join(TIMEFRAMES)}; presets {' '.join(PRESETS)}. "
                f"Shifted box: shifted_boxes/{token}_full_data_shifted.csv.\n")
    archive = shutil.make_archive(dst, 'zip', root_dir=_REPO_ROOT, base_dir=f'{token}_SIGNALS_DELIVERY')
    print(f"  [{token}] packaged {n} CSVs -> {os.path.basename(dst)}  + {os.path.basename(archive)}")


def main() -> int:
    ap = argparse.ArgumentParser(description='Reusable stock onboarding: box-shift (-1 BDay) + signal gen')
    ap.add_argument('--tokens', nargs='+', default=list(ONBOARD.keys()), choices=list(ONBOARD.keys()))
    ap.add_argument('--tf', nargs='+', default=TIMEFRAMES, choices=TIMEFRAMES,
                    help='restrict to these timeframes (default all 7)')
    ap.add_argument('--jobs', type=int, default=1,
                    help='parallel worker processes across (token,tf,preset) units (default 1 = serial). '
                         'Use a high value ONLY on a big-RAM host (each 1m worker needs ~1GB).')
    ap.add_argument('--no-package', action='store_true', help='generate + validate only (no bundle)')
    args = ap.parse_args()
    print(f"Onboarding (box-shift -1 business day) for: {', '.join(args.tokens)} "
          f"| tf={','.join(args.tf)} | jobs={args.jobs}")
    print("NQ is NOT touched (frozen anchor).\n")

    if args.jobs > 1:
        generate_parallel(args.tokens, args.tf, args.jobs)     # shifts boxes + fans units across processes
    all_errs = []
    for tok in args.tokens:
        if args.jobs > 1:
            box_idx = _load_shifted_box(tok)                   # already shifted+generated above
        else:
            box_idx = shift_box(tok)
            generate(tok, box_idx)
        errs = validate(tok, box_idx) if args.tf == TIMEFRAMES else []   # validation assumes all 7 TFs present
        all_errs += errs
        print(f"  [{tok}] validation: {'OK' if not errs else ('SKIPPED (tf subset)' if args.tf != TIMEFRAMES else errs)}")
        if not args.no_package and not errs and args.tf == TIMEFRAMES:
            package(tok)
    if all_errs:
        print("VALIDATION FAILED:", all_errs, file=sys.stderr); return 1
    print("\nDONE.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
