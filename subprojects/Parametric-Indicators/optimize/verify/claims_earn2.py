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


# =============================================================================================
# E-S1 — the earnings event-state dataset v1 (the ×indicators substrate)
# =============================================================================================
def _es1(inst: str) -> pd.DataFrame:
    return pd.read_csv(EARN / f"es1_event_state_{inst}.csv", parse_dates=["et"])


def _es1_man(inst: str) -> dict:
    return json.load(open(EARN / f"es1_manifest_{inst}.json"))


def _es1_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: on both legs, the power context re-joined LOCALLY against the
    committed ep1_events files must match exactly; stance columns 330; alphabet respected."""
    for inst in ("NQ", "ES"):
        d = _es1(inst)
        ref = pd.read_csv(EARN / f"ep1_events_{inst}.csv", parse_dates=["event_et"])
        j = ref.rename(columns={"event_et": "et", "ticker": "title"}).merge(
            d[["et", "title", "pred", "jump_pct"]], on=["et", "title"],
            how="left", suffixes=("_ref", ""))
        if len(j) != len(ref) or (j.pred - j.pred_ref).abs().max() > 1e-9 \
                or (j.jump_pct - j.jump_pct_ref).abs().max() > 1e-9:
            return False, f"{inst}: power context does not re-derive"
        sc = [c for c in d.columns if c.startswith(("cdir_", "vdir_"))]
        if len(sc) != 330:
            return False, f"{inst}: {len(sc)} stance cols"
        vals = set(np.unique(d[sc].fillna(0).to_numpy().ravel()))
        if not vals.issubset({-1.0, 0.0, 1.0, 2.0}):
            return False, f"{inst}: alphabet violated"
    return True, "power context cent-exact vs E-P1 evidence; 330 cols; alphabet clean (both legs)"


def _es1_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT COST IDENTITY: reference bracket net must equal pnl − the deployed
    stressed cost (constants from the LIVE executor, not the build) on every outcome row."""
    import sys as _s
    _s.path.insert(0, str(EARN.parents[3]))
    from src.deploy.release_executor import COST_PER_LEG
    for inst in ("NQ", "ES"):
        d = _es1(inst)
        m = d.ride_pnl_usd.notna()
        if not np.allclose(d.loc[m, "ride_net_stressed_usd"],
                           d.loc[m, "ride_pnl_usd"] - COST_PER_LEG[inst]["stressed"]):
            return False, f"{inst}: cost identity broken"
    return True, "net = pnl − live stressed cost on all outcome rows (both legs)"


def _es1_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER + NON-DEGENERACY: all 8 manifest gates PASS (incl. the C2 repaint
    falsifier) and the state vector varies (≥60% of cdir columns take ≥2 values)."""
    for inst in ("NQ", "ES"):
        g = _es1_man(inst)["gates"]
        if not all(g[k]["pass"] for k in g):
            return False, f"{inst}: gate failed"
        d = _es1(inst)
        cd = [c for c in d.columns if c.startswith("cdir_")]
        if np.mean([d[c].nunique() > 1 for c in cd]) < 0.60:
            return False, f"{inst}: degenerate state vector"
    return True, "8/8 gates incl. repaint falsifier; state varies (both legs)"


register(Claim(
    id="ES1-EVENT-STATE-DATASET",
    issue="#169",
    statement="The earnings event-state dataset v1 is BUILT and gate-clean: 462 rows × 2 "
              "legs (NQ, ES) over the 12-ticker 16-year table — per row: the E-P1 power "
              "context (parity-anchored EXACTLY to the committed evidence on all 366 scored "
              "rows), the frozen macro bracket as a REFERENCE outcome (432/462 with 1s "
              "coverage; H1 already rejected this ride — stored as what-it-would-do), and "
              "the 165-registry stance vector at stamp−300s (the repaint falsifier again "
              "proves no indicator repaints, 25×165 per leg). v1 FROZEN; the substrate for "
              "the ×indicators phase — which remains bound to mechanism-first, locked-"
              "holdout pre-registrations (the fusion era measured macro state-conditioning "
              "at ≈zero).",
    source="optimize/earnings/data/es1_event_state_{NQ,ES}.csv + manifests",
    value_fn=lambda: sum(len(_es1(i)) for i in ("NQ", "ES")),
    expect=924, tol=0,
    blind_spot="Acceptance-lag shifts stance bar and bracket entry (C4 human check #110 the "
               "eventual cure); AMC thin sessions make bracket fills model-grade; default "
               "params; NQ/ES only (RTY/YM declared v2); cross-series stance columns "
               "structurally neutral.",
    checks=[Check("V1", "power context re-derives vs E-P1; schema/alphabet clean", _es1_v1),
            Check("V2", "net = pnl − live stressed cost identity", _es1_v2),
            Check("V3", "8/8 gates incl. repaint falsifier; non-degenerate", _es1_v3)]))


# =============================================================================================
# E-X2 — the joint two-calendar forecast: NOT CERTIFIED (line 2 missed by a hair; rule held)
# =============================================================================================
def _ex2(inst: str) -> dict:
    return json.load(open(EARN / f"ex2_result_{inst}.json"))


def _ex2_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: on both instruments the recorded lines must re-derive from the
    recorded scores under the registered thresholds (1.001 tolerances; union CI)."""
    for inst in ("NQ", "ES"):
        r = _ex2(inst)
        S = r["scores"]
        want = {
            "1_no_macro_degradation": S["Cj"]["macro"] <= 1.001 * S["Cm"]["macro"],
            "2_no_earn_degradation": S["Cj"]["earn"] <= 1.001 * S["Ce"]["earn"],
            "3_union_ci": r["decision_union"]["boot90_ci"][0] > 0
                          and r["decision_union"]["mean_diff_B_minus_Cj"] > 0,
            "4_overall_single_best": S["Cj"]["overall"] <= 1.001 * min(
                S["B"]["overall"], S["Cm"]["overall"], S["Ce"]["overall"]),
        }
        if {k: bool(v) for k, v in want.items()} != r["lines"]:
            return False, f"{inst}: lines do not re-derive"
    return True, "lines re-derive from scores on both instruments"


