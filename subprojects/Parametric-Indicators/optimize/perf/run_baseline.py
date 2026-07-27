"""Task 2 — server baseline profile of the optimizer's indicator cold/warm split (issue #54).

Runs the REAL optimizer objective for N trials with the cache Probe installed, fully isolated so it
pollutes nothing:
  * ``WSH_JOURNAL_DIR`` → a throwaway per-study journal store (no shared Postgres/SQLite write).
  * a fresh, COLD ``vote_cache`` dir → the first trials are genuine cold misses; reuse builds as it goes,
    so the measured hit-rate is the real sweep's steady-state, not a pre-warmed artifact.

Emits, to ``optimize/perf/results/baseline_<inst>_<tf>.json``: wall-clock, cold-compute seconds and its
fraction of wall, disk hit-rate, and the **per-indicator cold-cost ranking** that Tasks 3/5 use to pick
which indicators to accelerate. A daemon heartbeat prints progress every ``--heartbeat`` seconds.

Server run (venv has numpy/pandas/optuna/scipy/numba):
  WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data \
  /home/dev/Mulham/.venv/bin/python3 -m optimize.perf.run_baseline --tf 4h --trials 200
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Parametric-Indicators root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--heartbeat", type=int, default=30, help="seconds between progress prints")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # --- isolation: throwaway journal store + cold vote cache -------------------------------------
    tmp = Path(tempfile.mkdtemp(prefix="probe54_"))
    (tmp / "journal").mkdir(parents=True, exist_ok=True)
    os.environ["WSH_JOURNAL_DIR"] = str(tmp / "journal")     # journal wins over any WSH_STORAGE_URL (isolation)

    from optimize import vote_cache, core
    vote_cache.set_cache_dir(tmp / "vote_cache")
    vote_cache._clear_disk_cache()
    core._clear_caches()

    from optimize import optimizer
    from indicators import library
    from optimize.perf.cache_probe import Probe

    prefix = f"probe54_{int(time.time())}"                    # unique throwaway study prefix
    print(f"[baseline] tf={args.tf} inst={args.instrument} trials={args.trials} folds={args.folds} "
          f"min_trades={args.min_trades} registry={len(library.SCHEMA)} ind_1min=True prefix={prefix}",
          flush=True)

    probe = Probe().install()
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(args.heartbeat):
            s = probe.snapshot()
            print(f"[hb {time.strftime('%H:%M:%S')}] cold_computes={s['cold_computes']} "
                  f"cold_s={s['cold_seconds']:.1f} hits={s['hits']} misses={s['misses']} "
                  f"hit_rate={s['hit_rate']:.2f}", flush=True)

    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()

    t0 = time.time()
    result = optimizer.run(args.tf, n_trials=args.trials, folds=args.folds,
                           min_trades=args.min_trades, ind_1min=True,
                           study_prefix=prefix, warm_start=False, instrument=args.instrument)
    wall = time.time() - t0
    stop.set()
    probe.uninstall()

    snap = probe.snapshot()
    out = {
        "tf": args.tf, "instrument": args.instrument, "trials": args.trials,
        "folds": args.folds, "min_trades": args.min_trades,
        "registry_size": len(library.SCHEMA), "ind_1min": True,
        "wall_seconds": round(wall, 2),
        "cold_seconds": snap["cold_seconds"], "cold_computes": snap["cold_computes"],
        "cold_frac_of_wall": round(snap["cold_seconds"] / wall, 4) if wall else None,
        "hits": snap["hits"], "misses": snap["misses"], "hit_rate": snap["hit_rate"],
        "bytes_read": snap["bytes_read"], "bytes_written": snap["bytes_written"],
        "per_indicator": snap["per_indicator"],
        "optimizer_result": result,
    }
    outp = Path(args.out) if args.out else (
        Path(__file__).resolve().parent / "results" / f"baseline_{args.instrument}_{args.tf}.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2))
    cold_pct = (100 * snap["cold_seconds"] / wall) if wall else 0.0
    print(f"[baseline] DONE wall={wall:.0f}s cold={snap['cold_seconds']:.0f}s ({cold_pct:.0f}% of wall) "
          f"hit_rate={snap['hit_rate']:.2f} cold_computes={snap['cold_computes']} -> {outp}", flush=True)
    top = list(out["per_indicator"].items())[:12]
    print("[baseline] top cold-cost indicators:", flush=True)
    for k, v in top:
        print(f"    {k:24s} computes={v['computes']:5d} cold_s={v['cold_seconds']:.2f}", flush=True)

    shutil.rmtree(tmp, ignore_errors=True)                    # drop the throwaway store
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
