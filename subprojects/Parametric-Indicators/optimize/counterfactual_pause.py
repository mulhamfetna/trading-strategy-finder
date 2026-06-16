"""Counterfactual pause attribution — does the champion's no-entry pause cost money? READ-ONLY.

For the 4h champion, every blocked box signal (vol-gated / vetoed / confirm<K) is simulated as an ISOLATED
trade with the champion's exact SL/TP exit (reusing fast_backtest), and bucketed into a per-filter P/L
ledger. Box-silent bars (no signal) are characterized by price displacement. Verdict per filter:
over-filtering (positive expectancy ⇒ relaxing is justified) vs correctly filtering (accept the pause).

Run:  python3 -m optimize.counterfactual_pause [--tf 4h] [--out optimize/results/counterfactual_pause_4h.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import config                                              # noqa: E402
from optimize import two_stage as TS                       # noqa: E402
from optimize.fast_engine import fast_backtest             # noqa: E402
from indicators import library, runner                     # noqa: E402

CAUSES = ["box_silence", "vol_gated", "vetoed", "confirm<K", "would_enter"]


def attribute(sig, vol_gate, veto, confirm):
    """Label every ENTRY bar idx (1..n-1) by why it did/didn't enter. The signal is read from idx-1
    (engine convention); the gate masks are applied at idx. Returns an object array length n (cause[0]=None)."""
    sig = np.asarray(sig)
    vol_gate = np.asarray(vol_gate, dtype=bool)
    veto = np.asarray(veto, dtype=bool)
    confirm = np.asarray(confirm, dtype=bool)
    n = len(sig)
    cause = np.full(n, None, dtype=object)
    for idx in range(1, n):
        if sig[idx - 1] == 0:
            cause[idx] = "box_silence"
        elif not vol_gate[idx]:
            cause[idx] = "vol_gated"
        elif veto[idx]:
            cause[idx] = "vetoed"
        elif not confirm[idx]:
            cause[idx] = "confirm<K"
        else:
            cause[idx] = "would_enter"
    return cause


def load_champion(tf: str = "4h"):
    """Reuse diagnose_pause's setup: champion ctx + the vol/veto/confirm masks + champion params."""
    ctx = TS._Ctx(tf, split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=True)
    if not ctx.has_champion:
        raise SystemExit("no champion seed found (need optimize/results/wsh4_champions_full.json)")
    d, d1, box, vf, n_split = ctx.df_dec, ctx.df1, ctx.box, ctx.vf, ctx.n_split
    bar_td = ctx.tf.bar_td
    cont = ctx.champ_cont
    gate_pct = float(cont["gate_pct"]); K = int(cont["k"])
    params = ctx.build_params(ctx.champ_en, ctx.champ_flip, cont)
    inds = library.from_specs([s for s in params["indicators"] if s.get("enabled")])
    n = len(d)
    sig = np.asarray(ctx.sig_int)[:n]

    vol_gate = np.ones(n, dtype=bool)
    if gate_pct > 0:
        gthr = float(np.percentile(vf[:n_split], gate_pct))
        vol_gate = vf[:n] <= gthr
    src = runner.indicator_source_1min(d, d1, bar_td)
    votes = runner.compute_votes(d, box, inds, src=src)
    veto = np.asarray(runner.veto_mask(d, box, inds, src=src, votes=votes))[:n]
    confirm = np.asarray(runner.confirm_mask(d, box, inds, K, src=src, votes=votes))[:n]
    return dict(ctx=ctx, d=d, d1=d1, box=box, n=n, sig=sig, vol_gate=vol_gate, veto=veto,
                confirm=confirm, params=params, pv=float(config.NQ_POINT_VALUE),
                bar_td=bar_td, gate_pct=gate_pct, K=K)


def _engine_gate(C):
    """The champion's effective per-bar gate: vol_gate ∧ ¬veto ∧ confirm (engine convention)."""
    return C["vol_gate"] & ~C["veto"] & C["confirm"]


def _bt_args(C):
    d, d1 = C["d"], C["d1"]
    p = C["params"]
    return (d["Date"].to_numpy(), d["Close"].to_numpy(float), C["sig"],
            d1["Date"].to_numpy(), d1["High"].to_numpy(float),
            d1["Low"].to_numpy(float), d1["Close"].to_numpy(float),
            float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]), bool(p["flip"]))


def champion_taken_trades(C):
    """Full champion run via fast_backtest with the real gate (matches core.backtest_metrics' candidate stream)."""
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = _bt_args(C)
    return fast_backtest(dd, cl, si, _engine_gate(C), md, mh, ml, mc, sls, slh, tp, flip)


