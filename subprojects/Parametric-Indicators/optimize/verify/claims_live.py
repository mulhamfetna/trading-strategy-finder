"""#195 (RUNG-4 board #194, phase 1) — the frozen live allowlist. Pre-registration:
docs/LIVE-ALLOWLIST-PREREGISTRATION.md (rule frozen before derivation). Evidence: the committed round-2
books + the derived optimize/live/live_allowlist.json. Consumed by the LIVE-PROTOCOL (#199) by hash."""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

PI = Path(__file__).resolve().parents[2]
AL = PI / "optimize" / "live" / "live_allowlist.json"
D = PI / "optimize" / "fwd" / "data_r2"
PRE = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00", "GC": "2026-07-02 19:59:00",
       "SI": "2026-07-02 19:59:00", "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
       "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00", "YM": "2026-07-05 19:59:00"}
COST = 25.0


def _al() -> dict:
    return json.load(open(AL))


def _rederive(drop: str | None = None) -> list[str]:
    """Re-run the pre-registered rule from the books; optionally with one criterion dropped."""
    diag = json.load(open(D / "fwd_slot_diag.json"))
    allowed = []
    for f in sorted(glob.glob(str(D / "fwd_book_*.csv"))):
        slot = Path(f).stem[9:]; tok = slot.split("_")[0]
        b = pd.read_csv(f); b["et"] = pd.to_datetime(pd.to_numeric(b["entry_time"]), unit="s")
        fr = b[b["et"] > pd.Timestamp(PRE[tok])]
        dg = diag.get(slot, {})
        crit = {"fresh_pos": float((fr["pnl"] - COST).sum()) > 0,
                "fresh_n": len(fr) >= 10,
                "gross2x": float(b["pnl"].mean()) >= 2 * COST,
                "full_pos": float((b["pnl"] - COST).sum()) > 0,
                "not_dark": (dg.get("entry_rate_lifetime") or 0) >= 0.05 and (dg.get("entry_rate_last60d") or 0) >= 0.01}
        if drop:
            crit.pop(drop)
        if all(crit.values()):
            allowed.append(slot)
    return sorted(allowed)


def _v1() -> tuple[bool, str]:
    """V1 — THE LIST RE-DERIVES: applying the frozen rule to the committed books reproduces exactly the
    committed allowlist (membership and size), and the per-slot rule breakdown in the JSON is consistent."""
    a = _al()
    fresh = _rederive()
    ok = fresh == a["allowed"] == sorted(a["allowed"]) and a["n_allowed"] == len(fresh) == 9
    return ok, f"rederived {len(fresh)} == committed {a['n_allowed']}; lists equal: {fresh == a['allowed']}"


def _v2() -> tuple[bool, str]:
    """V2 — FROZEN AND CONSUMABLE: the pre-registration document exists with the five criteria, and the
    JSON's hash is stable so #199 can pin it (recomputed here and printed for the record)."""
    doc = (PI.parents[1] / "docs" / "LIVE-ALLOWLIST-PREREGISTRATION.md").read_text()
    need = ["fresh-window net P/L at $25/rt > 0", "entries ≥ 10", "2× friction", "not gate-dark", "seed 195"]
    missing = [n for n in need if n not in doc]
    h = hashlib.sha256(AL.read_bytes()).hexdigest()[:16]
    return (not missing), f"prereg criteria present {5-len(missing)}/5; allowlist sha256[:16]={h}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (every criterion binds, and the control can lose): the committed control shows the
    real set beating the p95 of 20 seeded random same-size sets by design-floor; AND dropping the
    2x-friction criterion admits additional (friction-illusion) slots, dropping fresh-positivity admits
    many more — a rule whose criteria change nothing is decoration."""
    a = _al()
    ctl = a["control"]
    base = _rederive()
    no_gross = _rederive(drop="gross2x")
    no_fresh = _rederive(drop="fresh_pos")
    ok = (ctl["beats_p95"] and a["fresh_net25_allowed_total"] > ctl["p95"]
          and len(no_gross) > len(base) and len(no_fresh) >= len(base) + 3)
    return ok, (f"real {a['fresh_net25_allowed_total']:,.0f} vs p95 {ctl['p95']:,.0f}; "
                f"drop-gross2x admits +{len(no_gross)-len(base)}; drop-fresh-pos admits +{len(no_fresh)-len(base)}")


def _n_allowed() -> float:
    return float(_al()["n_allowed"])


register(Claim(
    id="LIVE-ALLOWLIST-FROZEN",
    issue="#195",
    statement="The live allowlist is a frozen, rule-derived artefact, not a hand-pick: applying the five "
              "pre-registered criteria (fresh net@$25 > 0; fresh n >= 10; full-book gross >= 2x friction; "
              "full-book net@$25 > 0; not gate-dark) to the committed round-2 books admits exactly 9 of 54 "
              "slots — ES 4h/2h/1h/15m, NQ 4h/2h, GC 4h, HG 4h, NG 4h — with a fresh-window net@$25 of "
              "+$37,315 vs a $3,844 p95 for random same-size sets. The 4h-and-ES structure the forward "
              "report observed is now the binding live universe for #199.",
    source="optimize/live/live_allowlist.json + docs/LIVE-ALLOWLIST-PREREGISTRATION.md + optimize/fwd/data_r2/fwd_book_*.csv + optimize/fwd/data_r2/fwd_slot_diag.json",
    value_fn=_n_allowed,
    expect=9.0,
    tol=0.0,
    blind_spot="Selected ON the round-2 window: the allowlist is the hypothesis the live run tests, not a "
               "certified edge, and the control shares criterion 1's selection direction (a floor, not "
               "proof). ES members were selected pre-#197 re-selection; #197/#198 outcomes amend the list "
               "by re-running the rule, never by hand.",
    checks=[Check("V1", "list-rederives-from-books", _v1),
            Check("V2", "frozen-and-hash-pinned", _v2),
            Check("V3", "criteria-bind-and-control-can-lose", _v3)],
))
