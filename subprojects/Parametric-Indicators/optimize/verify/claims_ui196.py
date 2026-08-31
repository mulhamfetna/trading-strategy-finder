"""#196 (RUNG-4 board #194, phase 1) — one engine per number on the dashboard's L1 view.

Root cause found 2026-08-30: /api/backtest_causal merged the CAUSAL engine's money cards (meta.boxes —
the numbers the books and claims use) with the OLD strategy engine's trades ledger (strategy.build_payload)
in ONE response — on ES 15m: 180 trades/$14,033 on the ledger vs 205/$28,905 on the cards, stable across
re-runs (not caching). Fix: the merged L1 payload now serves the causal layer's trades and equity on every
user-facing surface. Evidence: the pre-fix reproduction gate (25/54 count mismatches) and the post-fix gate
(0/54) — same books, same dashboard, ~2 h apart.
"""
from __future__ import annotations

import json
from pathlib import Path

from harness import Check, Claim, register

D = Path(__file__).resolve().parents[1] / "fwd" / "data_r2"


def _g(name: str) -> dict:
    return json.load(open(D / name))


def _mv(x: str) -> int:
    return int(x.replace("$", "").replace(",", "").replace("+", ""))


def _v1() -> tuple[bool, str]:
    """V1 — THE BUG WAS REAL AND STABLE: the pre-fix reproduction gate (gate_196.json, run fresh on
    2026-08-30, after restarts and cache wipes) still shows 25/54 slots with a status-line count that is
    not the causal book's — ES 15m at 180 vs 205 — ruling out the stale-cache explanation."""
    g = _g("gate_196.json")
    bad = [k for k, v in g.items() if v["seen_n"] != v["want_n"]]
    es = g["ES_15m"]
    ok = len(bad) == 25 and (es["seen_n"], es["want_n"]) == (180, 205)
    return ok, f"pre-fix count mismatches {len(bad)}/54; ES_15m {es['seen_n']} vs {es['want_n']}"


def _v2() -> tuple[bool, str]:
    """V2 — THE FIX CLOSES IT WITHOUT MOVING MONEY: the post-fix gate (gate_196b.json) has 0/54 count
    mismatches while the money distribution is unchanged (26 dollar-exact, all within the cent-rounding
    bound, worst $25) — the change touched which ledger is DISPLAYED, not any computed number."""
    g = _g("gate_196b.json")
    bad = [k for k, v in g.items() if v["seen_n"] != v["want_n"]]
    dm = [abs(_mv(v["seen_pnl"]) - _mv(v["want_pnl"])) for v in g.values()]
    ok = not bad and sum(1 for d in dm if d == 0) == 26 and max(dm) <= 25
    return ok, f"post-fix count mismatches {len(bad)}/54; money exact {sum(1 for d in dm if d==0)}/54, worst ${max(dm)}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the fix changed exactly the diseased surface): comparing the two gate JSONs slot
    by slot, every one of the 25 pre-fix mismatching slots now matches, NO slot's wanted book count
    changed between runs (same books), and the golden NQ slots were exact in BOTH runs (the fix could not
    have 'fixed' NQ because NQ was never broken)."""
    a, b = _g("gate_196.json"), _g("gate_196b.json")
    healed = all(b[k]["seen_n"] == b[k]["want_n"] for k, v in a.items() if v["seen_n"] != v["want_n"])
    same_books = all(a[k]["want_n"] == b[k]["want_n"] for k in a)
    nq_both = all(a[k]["seen_n"] == a[k]["want_n"] and b[k]["seen_n"] == b[k]["want_n"]
                  for k in a if k.startswith("NQ_"))
    ok = healed and same_books and nq_both
    return ok, f"25 diseased slots healed={healed}; books identical across runs={same_books}; NQ exact in both={nq_both}"


def _mismatches_after() -> float:
    return float(sum(1 for v in _g("gate_196b.json").values() if v["seen_n"] != v["want_n"]))


register(Claim(
    id="UI-TRADES-SINGLE-ENGINE",
    issue="#196",
    statement="The dashboard's L1 view now serves ONE engine per number: the merged /api/backtest_causal "
              "payload's trades ledger and equity come from the causal engine (the same rows the books and "
              "claims use), closing the strategy-vs-causal count divergence — 25/54 slots mismatching "
              "before the fix (ES 15m: 180 shown vs 205 in the book, with the two engines also disagreeing "
              "$14,033 vs $28,905 on the hidden strategy ledger), 0/54 after, with the money surface "
              "unchanged and the golden gate ALL MATCH. No live surface can read the wrong ledger again.",
    source="optimize/fwd/data_r2/gate_196.json + optimize/fwd/data_r2/gate_196b.json",
    value_fn=_mismatches_after,
    expect=0.0,
    tol=0.0,
    blind_spot="The gate reads headline cards and the status line, not chart pixels; the old strategy "
               "engine still powers the L1 view's auxiliary charts (vol/state/drawdown/events) by design — "
               "those are qualitative panels, and aligning them is not claimed here. The round-2 claim's "
               "pinned ES_15m failure stays in the ledger as the historical record that found this.",
    checks=[Check("V1", "bug-real-and-stable", _v1),
            Check("V2", "fix-closes-without-moving-money", _v2),
            Check("V3", "healed-exactly-the-diseased-slots", _v3)],
))