def simulate_one(C, entry_idx: int):
    """Simulate the box signal that would enter at `entry_idx`, in ISOLATION: real signals, but a gate that is
    True at exactly that entry bar. Returns the single completed trade dict, or None if it never closes."""
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = _bt_args(C)
    gate_one = np.zeros(C["n"], dtype=bool)
    gate_one[int(entry_idx)] = True
    trades = fast_backtest(dd, cl, si, gate_one, md, mh, ml, mc, sls, slh, tp, flip)
    return trades[0] if trades else None


def _median_trade_duration_bars(C, taken) -> int:
    """Median real-trade hold in decision bars (horizon for box-silence displacement). >=1."""
    secs = C["bar_td"].total_seconds()
    durs = []
    for t in taken:
        dt = (np.datetime64(t["exit_time"]) - np.datetime64(t["entry_time"])) / np.timedelta64(1, "s")
        durs.append(max(1, round(float(dt) / secs)))
    return int(np.median(durs)) if durs else 1


def _bucket(trades_pnl_pts, pv):
    pnl = np.array([p * pv for p in trades_pnl_pts], dtype=float)
    n = len(pnl)
    return {"n": n,
            "win_rate": float((pnl > 0).mean()) if n else 0.0,
            "avg_pnl": float(pnl.mean()) if n else 0.0,
            "total_pnl": float(pnl.sum()) if n else 0.0,
            "med_pnl": float(np.median(pnl)) if n else 0.0}


def silence_displacement(C, horizon: int):
    """For every box-silent ENTRY bar (sig[idx-1]==0), MFE/MAE over the next `horizon` decision bars from the
    bar's close (points). Reports the fraction whose max |move| exceeded the champion tp (a real missed move)."""
    d = C["d"]
    close = d["Close"].to_numpy(float); high = d["High"].to_numpy(float); low = d["Low"].to_numpy(float)
    n = C["n"]; sig = C["sig"]; tp = float(C["params"]["tp"])
    mfe, mae = [], []
    for idx in range(1, n):
        if sig[idx - 1] != 0:
            continue
        j = min(idx + horizon, n)
        if j <= idx:
            continue
        c0 = close[idx]
        mfe.append(float(high[idx:j].max() - c0))
        mae.append(float(c0 - low[idx:j].min()))
    mfe = np.array(mfe); mae = np.array(mae)
    nn = len(mfe)
    exceed = float((np.maximum(mfe, mae) >= tp).mean()) if nn else 0.0
    return {"n": int(nn), "med_mfe": float(np.median(mfe)) if nn else 0.0,
            "med_mae": float(np.median(mae)) if nn else 0.0,
            "frac_exceeds_tp": exceed, "tp": tp}


def build_ledger(C):
    """Full counterfactual ledger: per-filter isolated-trade buckets + box-silence displacement + benchmark."""
    taken = champion_taken_trades(C)
    champ_pnl = np.array([t["pnl_points"] * C["pv"] for t in taken], dtype=float)
    cause = attribute(C["sig"], C["vol_gate"], C["veto"], C["confirm"])
    horizon = _median_trade_duration_bars(C, taken)

    buckets = {}
    for label in ("vol_gated", "vetoed", "confirm<K"):
        idxs = [i for i in range(1, C["n"]) if cause[i] == label]
        trades = []
        for i in idxs:
            t = simulate_one(C, i)
            if t is not None:
                trades.append(t)
        b = _bucket([t["pnl_points"] for t in trades], C["pv"])
        b["n_unresolved"] = len(idxs) - len(trades)
        b["trades"] = [dict(cause=label, entry_time=str(t["entry_time"]), exit_time=str(t["exit_time"]),
                            direction=t["direction"], entry_price=float(t["entry_price"]),
                            exit_price=float(t["exit_price"]), exit_reason=t["exit_reason"],
                            pnl=round(float(t["pnl_points"]) * C["pv"], 2)) for t in trades]
        buckets[label] = b

    return {"buckets": buckets,
            "box_silence": silence_displacement(C, horizon),
            "champion_avg_pnl": float(champ_pnl.mean()) if len(champ_pnl) else 0.0,
            "champion_n": int(len(champ_pnl)), "horizon_bars": int(horizon)}


