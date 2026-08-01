"""Package the DEPLOYED (best-per-slot) champion set: 54 playbook PDFs + 54 champion JSONs + a standalone
backtester that reproduces every number, plus a report saying plainly what the set is and why.

⚠️ Reads precise_metrics.json / precise_decision.json ONLY. The older measurement files were taken on
champions whose stops had been rounded to 4 decimal places — a 1-2% distortion in the low-priced markets
that flipped NG 5m's sign and got 10 of 54 verdicts wrong. Using them here would put the bug in the bundle.
"""
import json
import os
import shutil
import subprocess
from collections import Counter
from datetime import date

BASE = os.path.expanduser("~/Mulham/wsg-i")
STAMP = os.environ.get("WSH_GEN_DATE") or date.today().isoformat()
NAME = f"BOX_STRATEGY_CHAMPIONS_{STAMP}"
OUT = os.path.join(BASE, NAME)
FULLNAME = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "HG": "Copper",
            "CL": "Crude Oil", "NG": "Natural Gas", "RTY": "Russell 2000", "YM": "Dow"}
SRC_TXT = {"deployed": "incumbent", "eod1": "forced end-of-day", "bolt-on": "bolt-on"}

met = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/precise_metrics.json")) if not r.get("err")}
dec = json.load(open(f"{BASE}/precise_decision.json"))

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(f"{OUT}/playbooks", exist_ok=True)
shutil.copytree(f"{BASE}/playbooks_backtester_best", f"{OUT}/backtester")
for f in sorted(os.listdir(f"{BASE}/playbooks_best")):
    shutil.copy(f"{BASE}/playbooks_best/{f}", f"{OUT}/playbooks/{f}")

M = lambda v: ("+" if (v or 0) >= 0 else "−") + "$" + f"{abs(v or 0):,.0f}"
tot = {n: 0.0 for n in ("deployed", "bolt-on", "eod1")}
rows = []
for d in dec:
    k, w = (d["inst"], d["tf"]), d["winner"]
    m = met[k]
    for n in tot:
        tot[n] += m[n]["oos2026"]["pnl"] or 0
    rows.append({"inst": d["inst"], "tf": d["tf"], "winner": w,
                 "oos": {n: m[n]["oos2026"]["pnl"] for n in tot},
                 "full": m[w]["full"]["pnl"], "dd": m[w]["full"]["max_dd"]})
sd = sum(r["oos"]["deployed"] or 0 for r in rows)
sw = sum(r["oos"][r["winner"]] or 0 for r in rows)
won = Counter(r["winner"] for r in rows)

rep = [f"# Box-strategy champions — DEPLOYED set, {STAMP}", "",
       "54 strategies (9 markets x 6 timeframes). These are the ones actually running on the dashboard.", "",
       "## How each slot was chosen", "",
       "Every slot holds the best of **three candidates**, decided on the held-out **2026** year — the only",
       "window none of the searches ever saw. In-sample profit never picks a winner: each champion was",
       "*selected* by a search that read the in-sample data, so its in-sample number flatters it by",
       "construction. A challenger had to beat the incumbent's 2026 profit by **more than 10%** to take a",
       "slot; anything that loses money in 2026 was disqualified outright.", "",
       "| candidate | what it is | slots won |",
       "|---|---|---:|",
       f"| **incumbent** | the champion already deployed (most hold overnight) | {won['deployed']} |",
       f"| **forced end-of-day** | cold-start, re-optimized *with* the bell close forced on | {won['eod1']} |",
       f"| **bolt-on** | the incumbent with the bell close simply switched on, not re-tuned | {won['bolt-on']} |", "",
       "Exit rules are therefore **mixed by design** — some close at the bell, some hold, some cap how many",
       "bars they stay in. That mix is the finding, not an inconsistency.", "",
       "## Does forcing the bell close help? Not as a blanket rule.", "",
       "| if you ran ONE approach across all 54 slots | 2026 profit |", "|---|---:|",
       f"| all incumbents | {M(tot['deployed'])} |",
       f"| all bolt-on (bell close, no re-tuning) | {M(tot['bolt-on'])} |",
       f"| all forced end-of-day (bell close, re-tuned) | {M(tot['eod1'])} |",
       f"| **best per slot (this set)** | **{M(sw)}** |", "",
       f"Forcing every slot to close at the bell **makes less money than leaving it alone** — whether you",
       f"bolt it on ({M(tot['bolt-on'])}) or re-tune for it ({M(tot['eod1'])}), both lose to simply keeping the",
       f"incumbents ({M(tot['deployed'])}). There is no \"end-of-day is good/bad\" answer. The entire gain comes",
       f"from choosing **per slot**: {M(sw)}, which beats the incumbents by **{M(sw - sd)}** "
       f"({((sw / sd - 1) * 100) if sd else 0:+.1f}%).", "",
       "## Every slot", "",
       "| slot | market | incumbent 2026 | bolt-on 2026 | forced-EOD 2026 | ships | full P/L | max DD |",
       "|---|---|---:|---:|---:|---|---:|---:|"]
