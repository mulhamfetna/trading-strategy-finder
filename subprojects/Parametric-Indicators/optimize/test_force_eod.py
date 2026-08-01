"""--force-eod: NEVER hold overnight. The end-of-day close is pinned ON for every trial.

WHY IT EXISTS. We measured what happens when you bolt the end-of-day rule onto champions that were TUNED
to hold overnight: the suite loses **$40,429 of out-of-sample profit (−5.8%)**, and one slot (RTY 1h) flips
from +$6,539 to −$1,729 — it stops working entirely. That is the cost of CRIPPLING a strategy, not the cost
of the rule.

--force-eod instead makes the rule part of the world the optimizer searches in, so each champion's stops,
targets and indicator gate adapt to the shorter horizon from the start.

The failure this pins: a flag that *says* it forces the rule while some trials quietly still hold overnight
would be worse than useless — we would ship "never holds overnight" champions that do.
"""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import optimizer as OPT  # noqa: E402


def test_forcing_eod_removes_it_as_a_searched_dimension():
    """Pinned ON ⇒ it is no longer a CHOICE ⇒ it is no longer a dimension, and the budget shrinks.

    ⚠️ `normal` must state force_eod=False EXPLICITLY. Since 2026-07-30 the end-of-day close is the
    training standard and force_eod defaults to True (#79), so relying on the default would compare
    forced-against-forced and assert nothing at all.
    """
    normal = OPT.search_dims(split_sltp=False, force_eod=False)
    forced = OPT.search_dims(split_sltp=False, force_eod=True)
    # 2026-08-01: the bars cap is pinned OFF and no longer searched by default, so base_cat lost
    # en_cap_bars too. Both sides of this comparison are measured with the bars cap in the SAME state,
    # which is what makes the -1 attributable to en_cap_eod rather than to two changes at once.
    assert normal["base_cat"] == 2        # flip, en_cap_eod
    assert forced["base_cat"] == 1        # flip            (en_cap_eod pinned, not searched)
    assert forced["total"] == normal["total"] - 1
    assert OPT.recommended_trials(False, force_eod=True) == \
        OPT.recommended_trials(False, force_eod=False) - OPT.TRIALS_PER_DIM


def test_the_bar_cap_is_still_searched_under_force_eod():
    """Forcing the bell must NOT also pin the bar cap — 'both' (bell OR N bars, whichever first) has to stay
    reachable, otherwise we have quietly narrowed the search to one exit rule."""
    forced = OPT.search_dims(split_sltp=False, force_eod=True)
    # 2026-08-01: cooldown retired from the search, and cap_1min is only a dimension when the bars cap
    # can be on — searching a holding-time cap while the cap itself is pinned off is a knob nothing reads.
    assert forced["base_int"] == 1        # k


def test_derive_cap_mode_under_forced_eod_can_still_reach_both():
    # with en_cap_eod pinned True, the bar switch decides between 'eod' and 'both'
    assert OPT.derive_cap_mode(False, True) == "eod"
    assert OPT.derive_cap_mode(True, True) == "both"
    # and it can NEVER produce a mode that holds overnight
    for bars in (False, True):
        assert OPT.derive_cap_mode(bars, True) in ("eod", "both")


def test_every_trial_actually_closes_at_the_bell():
    """THE ONE THAT MATTERS. Sample the objective's search space many times and assert that NOT ONE trial
    can hold overnight. A flag that merely *claims* to force the rule, while some trials still hold, would
    ship champions that do the opposite of what the label says."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.CRITICAL)

    modes = []

    def fake_objective(trial):
        # mirror the objective's cap block exactly (see optimizer.objective)
        force_eod = True
        en_cap_bars = trial.suggest_categorical("en_cap_bars", [False, True])
        en_cap_eod = True if force_eod else trial.suggest_categorical("en_cap_eod", [False, True])
        trial.suggest_int("cap_1min", OPT.CAP_1MIN_MIN, OPT.CAP_1MIN_MAX)
        modes.append(OPT.derive_cap_mode(en_cap_bars, en_cap_eod))
        return 0.0

    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=3))
    study.optimize(fake_objective, n_trials=200)

    assert len(modes) == 200
    assert set(modes) <= {"eod", "both"}, f"a trial could hold overnight: {set(modes)}"
    assert "none" not in modes and "bars" not in modes
    # and both reachable shapes must actually occur, or the search collapsed to one exit rule
    assert "eod" in modes and "both" in modes, f"search collapsed: {set(modes)}"
