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
while a re-run on today's tree searched 165 (471 dims, 47,100 trials) — same command line, same flags,
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


def test_scoped_budget_reproduces_the_july_campaign_exactly():
    """The July `wshgap` run printed 'TOTAL 59 dims' / 'RECOMMENDED 5,900 trials' on a tree whose registry
    held only these 18. Reproducing those numbers is what proves the accounting is right rather than
    merely smaller.

    ⚠️ July's configuration must be pinned EXPLICITLY, not inherited from today's defaults. It searched
    the end-of-day close as a dimension; since 2026-07-30 that is pinned ON for all training (#79), which
    legitimately removes one dimension (59 → 58). A historical-reproduction test that silently tracks the
    current default stops reproducing history the moment a default changes — which is exactly what it is
    supposed to notice.
    """
    july = dict(only_inds=ORIGINAL_18, force_eod=False)      # as it actually ran
    assert O.search_dims(False, **july)["total"] == 59
    assert O.recommended_trials(False, **july) == 5_900


def test_todays_default_is_one_dimension_smaller_than_july():
    """The deliberate difference, asserted rather than left implicit: the end-of-day close is now pinned,
    so it is no longer searched."""
    july = O.search_dims(False, only_inds=ORIGINAL_18, force_eod=False)["total"]
    today = O.search_dims(False, only_inds=ORIGINAL_18)["total"]
    assert today == july - 1 == 58


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
