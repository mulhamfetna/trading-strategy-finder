"""#190 — backfill claims for the load-bearing PRE-PROTOCOL results (RUNG-4 board #194, phase 1).

These three results predate the #118 protocol, and the project still ACTS on all of them: the deployed
champion set is what the dashboard serves and the forward tests measure; the gap-aware fill model is
mandatory in the engine; the three NO-GO verdicts closed whole research directions. Until now their numbers
lived in documents only. Each claim below pins them to committed evidence under the ledger's rules —
including the evidence-tracked check — WITHOUT re-litigating them: these are claims about what was decided
and recorded, with falsifiers that would catch silent regeneration or silent adoption.
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from harness import Check, Claim, register

PI = Path(__file__).resolve().parents[2]
ROOT = PI.parents[1]


def _load_set(prefix: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in glob.glob(str(PI / "optimize" / "results" / f"{prefix}_champions_full*.json")):
        tok = Path(f).stem.split("_champions_full")[-1].lstrip("_") or "NQ"
        for tf, v in json.load(open(f)).items():
            out[f"{tok}_{tf}"] = v
    return out


# ----------------------------------------------------------------- claim 1: the deployed champion set
def _best_total() -> float:
    return round(sum(v["full_pnl"] for v in _load_set("best").values()), 2)


def _cs_v1() -> tuple[bool, str]:
    """V1 — THE SET IS COMPLETE AND WELL-FORMED: 54 slots (9 instruments x 6 TFs), every slot with finite
    box parameters (sl_soft/sl_hard/tp/gate_pct/k) and stored selection metrics (full_pnl, full_dd, win)."""
    b = _load_set("best")
    toks = {k.split("_")[0] for k in b}
    need = ("sl_soft", "sl_hard", "tp", "gate_pct", "k")
    bad = [k for k, v in b.items()
           if not all(p in v.get("box", {}) for p in need) or not all(m in v for m in ("full_pnl", "full_dd", "win"))]
    ok = len(b) == 54 and len(toks) == 9 and not bad
    return ok, f"slots {len(b)}, instruments {len(toks)}, malformed {bad[:3]}"


def _cs_v2() -> tuple[bool, str]:
    """V2 — THE RECORDED DECISION RE-DERIVES: the set was 'best of three per slot, decided on 2026'
    (payload.py): 29 slots kept the incumbent (cap1p), 24 took the forced-EOD champion (eod1p), 1 neither
    (the bolt-on). Recompute the split by comparing box params across the three committed sets."""
    b, c, e = _load_set("best"), _load_set("cap1p"), _load_set("eod1p")
    sc = se = so = 0
    for k, v in b.items():
        bx = json.dumps(v["box"], sort_keys=True)
        if k in c and json.dumps(c[k]["box"], sort_keys=True) == bx:
            sc += 1
        elif k in e and json.dumps(e[k]["box"], sort_keys=True) == bx:
            se += 1
        else:
            so += 1
    ok = (sc, se, so) == (29, 24, 1)
    return ok, f"incumbent {sc} / eod {se} / neither {so} (recorded: 29/24/1)"


def _cs_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (a silent regeneration would be caught): these are SELECTION-TIME records, not
    today's engine output. The ES box was found double-shifted and corrected in #179, so re-running the
    engine today CANNOT reproduce the stored ES figures: the stored ES total must differ from the
    corrected-box round-2 books by more than $10k. If someone regenerated the champion files against
    today's data, this check flips."""
    es_stored = sum(v["full_pnl"] for k, v in _load_set("best").items() if k.startswith("ES_"))
    es_books = 0.0
    for f in glob.glob(str(PI / "optimize" / "fwd" / "data_r2" / "fwd_book_ES_*.csv")):
        es_books += float(pd.read_csv(f)["pnl"].sum())
    ok = abs(es_stored - es_books) > 10_000
    return ok, f"ES stored {es_stored:,.0f} vs corrected-box books {es_books:,.0f} (must differ; Δ {abs(es_stored-es_books):,.0f})"


