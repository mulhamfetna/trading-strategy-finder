"""Rebuild the bundle MANIFEST.json from champions/*.json — the champion files are the single source of
truth, so the manifest (and the README built from it) can never drift out of sync with what ships again."""
import json, os, re
from pathlib import Path

B = Path(os.path.expanduser("~/Mulham/wsg-i/playbooks_backtester"))
CH = B / "champions"

TF_ORDER = {t: i for i, t in enumerate(["4h", "2h", "1h", "15m", "5m", "2m"])}
INST_ORDER = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]


def num(lab, pat):
    m = re.search(pat, lab)
    if not m:
        return None
    sign = -1 if m.group(1) in ("-", "−") else 1
    return sign * float(m.group(2).replace(",", ""))


man = []
for f in sorted(CH.glob("*.json")):
    c = json.loads(f.read_text())
    p, lab = c["preset"], c["label"]
    inst, tf = c["instrument"], c["timeframe"]

    full = num(lab, r"([+-−]?)\$?([\d,]+) full")
    dd = num(lab, r"\$?([+-−]?)\$?([\d,]+) DD")
    win = re.search(r"([\d.]+)% win", lab)
    oos = num(lab, r"OOS-2026 ([+-−])\$([\d,]+)")

    man.append({
        "name": f.stem,
        "inst": inst,
        "tf": tf,
        "variant": p.get("ind_1min") is False,
        "full": int(full if full is not None else 0),
        "dd": int(abs(dd) if dd is not None else 0),
        "win": float(win.group(1)) if win else 0.0,
        "oos": int(oos) if oos is not None else None,
        "n_ind": sum(1 for s in p.get("indicators", []) if s.get("enabled")),
        "cap_1min": int(p.get("cap_1min") or 0),
        "flip": bool(p.get("flip")),
        "k": int(p.get("k") or 0),
        "label": lab,
    })

man.sort(key=lambda m: (INST_ORDER.index(m["inst"]), TF_ORDER[m["tf"]], m["variant"]))
json.dump(man, open(B / "MANIFEST.json", "w"), indent=1)

insts = sorted({m["inst"] for m in man}, key=INST_ORDER.index)
pos = sum(1 for m in man if (m["oos"] or 0) > 0)
print(f"MANIFEST rebuilt: {len(man)} champions across {len(insts)} markets {insts}")
print(f"  positive OOS: {pos}/{len(man)}")
for m in man:
    if (m["full"] or 0) <= 0 or (m["oos"] or 0) <= 0:
        print(f"  ⚠ weak slot: {m['name']:12} full ${m['full']:,} · OOS ${m['oos']:,}")
