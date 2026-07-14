"""WATCHDOG — a live monitor for long runs that catches SILENT failures.

WHY THIS EXISTS. Every failure we hit today was silent. Not one of them crashed:

  1. An rsync overwrote the calendar. A study then ran on 122 releases instead of 871 and produced a
     perfectly reasonable-looking answer. NOTHING COMPLAINED.
  2. A 10-minute run wrote an EMPTY log, because Python buffers stdout when it is redirected to a file.
     Indistinguishable from a hang. I had no idea whether it was working, stuck, or dying.
  3. A benchmark reported a +74% regression that was pure noise from another process saturating the box.
  4. A drift test silently ran on 70 trades instead of 235 because it used the wrong gate.

**A job that fails loudly is a nuisance. A job that succeeds WRONGLY is a disaster.** This watchdog is
built to catch the second kind.

WHAT IT CHECKS, on a poll loop:

  DEAD        the process is gone but the log has no completion marker
  STALLED     the log has not grown in --stall-secs (the classic silent hang)
  ERRORS      exceptions / tracebacks / HTTP failures accumulating in the log
  WRONG-SIZE  the run reports a sample size far below what the calendar implies
              (this is the #1 check — it is the failure that nearly published a wrong answer)
  SLOW        the ETA has blown far past the original estimate

AND IT REPORTS: progress, rate, ETA, elapsed — every poll, so a long run is never a blind wait.

  python3 optimize/fundamentals/watchdog.py --log run.log --pattern study_surprise --expect-min 800
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# What "finished cleanly" looks like. If the process dies without one of these, it died silently.
DONE_MARKERS = ["VERDICT", "does the SURPRISE differ", "ALL GOLDEN", "OK ✓", "passed", "=== done ==="]
FAIL_MARKERS = ["Traceback", "MemoryError", "Killed", "Segmentation fault", "AssertionError"]


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout
    except Exception:                                     # noqa: BLE001
        return ""


def as_int(s: str) -> int:
    """First integer in the output, or 0.

    `grep -c` PRINTS "0" and ALSO exits non-zero when it finds nothing — so a `|| echo 0` fallback
    fires as well and you get "0\\n0", which int() rejects. Parse defensively rather than trust the
    shell to behave.
    """
    for tok in (s or "").split():
        try:
            return int(tok)
        except ValueError:
            continue
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="the log file to watch")
    ap.add_argument("--pattern", default="", help="pgrep pattern for the process (to detect death)")
    ap.add_argument("--host", default="", help="watch on a remote host over ssh (e.g. amd-trading)")
    ap.add_argument("--poll", type=int, default=30, help="seconds between polls")
    ap.add_argument("--stall-secs", type=int, default=180,
                    help="alert if the log has not grown in this many seconds")
    ap.add_argument("--expect-min", type=int, default=0,
                    help="ALERT if the run reports a sample smaller than this "
                         "(catches the silent wrong-sample failure)")
    ap.add_argument("--max-min", type=float, default=60.0, help="alert if it runs longer than this")
    a = ap.parse_args()

    R = (lambda c: sh(f"ssh {a.host} '{c}'")) if a.host else sh
    t0 = time.time()
    last_size, last_growth = -1, time.time()
    alerts: list[str] = []

    print(f"WATCHDOG on {a.log}" + (f" @ {a.host}" if a.host else ""))
    print(f"  polling every {a.poll}s · stall alert at {a.stall_secs}s · "
          f"expect >= {a.expect_min} samples · max {a.max_min:.0f} min\n")

    while True:
        el = time.time() - t0
        size = as_int(R(f"stat -c %s {a.log} 2>/dev/null"))
        alive = bool(R(f"pgrep -f '{a.pattern}' 2>/dev/null").strip()) if a.pattern else True
        tail = R(f"grep -vE '^\\s*!' {a.log} 2>/dev/null | tail -3")
        nerr = as_int(R(f"grep -cE '{'|'.join(FAIL_MARKERS)}' {a.log} 2>/dev/null"))
        nhttp = as_int(R(f"grep -c 'HTTP Error' {a.log} 2>/dev/null"))

        if size != last_size:
            last_size, last_growth = size, time.time()
        quiet = time.time() - last_growth

        # --- the progress line the script itself emits -------------------------------------------
        prog = R(f"grep -oE '\\[fetch\\][^\\n]*' {a.log} 2>/dev/null | tail -1").strip()

        # --- SANITY: does the FINAL reported sample size look right? -------------------------------
        #
        # ⚠️ ONLY the FINAL, AUTHORITATIVE count. Never an intermediate progress line.
        #
        # The first version of this matched ANY line containing "releases" — including the per-series
        # progress lines ("nonfarm_payrolls PAYEMS 196 releases"). It fired 🚨 WRONG-SAMPLE while the run
        # was 26% through fetching, and then EXITED, leaving the job unmonitored.
        #
        # A watchdog that cries wolf is WORSE than no watchdog: it trains you to ignore it. So this only
        # matches the study's own terminal summary line, and nothing else.
        FINAL = r"(\d+)\s+(?:priced\s+)?releases\s+with\s+a\s+causal"
        m = re.search(FINAL, R(f"grep -aE 'releases with a causal' {a.log} 2>/dev/null"))
        n_rep = int(m.group(1)) if m else 0

        status, why = "RUNNING", ""
        if not alive and not any(k in R(f"tail -40 {a.log} 2>/dev/null") for k in DONE_MARKERS):
            status, why = "❌ DEAD", "process gone, no completion marker — it died SILENTLY"
        elif nerr:
            status, why = "❌ ERROR", f"{nerr} traceback/fatal marker(s) in the log"
        elif not alive:
            status = "✅ DONE"
        elif quiet > a.stall_secs:
            status, why = "⚠️ STALLED", f"log has not grown in {quiet:.0f}s"
        elif el / 60 > a.max_min:
            status, why = "⚠️ SLOW", f"running {el/60:.0f} min (expected < {a.max_min:.0f})"

        # THE MOST IMPORTANT CHECK: a run that "succeeds" on the wrong sample.
        # Fires ONLY once the study has printed its final count (n_rep > 0 means the terminal summary
        # line exists). While it is still fetching, n_rep is 0 and this stays silent — as it must.
        if a.expect_min and n_rep and n_rep < a.expect_min:
            status = "🚨 WRONG-SAMPLE"
            why = (f"final count is only {n_rep}, expected >= {a.expect_min}. "
                   f"THE RUN IS PRODUCING A PLAUSIBLE ANSWER FROM THE WRONG DATA.")

        line = (f"[{el/60:>5.1f}m] {status:<15} log={size/1024:>7.1f}KB  quiet={quiet:>4.0f}s  "
                f"errs={nerr}/{nhttp}")
        if n_rep:
            line += f"  n={n_rep}"
        print(line, flush=True)
        if prog:
            print(f"          {prog}", flush=True)
        if why:
            print(f"          ⇒ {why}", flush=True)
            if status.startswith(("❌", "🚨")):
                alerts.append(f"{status}: {why}")

        if status.startswith(("✅", "❌", "🚨")):
            print()
            if tail.strip():
                print("  --- last output ---")
                for l in tail.strip().splitlines():
                    print(f"    {l}")
            print()
            if alerts:
                print("  🚨 ALERTS:")
                for x in alerts:
                    print(f"    {x}")
                return 1
            print("  ✅ finished cleanly.")
            return 0

        time.sleep(a.poll)


if __name__ == "__main__":
    raise SystemExit(main())
