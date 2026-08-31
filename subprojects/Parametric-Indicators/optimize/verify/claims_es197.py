"""#197 (RUNG-4 board #194, phase 2) — ES re-selection on the corrected box. Pre-registration:
docs/WS-ES197-PREREGISTRATION.md + two dated PRE-RESULTS amendments (budget; search space).
Evidence: optimize/es197/data/ (decision JSON, the fresh champion set, six Pareto CSVs, leaderboard)."""
from __future__ import annotations

import json
from pathlib import Path

from harness import Check, Claim, register

PI = Path(__file__).resolve().parents[2]
D = PI / "optimize" / "es197" / "data"
TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def _dec() -> dict:
    return json.load(open(D / "es197_decision.json"))


def _v1() -> tuple[bool, str]:
    """V1 — EVERY DECISION RE-DERIVES FROM THE FROZEN RULE: adopt iff (fresh median-fold net@$25 >
    incumbent median + incumbent fold SE) AND gross >= 2x friction AND full net@$25 > 0 AND not
    gate-dark. Applying that to the committed fold numbers reproduces RETAIN x6."""
    d = _dec()
    bad = []
    for tf in TFS:
        r = d[tf]
        c = {"beats": r["fresh_median"] > r["incumbent_median"] + r["incumbent_fold_se"],
             "gross": r["fresh_full"]["gross_per_trade"] >= 50.0,
             "net": r["fresh_full"]["net25"] > 0,
             "dark": r["fresh_full"]["entry_rate"] >= 0.05}
        want = "ADOPT" if all(c.values()) else "RETAIN"
        if want != r["decision"] or list(c.values()) != list(r["criteria"].values()):
            bad.append(tf)
    return (not bad), (f"6/6 re-derive (RETAIN x6)" if not bad else f"diverge: {bad}")


def _v2() -> tuple[bool, str]:
    """V2 — THE CAMPAIGN WAS REAL AND THE CANDIDATES DIFFER: the committed fresh champion set exists for
    all six TFs with finite params, and differs from the incumbent set on every slot (a copied file
    could not produce these fold numbers); the six Pareto CSVs are non-empty."""
    fresh = json.load(open(D / "es197b_champions_full_ES.json"))
    inc = json.load(open(PI / "optimize" / "results" / "best_champions_full_ES.json"))
    same = [tf for tf in TFS if json.dumps(fresh[tf]["box"], sort_keys=True) == json.dumps(inc[tf]["box"], sort_keys=True)]
    empt = [tf for tf in TFS if (D / f"{tf}_wsi_pareto_ES.csv").stat().st_size < 1000]
    ok = not same and not empt and all(tf in fresh for tf in TFS)
    return ok, f"fresh==incumbent on {same or 'none'}; thin pareto CSVs: {empt or 'none'}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the rule is not rubber-stamp-retain): three slots came within ONE criterion of
    adoption, each blocked by a DIFFERENT clause — 2h beat the incumbent's median but not by the fold SE;
    5m beat by SE and passed the money criteria but is gate-dark; 2m beat by SE but fails the friction
    criteria. A rule that always retains would show uniform failures; a rule that always adopts would
    have adopted these."""
    d = _dec()
    c2h, c5m, c2m = d["2h"]["criteria"], d["5m"]["criteria"], d["2m"]["criteria"]
    ok = (d["2h"]["fresh_median"] > d["2h"]["incumbent_median"] and not c2h["beats_incumbent_by_SE"]
          and c5m["beats_incumbent_by_SE"] and not c5m["not_gate_dark"]
          and c2m["beats_incumbent_by_SE"] and not c2m["gross_2x_friction"])
    return ok, ("2h blocked by SE margin; 5m by gate-darkness; 2m by friction — three near-adopts, "
                "three different blocking clauses")


def _n_adopted() -> float:
    return float(sum(1 for tf in TFS if _dec()[tf]["decision"] == "ADOPT"))


register(Claim(
    id="ES197-RETAIN-ALL-SIX",
    issue="#197",
    statement="ES re-selection on the corrected box: a full fresh campaign (es197b — 5,899 trials/slot in "
              "the incumbents' own 18-indicator space after the pre-results amendments; 2,595-4,722 "
              "feasible per study) produced champions that beat the deployed incumbents on NO slot under "
              "the frozen rule at $25/rt: RETAIN x6. The incumbents — although selected on the "
              "double-shifted box — hold up on the corrected one (median-fold nets $8k-$17k on "
              "4h/2h/1h/15m). Bonus finding pinned on #90: the first campaign (full 165-indicator "
              "registry, 454 params/trial) was structurally infeasible — 0 complete in ~2,900 "
              "trials/study — while the 18-indicator space is 44-80% feasible.",
    source="optimize/es197/data/es197_decision.json + optimize/es197/data/es197b_champions_full_ES.json + optimize/es197/data/*_wsi_pareto_ES.csv + docs/WS-ES197-PREREGISTRATION.md",
    value_fn=_n_adopted,
    expect=0.0,
    tol=0.0,
    blind_spot="No OOS exists inside the 20-month corrected-box frame (declared up front): RETAIN means "
               "'not beaten under the training protocol', not 'optimal'. The fresh 5m champion beating a "
               "negative incumbent while gate-dark, and 2h's inside-SE improvement, are recorded as "
               "unadopted observations. The full-registry search question remains #90's, not this claim's.",
    checks=[Check("V1", "decisions-rederive-from-frozen-rule", _v1),
            Check("V2", "campaign-real-candidates-differ", _v2),
            Check("V3", "three-near-adopts-three-blockers", _v3)],
))
