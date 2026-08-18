"""Is the fast engine LYING, or is the EXTRACTOR mangling the champion?

Every divergence this campaign found is in one of the four LOWEST-PRICED markets (HG $4.33, NG $3.57,
SI $31, CL $73). The five markets above $2,000 have never diverged once. That points at numeric precision,
not at a market-specific engine bug.

Suspect: report_wsi rounds sl_soft / sl_hard / tp / dd_limit to FOUR DECIMALS when it writes a champion.
On the NASDAQ (stops ~20-135 points) that is invisible. On Natural Gas at $3.57 the stops come out at
0.0008 — where the 4th decimal is the ONLY significant digit, and rounding can move the stop by several
percent. If so, the optimizer SCORED one strategy and we EXTRACTED a different one, and the "lie" is ours.

This compares, for each divergent slot, the trial's TRUE searched params against what we wrote to disk.
"""
import json
import os

import optuna

os.environ.setdefault("PYTHONPATH", ".")
BASE = os.path.expanduser("~/Mulham/wsg-i")
URL = os.environ["WSH_STORAGE_URL"]

SLOTS = [("NG", "5m"), ("NG", "2m"), ("NG", "2h"), ("NG", "15m"),
         ("HG", "2m"), ("HG", "15m"), ("CL", "15m"), ("SI", "5m")]
FIELDS = ("sl_soft", "sl_hard", "tp", "dd_limit")

print(f"{'slot':8} {'field':9} {'TRIAL (searched)':>22} {'CHAMPION (written)':>20} {'rel. error':>11}")
print("-" * 76)
worst = []
for inst, tf in SLOTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    ch = json.load(open(f"{BASE}/Parametric-Indicators/optimize/results/eod1_champions_full{suf}.json"))
    box = ch[tf]["box"]
    st = optuna.load_study(study_name=f"eod1_{tf}_{inst}", storage=URL)
    cands = [t for t in st.trials if t.user_attrs.get("full_pnl") is not None]
    # the champion is the one whose recorded full_pnl the pareto extractor picked; match on it
    t = max(cands, key=lambda x: x.user_attrs["full_pnl"])
    p = t.params
    true = {"sl_soft": p.get("sl_soft"),
            "sl_hard": (p.get("sl_soft") or 0) + (p.get("sl_hard_delta") or 0),
            "tp": p.get("tp"), "dd_limit": p.get("dd_limit")}
    for f in FIELDS:
        tv, cv = true.get(f), box.get(f)
        if tv is None or cv is None:
            continue
        err = abs(tv - cv) / abs(tv) * 100 if tv else 0.0
        flag = "  <<<" if err > 0.5 else ""
        print(f"{inst + '_' + tf:8} {f:9} {tv:>22.10f} {cv:>20} {err:>10.3f}%{flag}")
        worst.append((err, f"{inst}_{tf}.{f}"))
    print()

worst.sort(reverse=True)
print("WORST DISTORTIONS INTRODUCED BY THE EXTRACTOR'S ROUNDING:")
for e, name in worst[:6]:
    print(f"    {name:20} {e:7.3f}%")
