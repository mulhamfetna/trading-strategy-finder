"""WS-ESCPI claims (#139) — the ES CPI-alone study's published numbers.

Protocol: #118. value_fn reads the COMMITTED artefacts; V1/V2/V3 fail for different reasons;
blind spots declared; `expect` never adjusted. Pre-registration:
docs/WS-ESCPI-PREREGISTRATION.md (051ff07, filed BEFORE the YM file was opened).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

FUND = Path(__file__).resolve().parents[1] / "fundamentals"
COST_ES, COST_YM = 52.50, 22.50


def _ev(name: str) -> pd.DataFrame:
    return pd.read_csv(FUND / name, parse_dates=["et"])


# ---------------------------------------------------------------------------------------------
# CLAIM — the ES CPI-alone battery PASSES (robustness-grade: its history discovered the effect)
# ---------------------------------------------------------------------------------------------
def _es_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: net mean/p from the per-event file must match the blocks row
    (net +$151.37, p=0.0027 < α=0.01) with both halves gross-positive."""
    import math
    e = _ev("wsescpi_events_ES.csv")
    e = e[e.block == "CPI-alone"]
    g = e.pnl_usd.to_numpy()
    net = g - COST_ES
    t = net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))
    p = math.erfc(abs(t) / math.sqrt(2))
    half = len(g) // 2
    ok = abs(net.mean() - 151.37) < 0.01 and p < 0.01 and g[:half].mean() > 0 \
        and g[half:].mean() > 0
    return ok, f"n={len(e)} net ${net.mean():+.2f} p={p:.2g}"


def _es_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT IMPLEMENTATION: the executor replay (--series 'Inflation Rate MoM',
    floor 2024) is a different code path from the study runner; its 29-event window must
    reproduce the runner's 2024→2026 slice to the cent (net +$529.44/event)."""
    r = _ev("wsescpi_replay_ES.csv")
    e = _ev("wsescpi_events_ES.csv")
    e = e[(e.block == "CPI-alone") & (pd.to_datetime(e.et).dt.year >= 2024)]
    ok = len(r) == 29 and abs(r.net_stressed_usd.mean() - 529.44) < 0.01 \
        and abs((e.pnl_usd - COST_ES).mean() - r.net_stressed_usd.mean()) < 0.01
    return ok, (f"executor n={len(r)} net ${r.net_stressed_usd.mean():+.2f} vs runner "
                f"${(e.pnl_usd - COST_ES).mean():+.2f}")


def _es_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the ES pipeline scores anything positive'. FALSE: the same pipeline on
    Retail-alone minutes is significantly NEGATIVE (the confirmed anti-premium), gross −$66.38."""
    b = pd.read_csv(FUND / "wsescpi_blocks_ES.csv").set_index("block")
    r = b.loc["Retail-falsifier"]
    ok = r.gross_mean < -30 and r.p < 0.01 and "NEGATIVE" in str(r.verdict)
    return ok, f"Retail on ES: gross ${r.gross_mean:+.2f} p={r.p:.2g} {r.verdict}"


register(Claim(
    id="ESCPI-ES-BATTERY-PASS",
    issue="#139",
    statement="The ES CPI-alone ride passes the full pre-registered battery (robustness-grade — "
              "ES's own history generated the hypothesis): n=116, net +$151.37/event at $52.50 "
              "stressed costs, p=0.0027 (α=0.01), both halves gross-positive, jump 20.5× quiet "
              "baseline, control floor and 1,000-placebo noise check green. 2024→2026: n=29, net "
              "+$529.44/event, +$15,353.82/contract total.",
    source="optimize/fundamentals/wsescpi_blocks_ES.csv",
    value_fn=lambda: round(float(pd.read_csv(FUND / "wsescpi_blocks_ES.csv")
                                 .set_index("block").loc["CPI-alone", "net_stressed_mean"]), 2),
    expect=151.37, tol=0.01,
    blind_spot="Robustness is not independence: every gate here runs on the data that DISCOVERED "
               "the effect. Independence was assigned to the YM holdout, which came out "
               "VOID-DATA — so this claim alone can never justify shipping.",
    checks=[Check("V1", "net/p/halves re-derive from per-event fills", _es_v1),
            Check("V2", "the executor (independent implementation) reproduces to the cent", _es_v2),
            Check("V3", "the pipeline scores Retail NEGATIVE (it does not bless everything)", _es_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — the YM holdout is VOID-DATA; the descriptive agreement is recorded, not claimed
# ---------------------------------------------------------------------------------------------
def _ym_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: the result manifest must be internally consistent — verdict VOID-DATA
    if and only if coverage < 0.70 (the pre-registered line)."""
    r = json.load(open(FUND / "wsescpi_result_YM.json"))
    ok = r["verdict"] == "VOID-DATA" and r["coverage"] < 0.70
    return ok, f"verdict {r['verdict']}, coverage {r['coverage']:.3f}"


