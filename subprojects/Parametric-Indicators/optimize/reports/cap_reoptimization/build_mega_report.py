"""Build the MEGA REPORT: all 9 markets x 6 timeframes, cold-started, 1-minute-indicator based,
with the new time-cap model (bar cap / end-of-day cap / both / none).

Every number here is UI-VERIFIED (the exact on-screen dashboard figure), never the optimizer's own claim.
"""
import json
import os
from collections import Counter
from datetime import date

T = os.path.expanduser("~/.claude/jobs/b835c01f/tmp")
new = {(r["inst"], r["tf"]): r for r in json.load(open(f"{T}/cap_verify.json")) if "full" in r}
caps = json.load(open(f"{T}/cap_modes.json"))
nq4 = json.load(open(f"{T}/nq4h_verify.json"))
MAN = json.load(open("/mnt/data/projects/trading/subprojects/Parametric-Indicators/"
                     "shareable/playbooks_backtester/MANIFEST.json"))
dep = {(m["inst"], m["tf"]): m for m in MAN if not m["variant"]}

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
NAMES = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "HG": "Copper",
         "CL": "Crude Oil", "NG": "Natural Gas", "RTY": "Russell 2000", "YM": "Dow"}
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
CAP_LABEL = {"none": "no time cap", "bars": "bar cap", "eod": "end-of-day", "both": "both (first to fire)"}


