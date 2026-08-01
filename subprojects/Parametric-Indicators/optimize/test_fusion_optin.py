"""Cross-instrument contributors are a FUSION-STUDY feature and must never switch on by accident (#96).

USER DECISION, 2026-08-01. ES-as-an-input-to-NQ is not a native indicator. It came out of the fusion
round — the set of experiments about combining several separate ideas — and it must stay usable without
leaking into ordinary optimizer work.

WHY "OFF BY DEFAULT" WAS NOT ENOUGH. `--contributors` was already empty by default. But *off unless you
type a flag* is not the same as *cannot be switched on by accident*: `--contributors ES` is one word,
and everything it costs is invisible until much later.

    +471 search dimensions for ONE token — the strategy's own search is 470, so a single contributor
    DOUBLES the problem. At the dimension-proportional budget that is 94,100 trials x 8.4 s measured,
    about 9.1 DAYS for one run. And the resulting champion needs a second instrument's data to
    reproduce its own decisions.

So enabling it now takes TWO deliberate acts: naming the tokens, and acknowledging the opt-in.
"""
import inspect

import pytest

from optimize import contributor_search as CS
from optimize import optimizer as OPT
from optimize import run_spec as RS


def test_no_tokens_is_always_fine():
    """Every ordinary run must be untouched — the gate is a no-op when nothing was asked for."""
    CS.require_fusion_optin(())
    CS.require_fusion_optin(None)
    CS.require_fusion_optin(("",))


def test_naming_a_token_alone_is_refused():
    with pytest.raises(CS.FusionNotEnabled) as e:
        CS.require_fusion_optin(("ES",))
    msg = str(e.value)
    assert "FUSION-STUDY feature" in msg
    assert "471" in msg, "the refusal must state the dimensional cost, not just say no"
    assert CS.FUSION_ACK_FLAG in msg, "and it must name the way through"


def test_the_explicit_acknowledgement_lets_it_through():
    CS.require_fusion_optin(("ES",), ack=True)


def test_the_environment_variable_also_works_for_server_launchers(monkeypatch):
    monkeypatch.setenv(CS.FUSION_ACK_ENV, "1")
    CS.require_fusion_optin(("ES",))


def test_a_truthy_looking_env_value_is_not_enough(monkeypatch):
    """Only "1". A stray `WSH_ENABLE_FUSION_CONTRIBUTORS=false` in a shell profile must not enable it —
    the whole point is that the opt-in is unambiguous."""
    for v in ("0", "false", "no", "", "yes", "true"):
        monkeypatch.setenv(CS.FUSION_ACK_ENV, v)
        if v == "1":
            continue
        with pytest.raises(CS.FusionNotEnabled):
            CS.require_fusion_optin(("ES",))


@pytest.mark.parametrize("mod", ["optimize.optimizer", "optimize.l2.optimize"])
def test_both_optimizers_declare_the_gate(mod):
    import importlib
    src = inspect.getsource(importlib.import_module(mod).main)
    assert "--enable-fusion-contributors" in src
    assert "require_fusion_optin" in src, "the flag must actually drive the gate"


@pytest.mark.parametrize("mod", ["optimize.optimizer", "optimize.l2.optimize"])
def test_the_refusal_has_its_own_exit_code(mod):
    """4, distinct from the preflight refusal (3) and from a crash (1) — a launcher must be able to tell
    'you did not opt in' from 'the run failed'."""
    import importlib
    import re
    src = inspect.getsource(importlib.import_module(mod).main)
    m = re.search(r"FusionNotEnabled.*?return (\d+)", src, re.S)
    assert m and m.group(1) == "4"


def test_runspec_defaults_to_off_and_must_be_asked_for():
    spec = RS.RunSpec(tf="4h", contributors=("ES",))
    argv = RS.build_argv(spec)
    assert "--contributors" in argv
    assert "--enable-fusion-contributors" not in argv, (
        "a RunSpec that merely names tokens must NOT silently acknowledge the opt-in — it should hit "
        "the same refusal a human would")
    opted = RS.build_argv(RS.RunSpec(tf="4h", contributors=("ES",), enable_fusion_contributors=True))
    assert "--enable-fusion-contributors" in opted


def test_a_plain_runspec_carries_no_contributor_anything():
    argv = RS.build_argv(RS.RunSpec(tf="4h"))
    assert not any(a.startswith("--contributors") or a.startswith("--enable-fusion") for a in argv)


def test_the_default_search_space_has_no_contributor_dimensions():
    """The cost this gate exists to prevent, asserted from the other side."""
    assert OPT.search_dims(False)["contributors"] == 0
    assert CS.contributor_dims(()) == 0
    assert CS.contributor_dims(("ES",)) > 400, (
        "one token should be roughly the size of the whole strategy search — that is the point")
