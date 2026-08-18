"""What the UI SHOWS must be what the runner EXECUTES — byte for byte.

THE DEFECT THIS LOCKS OUT (#91). The optimizer invocation was constructed in six independent places.
`control.preview_command()` built the string the operator saw; `runner.build_command()` built a
DIFFERENT one that actually ran. `control.py` documented the arrangement in its own docstring —
*"mirrors remote_wsi.sh's IND_ARGS construction exactly"* — which is a request that humans keep three
implementations byte-identical, forever.

They did not. Measured across four configurations, the two diverged on **all four**:

    config              UI showed                actually ran
    plain               --trials 47100           --study-prefix cc03e2b7f5 --auto-trials
    scoped to 18        --trials 5900            --study-prefix cc3e57b4a7 --auto-trials
    split + max-enabled --trials 47700           --study-prefix ccbf7e1aef --auto-trials
    cold start          --trials 47100           --study-prefix cceafa9c36 --auto-trials

The operator was also assigned a `--study-prefix` the screen never mentioned, so they could not tell
which study their run would write to. And the trial NUMBERS agreed only because the budget was fixed in
`search_dims()` and in `preview_command()` separately, hours apart — an agreement that had to be
re-established after every change.

Both now call `run_spec.build_argv`, so this is not merely a test that they agree: there is nothing left
to keep in sync. This file exists to keep it that way.
"""
import pytest

from indicators import library
from optimize import run_spec as RS
from optimize.dashboard import control, runner

ORIGINAL_18 = list(library.REGISTRY)[:18]

CONFIGS = [
    ("plain",              {"timeframes": ["4h"]}),
    ("scoped to 18",       {"timeframes": ["4h"], "only_indicators": ORIGINAL_18}),
    ("excluded 5",         {"timeframes": ["4h"], "exclude_indicators": ORIGINAL_18[:5]}),
    ("split + max-enabled", {"timeframes": ["4h"], "split_sltp": True, "max_enabled": 5}),
    ("cold start",         {"timeframes": ["4h"], "cold_start": True}),
    ("explicit trials",    {"timeframes": ["4h"], "trials_mode": "one", "trials": 250}),
    ("non-NQ instrument",  {"timeframes": ["4h"], "instrument": "GC"}),
    ("sampler + dd cap",   {"timeframes": ["4h"], "sampler": "tpe", "dd_cap": 0.5}),
    ("reference",          {"timeframes": ["4h"], "reference": "ES"}),
    ("expanded queue cell", {"timeframes": ["4h"], "auto_trials": False, "trials": 900}),
]


def _args_only(argv: list[str]) -> list[str]:
    """Drop the interpreter and -u so we compare the ARGUMENTS, not how python was invoked."""
    i = argv.index("optimize/optimizer.py")
    return argv[i:]


@pytest.mark.parametrize("label,cfg", CONFIGS, ids=[c[0] for c in CONFIGS])
def test_preview_is_exactly_what_runs(label, cfg):
    """THE REGRESSION. Shown and executed must be identical argument-for-argument."""
    shown = control.preview_command(cfg).split()
    ran = runner.build_command(cfg, "4h")
    assert _args_only(shown) == _args_only(ran), (
        f"{label}: the UI shows a different command from the one that runs\n"
        f"  shown: {' '.join(_args_only(shown))}\n"
        f"  runs : {' '.join(_args_only(ran))}")


@pytest.mark.parametrize("label,cfg", CONFIGS, ids=[c[0] for c in CONFIGS])
def test_preview_shows_the_study_prefix(label, cfg):
    """An operator must be able to tell WHICH study their run will write to. The old preview omitted
    --study-prefix entirely, so the screen could not answer that question."""
    shown = control.preview_command(cfg)
    assert "--study-prefix" in shown, f"{label}: preview hides the study it will write to"
    assert runner.study_prefix(cfg) in shown


def test_budget_shown_matches_the_budget_the_spec_resolves_to():
    """`plan()` reports a trial number for the UI; it must be the number this spec actually produces."""
    for label, cfg in CONFIGS:
        spec = runner.spec_for(cfg, "4h")
        p = control.plan(cfg)
        if spec.trials is not None:                     # explicit count pinned by the operator
            assert spec.effective_trials() == spec.trials, label
        else:
            assert p["recommended_trials"] == spec.effective_trials(), (
                f"{label}: plan says {p['recommended_trials']} trials, spec resolves to "
                f"{spec.effective_trials()}")


def test_scoped_run_is_not_charged_the_full_registry_budget():
    """The 8x over-budget, restated as a property of the spec (#2)."""
    full = runner.spec_for({"timeframes": ["4h"]}, "4h")
    scoped = runner.spec_for({"timeframes": ["4h"], "only_indicators": ORIGINAL_18}, "4h")
    assert scoped.indicators_searched() == 18
    assert full.indicators_searched() == len(library.REGISTRY)
    assert scoped.effective_trials() < full.effective_trials()


def test_one_builder_is_actually_used_by_both():
    """Guards the STRUCTURE, not just the outcome: if either caller starts hand-building an argv again,
    the agreement above becomes a coincidence rather than a guarantee."""
    import inspect
    for fn in (control.preview_command, runner.build_command):
        src = inspect.getsource(fn)
        assert "build_argv" in src, (
            f"{fn.__qualname__} no longer delegates to run_spec.build_argv — the divergence class is back")


def test_spec_round_trips_through_from_cfg():
    """from_cfg must capture every field the UI can set, or a setting silently stops reaching the run."""
    cfg = {"timeframes": ["2h"], "instrument": "GC", "split_sltp": True, "sampler": "tpe",
           "only_indicators": ORIGINAL_18[:3], "exclude_indicators": ORIGINAL_18[3:5],
           "reference": "ES", "max_enabled": 4, "cold_start": True, "dd_cap": 0.4,
           "trials_mode": "one", "trials": 123, "ind_1min": False}
    s = RS.from_cfg(cfg, "2h", study_prefix="p")
    assert (s.tf, s.instrument, s.split_sltp, s.sampler) == ("2h", "GC", True, "tpe")
    assert s.only_indicators == tuple(ORIGINAL_18[:3])
    assert s.exclude_indicators == tuple(ORIGINAL_18[3:5])
    assert (s.reference, s.max_enabled, s.warm_start, s.dd_pnl_cap) == ("ES", 4, False, 0.4)
    assert (s.trials, s.ind_1min) == (123, False)
    argv = RS.build_argv(s)
    for expected in ("--instrument", "GC", "--split-sltp", "--sampler", "tpe", "--reference", "ES",
                     "--max-enabled", "4", "--no-warm-start", "--dd-pnl-cap", "0.4", "--trials", "123"):
        assert expected in argv, f"{expected} missing from built argv"
    # The frame is now ALWAYS stated. ind_1min=False must appear as the explicit opt-out, not as the
    # ABSENCE of a flag — an absent flag used to mean "decision timeframe", and that silent meaning is
    # exactly what scored the deployed champion infeasible.
    assert "--ind-1min" not in argv and "--tf-indicators" in argv
