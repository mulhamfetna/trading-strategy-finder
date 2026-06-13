"""Stage 1 correctness gate — the freeze-once gate_used path must equal the canonical full recompute.

Runs `core.backtest_metrics` on the FULL 29-month series two ways with the champion's own SL/TP:
  (A) canonical: recompute the vol+indicator layer internally (gate_ref_vf = full vf);
  (B) freeze-once: pass the precomputed gate_used + sig_int.
They must produce identical metrics — proving the `gate_used` bypass + the freeze_once() construction are
exact. (Per-window slicing then just slices this proven full-series gate.)
"""
from __future__ import annotations

import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import core, timeframes as TF  # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle  # noqa: E402
from optimize.sub.suboptimizer import champion, freeze_once  # noqa: E402

BAR = TF.get("4h").bar_td


def main() -> int:
    champ = champion()
    df4, df1, box, vf, months = load_bundle()
    N = len(df4)
    si_full, gate_full = freeze_once(df4, df1, box, vf, champ)

    common = dict(sl_soft=champ["sl_soft"], sl_hard=champ["sl_hard"], tp=champ["tp"],
                  dd_limit=champ["dd_limit"], cooldown=champ["cooldown"], flip=champ["flip"],
                  window="full")
    # (A) canonical — recompute layer internally over the full series
    pa = dict(common, gate_pct=champ["gate_pct"], indicators=champ["indicators"],
              k=champ["k"], ind_1min=True)
    mA = core.backtest_metrics(df4, df1, box, vf, N, pa, BAR, gate_ref_vf=vf, sig_int=si_full)
    # (B) freeze-once — precomputed gate_used + sig_int, no layer recompute
    pb = dict(common, gate_pct=0.0)
    mB = core.backtest_metrics(df4, df1, box, vf, N, pb, BAR, gate_used=gate_full, sig_int=si_full)

    keys = ["pnl", "max_dd", "n_taken", "n_candidates", "win", "n_locks"]
    ok = all(mA[k] == mB[k] for k in keys)
    print("freeze-once vs canonical (full 29mo, champion SL/TP):")
    for k in keys:
        print(f"  {k:14s} canonical={mA[k]!r:>12}  frozen={mB[k]!r:>12}  {'OK' if mA[k]==mB[k] else 'MISMATCH'}")
    print("RESULT:", "PARITY OK ✓" if ok else "❌ MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
