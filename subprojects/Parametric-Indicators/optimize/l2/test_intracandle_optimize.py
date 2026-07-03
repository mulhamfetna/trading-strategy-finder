import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import optuna  # noqa: E402
from optimize.l2.optimize import suggest_l2_params  # noqa: E402

_B = {"sl_soft": [10, 50], "sl_hard": [0, 60], "tp": [20, 80]}


def test_intracandle_dims_added():
    def obj(trial):
        p = suggest_l2_params(trial, _B, 2, intracandle=True)
        assert p["l2_intracandle"] is True
        assert p["l2_intracandle_max_wait"] in (30, 60, 120, 240)
        return 0.0
    optuna.create_study().optimize(obj, n_trials=3)


def test_default_space_unchanged():
    def obj(trial):
        p = suggest_l2_params(trial, _B, 2)              # no intracandle
        assert "l2_intracandle_max_wait" not in p
        return 0.0
    optuna.create_study().optimize(obj, n_trials=2)