def _verdict(b, champ_avg):
    """Over-filtering iff the bucket's avg P/L is positive AND a meaningful fraction of the champion's own
    edge (>=50% of champion avg trade). Else correctly filtering."""
    if b["n"] == 0:
        return "n/a (no blocked signals)"
    if b["avg_pnl"] > 0 and champ_avg > 0 and b["avg_pnl"] >= 0.5 * champ_avg:
        return "OVER-FILTERING (relaxing is justified)"
    return "correctly filtering (accept the pause)"


def write_csv(led, path: str):
    import csv
    rows = [t for b in led["buckets"].values() for t in b["trades"]]
    cols = ["cause", "entry_time", "exit_time", "direction", "entry_price", "exit_price", "exit_reason", "pnl"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["entry_time"]):
            w.writerow(r)
    return len(rows)


def write_report(led, tf: str, path: str):
    ca = led["champion_avg_pnl"]
    lines = [f"# Counterfactual pause attribution — {tf} champion", "",
             f"Read-only. Each blocked box signal simulated as an ISOLATED trade with the champion's exact "
             f"SL/TP exit (reused `fast_backtest`). Benchmark = champion avg trade **${ca:,.0f}** over "
             f"{led['champion_n']} trades. Displacement horizon = **{led['horizon_bars']} bars** "
             f"(median real-trade hold).", "",
             "## Per-filter ledger", "",
             "| filter | blocked n | win% | avg P/L | total P/L | verdict |",
             "|---|--:|--:|--:|--:|---|"]
    for k in ("vol_gated", "vetoed", "confirm<K"):
        b = led["buckets"][k]
        lines.append(f"| {k} | {b['n']} | {100*b['win_rate']:.1f}% | ${b['avg_pnl']:,.0f} | "
                     f"${b['total_pnl']:,.0f} | {_verdict(b, ca)} |")
    s = led["box_silence"]
    lines += ["", "## Box-silence (no signal — cannot simulate a trade)", "",
              f"- silent entry bars: **{s['n']}** · median MFE {s['med_mfe']:.0f} pts · median MAE "
              f"{s['med_mae']:.0f} pts", f"- fraction whose max move exceeded the champion TP "
              f"({s['tp']:.0f} pts): **{100*s['frac_exceeds_tp']:.1f}%** (a real directional move was "
              f"available there).", "",
              "## Verdict ledger", "",
              "```mermaid", "flowchart TD", '  P["no-entry pause"] --> V["vol_gated"]',
              '  P --> VE["vetoed"]', '  P --> C["confirm&lt;K"]', '  P --> B["box_silence (~71%)"]']
    for k, nm in (("vol_gated", "V"), ("vetoed", "VE"), ("confirm<K", "C")):
        b = led["buckets"][k]
        tag = "OVER-FILTER" if "OVER" in _verdict(b, ca) else "correct"
        lines.append(f'  {nm} --> {nm}R["{tag}: ${b["total_pnl"]:,.0f} over {b["n"]}"]')
    lines += ['  B --> BR["' + f"{100*s['frac_exceeds_tp']:.0f}% windows had a >TP move" + '"]', "```", "",
              "## Conclusion", "",
              "_Filled from the numbers above: which filter (if any) is over-filtering, and whether the "
              "box-silence windows held real moves — i.e. which lever (confirmation relax vs box-trigger "
              "change) the evidence supports, or whether to ACCEPT the pause._", ""]
    Path(path).write_text("\n".join(lines) + "\n")


def main() -> int:
    import warnings; warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--out", default=str(_HERE / "results" / "counterfactual_pause_4h.csv"))
    ap.add_argument("--report", default=str(_PI / "study_range_regime" / "REPORT_counterfactual_pause.md"))
    a = ap.parse_args()
    C = load_champion(a.tf)
    led = build_ledger(C)
    nrows = write_csv(led, a.out)
    write_report(led, a.tf, a.report)
    print(f"champion avg trade ${led['champion_avg_pnl']:,.0f} (n={led['champion_n']}); horizon "
          f"{led['horizon_bars']} bars")
    for k in ("vol_gated", "vetoed", "confirm<K"):
        b = led["buckets"][k]
        print(f"  {k:11} n={b['n']:4} win={100*b['win_rate']:5.1f}% avg=${b['avg_pnl']:>8,.0f} "
              f"total=${b['total_pnl']:>10,.0f}  {_verdict(b, led['champion_avg_pnl'])}")
    s = led["box_silence"]
    print(f"  box_silence n={s['n']} medMFE={s['med_mfe']:.0f} medMAE={s['med_mae']:.0f} "
          f">TP={100*s['frac_exceeds_tp']:.1f}%")
    print(f"wrote {nrows} counterfactual trades -> {a.out}; report -> {a.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
