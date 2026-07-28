"""Issue #62 evidence harness — every accelerator proven, then timed, on the REAL 1-minute frame.

Three phases, each independently runnable:

  primitives  the shared leaves (`_roll_max`/`_roll_min`, `ema`, `rma`, `nan_ema`) are asserted
              **BIT-IDENTICAL** to their frozen references — these are exact selections and sequential
              recurrences, so nothing weaker is acceptable.
  votes       every accelerated INDICATOR is compared to its reference through the real
              `Indicator.directions()`, so the criterion tested is the one the library actually emits
              rather than a hand-copied restatement of it (a restatement would be a tautology, not a
              gate). Swept across the searched parameter grid; the flip count must be 0.
  timing      per-indicator full-frame wall-clock, warmed, reference vs accelerated.

The reference implementations are slow by construction, so `votes` memoizes the swapped function: a
threshold sweep then costs ONE reference compute and re-runs only the cheap vote layer. Window-like
parameters (integer, wide range) are sampled — always including min / default / max, the corners where
`dfa` hid — and exactly what was swept is recorded in the JSON.

Swapping is done by IDENTITY across every loaded `indicators.*` module, because the leaves are bound
at import time (`from ..classic import _roll_max`); patching only `classic` would silently miss them
and the gate would pass without having tested anything.

Run (server):
  WSH_DATA_BASE=/home/dev/Mulham/wsg-i /home/dev/Mulham/.venv/bin/python3 \
      -m optimize.perf.bench_budget --phases primitives,votes,timing
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from loader import load_data
from indicators import classic, library, smc
from indicators import _reference as REF
from indicators.calc import dsp as DSP, ma as MA, osc as OSC, quant as Q, tier2 as T2, trend as TR, vol as V
from indicators.runner import market_context
from optimize import timeframes as TF


# --------------------------------------------------------------------------------------------------
# shims: smc's fallback paths take a pre-normalised signature; give them the public one so they can be
# swapped in by identity like every other reference.
def _ifvg_reference(high, low, close, signal_at=None):
    n = len(close)
    want = None
    if signal_at is not None:
        want = np.zeros(n, bool)
        idx = np.asarray(signal_at, dtype=np.intp)
        want[idx[(idx >= 0) & (idx < n)]] = True
    return smc._ifvg_py(np.asarray(high, float), np.asarray(low, float), np.asarray(close, float), want)


def _order_blocks_reference(open_, high, low, close, swing_l=2, signal_at=None):
    c = np.asarray(close, float)
    n = len(c)
    want = None
    if signal_at is not None:
        want = np.zeros(n, bool)
        idx = np.asarray(signal_at, dtype=np.intp)
        want[idx[(idx >= 0) & (idx < n)]] = True
    sh, sl = smc.market_structure(c, swing_l)
    return smc._order_blocks_py(np.asarray(open_, float), np.asarray(high, float),
                                np.asarray(low, float), c, sh, sl, int(swing_l), want)


# (registry key, fast function, reference function) — every indicator-level accelerator in #62.
ACCELERATED = [
    ("sinewave",           DSP.hilbert_sinewave,   DSP.hilbert_sinewave_reference),
    ("hilbert_cycle",      DSP.dominant_cycle,     DSP.dominant_cycle_reference),
    ("mama_fama",          DSP.mama_fama,          DSP.mama_fama_reference),
    ("frama",              DSP.frama,              DSP.frama_reference),
    ("schaff_trend_cycle", DSP.schaff_trend_cycle, DSP.schaff_trend_cycle_reference),
    ("ifvg",               smc.ifvg,               _ifvg_reference),
    ("order_block",        smc.order_blocks,       _order_blocks_reference),
    ("proj_bands",         V.proj_bands,           V.proj_bands_reference),
    ("ulcer",              V.ulcer,                V.ulcer_reference),
    ("ou_halflife",        T2.ou_coefficient,      T2.ou_coefficient_reference),
    ("cmo_chande_dmi",     OSC.dynamic_dmi,        OSC.dynamic_dmi_reference),
    ("linreg_channel",     TR.linreg_dev,          TR.linreg_dev_reference),
    ("linreg_slope",       TR.linreg_slope,        TR.linreg_slope_reference),
    ("linreg_r2",          Q.linreg_r2,            Q.linreg_r2_reference),
    ("lsma",               MA.lsma,                MA.lsma_reference),
]

# The shared leaves, and the indicators whose whole cost is those leaves (they carry no private
# accelerator, so they are vote-checked by swapping the LEAVES back to their references).
LEAVES = [
    (classic._roll_max, REF.roll_max_ref),
    (classic._roll_min, REF.roll_min_ref),
    (classic.ema,       REF.ema_ref),
    (classic.rma,       REF.rma_ref),
    (OSC.nan_ema,       OSC.nan_ema_reference),
]
LEAF_DRIVEN = ["ichimoku_cloud", "ichimoku_tk_cross", "chande_kroll", "smi", "chandelier",
               "stoch", "williams_r", "aroon", "donchian", "supertrend"]


# --------------------------------------------------------------------------------------------------
def _indicator_modules():
    return [m for name, m in sys.modules.items()
            if name == "indicators" or name.startswith("indicators.") and m is not None]


@contextmanager
def _swapped(pairs):
    """Replace each `target` with `replacement` at EVERY name in every loaded indicators.* module that
    is currently bound to it (identity match), then restore exactly."""
    saved = []
    for target, replacement in pairs:
        for mod in _indicator_modules():
            for name, val in list(vars(mod).items()):
                if val is target:
                    saved.append((mod, name, val))
                    setattr(mod, name, replacement)
    try:
        yield len(saved)
    finally:
        for mod, name, val in reversed(saved):
            setattr(mod, name, val)


def _memoize(fn, stats):
    """Cache by (array CONTENT hash, scalar args); return copies so a caller mutating the result cannot
    poison the cache. Purpose: a threshold sweep must not recompute the same value array 40 times.

    The key hashes the bytes rather than using `id()` / the data pointer. An earlier version keyed on
    the pointer and silently returned a STALE array whenever a freed temporary was reallocated at the
    same address — which is exactly what happens when an indicator chains two calls (`smi` does
    `nan_ema(nan_ema(...))`). The self-control phase exists because of that bug.
    """
    cache = {}

    def key_of(a):
        if isinstance(a, np.ndarray):
            return ("arr", hashlib.blake2b(np.ascontiguousarray(a).tobytes(),
                                           digest_size=16).digest(), a.shape, a.dtype.str)
        return ("val", repr(a))

    def wrapped(*args, **kw):
        k = tuple(key_of(a) for a in args) + tuple((n, key_of(v)) for n, v in sorted(kw.items()))
        if k not in cache:
            stats["computes"] += 1
            cache[k] = fn(*args, **kw)
        r = cache[k]
        if isinstance(r, tuple):
            return tuple(x.copy() if isinstance(x, np.ndarray) else x for x in r)
        return r.copy() if isinstance(r, np.ndarray) else r

    return wrapped


def _sweep_values(p, max_full=51, max_sampled=7):
    """Values to test for one schema parameter. Coarse (wide) parameters are SAMPLED, always including
    min / default / max; everything else gets its full searched grid."""
    lo, hi, step, dflt = p.get("min"), p.get("max"), p.get("step"), p.get("default")
    if lo is None or hi is None or not step:
        return [dflt], "default-only"
    grid = np.round(np.arange(lo, hi + step / 2.0, step), 6)
    if len(grid) == 0:
        return [dflt], "default-only"
    if len(grid) <= max_full:
        return [g.item() for g in grid], f"full({len(grid)})"
    picks = {float(lo), float(hi), float(dflt), *[float(v) for v in np.linspace(lo, hi, max_sampled)]}
    snapped = sorted({float(grid[int(np.abs(grid - v).argmin())]) for v in picks})
    return snapped, f"sampled({len(snapped)}/{len(grid)})"


def _sweep_points(key):
    """(label, params) points: defaults, each parameter varied alone, then the all-min / all-max corners."""
    ps = library.SCHEMA[key].get("params", [])
    base = {p["name"]: p["default"] for p in ps}
    points = [("default", base)]
    for p in ps:
        vals, _how = _sweep_values(p)
        for v in vals:
            if v != base[p["name"]]:
                q = dict(base); q[p["name"]] = v
                points.append((f"{p['name']}={v}", q))
    for nm in ("all_min", "all_max"):
        q = dict(base)
        for p in ps:
            if p.get("min") is not None and p.get("max") is not None:
                q[p["name"]] = p["min"] if nm == "all_min" else p["max"]
        if q != base:
            points.append((nm, q))
    return points


def _directions(key, params, ctx):
    ind = library.from_specs([{"key": key, "enabled": True,
                               "mode": library.SCHEMA[key]["mode"], "params": dict(params)}])[0]
    cdir, vdir = ind.directions(ctx)
    return np.asarray(cdir), np.asarray(vdir)


def _vote_check(key, pairs, ctx, log):
    """Compare the EMITTED confirm/veto arrays, fast vs reference, across the parameter sweep."""
    points = _sweep_points(key)
    s_fast, s_ref = {"computes": 0}, {"computes": 0}

    with _swapped([(t, _memoize(t, s_fast)) for t, _r in pairs]) as n_fast:
        fast = {lbl: _directions(key, prm, ctx) for lbl, prm in points}
    with _swapped([(t, _memoize(r, s_ref)) for t, r in pairs]) as n_ref:
        ref = {lbl: _directions(key, prm, ctx) for lbl, prm in points}

    flips, worst = 0, None
    for lbl in fast:
        cf, vf = fast[lbl]
        cr, vr = ref[lbl]
        d = int(np.sum(cf != cr)) + int(np.sum(vf != vr))
        flips += d
        if d and (worst is None or d > worst[1]):
            worst = (lbl, d)
    note = ""
    if not n_fast or not n_ref:
        note = "NOTHING WAS SWAPPED — gate is vacuous"
    elif s_ref["computes"] == 0:
        note = "reference never called — this indicator does not use the swapped function"
    log(f"    {key:20s} points={len(points):4d} ref_computes={s_ref['computes']:4d} "
        f"flips={flips}" + (f"  WORST {worst[0]} ({worst[1]} bars)" if worst else "")
        + (f"   !! {note}" if note else ""))
    return {"key": key, "points": len(points), "sites_swapped": n_ref,
            "ref_computes": s_ref["computes"], "vote_flips": flips,
            "exercised": bool(n_ref and s_ref["computes"]), "note": note or None,
            "worst_point": worst[0] if worst else None,
            "swept": [p["name"] + ":" + _sweep_values(p)[1] for p in library.SCHEMA[key].get("params", [])]}


def phase_control(ctx, log):
    """DUMB CONTROL. Run the whole vote machinery with the reference swapped in for ITSELF. Any flip
    reported here is a harness bug, not a finding — the first version of the memo keyed on the array's
    data pointer and reported 19,146 phantom `smi` flips that way."""
    rows = []
    for key, fast_fn, _ref in ACCELERATED:
        rows.append(_vote_check(key, [(fast_fn, fast_fn)], ctx, log))
    for key in LEAF_DRIVEN:
        if key in library.SCHEMA:
            rows.append(_vote_check(key, [(t, t) for t, _r in LEAVES], ctx, log))
    total = sum(r["vote_flips"] for r in rows)
    log(f"[budget] CONTROL FLIPS = {total} (MUST be 0; anything else means the harness is broken)")
    return {"rows": rows, "total_flips": total}


# --------------------------------------------------------------------------------------------------
def phase_primitives(close, high, low, log):
    """Bit-identity of the shared leaves. Anything short of exact equality here is a failure."""
    out = []
    for n in (2, 5, 9, 14, 26, 52, 100, 200):
        for name, fast, ref in (
            (f"_roll_max n={n}", classic._roll_max(high, n), REF.roll_max_ref(high, n)),
            (f"_roll_min n={n}", classic._roll_min(low, n), REF.roll_min_ref(low, n)),
            (f"ema n={n}", classic.ema(close, n), REF.ema_ref(close, n)),
            (f"rma n={n}", classic.rma(close, n), REF.rma_ref(close, n)),
            (f"nan_ema n={n}", OSC.nan_ema(close, n), OSC.nan_ema_reference(close, n)),
        ):
            a, b = np.asarray(fast, float), np.asarray(ref, float)
            same_nan = bool(np.array_equal(np.isnan(a), np.isnan(b)))
            exact = bool(same_nan and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
            out.append({"case": name, "bit_identical": exact})
            if not exact:
                log(f"    !! {name}: NOT bit-identical (nan_mask_ok={same_nan})")
    log(f"    {sum(o['bit_identical'] for o in out)}/{len(out)} primitive cases bit-identical")
    return out


def phase_exactness(ctx, log):
    """Per-accelerator VALUE diff on the real frame, and — where the accelerator cannot be made
    bit-identical — how far the deciding quantity ever gets from its decision boundary.

    "Zero vote flips" answers *did it change a decision on this data*. It does not answer *how close
    did it come*. For the three Ehlers filters the transcendental sits inside a loop-carried
    recurrence, so it cannot be hoisted into numpy the way `frama`'s was; the honest claim there is a
    measured MARGIN, and this is where that number comes from.
    """
    c = np.ascontiguousarray(np.asarray(ctx.close, float))
    h = np.ascontiguousarray(np.asarray(ctx.high, float))
    l = np.ascontiguousarray(np.asarray(ctx.low, float))
    rows = []

    def diff(tag, a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        nan_ok = bool(np.array_equal(np.isnan(a), np.isnan(b)))
        d = np.abs(a - b)
        d = d[np.isfinite(d)]
        row = {"case": tag, "nan_mask_ok": nan_ok, "n_differing": int((d > 0).sum()),
               "max_abs_diff": float(d.max()) if d.size else 0.0}
        row["bit_identical"] = bool(nan_ok and row["n_differing"] == 0)
        rows.append(row)
        log(f"    {tag:30s} bit_identical={row['bit_identical']!s:5s} "
            f"differing={row['n_differing']:>7d} max|Δ|={row['max_abs_diff']:.3e}")
        return row["max_abs_diff"]

    for n in (4, 16, 61):
        diff(f"frama n={n}", DSP.frama(h, l, c, n), DSP.frama_reference(h, l, c, n))
    for n in (10, 50, 150):
        diff(f"ou_coefficient n={n}", T2.ou_coefficient(c, n), T2.ou_coefficient_reference(c, n))
    for n in (5, 14, 50):
        diff(f"ulcer n={n}", V.ulcer(c, n), V.ulcer_reference(c, n))
    for n in (14, 60):
        diff(f"proj_bands n={n}", V.proj_bands(h, l, n)[0], V.proj_bands_reference(h, l, n)[0])
    for n in (5, 14, 40):
        diff(f"dynamic_dmi n={n}", OSC.dynamic_dmi(c, n), OSC.dynamic_dmi_reference(c, n))
    for n in (20, 100):
        diff(f"linreg_dev n={n}", TR.linreg_dev(c, n)[1], TR.linreg_dev_reference(c, n)[1])
        diff(f"linreg_slope n={n}", TR.linreg_slope(c, n), TR.linreg_slope_reference(c, n))
    for n in (20, 80):
        diff(f"linreg_r2 n={n}", Q.linreg_r2(c, n), Q.linreg_r2_reference(c, n))
    for n in (25, 100):
        diff(f"lsma n={n}", MA.lsma(c, n), MA.lsma_reference(c, n))
    diff("schaff_trend_cycle", DSP.schaff_trend_cycle(c, 23, 50, 10),
         DSP.schaff_trend_cycle_reference(c, 23, 50, 10))

    log("    -- the Ehlers group: trig inside a loop-carried recurrence, so 1 ULP is unavoidable --")
    d_dc = diff("dominant_cycle", DSP.dominant_cycle(c)[0], DSP.dominant_cycle_reference(c)[0])
    d_mf = diff("mama_fama", DSP.mama_fama(c)[0], DSP.mama_fama_reference(c)[0])
    d_sw = diff("hilbert_sinewave", DSP.hilbert_sinewave(c)[0], DSP.hilbert_sinewave_reference(c)[0])

    margins = []

    def margin(tag, q, drift):
        m = np.abs(np.asarray(q, float))
        m = m[np.isfinite(m) & (m > 0)]
        row = {"case": tag, "min_margin": float(m.min()) if m.size else None, "drift": float(drift),
               "bars_within_drift": int((m <= drift).sum()) if m.size else 0}
        row["safety_factor"] = (row["min_margin"] / drift) if (m.size and drift > 0) else None
        margins.append(row)
        log(f"    {tag:30s} min|margin|={row['min_margin']:.3e}  drift={drift:.3e}  "
            f"within_drift={row['bars_within_drift']}  safety={row['safety_factor']:.3g}x")

    sine, lead = DSP.hilbert_sinewave(c)
    margin("sinewave sign(sine-lead)", sine - lead, max(d_sw, np.finfo(float).tiny))
    mama, fama = DSP.mama_fama(c)
    margin("mama_fama sign(mama-fama)", mama - fama, max(d_mf, np.finfo(float).tiny))
    per, _ = DSP.dominant_cycle(c)
    live = per[np.isfinite(per) & (per > 0)]
    p = next(p for p in library.SCHEMA["hilbert_cycle"]["params"] if p["name"] == "threshold")
    grid = np.round(np.arange(p["min"], p["max"] + p["step"] / 2, p["step"]), 6)
    closest = min(float(np.abs(live - t).min()) for t in grid)
    margin("hilbert_cycle |per-thr| (grid)", np.array([closest]), max(d_dc, np.finfo(float).tiny))
    return {"diffs": rows, "margins": margins,
            "all_bit_identical_except_ehlers": all(
                r["bit_identical"] for r in rows
                if not r["case"].startswith(("dominant_cycle", "mama_fama", "hilbert_sinewave")))}


def phase_timing(ctx, keys, log):
    rows = []
    for key, fast_fn, ref_fn in ACCELERATED:
        if key not in keys:
            continue
        params = {p["name"]: p["default"] for p in library.SCHEMA[key].get("params", [])}
        _directions(key, params, ctx)                                   # warm-up: JIT, NOT timed
        t0 = time.perf_counter(); _directions(key, params, ctx); fast_s = time.perf_counter() - t0
        with _swapped([(fast_fn, ref_fn)]):
            t0 = time.perf_counter(); _directions(key, params, ctx); ref_s = time.perf_counter() - t0
        rows.append({"key": key, "reference_s": round(ref_s, 4), "accelerated_s": round(fast_s, 4),
                     "speedup": round(ref_s / fast_s, 1) if fast_s > 0 else None})
        log(f"    {key:20s} ref={ref_s:8.3f}s  fast={fast_s:8.3f}s  {rows[-1]['speedup']}x")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", type=int, default=0, help="0 = the full frame")
    ap.add_argument("--phases", default="primitives,exactness,control,votes,timing")
    ap.add_argument("--only", default="", help="comma-separated registry keys (votes/timing)")
    ap.add_argument("--out", default="optimize/perf/results/budget_accel.json")
    args = ap.parse_args()
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    only = {k.strip() for k in args.only.split(",") if k.strip()}

    def log(msg):
        print(msg, flush=True)

    base = os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading")
    df = load_data(str(Path(base) / TF.RAW_DIR / "NQ_1m.csv")).sort_values("Date").reset_index(drop=True)
    if args.bars:
        df = df.iloc[: args.bars]
    ctx = market_context(df)
    log(f"[budget] frame={len(df):,} bars | numba={classic._HAVE_NUMBA} | phases={phases}")

    res = {"bars": len(df), "have_numba": bool(classic._HAVE_NUMBA)}
    if "primitives" in phases:
        log("[budget] phase primitives — bit-identity of the shared leaves")
        res["primitives"] = phase_primitives(np.asarray(ctx.close, float), np.asarray(ctx.high, float),
                                             np.asarray(ctx.low, float), log)
        res["primitives_all_bit_identical"] = all(o["bit_identical"] for o in res["primitives"])
    if "exactness" in phases:
        log("[budget] phase exactness — value diffs, and decision-boundary margins where 1 ULP remains")
        res["exactness"] = phase_exactness(ctx, log)
    if "control" in phases:
        log("[budget] phase control — the same machinery comparing each function to ITSELF")
        res["control"] = phase_control(ctx, log)
    if "votes" in phases:
        log("[budget] phase votes — emitted confirm/veto arrays, fast vs reference")
        rows = []
        for key, fast_fn, ref_fn in ACCELERATED:
            if only and key not in only:
                continue
            rows.append(_vote_check(key, [(fast_fn, ref_fn)], ctx, log))
        for key in LEAF_DRIVEN:
            if (only and key not in only) or key not in library.SCHEMA:
                continue
            rows.append(_vote_check(key, LEAVES, ctx, log))
        res["votes"] = rows
        res["total_vote_flips"] = sum(r["vote_flips"] for r in rows)
        log(f"[budget] TOTAL VOTE FLIPS = {res['total_vote_flips']}")
    if "timing" in phases:
        log("[budget] phase timing — full-frame wall-clock, warmed")
        res["timing"] = phase_timing(ctx, only or {a[0] for a in ACCELERATED}, log)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    log(f"[budget] WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
