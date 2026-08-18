"""No module may resolve a project path from a hardcoded absolute path (#94).

THE DEFECT THIS LOCKS OUT. Twelve modules wrote the repository root as a literal, with the environment
variable as an *override*:

    _BASE = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))

The default is one machine's layout. Anywhere else it resolves to a directory that does not exist —
and because `optimize/l2/contributors/registry.py` calls its loader at MODULE level, that surfaces as
`FileNotFoundError` at **import**, which makes pytest drop the entire file at collection.

That is the part worth pinning: it is not a failing test, it is an **ABSENT** one. It shows up in
neither the pass count nor the skip count. The contributor tests had silently never run on the server,
and nothing in any suite output said so.

The second half of the defect is that one variable meant two things — the repo root (a property of the
checkout, always derivable) and the data root (genuinely machine-specific). Running the suite against
the wrong one produced 32 `FileNotFoundError` failures that looked exactly like regressions from the
change under test; against the right one, 1,126 passed.
"""
import ast
import os
import pathlib

import pytest

import roots

_PI = pathlib.Path(__file__).resolve().parent
_REPO = _PI.parents[1]

# Exempt, each for a stated reason — not because they are inconvenient.
#
#   server-audit/     a harvested record of code EXACTLY as it ran on the server. Rewriting it would
#                     destroy the evidence it exists to preserve.
#   optimize/reports/ one-off analysis scripts rescued from the server. Same argument: they are the
#                     provenance of a finished result, not code anyone runs again. They DO carry
#                     server paths and would not run elsewhere — that is a property of the record.
#   shareable/        a vendored, self-contained bundle shipped to third parties; it deliberately
#                     carries its own copy of everything.
#   this file         it necessarily contains the very prefixes it searches for.
_EXEMPT = ("server-audit/", "optimize/reports/", "shareable/", "__pycache__/", "test_roots.py")


def _py_files():
    for p in _PI.rglob("*.py"):
        rel = str(p.relative_to(_PI))
        if any(x in rel.replace(os.sep, "/") for x in _EXEMPT):
            continue
        yield p


def test_repo_root_is_derived_not_configured():
    """The checkout's location is a fact about the checkout. It must never need to be told."""
    assert roots.REPO_ROOT == _REPO
    assert (roots.REPO_ROOT / "subprojects" / "Parametric-Indicators").is_dir()
    assert roots.INSTRUMENTS_PY.name == "instruments.py"
    assert "subprojects/all-stocks-signals" in roots.INSTRUMENTS_PY.as_posix()


def test_instruments_registry_is_repo_relative_not_data_relative(monkeypatch):
    """CODE follows the checkout. Pointing the DATA root elsewhere must not move the code we import —
    on the server that difference is 'the copy I am running' vs 'an rsync snapshot from June'."""
    monkeypatch.setenv("WSH_DATA_ROOT", "/nonexistent/data/tree")
    import importlib
    r2 = importlib.reload(roots)
    try:
        assert r2.DATA_ROOT == pathlib.Path("/nonexistent/data/tree")
        assert r2.INSTRUMENTS_PY == _REPO / "subprojects" / "all-stocks-signals" / "instruments.py"
    finally:
        monkeypatch.delenv("WSH_DATA_ROOT", raising=False)
        importlib.reload(roots)


@pytest.mark.parametrize("var", ["WSH_DATA_ROOT", "WSH_DATA_BASE"])
def test_both_env_names_select_the_data_root(monkeypatch, var):
    """WSH_DATA_BASE is the legacy name every server script exports; it must keep working."""
    monkeypatch.delenv("WSH_DATA_ROOT", raising=False)
    monkeypatch.delenv("WSH_DATA_BASE", raising=False)
    monkeypatch.setenv(var, "/tmp/some/data/root")
    import importlib
    try:
        assert importlib.reload(roots).DATA_ROOT == pathlib.Path("/tmp/some/data/root")
    finally:
        monkeypatch.delenv(var, raising=False)
        importlib.reload(roots)


def test_new_name_wins_when_both_are_set(monkeypatch):
    monkeypatch.setenv("WSH_DATA_BASE", "/tmp/legacy")
    monkeypatch.setenv("WSH_DATA_ROOT", "/tmp/current")
    import importlib
    try:
        assert importlib.reload(roots).DATA_ROOT == pathlib.Path("/tmp/current")
    finally:
        monkeypatch.delenv("WSH_DATA_BASE", raising=False)
        monkeypatch.delenv("WSH_DATA_ROOT", raising=False)
        importlib.reload(roots)


def test_an_empty_env_var_does_not_become_the_current_directory(monkeypatch):
    """`export WSH_DATA_BASE=''` is a common shape in the shell launchers (the `${VAR:-}` idiom). An
    empty string must fall through to the derived root, not silently resolve to Path('.')."""
    monkeypatch.setenv("WSH_DATA_BASE", "")
    monkeypatch.delenv("WSH_DATA_ROOT", raising=False)
    import importlib
    try:
        assert importlib.reload(roots).DATA_ROOT == _REPO
    finally:
        monkeypatch.delenv("WSH_DATA_BASE", raising=False)
        importlib.reload(roots)


def test_no_module_hardcodes_the_repository_root():
    """THE SWEEP. Any string literal that looks like an absolute path into this project is the defect.

    Uses the AST rather than a regex, per the #89 lesson: a regex over source text cannot tell a real
    string constant from the same characters inside a docstring — and `roots.py`'s own docstring quotes
    the offending line in order to document it.
    """
    # A docstring is an ast.Constant too, and ast gives no parent links — so collect the docstrings
    # first and skip those exact values. Without this, roots.py fails its own test for quoting the bug.
    real = []
    for p in _py_files():
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:
            continue
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(node, clean=False)
                if d is not None:
                    docstrings.add(d)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value
                if v in docstrings:
                    continue
                if v.startswith("/mnt/data/projects/") or v.startswith("/home/dev/Mulham/"):
                    real.append(f"{p.relative_to(_PI)}:{node.lineno}: {v!r}")
    assert not real, (
        "these resolve a project path from a machine-specific literal — import-time failure anywhere "
        "else, which pytest reports as an ABSENT test rather than a failing one (#94):\n  "
        + "\n  ".join(sorted(set(real))))


def test_require_data_names_the_candidate_roots(monkeypatch):
    """The error message is the whole point. A bare FileNotFoundError deep in a loader reads as 'the
    code is broken'; it cost a full suite run and 32 apparent regressions to learn it actually meant
    'you pointed at the wrong tree'."""
    monkeypatch.setenv("WSH_DATA_ROOT", "/tmp/definitely-not-a-data-root")
    import importlib
    r2 = importlib.reload(roots)
    try:
        with pytest.raises(FileNotFoundError) as e:
            r2.require_data("ALL_STOCKS")
        msg = str(e.value)
        assert "WRONG ROOT" in msg
        assert "WSH_DATA_ROOT" in msg
        assert "ALL_STOCKS" in msg
    finally:
        monkeypatch.delenv("WSH_DATA_ROOT", raising=False)
        importlib.reload(roots)


def test_describe_is_one_line_and_names_both_roots():
    d = roots.describe()
    assert "\n" not in d
    assert "repo=" in d and "data=" in d
