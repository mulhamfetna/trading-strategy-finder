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

    PROG       periodic progress + throughput + ETA, every --report-min minutes
    STALL      log has not grown for --stall-min minutes while the process is still alive
    DIED       process is gone and the done-pattern never appeared
    ERROR      an error signature appeared in the log
    DONE       the done-pattern appeared

⚠️ THE ETA USES A RECENT-WINDOW RATE, NOT THE AVERAGE SINCE START. These jobs are not uniform: the
first stretch flies through cached items and then drops to network speed. An average-since-start ETA
would be wildly optimistic exactly when the job is at its slowest, which is the moment an estimate is
actually wanted. The rate is measured over the trailing --rate-window-min minutes instead.

⚠️ SILENCE IS NOT SUCCESS. This watcher deliberately reports failure states as loudly as success. A
watcher that only greps for the happy path stays quiet through a crashloop, and quiet is exactly what
a healthy run looks like.

⚠️ GET THE PID FROM `$!`, NOT FROM `pgrep -f ... | head -1`.
A launch like `nohup env VAR=x python script.py &` creates MORE THAN ONE matching process (the `env`
wrapper and the interpreter). `pgrep -f | head -1` can return the wrapper, which exits immediately —
and this watcher then correctly reports DIED for a job that is running perfectly well. A false DIED is
almost as costly as a missed one, because it invites you to kill and restart healthy work. Capture
`$!` at launch, or confirm with `pgrep -af <script>` that the PID you took is the interpreter.

    python3 optimize/earnings/watch_run.py --pid 88422 --log /tmp/ws-legacy18/classify16y.log \
        --done "wrote ->" --stall-min 10
"""
from __future__ import annotations

import argparse
import os
import re
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

ERROR_PAT = re.compile(r"Traceback|MemoryError|Killed|OOM|Errno|HTTPError|Too Many Requests|"
                       r"refus|denied|FATAL", re.I)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _fmt(mins: float) -> str:
    if mins < 1:
        return "<1m"
    if mins < 90:
        return f"{mins:.0f}m"
    return f"{mins/60:.1f}h"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--done", default="wrote ->", help="substring that means the job finished cleanly")
    ap.add_argument("--stall-min", type=float, default=10.0,
                    help="minutes of no log growth before calling it stalled")
    ap.add_argument("--poll-s", type=float, default=60.0)
    ap.add_argument("--label", default="run")
    ap.add_argument("--progress-re", default=r"(\d+)\s*/\s*(\d+)",
                    help="regex with 2 groups (done, total); the LAST match in the log tail is used")
    ap.add_argument("--report-min", type=float, default=10.0, help="minutes between PROG lines")
    ap.add_argument("--rate-window-min", type=float, default=15.0,
                    help="trailing window used to measure throughput for the ETA")
    ap.add_argument("--unit", default="items")
    a = ap.parse_args()

    log = Path(a.log)
    last_size, last_change = -1, time.monotonic()
    reported_stall = False
    prog_re = re.compile(a.progress_re)
    samples: deque[tuple[float, int]] = deque()          # (monotonic seconds, position)
    started = time.monotonic()
    next_report = started + a.report_min * 60

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

        # Track position for throughput. The LAST match in the tail is the current position.
        now = time.monotonic()
        hits = prog_re.findall(text_tail)
        pos = total = None
        if hits:
            try:
                pos, total = int(hits[-1][0]), int(hits[-1][1])
            except (ValueError, IndexError):
                pos = total = None
        if pos is not None:
            if not samples or samples[-1][1] != pos:
                samples.append((now, pos))
            while samples and now - samples[0][0] > a.rate_window_min * 60:
                samples.popleft()

        # Non-terminal but actionable: alive yet frozen.
        idle_min = (now - last_change) / 60.0
        if idle_min >= a.stall_min and not reported_stall:
            extra = f" at {pos}/{total}" if pos is not None else ""
            print(f"STALL [{a.label}] pid {a.pid} ALIVE but log frozen for {idle_min:.0f} min{extra} "
                  f"— likely a hung socket, not slow progress", flush=True)
            reported_stall = True                            # report once per stall, not every poll

        # Periodic progress + ETA.
        if now >= next_report:
            next_report = now + a.report_min * 60
            elapsed = (now - started) / 60.0
            if pos is not None and total:
                pct = 100.0 * pos / total
                # Rate over the TRAILING window, not since start — see the module docstring.
                if len(samples) >= 2:
                    dt = (samples[-1][0] - samples[0][0]) / 60.0
                    dn = samples[-1][1] - samples[0][1]
                    rate = dn / dt if dt > 0 else 0.0
                else:
                    rate = 0.0
                if rate > 0:
                    eta_min = (total - pos) / rate
                    finish = (datetime.now() + timedelta(minutes=eta_min)).strftime("%H:%M")
                    print(f"PROG  [{a.label}] {pos:,}/{total:,} {a.unit} ({pct:.0f}%) · "
                          f"{rate:.1f}/min · elapsed {_fmt(elapsed)} · "
                          f"ETA {_fmt(eta_min)} (~{finish})", flush=True)
                else:
                    print(f"PROG  [{a.label}] {pos:,}/{total:,} {a.unit} ({pct:.0f}%) · "
                          f"rate not yet measurable · elapsed {_fmt(elapsed)}", flush=True)
            else:
                print(f"PROG  [{a.label}] alive, no position parsed from the log "
                      f"({size:,} bytes) · elapsed {_fmt(elapsed)}", flush=True)

        time.sleep(a.poll_s)


if __name__ == "__main__":
    raise SystemExit(main())
