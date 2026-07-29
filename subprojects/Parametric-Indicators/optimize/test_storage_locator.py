"""A study must be findable without knowing which backend created it.

THE INCIDENT THIS PREVENTS (2026-07-29). Three storage backends are selectable by two usually-unset
environment variables — journal files, a served RDB (Postgres), and per-timeframe SQLite (the default).
The study files are named identically in each, and nothing announced which was live.

Twice in one session I reported a COMPLETED 12-study campaign as lost, because I queried Postgres while
the studies sat in SQLite. The trials were all there — 5,900 per study. The search was simply pointed at
the wrong half of the system.

`find_study()` searches every backend; `describe_backend()` makes the live one visible at study start.
An empty result from one backend means "not here" — never "nowhere".
"""
import optuna
import pytest

from optimize import storage as S


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(S.ENV_VAR, raising=False)
    monkeypatch.delenv(S.JOURNAL_ENV, raising=False)


def test_finds_a_real_sqlite_study(tmp_path):
    """End-to-end: create a genuine Optuna study in a per-TF file, then locate it by name alone."""
    db = tmp_path / "wsh_4h.db"
    st = optuna.create_study(study_name="probe_4h", storage=f"sqlite:///{db}")
    st.optimize(lambda t: (t.suggest_float("x", 0, 1) - 0.5) ** 2, n_trials=3)

    hits = S.find_study("probe_4h", studies_dir=tmp_path)
    assert len(hits) == 1, f"expected exactly one location, got {hits}"
    assert hits[0]["backend"] == "sqlite"
    assert hits[0]["trials"] == 3
    assert hits[0]["location"].endswith("wsh_4h.db")


def test_scans_every_file_not_just_the_expected_one(tmp_path):
    """The July studies were spread across 12 differently-named files. A locator that only checks the
    file it *expects* reproduces the original error."""
    for tf in ("4h", "2h", "15m"):
        optuna.create_study(study_name=f"camp_{tf}", storage=f"sqlite:///{tmp_path}/wsh_{tf}.db")
    for tf in ("4h", "2h", "15m"):
        assert S.find_study(f"camp_{tf}", studies_dir=tmp_path), f"camp_{tf} not found"


def test_missing_study_returns_empty_not_an_error(tmp_path):
    assert S.find_study("nope", studies_dir=tmp_path) == []


def test_unreachable_rdb_does_not_hide_a_sqlite_hit(tmp_path):
    """The failure mode that matters: a broken/absent Postgres must not mask the real location."""
    optuna.create_study(study_name="here_4h", storage=f"sqlite:///{tmp_path}/wsh_4h.db")
    hits = S.find_study("here_4h", studies_dir=tmp_path,
                        url="postgresql://nobody@127.0.0.1:1/doesnotexist")
    assert any(h["backend"] == "sqlite" for h in hits), (
        "an unreachable RDB swallowed the SQLite hit — this is exactly the original incident")


def test_journal_backend_is_found(tmp_path):
    (tmp_path / "j").mkdir()
    (tmp_path / "j" / "jstudy_4h.log").write_text("")
    hits = S.find_study("jstudy_4h", studies_dir=tmp_path, journal=str(tmp_path / "j"))
    assert [h["backend"] for h in hits] == ["journal"]


# ── describe_backend: the other half — making the live backend visible ───────────────────────────────

def test_describe_defaults_to_sqlite():
    assert "SQLite file" in S.describe_backend("/x/wsh_4h.db")


def test_describe_reports_rdb_without_leaking_credentials(monkeypatch):
    monkeypatch.setenv(S.ENV_VAR, "postgresql://wsh:hunter2@localhost:55432/wsh")
    out = S.describe_backend("/x/wsh_4h.db")
    assert "served RDB" in out
    assert "hunter2" not in out, "storage description leaked a password into the logs"
    assert "wsh:" not in out


def test_describe_reports_journal(monkeypatch, tmp_path):
    monkeypatch.setenv(S.JOURNAL_ENV, str(tmp_path))
    assert "journal files" in S.describe_backend("/x/wsh_4h.db")
