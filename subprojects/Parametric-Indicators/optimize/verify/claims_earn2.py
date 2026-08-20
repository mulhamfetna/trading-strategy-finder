"""WS-EARN return claims (#169+) — ledger for the earnings workstream's published numbers.

Protocol: #118. Pre-registrations: docs/EP1-PREREGISTRATION.md (gates frozen pre-run).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

EARN = Path(__file__).resolve().parents[1] / "earnings" / "data"


def _ep1() -> dict:
    return json.load(open(EARN / "ep1_result.json"))


def _ep1_ev(inst: str) -> pd.DataFrame:
    return pd.read_csv(EARN / f"ep1_events_{inst}.csv")


def _ep1_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: the NQ primary Spearman + Fisher CI recomputed locally from the
    committed per-event file must match the manifest."""
    from scipy import stats
    d = _ep1_ev("NQ").dropna(subset=["pred", "jump_pct"])
    r, _ = stats.spearmanr(d.pred, d.jump_pct)
    m = _ep1()["instruments"]["NQ"]
    z = np.arctanh(r); se = 1.0 / np.sqrt(len(d) - 3)
    lo = float(np.tanh(z - 1.96 * se))
    ok = abs(r - m["spearman"]) < 5e-4 and abs(lo - m["fisher_ci"][0]) < 5e-4 \
        and len(d) == m["n_scored"]
    return ok, f"NQ rho {r:+.4f} (n={len(d)}) CI-lo {lo:+.4f} re-derive"


def _ep1_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT INSTRUMENT: the ES full replication re-derived from its own
    committed file; CI-lo must clear zero (a different price file, same stamps)."""
    from scipy import stats
    d = _ep1_ev("ES").dropna(subset=["pred", "jump_pct"])
    r, _ = stats.spearmanr(d.pred, d.jump_pct)
    z = np.arctanh(r); se = 1.0 / np.sqrt(len(d) - 3)
    lo = float(np.tanh(z - 1.96 * se))
    m = _ep1()["instruments"]["ES"]
    ok = abs(r - m["spearman"]) < 5e-4 and lo > 0
    return ok, f"ES rho {r:+.4f} CI-lo {lo:+.4f} > 0"


def _ep1_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER + CONTROL from the manifest's recorded fields: the observed rho beats
    the 200-ticker-shuffle p95 (P_hist rebuilt each shuffle — else the model is vol
    clustering) AND the clean-minute control is ≤ half the real rho AND the quintile scorer
    passes — the full M2 battery, all recorded PASS with the verdict following."""
    r = _ep1()
    nq = r["instruments"]["NQ"]
    ok = (nq["spearman"] > nq["v3_shuffle"]["p95"]
          and abs(nq["control"]["spearman"]) <= 0.5 * abs(nq["spearman"])
          and nq["v1_bucket_spearman"] >= 0.8
          and all(r["gates"].values()) and r["verdict"] == "PASS")
    return ok, (f"shuffle p95 {nq['v3_shuffle']['p95']:+.4f} < rho {nq['spearman']:+.4f}; "
                f"control {nq['control']['spearman']:+.4f}; V1 {nq['v1_bucket_spearman']}")


register(Claim(
    id="EP1-EARNINGS-POWER-FORECASTABLE",
    issue="#169",
    statement="Earnings move SIZE is forecastable the night before, exactly like macro size: "
              "P_hist per ticker (expanding median of the same ticker's prior earnings-"
              "minute |move|%, shifted, ≥8 priors) ranks realized NQ jumps with pooled OOS "
              "Spearman +0.4583, Fisher CI [+0.3733, +0.5356] (n=366 scored of 462 events "
              "with a bar, of 783 in the table) — and the FULL independent ES replication "
              "agrees (+0.3323, CI-lo +0.2379). Quintiles ordered (V1 ≥0.8); 200 ticker-"
              "label shuffles beaten; the clean-minute control materially weaker. The M2 "
              "law extends to earnings: the calendar's violence is rankable from own "
              "history — E-S1 (event-state dataset) and E-X1 (earnings × the fused "
              "forecast) are ARMED, each behind its own pre-registration.",
    source="optimize/earnings/data/ep1_result.json + ep1_events_{NQ,ES}.csv",
    value_fn=lambda: _ep1()["instruments"]["NQ"]["spearman"],
    expect=0.4583, tol=0.0001,
    blind_spot="Acceptance ≠ announcement (INTC ~7min) smears jump_pct DOWN — conservative "
               "for the primary, but a pass does not certify per-minute tradability; 321/783 "
               "events lack a 1m bar at the stamp (AMC thin sessions — counted, not hidden); "
               "12 mega-caps, one index — ticker asymmetry first-class; POWER ≠ PREMIUM "
               "stands (this ranks violence, it does not claim payment).",
    checks=[Check("V1", "NQ primary re-derives from the committed per-event file", _ep1_v1),
            Check("V2", "the ES replication re-derives and clears zero", _ep1_v2),
            Check("V3", "shuffle + control + quintile gates recorded and consistent", _ep1_v3)]))


