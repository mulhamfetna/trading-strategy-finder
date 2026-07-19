"""STRICT extraction of engine parameters from a champion preset.

WHY THIS MODULE EXISTS — read before "simplifying" it.

Six studies (D1, Z1, Z2, Z3, Z4, D4) used to read the champion's stops like this:

    float(p.get("sl_soft_points", 30))          # <- key does not exist
    STOP = 40.0                                 # <- hardcoded, ignores sl_hard
    float(p.get("tp_hard_points", 60))          # <- key does not exist
    bool(p.get("flip_entry_direction", False))  # <- key does not exist

NONE of those key names exist. The preset stores `sl_soft`, `sl_hard`, `tp`, `flip`. Because
`dict.get(key, default)` CANNOT FAIL, every one of those studies silently backtested a 30/40/60
strategy we do not trade, ran to completion, printed a clean table, and reported confident conclusions.
On NQ 4h that is 642 trades at a 41.9% win rate instead of the champion's 445 at 56.0%, with P&L bounds
of -40/+60 instead of -151.4/+125.6. It invalidated the headline results of two workstreams
(#7 own-distribution and #17 fat-tail sizing).

It stayed invisible because `gate_pct` IS spelled correctly — so the preset was demonstrably loaded and
the code looked champion-aware — and because 30/40/60 are plausible numbers that produce a plausible
backtest. D1 in particular hardcoded a 40-point stop, then "discovered" that trade P&L is truncated at
exactly -40, which read as confirmation rather than tautology.

THE RULE: a missing STRATEGY PARAMETER must be a HARD FAILURE, never a default. A default is a silent
wrong answer that costs a workstream; a KeyError costs five minutes.

See docs/superpowers/BUG-01-sizing-studies-ran-the-wrong-strategy.md.
"""
from __future__ import annotations

# The engine's real parameter names, in the order fast_backtest() takes them.
_REQUIRED = ("sl_soft", "sl_hard", "tp")


def champion_stops(p: dict, tf: str = "?") -> tuple[float, float, float, bool]:
    """(sl_soft, sl_hard, tp, flip) from a champion preset — STRICTLY.

    Raises KeyError if any stop parameter is absent. Do NOT add a default: that is precisely the bug
    this module exists to prevent.

    `flip` is the one genuinely optional field — its absence means "do not flip", which is a real
    semantic default rather than a stand-in for a missing measurement.
    """
    missing = [k for k in _REQUIRED if k not in p]
    if missing:
        raise KeyError(
            f"champion preset for tf={tf!r} is missing {missing}. "
            f"Refusing to substitute defaults — that silently backtests a different strategy "
            f"(see docs/superpowers/BUG-01-sizing-studies-ran-the-wrong-strategy.md). "
            f"Keys present: {sorted(p)}"
        )
    return float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]), bool(p.get("flip", False))


def describe(p: dict, tf: str) -> str:
    """One-line banner so every run PRINTS the stops it actually used — no more invisible defaults."""
    ss, sh, tp, flip = champion_stops(p, tf)
    return (f"  [champion {tf:>3}] sl_soft={ss:.2f}  sl_hard={sh:.2f}  tp={tp:.2f}  "
            f"flip={flip}  gate_pct={p.get('gate_pct')}")