def _ex2_v2() -> tuple[bool, str]:
    """V2 — THE WITNESS: ES passes ALL FOUR lines (the composition is clean there) and its
    union differential is CI-positive — the failure is NQ-local and small, not structural."""
    r = _ex2("ES")
    ok = all(r["lines"].values()) and r["decision_union"]["boot90_ci"][0] > 0
    return ok, f"ES lines {r['lines']}; union CI {r['decision_union']['boot90_ci']}"


def _ex2_v3() -> tuple[bool, str]:
    """V3 — BAR INTEGRITY (the third in the series): NQ's line 2 fails by ≈0.05% beyond the
    registered 0.1% tolerance while lines 1/3/4 pass and the union CI is hugely positive —
    and the verdict must still be NOT-CERTIFIED. The appealing composition was not promoted
    over its own registered line."""
    r = _ex2("NQ")
    S = r["scores"]
    ratio = S["Cj"]["earn"] / S["Ce"]["earn"]
    ok = (not r["lines"]["2_no_earn_degradation"] and 1.001 < ratio < 1.01
          and r["lines"]["1_no_macro_degradation"] and r["lines"]["3_union_ci"]
          and r["lines"]["4_overall_single_best"])
    return ok, f"NQ earn ratio {ratio:.5f} vs 1.001 line; other lines pass — rule held"


register(Claim(
    id="EX2-JOINT-FORECAST-NOT-CERTIFIED",
    issue="#169",
    statement="The joint two-calendar forecast is NOT CERTIFIED, by its own registered "
              "rule: on NQ the joint model degrades earnings-bar QLIKE by 0.15% vs the "
              "single-calendar model (0.7945→0.7957) against the pre-registered 0.1% "
              "no-degradation line — a miss of ≈0.05%, and the rule held (the third "
              "near-miss refused: FU-6's 0.003 AUC, FU-3's CI touch, now this). The "
              "texture recorded WITH the verdict: ES passes ALL FOUR lines cleanly "
              "(composition is clean there), the union differential is hugely CI-positive "
              "on both (NQ +4.52 [3.20,6.09]; ES +5.29), and the joint model is the "
              "overall single-best forecast on both instruments (NQ 0.4853 vs B 0.5485). "
              "Consequence: the single-calendar models stand alone as the reference "
              "repairs; E-D1 (productionization) is NOT armed; a v2 with a freshly "
              "registered tolerance may be filed later — never a post-hoc widening.",
    source="optimize/earnings/data/ex2_result_{NQ,ES}.json",
    value_fn=lambda: round(_ex2("NQ")["decision_union"]["mean_diff_B_minus_Cj"], 4),
    expect=4.5245, tol=0.0001,
    blind_spot="n=92 earnings bars makes the 0.1% line noise-sensitive — that is a design "
               "lesson (tolerances must be powered), recorded for any v2 registration; "
               "research frames; two instruments; zero overlap bars (08:30 vs 16:30 clocks) "
               "so no shared-bar stress was actually exercised.",
    checks=[Check("V1", "lines re-derive from scores under the registered thresholds", _ex2_v1),
            Check("V2", "ES passes all four lines (the failure is NQ-local, small)", _ex2_v2),
            Check("V3", "the near-miss was refused — bar integrity, third in the series", _ex2_v3)]))


