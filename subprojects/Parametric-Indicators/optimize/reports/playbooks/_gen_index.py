"""Regenerate INDEX.md for the playbook suite from the bundle MANIFEST.json (single source of truth).

Verdict rules mirror build_playbooks.verdict_for() exactly, so the index and the PDFs can never disagree:
  non-feasible : full-window P/L <= 0, OR (a flagged slot whose 2026 loss exceeds half its drawdown)
  caution      : profitable in-sample but carries >=1 honest flag (negative/flat OOS, thin cushion, low win)
  deployable   : clears the bar, positive and holds out-of-sample

Run:  python3 _gen_index.py  (writes INDEX.md next to the PDFs)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAN = HERE.parent.parent.parent / "shareable" / "playbooks_backtester" / "MANIFEST.json"

FULL = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "HG": "Copper",
        "CL": "Crude Oil", "NG": "Natural Gas", "RTY": "Russell 2000", "YM": "Dow"}
INST_ORDER = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TF_ORDER = {t: i for i, t in enumerate(["4h", "2h", "1h", "15m", "5m", "2m"])}

man = json.loads(MAN.read_text())
man.sort(key=lambda m: (INST_ORDER.index(m["inst"]), TF_ORDER[m["tf"]], m["variant"]))


def money(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"


def verdict(m):
    """Mirror of build_playbooks.verdict_for()."""
    fp, fdd, fw, op = m["full"], m["dd"], m["win"], m["oos"]
    reasons = []
    rdd = (fp / fdd) if (fp and fdd) else None
    if fp is None or fp <= 0:
        return "✗ Non-feasible", ["loses money in-sample"]
    if op is not None and op < 0:
        reasons.append(f"loses {money(op)} out-of-sample")
    elif op is not None and fdd and 0 <= op < 0.10 * fdd:
        reasons.append(f"essentially flat out-of-sample ({money(op)} vs ${fdd:,.0f} DD)")
    if rdd is not None and rdd < 1:
        reasons.append("drawdown exceeds total profit")
    if fw is not None and fw < 35:
        reasons.append(f"low win rate ({fw:.0f}%)")
    if not reasons:
        return "✓ Deployable", []
    severe = (op is not None and fdd and op < -0.5 * fdd)
    return ("✗ Non-feasible" if severe else "⚠ Caution"), reasons


rows, tally = [], {"✓ Deployable": 0, "⚠ Caution": 0, "✗ Non-feasible": 0}
for m in man:
    v, reasons = verdict(m)
    tally[v] += 1
    name = m["name"]
    rows.append(f"| `{name}` | {FULL[m['inst']]} | {v} | ${m['full']:,.0f} | ${m['dd']:,.0f} | "
                f"{m['win']:.1f}% | {money(m['oos'])} | {'; '.join(reasons) if reasons else '—'} |")

n = len(man)
pos = sum(1 for m in man if (m["oos"] or 0) > 0)
n_mkt = len({m["inst"] for m in man})
n_var = sum(1 for m in man if m["variant"])

INDEX = f"""# Shareable Playbooks — {n_mkt} markets × 6 timeframes ({n - n_var} + {n_var} variant = {n})

_Numbers captured live from the dashboard UI (on-screen `meta.boxes` = truth); 2026 out-of-sample from the
held-out 2026 backtest. Every champion is reproduced to the dollar by the shareable backtester bundle._

**{tally['✓ Deployable']} Deployable ✓ · {tally['⚠ Caution']} Caution ⚠ · {tally['✗ Non-feasible']} Non-feasible ✗ · {pos}/{n} profitable out-of-sample (2026).**

Each `<INST>_<TF>_playbook.pdf` is a self-contained pageless PDF: verdict, what-it-is, copy-paste champion
settings, how-it-trades (Mermaid), full tearsheet + embedded dashboard snapshot, 2026 out-of-sample, and
honest when-NOT-to-trade guidance.

| Playbook | Market | Verdict | Full P/L | Max DD | Win | 2026 OOS | Flags |
|---|---|---|--:|--:|--:|--:|---|
{chr(10).join(rows)}

---
_Author: **Mulham Fetna** · contact@mulhamfetna.com · ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)_
"""

(HERE / "INDEX.md").write_text(INDEX)
print(f"wrote INDEX.md — {n} playbooks, {n_mkt} markets, {tally}, {pos}/{n} positive OOS")
