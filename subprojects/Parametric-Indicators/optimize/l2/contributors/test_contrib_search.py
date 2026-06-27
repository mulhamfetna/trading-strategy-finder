import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import optuna
from optimize import optimizer as OPT


def test_suggest_indicators_prefix_namespaces_param_names():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t, prefix="es_")
    names = set(t.params)
    assert "es_en_ema_trend" in names and "es_ema_trend_fast" in names
    assert "en_ema_trend" not in names           # the default namespace is untouched


def test_prefix_default_is_unchanged():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t)
    assert "en_ema_trend" in t.params and "es_en_ema_trend" not in t.params
