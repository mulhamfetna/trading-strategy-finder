"""GAP-AWARE FILLS — every champion, before vs after, side by side (no time cap).

WHAT THIS ANSWERS. The engine used to fill every hard SL/TP exactly at its line, even when the bar had
already OPENED beyond it — a fill that never existed (GAP-01). As of 2026-07-20 it fills at the OPEN in
that case. This measures the effect on EVERY champion: 9 markets x 6 timeframes = 54 slots.

THE CONFIGURATION — "the last reported champion, WITHOUT time capping":
  * champion parameters come from optimize/results/wsh4_champions_full<_INST>.json (the stored,
    reported set — its NQ 4h full_pnl of 148,670.2 is exactly the old golden, so this IS the set the
    reports were built on);
  * the TIME CAP IS FORCED OFF for every slot (cap_mode="none", cap_1min=0), so all 54 are compared on
    the same, un-capped footing.

    ⚠️ SCOPE NOTE, stated plainly: a champion set that was *optimized* without the cap model exists ONLY
    for NQ (commit de23947 — the other 8 markets were onboarded later, after caps existed). So this is
    not "the pre-cap champions" for those markets; it is "the current champions, run with the cap off".
    That is the only definition under which all 54 slots can be compared like-for-like.

  * BEFORE = gap_fills=False (the old fill-at-the-line model — bit-for-bit the old behaviour)
  * AFTER  = gap_fills=True  (fill at the bar's OPEN when it gapped past the level)

Everything else is identical: same signals, same gate, same parameters, same data. ONLY the fill price
model differs, so every delta below is attributable to it.

BOTH WINDOWS are reported: `full` (the whole research window) and `oos2026` (the out-of-sample year).

  python3 -u optimize/reports/gap_fills/champion_gap_compare.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PI))

import presets                                        # noqa: E402
from optimize import l2 as _l2pkg                     # noqa: E402
from optimize.l2 import payload as L2                 # noqa: E402

RES = _PI / "optimize" / "results"
OUT = Path(__file__).resolve().parent / "champion_gap_compare.json"

INSTS = ["NQ", "ES", "GC", "SI", "CL", "NG", "HG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
KEYS = ["pnl", "max_dd"]
SKEYS = ["n_taken", "win"]


def metrics(inst, tf, lp):
    """Full metric set on BOTH windows, from the causal on-screen engine (the same path the dashboard
    and the playbooks use, so these numbers are the ones a reader can reproduce on screen)."""
    out = {}
    for key, win in (("full", "full"), ("oos2026", "2026")):
        p = dict(lp)
        p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b, s = pay["meta"]["boxes"], pay["meta"]["summary"]
        m = {k: b.get(k) for k in KEYS}
        m.update({k: s.get(k) for k in SKEYS})
        out[key] = m
    return out


def main() -> int:
    rows = []
    t0 = time.time()
    total = len(INSTS) * len(TFS)
    print(f"\nGAP-AWARE FILLS — {total} champions, time cap FORCED OFF, before vs after\n")
    hdr = (f"{'#':>3} {'mkt':4}{'tf':4} | {'BEFORE full':>12} {'AFTER full':>12} {'delta':>11} {'%':>7} "
           f"| {'BEFORE oos':>11} {'AFTER oos':>11} {'delta':>10}")
    print(hdr); print("-" * len(hdr))

    for inst in INSTS:
        suf = "" if inst == "NQ" else f"_{inst}"
        fp = RES / f"wsh4_champions_full{suf}.json"
        if not fp.exists():
            print(f"  !! missing champion file for {inst}: {fp.name}")
            continue
        champs = json.load(open(fp))
        for tf in TFS:
            i = len(rows) + 1
            if tf not in champs:
                print(f"[{i:2d}/{total}] {inst:3} {tf:3}  !! no champion stored for this slot")
                continue
            c = champs[tf]
            base = presets._preset(tf, c["box"], c.get("indicators", {}))
            base["ind_1min"] = True
            # FORCE THE TIME CAP OFF — the whole point is an un-capped like-for-like comparison.
            base["cap_mode"] = "none"
            base["cap_1min"] = 0

            rec = {"inst": inst, "tf": tf, "stored_full_pnl": c.get("full_pnl")}
            try:
                before = metrics(inst, tf, L2.validate_layer_params({**base, "gap_fills": False}))
                after = metrics(inst, tf, L2.validate_layer_params({**base, "gap_fills": True}))
                rec["before"], rec["after"] = before, after
                bf, af = before["full"]["pnl"], after["full"]["pnl"]
                bo, ao = before["oos2026"]["pnl"], after["oos2026"]["pnl"]
                pct = (100.0 * (af - bf) / abs(bf)) if bf else 0.0
                print(f"[{i:2d}/{total}] {inst:3} {tf:3} | {bf:>12,.0f} {af:>12,.0f} {af-bf:>+11,.0f} "
                      f"{pct:>6.1f}% | {bo:>11,.0f} {ao:>11,.0f} {ao-bo:>+10,.0f}", flush=True)
            except Exception as e:                                   # noqa: BLE001
                rec["err"] = str(e)[:200]
                print(f"[{i:2d}/{total}] {inst:3} {tf:3}  ERROR {rec['err']}", flush=True)
            rows.append(rec)
            json.dump(rows, open(OUT, "w"), indent=1)

    ok = [r for r in rows if "before" in r]
    if ok:
        bf = sum(r["before"]["full"]["pnl"] for r in ok)
        af = sum(r["after"]["full"]["pnl"] for r in ok)
        bo = sum(r["before"]["oos2026"]["pnl"] for r in ok)
        ao = sum(r["after"]["oos2026"]["pnl"] for r in ok)
        print("-" * len(hdr))
        print(f"{'':8}TOTAL | {bf:>12,.0f} {af:>12,.0f} {af-bf:>+11,.0f} "
              f"{100*(af-bf)/abs(bf) if bf else 0:>6.1f}% | {bo:>11,.0f} {ao:>11,.0f} {ao-bo:>+10,.0f}")
        flips = [r for r in ok if r["before"]["full"]["pnl"] > 0 >= r["after"]["full"]["pnl"]]
        if flips:
            print(f"\n  🚨 {len(flips)} champion(s) FLIP from profitable to losing under honest fills:")
            for r in flips:
                print(f"       {r['inst']:3} {r['tf']:3}  {r['before']['full']['pnl']:>+10,.0f} -> "
                      f"{r['after']['full']['pnl']:>+10,.0f}")
    print(f"\n  wrote {OUT}   ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
