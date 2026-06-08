"""WS-AS.5 — structural validation of generated bundles (per instrument).

Checks the invariants that must hold for every (instrument, TF, preset) regardless of
instrument, reading directly from the technical output tree (output/<token>/...):

  1. counts:   long + short + hold == signal_rows ;  no_hold_rows == long + short
  2. subset:   holds-dropped rows ⊂ all-signals rows (no_hold has no 'hold')
  3. partition: by_direction long_to_short + short_to_long == reverse rows (exact split)
  4. no-mix:   every box_id's date resolves inside THIS instrument's own box Date index
  5. reverse ≤ no_hold (each window endpoint is a long/short signal)

Exit non-zero if any check fails. Run after generate_signals.py.

Usage: python3 subprojects/all-stocks-signals/validate_bundles.py [--instruments NQ ES ...]
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from instruments import REGISTRY, TOKENS, TIMEFRAMES, PRESETS  # noqa: E402

_OUT = os.path.join(_HERE, 'output')


def _box_dates(token: str) -> set:
    box = pd.read_csv(REGISTRY[token].box_csv, usecols=['Date'])
    return set(pd.to_datetime(box['Date']).dt.normalize().dt.date.astype(str))


def validate_cell(token: str, tf: str, preset: str, box_dates: set) -> list:
    base = os.path.join(_OUT, token, tf)
    errs = []
    allp = os.path.join(base, f'signals_{token}_{tf}_{preset}.csv')
    nhp = os.path.join(base, 'no_holds', f'signals_{token}_{tf}_{preset}_no_holds.csv')
    revp = os.path.join(base, f'reverse_signals_{token}_{tf}_{preset}.csv')
    l2sp = os.path.join(base, 'by_direction', f'long_to_short_{token}_{tf}_{preset}.csv')
    s2lp = os.path.join(base, 'by_direction', f'short_to_long_{token}_{tf}_{preset}.csv')
    for p in (allp, nhp, revp, l2sp, s2lp):
        if not os.path.exists(p):
            return [f"{token} {tf} {preset}: MISSING {os.path.basename(p)}"]

    a = pd.read_csv(allp)
    nh = pd.read_csv(nhp)
    rev = pd.read_csv(revp)
    l2s = pd.read_csv(l2sp)
    s2l = pd.read_csv(s2lp)
    tag = f"{token} {tf} {preset}"

    # 1. counts
    vc = a['signal'].value_counts()
    if vc.get('long', 0) + vc.get('short', 0) + vc.get('hold', 0) != len(a):
        errs.append(f"{tag}: signal counts != rows")
    if len(nh) != vc.get('long', 0) + vc.get('short', 0):
        errs.append(f"{tag}: no_hold_rows != long+short")
    # 2. subset
    if (nh['signal'] == 'hold').any():
        errs.append(f"{tag}: holds present in no_holds")
    # 3. partition
    if len(l2s) + len(s2l) != len(rev):
        errs.append(f"{tag}: by_direction split != reverse ({len(l2s)}+{len(s2l)} vs {len(rev)})")
    if len(rev) and not (set(l2s['first_signal'].unique()) <= {'long'}
                         and set(s2l['first_signal'].unique()) <= {'short'}):
        errs.append(f"{tag}: by_direction mislabelled")
    # 4. no-mix: box_id dates ∈ this instrument's box index
    ids = a['box_id'].dropna()
    if len(ids):
        dates = ids.astype(str).str.rsplit('_', n=1).str[-1]
        bad = set(dates.unique()) - box_dates
        if bad:
            errs.append(f"{tag}: {len(bad)} box_id date(s) outside own box index e.g. {list(bad)[:3]}")
    # 5. reverse ≤ no_hold
    if len(rev) > len(nh):
        errs.append(f"{tag}: reverse windows > no_hold rows")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--instruments', nargs='+', default=TOKENS, choices=TOKENS)
    args = ap.parse_args()
    total_err = []
    for token in args.instruments:
        if not os.path.isdir(os.path.join(_OUT, token)):
            print(f"SKIP {token}: no output"); continue
        bd = _box_dates(token)
        cell_errs = []
        for tf in TIMEFRAMES:
            for preset in PRESETS:
                cell_errs += validate_cell(token, tf, preset, bd)
        if cell_errs:
            print(f"[{token}] {len(cell_errs)} FAILURES")
            for e in cell_errs:
                print("   ", e)
        else:
            print(f"[{token}] OK — all {len(TIMEFRAMES)*len(PRESETS)} cells pass 5 invariants")
        total_err += cell_errs
    print(f"\n{'PASS' if not total_err else 'FAIL'}: {len(total_err)} total errors")
    return 1 if total_err else 0


if __name__ == '__main__':
    raise SystemExit(main())
