"""Issue #95 — is the SMC exclusion from the cross-instrument committee still justified?

THE CLAIM UNDER TEST. `optimize/contributor_search.SMC_COMMITTEE_KEYS` withholds six structural
indicators from the contributor committee SEARCH because they "do not vectorise over the long
contributor 1-minute frame": on the 486,954-bar ES frame `ifvg`=58.1s and `breaker`=37.9s alone were
**90% of a 106.4s 18-indicator committee trial** (docs/PERFORMANCE.md §9). `L1_ES_EXCLUDE` adds
`stochastic` and `adx` on the same basis (≈2.2s each).

Issue #62 then rewrote the SMC family as Numba state machines and re-measured on the NQ frame:
`ifvg` 29.90s -> 0.314s (95x), `order_block` 2.82s -> 0.118s (24x). So the rationale describes code
that has since been replaced — but #62 measured NQ, and the exclusion is about the **ES contributor
frame**, reached through a different call path (`_vote_from_1min` over a 1-minute source, sampled at
aligned decision bars). This measures the thing the exclusion actually claims.

WHAT IS MEASURED, and why each part is needed to decide:

  A. per-indicator worst-case cost on the REAL ES 1-minute committee context, at defaults / all-min /
     all-max. Per playbook P4 an indicator can look mid-table at defaults and be pathological at a grid
     edge the optimizer will eventually sample, so defaults alone cannot answer this.

  B. the COMMITTEE TRIAL cost with and without the excluded families. This is the number that decides,
     because the exclusion was never justified per-indicator — it was justified as "90% of a trial".
     A per-indicator win means nothing if the committee is dominated by something else now.

  C. a CONTROL: the same measurement with the accelerator disabled, so the speed-up claim is attributed
     to the acceleration rather than to hardware, warm caches, or a shorter frame (playbook C5).

METHOD NOTES (each one is a rule earned elsewhere in this repo):
  * Every timing calls `directions()` TWICE and times only the second — the first pays Numba JIT
    compilation, a fixed cost amortized over a whole sweep, not per-bar work. Timing the first and then
    extrapolating inflates the projection wildly (bench_worstcase caught `dfa` projecting 5.52s against
    a measured 0.178s).
  * Subset -> full-frame extrapolation is sound because cost is linear in series length for fixed
    parameters, but the headline numbers are re-confirmed at full scale (`--full-confirm`).
  * The bar count is printed next to every verdict. #74's blind spot was a parity claim that quoted the
    full frame while running on a 20,000-bar subset (C17).
  * An indicator that emits no vote at any grid corner is reported as such. A 0.00s "pass" that means
    "never ran" is how the cross-series blind spot formed (#74).

Run (server; ES data lives under wsg-i):
    WSH_DATA_BASE=/home/dev/Mulham/wsg-i /home/dev/Mulham/.venv/bin/python3 \
        -m optimize.perf.bench_smc_committee --bars 40000 --full-confirm
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
import pandas as pd

from indicators import library
from indicators import runner
from loader import load_data
from optimize import contributor_search as CS
from optimize import instruments
from optimize import timeframes as TF

# The families under test, and why each is in the list.
UNDER_TEST = {
    **{k: "SMC_COMMITTEE_KEYS — excluded from every contributor committee search" for k in CS.SMC_COMMITTEE_KEYS},
    "stochastic": "L1_ES_EXCLUDE — excluded from the L1 contributor search only",
    "adx": "L1_ES_EXCLUDE — excluded from the L1 contributor search only",
}


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout()


def _param_sets(key):
    """(label, params) at defaults / all-min / all-max — the worst-case sweep of playbook P4."""
    ps = library.SCHEMA[key].get("params", [])
    default = {p["name"]: p["default"] for p in ps}
    lo, hi = dict(default), dict(default)
    for p in ps:
        if p.get("min") is not None and p.get("max") is not None:
            lo[p["name"]] = p["min"]
            hi[p["name"]] = p["max"]
    return [("default", default), ("all_min", lo), ("all_max", hi)]


def _build(key, params):
    return library.from_specs([{"key": key, "enabled": True,
                                "mode": library.SCHEMA[key]["mode"], "params": params}])[0]


def _time_vote(key, params, ctx1, j, bd, timeout_s):
    """Seconds for ONE committee vote through the production path, warmed.

    Deliberately times `_vote_from_1min` rather than `directions()`: that is what the committee actually
    calls (compute on the 1-minute source, then sample at aligned decision bars). Timing `directions()`
    would measure a function the committee never invokes on this frame.
    """
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(int(timeout_s))
    try:
        ind = _build(key, params)
        v0 = runner._vote_from_1min(ind, ctx1, j, bd)      # warm-up: JIT + lazy setup, NOT timed
        t0 = time.perf_counter()
        runner._vote_from_1min(ind, ctx1, j, bd)
        secs = time.perf_counter() - t0
        return secs, None, bool(np.count_nonzero(np.asarray(v0)))
    except _Timeout:
        return None, f"TIMEOUT>{timeout_s}s", None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", None
    finally:
        signal.alarm(0)


def _committee_cost(keys, ctx1, j, bd, timeout_s):
    """Seconds to compute a whole committee at DEFAULT params — the trial-level number that decides."""
    total, failed = 0.0, []
    for k in keys:
        secs, err, _ = _time_vote(k, {p["name"]: p["default"] for p in library.SCHEMA[k].get("params", [])},
                                  ctx1, j, bd, timeout_s)
        if err:
            failed.append((k, err))
        else:
            total += secs
    return total, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default="ES", help="contributor instrument")
    ap.add_argument("--tf", default="4h", help="decision timeframe the committee is sampled onto")
    ap.add_argument("--bars", type=int, default=40000, help="stage-1 subset of the 1-minute frame")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--full-confirm", action="store_true",
                    help="re-measure the excluded families on the FULL 1-minute frame (the headline)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    dec_csv, min_csv, _box = instruments.resolve_paths(args.token, args.tf)
    df_dec = load_data(dec_csv).sort_values("Date").reset_index(drop=True)
    df1 = load_data(min_csv).sort_values("Date").reset_index(drop=True)
    full_bars = len(df1)
    bar_td = TF.get(args.tf).bar_td

    def _context(n_min):
        """Build the production committee source on the first n_min 1-minute bars."""
        d1 = df1.iloc[:n_min]
        last = d1["Date"].iloc[-1]
        dd = df_dec[df_dec["Date"] <= last].reset_index(drop=True)
        ctx1, j = runner.indicator_source_1min(dd, d1, bar_td)
        bd = np.ones(len(j), dtype=np.int8)          # box_dir: orientation only, not a cost factor
        return ctx1, np.asarray(j, dtype=np.int64), bd, len(dd)

    ctx1, j, bd, n_dec = _context(args.bars)
    scale = full_bars / args.bars
    print(f"[smc] {args.token} committee frame: {full_bars:,} 1-minute bars "
          f"({args.tf} decision bars sampled from it). Stage 1 on {args.bars:,} bars "
          f"-> x{scale:.1f} to full. {n_dec:,} decision bars in the subset.", flush=True)
    print(f"[smc] accelerator: numba {'PRESENT' if _numba_present() else 'ABSENT — control run'}",
          flush=True)

    rows = []
    for key, why in UNDER_TEST.items():
        worst_label, worst_s, notes, emitted_any = None, -1.0, {}, False
        for label, params in _param_sets(key):
            secs, err, emitted = _time_vote(key, params, ctx1, j, bd, args.timeout)
            if err:
                notes[label] = err
                if err.startswith("TIMEOUT"):
                    worst_label, worst_s = label, float(args.timeout)
                continue
            emitted_any = emitted_any or bool(emitted)
            if secs > worst_s:
                worst_label, worst_s = label, secs
        proj = worst_s * scale if worst_s >= 0 else None
        if not emitted_any:
            notes["_coverage"] = "quiet — computed, but emitted no vote at any grid corner"
        rows.append({"key": key, "why_excluded": why, "worst_config": worst_label,
                     "subset_s": round(worst_s, 4) if worst_s >= 0 else None,
                     "projected_full_s": round(proj, 2) if proj is not None else None,
                     "emitted_a_vote": emitted_any, "notes": notes})
        print(f"[smc]   {key:18s} worst={worst_label or '-':8s} "
              f"subset={worst_s:8.4f}s  proj_full={proj if proj is None else round(proj, 2)}s",
              flush=True)

    # --- B. the trial-level number -------------------------------------------------------------
    all_keys = list(library.REGISTRY)
    excluded = set(CS.L1_ES_EXCLUDE)
    kept = [k for k in all_keys if k not in excluded]
    print(f"\n[smc] committee trial cost at DEFAULT params, {args.bars:,}-bar subset:", flush=True)
    t_kept, f_kept = _committee_cost(kept, ctx1, j, bd, args.timeout)
    t_excl, f_excl = _committee_cost(sorted(excluded), ctx1, j, bd, args.timeout)
    print(f"[smc]   committee as searched today ({len(kept)} indicators): "
          f"{t_kept:.2f}s subset -> {t_kept * scale:.1f}s full", flush=True)
    print(f"[smc]   the {len(excluded)} EXCLUDED indicators:              "
          f"{t_excl:.2f}s subset -> {t_excl * scale:.1f}s full", flush=True)
    share = 100.0 * t_excl / (t_kept + t_excl) if (t_kept + t_excl) else 0.0
    print(f"[smc]   admitting them would make the trial {100.0 * t_excl / t_kept:.1f}% more expensive; "
          f"they would be {share:.1f}% of it (the original claim was 90%)", flush=True)

    full = None
    if args.full_confirm:
        print(f"\n[smc] FULL-FRAME confirmation on all {full_bars:,} 1-minute bars "
              f"(the projections above are extrapolations; these are measurements):", flush=True)
        fctx, fj, fbd, fdec = _context(full_bars)
        full = {}
        # ALL THREE grid corners, not just defaults. The first version of this bench measured defaults
        # at full scale and worst-case only on the subset — and the subset extrapolation UNDER-predicted
        # `ifvg` by 3.7x (0.06s projected vs 0.223s measured). An extrapolation that is wrong in the
        # cheap direction is exactly the one you must not lean on when arguing "cheap enough to admit".
        for key in UNDER_TEST:
            per_cfg, worst_label, worst_s = {}, None, -1.0
            for label, params in _param_sets(key):
                secs, err, _ = _time_vote(key, params, fctx, fj, fbd, max(args.timeout, 900))
                per_cfg[label] = {"s": None if err else round(secs, 3), "error": err}
                if err is None and secs > worst_s:
                    worst_label, worst_s = label, secs
            full[key] = {"default_s": per_cfg["default"]["s"], "by_config": per_cfg,
                         "worst_config": worst_label,
                         "worst_s": round(worst_s, 3) if worst_s >= 0 else None}
            print(f"[smc]   {key:18s} default={per_cfg['default']['s']}s  "
                  f"WORST={worst_label}={round(worst_s, 3) if worst_s >= 0 else 'ERR'}s", flush=True)
        tot_worst = sum(v["worst_s"] for v in full.values() if v["worst_s"] is not None)
        print(f"[smc]   --> all {len(full)} excluded indicators at their WORST grid corner, "
              f"measured on the full frame: {tot_worst:.2f}s", flush=True)

    out = {"token": args.token, "tf": args.tf, "full_1min_bars": full_bars,
           "subset_bars": args.bars, "scale": round(scale, 3),
           "numba_present": _numba_present(),
           "per_indicator_worstcase": rows,
           "committee_trial": {"kept_keys": len(kept), "excluded_keys": sorted(excluded),
                               "kept_subset_s": round(t_kept, 3),
                               "excluded_subset_s": round(t_excl, 3),
                               "kept_projected_full_s": round(t_kept * scale, 2),
                               "excluded_projected_full_s": round(t_excl * scale, 2),
                               "excluded_share_pct": round(share, 1),
                               "failures": {"kept": f_kept, "excluded": f_excl}},
           "full_frame_default": full}
    p = Path(args.out) if args.out else (Path(__file__).resolve().parent / "results" / "smc_committee.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    print(f"\n[smc] wrote {p}", flush=True)
    return 0


def _numba_present() -> bool:
    try:
        import numba  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    raise SystemExit(main())
