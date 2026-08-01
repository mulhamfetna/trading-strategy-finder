"""Does `synchronous_commit = off` remove the commit wall?

The profile says psycopg2 'commit' is ~55% of a trial (70 commits/trial, each waiting on a WAL fsync).
synchronous_commit=off stops waiting for that flush. It is NOT fsync=off: there is no corruption risk,
the only exposure is losing the last ~200ms of committed trials on a hard crash — irrelevant for a
resumable optimizer store.

Measures 1 and 20 workers, sync ON vs OFF.
"""
import os
import subprocess
import sys
import time

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
N = 300

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


def psql(sql):
    subprocess.run(["docker", "exec", "wsh-pg", "psql", "-U", "wsh", "-d", "wsh", "-c", sql],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def launch(n, tag, prefix):
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    code = WORKER.format(PI=PI, N=N, PREFIX=prefix)
    ps = [subprocess.Popen([sys.executable, "-c", code, f"{tag}{i}"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
          for i in range(n)]
    outs = [p.communicate()[0] for p in ps]
    els = [float(li.split()[1]) for o in outs for li in (o or "").splitlines()
           if li.startswith("ELAPSED")]
    if not els:
        return 0.0
    return N / max(els) * 60          # per-worker rate at the slowest worker


print("=== synchronous_commit: ON vs OFF (NQ 15m, %d trials/worker) ===" % N, flush=True)
for nw in (1, 20):
    psql("ALTER DATABASE wsh SET synchronous_commit = on;")
    on = launch(nw, f"n{nw}", f"sc_on{nw}")
    psql("ALTER DATABASE wsh SET synchronous_commit = off;")
    off = launch(nw, f"f{nw}", f"sc_off{nw}")
    t_on, t_off = on * nw, off * nw
    print(f"  {nw:2d} worker(s):  sync ON  {on:7.1f} tr/min/worker  (total {t_on:8.1f})", flush=True)
    print(f"               sync OFF {off:7.1f} tr/min/worker  (total {t_off:8.1f})   "
          f"=> {t_off / max(t_on, 1e-9):.2f}x", flush=True)
    if nw == 20:
        for lbl, tot in (("sync ON ", t_on), ("sync OFF", t_off)):
            print(f"     54-campaign ETA, {lbl}: {54 * 5900 / max(tot, 1e-9) / 60:5.2f} h", flush=True)

psql("ALTER DATABASE wsh SET synchronous_commit = off;")   # leave it ON the fast setting
print("SYNC_DONE", flush=True)
