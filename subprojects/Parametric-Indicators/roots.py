"""The ONE place that knows where the repository is and where the data is (#94).

THE DEFECT THIS REPLACES. Twelve modules resolved project paths like this:

    _BASE = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))

That is a machine-specific fact frozen as a literal, with the environment variable as an *override*
rather than the source of truth. On any machine but the one it was written on, the default is wrong.
`optimize/l2/contributors/registry.py` calls its loader at MODULE level, so a wrong root raises
`FileNotFoundError` at **import**, which takes the whole test file down at collection. That is not a
failing test — it is an **absent** one: it appears in neither the pass count nor the skip count. The
contributor tests had therefore never run on the server, and never reported as skipped either.

TWO ROOTS, NOT ONE. `WSH_DATA_BASE` was doing two different jobs:

    * the REPO root   — where `subprojects/all-stocks-signals/instruments.py` lives. This is a property
                        of the checkout, never of the machine. It can always be derived from __file__.
    * the DATA root   — where `Full_Canldes_Data/` and `ALL_STOCKS/` live. This IS machine-specific:
                        on the server they sit in a different tree from the code, and there are three
                        candidate trees.

Conflating them is why a full-suite run against the wrong tree produced **32 FileNotFoundError failures
that looked exactly like regressions from the change under test**. Re-run against the tree that has the
data: 1,126 passed, 0 failed. Nothing in the output said "you picked the wrong root".

BACKWARD COMPATIBILITY. `WSH_DATA_BASE` still works and still means the data root — every server script
and runner sets it. `WSH_DATA_ROOT` is the new, unambiguous name and wins when both are set.

ONE DELIBERATE BEHAVIOUR CHANGE. Repo-root lookups (the instrument registry) now resolve from the
CHECKOUT rather than from `WSH_DATA_BASE`. On the server that means the current `~/Mulham/code` copy
instead of an rsync snapshot under a data tree. Verified identical (`diff`) at the time of the change,
and it is the correct direction: code should come from the checkout you are running, not from whichever
tree happens to hold the candles.
"""
from __future__ import annotations

import os
from pathlib import Path

# Derived, never a literal: .../subprojects/Parametric-Indicators/roots.py -> .../trading
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Machine-specific. WSH_DATA_ROOT is the unambiguous name; WSH_DATA_BASE is the legacy one every
# existing runner exports. Empty strings are treated as unset — `export WSH_ONLY=''` is a common shape
# in the shell launchers and an empty root must not silently become Path('.').
# ⚠️ 2026-08-22: market data lives ONLY on the server (docs/DATA-AND-KNOWLEDGE-MAP.md). The
# REPO_ROOT fallback below resolves to an EMPTY tree locally — a FileNotFoundError there means
# "run on the server with WSH_DATA_BASE/WSG_DATA_ROOT set", not a bug.
DATA_ROOT: Path = Path(
    os.environ.get("WSH_DATA_ROOT") or os.environ.get("WSH_DATA_BASE") or REPO_ROOT
)

# The instrument registry is CODE, so it is repo-relative — see the module docstring.
INSTRUMENTS_PY: Path = REPO_ROOT / "subprojects" / "all-stocks-signals" / "instruments.py"


def data_path(*parts) -> Path:
    """A path under the data root."""
    return DATA_ROOT.joinpath(*parts)


def repo_path(*parts) -> Path:
    """A path under the repository checkout."""
    return REPO_ROOT.joinpath(*parts)


def require_data(*relative: str) -> None:
    """Fail LOUDLY and usefully when the data root does not hold what this run needs.

    The point is the message. A bare FileNotFoundError deep inside a loader reads as "the code is
    broken"; it took a full suite run and 32 apparent regressions to work out that it actually meant
    "you pointed at the wrong tree". This says so, and names the trees it knows about.
    """
    missing = [r for r in relative if not (DATA_ROOT / r).exists()]
    if not missing:
        return
    known = "\n".join(f"      {c}" for c in _candidate_roots())
    raise FileNotFoundError(
        f"data root {DATA_ROOT} does not contain: {', '.join(missing)}\n"
        f"    This is almost certainly the WRONG ROOT rather than missing code.\n"
        f"    Set WSH_DATA_ROOT (or the legacy WSH_DATA_BASE) to a tree that has it.\n"
        f"    Roots seen on this machine:\n{known or '      (none found)'}"
    )


def _candidate_roots() -> list[str]:
    """Directories that look like a data root, to put in the error message.

    Deliberately evidence-based: it reports what is actually on this machine rather than a hardcoded
    list that would rot the same way the original constant did.
    """
    marks = ("Full_Canldes_Data", "ALL_STOCKS")
    seen, out = set(), []
    for base in (REPO_ROOT, Path.home() / "Mulham", DATA_ROOT.parent):
        try:
            if not base.is_dir():
                continue
            for child in [base, *sorted(base.iterdir())]:
                if child in seen or not child.is_dir():
                    continue
                seen.add(child)
                hits = [m for m in marks if (child / m).is_dir()]
                if hits:
                    out.append(f"{child}  ({', '.join(hits)})")
        except OSError:
            continue
    return out


def describe() -> str:
    """One line for a run header / provenance stamp."""
    legacy = " (via legacy WSH_DATA_BASE)" if (
        not os.environ.get("WSH_DATA_ROOT") and os.environ.get("WSH_DATA_BASE")) else ""
    return f"repo={REPO_ROOT} data={DATA_ROOT}{legacy}"
