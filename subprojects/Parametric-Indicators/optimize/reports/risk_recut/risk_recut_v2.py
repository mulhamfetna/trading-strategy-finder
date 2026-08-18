"""RISK-02 (Issue #3) — position-sizing re-cut on the DEPLOYED book, honest fills, CAP-AWARE.

What this fixes versus RISK-01 (2026-07-22), whose method was sound but whose inputs were not:

  1. WRONG BOOK. RISK-01 read `wsh4_champions_full*.json` as "deployed". The deployed set moved to
     `best_*` on 2026-07-14. All 54 slots differ between the two — many only in precision, but many
     genuinely (NQ 2h sl_hard 86 -> 182; NQ 15m cap none -> eod). Here the champion file is resolved
     through payload._instrument_champions_path(), never named.
  2. TOO SMALL. RISK-01 covered 8 slots (NQ+GC x 4 edge TFs). The book is 54 slots across 9 markets.
     Issue #3 asks for the portfolio risk budget, and explicitly asks to "treat NG separately" — NG was
     absent from RISK-01 entirely, despite being the market where honest fills cost the most drawdown.
  3. CAP-BLIND. RISK-01 applied entry + SL/TP/flip only, no time-caps or breaker, and flagged that as a
     caveat worth revisiting. It is no longer a minor caveat: the deployed set's defining difference
     from wsh4 IS its caps (eod/both on many slots), and a cap truncates exactly the long losing holds
     that drive the drawdown tail sizing depends on. This ledger applies each champion's own cap, and
     also reports the cap-blind ledger so the size of that error is measured rather than assumed.

Unchanged from the established Z2/Z4 method, deliberately, so the comparison stays clean: per-trade
normalization by the champion's OWN hard stop (R = pnl_points / sl_hard, a full stop-out = -1 risk unit,
so f is a true fraction of capital), the synthetic fat-tail gap overlay (Pareto a=3 on 5% of stop-outs),
and the mandatory noise check that re-locates the PnL:DD peak across independent MC seeds.

Stops are read STRICTLY (champion_stops raises on a missing stop — never a default) and every stop and
cap actually used is printed, per the no-silent-defaults rule.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = "/home/dev/Mulham/code/subprojects/Parametric-Indicators"
sys.path.insert(0, ROOT)

import presets                                                    # noqa: E402
from optimize import data, signals, trading_days                  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int    # noqa: E402
from optimize.fundamentals.champion_params import champion_stops  # noqa: E402
from optimize.l2 import payload as L2                             # noqa: E402

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
ALPHA, M, N = 3.0, 4000, 1000
GRID = [0.001, 0.002, 0.003, 0.004, 0.006, 0.008, 0.010, 0.012, 0.015, 0.020, 0.025, 0.030, 0.040]


def slot_ledger(inst, tf, entry, cap_aware=True):
    """Per-trade R = pnl_points / sl_hard for one champion slot. Returns (R, info) or None."""
    box = entry["box"]
    preset = presets._preset(tf, box, entry.get("indicators", {}))
    ss, sh, tp, fl = champion_stops(preset, tf)          # STRICT — raises rather than defaulting
    df, df1, boxdf, vf, n = data.load_inputs(tf, instrument=inst)
    s = signals_to_int(signals.decision_signals(df, boxdf))
    gate = vf <= float(np.percentile(vf[:n], float(preset["gate_pct"])))

    kw = {}
    cap_mode, cap_1min = "none", 0
    if cap_aware:
        cap_mode = str(box.get("cap_mode") or "none")
        cap_1min = int(box.get("cap_1min") or 0)
        # back-compat, mirroring fast_engine: a bare bar count with no mode is the bars cap
        if cap_mode == "none" and cap_1min:
            cap_mode = "bars"
        if cap_mode in ("eod", "both"):
            margin = int(preset.get("eod_margin_min", 15) or 15)
            et, sl_arr = trading_days.eod_targets(df1["Date"].to_numpy(), margin)
            kw.update(eod_target=et, session_last=sl_arr)
        kw.update(cap_1min=cap_1min, cap_mode=cap_mode)

    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), s, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      ss, sh, tp, fl, m_open=df1["Open"].to_numpy(float), gap_fills=True, **kw)
    if not F:
        return None
    pnl = np.array([t["pnl_points"] for t in F], float)
    R = pnl / sh
    capped = sum(1 for t in F if t.get("exit_reason") == "TIME_CAP")
    info = dict(inst=inst, tf=tf, sl_soft=ss, sl_hard=sh, tp=tp, flip=fl,
                cap_mode=cap_mode, cap_1min=cap_1min, n=len(R),
                stop_outs=int((R <= -0.999).sum()), time_capped=capped,
                expectancy_pts=float(pnl.mean()), expectancy_R=float(R.mean()))
    return R, info


def build(cap_aware=True):
    """Ledger for every deployed champion slot. Returns {inst: {tf: R}} and the info rows."""
    per, rows = {}, []
    for inst in INSTS:
        path = L2._instrument_champions_path(inst)        # DEPLOYED set — resolved, never hardcoded
        if not path.exists():
            print(f"  [{inst}] SKIP — {path.name} absent", flush=True)
            continue
        champs = json.loads(path.read_text())
        per[inst] = {}
        for tf in TFS:
            if tf not in champs:
                continue
            try:
                got = slot_ledger(inst, tf, champs[tf], cap_aware=cap_aware)
            except Exception as e:
                print(f"  [{inst} {tf}] FAILED: {type(e).__name__}: {e}", flush=True)
                continue
            if got is None:
                print(f"  [{inst} {tf}] no trades", flush=True)
                continue
            R, info = got
            per[inst][tf] = R
            rows.append(info)
            print(f"  {inst:>3} {tf:>3} | file={path.name:<28} sl_hard={info['sl_hard']:>10.4f} "
                  f"cap={info['cap_mode']:<5}{info['cap_1min'] or '':<5} n={info['n']:>5} "
                  f"stop-outs={info['stop_outs']:>4} capped={info['time_capped']:>4} "
                  f"E={info['expectancy_R']:+.4f}R", flush=True)
    return per, rows


def sim(base, f, rng, overlay=False, g=0.05, cap=4.0):
    """One Monte-Carlo sweep at risk fraction f.

    `overlay` applies the Z2/Z4 SYNTHETIC gap tail (Pareto a=3 on 5% of stop-outs, capped at 4x).

    ⚠️ IT DEFAULTS OFF, AND THAT IS A CORRECTION, NOT A PREFERENCE. That overlay was invented to
    approximate gap risk the OLD engine could not express: pre-GAP-01 the backtest filled a gapped stop
    AT THE LINE, so no trade could ever lose more than 1 risk unit and the tail had to be bolted on
    synthetically. With gap_fills=True the ledger already contains the real thing — measured worst trades
    reach -46R on NG. Applying the synthetic tail on top now DOUBLE-COUNTS gaps, inflating drawdown and
    biasing the recommended size DOWN. Both are reported so the size of that double-count is visible.
    """
    idx = rng.integers(0, len(base), size=(M, N))
    R = base[idx]
    if overlay:
        stop = R <= -0.999
        gap = (rng.random((M, N)) < g) & stop
        fac = np.minimum(cap, (1 - rng.random((M, N))) ** (-1 / ALPHA))
        R = np.where(gap, R * fac, R)
    W = np.exp(np.cumsum(np.log(np.maximum(1 + f * R, 1e-9)), axis=1))
    dd = (1 - W / np.maximum.accumulate(W, axis=1)).max(axis=1)
    return float(np.median(W[:, -1])), float(np.median(dd))


def curve(base, seed=0, overlay=False):
    rng = np.random.default_rng(seed)
    out = []
    for f in GRID:
        gw, dd = sim(base, f, rng, overlay=overlay)
        out.append((f, gw, dd, (gw - 1) / dd if dd > 0 else np.inf))
    return out


def ruin_stats(base):
    """What sizing actually has to survive: how far past the intended 1-unit risk do real trades go?"""
    below = base[base < -1.0]
    return {
        "worst_R": float(base.min()),
        "frac_worse_than_1R": float((base < -1.0).mean()),
        "frac_worse_than_2R": float((base < -2.0).mean()),
        "frac_worse_than_5R": float((base < -5.0).mean()),
        "mean_excess_given_breach": float(below.mean()) if len(below) else 0.0,
        # the fraction of capital ONE worst-case trade costs at f = 1%
        "worst_trade_cost_at_1pct": float(-0.01 * base.min()),
    }


def analyse(name, base, overlay=False):
    rs = ruin_stats(base)
    print(f"\n=== {name} — {len(base):,} pooled trades, expectancy {base.mean():+.4f} R/trade ===")
    print(f"  tail: worst trade {rs['worst_R']:.2f}R | past 1R {100*rs['frac_worse_than_1R']:.2f}% "
          f"| past 2R {100*rs['frac_worse_than_2R']:.2f}% | past 5R {100*rs['frac_worse_than_5R']:.3f}%"
          f" | ONE worst trade at f=1% costs {100*rs['worst_trade_cost_at_1pct']:.1f}% of capital")
    print(f"  {'f/trade':>9} {'med growth':>11} {'med maxDD':>10} {'PnL:DD':>8}")
    print("  " + "-" * 42)
    rows = curve(base, overlay=overlay)
    kelly = max(rows, key=lambda x: x[1])[0]
    pnldd = max((r for r in rows if np.isfinite(r[3])), key=lambda x: x[3])[0]
    for f, gw, dd, ratio in rows:
        mk = ("  <- growth-optimal (~full Kelly)" if f == kelly else "") + \
             ("  *** PnL:DD-optimal" if f == pnldd else "")
        print(f"  {100*f:>7.1f}% {gw:>11.3f}x {100*dd:>9.1f}% {ratio:>8.2f}{mk}")
    return {"kelly": kelly, "pnldd": pnldd, "tail": rs}


def noise_check(name, base, seeds=range(8), overlay=False):
    """MANDATORY. A real optimum sits still across seeds; a wandering peak means a flat plateau and the
    'optimum' is Monte-Carlo noise. RISK-01's headline 33% size-up died here."""
    peaks, at = [], {f: [] for f in GRID}
    for sd in seeds:
        rows = curve(base, seed=sd, overlay=overlay)
        for f, _, _, r in rows:
            at[f].append(r)
        peaks.append(max((r for r in rows if np.isfinite(r[3])), key=lambda x: x[3])[0])
    means = {f: float(np.mean(v)) for f, v in at.items()}
    best = max(means.values())
    plat = [f for f in GRID if means[f] >= 0.97 * best]
    print(f"  {name:<22} peaks/seed (%) = {[round(100*p, 1) for p in peaks]}")
    print(f"  {'':<22} plateau within 3% of best: {100*min(plat):.1f}%–{100*max(plat):.1f}% "
          f"(best mean PnL:DD {best:.3f})")
    return {"peaks": peaks, "plateau": (min(plat), max(plat)), "best_mean_ratio": best}


