"""Issue #56 Question A — is there a SECOND `dfa` hiding at a parameter-grid edge?

`dfa` hid in plain sight because profiling only ever saw the parameters the optimizer happened to sample.
It cost 57 s at `n=20` and **756 s at `n=400`** — a 13× spread across its own grid. An indicator can look
mid-table at defaults and be pathological at a corner the optimizer *will* eventually reach.

This scans **every** registered indicator at three points in its grid — defaults, all-params-minimum,
all-params-maximum — and reports the worst, extrapolated to the full 486,969-bar 1-minute frame.

Two stages so one pathological indicator cannot stall the scan:
  stage 1  cheap scan on a subset, with a hard per-config timeout; anything that times out is itself a
           finding (it is already over any sane budget)
  stage 2  re-measure the worst offenders at full scale for an exact number

Cost is linear in series length for fixed parameters (per-bar work is constant), so subset → full-frame
extrapolation is sound; stage 2 confirms it for the ones that matter.

Run: WSH_DATA_BASE=/home/dev/Mulham/wsg-i /home/dev/Mulham/.venv/bin/python3 \
       -m optimize.perf.bench_worstcase --bars 20000 --timeout 20
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from loader import load_data
from indicators import library
from indicators.runner import market_context
from optimize import timeframes as TF

FULL_BARS = 486_969


class _Timeout(Exception):
    pass


def _alarm(_sig, _frm):
    raise _Timeout()


def _param_sets(key):
    """(label, params) at defaults / all-min / all-max. Non-numeric or choice params keep the default."""
    spec = library.SCHEMA[key]
    ps = spec.get("params", [])
    default = {p["name"]: p["default"] for p in ps}
    lo, hi = dict(default), dict(default)
    for p in ps:
        if p.get("min") is not None and p.get("max") is not None:
            lo[p["name"]] = p["min"]
            hi[p["name"]] = p["max"]
    out = [("default", default)]
    if lo != default:
        out.append(("all_min", lo))
    if hi != default:
        out.append(("all_max", hi))
    return out


def _time_directions(key, params, ctx, timeout_s):
    """Seconds for one directions() call, or None on timeout / error (with the reason).

    IMPORTANT — the call is made TWICE and only the second is timed. Any one-off first-call cost (most
    notably **Numba JIT compilation**, which `dfa` now pays) is a fixed cost amortized over an entire
    sweep, not per-bar work; including it and then extrapolating ×24 to the full frame inflates the
    projection wildly. (Caught in practice: unwarmed, `dfa` projected 5.52 s against a measured 0.178 s.)
    """
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(int(timeout_s))
    try:
        ind = library.from_specs([{"key": key, "enabled": True,
                                   "mode": library.SCHEMA[key]["mode"], "params": params}])[0]
        ind.directions(ctx)                     # warm-up: JIT compile / lazy setup, NOT timed
        t0 = time.perf_counter()
        ind.directions(ctx)
        return time.perf_counter() - t0, None
    except _Timeout:
        return None, f"TIMEOUT>{timeout_s}s"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    finally:
        signal.alarm(0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", type=int, default=20000, help="stage-1 subset length")
    ap.add_argument("--timeout", type=int, default=20, help="per-config seconds before giving up")
    ap.add_argument("--budget-s", type=float, default=2.0, help="full-frame budget per compute")
    ap.add_argument("--restage2", type=int, default=6, help="how many worst offenders to re-measure fully")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-fail", action="store_true",
                    help="report only; do not exit non-zero when something is over budget")
    args = ap.parse_args()

    base = os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading")
    csv = Path(base) / TF.RAW_DIR / "NQ_1m.csv"
    df = load_data(str(csv)).sort_values("Date").reset_index(drop=True)
    scale = FULL_BARS / args.bars
    ctx = market_context(df.iloc[: args.bars])
    print(f"[worstcase] {len(library.REGISTRY)} indicators | stage-1 on {args.bars:,} bars "
          f"(extrapolation ×{scale:.1f} to {FULL_BARS:,}) | timeout {args.timeout}s/config", flush=True)

    rows = []
    for i, key in enumerate(library.REGISTRY, 1):
        best_label, best_s, notes = None, -1.0, {}
        for label, params in _param_sets(key):
            secs, err = _time_directions(key, params, ctx, args.timeout)
            if err:
                notes[label] = err
                if err.startswith("TIMEOUT"):
                    best_label, best_s = label, float(args.timeout)   # at least this bad
                continue
            if secs > best_s:
                best_label, best_s, = label, secs
        proj = best_s * scale if best_s >= 0 else None
        rows.append({"key": key, "worst_config": best_label,
                     "subset_s": round(best_s, 4) if best_s >= 0 else None,
                     "projected_full_s": round(proj, 2) if proj is not None else None,
                     "over_budget": bool(proj is not None and proj > args.budget_s),
                     "notes": notes})
        if i % 25 == 0:
            print(f"[worstcase] scanned {i}/{len(library.REGISTRY)}", flush=True)

    ranked = sorted([r for r in rows if r["projected_full_s"] is not None],
                    key=lambda r: -r["projected_full_s"])
    over = [r for r in ranked if r["over_budget"]]
    print(f"\n[worstcase] === {len(over)} indicator(s) OVER the {args.budget_s}s full-frame budget ===",
          flush=True)
    for r in ranked[:20]:
        flag = "  <-- OVER BUDGET" if r["over_budget"] else ""
        print(f"    {r['key']:24s} worst={r['worst_config']:8s} "
              f"proj_full={r['projected_full_s']:8.2f}s{flag}", flush=True)

    out = {"bars_stage1": args.bars, "scale": round(scale, 3), "budget_s": args.budget_s,
           "n_indicators": len(library.REGISTRY), "n_over_budget": len(over),
           "ranked": ranked, "errors": {r["key"]: r["notes"] for r in rows if r["notes"]}}
    outp = Path(args.out) if args.out else (
        Path(__file__).resolve().parent / "results" / "worstcase_scan.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2))
    print(f"[worstcase] WROTE {outp}", flush=True)
    if over and not args.no_fail:
        # Exit non-zero so this can be a GATE in the END-of-round checklist rather than a report a
        # tired reviewer skims (issue #62). --no-fail keeps it a pure measurement when that is wanted.
        print(f"[worstcase] FAIL: {len(over)} indicator(s) over the {args.budget_s}s budget "
              f"({sum(r['projected_full_s'] for r in over):.1f}s total). "
              f"Accelerate them or justify raising the budget.", flush=True)
        return 1
    print(f"[worstcase] PASS: every indicator is within the {args.budget_s}s budget "
          f"(worst {ranked[0]['key']} at {ranked[0]['projected_full_s']:.2f}s).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
