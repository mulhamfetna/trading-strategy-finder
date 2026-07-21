"""ASIA-CELL OUT-OF-SAMPLE — does the 22:00 session edge REPLICATE across markets, or is it an NQ fluke?

THE FINDING UNDER TEST (S3, SESSION-03). On NQ's 4h champion, entries at the 22:00 ET boundary (the "Asia"
session) earned ~+$364/trade and held across both halves of the data. It was FROZEN, not acted on, for
one reason: it is 1 winning cell out of 6, on n=89 — exactly the multiple-comparisons / fluke-window trap.

WHY THIS IS THE RIGHT OOS TEST (and why the obvious one is impossible). The obvious out-of-sample test —
run the NQ champion over 2010-2023 (unseen when S3 was found on 2025-2026) — CANNOT be done: the box
levels the strategy trades on are externally scraped and exist only for ~2025-2026 (NQ_full_data.csv is
364 rows). 16 years of price does not help when the levels do not exist for it.

So we use CROSS-INSTRUMENT REPLICATION — the same discipline that confirmed the GC news finding. The 22:00
effect was discovered on NQ; if it is a REAL session effect it must show on the other EQUITY INDICES,
which share NQ's exact session clock (ES, YM, RTY: RTH 09:30-16:00 ET, Asia overnight). Those three are
INDEPENDENT data the finding was not selected on. The commodities (GC/SI/CL/NG/HG) are a looser control —
same ET clock, different liquidity calendar.

PRE-DECLARED READING (before the run):
  * REAL   ⇒ the 22:00 cell is positive AND beats the pooled mean on the equity indices too (ES/YM/RTY),
             and the pooled equity-index 22:00 cell clears a permutation null.
  * FLUKE  ⇒ 22:00 is positive on NQ only; the other indices are null or negative. Stays frozen/dead.

Per-cell null: permute which trades belong to which entry-hour and ask how often a RANDOM cell of the
same size beats the observed 22:00 mean. That is the honest test for "1 good cell out of many".

  WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 -u optimize/fundamentals/study_asia_oos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals                    # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int      # noqa: E402
from optimize.fundamentals.champion_params import champion_stops    # noqa: E402
from perf._common import champion_preset                            # noqa: E402

EQUITY = ["NQ", "ES", "YM", "RTY"]           # share the exact session clock — the replication group
COMMOD = ["GC", "SI", "CL", "NG", "HG"]      # same ET clock, different calendar — the control group
ASIA_HOUR = 22                               # the 4h boundary the S3 finding lives on
TF = "4h"
N_PERM = 20000


def champion_trades(inst):
    p = champion_preset(TF)                                  # NQ champion params; per-inst via resolve below
    # champion_preset is NQ-keyed; for non-NQ we need that market's own champion.
    import json
    suf = "" if inst == "NQ" else f"_{inst}"
    cf = Path(__file__).resolve().parents[1] / "results" / f"wsh4_champions_full{suf}.json"
    champ = json.loads(cf.read_text())[TF]
    import presets
    base = presets._preset(TF, champ["box"], champ.get("indicators", {}))
    base["ind_1min"] = True
    ss, sh, tp = float(champ["box"]["sl_soft"]), float(champ["box"]["sl_hard"]), float(champ["box"]["tp"])
    flip = bool(champ["box"].get("flip", False))
    gp = float(champ["box"]["gate_pct"])

    df, df1, box, vf, n = data.load_inputs(TF, instrument=inst)
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    pv = instruments.point_value(inst)
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), ss, sh, tp, flip,
                      m_open=df1["Open"].to_numpy(float))
    if not F:
        return None
    hrs = np.array([pd.Timestamp(t["entry_time"]).hour for t in F])
    pnl = np.array([float(t["pnl_points"]) for t in F]) * pv
    return hrs, pnl


def asia_cell(inst, rng):
    r = champion_trades(inst)
    if r is None:
        return None
    hrs, pnl = r
    m = hrs == ASIA_HOUR
    n_asia = int(m.sum())
    if n_asia < 5:
        return {"inst": inst, "n_asia": n_asia, "note": "too few 22:00 entries"}
    asia_mean = float(pnl[m].mean())
    pooled_mean = float(pnl.mean())
    win = float((pnl[m] > 0).mean())
    # per-cell null: how often does a RANDOM cell of size n_asia beat the observed 22:00 mean?
    null = np.array([rng.choice(pnl, n_asia, replace=False).mean() for _ in range(N_PERM)])
    p = float((null >= asia_mean).mean())
    return {"inst": inst, "n_all": len(pnl), "n_asia": n_asia, "asia_mean": asia_mean,
            "pooled_mean": pooled_mean, "excess": asia_mean - pooled_mean, "win": win, "p": p,
            "asia_pnl": pnl[m]}


def main() -> int:
    rng = np.random.default_rng(0)
    print(f"\nASIA-CELL OOS — 22:00 ET entry, {TF} champion, per market (gap-aware fills)\n")
    print(f"  {'mkt':4} {'grp':6} {'n(all)':>7} {'n(22h)':>7} {'$/trade @22h':>13} "
          f"{'pooled $/tr':>12} {'excess':>10} {'win%':>6} {'perm p':>8}")
    print("-" * 92)

    eq_pnls = []
    for grp, insts in (("EQUITY", EQUITY), ("COMMOD", COMMOD)):
        for inst in insts:
            try:
                r = asia_cell(inst, rng)
            except Exception as e:                                  # noqa: BLE001
                print(f"  {inst:4} {grp:6}  ERROR {str(e)[:60]}")
                continue
            if r is None or "asia_mean" not in r:
                print(f"  {inst:4} {grp:6}  {r.get('note','no trades') if r else 'no trades'}")
                continue
            star = " <-- replicates (p<.05, positive)" if (r["p"] < 0.05 and r["asia_mean"] > 0) else ""
            print(f"  {inst:4} {grp:6} {r['n_all']:>7} {r['n_asia']:>7} {r['asia_mean']:>+13,.0f} "
                  f"{r['pooled_mean']:>+12,.0f} {r['excess']:>+10,.0f} {100*r['win']:>5.1f}% {r['p']:>8.3f}{star}")
            if grp == "EQUITY":
                eq_pnls.append(r["asia_pnl"])

    # POOLED EQUITY-INDEX verdict — the tight replication group, all sharing NQ's session clock.
    print("\n" + "=" * 92)
    print("POOLED EQUITY-INDEX 22:00 CELL (NQ+ES+YM+RTY — the tight replication group)")
    print("=" * 92)
    if eq_pnls:
        allp = np.concatenate(eq_pnls)
        mean = allp.mean()
        t = mean / (allp.std(ddof=1) / np.sqrt(len(allp))) if allp.std(ddof=1) > 0 else 0.0
        # sign-flip / one-sample bootstrap p that the pooled 22:00 mean > 0
        boot = np.array([rng.choice(allp, len(allp), replace=True).mean() for _ in range(N_PERM)])
        p0 = float((boot <= 0).mean())
        print(f"  n={len(allp)}  mean ${mean:+,.0f}/trade  sd ${allp.std():,.0f}  t={t:+.2f}  "
              f"P(mean>0)={1-p0:.3f}")
        print(f"  NQ-alone was +$364/trade on n=89. If the pooled cell here is null or negative, the NQ")
        print(f"  finding was a 1-of-6 fluke and stays frozen. If clearly positive, it earns a real look.")
    else:
        print("  no equity-index 22:00 trades collected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