# =============================================================================================
# E-X1 — earnings × the fused forecast: PASS (the blindness law covers both calendars)
# =============================================================================================
def _ex1(inst: str) -> dict:
    return json.load(open(EARN / f"ex1_result_{inst}.json"))


def _ex1_v1() -> tuple[bool, str]:
    """V1 — INTERNAL RE-DERIVATION: on both instruments the decision differential must equal
    QLIKE(B,event) − QLIKE(C,event); the CI must bracket it; gain_C_over_D must equal the
    score difference."""
    for inst in ("NQ", "ES"):
        r = _ex1(inst)
        d = r["decision"]["mean_diff_B_minus_C"]
        ident = r["scores"]["B"]["event"] - r["scores"]["C"]["event"]
        lo, hi = r["decision"]["boot90_ci"]
        g = r["decomposition"]["gain_C_over_D"]
        gi = r["scores"]["D"]["event"] - r["scores"]["C"]["event"]
        if not (abs(d - ident) < 1e-9 and lo < d < hi and abs(g - gi) < 1e-9):
            return False, f"{inst}: identities broken"
    return True, "identities hold on both instruments"


def _ex1_v2() -> tuple[bool, str]:
    """V2 — THE WITNESS AND THE HONEST ASYMMETRY: the ES differential is CI-positive in
    sign (the registered line-2 witness) AND the recorded fact stands that on ES the
    DEPLOYED fixed-weight HAR beats the fused model on earnings bars (A < C) — the pass is
    recorded WITH its asymmetry, not despite it."""
    r = _ex1("ES")
    ok = (r["decision"]["boot90_ci"][0] > 0
          and r["scores"]["A"]["event"] < r["scores"]["C"]["event"])
    return ok, (f"ES diff CI {r['decision']['boot90_ci']} > 0; A "
                f"{r['scores']['A']['event']:.4f} < C {r['scores']['C']['event']:.4f} "
                f"(deployed weights already good on ES earnings bars)")


def _ex1_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER: on NQ the shuffled-power placebo collapses to the dummy level
    (placebo gain over D ≤ half of C's gain) while C's gain over D is positive — the power
    MAGNITUDE carries the repair, as on the macro calendar."""
    r = _ex1("NQ")
    g = r["decomposition"]["gain_C_over_D"]
    pg = r["decomposition"]["placebo_gain_over_D"]
    ok = g > 0 and pg <= 0.5 * g and all(r["lines"].values())
    return ok, f"NQ C-over-D {g:+.4f}, placebo {pg:+.4f}; lines {r['lines']}"


register(Claim(
    id="EX1-EARNINGS-FUSED-FORECAST-PASS",
    issue="#169",
    statement="E-X1 PASSES its four pre-registered lines: the live vol engine's calendar "
              "blindness extends to EARNINGS bars and the night-before per-ticker power "
              "repairs it — NQ test earnings bars (n=92): QLIKE fitted HAR-LS 1.3046 → "
              "FUSED 0.7945 (deployed 1.0812; dummy-only 0.8569; placebo 0.8569 — exact "
              "collapse: the power magnitude carries it), differential +0.5101 CI90 "
              "[+0.344, +0.704]; ES witness positive (+0.0996, CI clear). TWO honest "
              "asymmetries recorded: the earnings blindness is ≈14× SMALLER than macro "
              "(B ≈1.3 vs CPI's 7.6 — AMC thin bars + single-ticker dilution + the "
              "acceptance-lag smear), and on ES the deployed FIXED weights already beat "
              "every fitted variant on earnings bars. The blindness-and-repair law covers "
              "both calendars; the joint macro+earnings forecast is the declared follow-up; "
              "consumers stay behind the fusion-era laws.",
    source="optimize/earnings/data/ex1_result_{NQ,ES}.json",
    value_fn=lambda: round(_ex1("NQ")["decision"]["mean_diff_B_minus_C"], 4),
    expect=0.5101, tol=0.0001,
    blind_spot="92 test earnings bars (fewer than FU-11's 140); research 1h frames; "
               "acceptance-lag smears event-bar placement; two instruments only; the "
               "earnings dummy beta is NEGATIVE with power positive — the dummy alone "
               "over-corrects, another reason the power term is the load-bearer.",
    checks=[Check("V1", "decision fields re-derive from score fields, both instruments", _ex1_v1),
            Check("V2", "ES witness CI-positive; the A<C asymmetry recorded", _ex1_v2),
            Check("V3", "the placebo collapses on NQ; all lines hold", _ex1_v3)]))
