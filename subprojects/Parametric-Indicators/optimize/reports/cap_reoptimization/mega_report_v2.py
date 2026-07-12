"""MEGA REPORT v2 — the corrected one.

Every number recomputed on the fixed engine (the caps are finally honored end-to-end). Sources:
  honest_compare.json  — both champions, every slot, corrected on-screen P/L + 2026 OOS
  honest_verdict.json  — who won each slot
  final_presets_raw.json — the exact preset the dashboard sends (cap model per champion)
"""
import json
import os
from collections import Counter
from datetime import date

T = os.path.expanduser("/mnt/data/projects/trading/subprojects/Parametric-Indicators/"
                       "optimize/reports/cap_reoptimization")
rows = [r for r in json.load(open(f"{T}/honest_compare.json")) if r.get("old") and r.get("new")]
v = json.load(open(f"{T}/honest_verdict.json"))
presets = {(p["inst"], p["tf"]): p["collect"] for p in json.load(open(f"{T}/final_presets_raw.json"))}
new_wins, rejects = set(v["new_wins"]), set(v["rejects"])

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
NAMES = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "HG": "Copper",
         "CL": "Crude Oil", "NG": "Natural Gas", "RTY": "Russell 2000", "YM": "Dow"}
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
CAPL = {"none": "no cap", "bars": "bars({n})", "eod": "end-of-day",
        "both": "both({n}) — whichever first"}
rows.sort(key=lambda r: (INSTS.index(r["inst"]), TFS.index(r["tf"])))


def m(x):
    return ("+" if x >= 0 else "−") + "$" + f"{abs(x):,.0f}"


dep = sum(r["old"]["oos"] for r in rows)
fin = sum((r["new"]["oos"] if f"{r['inst']}_{r['tf']}" in new_wins else r["old"]["oos"]) for r in rows)
adopted = [r for r in rows if f"{r['inst']}_{r['tf']}" in new_wins]
held = [r for r in rows if f"{r['inst']}_{r['tf']}" not in new_wins and f"{r['inst']}_{r['tf']}" not in rejects]

cap_all = Counter(presets[(r["inst"], r["tf"])].get("cap_mode", "?") for r in rows)
cap_dep = Counter(presets[(r["inst"], r["tf"])].get("cap_mode", "?") for r in rows)

L = []
A = L.append
A("# Mega-Report — Cold-Start Re-Optimization with the Time-Cap Model")
A("")
A(f"**{date.today().isoformat()} · 9 markets × 6 timeframes = 54 champions · cold start · "
  "1-minute indicator frame · new time-cap search**")
A("")
A("> ⚠️ **This report supersedes an earlier version whose out-of-sample numbers were wrong.** The engine "
  "that produced them silently discarded the time-cap parameters, so every 2026 figure in the project — "
  "for the incumbents *and* the challengers — was measured with the cap switched off. That is fixed; "
  "everything below is recomputed. See §6.")
A("")
A("---")
A("")
A("## 1. Headline")
A("")
A("| | 2026 out-of-sample — the held-out year the tuning never saw |")
A("|---|---|")
A(f"| Previous deployed suite | **{m(dep)}** |")
A(f"| **New best-of-both suite** | **{m(fin)}** |")
A(f"| **Gain** | **{m(fin - dep)} ({100 * (fin - dep) / abs(dep):.0f}%)** |")
A("")
A(f"- **{len(adopted)} new champions adopted** — they beat the incumbent out-of-sample")
A(f"- **{len(held)} incumbents held** — the challenger did not beat them")
A(f"- **{len(rejects)} challengers rejected** — they lose money ({', '.join(sorted(rejects))})")
A("")
A("Every slot was decided on the **2026 out-of-sample result**, never on in-sample profit. That matters: "
  "ES 2h earned **$28,649 MORE in-sample** and **$5,526 LESS out-of-sample** — textbook overfitting, and "
  "the incumbent held.")
