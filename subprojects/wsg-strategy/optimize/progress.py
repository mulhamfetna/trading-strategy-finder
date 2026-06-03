"""Live progress view for the WS-H search — reads the Optuna SQLite studies and prints a per-
timeframe bar (trials done / target) plus the current best front point. Meant to be watched:

  watch -n 5 python3 subprojects/wsg-strategy/optimize/progress.py
  # or one-shot:
  python3 subprojects/wsg-strategy/optimize/progress.py [target]
"""
from __future__ import annotations

import sys
from pathlib import Path

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)
_DB = Path(__file__).resolve().parent / "studies" / "wsh.db"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m", "1m"]


def main(target: int = 1200) -> int:
    if not _DB.exists():
        print("no studies yet (studies/wsh.db missing)"); return 0
    storage = f"sqlite:///{_DB}"
    summaries = {s.study_name: s for s in optuna.get_all_study_summaries(storage=storage)}
    total_done = 0
    print(f"WS-H search progress  (target {target} trials/TF)\n")
    print(f"{'TF':>4} {'trials':>12}  {'progress':<22} {'best P/L @ DD':>22}")
    for tf in TFS:
        s = summaries.get(f"wsh_{tf}")
        n = s.n_trials if s else 0
        total_done += n
        pct = min(100, int(100 * n / target))
        bar = "█" * (pct * 20 // 100) + "·" * (20 - pct * 20 // 100)
        best = ""
        if s and s.n_trials:
            try:
                st = optuna.load_study(study_name=f"wsh_{tf}", storage=storage)
                front = [t for t in st.best_trials if t.values]
                if front:
                    bp = max(front, key=lambda t: t.values[0])
                    best = f"${bp.values[0]:>8,.0f} @ ${-bp.values[1]:>7,.0f}"
            except Exception:
                pass
        print(f"{tf:>4} {n:>6}/{target:<5} [{bar}] {pct:>3}%  {best:>22}")
    print(f"\ntotal trials so far: {total_done} / {target*len(TFS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1200))
