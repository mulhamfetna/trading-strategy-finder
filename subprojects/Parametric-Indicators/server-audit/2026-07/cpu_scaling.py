"""Is the 20-worker wall Postgres, or CPU/memory bandwidth?

Same workload, same 20 processes, but with NO shared trial store (Optuna InMemoryStorage). If throughput
still collapses => the store is innocent and we are CPU/memory-bandwidth bound. If it scales => Postgres
was the wall, and a lighter backend (Redis journal, batching) would actually buy something.
"""
import os
import subprocess
import sys
import time

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
N = 40

WORKER = f'''
import os, sys, time
sys.path.insert(0, "{PI}")
os.chdir("{PI}")
os.environ.pop("WSH_STORAGE_URL", None)          # no postgres
import optuna
optuna.logging.set_verbosity(optuna.logging.CRITICAL)
# Force InMemoryStorage: make create_study ignore whatever storage the optimizer hands it.
_orig = optuna.create_study
optuna.create_study = lambda **kw: _orig(**{{**kw, "storage": None, "load_if_exists": False}})
from optimize import optimizer as OPT
t0 = time.time()
OPT.run("15m", n_trials={N}, study_prefix="mem" + sys.argv[1], instrument="NQ",
        ind_1min=True, warm_start=False)
print(f"{{time.time()-t0:.1f}}")
'''

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def launch(n, tag):
    t0 = time.time()
    ps = [subprocess.Popen([sys.executable, "-c", WORKER, f"{tag}{i}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
          for i in range(n)]
    for p in ps:
        p.wait()
    wall = time.time() - t0
    per = N / wall * 60
    tot = N * n / wall * 60
    print(f"  {n:2d} worker(s) NO-STORE: wall {wall:6.1f}s | per-worker {per:6.1f} tr/min "
          f"| TOTAL {tot:7.1f} tr/min", flush=True)
    return per, tot


print("=== PURE CPU SCALING (in-memory store, zero shared I/O) ===", flush=True)
solo, _ = launch(1, "x")
par, tot = launch(20, "y")
drop = (1 - par / solo) * 100
print(f"\n  per-worker drop at 20x: {drop:.1f}%", flush=True)
print(f"  aggregate speedup:      {tot / solo:.1f}x   (perfect = 20x)", flush=True)
if drop > 40:
    print("  VERDICT: CPU / memory-bandwidth bound. The trial store is INNOCENT —", flush=True)
    print("           swapping Postgres for Redis would change nothing.", flush=True)
else:
    print("  VERDICT: scales fine without the store => POSTGRES was the wall.", flush=True)