def main():
    print("=" * 100)
    print("RISK-02 — sizing re-cut on the DEPLOYED book (best_*), honest fills, CAP-AWARE")
    print("=" * 100)
    print(f"deployed set = {L2.DEFAULT_CHAMPION_SET!r}\n")

    print("--- CAP-AWARE ledger (each champion's own time-cap applied) ---")
    per, rows = build(cap_aware=True)
    print("\n--- CAP-BLIND ledger (RISK-01's method, for comparison only) ---")
    per_blind, rows_blind = build(cap_aware=False)

    allR = np.concatenate([r for m in per.values() for r in m.values()])
    blindR = np.concatenate([r for m in per_blind.values() for r in m.values()])
    ngR = np.concatenate(list(per.get("NG", {}).values())) if per.get("NG") else np.array([])
    exNG = np.concatenate([r for i, m in per.items() if i != "NG" for r in m.values()])

    res = {}
    res["all"] = analyse("WHOLE BOOK, cap-aware (real gaps only)", allR)
    res["all_overlay"] = analyse("WHOLE BOOK, cap-aware + SYNTHETIC gap overlay (double-counts gaps)",
                                 allR, overlay=True)
    res["blind"] = analyse("WHOLE BOOK, cap-blind (RISK-01 method)", blindR)
    res["exNG"] = analyse("BOOK EXCLUDING NG, cap-aware", exNG)
    if len(ngR):
        res["NG"] = analyse("NG ALONE, cap-aware", ngR)

    print("\n" + "=" * 100)
    print("NOISE CHECK — where does the PnL:DD peak land across 8 independent MC seeds?")
    print("=" * 100)
    noise = {"all": noise_check("whole book", allR),
             "blind": noise_check("cap-blind", blindR),
             "exNG": noise_check("excluding NG", exNG)}
    if len(ngR):
        noise["NG"] = noise_check("NG alone", ngR)

    print("\n" + "=" * 100)
    print("PER-MARKET expectancy and stop-out rate (cap-aware)")
    print("=" * 100)
    print(f"  {'mkt':>4} {'trades':>8} {'stop-outs':>10} {'%stopped':>9} {'E[R]':>9} {'worst R':>9}")
    for inst in INSTS:
        if inst not in per or not per[inst]:
            continue
        r = np.concatenate(list(per[inst].values()))
        so = int((r <= -0.999).sum())
        print(f"  {inst:>4} {len(r):>8,} {so:>10,} {100*so/len(r):>8.1f}% "
              f"{r.mean():>+9.4f} {r.min():>9.2f}")

    out = Path("/home/dev/Mulham/risk2/risk_recut_v2.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"deployed_set": L2.DEFAULT_CHAMPION_SET, "slots": rows, "slots_cap_blind": rows_blind,
         "results": res, "noise": noise,
         "pooled": {"all": len(allR), "exNG": len(exNG), "NG": len(ngR)}}, indent=1, default=float))
    print(f"\nWROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
