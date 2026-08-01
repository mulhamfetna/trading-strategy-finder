"""The committee scope must be a CHOICE, and its cost must be an assertion rather than a comment (#95).

WHY THIS FILE EXISTS. Eight indicators were withheld from every cross-instrument committee search for
months because of a sentence in a comment: `ifvg`=58.1s and `breaker`=37.9s were "90% of a trial". That
sentence was true when written. Then #62 rewrote the family in Numba and #95 measured the real thing on
the real ES frame:

    committee as searched before (157 indicators)   18.94 s
    the 8 excluded indicators                        0.83 s   ->  +4.4% per trial, not 90%
    worst grid corner, all eight, full-frame         0.94 s

    control (accelerator forced off):
      ifvg     22.506 s -> 0.224 s   100x
      breaker  14.702 s -> 0.198 s   110x
      structure_trend / fvg / cisd / stochastic / adx:  UNCHANGED — never expensive at all

Nothing failed when that comment went stale. The exclusion simply kept applying, silently, on a number
that had stopped being true — for four of the six, on a number that was never about them in the first
place. **A cost-based exclusion is a measurement with an expiry date** (playbook rule S4), so the cost
belongs in a test that fails when it moves, not in prose nobody re-reads.

This file does NOT re-time the indicators — that is `optimize/perf/bench_smc_committee.py`, which needs
the real ES frame and takes minutes. It pins the things that made the stale comment dangerous: that the
scope is empty by default, that it is reimposable, that it is controllable from every launcher, and
that the budget which justified the exclusion is written down where it can be checked.
"""
import inspect
import pathlib

import pytest

from indicators import library
from optimize import contributor_search as CS

# From bench_smc_committee.py, measured on the full 486,954-bar ES frame, 2026-07-31.
MEASURED = {
    "committee_157_s": 18.94,
    "excluded_8_default_s": 0.83,
    "excluded_8_worst_corner_s": 0.94,
    "ifvg_reference_s": 22.506, "ifvg_accelerated_s": 0.224,
    "breaker_reference_s": 14.702, "breaker_accelerated_s": 0.198,
}


def test_nothing_is_withheld_by_default():
    assert CS.DEFAULT_COMMITTEE_EXCLUDE == (), (
        "the committee exclusion is back. If that is deliberate it needs a MEASUREMENT, not a comment — "
        "see bench_smc_committee.py")


def test_the_historical_sets_survive_as_names_so_old_runs_reproduce():
    """Removing a default must not destroy the ability to reproduce what ran before it."""
    assert set(CS.SMC_COMMITTEE_KEYS) == {
        "structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd"}
    assert set(CS.L1_ES_EXCLUDE) == set(CS.SMC_COMMITTEE_KEYS) | {"stochastic", "adx"}


def test_every_excluded_key_is_a_real_indicator():
    """A typo in this list would silently withhold nothing, which is the failure mode that looks like
    success."""
    for k in CS.L1_ES_EXCLUDE:
        assert k in library.REGISTRY, f"{k} is not in the registry"


def test_admitting_them_is_a_few_percent_not_most_of_a_trial():
    """The arithmetic that decided this, kept where it can be re-read. If someone re-imposes the
    exclusion citing cost, this is the number they have to argue with."""
    share = MEASURED["excluded_8_default_s"] / MEASURED["committee_157_s"]
    assert share < 0.06, f"admitting the eight is {share:.1%} of a trial"
    assert MEASURED["excluded_8_worst_corner_s"] < 1.0, (
        "even at the worst corner of every parameter grid, all eight together are under a second")


def test_the_two_that_were_genuinely_slow_are_the_ones_that_got_accelerated():
    """The control's finding, pinned: only ifvg and breaker were ever expensive. Everything else in the
    family was guilty by association."""
    assert MEASURED["ifvg_reference_s"] / MEASURED["ifvg_accelerated_s"] > 50
    assert MEASURED["breaker_reference_s"] / MEASURED["breaker_accelerated_s"] > 50


@pytest.mark.parametrize("mod,flag", [
    ("optimize.optimizer", "--contrib-exclude"),
    ("optimize.l2.optimize", "--contrib-exclude"),
])
def test_the_scope_is_controllable_from_every_launcher(mod, flag):
    """A default that cannot be changed from the outside is indistinguishable from a hardcoded constant —
    and the standing rule here is that a decision layer must be controllable by the human running the
    backtest."""
    import importlib
    m = importlib.import_module(mod)
    src = inspect.getsource(m.main)
    assert flag in src, f"{mod} cannot express a committee scope"


def test_the_old_opt_in_flag_is_gone():
    """`--contrib-include-smc` was an opt-IN, which only makes sense while withholding is the default.
    Leaving it would let a run silently mean the opposite of what it says.

    Checked through the AST, not by searching the text — the first version of this test failed on the
    COMMENT that documents the flag's removal, which is the same false positive a regex gave in #89.
    A code-shape check must look at code shapes.
    """
    import ast
    src = (pathlib.Path(__file__).resolve().parent / "l2" / "optimize.py").read_text()
    tree = ast.parse(src)
    flags = [a.value for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", None) == "add_argument"
             for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    assert "--contrib-include-smc" not in flags, "the opt-IN flag is still declared"
    assert "--contrib-exclude" in flags, "and the opt-OUT that replaced it must be there"
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "contrib_include_smc" not in attrs, "the removed flag is still being read"


def test_suggest_contributor_defaults_to_the_full_registry():
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    t = optuna.create_study().ask()
    CS.suggest_contributor(t, "ES")
    for k in CS.L1_ES_EXCLUDE:
        assert f"es_en_{k}" in t.params, f"{k} is not searchable by default"
