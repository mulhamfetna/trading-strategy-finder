"""Drawing an indicator's parameters only when it is enabled must not change the STRATEGY (#97).

WHY THIS NEEDS PROVING RATHER THAN ASSERTING. The rectangular search space draws every indicator's
parameters on every trial, enabled or not — deliberately, so NSGA-III sees a fixed dimension set and
crossover between any two genomes is well defined. #97 measured what that costs: a champion runs ~7
indicators and a mid-search trial ~56, out of 165, so roughly **two-thirds of the 295 parameter draws
are read by nothing**.

Conditional drawing gives disabled indicators their schema defaults instead. The claim is that this is
invisible to the engine, because a disabled indicator's parameters are never read. That is exactly the
kind of "obviously fine" claim that has been wrong before in this repo — the intra-candle flag, the
cross-series reference, the `--max-enabled` repair — so it is tested against the real spec builder
rather than argued.

WHAT IS DELIBERATELY NOT CLAIMED HERE: that NSGA-III's crossover is unaffected. Two parents can now
carry different parameter sets. Optuna supports that; whether the genetic operators degrade is an open
question these tests do not answer, and it is why the flag is OFF by default.
"""
import optuna

from indicators import library
from optimize import optimizer as OPT

optuna.logging.set_verbosity(optuna.logging.WARNING)

ORIGINAL_18 = tuple(list(library.REGISTRY)[:18])


def _specs(trial, conditional):
    return OPT._suggest_indicators(trial, only=ORIGINAL_18, conditional_params=conditional)


def _fixed(enabled_keys, conditional):
    """A FixedTrial that pins the enable flags, so both modes see the same enabled set — otherwise the
    comparison would be measuring two different genomes."""
    fixed = {}
    for k in ORIGINAL_18:
        fixed[f"en_{k}"] = k in enabled_keys
        for p in library.SCHEMA[k].get("params", []):
            fixed[f"{k}_{p['name']}"] = p["default"]
    return OPT._suggest_indicators(optuna.trial.FixedTrial(fixed), only=ORIGINAL_18,
                                   conditional_params=conditional)


def test_the_enabled_set_is_identical():
    on = set(ORIGINAL_18[:5])
    a = {s["key"]: s["enabled"] for s in _fixed(on, False)}
    b = {s["key"]: s["enabled"] for s in _fixed(on, True)}
    assert a == b


def test_enabled_indicators_keep_their_searched_parameters():
    """The half that must NOT change: an enabled indicator is still fully parameterised."""
    on = set(ORIGINAL_18[:5])
    a = {s["key"]: s["params"] for s in _fixed(on, False) if s["enabled"]}
    b = {s["key"]: s["params"] for s in _fixed(on, True) if s["enabled"]}
    assert a == b and a, "enabled indicators lost their parameters"


def test_disabled_indicators_carry_schema_defaults():
    on = set(ORIGINAL_18[:5])
    for s in _fixed(on, True):
        if s["enabled"]:
            continue
        assert s["params"] == {p["name"]: p["default"] for p in library.SCHEMA[s["key"]].get("params", [])}


def test_the_strategy_the_engine_receives_is_byte_identical():
    """THE CLAIM. `library.from_specs` is what turns specs into the objects the engine votes with. Build
    it both ways and compare what the engine would actually see: the enabled indicators and their
    parameters. Disabled ones contribute nothing, so they must not appear in the difference."""
    on = set(ORIGINAL_18[:6])
    rect = [s for s in _fixed(on, False) if s["enabled"]]
    cond = [s for s in _fixed(on, True) if s["enabled"]]
    assert [(s["key"], s["mode"], s["params"]) for s in rect] == \
           [(s["key"], s["mode"], s["params"]) for s in cond]
    assert [i.key for i in library.from_specs(rect)] == [i.key for i in library.from_specs(cond)]


def test_a_real_trial_draws_far_fewer_parameters():
    """The point of the change, measured on an actual Optuna trial rather than reasoned about."""
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=7))
    t_rect = study.ask(); _specs(t_rect, False)
    t_cond = study.ask(); _specs(t_cond, True)
    n_rect, n_cond = len(t_rect.params), len(t_cond.params)
    assert n_cond < n_rect, f"conditional drew {n_cond}, rectangular {n_rect}"
    # Both draw all 18 flags; only the parameter draws differ, and ~half the indicators are off.
    assert n_cond >= 18, "the enable flags must still be drawn — they are the search"


def test_it_is_off_by_default_because_crossover_is_unmeasured():
    """A default is a claim. This one is not supported yet: two parents can now carry different
    parameter sets, and whether NSGA-III's operators degrade has not been measured."""
    import inspect
    assert inspect.signature(OPT._suggest_indicators).parameters["conditional_params"].default is False
    assert inspect.signature(OPT.run).parameters["conditional_params"].default is False


# --- the measured verdict (#99, 2026-08-02) ------------------------------------------------------

MEASURED_99 = {
    # Two matched 46,600-trial NQ 4h studies, same seed, --conditional-params the only difference.
    "rect_completed": 28450, "cond_completed": 8487,
    "rect_median_pnl": 8192, "cond_median_pnl": -1218,
    "rect_p90": 10189, "cond_p90": 1128,
    "rect_feasible_front": 756, "cond_feasible_front": 9,
    "rect_wall_s": 14146, "cond_wall_s": 10480,
}


def test_the_measurement_says_do_not_adopt():
    """The pre-registered criterion was: adopt only if search quality shows no material degradation
    AND selection behaviour is unchanged. BOTH failed, and not marginally.

    Kept as assertions so that if anyone later proposes flipping the default, this is the evidence they
    have to argue with — the same discipline applied to the SMC exclusion in #95, where a stale comment
    justified a live restriction for months because nothing pinned the number.
    """
    m = MEASURED_99
    assert m["cond_median_pnl"] < 0 < m["rect_median_pnl"], (
        "the conditional arm's MEDIAN completed trial lost money while the rectangular arm's made it")
    assert m["cond_completed"] < m["rect_completed"] / 3, "3.4x fewer trials scored at all"
    assert m["cond_p90"] < m["rect_p90"] / 5, "even the upper decile is ~9x worse"
    assert m["cond_feasible_front"] < 20 < m["rect_feasible_front"]
    # and it WAS faster — which is exactly why speed alone was never allowed to carry the decision
    assert m["cond_wall_s"] < m["rect_wall_s"]


def test_the_flag_is_still_reachable_for_research():
    """Refuted as a default, kept as a capability. Someone re-testing this — on another timeframe, or
    after a change to how parameters are seeded — must not have to re-implement it first."""
    import inspect
    assert "conditional_params" in inspect.signature(OPT.run).parameters
    assert "--conditional-params" in inspect.getsource(OPT.main)
