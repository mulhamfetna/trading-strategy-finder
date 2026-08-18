"""Cold start is the default; warm start must be asked for (#102, owner decision 2026-08-03).

WHAT WARM START DOES. It enqueues the deployed champion as a seed, so the result is provably ≥ the prior
champion. That floor was added after wsh5 returned something worse than what was already deployed.

WHY THE DEFAULT IS BEING INVERTED ANYWAY. The floor is not free. Seeding the champion starts the search
inside one basin and evolves outward from it:

    the population grows on ONE SIDE, and configurations that would have won from a different
    starting point are eliminated before they are ever explored.

A guaranteed floor was bought with an unmeasured ceiling, and because warm start was the DEFAULT rather
than a choice, every study in the system was a refinement of the incumbent unless someone remembered to
opt out. That is a decision that should be made per run, out loud.

⚠️ WHAT THIS COSTS, PINNED HERE SO IT CANNOT BE FORGOTTEN: cold start REMOVES the ≥-champion guarantee.
A cold run can return something worse than the deployed set and nothing downstream will catch it.
Anything promoted out of a cold run must be compared against the deployed set explicitly.

⚠️⚠️ AND IT INVALIDATES A CLAIM: every #88 experiment (rounds 1-3, 24 runs) was warm-started, and its
headline — "the broken archive returned its own warm-start champion in 5 of 8 seeds" — is DEFINED in
terms of the seeded champion. It cannot survive unchanged into a cold-start world and was re-run cold.
"""
import argparse
import inspect

from optimize import optimizer as OPT
from optimize import two_stage as TS
from optimize import map_elites as ME
from optimize import run_spec as RS


def _parse(argv):
    ap = argparse.ArgumentParser()
    OPT.add_warm_start_args(ap)
    return ap.parse_args(argv)


# ── the default ──────────────────────────────────────────────────────────────────────────────────

def test_saying_nothing_starts_cold():
    assert _parse([]).warm_start is False


def test_warm_start_must_be_named():
    assert _parse(["--warm-start"]).warm_start is True


def test_the_old_negative_flag_still_works_and_now_restates_the_default():
    """Server run scripts, playbooks and the dashboard all emit `--no-warm-start`. Breaking them to make
    a point would trade a silent problem for a noisy one."""
    assert _parse(["--no-warm-start"]).warm_start is False


def test_both_at_once_is_an_error_not_last_one_wins():
    ap = argparse.ArgumentParser()
    OPT.add_warm_start_args(ap)
    try:
        ap.parse_args(["--warm-start", "--no-warm-start"])
    except SystemExit:
        return
    raise AssertionError("asking for both must be an error")


# ── every entry point ────────────────────────────────────────────────────────────────────────────

def test_every_run_signature_starts_cold():
    for fn in (OPT.run, TS.run, ME.run):
        p = inspect.signature(fn).parameters["warm_start"]
        assert p.default is False, f"{fn.__module__}.{fn.__name__} still warm-starts by default"


def test_the_context_object_starts_cold_too():
    assert inspect.signature(TS._Ctx.__init__).parameters["warm_start"].default is False


def test_the_run_spec_starts_cold():
    assert RS.RunSpec("4h").warm_start is False


def test_all_clis_share_ONE_flag_definition():
    for mod in (OPT, TS, ME):
        src = inspect.getsource(mod.main)
        assert "add_warm_start_args" in src, f"{mod.__name__}.main declares the flag itself"
        assert 'add_argument("--no-warm-start"' not in src, f"{mod.__name__}.main has its own copy"


# ── the launched command must say which it used ──────────────────────────────────────────────────

def test_build_argv_always_states_which_start():
    """Cold start removes the ≥-champion guarantee, so which one a run used must be readable off the
    command itself rather than inferred from whichever version of the code reads it later."""
    cold = RS.build_argv(RS.RunSpec("4h"))
    warm = RS.build_argv(RS.RunSpec("4h", warm_start=True))
    assert "--no-warm-start" in cold and "--warm-start" not in cold
    assert "--warm-start" in warm and "--no-warm-start" not in warm


def test_it_survives_a_round_trip_through_the_command():
    for want in (True, False):
        argv = RS.build_argv(RS.RunSpec("4h", warm_start=want))
        flags = [a for a in argv if a in ("--warm-start", "--no-warm-start")]
        assert len(flags) == 1
        assert _parse(flags).warm_start is want
