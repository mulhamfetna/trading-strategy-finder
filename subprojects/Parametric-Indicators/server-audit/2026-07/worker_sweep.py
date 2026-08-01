"""How many workers maximise AGGREGATE throughput?

Per-worker rate collapses 781 -> 245 tr/min going from 1 to 20 workers, so we are contention-bound, not
fsync-bound. More workers is not automatically better: past the knee, they just fight each other. Sweep
the count and take the aggregate maximum (that, not per-worker rate, is what sets the campaign ETA).
"""
import os
import subprocess
import sys

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
N = 250

WORKER = '''
import os, sys, time
sys.path.insert(0, "{PI}")
os.chdir("{PI}")
import optuna
optuna.logging.set_verbosity(optuna.logging.CRITICAL)
from optimize import optimizer as OPT
from optimize import data as D
D.load_inputs("15m", instrument="NQ")
t0 = time.time()
OPT.run("15m", n_trials={N}, study_prefix="{PREFIX}" + sys.argv[1], instrument="NQ",
        ind_1min=True, warm_start=False)
print("ELAPSED %.2f" % (time.time() - t0))
'''


def launch(n, prefix):
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    code = WORKER.format(PI=PI, N=N, PREFIX=prefix)
    ps = [subprocess.Popen([sys.executable, "-c", code, str(i)],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
          for i in range(n)]
    outs = [p.communicate()[0] for p in ps]
    els = [float(li.split()[1]) for o in outs for li in (o or "").splitlines()
           if li.startswith("ELAPSED")]
    if not els:
        return 0.0, 0.0
    slowest = max(els)
    per = N / slowest * 60
    return per, per * n


print("=== WORKER SWEEP — aggregate throughput (NQ 15m, %d trials each) ===" % N, flush=True)
best = (0, 0.0)
for nw in (12, 20, 26, 30):
    per, tot = launch(nw, f"sw{nw}_")
    eta = 54 * 5900 / max(tot, 1e-9) / 60
    star = ""
    if tot > best[1]:
        best = (nw, tot)
        star = "  <-- best so far"
    print(f"  {nw:2d} workers: per-worker {per:6.1f}  |  TOTAL {tot:8.1f} tr/min  |  "
          f"54-campaign ETA {eta:5.2f} h{star}", flush=True)

print(f"\n  BEST: {best[0]} workers @ {best[1]:.0f} tr/min "
      f"=> ETA {54 * 5900 / max(best[1], 1e-9) / 60:.2f} h", flush=True)
print("SWEEP_DONE", flush=True)