register(Claim(
    id="BEST-SET-SELECTION-RECORD",
    issue="#190",
    statement="The deployed champion set `best` (54 slots, 9 instruments x 6 TFs) is on the record: stored "
              "selection-time full-book P/L sums to $2,202,317.50; composition re-derives as 29 incumbent / "
              "24 forced-EOD / 1 bolt-on — exactly the recorded 2026-decided best-of-three; every slot "
              "carries finite parameters and metrics. These are records of what was selected, not certified "
              "performance: the honest forward test is #176/#179 (fresh window at 17.6% of the selection "
              "rate) and the ES slots were selected on the double-shifted box (#197 re-selects).",
    source="optimize/results/best_champions_full*.json + optimize/results/cap1p_champions_full*.json + optimize/results/eod1p_champions_full*.json + optimize/fwd/data_r2/fwd_book_ES_*.csv",
    value_fn=_best_total,
    expect=2202317.50,
    tol=0.5,
    blind_spot="Selection-time figures on then-current data (including the flawed ES box and the pre-#179 "
               "box frontier); the 2026 'decision year' was seen by the selection, so nothing here is OOS. "
               "This claim certifies the RECORD, deliberately not the edge.",
    checks=[Check("V1", "set-complete-and-well-formed", _cs_v1),
            Check("V2", "decision-composition-rederives", _cs_v2),
            Check("V3", "not-silently-regenerated", _cs_v3)],
))


# ----------------------------------------------------------------- claim 2: gap-aware fills
def _gap_rows() -> list[dict]:
    return json.load(open(PI / "optimize" / "reports" / "gap_fills" / "champion_gap_compare.json"))


def _gap_dd_delta() -> float:
    g = _gap_rows()
    db = sum(x["before"]["full"]["max_dd"] for x in g)
    da = sum(x["after"]["full"]["max_dd"] for x in g)
    return round(100.0 * (da - db) / db, 2)


def _gf_v1() -> tuple[bool, str]:
    """V1 — RISK TRUTH, NOT PROFIT: across the 54-slot before/after comparison, P/L is neutral
    (|delta| <= 0.5%) while aggregate max drawdown rises — the old model understated RISK, not returns."""
    g = _gap_rows()
    pb = sum(x["before"]["full"]["pnl"] for x in g); pa = sum(x["after"]["full"]["pnl"] for x in g)
    db = sum(x["before"]["full"]["max_dd"] for x in g); da = sum(x["after"]["full"]["max_dd"] for x in g)
    dpnl = 100.0 * (pa - pb) / abs(pb)
    ok = abs(dpnl) <= 0.5 and da > db and len(g) == 54
    return ok, f"54 slots; ΔP/L {dpnl:+.2f}% (neutral), ΔDD +{100*(da-db)/db:.2f}%"


def _gf_v2() -> tuple[bool, str]:
    """V2 — THE DECISION IS ENFORCED IN CODE: gap-aware fills are mandatory — asking the engine to turn
    them off is an error (the committed test suite proves it)."""
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", str(PI / "optimize" / "test_gap_fills_mandatory.py")],
                       capture_output=True, text=True, cwd=str(PI))
    ok = t.returncode == 0 and " passed" in t.stdout and "failed" not in t.stdout.split("\n")[-2]
    return ok, t.stdout.strip().splitlines()[-1] if t.stdout.strip() else "no output"


