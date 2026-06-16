"""α unit lock — objective swap + indicator scope. Run: python3 -m pytest optimize/test_alpha_objective.py -q"""
import warnings; warnings.filterwarnings("ignore")
import inspect
import optuna
from optimize import optimizer as O


def test_run_has_objective_default_winrate():
    sig = inspect.signature(O.run).parameters
    assert "objective" in sig and sig["objective"].default == "winrate"
    assert "exclude_inds" in sig and "only_inds" in sig


def test_suggest_indicators_only_whitelist():
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler())
    specs = O._suggest_indicators(st.ask(), only=("cci", "order_block", "structure_trend"))
    searched = {s["key"] for s in specs if s["_searched"]}
    assert searched == {"cci", "order_block", "structure_trend"}
    # everything else is forced OFF
    assert all(s["enabled"] is False for s in specs if not s["_searched"])


def test_suggest_indicators_exclude_blacklist():
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler())
    specs = O._suggest_indicators(st.ask(), exclude=("ifvg", "breaker", "cisd"))
    searched = {s["key"] for s in specs if s["_searched"]}
    assert not ({"ifvg", "breaker", "cisd"} & searched)        # the 3 new votes are NOT searched
    assert {"cci", "ema_trend"} <= searched                    # wsh4-era keys still searched


def test_default_searches_all():
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler())
    specs = O._suggest_indicators(st.ask())
    assert all(s["_searched"] for s in specs) and len(specs) == len(O.library.REGISTRY)
