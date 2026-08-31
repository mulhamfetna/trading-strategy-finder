"""#198 (RUNG-4 board #194, phase 2) — vol-gate recalibration cadence. Pre-registration:
docs/WS-GATECAL-PREREGISTRATION.md (filed before any run). Evidence: optimize/gatecal/data/
(arm summaries, the A0-parity proof, the verdict JSON; per-trade books on the server)."""
from __future__ import annotations

import json
from pathlib import Path

from harness import Check, Claim, register

D = Path(__file__).resolve().parents[1] / "gatecal" / "data"


def _v() -> dict:
    return json.load(open(D / "gatecal_verdict.json"))


def _v1() -> tuple[bool, str]:
    """V1 — THE HOOK'S OFF-STATE IS THE ENGINE: arm A0 (gate_recal_months absent) reproduced the round-2
    books IDENTICALLY on all 54 slots (entry times and P/L to half a cent) — the study's control is also
    the proof that merging the hook changed nothing."""
    p = json.load(open(D / "gatecal_a0_parity.json"))
    ok = p["n_identical"] == p["n_slots"] == 54
    return ok, f"A0 parity {p['n_identical']}/{p['n_slots']}"


def _v2() -> tuple[bool, str]:
    """V2 — THE VERDICT RE-DERIVES FROM THE FROZEN RULE: applying prereg §3 (an arm is POSITIVE iff its
    point difference beats the churn floor AND its bootstrap CI95 excludes zero) to the committed numbers
    yields NULL for quarterly and NULL for monthly — exactly what is published."""
    v = _v()
    churn = v["churn_floor_C_vs_A0"]
    lab = {}
    for arm in ("A1", "A2"):
        d = v[f"{arm}_vs_A0"]
        lab[arm] = ("POSITIVE" if d["point"] > churn and d["ci95"][0] > 0
                    else "NEGATIVE" if d["ci95"][1] < 0 else "NULL")
    ok = lab == v["verdict"] == {"A1": "NULL", "A2": "NULL"}
    return ok, f"re-derived {lab}; published {v['verdict']}; churn floor {churn:+,.0f}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the hook acts, and the rule can refuse): recalibration demonstrably CHANGES the
    fleet (A1/A2 fresh trade counts 5,074/5,023 vs A0's 3,733 — the dark slots reopen), and the rule is
    no rubber stamp: the random-percentile control's point difference (+$36,792) is the LARGEST of the
    three arms, yet its CI includes zero and it grants nothing — a judgement that only ever says yes
    would have said yes here."""
    v = _v()
    ok = (v["A1"]["fresh_n"] > 4500 and v["A2"]["fresh_n"] > 4500 and v["A0"]["fresh_n"] == 3733
          and v["C_vs_A0"]["point"] > max(v["A1_vs_A0"]["point"], v["A2_vs_A0"]["point"])
          and v["C_vs_A0"]["ci95"][0] < 0)
    return ok, (f"fresh n A0 {v['A0']['fresh_n']} vs A1 {v['A1']['fresh_n']} / A2 {v['A2']['fresh_n']}; "
                f"C point {v['C_vs_A0']['point']:+,.0f} CI {v['C_vs_A0']['ci95']}")


def _n_positive() -> float:
    return float(sum(1 for x in _v()["verdict"].values() if x == "POSITIVE"))


register(Claim(
    id="GATECAL-CADENCE-NULL",
    issue="#198",
    statement="Re-estimating ONLY the vol-gate threshold on a trailing window (same length as the frozen "
              "seed, causal, calendar cadence) does NOT recover the fleet's forward decay at $25/rt: "
              "quarterly -$4,070 and monthly -$710 vs frozen (bootstrap CI95s straddle zero), while the "
              "random-percentile churn control landed at +$36,792 by trading LESS — on a friction-negative "
              "window, fewer trades beat recalibrated trades. The dark slots do reopen (NQ 2m fresh "
              "entries 20 -> 46/86) but the reopened trades roughly pay the toll. The LIVE-PROTOCOL ships "
              "with FROZEN gates. Recorded as exploratory (post-hoc, NOT a verdict): on the 9 allowlist "
              "slots recalibration improved fresh net@$25 (+$17.1k/+$15.0k vs frozen, control $16.7k) — a "
              "pre-registrable hypothesis for #186/#199, not a result.",
    source="optimize/gatecal/data/gatecal_verdict.json + gatecal_a0_parity.json + gatecal_summary_*.json + docs/WS-GATECAL-PREREGISTRATION.md",
    value_fn=_n_positive,
    expect=0.0,
    tol=0.0,
    blind_spot="One fresh window (1-2.5 months per instrument) judged at fleet level; per-slot effects are "
               "under-powered and unlabelled here. The percentile itself was never re-fit (that is #186's "
               "optimization question, deliberately out of scope). The allowlist-subset observation is "
               "selection-on-selection and must not enter any protocol without its own pre-registration.",
    checks=[Check("V1", "off-state-is-the-engine", _v1),
            Check("V2", "verdict-rederives-from-frozen-rule", _v2),
            Check("V3", "hook-acts-and-rule-can-refuse", _v3)],
))
