"""Verify the shareable bundle reproduces all 54 deployed champions to the dollar (headline AND 2026 OOS).

Stages each market's data into the bundle's naming convention, then runs the bundle's own backtest.py per
champion and compares against the number recorded in its label.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(os.path.expanduser("~/Mulham/wsg-i"))
REPO = BASE / "Parametric-Indicators"
BUNDLE = BASE / "playbooks_backtester_eod1"
DATA = BASE / "bundle_data_all"
DATA.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO))
from optimize import instruments as I  # noqa: E402

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

for inst in INSTS:
    for tf in TFS:
        dec, minute, box = I.resolve_paths(inst, tf)
        for src, dst in ((dec, DATA / f"{inst}_{tf}.csv"),
                         (minute, DATA / f"{inst}_1m.csv"),
                         (box, DATA / f"{inst}_box.csv")):
            if not dst.exists():
                shutil.copy(src, dst)
print(f"staged {len(list(DATA.iterdir()))} data files", flush=True)

rows, bad = [], 0
total = len(INSTS) * len(TFS)
for inst in INSTS:
    for tf in TFS:
        slot = f"{inst}_{tf}"
        cf = BUNDLE / "champions" / f"{slot}.json"
        lab = json.loads(cf.read_text())["label"]
        rec_pnl = float(re.search(r"([+-])\$([\d,]+) full", lab).group(2).replace(",", "")) * \
            (1 if re.search(r"([+-])\$([\d,]+) full", lab).group(1) == "+" else -1)
        mo = re.search(r"OOS-2026 ([+-])\$([\d,]+)", lab)
        rec_oos = float(mo.group(2).replace(",", "")) * (1 if mo.group(1) == "+" else -1)

        p = subprocess.run([sys.executable, "backtest.py", "--champion", str(cf),
                            "--data", str(DATA), "--out", f"/tmp/tr_{slot}.csv"],
                           cwd=BUNDLE, capture_output=True, text=True, timeout=3600)

        def grab(pat):
            m = re.search(pat + r"\s*:\s*\$(-?[\d,]+)", p.stdout, re.I)
            return None if not m else float(m.group(1).replace(",", ""))

        got, got_oos = grab(r"net P/L"), grab(r"2026 out-of-sample")
        if got is None:
            print(f"{slot:9}: PARSE-FAIL  {p.stdout[-200:]} {p.stderr[-200:]}", flush=True)
            bad += 1
            continue
        ok = abs(got - rec_pnl) < 1.0 and (got_oos is None or abs(got_oos - rec_oos) < 1.0)
        bad += 0 if ok else 1
        print(f"{slot:9}: bundle ${got:>10,.0f} / OOS ${got_oos or 0:>9,.0f}   "
              f"recorded ${rec_pnl:>10,.0f} / OOS ${rec_oos:>9,.0f}   {'OK' if ok else 'MISMATCH'}",
              flush=True)
        rows.append({"slot": slot, "bundle": got, "recorded": rec_pnl,
                     "bundle_oos": got_oos, "recorded_oos": rec_oos, "ok": ok})

json.dump(rows, open(BASE / "eod1_bundle_verify.json", "w"), indent=1)
print(f"\nDONE: {len(rows) - bad}/{total} reproduce exactly" + (f"  ({bad} BAD)" if bad else ""),
      flush=True)
print("BUNDLEVERIFY_DONE", flush=True)