A("")
A("---")
A("")
A("## 2. What we changed")
A("")
A("The optimizer had **never once** searched the end-of-day cap. It only ever tuned a bar-count cap, and "
  "the code silently forced that mode on. The cap is now two independent questions — the same shape as "
  "the indicator questions:")
A("")
A("```mermaid")
A("flowchart TD")
A('    Q1["Use a max-hold BAR cap?"] -->|yes| N["How many 1-minute bars?"]')
A('    Q2["Force-close at END OF DAY?"]')
A('    N --> M{"both armed?"}')
A('    Q2 --> M')
A('    M -->|bar only| B["bars(N)"]')
A('    M -->|eod only| E["end-of-day"]')
A('    M -->|both| BO["BOTH — exit at whichever fires FIRST"]')
A('    M -->|neither| NO["no cap"]')
A("```")
A("")
A("**`both` did not exist before this work. Neither did a searchable `end-of-day`.**")
A("")
A("### Which cap model the 54 deployed champions actually use")
A("")
A("| cap model | champions |")
A("|---|---:|")
for k in ("none", "bars", "eod", "both"):
    A(f"| {CAPL[k].split('(')[0].strip()} | {cap_dep.get(k, 0)} |")
A("")
A(f"The two new modes account for **{cap_dep.get('eod', 0) + cap_dep.get('both', 0)} of the 54** deployed "
  "champions — strategies that were literally unreachable before today.")
A("")
A("---")
A("")
A("## 3. Every slot, corrected")
A("")
A("Both columns are on-screen figures from the fixed engine. **Bold = deployed.**")
A("")
A("| Slot | Market | cap model | Old P/L | Old 2026 | New P/L | New 2026 | Verdict |")
A("|---|---|---|---:|---:|---:|---:|---|")
for r in rows:
    slot = f"{r['inst']}_{r['tf']}"
    o, n = r["old"], r["new"]
    p = presets[(r["inst"], r["tf"])]
    cap = CAPL.get(p.get("cap_mode", "?"), "?").format(n=int(p.get("cap_1min") or 0))
    if slot in rejects:
        vd = "❌ **REJECT**"
    elif slot in new_wins:
        vd = "✅ **NEW**"
    else:
        vd = "old holds"
    A(f"| {slot} | {NAMES[r['inst']]} | {cap} | {m(o['pnl'])} | {m(o['oos'])} | "
      f"{m(n['pnl'])} | {m(n['oos'])} | {vd} |")
A("")
A("---")
A("")
A("## 4. The biggest movers")
A("")
A("### Slots that were LOSING money out-of-sample and are now profitable")
A("")
A("| Slot | was | now |")
A("|---|---:|---:|")
for r in adopted:
    if r["old"]["oos"] < 0:
        A(f"| {r['inst']}_{r['tf']} | {m(r['old']['oos'])} | **{m(r['new']['oos'])}** |")
A("")
A("### Largest out-of-sample gains")
A("")
A("| Slot | cap model | old 2026 | new 2026 | gain |")
A("|---|---|---:|---:|---:|")
for r in sorted(adopted, key=lambda x: -(x["new"]["oos"] - x["old"]["oos"]))[:10]:
    p = presets[(r["inst"], r["tf"])]
    cap = CAPL.get(p.get("cap_mode", "?"), "?").format(n=int(p.get("cap_1min") or 0))
    A(f"| {r['inst']}_{r['tf']} | {cap} | {m(r['old']['oos'])} | **{m(r['new']['oos'])}** | "
      f"**{m(r['new']['oos'] - r['old']['oos'])}** |")
A("")
A("**Gold is now perfect — all six timeframes adopted.** Silver: five of six.")
A("")
A("---")
A("")
A("## 5. When the optimizer lied")
A("")
A("The optimizer scores trials with a fast approximate engine; the dashboard runs the exact causal one. "
  "They disagree — sometimes about the *sign*:")
