"""α ladder — user-gated, fastest→slowest. Tier 1 (lean-3, local) runs here; Tiers 2-3 print the SERVER
command to launch on the AMD box (user-gated). Each tier writes REPORT_alpha_tier<N>_decision_pause.md with
the feasible front sorted by decision-pause (shortest first), highlighting the shortest pause at >=95% P/L."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import optuna
from optimize import optimizer as O

LEAN = ("cci", "order_block", "structure_trend")
WSH4_MED = 33587.0
FLOOR = 0.95 * WSH4_MED          # highlight band: keep >= 95% of the champion's median P/L

TIERS = {
    "1": dict(prefix="wsh7a", only=LEAN, exclude=(), where="local",
              desc="lean-3 fixed ON, continuous knobs only (~7 dims)"),
    "2": dict(prefix="wsh7b", only=(), exclude=("ifvg", "breaker", "cisd"), where="server",
              desc="wsh4-era 15-indicator space"),
    "3": dict(prefix="wsh7c", only=(), exclude=("ifvg", "breaker", "cisd"), where="server",
              desc="wsh4-era 15-indicator space, bigger budget + lean seed"),
}


def _report(prefix: str, tf: str, path: Path):
    name = f"{prefix}_{tf}"
    st = optuna.load_study(study_name=name, storage=O.study_storage.storage_url(O._db_for(tf, name)))
    rows = []
    for t in st.trials:
        ua = t.user_attrs
        if t.values is None or any(v > 0 for v in ua.get("constraint", [1.0])):   # feasible only
            continue
        rows.append((ua.get("decision_pause_days", 9e9), ua.get("median_pnl", 0.0),
                     ua.get("full_pnl", 0.0), ua.get("full_dd", 0.0), ua.get("median_win", 0.0)))
    rows.sort(key=lambda r: (r[0], -r[1]))            # shortest pause, then best P/L
    star = next((r for r in rows if r[1] >= FLOOR), None)
    L = [f"# α tier {prefix} — decision-pause front ({tf})\n",
         f"Feasible trials sorted by decision-pause (shortest first). Champion baseline: 11.5d / median "
         f"$33,587. Highlight ⭐ = shortest pause with median P/L ≥ ${FLOOR:,.0f} (−5%).\n",
         "| decision-pause d | median P/L | full P/L | full DD | win% |", "|--:|--:|--:|--:|--:|"]
    for r in rows[:40]:
        mark = " ⭐" if r is star else ""
        L.append(f"| {r[0]:.1f}{mark} | ${r[1]:,.0f} | ${r[2]:,.0f} | ${r[3]:,.0f} | {r[4]:.1f} |")
    if star:
        L.append(f"\n**Shortest pause @ ≥95% P/L: {star[0]:.1f} days** (median ${star[1]:,.0f}) — vs the "
                 f"champion's 11.5d / $33,587.")
    else:
        L.append("\n_No feasible trial reached ≥95% of the champion P/L — escalate to the next tier._")
    Path(path).write_text("\n".join(L) + "\n")
    return star, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="α escalation ladder (user-gated)")
    ap.add_argument("--tier", choices=list(TIERS), required=True)
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--trials", type=int, default=800)
    a = ap.parse_args()
    cfg = TIERS[a.tier]

    if cfg["where"] == "server":
        excl = ",".join(cfg["exclude"])
        print(f"TIER {a.tier} ({cfg['desc']}) runs on the SERVER. After your 'go', launch:")
        print(f"  WSH_PREFIX={cfg['prefix']} WSH_OBJECTIVE=decision_pause WSH_EXCLUDE={excl} "
              f"bash optimize/server/remote_wsi.sh run")
        print("Then pull + report with this script's _report() (or remote_wsi.sh pull).")
        return 0

    print(f"TIER {a.tier} ({cfg['desc']}) — running locally, prefix {cfg['prefix']}, {a.trials} trials …", flush=True)
    O.run(a.tf, n_trials=a.trials, ind_1min=True, study_prefix=cfg["prefix"], objective="decision_pause",
          only_inds=cfg["only"], exclude_inds=cfg["exclude"], warm_start=True)
    rep = _PI / "study_range_regime" / f"REPORT_alpha_tier{a.tier}_decision_pause.md"
    star, n = _report(cfg["prefix"], a.tf, rep)
    msg = (f"shortest pause @≥95% P/L = {star[0]:.1f}d (median ${star[1]:,.0f})" if star
           else "no point ≥95% P/L")
    print(f"TIER {a.tier} DONE — {n} feasible trials; {msg}. Report: {rep}", flush=True)
    print("PAUSED — review the report, then say 'go' to launch the next (server) tier.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