def m(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"


def get_new(inst, tf):
    if inst == "NQ" and tf == "4h":
        return nq4["pnl"], nq4["dd"], nq4["oos"], nq4["win"], nq4["n"]
    r = new.get((inst, tf))
    if not r:
        return None, None, None, None, None
    b, o = r["full"]["boxes"], r["oos2026"]["summary"]
    return b.get("pnl"), b.get("max_dd"), o.get("pnl"), b.get("win"), b.get("n_taken")


rows = []
for inst in INSTS:
    for tf in TFS:
        np_, nd, no, nw, nn = get_new(inst, tf)
        if np_ is None:
            continue
        d = dep.get((inst, tf), {})
        c = caps.get(f"{inst}_{tf}", {})
        if np_ <= 0 or no <= 0:
            pick = "REJECT"
        elif d.get("oos") is None or no > (d["oos"] or 0) * 1.05:
            pick = "NEW"
        elif (d["oos"] or 0) > no * 1.05:
            pick = "old"
        else:
            pick = "NEW" if nd < d.get("dd", 1e18) else "old"
        rows.append(dict(inst=inst, tf=tf, o_pnl=d.get("full"), o_dd=d.get("dd"), o_oos=d.get("oos"),
                         n_pnl=np_, n_dd=nd, n_oos=no, n_win=nw, n_trades=nn, pick=pick,
                         cap=c.get("cap_mode", "?"), cap_n=c.get("cap_1min", 0),
                         k=c.get("k"), n_ind=c.get("n_ind")))

adopted = [r for r in rows if r["pick"] == "NEW"]
held = [r for r in rows if r["pick"] == "old"]
rejected = [r for r in rows if r["pick"] == "REJECT"]

dep_oos = sum((r["o_oos"] or 0) for r in rows)
fin_oos = sum(max(r["n_oos"] if r["pick"] == "NEW" else -1e18, r["o_oos"] or 0) for r in rows)

cap_all = Counter(r["cap"] for r in rows)
cap_win = Counter(r["cap"] for r in adopted)

L = []
A = L.append
A(f"# Mega-Report — Cold-Start Re-Optimization with the Time-Cap Model")
A("")
A(f"**{date.today().isoformat()} · 9 markets × 6 timeframes = 54 champions · "
  f"cold start · 1-minute indicator frame · new time-cap search**")
A("")
A("Every figure below is the **exact on-screen dashboard number** (UI-verified), never the optimizer's "
  "own claim. That distinction is not pedantic — see *When the optimizer lied*, below.")
A("")
A("---")
A("")
A("## 1. Headline")
A("")
A("| | 2026 out-of-sample (the held-out year the tuning never saw) |")
A("|---|---|")
A(f"| Previous deployed suite | **{m(dep_oos)}** |")
A(f"| **New best-of-both suite** | **{m(fin_oos)}** |")
A(f"| **Gain** | **{m(fin_oos - dep_oos)} ({100*(fin_oos-dep_oos)/abs(dep_oos):.0f}%)** |")
A("")
A(f"- **{len(adopted)} new champions adopted** (they beat the incumbent out-of-sample)")
A(f"- **{len(held)} incumbents held** (the challenger did not beat them)")
A(f"- **{len(rejected)} challengers rejected outright** (they lose money)")
A("")
A("Nothing was promoted on the optimizer's word. Each slot was decided by the **2026 out-of-sample "
  "result**, because in-sample gains are exactly what overfitting looks like.")
A("")
A("---")
A("")
A("## 2. What we actually changed")
A("")
A("The optimizer had **never once** searched the end-of-day cap. It only ever tuned a bar-count cap, and "
  "the code silently forced that mode on. So we added the time cap as two independent questions — the same "
  "shape as the indicator questions:")
A("")
A("```mermaid")
A("flowchart TD")
A('    Q1["Use a max-hold BAR cap?<br/>(yes / no)"] -->|yes| N["How many 1-minute bars?<br/>(1 … 1440)"]')
A('    Q2["Force-close at END OF DAY?<br/>(yes / no)"]')
A('    N --> M{"both armed?"}')
A('    Q2 --> M')
A('    M -->|bar only| B["cap = bars(N)"]')
A('    M -->|eod only| E["cap = end-of-day"]')
A('    M -->|both| BO["cap = BOTH<br/>exit at whichever fires FIRST"]')
A('    M -->|neither| NO["cap = none"]')
A("```")
A("")
A("`both` did not exist before this work. Neither did a searchable `end-of-day`.")
A("")
A("### Did the new modes earn their place?")
A("")
A("| cap model | chosen by all 54 challengers | chosen by the champions that WON |")
A("|---|---:|---:|")
for k in ("none", "bars", "eod", "both"):
    A(f"| **{CAP_LABEL[k]}** | {cap_all.get(k,0)} | {cap_win.get(k,0)} |")
A("")
A(f"**Yes.** The two brand-new modes (`end-of-day` and `both`) account for "
  f"**{cap_win.get('eod',0)+cap_win.get('both',0)} of the {len(adopted)} winning champions** — work that was "
  "literally unreachable before today.")
A("")
A("---")
A("")
A("## 3. When the optimizer lied")
A("")
A("The optimizer scores trials with a fast approximate engine; the dashboard runs the exact causal one. "
  "They disagree — sometimes by the sign of the answer. This run caught two more cases:")
A("")
A("| Slot | Optimizer claimed | Reality (on-screen) | 2026 out-of-sample |")
A("|---|---:|---:|---:|")
A("| **NG 2m** | +$20,853 | **−$2,275** | **−$1,974** |")
A("| **NG 15m** | +$22,805 | +$3,470 | **−$1,870** |")
A("")
A("**NG 2m is the one that matters.** Had we trusted the optimizer, it would have replaced our best "
  "Natural Gas champion (+$30,294 / +$10,024 out-of-sample) with a strategy that *loses money*. "
  "Both were rejected; the incumbents stand.")
A("")
A("That is now **four** such lies caught by refusing to trust anything but the real dashboard number "
  "(Copper 2m, NG 15m twice, NG 2m).")
A("")
A("---")
A("")
A("## 4. Every slot, verified")
A("")
A("`cap` = the time-cap model the champion chose. **bold** = adopted.")
A("")
A("| Slot | Market | cap model | Old P/L | Old DD | Old 2026 | New P/L | New DD | **New 2026** | Verdict |")
A("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
for r in rows:
    cap = CAP_LABEL.get(r["cap"], r["cap"])
    if r["cap"] in ("bars", "both") and r["cap_n"]:
        cap += f" ({r['cap_n']})"
    v = {"NEW": "✅ **NEW**", "old": "old holds", "REJECT": "❌ **REJECT**"}[r["pick"]]
    A(f"| {r['inst']}_{r['tf']} | {NAMES[r['inst']]} | {cap} | {m(r['o_pnl'])} | "
      f"${(r['o_dd'] or 0):,.0f} | {m(r['o_oos'])} | {m(r['n_pnl'])} | ${r['n_dd']:,.0f} | "
      f"**{m(r['n_oos'])}** | {v} |")
A("")
A("---")
A("")
A("## 5. The biggest movers")
A("")
A("### Slots that were LOSING money out-of-sample and are now profitable")
A("")
A("| Slot | was | now |")
A("|---|---:|---:|")
for r in rows:
    if (r["o_oos"] or 0) < 0 and r["pick"] == "NEW":
        A(f"| {r['inst']}_{r['tf']} | {m(r['o_oos'])} | **{m(r['n_oos'])}** |")
A("")
A("### Largest out-of-sample gains")
A("")
A("| Slot | old 2026 | new 2026 | gain |")
A("|---|---:|---:|---:|")
for r in sorted(adopted, key=lambda x: -(x["n_oos"] - (x["o_oos"] or 0)))[:10]:
    A(f"| {r['inst']}_{r['tf']} | {m(r['o_oos'])} | **{m(r['n_oos'])}** | "
      f"**{m(r['n_oos'] - (r['o_oos'] or 0))}** |")
A("")
A("Silver and Gold were effectively rebuilt: Gold 15-minute went from **+$1,410** to **+$37,275** "
  "out-of-sample, Silver 5-minute from **+$4,240** to **+$18,924**.")
A("")
A("---")
A("")
A("## 6. Honest flags")
A("")
A("- **NG 15m remains non-feasible.** Old *and* new both lose money out-of-sample. **Do not trade it.**")
A("- **NQ 4h cannot be served by the dashboard.** Its default is hardcoded to a frozen anchor champion, "
  "so the UI will keep loading the old one even though the new champion is **+$22,395 better "
  "out-of-sample with less drawdown**. Unlocking that anchor is a decision, not a bug-fix — flagged for "
  "you.")
A("- **A cold start can go backwards.** 17 incumbents survived, some comfortably (ES 1h: +$29,035 vs "
  "+$12,015). That is expected: the old champions were *warm-started*, these were not. Keeping the winner "
  "per slot is the whole point.")
A("- **Low win rates** on some adopted champions (HG 15m at 16.3%, SI 5m at 38%) mean the profit rides on "
  "a few large winners. They pass out-of-sample, but they will feel bad to trade.")
A("")
A("---")
A("")
A("## 7. Method")
A("")
A("- **54 campaigns**, 5,900 trials each (59 search dimensions) ≈ **319,000 backtests**, 20 parallel "
  "workers, 5h59m.")
A("- **Cold start** — no warm-seeding from the previous champions.")
A("- **1-minute indicator frame** throughout (`--ind-1min`).")
A("- Champion per slot = top of the feasible Pareto front by **cross-validated median** P/L, not raw "
  "in-sample profit.")
A("- Every champion then re-run through the **real browser dashboard**, twice (full history + 2026), and "
  "the on-screen figure taken as truth.")
A("")
A("_Author: **Mulham Fetna** · contact@mulhamfetna.com · "
  "ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)_")

out = "/mnt/data/projects/trading/subprojects/Parametric-Indicators/docs/MEGA_REPORT_CAP_REOPTIMIZATION.md"
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w").write("\n".join(L) + "\n")
print(f"wrote {out}  ({len(L)} lines)")
print(f"adopted {len(adopted)} · held {len(held)} · rejected {len(rejected)}")
print(f"OOS {m(dep_oos)} -> {m(fin_oos)}  ({m(fin_oos-dep_oos)})")
