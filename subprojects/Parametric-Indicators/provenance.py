"""Every artifact says what produced it (#94, Layer 1).

THE PROBLEM THIS SOLVES. Nothing in this system stamped a result with the code that computed it, so
"is this artifact current?" was never answerable from the artifact — only guessable from a timestamp.
That guess has been wrong more than once:

  * a crashed run left a COMPLETE, GREEN golden-gate log on disk from a broken build, and the next poll
    read it as the current result. Only `stat` on the file caught it (playbook C16).
  * a report rescued from the server on 2026-07-31 turned out to be a DIFFERENT campaign's output,
    written over a "latest run" filename. Its own header claimed a search that never happened.
  * a full suite run against the wrong data tree produced 32 failures that read as regressions.

WHY THIS IS LAYER 1. Of the four layers proposed in `docs/ISSUE-94-local-server-sync-root-cause.md`,
this is the cheapest and the largest: it changes no workflow, and it converts the whole class of "is
this stale?" from a thing you must remember into a fact you can read. A report whose stamp says
`git_dirty: true`, or names a commit you do not recognise, is self-evidently suspect. Everything else
in #94 is easier to verify once this exists.

WHAT IT DELIBERATELY DOES NOT DO. It does not prevent divergence — nothing can, short of removing one
of the machines. It makes divergence *visible after the fact*, which is the property that was missing.

Usage:
    import provenance
    provenance.stamp(out_dir, argv=sys.argv)      # writes <out_dir>/_provenance.json
    print(provenance.one_line())                  # for a run header
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import roots

STAMP_NAME = "_provenance.json"


def _git(*args: str) -> str | None:
    """A git query that never raises and never blocks a run.

    A provenance stamp must not be able to break the thing it is describing — if git is missing, or the
    tree is not a repo, the stamp records that fact instead of failing.
    """
    try:
        out = subprocess.run(("git", "-C", str(roots.REPO_ROOT), *args),
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def _registry_size() -> int | None:
    """Imported lazily and defensively: the indicator library is heavy, and provenance must be usable
    from scripts that have no business importing it."""
    try:
        from indicators import library
        return len(library.REGISTRY)
    except Exception:  # noqa: BLE001
        return None


def _numba_version() -> str | None:
    """Recorded because the accelerator's PRESENCE changes which program runs. Locally `njit` is a
    no-op, so the reference implementation executes; a recursive kernel that passed locally once
    segfaulted on the server (playbook C13). 'Which machine ran this' is not a complete answer without
    it."""
    try:
        import numba
        return numba.__version__
    except Exception:  # noqa: BLE001
        return None


def snapshot(argv=None, extra: dict | None = None) -> dict:
    """Everything needed to answer 'what produced this artifact?'."""
    dirty = _git("status", "--porcelain")
    snap = {
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        # None means "could not tell" — deliberately distinct from False ("checked, tree is clean").
        # Reporting an unknown as clean is exactly the kind of quiet lie this module exists to prevent.
        "git_dirty": None if dirty is None else bool(dirty),
        "git_dirty_files": None if dirty is None else len(dirty.splitlines()),
        "host": platform.node(),
        "repo_root": str(roots.REPO_ROOT),
        "data_root": str(roots.DATA_ROOT),
        "python": platform.python_version(),
        "numba": _numba_version(),
        "registry_size": _registry_size(),
        "started_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "argv": list(argv) if argv is not None else None,
    }
    if extra:
        snap.update(extra)
    return snap


def stamp(out_dir, argv=None, extra: dict | None = None) -> Path:
    """Write `_provenance.json` next to an artifact. Returns the path written."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / STAMP_NAME
    p.write_text(json.dumps(snapshot(argv=argv, extra=extra), indent=2) + "\n")
    return p


def one_line(snap: dict | None = None) -> str:
    """A single line for a run header, so the terminal shows it even when nobody opens the JSON."""
    s = snap or snapshot()
    dirty = "?" if s["git_dirty"] is None else ("DIRTY" if s["git_dirty"] else "clean")
    return (f"[provenance] {s['git_commit']} ({s['git_branch']}, {dirty}) on {s['host']} · "
            f"data={s['data_root']} · py{s['python']} · "
            f"numba={s['numba'] or 'ABSENT'} · {s['registry_size']} indicators")


def read(out_dir) -> dict | None:
    p = Path(out_dir) / STAMP_NAME
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------------------------
# Preflight (#94, Layer 2)
# ---------------------------------------------------------------------------------------------

class PreflightError(RuntimeError):
    """A run that would be unattributable, stopped before it produces a plausible number."""


def preflight(require_data: tuple[str, ...] = (), allow_dirty: bool = False,
              allow_behind: bool = False, verbose: bool = True) -> dict:
    """Refuse to start a run whose result could not later be trusted.

    THE ARGUMENT FOR BLOCKING RATHER THAN WARNING. Every failure this catches is silent by nature: a
    stale checkout, a wrong data root, a missing accelerator. Each produces a run that completes
    normally and looks exactly like a correct one. A warning in a long log is a warning nobody reads —
    the stale-checkout case was found today only because I happened to run `git status` by hand. A
    result that should not be trusted is worth less than no result, so the default is to stop.

    Both overrides are recorded IN THE STAMP, so an overridden run is still attributable.
    """
    snap = snapshot()
    problems = []

    if snap["git_dirty"] and not allow_dirty:
        problems.append(
            f"the checkout has {snap['git_dirty_files']} uncommitted change(s) — this run would not be "
            f"reproducible from any commit. Commit, stash, or pass allow_dirty=True.")

    if not allow_behind:
        behind = _git("rev-list", "--count", "HEAD..@{upstream}")
        if behind and behind.isdigit() and int(behind) > 0:
            problems.append(
                f"the checkout is {behind} commit(s) BEHIND its upstream — you are almost certainly not "
                f"running the code you think you are. `git pull`, or pass allow_behind=True.")

    for rel in require_data:
        if not (roots.DATA_ROOT / rel).exists():
            problems.append(
                f"data root {roots.DATA_ROOT} has no {rel!r}. This is usually the WRONG ROOT rather "
                f"than missing data — see roots.require_data() for the candidates on this machine.")

    if verbose:
        print(one_line(snap), flush=True)

    if problems:
        raise PreflightError(
            "preflight refused to start this run:\n  - " + "\n  - ".join(problems)
            + "\n  (each of these produces a run that COMPLETES NORMALLY and looks correct — #94)")

    snap["preflight"] = {"allow_dirty": allow_dirty, "allow_behind": allow_behind,
                         "required_data": list(require_data)}
    return snap
