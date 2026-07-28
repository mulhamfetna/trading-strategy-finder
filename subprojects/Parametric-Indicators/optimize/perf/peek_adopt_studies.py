"""Issue #14 — peek at the live adopt-gate studies: best-on-train and which indicators it uses.

Answers the question a flat heartbeat raises: has the search actually BEATEN the warm-start champion
seed, or is the front still the seed? The optimizer guarantees the front is >= the prior champion, so a
best-on-train that never moves is not a stall — it may mean 10,000 trials over 165 indicators have not
found anything better than the existing 8.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import optuna


def main() -> int:
    names = sys.argv[1:] or ["adopt14v2treat_4h", "adopt14v2ctrl_4h"]
    storage = os.environ.get("WSH_STORAGE_URL")
    if not storage:
        print("WSH_STORAGE_URL not set — source pg.env first")
        return 2
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    for name in names:
        try:
            st = optuna.load_study(study_name=name, storage=storage)
        except Exception as e:                                   # noqa: BLE001
            print(f"{name}: {type(e).__name__}: {e}")
            continue
        done = [t for t in st.trials if t.values]
        if not done:
            print(f"{name}: {len(st.trials)} trials, none scored yet")
            continue
        best = max(done, key=lambda t: t.values[0])
        keys = [s["key"] for s in best.user_attrs.get("enabled_specs", [])]
        print(f"{name}: {len(st.trials):,} trials | best #{best.number} "
              f"obj0=${best.values[0]:,.0f} DD=${-best.values[1]:,.0f} | k={best.user_attrs.get('k_rule')} "
              f"| indicators {keys}")
        print(f"    (trial #{best.number} — the first 3 trials are the warm-start champion seeds, so a "
              f"best from #0-2 means the search has not beaten the existing champion on train)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
