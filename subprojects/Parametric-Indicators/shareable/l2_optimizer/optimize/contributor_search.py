"""Shared cross-instrument contributor SEARCH-SPACE block — used by both the L2 optimizer
(optimize/l2/optimize.py) and the L1 optimizer (optimize/optimizer.py). One source of truth for the
namespaced ES committee + signal voter + topology dims, so the two optimizers can't drift."""
from __future__ import annotations

from optimize import optimizer as OPT

# SMC structural indicators — EXCLUDED from the cross-instrument committee SEARCH by default because they do
# not vectorise over the long contributor 1-minute frame: on the 486,954-bar ES frame `ifvg`=58.1s and
# `breaker`=37.9s ALONE are 90% of a 106.4s 18-indicator committee trial (PERFORMANCE.md §9). Dropping the
# SMC family keeps each contributor-search trial ~10× faster. Still available in the dashboard backtester.
SMC_COMMITTEE_KEYS = ("structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd")

# The L1 optimizer scores K walk-forward folds + a full backtest per trial, so the ES committee compute is
# multiplied — also drop the two heaviest non-SMC indicators (stochastic≈2.2s, adx≈2.2s on the 487k-bar ES
# frame). L2 (single-window) keeps the SMC-only default.
L1_ES_EXCLUDE = SMC_COMMITTEE_KEYS + ("stochastic", "adx")


def suggest_contributor(trial, token: str, exclude_committee=SMC_COMMITTEE_KEYS) -> dict:
    """Searchable cross-instrument contributor cfg (B1 gate schema): master enable, state definition,
    composite signal voter (BOTH encodings searched), the namespaced indicator committee, k_es.
    The 6-cell truth table is keyed by JSON-safe 'dir|state' strings (the objective serialises params).
    `exclude_committee` keys are forced OFF (not searched) — defaults to the slow SMC family."""
    pre = f"{token.lower()}_"
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial, prefix=pre, exclude=exclude_committee)]
    enc = trial.suggest_categorical(f"{pre}sig_enc", ["none", "stance", "truthtable"])
    mode = trial.suggest_categorical(f"{pre}sig_mode", ["confirm", "veto", "both"])
    table = {f"{d}|{s}": trial.suggest_categorical(f"{pre}tt_{d}_{s}", ["confirm", "veto", "ignore"])
             for d in ("long", "short") for s in ("long", "short", "hold")}
    return {"token": token, "enabled": bool(trial.suggest_categorical(f"{pre}enabled", [False, True])),
            "tf": "4h", "state_def": trial.suggest_categorical(f"{pre}state", ["touch", "traversal"]),
            "k_es": int(trial.suggest_int(f"{pre}k_es", 1, 5)),
            "signal": {"encoding": enc, "mode": mode, "table": table},
            "committee": specs}
