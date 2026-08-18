"""Gap-aware fills are MANDATORY. There is no `gap_fills=False` anywhere a user or study can reach.

WHY (2026-07-29, user instruction). When a 1-minute bar OPENS beyond a hard stop or target, that stop
price never traded. The old engine filled you there anyway — at a price that did not exist. Measured
across all 54 champions (GAP-02) that flattered our risk by ~10% overall and **148% on natural gas**,
and an entire position-sizing workstream was then built on drawdowns that were never real.

A default-on-but-overridable flag was not enough: the override kept being reachable from presets,
profiles and layer params, so any study could quietly score a strategy at impossible prices. It is now
removed from every live surface:

    backtester (strategy.py)        -> hardcoded True
    optimizer  (optimize/core.py)   -> hardcoded True
    L1 runner  (optimize/l2/…)      -> hardcoded True
    both dashboards (payload.py)    -> request REJECTED, never silently ignored

The engine dataclass and fast_backtest keep the switch internally for one reason only: the archived
GAP-01/02 scripts reproduce the one-time before/after study that justified the change. fast_backtest
now warns loudly when it is used.

Note the rejection is deliberately an ERROR, not a silent override. Quietly giving honest fills to a
caller who asked for the optimistic model would leave them believing their numbers are something they
are not — the exact failure this change exists to end.
"""
import pathlib
import re
import warnings

import pytest

from optimize.l2 import payload as P


def _base():
    return {"sl_soft": 40.0, "sl_hard": 80.0, "tp": 100.0, "gate_pct": 60.0,
            "dd_limit": 2000.0, "cooldown": 1, "k": 1, "flip": False}


def test_asking_to_turn_gap_fills_off_is_an_error():
    with pytest.raises(P.L2ParamError) as e:
        P.validate_layer_params({**_base(), "gap_fills": False})
    assert "no longer supported" in str(e.value)


@pytest.mark.parametrize("falsy", [False, 0, "", None])
def test_every_falsy_spelling_is_rejected(falsy):
    """A JSON round-trip can turn False into 0 or "" — all of them mean the same request."""
    with pytest.raises(P.L2ParamError):
        P.validate_layer_params({**_base(), "gap_fills": falsy})


def test_explicitly_asking_for_honest_fills_is_fine():
    out = P.validate_layer_params({**_base(), "gap_fills": True})
    assert out["gap_fills"] is True


def test_absent_means_honest_fills():
    assert P.validate_layer_params(_base())["gap_fills"] is True


def test_the_flag_cannot_be_smuggled_through_as_a_truthy_string():
    """'false' is a non-empty string and therefore truthy — it must still end up honest, not off."""
    assert P.validate_layer_params({**_base(), "gap_fills": "false"})["gap_fills"] is True


# ── the real guard: no LIVE code path may read this from user-supplied params ────────────────────────

LIVE_PATHS = ["strategy.py", "optimize/core.py", "optimize/l2/l1_runner.py", "optimize/l2/payload.py"]


@pytest.mark.parametrize("rel", LIVE_PATHS)
def test_no_live_path_reads_gap_fills_from_params(rel):
    """The regression. Each of these used to do `params.get("gap_fills", True)`, which is exactly how an
    override stayed reachable — and is also a silent default on a risk parameter."""
    src = pathlib.Path(rel).read_text()
    bad = re.findall(r"""(?:params|p|P)\.get\(\s*["']gap_fills["']""", src)
    assert not bad, (
        f"{rel} still reads gap_fills from caller params ({bad}). Gap-aware fills are mandatory — "
        f"hardcode True and let payload._reject_gap_fills() refuse the request.")


@pytest.mark.parametrize("rel", LIVE_PATHS)
def test_live_paths_pass_it_as_true(rel):
    """Belt and braces: if a live file mentions gap_fills at all, it must assign it True."""
    src = pathlib.Path(rel).read_text()
    for m in re.finditer(r"gap_fills\s*=\s*([A-Za-z_.\(\)\[\]\"' ]+?)[,\)\n]", src):
        val = m.group(1).strip()
        assert val in ("True", "bool(True)"), f"{rel}: gap_fills assigned {val!r}, expected True"


def test_fast_engine_warns_if_the_archived_path_is_used():
    """The low-level switch survives for the archived GAP-01/02 scripts — but never silently."""
    import numpy as np

    from optimize.fast_engine import fast_backtest
    z = np.zeros(0)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            fast_backtest(z, z, np.zeros(0, dtype=np.int64), np.zeros(0, dtype=bool),
                          z, z, z, z, 40.0, 80.0, 100.0, False, m_open=z, gap_fills=False)
        except Exception:
            pass                      # empty arrays may raise; the warning must fire regardless
        assert any(issubclass(x.category, RuntimeWarning) and "NOT a supported system configuration"
                   in str(x.message) for x in w), "the archived fill-at-the-line path warned nothing"
