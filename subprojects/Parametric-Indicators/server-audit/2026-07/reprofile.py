"""Re-profile a campaign AFTER the Numba win — what is the new hot spot?

Prints top self-time functions and buckets them, so the next optimisation is chosen from evidence.
Emits progress as it goes (no silent waits).
"""
import cProfile
import io
import os
import pstats
import sys
import time

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import optuna  # noqa: E402
optuna.logging.set_verbosity(optuna.logging.CRITICAL)
from optimize import optimizer as OPT, core  # noqa: E402

TF = os.environ.get("TF", "15m")
N = int(os.environ.get("N", "120"))

print(f"[1/2] warming data + JIT ({TF}) ...", flush=True)
from optimize import data as D
D.load_inputs(TF, instrument="NQ")

print(f"[2/2] profiling {N} trials on {TF} ...", flush=True)
core._clear_caches()
t0 = time.time()
pr = cProfile.Profile()
pr.enable()
OPT.run(TF, n_trials=N, study_prefix="reprof", instrument="NQ", ind_1min=True, warm_start=False)
pr.disable()
wall = time.time() - t0
print(f"\n=== {N} trials in {wall:.1f}s  ({N/wall*60:.0f} trials/min) ===\n", flush=True)

s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(20)
print("TOP 20 BY SELF-TIME:", flush=True)
for line in s.getvalue().splitlines():
    if line.strip() and ("{" in line or ".py:" in line or "ncalls" in line):
        print("  " + line[:135], flush=True)

# bucket
st = pstats.Stats(pr)
tot = st.total_tt
b = {"SMC indicators": 0.0, "classic indicators": 0.0, "engine": 0.0,
     "postgres/store": 0.0, "optuna sampler": 0.0, "numpy/pandas": 0.0}
for (fn, _l, _n), (_cc, _nc, tt, _ct, _c) in st.stats.items():
    f = str(fn)
    if "indicators/smc" in f or "indicators/runner" in f:
        b["SMC indicators"] += tt
    elif "indicators/classic" in f or "indicators/" in f:
        b["classic indicators"] += tt
    elif "fast_engine" in f or "/core.py" in f or "/folds.py" in f:
        b["engine"] += tt
    elif "psycopg" in f or "sqlalchemy" in f or "storages" in f:
        b["postgres/store"] += tt
    elif "optuna" in f:
        b["optuna sampler"] += tt
    elif "numpy" in f or "pandas" in f:
        b["numpy/pandas"] += tt
print(f"\nBUCKETS (total self-time {tot:.1f}s):", flush=True)
for k, v in sorted(b.items(), key=lambda x: -x[1]):
    print(f"  {k:20} {v:7.2f}s  {100*v/max(tot,1e-9):5.1f}%", flush=True)
print(f"  {'other':20} {tot-sum(b.values()):7.2f}s  {100*(tot-sum(b.values()))/max(tot,1e-9):5.1f}%", flush=True)
print("REPROF_DONE", flush=True)
