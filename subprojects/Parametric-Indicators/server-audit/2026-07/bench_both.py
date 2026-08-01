"""Measure the two changes: (1) Numba SMC kernel, (2) JournalStorage vs Postgres."""
import os
import subprocess
import sys
import time
from pathlib import Path

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import numpy as np  # noqa: E402

# ---------------------------------------------------------------- 1) Numba kernel speedup (real data)
print("=== 1) SMC breaker_blocks — Numba vs pure Python (real 1-min frame) ===", flush=True)
from indicators import smc  # noqa: E402
from optimize import data as D  # noqa: E402

_dec, df1, _b, _v, _n = D.load_inputs("4h")
o = df1["Open"].to_numpy(float); h = df1["High"].to_numpy(float)
l = df1["Low"].to_numpy(float); c = df1["Close"].to_numpy(float)
print(f"  1-min bars: {len(c):,}", flush=True)

smc.breaker_blocks(o[:1000], h[:1000], l[:1000], c[:1000], swing_l=2)      # warm JIT

t0 = time.perf_counter(); fast = smc.breaker_blocks(o, h, l, c, swing_l=2); t_fast = time.perf_counter() - t0
t0 = time.perf_counter(); ref = smc._breaker_blocks_py(o, h, l, c, swing_l=2); t_ref = time.perf_counter() - t0

print(f"  pure python : {t_ref:7.3f}s", flush=True)
print(f"  numba jit   : {t_fast:7.3f}s", flush=True)
print(f"  SPEEDUP     : {t_ref / max(t_fast, 1e-9):7.1f}x   identical={np.array_equal(fast, ref)}", flush=True)

# ---------------------------------------------------------------- 2) storage: postgres vs journal
N = 400
WORKER = '''
import os, sys, time
sys.path.insert(0, "{PI}")
os.chdir("{PI}")
import optuna
optuna.logging.set_verbosity(optuna.logging.CRITICAL)
from optimize import optimizer as OPT
from optimize import data as D
D.load_inputs("15m", instrument="NQ")        # load OUTSIDE the timed region
t0 = time.time()
OPT.run("15m", n_trials={N}, study_prefix="{PREFIX}" + sys.argv[1], instrument="NQ",
        ind_1min=True, warm_start=False)
print("ELAPSED %.2f" % (time.time() - t0))
'''

JDIR = os.path.expanduser("~/Mulham/wsg-i/journals_bench")


def launch(n, tag, prefix, journal):
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    if journal:
        env["WSH_JOURNAL_DIR"] = JDIR
    else:
        env.pop("WSH_JOURNAL_DIR", None)
    code = WORKER.format(PI=PI, N=N, PREFIX=prefix)
    ps = [subprocess.Popen([sys.executable, "-c", code, f"{tag}{i}"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
          for i in range(n)]
    outs = [p.communicate()[0] for p in ps]
    els = []
    for out in outs:
        for line in (out or "").splitlines():
            if line.startswith("ELAPSED"):
                els.append(float(line.split()[1]))
    if not els:
        return 0.0
    slowest = max(els)                       # a campaign ends when its slowest worker ends
    return N / slowest * 60


print(f"\n=== 2) TRIAL STORE — NQ 15m, {N} trials/worker (startup excluded) ===", flush=True)
for nw in (1, 20):
    pg = launch(nw, f"p{nw}", f"bpg{nw}", journal=False)
    jr = launch(nw, f"j{nw}", f"bjr{nw}", journal=True)
    tot_pg, tot_jr = pg * nw, jr * nw
    print(f"  {nw:2d} worker(s):  postgres {pg:7.1f} tr/min/worker (total {tot_pg:8.1f})", flush=True)
    print(f"               journal  {jr:7.1f} tr/min/worker (total {tot_jr:8.1f})   "
          f"=> {tot_jr / max(tot_pg, 1e-9):.1f}x", flush=True)
    if nw == 20:
        est_pg = 54 * 5900 / max(tot_pg, 1e-9) / 60
        est_jr = 54 * 5900 / max(tot_jr, 1e-9) / 60
        print(f"\n  projected 54-campaign wall time @20 workers:", flush=True)
        print(f"     postgres : {est_pg:5.1f} h", flush=True)
        print(f"     journal  : {est_jr:5.1f} h", flush=True)
print("BENCH_DONE", flush=True)