def _ym_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT ARTEFACT: the descriptive per-event file (saved under the VOID label)
    re-derives net +$107.64, t≈3.15 — the number quoted to the owner as descriptive-only."""
    e = _ev("wsescpi_events_YM_descriptive.csv")
    net = e.pnl_usd.to_numpy() - COST_YM
    t = net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))
    ok = abs(net.mean() - 107.64) < 0.01 and 2.5 < t < 4.0 and len(e) == 116
    return ok, f"n={len(e)} net ${net.mean():+.2f} t={t:.2f} (DESCRIPTIVE, gate active)"


def _ym_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the VOID came from a still-broken file'. FALSE for the re-assembled file:
    116/118 events FILL (a dead file fills nothing) and the descriptive era pattern matches ES
    (2024→2026 slice positive) — the VOID is about tape THINNESS vs the pre-registered line,
    not absence of data."""
    e = _ev("wsescpi_events_YM_descriptive.csv")
    w = e[pd.to_datetime(e.et).dt.year >= 2024]
    ok = len(e) >= 110 and (w.pnl_usd - COST_YM).mean() > 100
    return ok, f"fills {len(e)}/118; 2024→2026 slice net ${(w.pnl_usd - COST_YM).mean():+.2f}/event"


register(Claim(
    id="ESCPI-YM-HOLDOUT-VOID",
    issue="#139",
    statement="The pre-registered YM holdout is VOID-DATA: after re-assembling the corrupt "
              "YM_1s.csv from raw (valid data had ended 2016-01-15 mid-row), YM's premarket tape "
              "is genuinely thin — median 101 traded pre-release seconds; 12.7% of CPI windows "
              "reach the registered 150-second line. No verdict claimable. Recorded descriptively "
              "under the VOID label: n=116, net +$107.64, t=3.15 — sign, size-order and era all "
              "agree with ES; formally it confirms nothing. Ship rule therefore falls to the "
              "owner's explicit acceptance of descriptive-grade evidence.",
    source="optimize/fundamentals/wsescpi_result_YM.json",
    value_fn=lambda: round(float(json.load(open(FUND / "wsescpi_result_YM.json"))["coverage"]), 3),
    expect=0.127, tol=0.001,
    blind_spot="The 150s/70% gate was an a-priori guess that proved stricter than YM's real thin "
               "tape; per discipline it was NOT loosened after seeing the data, which is exactly "
               "why the strong descriptive agreement cannot be upgraded to a PASS.",
    checks=[Check("V1", "manifest internally consistent (VOID ⇔ coverage < 0.70)", _ym_v1),
            Check("V2", "descriptive numbers re-derive from the committed VOID-label file", _ym_v2),
            Check("V3", "the VOID is thinness, not a dead file (116/118 fill; era pattern matches)", _ym_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — integration: +36.5% layer profit 2024→2026 at qty=1, and it is NOT diversification
# ---------------------------------------------------------------------------------------------
def _int_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: totals from the three committed replay files."""
    old = sum(_ev(f"wsescpi_replay_{i}.csv").net_stressed_usd.sum() for i in ("NQ", "RTY"))
    es = _ev("wsescpi_replay_ES.csv").net_stressed_usd.sum()
    pct = 100 * es / old
    ok = abs(old - 42097.32) < 1.0 and abs(es - 15353.82) < 0.01 and abs(pct - 36.5) < 0.2
    return ok, f"layer ${old:,.2f} + ES ${es:,.2f} = +{pct:.1f}%"


def _int_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT COMMITTED ARTEFACT: NQ/RTY replay means must match the WS-DEPLOY playbook
    champion.json performance_2024_2026 block (written by a different workstream)."""
    ch = json.load(open(Path(__file__).resolve().parents[4] / "playbooks" / "news-release-long"
                        / "champion.json"))
    perf = ch["performance_2024_2026"]
    nq, rty = _ev("wsescpi_replay_NQ.csv"), _ev("wsescpi_replay_RTY.csv")
    ok = abs(nq.pnl_usd.mean() - perf["NQ"]["gross_mean_per_event"]) < 0.01 \
        and abs(rty.pnl_usd.mean() - perf["RTY"]["gross_mean_per_event"]) < 0.01
    return ok, (f"NQ ${nq.pnl_usd.mean():+.2f} vs playbook {perf['NQ']['gross_mean_per_event']:+.2f}; "
                f"RTY ${rty.pnl_usd.mean():+.2f} vs {perf['RTY']['gross_mean_per_event']:+.2f}")


def _int_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'adding ES diversifies the layer'. FALSE: same-event correlation ES↔NQ
    > 0.5 and a meaningful share of CPI events lose on all three legs — ES SCALES the CPI bet."""
    nq, rty, es = (_ev(f"wsescpi_replay_{i}.csv") for i in ("NQ", "RTY", "ES"))
    j = nq.merge(es, on="et", suffixes=("_nq", "_es")).merge(
        rty.rename(columns={"net_stressed_usd": "net_rty"})[["et", "net_rty"]], on="et")
    corr = np.corrcoef(j.net_stressed_usd_nq, j.net_stressed_usd_es)[0, 1]
    all_lose = ((j[["net_stressed_usd_nq", "net_stressed_usd_es", "net_rty"]] < 0)
                .all(axis=1)).mean()
    ok = corr > 0.5 and all_lose > 0.10
    return ok, f"ES↔NQ corr {corr:.2f}; all-three-lose share {all_lose:.0%}"


register(Claim(
    id="ESCPI-INTEGRATION-36PCT",
    issue="#139",
    statement="Integrating ES CPI-only rides into the deployed layer adds +$15,353.82 net "
              "stressed over 2024→2026 at qty=1 — +36.5% on the layer's $42,097.32 — measured by "
              "the executor itself (NQ 81 × +$424.53, RTY 81 × +$95.19, ES 29 × +$529.44). "
              "Honestly labeled: this is SCALING the CPI bet, not diversification (ES↔NQ "
              "same-event correlation 0.78; 24% of CPI events lose on all three legs; worst "
              "joint CPI event −$1,023 on 2025-09-11).",
    source="optimize/fundamentals/wsescpi_replay_{NQ,RTY,ES}.csv",
    value_fn=lambda: round(float(_ev("wsescpi_replay_ES.csv").net_stressed_usd.sum()), 2),
    expect=15353.82, tol=0.01,
    blind_spot="qty=1 arithmetic only; margin at three simultaneous legs and scaled (worked-entry) "
               "execution on ES were not measured here — ES's deeper book should make the entry "
               "wall EASIER than NQ's, but that is expectation, not measurement.",
    checks=[Check("V1", "totals re-derive from the three replay files", _int_v1),
            Check("V2", "NQ/RTY means match the WS-DEPLOY playbook (independent artefact)", _int_v2),
            Check("V3", "'it diversifies' is FALSE — correlation and joint-loss measured", _int_v3)]))


# =============================================================================================
# WS-GRID (#140) — the literal full-grid closure (pre-reg b629543)
# =============================================================================================
def _grid_all() -> pd.DataFrame:
    import glob
    frames = []
    for f in sorted(glob.glob(str(FUND / "news4_scan_blocks_*_grid.csv"))):
        d = pd.read_csv(f)
        d["inst"] = Path(f).name.split("_")[3]
        frames.append(d)
    return pd.concat(frames)


def _grid_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: cell count and verdict census from the committed per-instrument
    files: 661 cells, exactly one EXPLORATORY-POSITIVE, and it is YM CPI."""
    g = _grid_all()
    pos = g[g.verdict == "EXPLORATORY-POSITIVE"]
    ok = len(g) == 661 and len(pos) == 1 and pos.iloc[0]["inst"] == "YM" \
        and "Inflation Rate MoM" in pos.iloc[0]["anchor"] \
        and abs(pos.iloc[0].net_stressed_mean - 107.64) < 0.01
    return ok, f"{len(g)} cells, positives={len(pos)} ({pos.iloc[0]['anchor'] if len(pos) else '-'})"


def _grid_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT KNOWN-TRUE EFFECT: the sweep must reproduce the Retail anti-premium
    on every instrument whose tape reacts — gross-negative significant on ES/GC/HG/SI/YM
    (NQ/RTY were N3's; CL/NG legitimately VOID by the jump gate)."""
    g = _grid_all()
    r = g[g.anchor.str.contains("Retail Sales MoM")]
    sig = r[r.verdict.str.startswith("SIGNIFICANT-NEGATIVE")]
    ok = set(sig.inst) == {"ES", "GC", "HG", "SI", "YM"} and (sig.gross_mean < 0).all() \
        and set(r[r.verdict == "VOID-TIMESTAMP"].inst) == {"CL", "NG"}
    return ok, f"Retail gross-negative on {sorted(sig.inst)}; void on {sorted(r[r.verdict=='VOID-TIMESTAMP'].inst)}"


def _grid_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: 'the sweep voids/nulls everything because thin instruments cannot show
    a positive'. FALSE twice: the THINNEST tape (YM) is exactly where the positive appears,
    and the macro blocks' jump gates pass on every instrument that has one (SI CPI 6x,
    HG CPI 4x, YM CPI 9.8x) — the nulls sit on real, violent minutes."""
    g = _grid_all()
    cpi = g[g.anchor.str.contains("Inflation Rate MoM")].set_index("inst")
    ok = cpi.loc["YM", "verdict"] == "EXPLORATORY-POSITIVE" \
        and cpi.loc["SI", "jump_ratio"] > 4 and cpi.loc["HG", "jump_ratio"] > 3
    return ok, (f"YM CPI positive on the thinnest tape; CPI jumps SI {cpi.loc['SI','jump_ratio']:.1f}x "
                f"HG {cpi.loc['HG','jump_ratio']:.1f}x")


register(Claim(
    id="GRID-CLOSURE-ONE-POSITIVE",
    issue="#140",
    statement="The literal full-grid closure (661 remaining cells across all 9 registry "
              "instruments, pre-registered exploratory sweep) found exactly ONE positive: "
              "YM CPI (+$107.64 net, p=0.0016, jump 9.8x). Census: 370 VOID-TIMESTAMP, 179 "
              "significant negatives (41% pure cost drag with gross > −$5; 29% gross-positive), "
              "106 POWERED-NULL, 5 UNDERPOWERED. The Retail anti-premium replicates gross-"
              "negative on 7 instruments; the CPI premium is an equity-index phenomenon ordered "
              "NQ > ES > YM > RTY; NG's own inventory release jumps 8.5x and grosses −$4.89. "
              "Every series×instrument cell of the premium grid now has a recorded verdict.",
    source="optimize/fundamentals/news4_scan_blocks_{INST}_grid.csv",
    value_fn=lambda: int((_grid_all().verdict == "EXPLORATORY-POSITIVE").sum()),
    expect=1, tol=0,
    blind_spot="One trade shape; the $150 powered-null line is nominal-dollar (generous in SI "
               "dollars, tight in NG); exploratory labels only — the YM CPI positive is the "
               "SAME data as the ESCPI descriptive and confirms nothing beyond it.",
    checks=[Check("V1", "census re-derives: 661 cells, one positive, it is YM CPI", _grid_v1),
            Check("V2", "the known-true Retail anti-premium replicates wherever tape reacts", _grid_v2),
            Check("V3", "the nulls are not thin-tape blindness (YM positive; jump gates pass)", _grid_v3)]))
