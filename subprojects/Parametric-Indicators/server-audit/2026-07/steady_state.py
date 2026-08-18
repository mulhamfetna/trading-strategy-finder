"""Steady-state scaling — the number that actually predicts the 54-campaign run.

The short (40-trial) tests were dominated by per-worker STARTUP (each process loads its CSVs; 20 doing
that at once collide on disk/page-cache). A real campaign runs 5,900 trials over ~an hour, so startup
amortises to nothing. Here we measure the TRIALS/MIN AFTER warm-up, 1 worker vs 20, on Postgres —
and separately, how much of a trial is spent talking to the store.
"""
import os
import re
import subprocess
import sys
import time

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
N = 400          # long enough that the ~2s startup is <2% of wall

WORKER = '''
import os, sys, time
sys.path.insert(0, "{PI}")
os.chdir("{PI}")
import optuna
optuna.logging.set_verbosity(optuna.logging.CRITICAL)
{STORE_PATCH}
from optimize import optimizer as OPT
from optimize import data as D
# warm up: load inputs FIRST, outside the timed region, so startup is excluded
D.load_inputs("15m", instrument="NQ")
t0 = time.time()
OPT.run("15m", n_trials={N}, study_prefix="{PREFIX}" + sys.argv[1], instrument="NQ",
        ind_1min=True, warm_start=False)
print("ELAPSED %.2f" % (time.time() - t0))
'''

PATCH_MEM = ('_o = optuna.create_study\n'
             'optuna.create_study = lambda **kw: _o(**{**kw, "storage": None, "load_if_exists": False})')

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def launch(n, tag, store_patch, prefix):
    code = WORKER.format(PI=PI, N=N, STORE_PATCH=store_patch, PREFIX=prefix)
    ps = [subprocess.Popen([sys.executable, "-c", code, f"{tag}{i}"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
          for i in range(n)]
    outs = [p.communicate()[0] for p in ps]
    els = [float(m.group(1)) for o in outs if (m := re.search(r"ELAPSED ([\d.]+)", o or ""))]
    if not els:
        return 0.0, 0.0
    slowest = max(els)                    # the campaign finishes when the slowest worker does
    per = N / slowest * 60
    return per, per * n


print(f"=== STEADY-STATE SCALING — NQ 15m, {N} trials/worker, startup excluded ===", flush=True)

print("\n-- with Postgres (production config) --", flush=True)
pg1, _ = launch(1, "s", "", "st1")
print(f"   1 worker : {pg1:7.1f} trials/min", flush=True)
pg20, pgt = launch(20, "p", "", "st20")
print(f"  20 workers: {pg20:7.1f} trials/min each  |  TOTAL {pgt:8.1f} trials/min", flush=True)
print(f"  aggregate speedup: {pgt / max(pg1, 1e-9):.1f}x   (perfect = 20x)", flush=True)

print("\n-- same, but NO trial store (isolates the store's cost) --", flush=True)
m1, _ = launch(1, "m", PATCH_MEM, "sm1")
print(f"   1 worker : {m1:7.1f} trials/min", flush=True)
m20, mt = launch(20, "n", PATCH_MEM, "sm20")
print(f"  20 workers: {m20:7.1f} trials/min each  |  TOTAL {mt:8.1f} trials/min", flush=True)

print("\n=== VERDICT ===", flush=True)
print(f"  store cost, 1 worker : {(1 - pg1 / max(m1, 1e-9)) * 100:5.1f}% of throughput", flush=True)
print(f"  store cost, 20 worker: {(1 - pgt / max(mt, 1e-9)) * 100:5.1f}% of throughput", flush=True)
print(f"  CPU-only scaling     : {mt / max(m1, 1e-9):.1f}x  (how well the MACHINE scales, store aside)", flush=True)
print(f"  real scaling (PG)    : {pgt / max(pg1, 1e-9):.1f}x", flush=True)
est = 54 * 5900 / max(pgt, 1e-9) / 60
print(f"\n  => projected 54-campaign wall time at 20 workers: {est:.1f} h", flush=True)
