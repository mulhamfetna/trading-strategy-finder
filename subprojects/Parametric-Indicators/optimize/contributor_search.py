"""Shared cross-instrument contributor SEARCH-SPACE block — used by both the L2 optimizer
(optimize/l2/optimize.py) and the L1 optimizer (optimize/optimizer.py). One source of truth for the
namespaced ES committee + signal voter + topology dims, so the two optimizers can't drift."""
from __future__ import annotations

import os

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

# Fixed dimensions ONE contributor token adds, outside its indicator committee:
#   enabled, state_def, sig_enc, sig_mode, k_es          = 5
#   tt_{long,short}_{long,short,hold} truth-table cells   = 6
# Named here rather than counted at the call site so the SEARCH and the BUDGET read the same number
# from the same place — the whole class of defect in #2/#89 was a budget computed from something other
# than the search it was sizing.
FIXED_DIMS_PER_TOKEN = 11


def contributor_dims(tokens, exclude_committee=(), only_committee=()) -> int:
    """Search dimensions added by the cross-instrument contributor block.

    THE DEFECT THIS CLOSES (#95, 2026-08-01). `search_dims()` had NO contributor term at all, so
    `--contributors ES --plan` reported the same 470 dimensions with and without the block. The
    committee is a SECOND full-registry search — it roughly DOUBLES the space — and `--auto-trials`
    was sizing runs for half of it.

    Found while trying to size the two arms of the #95 with/without comparison: both arms printed
    identical dimensions, which is impossible, because the arms differ by exactly eight committee keys.
    A comparison budgeted from a plan that cannot see the difference between its arms is not a
    comparison.
    """
    toks = tuple(tokens or ())
    if not toks:
        return 0
    keys = OPT.searchable_indicators(tuple(only_committee), tuple(exclude_committee))
    per_token = FIXED_DIMS_PER_TOKEN + len(keys) + sum(
        len(OPT.library.SCHEMA[k].get("params", [])) for k in keys)
    return per_token * len(toks)


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# FUSION OPT-IN GATE (user decision, 2026-08-01).
#
# The cross-instrument contributor block is NOT a native indicator. It came out of the fusion studies —
# the round where several separate ideas were tried as ways to combine instruments — and ES-as-an-input-
# to-NQ was one of them. It is a research feature, and it must not leak into ordinary optimizer work.
#
# WHY A GATE AND NOT JUST A DEFAULT. It is already off by default (`--contributors` is empty), but "off
# unless you type a flag" is not the same as "cannot be switched on by accident". Typing
# `--contributors ES` is one word, and the consequence is invisible until much later:
#
#   * it adds 471 search dimensions for ONE token — the strategy's own search is 470, so a single
#     contributor DOUBLES the problem
#   * at the ∝-dimension budget that is 94,100 trials x 8.4 s ≈ 9.1 DAYS for one run (#96)
#   * and it silently changes what a "champion" means: the resulting strategy needs a second
#     instrument's live data to reproduce its own decisions
#
# So enabling it now takes TWO deliberate acts: naming the tokens AND acknowledging the fusion opt-in.
# Usable, never accidental.
# ─────────────────────────────────────────────────────────────────────────────────────────────────

FUSION_ACK_FLAG = "--enable-fusion-contributors"
FUSION_ACK_ENV = "WSH_ENABLE_FUSION_CONTRIBUTORS"


class FusionNotEnabled(RuntimeError):
    """Contributor tokens were requested without the fusion opt-in."""


def require_fusion_optin(tokens, ack: bool = False) -> None:
    """Raise unless the caller has deliberately opted into the fusion contributor block.

    No-op when no tokens are requested, so every ordinary run is untouched.
    """
    toks = tuple(t for t in (tokens or ()) if t)
    if not toks:
        return
    if ack or os.environ.get(FUSION_ACK_ENV) == "1":
        return
    raise FusionNotEnabled(
        f"cross-instrument contributors {list(toks)} were requested, but the fusion opt-in was not "
        f"given.\n"
        f"    This is a FUSION-STUDY feature, not a native indicator: it feeds another instrument's\n"
        f"    bars into this strategy's decisions.\n"
        f"    Cost, so the choice is informed:\n"
        f"      · +{contributor_dims(toks)} search dimensions ({len(toks)} token(s)) on top of the\n"
        f"        strategy's own {OPT.search_dims(False)['total']} — one token roughly DOUBLES the search\n"
        f"      · ~9 days per run at the dimension-proportional budget (#96)\n"
        f"      · the resulting champion needs the other instrument's data to reproduce its decisions\n"
        f"    Add {FUSION_ACK_FLAG} (or {FUSION_ACK_ENV}=1) if that is genuinely what you want.")
