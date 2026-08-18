"""Where does an optimizer trial actually spend its time? Measured, not guessed.

Decides whether a cross-process cache (Redis) can possibly help, or whether it would only add
serialization overhead on top of work that is already CPU-bound and already memoized in-process.

  A) Postgres vs local SQLite for the SAME trials  -> how much is the trial STORE costing us?
  B) cProfile                                      -> how much time is in SQLAlchemy/optuna vs the engine?
  C) memo state                                    -> is the repeated work already absorbed in-process?
"""
import cProfile
import io
import os
import pstats
import sys
import time
from pathlib import Path

_PI = Path(os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators"))
sys.path.insert(0, str(_PI))
os.chdir(_PI)

import optuna  # noqa: E402
optuna.logging.set_verbosity(optuna.logging.WARNING)

from optimize import optimizer as OPT, core  # noqa: E402

N = int(os.environ.get("N_TRIALS", "60"))
TF = os.environ.get("TF", "4h")
INST = os.environ.get("INST", "NQ")
PG_URL = os.environ.get("WSH_STORAGE_URL", "")


def run_with(url, prefix, label):
    """Run N trials against a given store. url='' => unset => per-TF SQLite file."""
    if url:
        os.environ["WSH_STORAGE_URL"] = url
    else:
        os.environ.pop("WSH_STORAGE_URL", None)
    core._clear_caches()
    t0 = time.time()
    OPT.run(TF, n_trials=N, study_prefix=prefix, instrument=INST,
            ind_1min=True, warm_start=False)
    dt = time.time() - t0
    print(f"  {label:24} {N} trials in {dt:7.1f}s   ->  {N/dt*60:7.1f} trials/min", flush=True)
    return dt


print(f"=== A) TRIAL-STORE COST — {INST} {TF}, {N} trials each ===", flush=True)
t_pg = run_with(PG_URL, "probpg", "postgres (current)")
t_lite = run_with("", "problite", "local sqlite file")
diff = t_pg - t_lite
print(f"\n  postgres costs {diff:+.1f}s vs sqlite  ({abs(diff)/max(t_pg,1e-9)*100:.1f}% of wall)", flush=True)
print(f"  => {'STORE is a real cost' if abs(diff) > 0.15 * t_pg else 'STORE is NOT the bottleneck'}\n", flush=True)

print(f"=== B) cProfile ({N} trials, postgres) — where the time really goes ===", flush=True)
os.environ["WSH_STORAGE_URL"] = PG_URL
core._clear_caches()
pr = cProfile.Profile()
pr.enable()
OPT.run(TF, n_trials=N, study_prefix="probprof", instrument=INST, ind_1min=True, warm_start=False)
pr.disable()

st = pstats.Stats(pr)
total = st.total_tt

# bucket cumulative time by subsystem
buckets = {"engine/backtest": 0.0, "indicators": 0.0, "numpy/pandas": 0.0,
           "sqlalchemy/db": 0.0, "optuna/sampler": 0.0}
for (fn, _ln, _name), (_cc, _nc, tt, _ct, _cal) in st.stats.items():
    f = str(fn)
    if "sqlalchemy" in f or "psycopg" in f or "/storages/" in f:
        buckets["sqlalchemy/db"] += tt
    elif "optuna" in f:
        buckets["optuna/sampler"] += tt
    elif "fast_engine" in f or "/core.py" in f or "/folds.py" in f or "engine.py" in f:
        buckets["engine/backtest"] += tt
    elif "indicators" in f:
        buckets["indicators"] += tt
    elif "numpy" in f or "pandas" in f:
        buckets["numpy/pandas"] += tt

print(f"  total tottime: {total:.1f}s", flush=True)
for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
    print(f"    {k:18} {v:7.2f}s   {100*v/max(total,1e-9):5.1f}%", flush=True)
other = total - sum(buckets.values())
print(f"    {'other':18} {other:7.2f}s   {100*other/max(total,1e-9):5.1f}%", flush=True)

print(f"\n  --- top 12 by cumulative ---", flush=True)
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(12)
for line in s.getvalue().splitlines()[4:]:
    if line.strip():
        print("  " + line, flush=True)

print(f"\n=== C) IN-PROCESS MEMOS after {N} trials ===", flush=True)
print(f"  _SRC_MEMO  {len(core._SRC_MEMO):5d} entries", flush=True)
print(f"  _VOTE_MEMO {len(core._VOTE_MEMO):5d} entries", flush=True)
print(f"  _EOD_MEMO  {len(core._EOD_MEMO):5d} entries", flush=True)
