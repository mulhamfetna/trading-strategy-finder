"""Verify the shareable bundle reproduces the 12 CL+NG champions to the dollar.

Stages CL/NG data into a bundle-layout data folder (<INST>_<tf>.csv / <INST>_1m.csv / <INST>_box.csv)
using the repo's own resolve_paths, then runs bundle/backtest.py for each champion and compares the
bundle's headline P/L against the UI-verified on-screen number recorded in the champion label.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

BASE = Path(os.path.expanduser("~/Mulham/wsg-i"))
REPO = BASE / "Parametric-Indicators"
BUNDLE = BASE / "playbooks_backtester"
DATA = BASE / "bundle_data_clng"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
INSTS = ["CL", "NG"]

sys.path.insert(0, str(REPO))
from optimize import instruments as I  # noqa: E402

DATA.mkdir(exist_ok=True)

# ---- stage data in the bundle's naming convention -------------------------------------------------
for inst in INSTS:
    for tf in TFS:
        dec, minute, box = I.resolve_paths(inst, tf)
        for src, dst in ((dec, DATA / f"{inst}_{tf}.csv"),
                         (minute, DATA / f"{inst}_1m.csv"),
                         (box, DATA / f"{inst}_box.csv")):
            if not dst.exists():
                shutil.copy(src, dst)
print(f"staged data -> {DATA} ({len(list(DATA.iterdir()))} files)", flush=True)

# ---- run the bundle per champion and compare ------------------------------------------------------
rows, bad = [], 0
for inst in INSTS:
    for tf in TFS:
        cf = BUNDLE / "champions" / f"{inst}_{tf}.json"
        champ = json.loads(cf.read_text())
        lab = champ["label"]
        rec_pnl = float(re.search(r"([+-])\$([\d,]+) full", lab).group(2).replace(",", "")) * \
            (1 if re.search(r"([+-])\$([\d,]+) full", lab).group(1) == "+" else -1)
        mo = re.search(r"OOS-2026 ([+-])\$([\d,]+)", lab)
        rec_oos = float(mo.group(2).replace(",", "")) * (1 if mo.group(1) == "+" else -1)

        p = subprocess.run([sys.executable, "backtest.py", "--champion", str(cf),
                            "--data", str(DATA), "--out", f"/tmp/trades_{inst}_{tf}.csv"],
                           cwd=BUNDLE, capture_output=True, text=True, timeout=3600)

        def grab(pat):
            m = re.search(pat + r"\s*:\s*\$(-?[\d,]+)", p.stdout, re.I)
            return None if not m else float(m.group(1).replace(",", ""))

        got, got_oos = grab(r"net P/L"), grab(r"2026 out-of-sample")
        if got is None:
            print(f"{inst} {tf:3}: PARSE-FAIL\n{p.stdout[-600:]}\n{p.stderr[-400:]}", flush=True)
            bad += 1
            continue
        ok = abs(got - rec_pnl) < 1.0 and (got_oos is None or abs(got_oos - rec_oos) < 1.0)
        bad += 0 if ok else 1
        print(f"{inst} {tf:3}: bundle ${got:>10,.0f} / OOS ${got_oos or 0:>9,.0f}   "
              f"recorded ${rec_pnl:>10,.0f} / OOS ${rec_oos:>9,.0f}   {'OK' if ok else 'MISMATCH'}", flush=True)
        rows.append({"inst": inst, "tf": tf, "bundle": got, "recorded": rec_pnl,
                     "bundle_oos": got_oos, "recorded_oos": rec_oos, "ok": ok})

json.dump(rows, open(BASE / "clng_bundle_verify.json", "w"), indent=1)
print(f"\nDONE: {len(rows) - bad}/{len(rows)} reproduce exactly" + (f"  ({bad} BAD)" if bad else ""), flush=True)
