"""cap_1min added as an optimizer search dimension (L1 + L2) + threaded to the engine."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import optimizer as OPT


def test_cap_1min_is_a_counted_dimension():
    assert OPT.CAP_1MIN_MAX == 1440
    # force_eod=False stated explicitly: the end-of-day close became the training default on
    # 2026-07-30 (#79), which legitimately drops en_cap_eod from the searched dimensions.
    # This test describes the UNFORCED shape, so it must pin it rather than inherit it.
    d = OPT.search_dims(split_sltp=False, force_eod=False)
    assert d["base_int"] == 3                      # cooldown, k, cap_1min
    assert d["base_cat"] == 3                      # flip, en_cap_bars, en_cap_eod
    assert d["total"] == sum(v for k, v in d.items() if k != "total")
    # same pinning: d was computed unforced, so the budget must be too
    assert OPT.recommended_trials(False, per_dim=200, force_eod=False) == d["total"] * 200


def test_native_seed_carries_cap_1min():
    """'Cap off' is now encoded by the en_cap_bars switch, NOT by cap_1min==0. cap_1min is a rectangular
    dimension searched over 1..MAX and simply ignored when the switch is off, so a seed must carry an
    IN-RANGE value (0 would be rejected by Optuna as outside the distribution)."""
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    box0 = {"sl_soft": 100, "sl_hard": 150, "tp": 120, "gate_pct": 0, "dd_limit": 0,
            "cooldown": 0, "flip": False, "k": 1}
    s0 = OPT._native_seed(box0, {}, split_sltp=False, b=b)
    assert s0["en_cap_bars"] is False                             # no cap on the champion → switch off
    assert OPT.CAP_1MIN_MIN <= s0["cap_1min"] <= OPT.CAP_1MIN_MAX  # in-range placeholder, unused
    s1 = OPT._native_seed({**box0, "cap_1min": 5000}, {}, split_sltp=False, b=b)
    assert s1["en_cap_bars"] is True                              # legacy bars champion → switch on
    assert s1["cap_1min"] == OPT.CAP_1MIN_MAX                     # clamped to bound


def test_backtest_metrics_honors_cap_1min():
    """backtest_metrics threads cap_1min: a tight cap changes the result vs uncapped (cap=0)."""
    from optimize import core, data as data_mod, timeframes as TF
    from optimize.fast_engine import signals_to_int
    from optimize import signals as sig_mod
    df_dec, df1, box, vf, n_split = data_mod.load_inputs("4h")
    si = signals_to_int(sig_mod.decision_signals(df_dec, box))
    base = {"sl_soft": 149.8, "sl_hard": 178.4, "tp": 120.2, "gate_pct": 0, "dd_limit": 0,
            "cooldown": 0, "flip": False, "window": "full", "indicators": [], "k": 1, "ind_1min": False}
    m0 = core.backtest_metrics(df_dec, df1, box, vf, n_split, {**base, "cap_1min": 0},
                               TF.get("4h").bar_td, sig_int=si)
    m5 = core.backtest_metrics(df_dec, df1, box, vf, n_split, {**base, "cap_1min": 5},
                               TF.get("4h").bar_td, sig_int=si)
    assert round(m0["pnl"], 2) != round(m5["pnl"], 2)            # tight cap forces earlier exits
    assert m0 == core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(base),
                                       TF.get("4h").bar_td, sig_int=si)   # no cap key == cap=0 (off path)


def test_l2_suggest_includes_cap_1min():
    import optuna
    from optimize.l2 import optimize as L2O
    from indicators import library
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    fixed = {"sl_soft": 100.0, "sl_hard_delta": 20.0, "tp": 120.0, "gate_pct": 0.0,
             "dd_limit": 0.0, "cooldown": 0, "flip": False, "k": 1, "cap_1min": 90}
    for key in library.REGISTRY:                                  # every searched indicator param
        fixed[f"en_{key}"] = False
        for prm in library.SCHEMA[key].get("params", []):
            fixed[f"{key}_{prm['name']}"] = prm["default"]
    p = L2O.suggest_l2_params(optuna.trial.FixedTrial(fixed), b, cap=10)
    assert p["cap_1min"] == 90
