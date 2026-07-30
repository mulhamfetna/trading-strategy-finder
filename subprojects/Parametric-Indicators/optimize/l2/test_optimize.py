import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import optimize as l2opt, l1_runner

PERMISSIVE = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
              "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


def test_windows_split_in_sample_and_oos():
    r = l1_runner.run_l1("4h")
    w = l2opt.WINDOWS(r)
    assert w["in"] == (0, r.n_split)
    assert w["oos"] == (r.n_split, len(r.df_dec))


def test_score_window_in_sample_vs_oos():
    r = l1_runner.run_l1("4h")
    w = l2opt.WINDOWS(r)
    s_in = l2opt.score_window(r, dict(PERMISSIVE), *w["in"])
    s_oos = l2opt.score_window(r, dict(PERMISSIVE), *w["oos"])
    for s in (s_in, s_oos):
        assert {"pnl", "max_dd", "n", "win"} <= set(s)
    assert s_in["n"] > 0 and s_oos["n"] > 0        # both periods have dropped signals
    from optimize.l2 import engine
    full = engine.run_l2(r, dict(PERMISSIVE))
    assert s_in["n"] + s_oos["n"] == len(full.ledger)


# A SMOKE test proves the study runs and returns the right shape — it is not a search. Scoping it to a
# few cheap indicators is what keeps that true: with the full 165-indicator registry on the 1-minute
# frame this test stopped finishing at all (#80), spinning at ~100% CPU for 30+ minutes and stalling
# every run of `pytest optimize/l2/` — which silently removed ~120 tests from any "run everything" check.
# The registry grew 18 -> 165 and nothing re-derived what a "small study" costs.
_SMOKE_INDS = ("ema_trend", "rsi", "macd")


def test_run_small_study_smoke(tmp_path):
    db = tmp_path / "l2v1_smoke.db"
    res = l2opt.run(n_trials=3, study_prefix="l2v1smoke", seed=1, min_trades=1,
                    storage_url=f"sqlite:///{db}", only_inds=_SMOKE_INDS)
    assert res["n_trials"] >= 1
    assert "champion" in res
    if res["champion"] is not None:                # feasible winner found in the 3 trials
        c = res["champion"]
        assert {"pnl", "max_dd", "n", "win"} <= set(c["in_sample"])
        assert {"pnl", "max_dd", "n", "win"} <= set(c["oos"])
        assert "indicators" in c["params"] and c["params"]["ind_1min"] is True


def test_export_champion_writes_json(tmp_path):
    champ = {"params": dict(PERMISSIVE),
             "in_sample": {"pnl": 1.0, "max_dd": 2.0, "n": 3, "win": 50.0},
             "oos": {"pnl": -1.0, "max_dd": 4.0, "n": 2, "win": 0.0}}
    p = l2opt._export_champion(champ, "4h", tmp_path)
    assert p.exists()
    import json as _j
    d = _j.loads(p.read_text())
    assert d["tf"] == "4h" and d["in_sample"]["n"] == 3 and d["oos"]["pnl"] == -1.0
    assert d["prefix"] == "l2v1" and d["params"]["tp"] == 120.2     # params round-trip intact


def test_contributor_committee_excludes_smc_by_default():
    """SMC indicators are dropped from the cross-instrument committee SEARCH (speed) — present but forced
    OFF and never suggested as Optuna dimensions; non-SMC keys ARE searched."""
    import optuna
    study = optuna.create_study()
    trial = study.ask()
    c = l2opt._suggest_contributor(trial, "ES")
    by_key = {s["key"]: s for s in c["committee"]}
    for k in l2opt.SMC_COMMITTEE_KEYS:
        assert by_key[k]["enabled"] is False                       # SMC forced OFF
        assert f"es_en_{k}" not in trial.params                    # and NOT a search dimension
    assert "es_en_ema_trend" in trial.params                       # a non-SMC key IS searched


def test_contributor_committee_includes_smc_when_opted_in():
    import optuna
    study = optuna.create_study()
    trial = study.ask()
    l2opt._suggest_contributor(trial, "ES", exclude_committee=())
    assert "es_en_ifvg" in trial.params and "es_en_breaker" in trial.params  # SMC searched on opt-in
