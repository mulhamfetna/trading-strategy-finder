"""Phase 0 — benchmark harness (task #210). Times a full backtest per champion timeframe and appends
a labelled record to perf/bench_history.json so every optimization step has a recorded before/after.

Run:  python3 perf/bench.py <label> [tf ...]      e.g.  python3 perf/bench.py baseline
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from _common import TFS, load_bundle   # noqa: E402

_HERE = Path(__file__).resolve().parent
_HIST = _HERE / "bench_history.json"
sys.path.insert(0, str(_HERE.parent))
import strategy  # noqa: E402


def time_tf(tf: str, repeats: int = 2) -> float:
    df_dec, df1, box, vf, n2025, preset = load_bundle(tf)
    strategy.build_payload(df_dec, df1, box, vf, n2025, preset)        # warm
    best = min(_run(df_dec, df1, box, vf, n2025, preset) for _ in range(repeats))
    return best


def _run(*args) -> float:
    t = time.time(); strategy.build_payload(*args); return time.time() - t


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 perf/bench.py <label> [tf ...]"); return 2
    label = sys.argv[1]
    tfs = sys.argv[2:] or TFS
    print(f"benchmarking [{label}]: {tfs}", flush=True)
    res = {}
    for tf in tfs:
        dt = time_tf(tf)
        res[tf] = round(dt, 3)
        print(f"  [{tf}] {dt:7.3f}s", flush=True)
    hist = json.loads(_HIST.read_text()) if _HIST.exists() else []
    # NOTE: timestamps are added by the caller's shell if desired; Date.now() is unavailable here.
    hist.append({"label": label, "seconds": res, "total": round(sum(res.values()), 3)})
    _HIST.write_text(json.dumps(hist, indent=1))
    print(f"  total {sum(res.values()):.3f}s  -> appended to {_HIST.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
