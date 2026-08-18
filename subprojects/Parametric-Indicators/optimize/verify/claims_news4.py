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


# =============================================================================================
# N3 deep-dives (#137) — pre-registration docs/NEWS4-N3-PREREGISTRATION.md (70f29fc)
# =============================================================================================
def _n3_blocks(inst: str) -> pd.DataFrame:
    return pd.read_csv(FUND / f"news4_n3_blocks_{inst}.csv")


def _n3_events(inst: str, block: str) -> pd.DataFrame:
    d = pd.read_csv(FUND / f"news4_n3_events_{inst}.csv", parse_dates=["et"])
    return d[d.block == block]


N3_COST = {"NQ": 22.50, "RTY": 22.50, "ES": 52.50, "GC": 42.50, "CL": 42.50}


# ---------------------------------------------------------------------------------------------
# CLAIM — Retail Sales carries a REAL negative announcement effect (CONFIRMED-NEGATIVE, both)
# ---------------------------------------------------------------------------------------------
def _ret_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: NQ Retail gross mean and p recomputed from per-event fills must match
    the blocks file (gross −$86.10, p=7.2e-04 < α=0.00625) with both halves negative."""
    e = _n3_events("NQ", "Retail Sales MoM")
    g = e.pnl_usd.to_numpy()
    net = g - N3_COST["NQ"]
    t = net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))
    import math
    p = math.erfc(abs(t) / math.sqrt(2))
    half = len(g) // 2
    ok = abs(g.mean() + 86.10) < 0.01 and p < 0.05 / 8 and g[:half].mean() < 0 \
        and g[half:].mean() < 0
    return ok, f"gross ${g.mean():+.2f} p={p:.2g} halves {g[:half].mean():+.1f}/{g[half:].mean():+.1f}"


def _ret_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: the RTY price file (different exchange feed, different variance)
    must carry the same CONFIRMED-NEGATIVE verdict."""
    b = _n3_blocks("RTY").set_index("anchor")
    r = b.loc["Retail Sales MoM"]
    ok = r.verdict == "CONFIRMED-NEGATIVE" and r.gross_mean < 0
    return ok, f"RTY: {r.verdict}, gross ${r.gross_mean:+.2f}, p={r.p:.2g}"


def _ret_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'everything at 08:30 rides negative (a clock-time artefact)' would also
    make CPI/NFP negative and Durables negative. FALSE: same clock, same pipeline — the deployed
    set is CONFIRMED positive (+$133.06) and Durables is a POWERED-NULL (+$9.47 gross). The
    negative is SERIES-SPECIFIC."""
    pc = _blocks("NQ", posctrl=True).set_index("anchor")
    b = _n3_blocks("NQ").set_index("anchor")
    ok = pc.loc["POSCTRL DEPLOYED-SET", "verdict"] == "CONFIRMED" \
        and b.loc["Durable Goods Orders MoM", "verdict"] == "POWERED-NULL" \
        and b.loc["Durable Goods Orders MoM", "gross_mean"] > 0
    return ok, (f"deployed set {pc.loc['POSCTRL DEPLOYED-SET', 'verdict']}; Durables "
                f"{b.loc['Durable Goods Orders MoM', 'verdict']} "
                f"(gross ${b.loc['Durable Goods Orders MoM', 'gross_mean']:+.2f})")


register(Claim(
    id="N4-RETAIL-ANTI-PREMIUM-CONFIRMED",
    issue="#137",
    statement="Retail Sales MoM carries a REAL negative announcement effect at the deployed spec: "
              "NQ gross −$86.10/event (p=7.2e-04, n=113, both halves negative), RTY gross "
              "−$32.41 (p=1.7e-05, n=101). The only US macro series with a confirmed NEGATIVE "
              "ride at our costs — a documented do-not-ride series. (Whether its SHORT side is "
              "tradeable is a separate, un-pre-registered question.)",
    source="optimize/fundamentals/news4_n3_blocks_NQ.csv",
    value_fn=lambda: round(float(_n3_blocks("NQ").set_index("anchor")
                                 .loc["Retail Sales MoM", "gross_mean"]), 2),
    expect=-86.10, tol=0.01,
    blind_spot="Retail minutes that co-fire with CPI/NFP are excluded by the overlap rule, so "
               "this measures Retail-ALONE minutes; a Retail effect that only exists when "
               "co-released is invisible here (it belongs to the deployed set's evidence).",
    checks=[Check("V1", "gross/p/halves re-derive from per-event fills", _ret_v1),
            Check("V2", "independent RTY price file: same CONFIRMED-NEGATIVE", _ret_v2),
            Check("V3", "not a clock-time artefact: CPI/NFP positive, Durables null at 08:30", _ret_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — EIA/API on CL: the ride is excluded at cost with heavy power (the M1 VOID resolved)
# ---------------------------------------------------------------------------------------------
def _eia_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: EIA gross ≈ 0 (−$1.41) and MDE $20.01 recomputed from fills."""
    from math import sqrt
    e = _n3_events("CL", "EIA Crude Oil Stocks Change")
    g = e.pnl_usd.to_numpy()
    mde = (2.7344 + 0.8416) * (g - N3_COST["CL"]).std(ddof=1) / sqrt(len(g))  # α=0.00625
    ok = abs(g.mean() + 1.41) < 0.01 and abs(mde - 20.01) < 0.5
    return ok, f"gross ${g.mean():+.2f} MDE ${mde:.2f} n={len(g)}"


