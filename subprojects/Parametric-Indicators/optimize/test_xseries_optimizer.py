"""Locks the #17 rule: cross-series indicators are excluded from the optimizer search when there is
no reference (an enabled cross-series indicator with no reference can never confirm ⇒ blocks all
entries). See optimizer.run(): ref_df is None ⇒ exclude the cross-series keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna

from indicators import library
from optimize import optimizer

XS = tuple(library.lib_xseries.SCHEMA)   # rolling_corr, rolling_beta, cointegration, pca_factor


def test_cross_series_never_enabled_when_excluded():
    def obj(trial):
        specs = optimizer._suggest_indicators(trial, exclude=XS)
        trial.set_user_attr("xs_on", sum(1 for s in specs if s["enabled"] and s["key"] in XS))
        return 0.0
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    st.optimize(obj, n_trials=80)
    assert max(t.user_attrs["xs_on"] for t in st.trials) == 0


def test_cross_series_searchable_when_not_excluded():
    # sanity: without the exclusion they CAN be enabled (so the exclude above is what gates them)
    def obj(trial):
        specs = optimizer._suggest_indicators(trial)
        trial.set_user_attr("xs_on", sum(1 for s in specs if s["enabled"] and s["key"] in XS))
        return 0.0
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    st.optimize(obj, n_trials=80)
    assert max(t.user_attrs["xs_on"] for t in st.trials) > 0
