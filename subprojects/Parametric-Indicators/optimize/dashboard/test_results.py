import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import results


class _T:
    def __init__(self, number, values, state, constraints=None):
        self.number, self.values, self.state = number, values, state
        self.system_attrs = {"nsga3:generation": 0}
        if constraints is not None:
            self.system_attrs["constraints"] = constraints


def test_study_summary_parses_ranks_and_reads_feasibility(monkeypatch):
    import optuna
    C, P = optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.PRUNED
    trials = [
        _T(0, [1000.0, -5000.0, 55.0], C, constraints=[1.0]),    # infeasible (constraint > 0)
        _T(1, [3000.0, -400.0, 70.0], C, constraints=[-1.0]),    # feasible, best P/L
        _T(2, [2000.0, -100.0, 60.0], C, constraints=[-1.0]),    # feasible
        _T(3, None, P),                                          # pruned
    ]
    monkeypatch.setattr(results, "_load", lambda name: types.SimpleNamespace(trials=trials))
    s = results.study_summary("x")
    assert s["ok"] and s["complete"] == 3 and s["pruned"] == 1
    assert s["best_pnl"]["trial"] == 1                            # ranked by P/L
    assert s["feasible_count"] == 2 and s["best_feasible"]["trial"] == 1
    assert s["top"][0]["pnl"] == 3000.0 and s["top"][0]["feasible"] is True
    assert any(r["feasible"] is False for r in s["top"])         # infeasible trial surfaced too


def test_study_summary_unknown_study_is_safe(monkeypatch):
    def boom(name):
        raise KeyError("no such study")
    monkeypatch.setattr(results, "_load", boom)
    r = results.study_summary("nope")
    assert r["ok"] is False and "detail" in r