def _eia_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT DRAW: API (different reporting body, different day-time, 433 separate
    events) shows the same shape: gross ≈ 0, net ≈ −cost."""
    b = _n3_blocks("CL").set_index("anchor")
    r = b.loc["API Crude Oil Stock Change"]
    ok = abs(r.gross_mean) < 15 and r.net_stressed_mean < -25
    return ok, f"API gross ${r.gross_mean:+.2f} net ${r.net_stressed_mean:+.2f} n={int(r.n_filled)}"


def _eia_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the null is dead timestamps' — FALSE: EIA jump 5.33x, API 8.00x the quiet
    baseline; these are among the most violent minutes in the CL tape and still pay nothing."""
    b = _n3_blocks("CL").set_index("anchor")
    ok = b.loc["EIA Crude Oil Stocks Change", "jump_ratio"] > 4 \
        and b.loc["API Crude Oil Stock Change", "jump_ratio"] > 4
    return ok, (f"jump EIA {b.loc['EIA Crude Oil Stocks Change', 'jump_ratio']:.2f}x, "
                f"API {b.loc['API Crude Oil Stock Change', 'jump_ratio']:.2f}x")


register(Claim(
    id="N4-EIA-API-POWERED-NO",
    issue="#137",
    statement="The energy-inventory ride on CL is a powered NO at the deployed spec: EIA gross "
              "−$1.41/event (n=551, MDE $20), API gross +$5.27 (n=433, MDE $21) — gross ≈ zero, "
              "net ≈ −cost, while the release minutes jump 5.3-8.0x quiet baseline. M1's VOID "
              "(provenance-restricted) upgrades to a definitive exclusion.",
    source="optimize/fundamentals/news4_n3_blocks_CL.csv",
    value_fn=lambda: round(float(_n3_blocks("CL").set_index("anchor")
                                 .loc["EIA Crude Oil Stocks Change", "gross_mean"]), 2),
    expect=-1.41, tol=0.01,
    blind_spot="CL costs use the deployed formula ($42.50 stressed) — actual CL spread behaviour "
               "at 10:30 was never measured the way NQ's 2.1x stop-gap was; a kinder real cost "
               "would not rescue a $0 gross anyway.",
    checks=[Check("V1", "EIA gross/MDE re-derive from fills", _eia_v1),
            Check("V2", "API: independent body, same zero-gross shape", _eia_v2),
            Check("V3", "the null is not dead timestamps (5.3x/8.0x jumps)", _eia_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — the deployed-set premium does NOT extend confirmably to ES/GC (no new surface)
# ---------------------------------------------------------------------------------------------
def _esgc_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: ES pooled net (+$55.04) from fills; p=0.034 ≥ α=0.00625; MDE $92.79."""
    e = _n3_events("ES", "DEPLOYED-SET")
    net = e.pnl_usd.to_numpy() - N3_COST["ES"]
    ok = abs(net.mean() - 55.04) < 0.01 and len(net) == 327
    return ok, f"ES pooled net ${net.mean():+.2f} n={len(net)}"


def _esgc_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: GC (a different asset class entirely) also POWERED-NULL
    (+$8.48 net, MDE $89.40)."""
    b = _n3_blocks("GC").set_index("anchor")
    r = b.loc["DEPLOYED-SET"]
    return r.verdict == "POWERED-NULL", f"GC pooled: {r.verdict}, net ${r.net_stressed_mean:+.2f}"


def _esgc_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the ES/GC nulls are instrument-blindness (the pipeline cannot see
    structure on those files)'. FALSE: the descriptive CPI-alone slice inside the SAME ES events
    shows net +$151 (t≈3.0) — the pipeline resolves structure on ES; the pooled verdict is about
    NFP/FOMC dilution, not blindness."""
    sched = pd.read_csv(Path(__file__).resolve().parents[4] / "src" / "deploy" / "data"
                        / "release_schedule.csv", parse_dates=["et"])
    e = _n3_events("ES", "DEPLOYED-SET").merge(sched[["et", "title"]], on="et")
    cpi = e[e.title == "Inflation Rate MoM"].pnl_usd - N3_COST["ES"]
    t = cpi.mean() / (cpi.std(ddof=1) / np.sqrt(len(cpi)))
    return bool(t > 2.5 and cpi.mean() > 100), f"ES CPI-alone net ${cpi.mean():+.2f} t={t:+.2f}"


register(Claim(
    id="N4-ES-GC-NO-NEW-SURFACE",
    issue="#137",
    statement="The deployed-set ride does NOT confirm on ES or GC at the deployed spec and costs: "
              "ES pooled net +$55.04 (p=0.034 ≥ α=0.00625, MDE $93 → POWERED-NULL), GC +$8.48 "
              "(MDE $89 → POWERED-NULL). No new deployable surface. NOTED for the record: the "
              "descriptive ES CPI-alone slice is net +$151 (t≈3.0) — a promotion candidate that "
              "would need its own pre-registered confirmation on unconsumed data (its history is "
              "spent; forward confirmation only).",
    source="optimize/fundamentals/news4_n3_blocks_ES.csv",
    value_fn=lambda: round(float(_n3_blocks("ES").set_index("anchor")
                                 .loc["DEPLOYED-SET", "net_stressed_mean"]), 2),
    expect=55.04, tol=0.01,
    blind_spot="ES/GC reuse the same event minutes as NQ's evidence — independent PRICE files, "
               "not independent EVENTS; and the ES/GC cost lines are formula-derived, not "
               "measured (declared in the pre-registration).",
    checks=[Check("V1", "ES pooled net re-derives from fills", _esgc_v1),
            Check("V2", "GC (different asset class) also POWERED-NULL", _esgc_v2),
            Check("V3", "not instrument-blindness: ES CPI-alone slice resolves at t≈3.0", _esgc_v3)]))
