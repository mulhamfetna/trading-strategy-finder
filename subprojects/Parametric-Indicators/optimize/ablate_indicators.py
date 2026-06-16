"""β — exhaustive indicator ablation of the wsh4 1-min 4h champion. All 2^8 on/off subsets, full-period,
parallel. Reuses the golden engine path (backtest_metrics) + the two_stage._Ctx loader. Reports which
indicators can be dropped (PnL/DD/decision-pause/data-footprint per subset) — no hard filter, ranked.

CLI:  python3 -m optimize.ablate_indicators [--tf 4h] [--workers 10] [--drop-bonus N] [--top 40]
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from indicators import library

_CHAMPS = _HERE / "results" / "wsh4_champions_full.json"
DROP_BONUS = 5000.0   # $ credited per indicator dropped, for the ranking score (documented, tunable)


# ── loader + enumeration + param builder (β.1) ───────────────────────────────────────────────────
def load_champion(tf: str = "4h") -> dict:
    # champion JSON: indicators = {key: params_dict} for the ENABLED indicators only (matches _native_seed)
    c = json.loads(_CHAMPS.read_text())[tf]
    inds = c["indicators"]
    enabled = list(inds.keys())
    params_by_key = dict(inds)
    modes = {k: library.SCHEMA[k]["mode"] for k in enabled}
    return {"tf": tf, "box": c["box"], "enabled_keys": enabled,
            "params_by_key": params_by_key, "modes": modes}


def subsets(enabled_keys) -> list:
    keys = list(enabled_keys)
    out = []
    for r in range(len(keys) + 1):
        for combo in itertools.combinations(keys, r):
            out.append(frozenset(combo))
    return out


def build_params(champ: dict, keep: frozenset) -> dict:
    box = champ["box"]
    specs = [{"key": k, "enabled": (k in keep),
              "mode": champ["modes"].get(k, library.SCHEMA[k]["mode"]),
              "params": dict(champ["params_by_key"].get(k, {}))} for k in champ["enabled_keys"]]
    return dict(sl_soft=box["sl_soft"], sl_hard=box["sl_hard"], tp=box["tp"], gate_pct=box["gate_pct"],
                dd_limit=box["dd_limit"], cooldown=int(box["cooldown"]), flip=bool(box["flip"]),
                window="full", indicators=specs, k=int(box["k"]), ind_1min=True)


# ── per-subset evaluation + parallel runner (β.2) ────────────────────────────────────────────────
_CTX = None   # per-process loaded-once engine context

def _ctx(tf):
    global _CTX
    if _CTX is None:
        from optimize import two_stage as TS
        _CTX = TS._Ctx(tf, split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=False)
    return _CTX


def _evaluate_full(params: dict) -> dict:
    """Full-period backtest via the golden engine path; returns the backtest_metrics dict (+ S0 keys)."""
    from optimize.core import backtest_metrics
    c = _ctx(params["_tf"])
    p = {k: v for k, v in params.items() if k != "_tf"}
    return backtest_metrics(c.df_dec, c.df1, c.box, c.vf, c.n_split, dict(p, window="full"),
                            c.tf.bar_td, sig_int=c.sig_int)


def eval_subset(champ: dict, keep: frozenset) -> dict:
    params = build_params(champ, keep); params["_tf"] = champ["tf"]
    m = _evaluate_full(params)
    return {"kept": sorted(keep), "n_indicators": len(keep),
            "dropped": sorted(set(champ["enabled_keys"]) - keep),
            "pnl": m.get("pnl", 0.0), "max_dd": m.get("max_dd", 0.0), "win": m.get("win", 0.0),
            "pf": m.get("pf"), "n_taken": m.get("n_taken", 0),
            "decision_pause_days": m.get("max_no_entry_days_decision", 0.0),
            "overall_pause_days": m.get("max_no_entry_days", 0.0),
            "pause_source": m.get("longest_gap_source", "?"),
            "warmup_days": m.get("warmup_days", 0.0),
            "data_footprint_candles": m.get("data_footprint_candles", 0)}


def _eval_one(args):
    champ, keep = args
    return eval_subset(champ, keep)


def run_all(tf: str = "4h", workers: int = 10) -> list:
    champ = load_champion(tf)
    subs = subsets(champ["enabled_keys"])
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row in ex.map(_eval_one, [(champ, s) for s in subs]):
            rows.append(row)
    return rows


# ── ranking + report writers (β.3) ───────────────────────────────────────────────────────────────
def rank(rows, baseline_pnl, drop_bonus=DROP_BONUS):
    for r in rows:
        r["delta_pnl_pct"] = (round(100.0 * (r["pnl"] - baseline_pnl) / baseline_pnl, 2)
                              if baseline_pnl else 0.0)
        r["score"] = r["pnl"] + drop_bonus * len(r["dropped"])
    return sorted(rows, key=lambda r: r["score"], reverse=True)


def marginal_impact(rows, keys):
    """Mean PnL WITH vs WITHOUT each indicator across all subsets → avg ΔPnL of removing it."""
    out = {}
    for k in keys:
        with_k = [r["pnl"] for r in rows if k in r["kept"]]
        without_k = [r["pnl"] for r in rows if k not in r["kept"]]
        aw = round(sum(with_k) / len(with_k), 0) if with_k else 0.0
        ao = round(sum(without_k) / len(without_k), 0) if without_k else 0.0
        out[k] = {"avg_pnl_with": aw, "avg_pnl_without": ao, "avg_drop_cost": round(aw - ao, 0)}
    return out


def write_json(rows, path):
    Path(path).write_text(json.dumps(rows, indent=2)); return str(path)


def write_report(ranked, marg, champ, baseline, path, top=40):
    L = ["# Indicator ablation — wsh4 1-min 4h champion\n",
         f"Baseline (all {len(champ['enabled_keys'])} on) = **${baseline:,.0f}** P/L. All {len(ranked)} "
         f"subsets backtested full-period (ind_1min). Ranked by score = PnL + ${DROP_BONUS:,.0f} per "
         f"indicator dropped (no hard filter — pick your tolerance by eye).\n",
         "| rank | kept | #drop | PnL | ΔPnL% | maxDD | win% | decision-pause d | source | footprint(1m) |",
         "|--:|---|--:|--:|--:|--:|--:|--:|---|--:|"]
    for i, r in enumerate(ranked[:top], 1):
        L.append(f"| {i} | {', '.join(r['kept']) or '(none)'} | {len(r['dropped'])} | ${r['pnl']:,.0f} | "
                 f"{r['delta_pnl_pct']:+.1f} | ${r['max_dd']:,.0f} | {r['win']:.1f} | "
                 f"{r['decision_pause_days']:.1f} | {r['pause_source']} | {r['data_footprint_candles']} |")
    L.append(f"\n_… {max(0, len(ranked) - top)} more rows in the JSON._\n")
    L.append("## Per-indicator marginal impact (avg ΔPnL when removed; sorted cheapest-to-drop first)\n")
    L.append("| indicator | avg PnL with | avg PnL without | avg drop cost |")
    L.append("|---|--:|--:|--:|")
    for k, v in sorted(marg.items(), key=lambda kv: kv[1]["avg_drop_cost"]):
        L.append(f"| {k} | ${v['avg_pnl_with']:,.0f} | ${v['avg_pnl_without']:,.0f} | ${v['avg_drop_cost']:,.0f} |")
    Path(path).write_text("\n".join(L) + "\n"); return str(path)


# ── main (β.4) ────────────────────────────────────────────────────────────────────────────────────
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="β indicator ablation")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--drop-bonus", type=float, default=DROP_BONUS)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    champ = load_champion(a.tf)
    rows = run_all(a.tf, workers=a.workers)
    baseline = next(r["pnl"] for r in rows if len(r["kept"]) == len(champ["enabled_keys"]))
    assert abs(baseline - 142203) < 50, f"baseline {baseline} != golden 142,203 — loader/params wrong"
    ranked = rank(rows, baseline, a.drop_bonus)
    marg = marginal_impact(rows, champ["enabled_keys"])
    jp = write_json(rows, _HERE / "results" / f"ablation_wsi1m_{a.tf}.json")
    rp = write_report(ranked, marg, champ, baseline,
                      _PI / "study_range_regime" / f"REPORT_indicator_ablation_wsi1m_{a.tf}.md", top=a.top)
    print(f"ablation done: {len(rows)} subsets; baseline ${baseline:,.0f}; wrote {jp} + {rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