# =============================================================================================
# E-C1 — earnings × indicators: CLOSED-NULL (the conditioning phase closes)
# =============================================================================================
def _ec1() -> dict:
    return json.load(open(EARN / "ec1_result.json"))


def _ec1_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: the P_hist baseline rho on HOLDOUT-1 recomputed locally from the
    frozen E-S1 file must match the manifest (the anchor both deltas hang on)."""
    from scipy import stats
    d = pd.read_csv(EARN / "es1_event_state_NQ.csv", parse_dates=["et"])
    d = d.dropna(subset=["pred", "jump_pct"])
    h1 = d[d.et >= "2023-01-01"]
    r = float(stats.spearmanr(h1.pred, h1.jump_pct)[0])
    m = _ec1()
    ok = abs(r - m["baseline_rho"]["h1"]) < 5e-4 and len(h1) == m["n_h1"]
    return ok, f"H1 baseline rho {r:+.4f} (n={len(h1)}) re-derives"


def _ec1_v2() -> tuple[bool, str]:
    """V2 — RULE INTEGRITY: both models' verdicts follow the registered ARMED rule from
    their recorded fields (deltas CI-clear NEGATIVE ⇒ nothing armed), and the ES holdout
    deltas are negative too — the degradation replicates on the untouched instrument."""
    r = _ec1()
    for name, m in r["models"].items():
        armed = m["delta_h1"] > 0 and m["delta_ci90"][0] > 0 \
            and m["delta_h1"] > m["perm_p95"] and m["delta_h2"] > 0
        if armed or m["verdict"] != "CLOSED-NULL":
            return False, f"{name}: rule violated"
        if not (m["delta_ci90"][1] < 0 and m["delta_h2"] < 0):
            return False, f"{name}: expected CI-clear negative + ES-negative"
    return True, "both models CI-clear negative on H1 AND negative on untouched ES"


def _ec1_v3() -> tuple[bool, str]:
    """V3 — ATTRIBUTION HONESTY: the permuted-stance controls ALSO degrade (ridge perm95
    −0.30) — most of the loss is the extra degrees of freedom, not information; and the
    record admits the CONTRARIAN clause was under-instrumented (no permuted 5th percentile
    recorded), so 'state actively misleads' stays an open note, never a claimed finding."""
    r = _ec1()
    ridge = r["models"]["ridge"]
    ok = ridge["perm_p95"] < -0.1 and ridge["delta_h1"] < ridge["perm_p95"]
    return ok, (f"ridge perm95 {ridge['perm_p95']:+.4f} (dof noise dominates); real "
                f"{ridge['delta_h1']:+.4f}; contrarian question left OPEN by design")


register(Claim(
    id="EC1-STATE-ADDS-NO-SIZE",
    issue="#169",
    statement="Earnings × indicators CLOSES NULL on both fixed models — and the "
              "conditioning phase CLOSES with the state-blind law extended to SIZE: adding "
              "the 292-usable-column stance vector to P_hist DEGRADES holdout size ranking "
              "(ridge Δ −0.3930 CI [−0.5569, −0.2212]; tree Δ −0.1313 CI [−0.2061, "
              "−0.0586]; both also negative on the untouched ES holdout), with the "
              "permuted-stance controls showing most of the loss is pure degrees-of-freedom "
              "noise (ridge perm95 −0.30). P_hist ALONE is the best size forecast measured. "
              "The state-blind result now spans: direction (3 proofs), outcomes (FU-5/6), "
              "macro conditioning (FU-2/3/7), and earnings SIZE (this) — the library "
              "measures the tape; it does not predict the calendar.",
    source="optimize/earnings/data/ec1_result.json",
    value_fn=lambda: _ec1()["models"]["ridge"]["delta_h1"],
    expect=-0.393, tol=0.0001,
    blind_spot="The CONTRARIAN clause was under-instrumented (no permuted 5th percentile "
               "recorded) — whether real stances mislead BEYOND dof noise stays an open "
               "note, not a finding; n_train=191 with 293 features leans on regularization; "
               "two models, one look each; E-S1's declarations inherit.",
    checks=[Check("V1", "the P_hist holdout baseline re-derives from the frozen E-S1 file", _ec1_v1),
            Check("V2", "verdicts follow the rule; degradation replicates on ES", _ec1_v2),
            Check("V3", "dof-noise attribution honest; contrarian left open by design", _ec1_v3)]))


# =============================================================================================
# E-X2 v2 — powered tolerances: the interference is REAL (v1 confirmed at proper power)
# =============================================================================================
def _ex2v2(inst: str) -> dict:
    return json.load(open(EARN / f"ex2v2_result_{inst}.json"))


def _ex2v2_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: on both instruments each recorded line must re-derive from its
    recorded CI under the registered forms (fail iff CI-hi<0 for lines 1/2/4; CI-lo>0 for 3)."""
    for inst in ("NQ", "ES"):
        r = _ex2v2(inst)
        d = r["detail"]
        want = {"1_no_macro_degradation": d["1_macro"]["ci90"][1] >= 0,
                "2_no_earn_degradation": d["2_earn"]["ci90"][1] >= 0,
                "3_union_ci": d["3_union"]["mean"] > 0 and d["3_union"]["ci90"][0] > 0,
                "4_no_rival_overall": all(d[f"4_overall_vs_{x}"]["ci90"][1] >= 0
                                          for x in ("B", "Cm", "Ce"))}
        if {k: bool(v) for k, v in want.items()} != r["lines"]:
            return False, f"{inst}: lines do not re-derive"
    return True, "lines re-derive from CIs on both instruments"


