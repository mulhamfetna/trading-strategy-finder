"""Progress watcher, reporter and time estimator for long optimizer runs.

WHY THIS EXISTS. A study runs for hours in a detached process. Until now "how far along is it?" meant
tailing a log and guessing, and "when will it finish?" meant arithmetic done by hand from a rate
nobody had measured. Both of those are how a run gets declared finished, stalled, or lost when it is
none of those things.

WHAT IT REPORTS, per study:
  * trials done / target, and percent
  * the rate, measured over the LAST window rather than since launch — a study that has slowed down
    should show a slower ETA, and an average-since-start hides exactly that
  * completed vs pruned, because a run producing only pruned trials is not making progress even
    though its counter is climbing
  * ETA, and the wall-clock time it implies
  * ALIVE / STALLED / FINISHED, decided from whether the trial count moved since the last check

DELIBERATELY STATELESS BETWEEN CALLS except for one small file: it writes the last (time, count) pair
per study to /tmp so the next call can compute a windowed rate. If that file is missing it says so
rather than silently reporting a since-launch average as if it were current.

Run on the server:
    python3 optimize/server/watch_study.py q99rect_4h q99cond_4h --target 46600
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import storage

STATE = Path("/tmp/.watch_study_state.json")


def _counts(study_name: str, db: str | None = None):
    """(total, completed, pruned) for a study, or None if it cannot be found.

    BACKEND-AWARE ON PURPOSE. A study can live in a per-TF SQLite file, in an explicit SQLite file
    (`--db`, for runs launched with WSH_STORAGE_URL), or in Postgres. The first version of this watcher
    assumed SQLite and crashed the moment the #99 arms moved to Postgres — a monitor that dies when the
    thing it monitors changes shape is not a monitor.

    The trial-state table has the same shape in both backends, so one query serves both.
    """
    SQL_ID = "SELECT study_id FROM studies WHERE study_name = :n"
    SQL_STATES = "SELECT state, COUNT(*) FROM trials WHERE study_id = :s GROUP BY state"

    if db:
        url = f"sqlite:///{db}"
    else:
        hits = storage.find_study(study_name)
        if not hits:
            return None
        h = hits[0]
        loc = h["location"]
        url = loc if "://" in str(loc) else f"sqlite:///{loc}"

    try:
        from sqlalchemy import create_engine, text
        eng = create_engine(url)
        with eng.connect() as con:
            row = con.execute(text(SQL_ID), {"n": study_name}).fetchone()
            if not row:
                return None
            rows = con.execute(text(SQL_STATES), {"s": row[0]}).fetchall()
        eng.dispose()
    except Exception as e:                      # report the reason rather than vanishing
        return ("ERROR", f"{type(e).__name__}: {str(e)[:60]}")

    by = {str(s): n for s, n in rows}
    total = sum(by.values())
    return total, by.get("TrialState.COMPLETE", by.get("COMPLETE", 0)), \
        by.get("TrialState.PRUNED", by.get("PRUNED", 0))


def _fmt_eta(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:
        return "unknown"
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("studies", nargs="+")
    ap.add_argument("--target", type=int, required=True, help="target trials per study")
    ap.add_argument("--db", nargs="*", default=None,
                    help="explicit SQLite file per study, in the same order as the study names. Use when "
                         "the run was launched with WSH_STORAGE_URL, which puts the study where "
                         "find_study does not look.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    now = time.time()
    prev = {}
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text())
        except Exception:
            prev = {}

    out, new_state = [], {}
    for i, name in enumerate(args.studies):
        db = args.db[i] if args.db and i < len(args.db) else None
        c = _counts(name, db)
        if c is None:
            out.append({"study": name, "status": f"NOT FOUND{' in ' + db if db else ''}"})
            continue
        if c and c[0] == "ERROR":
            out.append({"study": name, "status": f"ERROR {c[1]}"})
            continue
        total, complete, pruned = c
        new_state[name] = {"t": now, "n": total}
        p = prev.get(name)
        rate = eta = None
        status = "ALIVE"
        if p and now > p["t"]:
            dn, dt = total - p["n"], now - p["t"]
            rate = dn / dt * 60.0                       # trials per minute, over the last window only
            if dn == 0:
                status = "STALLED"
            elif rate > 0:
                eta = (args.target - total) / (rate / 60.0)
        if total >= args.target:
            status = "FINISHED"
        out.append({"study": name, "trials": total, "target": args.target,
                    "pct": round(100.0 * total / args.target, 1),
                    "complete": complete, "pruned": pruned,
                    "rate_per_min": round(rate, 1) if rate else None,
                    "eta": _fmt_eta(eta) if eta else ("—" if status == "FINISHED" else "no window yet"),
                    "status": status})

    STATE.write_text(json.dumps(new_state))

    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"[watch] {time.strftime('%Y-%m-%d %H:%M:%S')}")
    for r in out:
        if str(r.get("status", "")).startswith(("NOT FOUND", "ERROR")):
            print(f"  {r['study']:16s} {r['status']}")
            continue
        # completed vs pruned matters: a counter climbing on pruned trials alone is not progress
        print(f"  {r['study']:16s} {r['trials']:6,d}/{r['target']:,} ({r['pct']:5.1f}%)  "
              f"complete={r['complete']:5,d} pruned={r['pruned']:6,d}  "
              f"rate={str(r['rate_per_min'] or '—'):>6s}/min  ETA {r['eta']:>12s}  {r['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
