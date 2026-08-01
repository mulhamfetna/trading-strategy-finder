"""Every artifact must be able to say what produced it, and a run that could not be attributed must
refuse to start (#94 Layers 1-2).

WHY THESE ASSERTIONS AND NOT OTHERS. Each one pins a case where the absence of provenance already cost
something real:

  * a green golden-gate log survived a CRASHED build and was read as the current result (C16)
  * a rescued report described a campaign that never ran, because it was written over a "latest run"
    filename by a different campaign
  * a suite run against the wrong data tree produced 32 failures that read as regressions

The subtle one is `git_dirty`. It is three-valued on purpose — True / False / None. `None` means "could
not tell" and must never collapse into False, because reporting an unknown as "clean" is exactly the
quiet lie the module exists to prevent.
"""
import json
import subprocess

import pytest

import provenance
import roots


def test_snapshot_answers_what_produced_this(tmp_path):
    s = provenance.snapshot(argv=["python", "-m", "thing", "--flag"])
    for k in ("git_commit", "git_branch", "git_dirty", "host", "repo_root", "data_root",
              "python", "numba", "registry_size", "started_utc", "argv"):
        assert k in s, f"provenance is missing {k}"
    assert s["repo_root"] == str(roots.REPO_ROOT)
    assert s["data_root"] == str(roots.DATA_ROOT)
    assert s["argv"] == ["python", "-m", "thing", "--flag"]


def test_stamp_is_written_next_to_the_artifact_and_is_valid_json(tmp_path):
    out = tmp_path / "results"
    p = provenance.stamp(out, argv=["run"])
    assert p == out / "_provenance.json"
    assert json.loads(p.read_text())["argv"] == ["run"]
    assert provenance.read(out)["repo_root"] == str(roots.REPO_ROOT)


def test_dirty_is_three_valued_never_collapsed_to_clean(monkeypatch):
    """None means 'could not tell'. If git is unavailable, the stamp must NOT claim the tree was clean."""
    monkeypatch.setattr(provenance, "_git", lambda *a: None)
    s = provenance.snapshot()
    assert s["git_dirty"] is None
    assert s["git_dirty"] is not False
    assert "?" in provenance.one_line(s)


def test_a_stamp_never_breaks_the_run_it_describes(monkeypatch, tmp_path):
    """Provenance is bookkeeping. If git, numba and the indicator library are all unavailable it must
    still produce a stamp rather than take the run down with it."""
    def boom(*a, **k):
        raise OSError("no git here")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(provenance, "_registry_size", lambda: None)
    monkeypatch.setattr(provenance, "_numba_version", lambda: None)
    p = provenance.stamp(tmp_path / "out")
    s = json.loads(p.read_text())
    assert s["git_commit"] is None and s["registry_size"] is None


def test_one_line_reports_the_accelerator_because_it_changes_which_program_runs():
    """Locally `njit` is a no-op, so the REFERENCE implementation executes; a recursive kernel that
    passed locally once segfaulted on the server (C13). 'Which host' is not a complete answer."""
    line = provenance.one_line()
    assert "numba=" in line
    assert "data=" in line and "indicators" in line


# --- preflight -------------------------------------------------------------------------------

def _fake_snapshot(**over):
    base = {"git_dirty": False, "git_dirty_files": 0, "git_commit": "abc1234", "git_branch": "dev",
            "host": "h", "repo_root": "/r", "data_root": "/d", "python": "3.12.0", "numba": None,
            "registry_size": 165, "started_utc": "x", "argv": None}
    base.update(over)
    return lambda **k: dict(base)


def test_preflight_blocks_a_dirty_checkout(monkeypatch):
    monkeypatch.setattr(provenance, "snapshot", _fake_snapshot(git_dirty=True, git_dirty_files=3))
    with pytest.raises(provenance.PreflightError) as e:
        provenance.preflight(verbose=False)
    assert "uncommitted" in str(e.value)
    assert "COMPLETES NORMALLY" in str(e.value), "the message must say why a warning would not do"


def test_preflight_allows_a_dirty_checkout_when_asked_and_records_it(monkeypatch):
    """The override is not a bypass: it lands in the stamp, so the run stays attributable."""
    monkeypatch.setattr(provenance, "snapshot", _fake_snapshot(git_dirty=True, git_dirty_files=1))
    monkeypatch.setattr(provenance, "_git", lambda *a: "0")
    snap = provenance.preflight(allow_dirty=True, verbose=False)
    assert snap["preflight"]["allow_dirty"] is True


def test_preflight_blocks_a_checkout_that_is_behind_upstream(monkeypatch):
    """The failure found today: the server was 9 commits behind and nothing said so."""
    monkeypatch.setattr(provenance, "snapshot", _fake_snapshot())
    monkeypatch.setattr(provenance, "_git", lambda *a: "9")
    with pytest.raises(provenance.PreflightError) as e:
        provenance.preflight(verbose=False)
    assert "BEHIND" in str(e.value)


def test_preflight_blocks_a_wrong_data_root(monkeypatch):
    """The 32-fake-regressions case: it must be caught BEFORE the run, not diagnosed afterwards."""
    monkeypatch.setattr(provenance, "snapshot", _fake_snapshot())
    monkeypatch.setattr(provenance, "_git", lambda *a: "0")
    with pytest.raises(provenance.PreflightError) as e:
        provenance.preflight(require_data=("ALL_STOCKS_THAT_DOES_NOT_EXIST",), verbose=False)
    assert "WRONG ROOT" in str(e.value)


def test_a_clean_run_passes_preflight_and_returns_its_snapshot(monkeypatch):
    monkeypatch.setattr(provenance, "snapshot", _fake_snapshot(numba="0.65"))
    monkeypatch.setattr(provenance, "_git", lambda *a: "0")
    snap = provenance.preflight(verbose=False)
    assert snap["git_commit"] == "abc1234" and snap["preflight"]["allow_dirty"] is False
