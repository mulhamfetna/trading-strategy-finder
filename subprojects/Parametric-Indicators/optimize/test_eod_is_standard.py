"""End-of-day close is the STANDARD for all training — not a searched option.

USER DECISION, 2026-07-30. Holding overnight is what stops a stop-loss from working: a stop-loss is an
instruction the market must WALK into, and it cannot execute while the market is shut. On natural gas the
worst trade lost **182.84x its intended risk** to a **+5.52% weekend reopen gap** — the stop was 0.03% of
price, the gap was 5.52%, 180 times larger (#79). Closing at the bell removes that exposure structurally
instead of pricing it.

THE MEASURED COST, honestly bracketed. The forced-end-of-day campaign scored **$631,999** on the 2026
out-of-sample year versus **$638,462** for the incumbents — about **−1.0%**. The tempting headline is
−24.8% against the deployed "best" set ($840,037), but that set is best-of-three-per-slot *chosen on the
2026 year it is scored on*, so it carries a selection effect and is not a fair comparison.

SCOPE — deliberately narrow. This pins the default for TRAINING (the optimizer). It does NOT make the
engine reject other cap modes, because 17 of the 54 deployed champions currently hold overnight
(cap_mode none/bars) and the golden gate pins their exact trade ledgers. Forcing the engine would break
every one of them and all six golden baselines. New champions are trained to the bell; existing ones keep
running until they are retrained.
"""
import inspect

import pytest

from optimize import optimizer as OPT


def test_run_defaults_to_forcing_end_of_day():
    assert inspect.signature(OPT.run).parameters["force_eod"].default is True, (
        "training must close at the bell by default — see #79's weekend gap")


@pytest.mark.parametrize("fn", ["search_dims", "recommended_trials", "print_plan"])
def test_budget_helpers_assume_the_standard(fn):
    """The plan must cost the search we actually run. If these still defaulted to False they would
    advertise a dimension the run does not search."""
    assert inspect.signature(getattr(OPT, fn)).parameters["force_eod"].default is True


def test_pinning_eod_removes_a_searched_dimension():
    """Pinned ⇒ en_cap_eod is no longer suggested, so the space is one dimension smaller and the
    ∝-dimension budget follows it."""
    standard = OPT.search_dims(False)["total"]
    research = OPT.search_dims(False, force_eod=False)["total"]
    assert standard == research - 1
    assert OPT.recommended_trials(False) < OPT.recommended_trials(False, force_eod=False)


def test_cli_exposes_an_explicit_opt_out():
    """Research must still be able to allow overnight holds — but by asking for it, loudly, not by
    omitting a flag."""
    import argparse
    src = inspect.getsource(OPT.main) if hasattr(OPT, "main") else ""
    assert "--no-force-eod" in src, "there must be an explicit way to re-open overnight holds"
    assert "RESEARCH ONLY" in src, "the opt-out must announce what it re-opens (#79)"
    assert isinstance(argparse.ArgumentParser(), argparse.ArgumentParser)


def test_engine_is_NOT_forced():
    """The scope boundary, asserted so it cannot be widened by accident.

    17 of 54 deployed champions hold overnight (cap_mode none/bars) and the golden gate pins their exact
    trade ledgers. If the ENGINE ever refuses a non-eod cap_mode, those champions and all six golden
    baselines break at once.
    """
    from optimize.l2 import payload as P
    for mode in ("none", "bars", "eod", "both"):
        p = P.validate_layer_params({"sl_soft": 40.0, "sl_hard": 80.0, "tp": 100.0, "gate_pct": 60.0,
                                     "dd_limit": 2000.0, "cooldown": 1, "k": 1, "flip": False,
                                     "cap_mode": mode})
        assert p["cap_mode"] == mode, (
            f"the engine rejected cap_mode={mode!r} — that would break the 17 overnight champions and "
            f"the golden gate. Forcing the bell is a TRAINING default, not an engine restriction.")
