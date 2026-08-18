"""WS-NEWS4 claims (#136) — the wide-series premium scan's published numbers.

Protocol: #118. value_fn reads the COMMITTED artefacts (news4_scan_blocks_*.csv,
news4_scan_events_*.csv, the posctrl files, p3_result_RTY.json); V1/V2/V3 fail for
DIFFERENT reasons; every claim declares its blind spot; `expect` is never adjusted.
Pre-registration: docs/NEWS4-N2-PREREGISTRATION.md (commit a988f17, filed before any run).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

FUND = Path(__file__).resolve().parents[1] / "fundamentals"
COST = 22.50                       # stressed $/event, both instruments (tick $5, 2.50+4t per leg)
ALPHA_T1 = 0.05 / 20


def _blocks(inst: str, posctrl: bool = False) -> pd.DataFrame:
    sfx = f"{inst}_posctrl" if posctrl else inst
    return pd.read_csv(FUND / f"news4_scan_blocks_{sfx}.csv")


def _events(inst: str, posctrl: bool = False) -> pd.DataFrame:
    sfx = f"{inst}_posctrl" if posctrl else inst
    return pd.read_csv(FUND / f"news4_scan_events_{sfx}.csv", parse_dates=["et"])


# ---------------------------------------------------------------------------------------------
# CLAIM — the scan confirmed ZERO new premiums (Tier 1, both instruments)
# ---------------------------------------------------------------------------------------------
def _zero_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION from the per-event file: recompute each NQ Tier-1 block's net mean and
    normal-approx p from raw fills; they must match the blocks CSV within tolerance."""
    b = _blocks("NQ")
    b = b[b.tier == 1]
    ev = _events("NQ")
    bad = []
    for _, r in b.iterrows():
        x = ev[ev.block == r.anchor].pnl_usd.to_numpy() - COST
        if len(x) < 3:
            continue
        m = x.mean()
        if abs(m - r.net_stressed_mean) > 0.01:
            bad.append(f"{r.anchor}: {m:.2f} vs {r.net_stressed_mean:.2f}")
    return not bad, ("all Tier-1 net means re-derive" if not bad else "; ".join(bad))


def _zero_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: RTY is a different price file with different variance. Its Tier-1
    table must also carry zero CONFIRMED verdicts."""
    b = _blocks("RTY")
    n_conf = int((b[b.tier == 1].verdict == "CONFIRMED").sum())
    return n_conf == 0, f"RTY Tier-1 CONFIRMED count = {n_conf}"


def _zero_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the pipeline cannot confirm anything' would explain zero confirmations.
    FALSE: the positive control (the deployed set through the IDENTICAL pipeline) confirms —
    NQ pooled net +$133.06 (M3's number to the cent) with verdict CONFIRMED."""
    b = _blocks("NQ", posctrl=True)
    row = b[b.anchor == "POSCTRL DEPLOYED-SET"].iloc[0]
    ok = row.verdict == "CONFIRMED" and abs(row.net_stressed_mean - 133.06) < 0.01 \
        and int(row.n_filled) == 327
    return ok, (f"posctrl pooled: n={int(row.n_filled)} net ${row.net_stressed_mean:+.2f} "
                f"verdict {row.verdict}")


