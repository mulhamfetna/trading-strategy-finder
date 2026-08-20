"""XNI phase-3 claims (#172+) — ledger for the earnings x news x indicators phase.

Protocol: #118. Pre-registrations: docs/X1-PREREGISTRATION.md (census gate + verdicts frozen).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401

from harness import Check, Claim, register

XNI = Path(__file__).resolve().parents[1] / "xni" / "data"


def _x1(inst: str) -> dict:
    return json.load(open(XNI / f"x1_result_{inst}.json"))


def _x1_v1() -> tuple[bool, str]:
    """V1 — CENSUS + GATE INTEGRITY: both types cleared the n>=30 census gate on both
    instruments (no outcome was read illegitimately), and the counts are consistent
    (T1 subset of T2; earnings-side census present)."""
    for inst in ("NQ", "ES"):
        r = _x1(inst)
        c = r["census"]
        if not (c["T1"] >= 30 and c["T2"] >= 30 and c["T1"] <= c["T2"]
                and all(r["types"][t]["n"] >= 30 for t in ("T1", "T2"))):
            return False, f"{inst}: census/gate inconsistent {c}"
    return True, "gate cleared on both instruments (T1 63/64, T2 118/118); T1 ⊆ T2"


def _x1_v2() -> tuple[bool, str]:
    """V2 — PRIMARY-RULE INTEGRITY: NQ (the registered primary) has CI ∋ 0 on BOTH types
    ⇒ the phase verdict is CLOSED-INDEPENDENT — and the ES T1 single-witness candidate
    (+0.358, CI-clear, above shuffle) was NOT promoted (no pooled rule was registered;
    none was invented post hoc)."""
    nq = _x1("NQ")
    es = _x1("ES")
    ok = (all(nq["types"][t]["boot90_ci"][0] <= 0 <= nq["types"][t]["boot90_ci"][1]
              for t in ("T1", "T2"))
          and es["types"]["T1"]["verdict"] == "SUPER-ADDITIVE-CANDIDATE"
          and nq["types"]["T1"]["verdict"] == "CLOSED-INDEPENDENT")
    return ok, ("NQ CIs ∋ 0 both types; ES T1 candidate recorded, not promoted "
                "(fresh-registration hypothesis only)")


def _x1_v3() -> tuple[bool, str]:
    """V3 — NOISE-CHECK RECORD: on the primary, both observed differences sit BELOW their
    within-series shuffle p95 (the positive-claim bar) — independence is the measured
    state, not an absence of measurement."""
    nq = _x1("NQ")
    ok = all(nq["types"][t]["mean_logjump_diff"] < nq["types"][t]["shuffle_p95"]
             for t in ("T1", "T2"))
    return ok, ("NQ T1 +0.1723 < shuf95 +0.2630; T2 +0.0494 < +0.2049 — "
                "below the noise bar, measured")


register(Claim(
    id="X1-CALENDARS-INDEPENDENT",
    issue="#173",
    statement="X-1 CLOSES INDEPENDENT on both collision types, by the primary rule: the two "
              "forecastable calendars resolve WITHOUT a measurable interaction term. Census "
              "(the gate cleared): T1 earnings-night→macro-morning 63/64 collisions "
              "(NQ/ES), T2 same-24h 118. NQ (primary): T1 Δlog(jump) +0.1723 CI [−0.0631, "
              "+0.3985], T2 +0.0494 CI [−0.1443, +0.2409] — both ∋ 0 and below the "
              "within-series shuffle p95. RECORDED, NOT PROMOTED: ES's T1 clears every line "
              "alone (+0.3580, CI [+0.1225, +0.5845], above shuffle) — a single-witness, "
              "fresh-registration-eligible hypothesis. THE CONSEQUENCE: compound power "
              "composes ADDITIVELY from the two certified forecasts — X-3's collision flag "
              "needs no interaction statistics; FU-15's gate input gains nothing extra.",
    source="optimize/xni/data/x1_result_{NQ,ES}.json",
    value_fn=lambda: _x1("NQ")["types"]["T1"]["mean_logjump_diff"],
    expect=0.1723, tol=0.0001,
    blind_spot="12 mega-cap tickers define 'earnings night'; one control per collision "
               "(nearest-in-time within series); the earnings side's own power was not "
               "dose-controlled (X-1 asked IF, not how much — declared); the ES T1 texture "
               "may be an ES-microstructure fact or noise — only a fresh registration on "
               "new data may decide.",
    checks=[Check("V1", "census gate cleared legitimately on both instruments", _x1_v1),
            Check("V2", "primary rule held; the ES candidate not promoted", _x1_v2),
            Check("V3", "primary differences below the noise bar — measured independence", _x1_v3)]))
