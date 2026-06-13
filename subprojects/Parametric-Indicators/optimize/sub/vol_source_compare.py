"""opt1 (ATR/vol-multiple) under DIFFERENT volatility sources — is the multiplier driven by 4h or 1-min vol?
Consistency check vs the '1-minute frame' convention. Compares, OOS (guarded band 0.33–1.05):
  • 4h ATR(14)            — what the study used (decision-frame)
  • HAR-RV vf             — the system's 1-MINUTE-based volatility forecast (canonical, aligned per dec-bar)
  • 1-min ATR(240)@dec    — true 1-minute ATR sampled at each decision bar's last-closed minute (the exact
                            1-min-indicator sampling, j_idx)
Each: fit global a on TRAIN, mult=clip(a·vol/vol_ref,band), eval on TEST vs the fixed champion.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from indicators import classic, runner
from optimize import timeframes as TF, signals as sig_mod
from optimize.sub.data_2024_2026 import load_bundle
from optimize.sub.suboptimizer import champion, freeze_once
from optimize.sub.stage2 import eval_dynamic

_BAR = TF.get("4h").bar_td
BAND = (40 / 120.2, 175 / 167.1)        # guarded shared-multiplier band = (0.333, 1.047)
TRAIN_END = "2025-06"


def _fit_eval(name, vol, df4, df1, box, gate, sig, champ, tr_hi, N):
    vol = np.asarray(vol, float)
    vol = np.nan_to_num(vol, nan=np.nanmean(vol))
    ref = float(vol[:tr_hi].mean())
    base = vol / ref
    best_a, best = 1.0, -1e18
    for a in np.linspace(0.4, 1.8, 15):
        m = np.clip(a * base, *BAND)
        tr = eval_dynamic(df4, df1, box, gate, sig, champ, m, 0, tr_hi)
        if tr["pnl"] > best:
            best, best_a = tr["pnl"], a
    m = np.clip(best_a * base, *BAND)
    te = eval_dynamic(df4, df1, box, gate, sig, champ, m, tr_hi, N)
    mt = m[tr_hi:N]
    te.update(a=best_a, ref=ref, mult_med=float(np.median(mt)), mult_min=float(mt.min()), mult_max=float(mt.max()))
    return name, te


def main() -> int:
    champ = champion()
    df4, df1, box, vf, months = load_bundle()
    si_full, gate = freeze_once(df4, df1, box, vf, champ)
    sig = sig_mod.decision_signals(df4, box)
    N = len(df4); tr_hi = int(np.nonzero(months <= TRAIN_END)[0][-1]) + 1

    atr4h = classic.atr(df4["High"].to_numpy(float), df4["Low"].to_numpy(float), df4["Close"].to_numpy(float), 14)
    # 1-min ATR(240) sampled at each decision bar's last-closed minute (j_idx, the indicator sampling)
    _, j = runner.indicator_source_1min(df4, df1, _BAR)
    atr1m = classic.atr(df1["High"].to_numpy(float), df1["Low"].to_numpy(float), df1["Close"].to_numpy(float), 240)
    atr1m_dec = np.where(j >= 0, atr1m[np.clip(j, 0, len(atr1m) - 1)], np.nan)

    fixed = eval_dynamic(df4, df1, box, gate, sig, champ, np.ones(N), tr_hi, N)
    rows = [("fixed", dict(fixed, a=float("nan"), ref=float("nan"), mult_med=1, mult_min=1, mult_max=1)),
            _fit_eval("opt1 / 4h ATR(14)", atr4h, df4, df1, box, gate, sig, champ, tr_hi, N),
            _fit_eval("opt1 / HAR-RV vf (1-min)", vf, df4, df1, box, gate, sig, champ, tr_hi, N),
            _fit_eval("opt1 / 1-min ATR(240)@dec", atr1m_dec, df4, df1, box, gate, sig, champ, tr_hi, N)]
    print(f"\nOOS TEST (months > {TRAIN_END}), guarded band {BAND[0]:.2f}–{BAND[1]:.2f}")
    print(f"{'vol source':26s} {'pnl':>9s} {'maxDD':>8s} {'DD/PL':>6s} {'retDD':>6s} {'win%':>5s} {'a':>5s} {'mult med(min..max)':>20s}")
    for nm, m in rows:
        ddpl = 100 * m["max_dd"] / m["pnl"] if m["pnl"] > 0 else 0
        rdd = m["pnl"] / m["max_dd"] if m["max_dd"] > 0 else 0
        print(f"{nm:26s} {m['pnl']:>9.0f} {m['max_dd']:>8.0f} {ddpl:>5.0f}% {rdd:>6.2f} {m['win']:>5.1f} "
              f"{m['a']:>5.2f}  {m['mult_med']:.2f} ({m['mult_min']:.2f}..{m['mult_max']:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
