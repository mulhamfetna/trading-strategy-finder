"""WS-ORB (#183) claims — opening-range breakout on 9 instruments, 16 years, pre-registered grid.
Pre-registration: docs/WS-ORB-PREREGISTRATION.md (filed before any run). Evidence: optimize/orb/data/grid1/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from harness import Check, Claim, register

PI = Path(__file__).resolve().parents[1]
D = PI / "orb" / "data" / "grid1"
ANCH = PI / "orb" / "data" / "anchor_check.json"


def _verdicts() -> pd.DataFrame:
    return pd.read_csv(D / "verdicts.csv", keep_default_na=False)   # "NULL" is a verdict, not NaN


def _v1() -> tuple[bool, str]:
    """V1 — DEFINITIONS HELD: the reference passes its hand-computed synthetic tests (gap fill at open, stop-first,
    void ranges, session mapping); the anchor check ran BEFORE P/L with 7/9 confirmed and SI/HG moved to the
    observed volume step as the pre-registration prescribes; the grid is exactly 9 x 2 x 4 x 3 + 9 = 225 cells."""
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", str(PI / "orb" / "test_orb_reference.py")],
                       capture_output=True, text=True, cwd=str(PI))
    tests_ok = t.returncode == 0 and "6 passed" in t.stdout
    a = json.load(open(ANCH))
    confirmed = sorted(k for k, v in a.items() if v["pass"])
    moved = sorted(k for k, v in a.items() if not v["pass"])
    v = _verdicts()
    ok = tests_ok and len(confirmed) == 7 and moved == ["HG", "SI"] and len(v) == 225
    return ok, f"tests {'6/6' if tests_ok else 'FAIL'}; anchors confirmed {confirmed}, moved {moved}; cells {len(v)}"


def _v2() -> tuple[bool, str]:
    """V2 — THE VERDICT TABLE REPRODUCES: from the committed summary, POSITIVE 0, NEGATIVE (powered, MDE <= $25)
    28, negative-but-underpowered 58, UNDERPOWERED 138, NULL 1; the strongest cell has t = 1.78 (NG globex 60 R3,
    148 trades) and the strongest NQ cell t = 1.56; every cell with t > 1 reverses sign or is below $30/trade in
    the exploration window except NQ globex 60 (R1 +$26, R2 +$6 per trade)."""
    v = _verdicts()
    vc = v["verdict"].value_counts().to_dict()
    best = v.sort_values("t25", ascending=False).iloc[0]
    ok = (vc.get("NEGATIVE", 0) == 28 and vc.get("NEGATIVE (t) but UNDERPOWERED vs $25", 0) == 58
          and vc.get("UNDERPOWERED", 0) == 138 and vc.get("NULL", 0) == 1
          and not any(str(x).startswith("POSITIVE") for x in v["verdict"])
          and best["cell"] == "NG_globex_60_R3" and abs(best["t25"] - 1.781) < 0.01)
    return ok, f"{vc}; best {best['cell']} t={best['t25']}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: if a real opening-range edge existed at the top of the grid, the REAL anchor would beat
    randomly placed ranges of the same length/rule AND clear the noise bar. The best NQ cell (globex 60 R1,
    $72.72/trade) does NOT beat the random-anchor p95 ($113) — a 60-minute range breakout from any hour of the
    NQ session earns as much, i.e. the anchor carries no information; the three cells that do beat p95 all sit
    below t = 2 (MDE $85-$132/trade vs observed $47-$66)."""
    c = json.load(open(D / "controls_top.json"))
    v = _verdicts().set_index("cell")
    nq = c["NQ_globex_60_R1"]
    others = [k for k in c if k != "NQ_globex_60_R1"]
    ok = (not nq["beats_p95"] and all(c[k]["beats_p95"] for k in others)
          and all(v.loc[k, "t25"] < 2.0 for k in c))
    return ok, (f"NQ_globex_60_R1 real {nq['real_conf_mean25']:.2f} vs p95 {nq['p95']:.2f} beats={nq['beats_p95']}; "
                f"others beat p95: {[c[k]['beats_p95'] for k in others]}; t25 of all four < 2: {[round(v.loc[k,'t25'],2) for k in c]}")


def _n_positive() -> float:
    return float(sum(1 for x in _verdicts()["verdict"] if str(x).startswith("POSITIVE")))


register(Claim(
    id="ORB-GRID-NO-POSITIVE-CELL",
    issue="#183",
    statement="WS-ORB (#183): on the 16-year 1-minute tape (2010-06 .. 2026-08-07), the pre-registered "
              "opening-range-breakout grid — 9 instruments x {cash-open, 18:00 Globex} x {5,15,30,60 min} x "
              "{1R/10R classic, 10%-ATR14 stop, 50%-range target} + the Holmberg vol-threshold comparator = 225 "
              "cells, 1 contract, engine gap/stop-first fills — produced ZERO cells meeting the POSITIVE bar "
              "(t >= 2.5 at $25/round-trip on 2018-2024, sign agreement 2010-2017, year stability). 28 cells are "
              "NEGATIVE with power (MDE <= $25/trade), 58 more are negative at t <= -2 but under-powered against "
              "the $25 bar, 138 are UNDERPOWERED, 1 NULL. The 5-minute window — the literature's favourite — is "
              "the worst (28% of its cells powered-negative); R3 (50%-range target) is the worst rule (33%). The "
              "best cell in the grid is NG globex 60-min R3 at t = 1.78 on 148 trades; the best NQ cells earn "
              "$47-$73/trade after costs at t 1.5 but reverse sign before 2018, and the top NQ cell does not beat "
              "randomly placed 60-minute ranges.",
    source="optimize/orb/data/grid1/{orb_summary.json,verdicts.csv,controls_top.json} + anchor_check.json",
    value_fn=_n_positive,
    expect=0.0,
    tol=0.0,
    blind_spot="Per-trade power is the binding constraint even over 16 years (median MDE $51/trade vs a $25 "
               "bar), so 138 cells get no verdict — 'not proven' is not 'proven absent'. Continuous-contract "
               "roll days are inside the books (flagged as a declared blind spot, not yet split out). The SI "
               "07:00 anchor may be a DST artefact. No pooling across instruments was pre-registered, so none "
               "is claimed.",
    checks=[Check("V1", "definitions-held", _v1),
            Check("V2", "verdict-table-reproduces", _v2),
            Check("V3", "anchor-carries-no-information", _v3)],
))
