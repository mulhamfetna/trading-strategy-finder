"""Shared cross-instrument contributor SEARCH-SPACE block — used by both the L2 optimizer
(optimize/l2/optimize.py) and the L1 optimizer (optimize/optimizer.py). One source of truth for the
namespaced ES committee + signal voter + topology dims, so the two optimizers can't drift."""
from __future__ import annotations

from optimize import optimizer as OPT

# SMC structural indicators — EXCLUDED from the cross-instrument committee SEARCH by default.
#
# ⚠️ THE COST THAT JUSTIFIED THIS EXCLUSION NO LONGER EXISTS (#89 sweep, 2026-07-31). The original
# rationale was that these "do not vectorise over the long contributor 1-minute frame": on the
# 486,954-bar ES frame `ifvg`=58.1s and `breaker`=37.9s ALONE were 90% of a 106.4s 18-indicator
# committee trial (PERFORMANCE.md §9). Then #62 rewrote the SMC family as Numba state machines and
# re-measured on the full frame: `ifvg` **29.90s → 0.314s (95×)** and `order_block` **2.82s → 0.118s
# (24×)** (docs/CLOSEOUT-2026-07-28-indicator-budget.md). The 90%-of-a-trial claim is a PRE-
# ACCELERATION number describing code that has since been replaced.
#
# This is therefore a live restriction of the SEARCH SPACE resting on a stale measurement — six
# structural indicators are never offered to the cross-instrument committee, for a speed reason that
# has been engineered away. It is left ON deliberately rather than flipped here: changing a default
# changes what every contributor search explores, and that is a measured decision, not a cleanup.
# Re-measure on the ES frame, then decide — tracked as its own issue. Still available in the
# dashboard backtester either way.
SMC_COMMITTEE_KEYS = ("structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd")

# The L1 optimizer scores K walk-forward folds + a full backtest per trial, so the ES committee compute is
# multiplied — also drop the two heaviest non-SMC indicators (stochastic≈2.2s, adx≈2.2s on the 487k-bar ES
# frame). L2 (single-window) keeps the SMC-only default.
# ⚠️ Same caveat: those 2.2s figures are pre-#62 as well, and inherit whatever SMC_COMMITTEE_KEYS becomes.
L1_ES_EXCLUDE = SMC_COMMITTEE_KEYS + ("stochastic", "adx")


def suggest_contributor(trial, token: str, exclude_committee=SMC_COMMITTEE_KEYS,
                        only_committee=()) -> dict:
    """Searchable cross-instrument contributor cfg (B1 gate schema): master enable, state definition,
    composite signal voter (BOTH encodings searched), the namespaced indicator committee, k_es.
    The 6-cell truth table is keyed by JSON-safe 'dir|state' strings (the objective serialises params).
    `exclude_committee` keys are forced OFF (not searched) — defaults to the slow SMC family.
    `only_committee` restricts the committee to those keys (empty ⇒ the whole registry, unchanged) —
    the same scoping the L1 optimizer's --only-indicators provides, needed because this committee is a
    SECOND full-registry search on top of the strategy's own (#80/#81)."""
    pre = f"{token.lower()}_"
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial, prefix=pre, exclude=exclude_committee,
                                              only=tuple(only_committee))]
    enc = trial.suggest_categorical(f"{pre}sig_enc", ["none", "stance", "truthtable"])
    mode = trial.suggest_categorical(f"{pre}sig_mode", ["confirm", "veto", "both"])
    table = {f"{d}|{s}": trial.suggest_categorical(f"{pre}tt_{d}_{s}", ["confirm", "veto", "ignore"])
             for d in ("long", "short") for s in ("long", "short", "hold")}
    return {"token": token, "enabled": bool(trial.suggest_categorical(f"{pre}enabled", [False, True])),
            "tf": "4h", "state_def": trial.suggest_categorical(f"{pre}state", ["touch", "traversal"]),
            "k_es": int(trial.suggest_int(f"{pre}k_es", 1, 5)),
            "signal": {"encoding": enc, "mode": mode, "table": table},
            "committee": specs}