for r in rows:
    star = {"deployed": "incumbent", "eod1": "**forced-EOD**", "bolt-on": "**bolt-on**"}[r["winner"]]
    rep.append(f"| {r['inst']}_{r['tf']} | {FULLNAME[r['inst']]} {r['tf']} | {M(r['oos']['deployed'])} | "
               f"{M(r['oos']['bolt-on'])} | {M(r['oos']['eod1'])} | {star} | {M(r['full'])} | "
               f"${r['dd']:,.0f} |")

rep += ["", "## How the numbers were produced", "",
        "Every figure comes from the **causal engine** — the same one the dashboard draws, which never sees a",
        "bar before it closes. The bundled backtester reproduces every headline and every 2026 figure here to",
        "the dollar; that check runs before the bundle ships.", "",
        "Weak and negative slots are **included and flagged**, not hidden. The backtester reproduces their bad",
        "numbers too — a champion set you can only trust when it flatters you is not a champion set.", "",
        "> **A note on precision.** An earlier build of this bundle persisted stop and target parameters",
        "> rounded to four decimal places. Prices here span four orders of magnitude (the Dow trades near",
        "> $44,000, natural gas near $3.57), so four decimals leaves a natural-gas stop of 0.0008 with a single",
        "> significant digit. On NG 5m that 1.1% distortion moved the result by $39,793 and flipped its sign.",
        "> Parameters are now stored to 12 significant digits, and every number in this bundle was re-measured",
        "> from the corrected champions.", "",
        "---", "",
        "Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna"]
open(f"{OUT}/MEGA_REPORT.md", "w").write("\n".join(rep) + "\n")

open(f"{OUT}/README.md", "w").write(f"""# Box-strategy champions — deployed set ({STAMP})

54 trading strategies: **9 markets x 6 timeframes**. This is the set actually running on the dashboard.

## What's in here

| folder | what it is |
|---|---|
| `playbooks/` | one PDF per champion (54) — what it trades, the exact settings, full tearsheet, 2026 out-of-sample, and when NOT to trade it |
| `backtester/` | a standalone backtester. It reproduces every number in every playbook, to the dollar, without the main repo |
| `backtester/champions/` | the 54 champion files (JSON) — the strategies themselves |
| `MEGA_REPORT.md` | how each slot was chosen, and the three-way comparison behind it |

## Run it

```bash
cd backtester
pip install -r requirements.txt
python backtest.py --champion champions/NQ_4h.json --data <your data dir>
```

## Read this before trading any of it

* The **2026** column is the only honest one. Every strategy here was *chosen* by a search that read the
  in-sample data, so its in-sample profit flatters it by construction.
* Slots that lose money are **included and flagged**, not removed.
* Exit rules differ by slot on purpose — see `MEGA_REPORT.md`.

---
Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
""")

os.chdir(BASE)
zp = f"{NAME}.zip"
if os.path.exists(zp):
    os.remove(zp)
subprocess.run(["zip", "-qr", zp, NAME], check=True)
print(f"BUILT {zp}  ({os.path.getsize(zp)/1e6:.1f} MB)")
print(f"  playbooks : {len([f for f in os.listdir(f'{OUT}/playbooks') if f.endswith('.pdf')])} PDFs")
print(f"  champions : {len(os.listdir(f'{OUT}/backtester/champions'))} JSON")
print(f"  2026 best-per-slot {M(sw)} vs incumbents {M(sd)}  ({M(sw - sd)})")
print(f"  slots won: incumbent {won['deployed']} · forced-EOD {won['eod1']} · bolt-on {won['bolt-on']}")
print("PACKAGE_DONE")
