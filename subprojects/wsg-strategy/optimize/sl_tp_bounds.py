"""H.5 — per-timeframe SL/TP point-bound derivation (TASK.md D2).

For each actionable entry on a timeframe, measure the post-entry price excursion on the 1-minute
frame over a TF-SCALED horizon (HORIZON_BARS decision bars). This naturally tightens ranges for
fine TFs (6 bars of 1m = 6 min → small moves) and widens them for coarse TFs (6 bars of 4h = 24h →
big moves), matching the intuition that finer entries intend smaller moves — while keeping the
measurement decoupled from the SL/TP being searched.

Per entry (direction-adjusted, in points):
  MFE = max favorable excursion (how far the trade could have run our way)
  MAE = max adverse excursion (how far it went against us)

Bounds are FRACTIONS of each TF's MEDIAN excursion, not raw percentiles. The strategy's edge is
stops/targets TIGHTER than the natural excursion (tight stop + favourable R:R), so the range must
span from "much tighter than typical" up to "around/above typical". Multiples (below) are chosen so
the proven 4h winner (sl_soft 30 / sl_hard 40 / tp 60) sits comfortably inside the 4h ranges:
  sl_soft ∈ [0.15, 0.90] × median(MAE)
  sl_hard ∈ [0.20, 1.20] × median(MAE)
  tp      ∈ [0.20, 1.50] × median(MFE)
All floored at MIN_PTS. These are SEARCH RANGES — the optimiser (H.7) finds each TF's optimum inside.

CLI:  python3 subprojects/wsg-strategy/optimize/sl_tp_bounds.py [tf ...]   → sl_tp_bounds.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data as data_mod, timeframes as TF, signals as sig_mod  # noqa: E402

HORIZON_BARS = 6      # forward window = 6 decision bars (matches the HAR short-lookback unit)
MIN_PTS = 5           # floor for any bound (no sub-5-point stops/targets)
OUT = _HERE / "sl_tp_bounds.json"


def excursions(tf_name: str):
    """Return (mfe_array, mae_array) of post-entry excursions in points over HORIZON_BARS bars."""
    df_dec, df1, box, _vf, _n = data_mod.load_inputs(tf_name)
    sig = sig_mod.decision_signals(df_dec, box)
    tf = TF.get(tf_name)
    horizon = pd.Timedelta(minutes=tf.minutes * HORIZON_BARS)

    m_t = df1["Date"].to_numpy()
    m_hi = df1["High"].to_numpy(float)
    m_lo = df1["Low"].to_numpy(float)
    dec_t = df_dec["Date"].to_numpy()
    dec_close = df_dec["Close"].to_numpy(float)

    mfe, mae = [], []
    for i in range(1, len(df_dec)):
        s = sig[i - 1]                       # engine enters at i on the just-closed bar i-1's signal
        if s not in ("long", "short"):
            continue
        entry_price = dec_close[i - 1]
        t0 = dec_t[i]
        t1 = t0 + np.timedelta64(horizon)
        lo = np.searchsorted(m_t, t0, side="left")
        hi = np.searchsorted(m_t, t1, side="left")
        if hi <= lo:
            continue
        wh = m_hi[lo:hi]; wl = m_lo[lo:hi]
        if s == "long":
            mfe.append(float(wh.max() - entry_price))
            mae.append(float(entry_price - wl.min()))
        else:
            mfe.append(float(entry_price - wl.min()))
            mae.append(float(wh.max() - entry_price))
    return np.array(mfe), np.array(mae)


def _rng(scale: float, lo_mult: float, hi_mult: float):
    lo = max(MIN_PTS, int(round(lo_mult * scale)))
    hi = max(lo + 1, int(round(hi_mult * scale)))
    return [lo, hi]


def bounds_for(tf_name: str) -> dict:
    mfe, mae = excursions(tf_name)
    if len(mfe) < 10:
        return dict(timeframe=tf_name, n_entries=int(len(mfe)), note="too few entries")
    mfe = np.clip(mfe, 0, None); mae = np.clip(mae, 0, None)
    med_mfe = float(np.median(mfe)); med_mae = float(np.median(mae))
    return dict(
        timeframe=tf_name, n_entries=int(len(mfe)), horizon_bars=HORIZON_BARS,
        sl_soft=_rng(med_mae, 0.15, 0.90),
        sl_hard=_rng(med_mae, 0.20, 1.20),
        tp=_rng(med_mfe, 0.20, 1.50),
        mfe_med=round(med_mfe, 1), mae_med=round(med_mae, 1),
    )


def main(argv: list[str]) -> int:
    names = argv or list(TF.TIMEFRAMES)
    res = {}
    print(f"SL/TP search bounds (horizon = {HORIZON_BARS} decision bars; floor {MIN_PTS} pts)\n", flush=True)
    print(f"{'TF':>4} {'#entries':>8} {'sl_soft':>12} {'sl_hard':>12} {'tp':>12} {'MFEmed':>7} {'MAEmed':>7}", flush=True)
    for name in names:
        t = time.time()
        r = bounds_for(name)
        res[name] = r
        if "tp" in r:
            print(f"{name:>4} {r['n_entries']:>8} {str(r['sl_soft']):>12} {str(r['sl_hard']):>12} "
                  f"{str(r['tp']):>12} {r['mfe_med']:>7} {r['mae_med']:>7}   ({time.time()-t:.0f}s)", flush=True)
        else:
            print(f"{name:>4} {r['n_entries']:>8}  {r.get('note')}", flush=True)
    OUT.write_text(json.dumps(res, indent=2))
    print(f"\nwrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
