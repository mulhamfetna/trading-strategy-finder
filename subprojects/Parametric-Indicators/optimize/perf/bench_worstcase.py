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
import roots                                 # the ONE resolver for repo/data roots (#94)

from loader import load_data
import provenance                            # every artifact says what produced it (#94)
from indicators import library
from indicators.runner import market_context
from optimize import timeframes as TF

FULL_BARS = 486_969
_XS_KEYS = ("rolling_corr", "rolling_beta", "cointegration", "pca_factor")


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


def _time_directions_and_check(key, params, ctx, timeout_s):
    """(seconds, error, emitted_anything). `emitted_anything` is False when the indicator returned an
    all-zero vote — which for a cross-series indicator on a reference-free context means it SHORT-
    CIRCUITED rather than ran, and its 0.00 s is meaningless (issue #74)."""
    secs, err = _time_directions(key, params, ctx, timeout_s)
    if err is not None:
        return secs, err, None
    ind = library.from_specs([{"key": key, "enabled": True,
                               "mode": library.SCHEMA[key]["mode"], "params": params}])[0]
    cdir, vdir = ind.directions(ctx)
    emitted = bool(np.count_nonzero(np.asarray(cdir)) or np.count_nonzero(np.asarray(vdir)))
    return secs, None, emitted


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
    ap.add_argument("--reference", default=None,
                    help="reference instrument token (e.g. ES) for the CROSS-SERIES indicators. Without "
                         "it they short-circuit on a missing ref_close and time at 0.00s — a pass that "
                         "means 'never ran', not 'cheap' (issue #74). They are flagged NOT EXERCISED.")
    args = ap.parse_args()

    base = str(roots.DATA_ROOT)                  # never a hardcoded absolute path (#94)
    csv = Path(base) / TF.RAW_DIR / "NQ_1m.csv"
    df = load_data(str(csv)).sort_values("Date").reset_index(drop=True)
    scale = FULL_BARS / args.bars
    ref_df = None
    if args.reference:
        from optimize import instruments
        _dec, ref_min, _box = instruments.resolve_paths(args.reference, "4h")
        ref_df = load_data(ref_min).sort_values("Date").reset_index(drop=True)
    ctx = market_context(df.iloc[: args.bars], ref_df)
    print(f"[worstcase] {len(library.REGISTRY)} indicators | stage-1 on {args.bars:,} bars "
          f"(extrapolation ×{scale:.1f} to {FULL_BARS:,}) | timeout {args.timeout}s/config | "
          f"reference {args.reference or 'NONE — cross-series indicators will be flagged NOT EXERCISED'}",
          flush=True)

    rows = []
    for i, key in enumerate(library.REGISTRY, 1):
        best_label, best_s, notes = None, -1.0, {}
        exercised = False
        for label, params in _param_sets(key):
            secs, err, emitted = _time_directions_and_check(key, params, ctx, args.timeout)
            if err:
                notes[label] = err
                if err.startswith("TIMEOUT"):
                    best_label, best_s = label, float(args.timeout)   # at least this bad
                continue
            exercised = exercised or bool(emitted)
            if secs > best_s:
                best_label, best_s, = label, secs
        proj = best_s * scale if best_s >= 0 else None
        # Two DIFFERENT things, deliberately not conflated (issue #74):
        #   void      the indicator could not run at all — a cross-series key on a context with no
        #             reference short-circuits on `ref_close is None` and returns instantly. Its timing
        #             is not a measurement, and reporting 0.00 s as a pass is how the blind spot formed.
        #   quiet     it DID compute (the time is real) but voted nowhere at any corner. Normal for a
        #             rarely-triggering veto — `proj_bands` is one — and NOT a coverage problem.
        void = key in _XS_KEYS and ref_df is None
        if void:
            notes["_coverage"] = ("NOT EXERCISED — cross-series indicator with no reference; it "
                                  "short-circuited and this timing is not evidence of cost. Pass "
                                  "--reference <token> to measure it.")
        elif not exercised:
            notes["_coverage"] = "quiet — computed, but emitted no vote at any grid corner"
        rows.append({"key": key, "worst_config": best_label,
                     "subset_s": round(best_s, 4) if best_s >= 0 else None,
                     "projected_full_s": round(proj, 2) if proj is not None else None,
                     "over_budget": bool(proj is not None and proj > args.budget_s),
                     "emitted_a_vote": exercised, "measurement_void": void,
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
    out["provenance"] = provenance.snapshot(argv=sys.argv)   # what produced this (#94)
    outp.write_text(json.dumps(out, indent=2))
    print(f"[worstcase] WROTE {outp}", flush=True)
    void = [r["key"] for r in ranked if r.get("measurement_void")]
    quiet = [r["key"] for r in ranked if not r.get("measurement_void") and not r.get("emitted_a_vote")]
    if quiet:
        print(f"\n[worstcase] note: {len(quiet)} indicator(s) computed but voted nowhere at any grid "
              f"corner (normal for a rarely-triggering veto): {', '.join(quiet)}", flush=True)
    out["measurement_void"] = void
    out["quiet_but_measured"] = quiet
    out["provenance"] = provenance.snapshot(argv=sys.argv)   # what produced this (#94)
    outp.write_text(json.dumps(out, indent=2))

    if void:
        # A budget claim that silently excludes indicators is worse than no claim. Fail loudly.
        print(f"\n[worstcase] FAIL: {len(void)} indicator(s) were NOT MEASURED — they short-circuited "
              f"on a missing reference and their 0.00s is meaningless:\n    {', '.join(void)}\n"
              f"[worstcase] Re-run with --reference ES. (issue #74)", flush=True)
        if not args.no_fail:
            return 1

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
