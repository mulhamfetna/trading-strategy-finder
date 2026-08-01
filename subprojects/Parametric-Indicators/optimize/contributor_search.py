"""Shared cross-instrument contributor SEARCH-SPACE block — used by both the L2 optimizer
(optimize/l2/optimize.py) and the L1 optimizer (optimize/optimizer.py). One source of truth for the
namespaced ES committee + signal voter + topology dims, so the two optimizers can't drift."""
from __future__ import annotations

from optimize import optimizer as OPT

# ─────────────────────────────────────────────────────────────────────────────────────────────────
# COMMITTEE SCOPE (#95, decided 2026-08-01: option A — the exclusion is REMOVED).
#
# WHAT WAS EXCLUDED AND WHY. Six SMC structural indicators (+ `stochastic`/`adx` for L1) were withheld
# from the cross-instrument committee SEARCH because they "do not vectorise over the long contributor
# 1-minute frame": on the 486,954-bar ES frame `ifvg`=58.1s and `breaker`=37.9s alone were 90% of a
# 106.4s trial (PERFORMANCE.md §9).
#
# WHY IT IS GONE. #62 rewrote the SMC family as Numba state machines, and #95 re-measured on the REAL
# ES committee frame through the production call path (`bench_smc_committee.py`):
#
#     committee as searched before (157 indicators)   18.94 s
#     the 8 excluded indicators                        0.83 s   ->  admitting them is +4.4% per trial
#     the original justification                         90%
#
#     worst grid corner, all eight, measured full-frame: 0.94 s
#
# THE CONTROL FOUND MORE THAN A SPEED-UP. Re-measured with the accelerator forced off, FOUR of the six
# were never expensive at all — `structure_trend`, `fvg`, `cisd` (and `stochastic`, `adx`) cost the same
# with Numba off as on, because there was nothing to accelerate. They were excluded by FAMILY
# MEMBERSHIP, not by measurement: swept up for sitting in the same source file as `ifvg`/`breaker`.
# Only those two were ever slow, and they are now 0.224 s and 0.198 s (100x / 110x).
#
# WHAT THIS DOES AND DOES NOT CLAIM. It removes a restriction whose stated reason no longer exists. It
# does NOT claim these indicators help — that is a separate question, and a search that cannot reach an
# indicator can never learn that it is useless either. The scope stays CONTROLLABLE (--contrib-exclude,
# and the RunSpec field behind the dashboard) so the restriction can be reimposed deliberately.
# ─────────────────────────────────────────────────────────────────────────────────────────────────

# Nothing is withheld by default any more. Kept as a NAME rather than inlined so a run can reimpose the
# historical scope explicitly and so `test_committee_cost_budget.py` has something to price.
DEFAULT_COMMITTEE_EXCLUDE: tuple[str, ...] = ()

# The historical sets, retained for reproducing pre-2026-08-01 runs and for the cost gate. NOT applied
# by default — referencing them is now an explicit choice.
SMC_COMMITTEE_KEYS = ("structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd")
L1_ES_EXCLUDE = SMC_COMMITTEE_KEYS + ("stochastic", "adx")


def suggest_contributor(trial, token: str, exclude_committee=DEFAULT_COMMITTEE_EXCLUDE,
                        only_committee=()) -> dict:
    """Searchable cross-instrument contributor cfg (B1 gate schema): master enable, state definition,
    composite signal voter (BOTH encodings searched), the namespaced indicator committee, k_es.
    The 6-cell truth table is keyed by JSON-safe 'dir|state' strings (the objective serialises params).
    `exclude_committee` keys are forced OFF (not searched). Defaults to NOTHING excluded (#95);
    pass L1_ES_EXCLUDE to reproduce a pre-2026-08-01 run.
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
