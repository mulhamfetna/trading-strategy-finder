"""The dimension-proportional trial budget must reflect the indicators actually being SEARCHED.

THE BUG THIS LOCKS OUT (issue #2, 2026-07-29). `--auto-trials` sizes the run as
`total_search_dimensions x TRIALS_PER_DIM`, but `search_dims()` counted the whole REGISTRY regardless of
`--only-indicators` / `--exclude-indicators`. Restricting a re-optimization to the original 18 indicators
therefore still budgeted **47,100 trials for a 59-dimension search** — an 8x over-budget.

Nothing failed. The run was simply going to take ~20 hours per study instead of ~45 minutes (~10 days for
a twelve-study campaign instead of ~9 hours), and the only symptom was a plan line quietly reporting 165
indicators for a search that could only ever touch 18. That is the expensive kind of bug: no error, no
wrong answer, just an enormous silent waste that looks exactly like normal operation.

It also made two campaigns non-comparable without anyone noticing: the July `wshgap` run searched 18
indicators (59 dims, 5,900 trials, 44 min/study) because its worktree predated the 143-indicator library,
while a re-run on today's tree searched 165 (466 dims, 46,600 trials) — same command line, same flags,
8x the budget over a differently-shaped space.
"""
import pytest

from indicators import library
from optimize import optimizer as O

# The original library — registry positions 0-17. Every indicator in every deployed champion is in here,
# and the adopt gate (#14) left the 147 newer ones DEFAULT-OFF.
ORIGINAL_18 = tuple(list(library.REGISTRY)[:18])


def test_only_indicators_shrinks_the_searchable_set():
    got = O.searchable_indicators(ORIGINAL_18)
    assert len(got) == 18
    assert set(got) == set(ORIGINAL_18)
    assert len(O.searchable_indicators()) == len(library.REGISTRY)


def test_exclude_indicators_shrinks_the_searchable_set():
    got = O.searchable_indicators(exclude_inds=ORIGINAL_18[:5])
    assert len(got) == len(library.REGISTRY) - 5


def test_only_and_exclude_compose():
    got = O.searchable_indicators(ORIGINAL_18, exclude_inds=ORIGINAL_18[:3])
    assert len(got) == 15


def test_unknown_key_in_only_is_ignored_not_counted():
    """A typo must not inflate the budget with a dimension that does not exist."""
    got = O.searchable_indicators(ORIGINAL_18 + ("not_a_real_indicator",))
    assert len(got) == 18


def test_budget_follows_the_restricted_scope():
    """THE REGRESSION. Restricting to 18 indicators must shrink dims AND the trial budget."""
    full = O.search_dims(False)["total"]
    scoped = O.search_dims(False, only_inds=ORIGINAL_18)["total"]
    assert scoped < full, "restricting the indicator scope did not shrink the search space"
    assert O.recommended_trials(False, only_inds=ORIGINAL_18) == scoped * O.TRIALS_PER_DIM
    assert O.recommended_trials(False) == full * O.TRIALS_PER_DIM


def test_the_july_campaign_shape_is_recorded_even_though_it_can_no_longer_be_REPRODUCED():
    """The July `wshgap` run printed 'TOTAL 59 dims' / 'RECOMMENDED 5,900 trials' on a tree whose
    registry held only these 18. That shape is now UNREACHABLE, and saying so is the point of this test.

    59 = base(5 continuous + 3 categorical + 3 integer = 11) + 18 flags + 30 indicator params.

    Three of those base dimensions have since been retired, each deliberately and each for its own
    reason, so the code can no longer be asked to produce 59:

        en_cap_eod   pinned ON   2026-07-30  the end-of-day close is the training standard (#79)
        dd_limit     pinned 0    2026-08-01  user decision — retired from the search
        cooldown     pinned 0    2026-08-01  user decision — retired from the search
        en_cap_bars  pinned OFF  2026-08-01  user decision — restorable with search_cap_bars=True
        cap_1min     not drawn   2026-08-01  only a dimension when the bars cap can be on

    A historical-reproduction test that quietly tracks the current default stops reproducing history
    the moment a default moves — which is exactly what it exists to notice. So instead of asserting a
    number the code can no longer make, this asserts the DRIFT, with the arithmetic that explains it.
    """
    JULY_TOTAL = 59
    # The closest today's code can come: everything July searched that still EXISTS as a dimension.
    closest = O.search_dims(False, only_inds=ORIGINAL_18, force_eod=False, search_cap_bars=True)
    assert closest["total"] == 57, (
        f"expected 57 (July's 59 minus dd_limit and cooldown, both retired 2026-08-01); "
        f"got {closest['total']}. If this moved, a base dimension changed and the list above is stale.")
    assert JULY_TOTAL - closest["total"] == 2

    today = O.search_dims(False, only_inds=ORIGINAL_18)
    assert today["total"] == 54, (
        "today's default also pins en_cap_eod ON and the bars cap OFF, dropping en_cap_bars and cap_1min")
    assert O.recommended_trials(False, only_inds=ORIGINAL_18) == 5_400


def test_todays_default_is_five_dimensions_smaller_than_july():
    """The deliberate difference, asserted rather than left implicit — and attributed dimension by
    dimension, because 'the number changed' is not a finding, but 'these five knobs stopped being
    searched, for these five reasons' is."""
    today = O.search_dims(False, only_inds=ORIGINAL_18)["total"]
    assert 59 - today == 5           # en_cap_eod, dd_limit, cooldown, en_cap_bars, cap_1min


@pytest.mark.parametrize("freeze", [True, False])
def test_freeze_still_dominates(freeze):
    """--freeze-indicators removes the indicator layer entirely; scoping it further changes nothing."""
    a = O.search_dims(False, freeze_indicators=freeze, only_inds=ORIGINAL_18)["total"]
    b = O.search_dims(False, freeze_indicators=freeze)["total"]
    assert (a == b) is freeze


def test_indicator_dimensions_are_the_only_thing_scoping_changes():
    """Guard the accounting: base/categorical/integer/split dims must be untouched by indicator scope."""
    full = O.search_dims(True, only_inds=())
    scoped = O.search_dims(True, only_inds=ORIGINAL_18)
    for k in ("base_cont", "base_cat", "base_int", "split", "intracandle"):
        assert full[k] == scoped[k], f"{k} changed with indicator scope"
    assert scoped["en_flags"] == 18
