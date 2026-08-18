"""The preflight gate must reach the places that actually launch hours-long runs (#94).

A mechanism nothing calls is not a mechanism. `provenance.preflight()` is tested on its own in
`test_provenance.py`; this pins that it is WIRED — into the CLI, into the RunSpec the control centre
builds, and into the server launcher — and that its refusal cannot turn into something worse than the
problem it prevents.

THE DANGEROUS CASE, and why it gets its own test. The server watchdog runs the optimizer inside

    while :; do ... python3 optimize/optimizer.py ... || true ; done

If preflight refuses and the launcher swallows the exit code, that loop respawns a refusing optimizer
forever — writing the same error into the log thousands of times a minute. A gate that converts "your
checkout is stale" into a hot loop is worse than no gate. So the refusal uses a DISTINCT exit code (3)
and the worker breaks on it.
"""
import ast
import inspect
import pathlib
import re

from optimize import optimizer as OPT
from optimize import run_spec as RS

_SERVER = pathlib.Path(__file__).resolve().parent / "server" / "remote_wsi.sh"


def test_cli_exposes_the_gate_and_both_escapes():
    src = inspect.getsource(OPT.main)
    assert "--allow-dirty" in src
    assert "--allow-behind" in src
    assert "--no-preflight" in src, "there must be a way out that is not 'delete the check'"
    assert "provenance.preflight" in src, "the flags must actually drive the gate"


def test_the_gate_runs_after_plan_so_a_dry_run_stays_usable():
    """`--plan` costs nothing and must keep working on a dirty tree — it is what you run WHILE editing.
    Gating it would make the tool useless exactly when you are trying to size a search."""
    src = inspect.getsource(OPT.main)
    plan_return = src.index("[--plan] dry run")
    gate = src.index("provenance.preflight")
    assert plan_return < gate, "preflight must come after the --plan early return"


def test_refusal_uses_a_distinct_exit_code():
    """3, not 1. The server watchdog must be able to tell 'refused' from 'crashed' — one means stop,
    the other means the chunk failed and looping on is reasonable."""
    src = inspect.getsource(OPT.main)
    m = re.search(r"PreflightError.*?return (\d+)", src, re.S)
    assert m and m.group(1) == "3", "a preflight refusal must return exit code 3"


def test_runspec_can_express_the_escapes():
    """The control centre launches through build_argv. An override the UI cannot express is an override
    the operator cannot use — they would reach for --no-preflight, or stop using the UI."""
    spec = RS.RunSpec(tf="4h", allow_dirty=True, allow_behind=True)
    argv = RS.build_argv(spec)
    assert "--allow-dirty" in argv and "--allow-behind" in argv
    clean = RS.build_argv(RS.RunSpec(tf="4h"))
    assert "--allow-dirty" not in clean and "--allow-behind" not in clean, "escapes must be opt-in"


def test_runspec_escapes_come_from_the_config():
    spec = RS.from_cfg({"timeframes": ["4h"], "allow_dirty": True}, "4h")
    assert spec.allow_dirty is True and spec.allow_behind is False


def test_the_server_watchdog_breaks_on_a_refusal_instead_of_hot_looping():
    """THE DANGEROUS CASE. `while :; do optimizer || true; done` would respawn a refusing optimizer
    forever. The worker must check the exit code and break."""
    src = _SERVER.read_text()
    assert "rc=" in src and "-eq 3" in src, "the worker must recognise the preflight exit code"
    assert "PREFLIGHT REFUSED" in src, "and say so in the log rather than failing silently"
    # the old swallow-everything form must be gone from the watchdog's optimizer call
    assert "--min-trades 5 $IND_ARGS >> \\\"\\$log\\\" 2>&1 || true" not in src, (
        "the watchdog still swallows the optimizer's exit code — a refusal becomes a hot loop")


def test_the_server_launcher_can_override_deliberately():
    src = _SERVER.read_text()
    assert "WSH_ALLOW_DIRTY" in src and "WSH_ALLOW_BEHIND" in src
    assert "$DIRTY_ARG $BEHIND_ARG" in src or "$DIRTY_ARG" in src, (
        "the escapes must reach the optimizer invocation, not just be defined")


def test_no_launcher_forces_the_escapes_on():
    """An escape that is always on is not an escape, it is a deleted check. These must be empty unless
    the operator sets the environment variable."""
    src = _SERVER.read_text()
    assert 'DIRTY_ARG="${WSH_ALLOW_DIRTY:+--allow-dirty}"' in src
    assert 'BEHIND_ARG="${WSH_ALLOW_BEHIND:+--allow-behind}"' in src
    assert "--allow-dirty --allow-behind" not in src.replace(
        'DIRTY_ARG="${WSH_ALLOW_DIRTY:+--allow-dirty}"', ""), "hardcoded escapes in a launcher"


def test_preflight_is_called_with_both_flags_not_just_one():
    """A half-wired gate is the worst outcome: it blocks the case you remembered and silently permits
    the one you did not."""
    src = inspect.getsource(OPT.main)
    tree = ast.parse(src.strip())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "preflight"]
    assert calls, "preflight is never called"
    kw = {k.arg for c in calls for k in c.keywords}
    assert {"allow_dirty", "allow_behind"} <= kw