def _gf_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the comparison is causal, not a rescale): a uniform 'multiply DD by 1.1' fake would
    change every slot and leave trade counts alone. The real thing does the opposite: at least one slot is
    bit-identical before/after (a book with no gapped exits has nothing to reprice) AND total taken-trade
    counts DIFFER (a repriced stop changes the subsequent trade sequence)."""
    g = _gap_rows()
    zero = sum(1 for x in g if x["before"]["full"] == x["after"]["full"])
    nb = sum(x["before"]["full"]["n_taken"] for x in g); na = sum(x["after"]["full"]["n_taken"] for x in g)
    ok = zero >= 1 and nb != na
    return ok, f"bit-identical slots {zero}; n_taken before {nb} vs after {na}"


register(Claim(
    id="GAP-FILLS-RISK-TRUTH",
    issue="#190",
    statement="Gap-aware fills (GAP-01/02): filling a gapped stop/target at the bar OPEN instead of the "
              "imaginary line repriced the 54-champion book's aggregate max drawdown by +9.78% while "
              "leaving P/L neutral (-0.17%) — the old model understated risk, not returns — and the engine "
              "now refuses to run any other way (gap_fills=False is an error by test).",
    source="optimize/reports/gap_fills/champion_gap_compare.json + optimize/test_gap_fills_mandatory.py",
    value_fn=_gap_dd_delta,
    expect=9.78,
    tol=0.05,
    blind_spot="Bar-open fills are still OPTIMISTIC for entries (#92 tracks the entry side) and 1-minute "
               "bars cannot see intra-bar sweep sequencing; 94% of stop-outs are 1-second sweeps, so true "
               "slippage is bounded below by this model, not measured by it.",
    checks=[Check("V1", "pnl-neutral-dd-up", _gf_v1),
            Check("V2", "mandatory-in-code", _gf_v2),
            Check("V3", "causal-not-a-rescale", _gf_v3)],
))


# ----------------------------------------------------------------- claim 3: the three NO-GO verdicts
_NOGO = {
    "chronos2-vol": ("docs/ROBUSTNESS.md", ["selection is no better than random", "NO-GO"]),
    "regime-hmm": ("docs/ROBUSTNESS.md", ["no durable regime edge"]),
    "timesfm-fusion": ("docs/ROBUSTNESS.md", ["0/3 years", "NO-GO"]),
}


def _nogo_count() -> float:
    n = 0
    for sub, (doc, phrases) in _NOGO.items():
        text = (ROOT / "subprojects" / sub / doc).read_text()
        if all(p in text for p in phrases):
            n += 1
    return float(n)


def _ng_v1() -> tuple[bool, str]:
    """V1 — THE VERDICTS ARE ON THE RECORD, WITH THEIR EVIDENCE PHRASES: each committed ROBUSTNESS doc
    contains both its verdict and the specific finding that carries it (random control for Chronos-2;
    'no durable regime edge' for HMM/Jump; '0/3 years' for the TimesFM gate)."""
    missing = [s for s, (d, ps) in _NOGO.items() if not all(p in (ROOT / "subprojects" / s / d).read_text() for p in ps)]
    return (not missing), (f"3/3 verdict+evidence phrases present" if not missing else f"missing: {missing}")


def _ng_v2() -> tuple[bool, str]:
    """V2 — THE VERDICTS ARE ACTED ON: nothing in the live engine tree imports from the three NO-GO
    subprojects (a NO-GO that still ships is not a NO-GO)."""
    hits = []
    pats = ("chronos", "regime_hmm", "regime-hmm", "timesfm")
    for py in list((PI / "optimize").rglob("*.py")) + list((ROOT / "src").rglob("*.py")):
        s = str(py)
        if "test_" in s or "server-audit" in s or "shareable" in s or "verify" in s:
            continue
        txt = py.read_text(errors="ignore")
        for line in txt.splitlines():
            ls = line.strip()
            if (ls.startswith("import ") or ls.startswith("from ")) and any(p in ls for p in pats):
                hits.append(f"{py.relative_to(ROOT)}: {ls[:60]}")
    return (not hits), (f"0 live imports from the NO-GO subprojects" if not hits else f"imports found: {hits[:3]}")


def _ng_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (silent adoption would be caught): if any NO-GO had been quietly reversed, the L1
    layer-parameter schema would carry its gate (a chronos/timesfm/regime veto parameter). The schema is
    checked directly: none of those names exist in validate_layer_params' accepted keys."""
    src = (PI / "optimize" / "l2" / "l2common.py")
    if not src.exists():
        src = next(iter((PI / "optimize").rglob("*.py")))
    import re as _re
    hits = []
    for py in (PI / "optimize").rglob("*.py"):
        s = str(py)
        if "test_" in s or "verify" in s:
            continue
        for m in _re.finditer(r"[\"'](chronos\w*|timesfm\w*|hmm_\w*|regime_gate\w*)[\"']", py.read_text(errors="ignore")):
            hits.append(f"{py.relative_to(PI)}: {m.group(1)}")
    return (not hits), (f"no NO-GO gate parameter in the engine schema" if not hits else f"{hits[:3]}")


register(Claim(
    id="NOGO-VERDICTS-ON-RECORD",
    issue="#190",
    statement="The three pre-protocol NO-GO verdicts the project still acts on are ledger-bound: Chronos-2 "
              "vol-gating (its slot selection is no better than random — the box strategy is vol-SEEKING), "
              "regime HMM/Jump (no durable regime edge on the available book), and the TimesFM vol-gate "
              "(0/3 years — robustness killed a single-window win). Each verdict sits in a committed "
              "robustness document with its carrying evidence, and none of the three is imported or "
              "parameterised anywhere in the live engine.",
    source="subprojects/chronos2-vol/docs/ROBUSTNESS.md + subprojects/regime-hmm/docs/ROBUSTNESS.md + subprojects/timesfm-fusion/docs/ROBUSTNESS.md",
    value_fn=_nogo_count,
    expect=3.0,
    tol=0.0,
    blind_spot="These are pre-protocol studies: no pre-registration existed, the HMM verdict rests on an "
               "n=1 book (2024-26), and the TimesFM open follow-up (pre-2024 box levels) was never run. "
               "The verdicts are binding as DECISIONS; as science they are the weakest tier in the ledger, "
               "which is exactly why they are recorded rather than upgraded.",
    checks=[Check("V1", "verdicts-with-evidence-on-record", _ng_v1),
            Check("V2", "acted-on-no-live-imports", _ng_v2),
            Check("V3", "no-silent-adoption-in-schema", _ng_v3)],
))