def _ex2v2_v2() -> tuple[bool, str]:
    """V2 — THE CONFIRMATION STRUCTURE: NQ line 2 is CLEAR-negative (the degradation is
    significant, not noise — v1's fixed ratio was accidentally right) while ES passes all
    four — the interference is NQ-local, replicating v1's geography exactly."""
    nq = _ex2v2("NQ")
    es = _ex2v2("ES")
    ok = (nq["detail"]["2_earn"]["ci90"][1] < 0 and not nq["all_pass"]
          and es["all_pass"])
    return ok, (f"NQ L2 CI {nq['detail']['2_earn']['ci90']} clear-negative; ES all-pass "
                f"{es['all_pass']}")


def _ex2v2_v3() -> tuple[bool, str]:
    """V3 — POWER HONESTY: the powered line did its job in BOTH directions — it localizes
    the real effect (NQ L2 mean −0.0013 vs its MDE 0.0011: just detectable) and it passes
    the noise-level differences it should pass (NQ L1 mean −0.0002 with CI touching 0)."""
    nq = _ex2v2("NQ")
    L1, L2 = nq["detail"]["1_macro"], nq["detail"]["2_earn"]
    ok = (abs(L2["mean"]) > L2["mde"] and L1["ci90"][1] >= 0
          and abs(L1["mean"]) <= 2 * L1["mde"])
    return ok, (f"L2 |mean| {abs(L2['mean'])} > MDE {L2['mde']} (detected); "
                f"L1 mean {L1['mean']} within noise (passed)")


register(Claim(
    id="EX2V2-INTERFERENCE-CONFIRMED",
    issue="#169",
    statement="E-X2 v2 (powered CI-form tolerances, BOTH instruments required) FAILS — and "
              "thereby CONFIRMS v1 at proper power: the joint model's NQ earnings-bar "
              "degradation is STATISTICALLY REAL (paired C_e − C_j = −0.0013, CI90 "
              "[−0.0024, −0.0003], just above its own MDE 0.0011), not noise — v1's "
              "fixed-ratio near-miss was a true detection. ES passes all four lines "
              "(composition clean there); the interference is NQ-local, matching v1's "
              "geography. VERDICT: the single-calendar models (FU-11 macro, E-X1 earnings) "
              "stand PERMANENTLY as the reference repairs; a fitted joint model is dead on "
              "NQ. The engineering insight recorded: composition at the MODEL level "
              "interferes; composition at the ROUTING level (each certified model applied "
              "to its own calendar's bars) is interference-free BY CONSTRUCTION and "
              "inherits each model's certification — the natural E-D1 design, awaiting the "
              "owner's word, never smuggled.",
    source="optimize/earnings/data/ex2v2_result_{NQ,ES}.json",
    value_fn=lambda: _ex2v2("NQ")["detail"]["2_earn"]["mean"],
    expect=-0.0013, tol=0.0001,
    blind_spot="v2 was registered after v1's numbers were known (declared in the pre-reg; "
               "legitimacy = house-standard CI form + added strictness + v1 standing); "
               "the detected degradation is tiny in absolute terms (−0.0013 QLIKE) — real "
               "and irrelevant to any consumer except a fitted joint model; n≈92 earnings "
               "bars bounds what the powered line can see (MDEs reported).",
    checks=[Check("V1", "lines re-derive from CIs under the registered forms", _ex2v2_v1),
            Check("V2", "NQ clear-negative + ES all-pass: v1's geography confirmed", _ex2v2_v2),
            Check("V3", "the powered line detects the real effect AND passes noise", _ex2v2_v3)]))
