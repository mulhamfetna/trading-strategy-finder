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


def test_run_small_study_smoke(tmp_path):
    db = tmp_path / "l2v1_smoke.db"
    res = l2opt.run(n_trials=3, study_prefix="l2v1smoke", seed=1, min_trades=1,
                    storage_url=f"sqlite:///{db}")
    assert res["n_trials"] >= 1
    assert "champion" in res
    if res["champion"] is not None:                # feasible winner found in the 8 trials
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
