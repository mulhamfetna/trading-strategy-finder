import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna

from optimize import optimizer


def test_max_enabled_caps_active_indicators():
    def obj(trial):
        specs = optimizer._suggest_indicators(trial, max_enabled=3)
        n_on = sum(1 for s in specs if s["enabled"])
        trial.set_user_attr("n_on", n_on)
        return float(n_on)
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    st.optimize(obj, n_trials=60)
    assert max(t.user_attrs["n_on"] for t in st.trials) <= 3


def test_no_cap_when_max_enabled_none():
    # Without a cap, at least one trial should enable more than 3 (sanity that the cap is what limits).
    def obj(trial):
        specs = optimizer._suggest_indicators(trial, max_enabled=None)
        trial.set_user_attr("n_on", sum(1 for s in specs if s["enabled"]))
        return 0.0
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    st.optimize(obj, n_trials=60)
    assert max(t.user_attrs["n_on"] for t in st.trials) > 3
