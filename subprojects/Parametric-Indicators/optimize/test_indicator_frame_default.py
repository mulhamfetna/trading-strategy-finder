"""The 1-minute indicator frame is the DEFAULT everywhere, and the other frame must be asked for.

WHY THE POLARITY MATTERS MORE THAN IT LOOKS. Every champion in the deployed book was tuned with
indicators read off the 1-minute frame. The decision-timeframe frame is a research alternative. But the
flag was `--ind-1min` with `ind_1min: bool = False` — opt-IN — so the WRONG frame was what you got by
forgetting, and forgetting is silent: the run completes and the numbers look like numbers.

The size of the difference, measured on the deployed NQ 4h champion (2026-08-03):

    1-minute frame     full P/L $147,191   full DD $14,043   → FEASIBLE
    decision frame     full P/L  $38,494   full DD $23,580   → INFEASIBLE (25% rule allows $9,623)

So a MAP-Elites run in the wrong frame returns an EMPTY archive, which reads as a broken algorithm
rather than a mis-set flag. That is how it actually presented during #88, and it cost a debugging pass.

This is the "no silent defaults" rule applied to a frame instead of a parameter: a measurement input you
can get wrong by OMISSION is a defect, not a convenience.
"""
import argparse
import inspect

from optimize import optimizer as OPT
from optimize import two_stage as TS
from optimize import map_elites as ME
from optimize import run_spec as RS


def _parse(argv):
    ap = argparse.ArgumentParser()
    OPT.add_indicator_frame_args(ap)
    return ap.parse_args(argv)


# ── the default itself ───────────────────────────────────────────────────────────────────────────

def test_saying_nothing_gives_the_one_minute_frame():
    assert _parse([]).ind_1min is True


def test_the_other_frame_must_be_asked_for_by_name():
    assert _parse(["--tf-indicators"]).ind_1min is False


def test_the_old_flag_still_works_and_now_only_restates_the_default():
    """Kept for compatibility: server run scripts, playbooks and docs all say `--ind-1min`. Breaking
    them to make a point would trade one silent failure for a noisy one."""
    assert _parse(["--ind-1min"]).ind_1min is True


def test_the_two_frames_cannot_both_be_requested():
    ap = argparse.ArgumentParser()
    OPT.add_indicator_frame_args(ap)
    try:
        ap.parse_args(["--ind-1min", "--tf-indicators"])
    except SystemExit:
        return
    raise AssertionError("asking for both frames at once must be an error, not a last-one-wins")


# ── every entry point, not just the one that was noticed ─────────────────────────────────────────

def test_every_run_signature_defaults_to_the_one_minute_frame():
    """FOUR separate defaults existed and every production caller passed ind_1min=True by hand — which
    is the tell that the default was wrong, not that the callers were careful."""
    for fn in (OPT.run, TS.run, ME.run):
        p = inspect.signature(fn).parameters["ind_1min"]
        assert p.default is True, f"{fn.__module__}.{fn.__name__} still defaults to the decision frame"


def test_the_context_object_defaults_too():
    """`_Ctx` is what the benches and one-off scripts build directly, bypassing run()."""
    assert inspect.signature(TS._Ctx.__init__).parameters["ind_1min"].default is True


def test_the_run_spec_default_matches():
    assert RS.RunSpec("4h").ind_1min is True


def test_all_four_clis_share_ONE_flag_definition():
    """Four copies of a default is four chances for one of them to be the old one. The CLIs must call
    the shared helper rather than declare `--ind-1min` themselves."""
    for mod in (OPT, TS, ME):
        src = inspect.getsource(mod.main)
        assert "add_indicator_frame_args" in src, f"{mod.__name__}.main declares the frame flag itself"
        assert 'add_argument("--ind-1min"' not in src, f"{mod.__name__}.main has its own copy"


# ── the launched command must SAY which frame it used ────────────────────────────────────────────

def test_build_argv_always_states_the_frame():
    """A launched command is a record of what was run. Relying on the default would make the record
    depend on the version of the code that later reads it."""
    on = RS.build_argv(RS.RunSpec("4h", ind_1min=True))
    off = RS.build_argv(RS.RunSpec("4h", ind_1min=False))
    assert "--ind-1min" in on and "--tf-indicators" not in on
    assert "--tf-indicators" in off and "--ind-1min" not in off


def test_the_frame_survives_a_round_trip_through_the_command():
    """preview == execution (#91): whatever the UI shows must parse back to the same frame."""
    for want in (True, False):
        argv = RS.build_argv(RS.RunSpec("4h", ind_1min=want))
        flags = [a for a in argv if a in ("--ind-1min", "--tf-indicators")]
        assert len(flags) == 1
        assert _parse(flags).ind_1min is want