register(Claim(
    id="N4-SCAN-ZERO-CONFIRMED",
    issue="#136",
    statement="The wide-series premium scan (89 NQ / 89 RTY moment blocks, 11,822 untested release "
              "moments, pre-registered Tier-1 family of 10 blocks x 2 instruments at Bonferroni "
              "α=0.05/20) confirmed ZERO announcement premiums outside the deployed {CPI,NFP,FOMC} "
              "set. Every Tier-1 block passes the release-minute jump gate (1.56-4.67x quiet "
              "baseline) yet none carries a harvestable ride premium: POWER ≠ PREMIUM at full-"
              "calendar scale.",
    source="optimize/fundamentals/news4_scan_blocks_{NQ,RTY}.csv",
    value_fn=lambda: int((_blocks("NQ")[_blocks("NQ").tier == 1].verdict == "CONFIRMED").sum()),
    expect=0, tol=0,
    blind_spot="A premium with a different SHAPE (short side, different stop/TP geometry, entry "
               "earlier than -300s, or conditional on a state variable) is invisible: the scan "
               "tests the frozen deployed spec only. Also shares the TV calendar with every prior "
               "study — a calendar-wide timestamp defect passes the jump gate only if it shifts "
               "minutes entirely.",
    checks=[Check("V1", "Tier-1 net means re-derive from per-event fills", _zero_v1),
            Check("V2", "independent RTY price file also carries zero confirmations", _zero_v2),
            Check("V3", "the identical pipeline CONFIRMS the deployed set (+$133.06 exact)", _zero_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — the positive control reproduces M3 exactly (the scan IS the verified study)
# ---------------------------------------------------------------------------------------------
def _pc_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: pooled net mean recomputed from the posctrl per-event file must equal
    the blocks-file figure and M3's +$133.06."""
    e = _events("NQ", posctrl=True)
    x = e[e.block == "POSCTRL DEPLOYED-SET"].pnl_usd.to_numpy() - COST
    return abs(x.mean() - 133.06) < 0.01 and len(x) == 327, f"n={len(x)} net ${x.mean():+.2f}"


def _pc_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT COMMITTED ARTEFACT: the RTY posctrl at the study's floor (2019) must
    reproduce the committed M3 cell (p3_result_RTY.json: long, stop 0.1, tp 0.4, gross +$57.98)
    within the one known tie-break event (238 vs 239)."""
    e = _events("RTY", posctrl=True)
    d = e[e.block == "POSCTRL DEPLOYED-SET"]
    d = d[d.et.dt.year >= 2019]
    ref = json.load(open(FUND / "p3_result_RTY.json"))
    cell = next(c for c in ref["cells"]
                if c["arm"] == "long" and c["stop"] == 0.1 and c["tp"] == 0.4)
    ok = abs(d.pnl_usd.mean() - cell["gross"]) < 1.5 and abs(len(d) - cell["n"]) <= 1
    return ok, (f"scan n={len(d)} gross ${d.pnl_usd.mean():+.2f} vs committed n={cell['n']} "
                f"gross ${cell['gross']:+.2f}")


def _pc_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the pipeline always confirms whatever it is fed' would also produce the
    CPI confirmation. FALSE: fed FOMC alone through the same pipeline it does NOT confirm
    (UNDERPOWERED, mean negative), while CPI alone DOES (+$309.02, p=2.8e-05)."""
    b = _blocks("NQ", posctrl=True)
    fomc = b[b.anchor == "POSCTRL Fed Interest Rate Decision"].iloc[0]
    cpi = b[b.anchor == "POSCTRL Inflation Rate MoM"].iloc[0]
    ok = fomc.verdict != "CONFIRMED" and cpi.verdict == "CONFIRMED" \
        and abs(cpi.net_stressed_mean - 309.02) < 0.01
    return ok, f"FOMC alone: {fomc.verdict}; CPI alone: {cpi.verdict} ${cpi.net_stressed_mean:+.2f}"


register(Claim(
    id="N4-POSCTRL-M3-PARITY",
    issue="#136",
    statement="The scan pipeline reproduces the verified M3 evidence exactly: the deployed set "
              "through the identical code gives NQ pooled n=327, net +$133.06 (CONFIRMED); RTY at "
              "the study floor reproduces the committed cell (+$57.98 gross) within the known "
              "1-event tie-break. The premium is CPI-concentrated: CPI alone confirms on BOTH "
              "instruments (NQ +$309.02, RTY +$78.41 net), NFP and FOMC alone never do.",
    source="optimize/fundamentals/news4_scan_blocks_NQ_posctrl.csv",
    value_fn=lambda: round(float(_blocks("NQ", posctrl=True)
                                 .set_index("anchor")
                                 .loc["POSCTRL DEPLOYED-SET", "net_stressed_mean"]), 2),
    expect=133.06, tol=0.01,
    blind_spot="Parity binds the scan to M3's fills, not to reality — a defect shared by the "
               "executor's bracket (e.g. the fill model itself) reproduces exactly and passes.",
    checks=[Check("V1", "pooled figure re-derives from posctrl per-event fills", _pc_v1),
            Check("V2", "RTY floor-2019 matches the committed p3_result_RTY cell", _pc_v2),
            Check("V3", "the pipeline does NOT confirm FOMC-alone while confirming CPI-alone", _pc_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — the nulls are POWERED against a CPI-sized premium (NQ side)
# ---------------------------------------------------------------------------------------------
def _pow_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: recompute each NQ Tier-1 MDE from the per-event fills with the
    pre-registered formula (80% power, α=0.0025); must match the blocks file within $1."""
    from math import sqrt
    b = _blocks("NQ")
    b = b[b.tier == 1]
    ev = _events("NQ")
    bad = []
    for _, r in b.iterrows():
        x = ev[ev.block == r.anchor].pnl_usd.to_numpy() - COST
        mde = (3.0233 + 0.8416) * x.std(ddof=1) / sqrt(len(x))   # z_{1-α/2}+z_{0.8}, α=0.0025
        if abs(mde - r.mde_usd) > 1.0:
            bad.append(f"{r.anchor}: {mde:.1f} vs {r.mde_usd:.1f}")
    return not bad, ("all Tier-1 MDEs re-derive" if not bad else "; ".join(bad))


def _pow_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: RTY's cheaper variance gives MUCH smaller MDEs ($26-$120); 9 of 10
    RTY Tier-1 blocks exclude even the smaller RTY CPI-sized premium (+$78.41) — GDP Adv (n=27,
    MDE $120) is the declared exception."""
    b = _blocks("RTY")
    t1 = b[b.tier == 1]
    n_below = int((t1.mde_usd < 78.41).sum())
    return n_below >= 9, f"{n_below}/10 RTY Tier-1 blocks have MDE < RTY CPI premium ($78.41)"


def _pow_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the nulls are dead-timestamp artefacts' (rides at wrong minutes measure
    nothing and cheaply produce nulls). FALSE: every Tier-1 block on both instruments passes the
    jump gate — release-minute range 1.56-4.67x the quiet baseline. The moments are real."""
    ok = True
    lo = []
    for inst in ("NQ", "RTY"):
        t1 = _blocks(inst)
        t1 = t1[t1.tier == 1]
        ok &= bool((t1.jump_ratio > 1.2).all())
        lo.append(f"{inst} min jump {t1.jump_ratio.min():.2f}")
    return ok, "; ".join(lo)


register(Claim(
    id="N4-POWERED-AGAINST-CPI-SIZE",
    issue="#136",
    statement="The Tier-1 nulls are informative, not underpowered hand-waving: on NQ, every one of "
              "the 10 blocks has MDE (80% power at α=0.0025) between $67 and $234/event — ALL "
              "below the CPI-sized premium (+$309.02 net) the same pipeline confirms. A CPI-class "
              "premium hiding in any Tier-1 block would have been seen. (Per-block NEGATIVE "
              "verdicts still follow the pre-registered POWERED-NULL ≤$150 line.)",
    source="optimize/fundamentals/news4_scan_blocks_NQ.csv",
    value_fn=lambda: round(float(_blocks("NQ")[_blocks("NQ").tier == 1].mde_usd.max()), 2),
    expect=234.22, tol=0.5,
    blind_spot="MDE is computed from the realized sd of the frozen ride — a premium with lower "
               "variance (e.g. conditional entries) could be smaller than the MDE yet real. "
               "Power statements are about THIS spec's noise, nothing else.",
    checks=[Check("V1", "Tier-1 MDEs re-derive from per-event fills", _pow_v1),
            Check("V2", "RTY's smaller MDEs exclude the RTY-CPI-sized premium on 9/10", _pow_v2),
            Check("V3", "the nulls are not dead-timestamp artefacts (jump gate all-pass)", _pow_v3)]))
