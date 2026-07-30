"""Issue #2 — DEPLOYED (best_*) vs RE-OPTIMIZED (wshgap4_*) champions, both on the CURRENT engine.

Two things this fixes versus the retracted July comparison (`full_compare.py`):

  1. The baseline is the set that is actually DEPLOYED, resolved through payload's own resolver rather
     than hardcoded. July's script loaded `wsh4_*`, retired since 2026-07-14, and so reported a $52k
     gain that was really a $12.8k out-of-sample LOSS.
  2. The holdout is real. `wshgap4` trained on 2025 only (`--train-window 2025`), so the 2026 column
     below is data the search never saw. July's run trained on the whole series and then called 2026
     "out-of-sample".

Both sides are scored by the same engine through build_view_payload — the exact backend a dashboard
"Run" click triggers — each champion running its OWN parameters, under gap_fills=True (the default) and
ind_1min=True.
"""
import json
import sys
from pathlib import Path

ROOT = "/home/dev/Mulham/code/subprojects/Parametric-Indicators"
sys.path.insert(0, ROOT)

import presets                                    # noqa: E402
from optimize.l2 import payload as L2             # noqa: E402

RES = Path(ROOT) / "optimize" / "results"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
# 2025 is what the optimizer trained on; 2026 is the untouched holdout. 'full' spans both, so it is
# reported for continuity with older reports but is NOT the axis any adoption decision may rest on.
WINDOWS = [("train2025", "2025"), ("holdout2026", "2026"), ("full", "full")]
KEYS = ("pnl", "max_dd", "win", "pf", "payoff", "n_taken", "exposure")


def score(inst, tf, entry):
    base = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    base["ind_1min"] = True
    base["gap_fills"] = True
    lp = L2.validate_layer_params(base)
    out = {}
    for label, win in WINDOWS:
        p = dict(lp)
        p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b = pay["meta"]["boxes"]
        out[label] = {k: b.get(k) for k in KEYS}
    out["box"] = {k: entry["box"].get(k) for k in
                  ("sl_soft", "sl_hard", "tp", "cap_mode", "cap_1min", "gate_pct", "dd_limit", "flip", "k")}
    out["indicators"] = sorted(entry.get("indicators", {}))
    return out


def main():
    report, rows = {}, []
    for inst in ("NQ", "GC"):
        suf = "" if inst == "NQ" else f"_{inst}"
        dep_path = L2._instrument_champions_path(inst)          # the DEPLOYED set — never hardcoded
        new_path = RES / f"wshgap4_champions_full{suf}.json"
        print(f"[{inst}] deployed={dep_path.name}  candidate={new_path.name}", flush=True)
        if not new_path.exists():
            print(f"[{inst}] SKIP — {new_path.name} missing", flush=True)
            continue
        dep, new = json.loads(dep_path.read_text()), json.loads(new_path.read_text())
        for tf in TFS:
            if tf not in dep or tf not in new:
                print(f"[{inst} {tf}] SKIP — absent from one set", flush=True)
                continue
            d, n = score(inst, tf, dep[tf]), score(inst, tf, new[tf])
            report[f"{inst}_{tf}"] = {"deployed": d, "reopt": n,
                                      "deployed_file": dep_path.name, "candidate_file": new_path.name}
            rows.append((inst, tf, d, n))
            print(f"done {inst} {tf}", flush=True)

    # ---- the table. The holdout column is the one that decides anything. ----
    print("\n" + "=" * 108)
    print("DEPLOYED (best_*) vs RE-OPTIMIZED (wshgap4) — both on the current engine, honest fills")
    print("=" * 108)
    hdr = f"{'slot':<9} | {'train2025 P/L':>26} | {'HOLDOUT 2026 P/L':>26} | {'holdout dd':>20}"
    print(hdr); print("-" * len(hdr))
    tot = {w: [0.0, 0.0] for _, w in [("a", "train2025"), ("b", "holdout2026")]}
    for inst, tf, d, n in rows:
        t_d, t_n = d["train2025"]["pnl"] or 0, n["train2025"]["pnl"] or 0
        h_d, h_n = d["holdout2026"]["pnl"] or 0, n["holdout2026"]["pnl"] or 0
        dd_d, dd_n = d["holdout2026"]["max_dd"] or 0, n["holdout2026"]["max_dd"] or 0
        tot["train2025"][0] += t_d; tot["train2025"][1] += t_n
        tot["holdout2026"][0] += h_d; tot["holdout2026"][1] += h_n
        flag = "  <-- WORSE OOS" if h_n < h_d else ""
        print(f"{inst+' '+tf:<9} | {t_d:>10,.0f} -> {t_n:>10,.0f} | {h_d:>10,.0f} -> {h_n:>10,.0f} | "
              f"{dd_d:>8,.0f} -> {dd_n:>8,.0f}{flag}")
    print("-" * len(hdr))
    for w in ("train2025", "holdout2026"):
        a, b = tot[w]
        print(f"{'TOTAL ' + w:<9} | deployed {a:>12,.0f}  reopt {b:>12,.0f}  delta {b - a:>+12,.0f}")
    print("=" * 108)
    print("\nThe train2025 column is where the optimizer was allowed to look — a gain there is expected and\n"
          "proves nothing. Only the HOLDOUT 2026 column is evidence. A slot may be proposed for adoption\n"
          "only if it improves the holdout AND does not worsen holdout drawdown.")

    out = Path("/home/dev/Mulham/gap4/compare_gap2.json")
    out.write_text(json.dumps(report, indent=1))
    print(f"\nWROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
