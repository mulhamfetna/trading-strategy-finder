"""Stale-run watcher — turns a long job's silence into an EVENT instead of a guess.

THE PROBLEM THIS SOLVES

A plain "wait until the process exits" watcher cannot tell these three apart:

    · the job is working normally          (log growing, process alive)
    · the job is HUNG                      (log frozen, process alive)   <-- indistinguishable
    · the job DIED without finishing       (process gone, no done marker)

The middle case is the dangerous one. A network-bound job that stalls on a hung socket looks exactly
like a job that is merely slow, and the only symptom is that nothing happens — forever. This repo has
been bitten by the same shape before: `| head -N` SIGPIPEd a 285-second run mid-A/B and, because the
filter missed stderr, it presented as a silent crash with exit code 0.

WHAT THIS EMITS (one stdout line per event, so a Monitor turns each into a notification)

    STALL      log has not grown for --stall-min minutes while the process is still alive
    DIED       process is gone and the done-pattern never appeared
    ERROR      an error signature appeared in the log
    DONE       the done-pattern appeared

⚠️ SILENCE IS NOT SUCCESS. This watcher deliberately reports failure states as loudly as success. A
watcher that only greps for the happy path stays quiet through a crashloop, and quiet is exactly what
a healthy run looks like.

    python3 optimize/earnings/watch_run.py --pid 88422 --log /tmp/ws-legacy18/classify16y.log \
        --done "wrote ->" --stall-min 10
"""
from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path

ERROR_PAT = re.compile(r"Traceback|MemoryError|Killed|OOM|Errno|HTTPError|Too Many Requests|"
                       r"refus|denied|FATAL", re.I)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--done", default="wrote ->", help="substring that means the job finished cleanly")
    ap.add_argument("--stall-min", type=float, default=10.0,
                    help="minutes of no log growth before calling it stalled")
    ap.add_argument("--poll-s", type=float, default=60.0)
    ap.add_argument("--label", default="run")
    a = ap.parse_args()

    log = Path(a.log)
    last_size, last_change = -1, time.monotonic()
    reported_stall = False

    while True:
        size = log.stat().st_size if log.exists() else 0
        text_tail = ""
        if log.exists():
            with log.open("rb") as fh:                       # cheap tail, no full read
                fh.seek(max(0, size - 4000))
                text_tail = fh.read().decode("utf-8", errors="replace")

        if size != last_size:
            last_size, last_change = size, time.monotonic()
            reported_stall = False

        # Terminal: finished cleanly.
        if a.done in text_tail:
            print(f"DONE  [{a.label}] completion marker seen ({size:,} bytes of log)", flush=True)
            return 0

        # Terminal: an error signature is present.
        m = ERROR_PAT.search(text_tail)
        if m:
            line = next((ln for ln in text_tail.splitlines()[::-1] if ERROR_PAT.search(ln)), "")
            print(f"ERROR [{a.label}] {m.group(0)} — {line.strip()[:160]}", flush=True)
            return 1

        # Terminal: the process vanished without finishing.
        if not alive(a.pid):
            print(f"DIED  [{a.label}] pid {a.pid} gone, no completion marker. "
                  f"last log line: {text_tail.strip().splitlines()[-1][:140] if text_tail.strip() else '(empty)'}",
                  flush=True)
            return 1

        # Non-terminal but actionable: alive yet frozen.
        idle_min = (time.monotonic() - last_change) / 60.0
        if idle_min >= a.stall_min and not reported_stall:
            print(f"STALL [{a.label}] pid {a.pid} ALIVE but log frozen for {idle_min:.0f} min "
                  f"— likely a hung socket, not slow progress", flush=True)
            reported_stall = True                            # report once per stall, not every poll

        time.sleep(a.poll_s)


if __name__ == "__main__":
    raise SystemExit(main())
