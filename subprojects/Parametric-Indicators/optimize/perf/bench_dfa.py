"""Task 3 server benchmark: accelerated `dfa` vs the reference on the REAL 1-minute frame (issue #54).

For each window n in {20, 100, 400} (grid min / default / max) over the true ~486,970-bar NQ 1-minute
close: time the reference (`calc.quant.dfa`) vs the accelerated `cold_accel.dfa_fast`, and re-verify the
parity contract on real data — identical finite mask, float-closeness, and ZERO vote-boolean flips across
the whole threshold grid [0.30, 0.70]. Writes results/dfa_bench_NQ_1m.json.

Run: WSH_DATA_BASE=/home/dev/Mulham/wsg-i /home/dev/Mulham/.venv/bin/python3 -m optimize.perf.bench_dfa
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from loader import load_data
from indicators.calc import quant as Q
from optimize import timeframes as TF
from optimize.perf import cold_accel

THR = np.round(np.arange(0.30, 0.7001, 0.01), 2)


def main() -> int:
    base = os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading")
    csv = Path(base) / TF.RAW_DIR / "NQ_1m.csv"
    close = load_data(str(csv)).sort_values("Date")["Close"].to_numpy(float)
    print(f"[dfa-bench] loaded {len(close):,} 1-min closes from {csv}", flush=True)

    cold_accel.dfa_fast(close[:3000], 100)   # warm up the JIT so timings exclude compilation
    res = {"n_bars": int(len(close)), "per_n": {}}
    for n in (20, 100, 400):
        t0 = time.perf_counter(); ref = Q.dfa(close, n); tr = time.perf_counter() - t0
        t0 = time.perf_counter(); fast = cold_accel.dfa_fast(close, n); tf = time.perf_counter() - t0
        fin_ref, fin_fast = np.isfinite(ref), np.isfinite(fast)
        mask_ok = bool(np.array_equal(fin_ref, fin_fast))
        close_ok = bool(np.allclose(ref[fin_ref], fast[fin_fast], rtol=1e-6, atol=1e-8)) if fin_ref.any() else True
        max_flips = 0
        for thr in THR:
            vr = fin_ref & (ref < thr); vf = fin_fast & (fast < thr)
            max_flips = max(max_flips, int(np.sum(vr != vf)))
        row = {"ref_s": round(tr, 3), "fast_s": round(tf, 3),
               "speedup": round(tr / tf, 1) if tf else None,
               "mask_match": mask_ok, "float_close": close_ok,
               "max_vote_flips_over_grid": max_flips}
        res["per_n"][str(n)] = row
        print(f"[dfa-bench n={n}] ref={tr:.2f}s fast={tf:.3f}s speedup={tr/tf:.0f}x "
              f"mask={mask_ok} float_close={close_ok} max_vote_flips={max_flips}", flush=True)

    out = Path(__file__).resolve().parent / "results" / "dfa_bench_NQ_1m.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(f"[dfa-bench] WROTE {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
