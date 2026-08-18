"""The control centre must budget for the search it is ACTUALLY launching.

THE BUG THIS LOCKS OUT. `plan()` and `preview_command()` computed the search size from the WHOLE
registry, while the very same cfg passed `--only-indicators` through to the launched command. Selecting
the original 18 indicators displayed **"471 dims / 47,100 trials"** and launched `--trials 47100` for a
search that could only ever touch **59 dimensions / 5,900 trials** — an 8x over-budget, i.e. roughly
20 hours per study instead of 45 minutes.

This is the same defect that was fixed in the CLI's `--auto-trials` path (#2) — and it survived there,
because the fix went in at `optimizer.main()` while the control plane builds its own budget. The control
plane is the path a HUMAN uses, so this was the copy that mattered.

The wider point this protects: the optimizer's default is to search the WHOLE registry, and narrowing it
is the operator's choice. That choice is only real if the cost estimate and the launched command both
follow it.
"""
import pytest

from indicators import library
from optimize import optimizer as OPT
from optimize.dashboard import control

ORIGINAL_18 = list(library.REGISTRY)[:18]


def _budget_of(cfg: dict, tf: str = "4h") -> int:
    """The trial budget this cfg actually results in.

    ⚠️ This used to parse `--trials N` out of the preview string. That encoded an IMPLEMENTATION DETAIL,
    not the contract: after #91 the command emits `--auto-trials` and the optimizer computes the budget
    itself — one place instead of two, which is strictly better and is what makes preview and execution
    identical. The intent being asserted was always "the budget follows the indicator scope", so ask the
    spec that question directly instead of scraping a string.
    """
    from optimize.dashboard import runner
    return runner.spec_for(cfg, tf).effective_trials()


def test_default_searches_the_whole_registry():
    """The DEFAULT must remain 'search everything' — narrowing is opt-in, never implicit."""
    p = control.plan({"timeframes": ["4h"]})
    assert p["indicators_searched"] == len(library.REGISTRY)
    assert p["dims"] == OPT.search_dims(False)["total"]
    assert p["recommended_trials"] == OPT.recommended_trials(False)


def test_only_indicators_shrinks_the_plan():
    p = control.plan({"timeframes": ["4h"], "only_indicators": ORIGINAL_18})
    assert p["indicators_searched"] == 18
    assert p["dims"] == OPT.search_dims(False, only_inds=tuple(ORIGINAL_18))["total"]
    assert p["recommended_trials"] == OPT.recommended_trials(False, only_inds=tuple(ORIGINAL_18))
    assert p["recommended_trials"] < OPT.recommended_trials(False), "scoping did not reduce the budget"


def test_exclude_indicators_shrinks_the_plan():
    p = control.plan({"timeframes": ["4h"], "exclude_indicators": ORIGINAL_18[:5]})
    assert p["indicators_searched"] == len(library.REGISTRY) - 5


def test_launched_command_carries_the_scoped_budget():
    """THE REGRESSION: a scoped search must not be charged the full-registry budget."""
    cfg = {"timeframes": ["4h"], "only_indicators": ORIGINAL_18}
    p = control.plan(cfg)
    launched = _budget_of(cfg)
    assert launched == p["recommended_trials"]
    assert launched == OPT.recommended_trials(False, only_inds=tuple(ORIGINAL_18))
    assert launched < OPT.recommended_trials(False), (
        f"run resolves to {launched} trials for an 18-indicator search — the full-registry budget")


def test_plan_and_command_never_disagree():
    """Whatever the scope, the number SHOWN and the number the run resolves to must be the same."""
    for cfg in ({"timeframes": ["4h"]},
                {"timeframes": ["4h"], "only_indicators": ORIGINAL_18},
                {"timeframes": ["4h"], "exclude_indicators": ORIGINAL_18[:3]},
                {"timeframes": ["4h"], "only_indicators": ORIGINAL_18[:4], "split_sltp": True}):
        p = control.plan(cfg)
        assert _budget_of(cfg) == p["recommended_trials"], f"mismatch for cfg={cfg}"


def test_explicit_trial_count_still_wins():
    """An operator who types a number gets that number — scoping must not override an explicit choice."""
    cfg = {"timeframes": ["4h"], "only_indicators": ORIGINAL_18, "trials_mode": "one", "trials": 250}
    assert _budget_of(cfg) == 250
    assert "--trials 250" in control.plan(cfg)["command"]


@pytest.mark.parametrize("cfg_key", ["only_indicators", "exclude_indicators"])
def test_scope_is_reported_so_the_operator_can_see_it(cfg_key):
    """The UI must be able to show WHAT it is charging for, not leave it to be inferred."""
    p = control.plan({"timeframes": ["4h"], cfg_key: ORIGINAL_18})
    assert "indicators_searched" in p and "indicators_total" in p
    assert p["indicators_total"] == len(library.REGISTRY)
    assert 0 < p["indicators_searched"] <= p["indicators_total"]
