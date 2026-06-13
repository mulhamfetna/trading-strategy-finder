"""Tier 3 — per-study trial-state stats for observability.

Reports COMPLETE / RUNNING / FAIL / PRUNED / total per study so a contention storm (rising FAIL, dropping
RUNNING) is visible within a poll instead of hours later via log grep. Honours the Tier-1 storage URL via
trial_count's quiet resolver. Two output modes for the launcher:

  python3 optimize/study_stats.py 4h 1h 5m            # human table
  python3 optimize/study_stats.py 4h 1h 5m --json     # one JSON line per poll (for a structured run log)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import optuna  # noqa: E402
from optuna.trial import TrialState  # noqa: E402
from optimize import trial_count  # noqa: E402  (reuse the quiet per-TF/shared URL resolver)


def stats(prefix: str, tf: str) -> dict:
    """{'tf','complete','running','fail','pruned','total'} for `<prefix>_<tf>` (zeros if absent)."""
    name = f"{prefix}_{tf}"
    out = {"tf": tf, "complete": 0, "running": 0, "fail": 0, "pruned": 0, "total": 0}
    try:
        s = optuna.load_study(study_name=name, storage=trial_count._quiet_url(tf, name))
        states = [t.state for t in s.get_trials(deepcopy=False)]
        out.update(complete=states.count(TrialState.COMPLETE), running=states.count(TrialState.RUNNING),
                   fail=states.count(TrialState.FAIL), pruned=states.count(TrialState.PRUNED),
                   total=len(states))
    except Exception:
        pass
    return out


def collect(prefix: str, tfs) -> list:
    return [stats(prefix, tf) for tf in tfs]


if __name__ == "__main__":
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("tfs", nargs="+")
    ap.add_argument("--prefix", default="wsh4")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = collect(a.prefix, a.tfs)
    if a.json:
        print(json.dumps({"prefix": a.prefix, "studies": rows}))
    else:
        for r in rows:
            print(f"  {r['tf']:>4s}  complete={r['complete']:5d}  running={r['running']:3d}  "
                  f"FAIL={r['fail']:3d}  pruned={r['pruned']:5d}  total={r['total']:5d}")
