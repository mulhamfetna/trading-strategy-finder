"""Issue #74 — measure the four cross-series indicators, which every cost scan has been blind to.

`bench_worstcase.py` builds a single-instrument context, so `rolling_corr` / `rolling_beta` /
`cointegration` / `pca_factor` find `ctx.ref_close is None`, return all-zero votes immediately, and are
reported at **0.00 s**. That is "never ran", not "cheap".

Before optimizing anything, establish what is actually true. Three questions, three answers:

  Q1  WIRING   — with a reference configured, do they emit a non-zero vote on the PRODUCTION
                 `--ind-1min` path? (`runner.indicator_source_1min` builds `market_context(df1)` with
                 no `ref_df` argument at any call site in the repo — so the prediction is NO.)
  Q2  CONTROL  — do they emit votes on the decision-TF path with the SAME reference? If Q2 says yes and
                 Q1 says no, the 1-minute path is broken, and Q1's "no" is not a property of the data.
  Q3  COST     — what would they cost on the 1-minute frame if they WERE wired: defaults, all-min,
                 all-max, projected to the full 486,969-bar frame against the standing 2 s budget.

Q3 is the number issue #74 asked for; Q1/Q2 exist because a cost question is meaningless if the thing
never runs. Run:

  WSH_DATA_BASE=/home/dev/Mulham/wsg-i /home/dev/Mulham/.venv/bin/python3 \
      -m optimize.perf.probe_xseries --tf 4h --instrument NQ --reference ES
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from indicators import library
from indicators.runner import box_direction_int, market_context
from indicators import runner
from optimize import data as data_mod
from optimize import timeframes as TF

FULL_BARS = 486_969
XS_KEYS = ("rolling_corr", "rolling_beta", "cointegration", "pca_factor")


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout()


def _specs(keys):
    out = []
    for k in keys:
        spec = library.SCHEMA[k]
        out.append({"key": k, "enabled": True, "mode": spec["mode"],
                    "params": {p["name"]: p["default"] for p in spec.get("params", [])}})
    return out


def _param_sets(key):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--reference", default="ES")
    ap.add_argument("--bars", type=int, default=20000, help="1-minute subset for the cost scan")
    ap.add_argument("--timeout", type=int, default=120, help="per-config seconds before giving up")
    ap.add_argument("--budget-s", type=float, default=2.0)
    ap.add_argument("--out", default="optimize/perf/results/xseries_probe.json")
    args = ap.parse_args()

    def log(m):
        print(m, flush=True)

    tf = TF.get(args.tf)
    log(f"[xseries] loading {args.instrument} {args.tf} + reference {args.reference} ...")
    df_dec, df1, box, _vf, _n = data_mod.load_inputs(args.tf, args.instrument)
    ref_dec, ref_1m, *_ = data_mod.load_inputs(args.tf, args.reference)
    log(f"[xseries] primary: {len(df_dec):,} decision bars / {len(df1):,} 1-minute bars | "
        f"reference: {len(ref_dec):,} / {len(ref_1m):,}")

    inds = library.from_specs(_specs(XS_KEYS))
    res = {"tf": args.tf, "instrument": args.instrument, "reference": args.reference,
           "decision_bars": len(df_dec), "minute_bars": len(df1)}

    # ---- Q2 (control first): the decision-TF path, reference attached -----------------------------
    log("\n[xseries] Q2 CONTROL — decision-TF path with the reference attached")
    votes_dec = runner.compute_votes(df_dec, box, inds, src=None, ref_df=ref_dec)
    q2 = {}
    for ind in inds:
        v = np.asarray(votes_dec[id(ind)])
        q2[ind.key] = {"nonzero_votes": int(np.count_nonzero(v)), "bars": int(v.size)}
        log(f"    {ind.key:16s} non-zero votes = {q2[ind.key]['nonzero_votes']:>6d} / {v.size}")
    res["q2_decision_tf"] = q2

    # ---- Q1: the PRODUCTION 1-minute path, same reference -----------------------------------------
    log("\n[xseries] Q1 WIRING — production --ind-1min path, SAME reference")
    src = runner.indicator_source_1min(df_dec, df1, tf.bar_td)
    ctx_1m, _j = src
    log(f"    ctx_1min.ref_close is {'None  <-- no reference reaches the 1-minute context' if ctx_1m.ref_close is None else 'PRESENT'}")
    votes_1m = runner.compute_votes(df_dec, box, inds, src=src, ref_df=ref_dec)
    q1 = {}
    for ind in inds:
        v = np.asarray(votes_1m[id(ind)])
        q1[ind.key] = {"nonzero_votes": int(np.count_nonzero(v)), "bars": int(v.size)}
        log(f"    {ind.key:16s} non-zero votes = {q1[ind.key]['nonzero_votes']:>6d} / {v.size}")
    res["q1_onemin_path"] = q1
    res["ref_reaches_1min_context"] = ctx_1m.ref_close is not None
    res["inert_in_production"] = all(q1[k]["nonzero_votes"] == 0 for k in q1) and \
        any(q2[k]["nonzero_votes"] > 0 for k in q2)
    log(f"\n[xseries] VERDICT: cross-series indicators are "
        f"{'INERT on the production 1-minute path while ALIVE on the decision-TF path' if res['inert_in_production'] else 'behaving consistently across both paths'}")

    # ---- Q3: what they would cost on the 1-minute frame if wired ----------------------------------
    log(f"\n[xseries] Q3 COST — 1-minute frame, reference attached, {args.bars:,}-bar subset "
        f"(×{FULL_BARS / args.bars:.1f} to the full frame), budget {args.budget_s}s")
    sub, ref_sub = df1.iloc[: args.bars], ref_1m
    ctx_ref = market_context(sub, ref_sub)
    assert ctx_ref.ref_close is not None and np.isfinite(ctx_ref.ref_close).any(), \
        "the cost scan needs a live reference — otherwise it measures the same 0.00s blind spot"
    scale = FULL_BARS / args.bars
    rows = []
    for key in XS_KEYS:
        best = {"key": key, "worst_config": None, "subset_s": -1.0, "notes": {}}
        for label, params in _param_sets(key):
            ind = library.from_specs([{"key": key, "enabled": True,
                                       "mode": library.SCHEMA[key]["mode"], "params": params}])[0]
            signal.signal(signal.SIGALRM, _alarm)
            signal.alarm(args.timeout)
            try:
                ind.directions(ctx_ref)                       # warm-up, NOT timed
                t0 = time.perf_counter()
                cdir, vdir = ind.directions(ctx_ref)
                secs = time.perf_counter() - t0
                nz = int(np.count_nonzero(np.asarray(cdir)) + np.count_nonzero(np.asarray(vdir)))
                if nz == 0:
                    best["notes"][label] = "EMITTED NOTHING — the reference is not reaching it"
                if secs > best["subset_s"]:
                    best.update(worst_config=label, subset_s=secs)
            except _Timeout:
                best["notes"][label] = f"TIMEOUT>{args.timeout}s"
                best.update(worst_config=label, subset_s=float(args.timeout))
            except Exception as e:                            # noqa: BLE001
                best["notes"][label] = f"{type(e).__name__}: {e}"
            finally:
                signal.alarm(0)
        best["projected_full_s"] = round(best["subset_s"] * scale, 2) if best["subset_s"] >= 0 else None
        best["over_budget"] = bool(best["projected_full_s"] and best["projected_full_s"] > args.budget_s)
        best["subset_s"] = round(best["subset_s"], 4)
        rows.append(best)
        flag = "  <-- OVER BUDGET" if best["over_budget"] else ""
        log(f"    {key:16s} worst={str(best['worst_config']):8s} "
            f"proj_full={best['projected_full_s']:9.2f}s{flag}  {best['notes'] or ''}")
    res["q3_cost"] = rows

    # ---- Q4: parity on the FULL frame, with the reference attached --------------------------------
    # ⚠️ This deliberately rebuilds the context on the WHOLE 1-minute frame rather than reusing the
    # cost scan's subset. The first version reused `ctx_ref` (20,000 bars) while the log claimed "the
    # real 1-minute frame": it reported `pca_factor` drift 3e-14 and 0 flips. On the full frame the
    # same build showed drift **0.156** and **3 flipped stances**. A parity claim is only as big as the
    # data it ran on — never let a cost subset leak into a correctness gate.
    log("\n[xseries] Q4 PARITY — accelerated vs reference on the FULL 1-minute frame, reference attached")
    from indicators.calc import xseries as XS
    ctx_full = market_context(df1, ref_1m)
    c1 = np.ascontiguousarray(np.asarray(ctx_full.close, float))
    r1 = np.ascontiguousarray(np.asarray(ctx_full.ref_close, float))
    log(f"    parity frame = {len(c1):,} bars (cost scan used {args.bars:,} — not reused here)")
    par = []

    def _cmp(tag, fast, ref, sign_vote=False):
        fast, ref = np.asarray(fast, float), np.asarray(ref, float)
        nan_ok = bool(np.array_equal(np.isnan(fast), np.isnan(ref)))
        d = np.abs(fast - ref)
        d = d[np.isfinite(d)]
        row = {"case": tag, "nan_mask_ok": nan_ok, "n_differing": int((d > 0).sum()),
               "max_abs_diff": float(d.max()) if d.size else 0.0}
        row["bit_identical"] = bool(nan_ok and row["n_differing"] == 0)
        if sign_vote:
            m = np.isfinite(fast) & np.isfinite(ref)
            row["sign_flips"] = int(np.sum(np.sign(fast[m]) != np.sign(ref[m])))
            a = np.abs(ref[m])
            # `min |margin|` alone is a bad summary: one degenerate bar sitting at exactly 0 drags it
            # to ~0 and hides that everything else is far away. Report BOTH — how many bars are
            # genuinely within reach of the drift, and how many are exactly zero (arbitrary in EITHER
            # implementation, so not evidence of a defect).
            row["bars_within_drift"] = int(np.sum(a <= row["max_abs_diff"]))
            row["bars_exactly_zero"] = int(np.sum(a == 0))
            live = a[a > 0]
            row["min_nonzero_margin"] = float(live.min()) if live.size else None
            row["safety_factor"] = (row["min_nonzero_margin"] / row["max_abs_diff"]
                                    if row["min_nonzero_margin"] and row["max_abs_diff"] > 0 else None)
        par.append(row)
        extra = ""
        if sign_vote:
            extra = (f"  sign_flips={row['sign_flips']}"
                     f"  within_drift={row['bars_within_drift']} (exact_zero={row['bars_exactly_zero']})"
                     f"  min_nonzero_margin={row['min_nonzero_margin']:.3e}")
        log(f"    {tag:30s} bit_identical={row['bit_identical']!s:5s} differing={row['n_differing']:>7d} "
            f"max|Δ|={row['max_abs_diff']:.3e}{extra}")

    for n in (5, 8, 20, 50, 300):               # n=5 is the grid MINIMUM and the degenerate case
        _cmp(f"rolling_corr n={n}", XS.rolling_corr(c1, r1, n), XS.rolling_corr_reference(c1, r1, n))
        _cmp(f"rolling_beta n={n}", XS.rolling_beta(c1, r1, n), XS.rolling_beta_reference(c1, r1, n))
        _cmp(f"spread_zscore n={n}", XS.spread_zscore(c1, r1, n), XS.spread_zscore_reference(c1, r1, n))
        _cmp(f"pca_factor n={n}", XS.pca_factor(c1, r1, n), XS.pca_factor_reference(c1, r1, n),
             sign_vote=True)
    res["q4_parity"] = par
    res["q4_all_bit_identical_except_pca"] = all(
        p["bit_identical"] for p in par if not p["case"].startswith("pca_factor"))
    res["q4_pca_sign_flips"] = sum(p.get("sign_flips", 0) for p in par)
    log(f"[xseries] non-PCA all bit-identical: {res['q4_all_bit_identical_except_pca']} | "
        f"pca_factor stance flips: {res['q4_pca_sign_flips']}")
    res["n_over_budget"] = sum(r["over_budget"] for r in rows)
    res["total_projected_s"] = round(sum(r["projected_full_s"] or 0 for r in rows), 1)
    log(f"\n[xseries] {res['n_over_budget']}/4 over the {args.budget_s}s budget; "
        f"{res['total_projected_s']}s for the four together")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    log(f"[xseries] WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