A("")
A("| Slot | Optimizer claimed | Reality | 2026 OOS |")
A("|---|---:|---:|---:|")
A("| **NG 2m** | +$20,853 | **−$2,275** | **−$1,909** |")
A("| **NG 15m** | +$22,805 | +$3,470 | **−$1,880** |")
A("")
A("**NG 2m is the one that matters.** On the optimizer's word it would have replaced our best Natural Gas "
  "champion (+$30,294 / +$9,758 out-of-sample) with a strategy that **loses money**. Both rejected.")
A("")
A("---")
A("")
A("## 6. Four bugs this campaign exposed (all fixed, all tested)")
A("")
A("The campaign was worth running for the champions. It may have been worth more for these:")
A("")
A("1. **`core.py` never passed the cap to the optimizer's scorer.** A trial could be *recorded* as an "
  "end-of-day champion while being *scored* with no cap at all. Caught before launch; without it the "
  "entire 6-hour run would have been meaningless.")
A("2. **`build_payload` discarded the caps**, so **every out-of-sample number ever reported** — "
  "incumbents, challengers, playbooks, bundle — was measured with the cap off. This is why this report "
  "supersedes the last one.")
A("3. **`report_wsi` stripped the cap off every LEGACY champion.** Legacy studies predate the cap "
  "switches, so a truthiness test on a missing parameter silently zeroed the cap — quietly rewriting the "
  "deployed champions. Caught only because CL 2h re-measured at $4,201 having verified at $10,448 hours "
  "earlier.")
A("4. **The dashboard could not represent `both`.** Its cap dropdown had three options; a `both` champion "
  "fell back to `none`, and the backend then ran it as bars-only. 15 champions use `both` — the UI was "
  "executing a different strategy than the one on file.")
A("")
A("Plus two in the shareable bundle: it priced **Copper, Oil and Gas at the Nasdaq's point value** "
  "(Copper 15m: $41,588 → $33), and read its out-of-sample from a different field than its headline.")
A("")
A("---")
A("")
A("## 7. Honest flags")
A("")
A("- **NG 15m is non-feasible.** Old *and* new both lose money out-of-sample. **Do not trade it.**")
A("- **A cold start can go backwards.** 18 incumbents survived, some comfortably (ES 1h: +$28,193 vs "
  "+$12,015). Expected — the old champions were warm-started, these were not. Keeping the winner per slot "
  "is the entire point.")
A("- **Low win rates** on some adopted champions mean profit rides on a few large winners. They pass "
  "out-of-sample, but they will feel bad to trade.")
A("- **NQ 1h**: the legacy chart engine and the causal engine disagree on this champion ($80,339 vs "
  "$77,439). The causal number is what we deploy and what the bundle reproduces; the divergence is an "
  "open item.")
A("")
A("---")
A("")
A("## 8. Method")
A("")
A("- **54 campaigns**, 5,900 trials each (59 dimensions) ≈ **319,000 backtests**, 20 parallel workers, "
  "**5h59m**.")
A("- **Cold start** — no warm-seeding from the previous champions.")
A("- **1-minute indicator frame** throughout.")
A("- Champion per slot = top of the feasible Pareto front by **cross-validated median** P/L.")
A("- Both champions of every slot then re-run on the fixed engine for the full history **and** the "
  "held-out 2026 year; the winner is the one that holds up **out-of-sample**.")
A("- The shareable bundle reproduces all **54/54** to the dollar — headline *and* out-of-sample.")
A("")
A("_Author: **Mulham Fetna** · contact@mulhamfetna.com · "
  "ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)_")

out = ("/mnt/data/projects/trading/subprojects/Parametric-Indicators/docs/"
       "MEGA_REPORT_CAP_REOPTIMIZATION.md")
open(out, "w").write("\n".join(L) + "\n")
print(f"wrote {out}")
print(f"adopted {len(adopted)} · held {len(held)} · rejected {len(rejects)}")
print(f"OOS {m(dep)} -> {m(fin)}  ({m(fin - dep)})")
print(f"cap models deployed: {dict(cap_dep)}")
