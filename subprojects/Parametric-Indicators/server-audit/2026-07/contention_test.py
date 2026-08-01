"""Does Postgres contention throttle us at 20 concurrent workers?

If per-worker throughput holds steady from 1 -> 20 workers, the store is NOT the wall and a different
storage backend (Redis journal, etc.) buys nothing. If it collapses, the store IS the wall.

Runs the SAME fixed workload (N trials, NQ 15m) as 1 worker, then as 20 concurrent workers, and compares
the PER-WORKER rate.
"""
import os
import subprocess
import sys
import time

WSI = os.path.expanduser("~/Mulham/wsg-i")
PI = os.path.join(WSI, "Parametric-Indicators")
N = 40

WORKER = f'''
import os, sys, time
sys.path.insert(0, "{PI}")
os.chdir("{PI}")
import optuna; optuna.logging.set_verbosity(optuna.logging.CRITICAL)
from optimize import optimizer as OPT
t0 = time.time()
OPT.run("15m", n_trials={N}, study_prefix="cont" + sys.argv[1], instrument="NQ",
        ind_1min=True, warm_start=False)
print(f"{{time.time()-t0:.1f}}")
'''

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def launch(n_workers, tag):
    procs = []
    t0 = time.time()
    for i in range(n_workers):
        p = subprocess.Popen([sys.executable, "-c", WORKER, f"{tag}{i}"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        procs.append(p)
    for p in procs:
        p.wait()
    wall = time.time() - t0
    per_worker_rate = N / wall * 60          # trials/min achieved by EACH worker
    total_rate = N * n_workers / wall * 60   # aggregate
    print(f"  {n_workers:2d} worker(s): wall {wall:6.1f}s | per-worker {per_worker_rate:6.1f} tr/min "
          f"| TOTAL {total_rate:7.1f} tr/min", flush=True)
    return per_worker_rate, total_rate


print(f"=== POSTGRES CONTENTION — {N} trials each, NQ 15m ===", flush=True)
solo, _ = launch(1, "a")
par, total = launch(20, "b")

drop = (1 - par / solo) * 100
print(f"\n  per-worker throughput drop at 20x: {drop:.1f}%", flush=True)
print(f"  aggregate speedup vs 1 worker:     {total / solo:.1f}x  (perfect would be 20x)", flush=True)
if drop > 40:
    print("  => CONTENTION IS REAL — the trial store / CPU is throttling parallel workers", flush=True)
else:
    print("  => scales fine — the store is NOT the wall; parallelism is doing its job", flush=True)
