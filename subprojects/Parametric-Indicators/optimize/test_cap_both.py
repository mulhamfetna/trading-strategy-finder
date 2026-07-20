"""Two independent time caps, searched by the optimizer, that coexist as 'whichever fires first'.

The search asks three questions (mirroring the indicator pattern):
    en_cap_bars : use a max-hold bar cap?   -> cap_1min : how many traded 1-min bars
    en_cap_eod  : force-close at end of trading day?

Encoded on the wire as the existing `cap_mode` field, now with a fourth value:
    none | bars | eod | both        ("both" = exit at the bar deadline OR end-of-day, whichever is sooner)

These tests pin the two failure modes that make a cap campaign meaningless:

1. THE SILENT DROP. optimize/core.py (which scores EVERY optimizer trial) called fast_backtest with an
   explicit kwarg list that omitted cap_mode / eod_target / session_last. So a trial could be RECORDED as
   en_cap_eod=True while being SCORED with no EOD cap at all -- and be deployed as an "EOD champion" that
   was never once evaluated as one. No error, no warning.

2. ENGINE DISAGREEMENT. engine.py applies the bar cap (:350) and the EOD cap (:354) as independent checks,
   so it already exits at whichever lands first. fast_engine treated them as exclusive and ignored cap_1min
   whenever EOD was on. The only pre-existing EOD parity test runs with the bar cap OFF, so the corner we
   now want to search was exactly the untested one where the two engines diverged.
"""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np  # noqa: E402

from optimize import optimizer as OPT  # noqa: E402
from optimize.fast_engine import fast_backtest  # noqa: E402


# ---------------------------------------------------------------- fast engine: "both" = whichever first

def _synthetic(cap_1min, cap_mode, eod_bar):
    """3 decision bars (entry at 1-min bar e=1); 10 flat 1-min bars, so only a cap can ever exit."""
    d_dates = np.array([0, 60, 120], dtype="int64").astype("datetime64[s]")
    d_close = np.array([100.0, 100.0, 100.0])
    sig = np.array([1, 0, 0], dtype=np.int64)
    m_dates = np.arange(0, 600, 60).astype("datetime64[s]")     # 10 bars
    m = np.full(10, 100.0)
    eod_target = np.full(10, eod_bar, dtype=np.int64)
    session_last = np.full(10, 9, dtype=np.int64)
    return fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                         sl_soft=50, sl_hard=90, tp=90, flip=False,
                         cap_1min=cap_1min, cap_mode=cap_mode,
                         eod_target=eod_target, session_last=session_last, m_open=m)


def test_both_takes_the_bar_cap_when_it_lands_first():
    # entry at global bar 1. bar cap = 2 bars -> exits at global bar 2. EOD target = bar 7 (later).
    tr = _synthetic(cap_1min=2, cap_mode="both", eod_bar=7)
    assert len(tr) == 1
    assert tr[0]["exit_reason"] == "TIME_CAP"
    assert np.datetime64(tr[0]["exit_time"]) == np.datetime64(120, "s")   # global bar 2


def test_both_takes_end_of_day_when_it_lands_first():
    # bar cap = 8 bars (would exit at global bar 8), EOD target = bar 3 -> EOD wins.
    tr = _synthetic(cap_1min=8, cap_mode="both", eod_bar=3)
    assert len(tr) == 1
    assert tr[0]["exit_reason"] == "END_OF_DAY"
    assert np.datetime64(tr[0]["exit_time"]) == np.datetime64(180, "s")   # global bar 3


def test_both_ties_resolve_to_the_bar_cap():
    # both deadlines land on global bar 4 -> engine.py checks the bar cap first, so TIME_CAP wins.
    tr = _synthetic(cap_1min=4, cap_mode="both", eod_bar=4)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "TIME_CAP"


def test_eod_alone_ignores_the_bar_cap():
    # cap_mode='eod' means EOD ONLY: cap_1min must not fire, even though it is set and lands earlier.
    tr = _synthetic(cap_1min=2, cap_mode="eod", eod_bar=6)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "END_OF_DAY"


def test_bars_alone_ignores_end_of_day():
    tr = _synthetic(cap_1min=2, cap_mode="bars", eod_bar=3)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "TIME_CAP"


def test_backcompat_bare_cap_1min_is_still_a_bars_cap():
    """The golden depends on this: cap_1min>0 with no cap_mode == a bars cap."""
    tr = _synthetic(cap_1min=2, cap_mode="none", eod_bar=3)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "TIME_CAP"


# ---------------------------------------------------------------- core.py must SCORE what it RECORDS

def _real_inputs():
    from optimize import data as data_mod
    from optimize.fast_engine import signals_to_int
    from optimize import signals as sig_mod
    df_dec, df1, box, vf, n_split = data_mod.load_inputs("4h")
    si = signals_to_int(sig_mod.decision_signals(df_dec, box))
    return df_dec, df1, box, vf, n_split, si


_BASE = {"sl_soft": 149.8, "sl_hard": 178.4, "tp": 120.2, "gate_pct": 0, "dd_limit": 0,
         "cooldown": 0, "flip": False, "window": "full", "indicators": [], "k": 1, "ind_1min": False}


def test_core_scores_eod_not_silently_uncapped():
    """THE REGRESSION TEST. cap_mode='eod' must actually change the score. Before the fix, core.py dropped
    cap_mode on the floor, so this was byte-identical to the uncapped run."""
    from optimize import core, timeframes as TF
    df_dec, df1, box, vf, n_split, si = _real_inputs()
    bar = TF.get("4h").bar_td
    off = core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                {**_BASE, "cap_1min": 0, "cap_mode": "none"}, bar, sig_int=si)
    eod = core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                {**_BASE, "cap_1min": 0, "cap_mode": "eod"}, bar, sig_int=si)
    assert round(off["pnl"], 2) != round(eod["pnl"], 2), \
        "cap_mode='eod' did not change the score -> core.py is dropping it (trials would be scored uncapped)"


def test_core_scores_all_four_cap_modes_distinctly():
    """Every mode must reach the scorer as itself. core.py returns reduced trade dicts (no timestamps),
    so the 'whichever first' ORDERING is pinned by the synthetic fast-engine tests and the engine↔fast
    parity test above; what matters here is that none of the four collapses onto another — a collapse is
    the signature of a dropped/ignored cap param."""
    from optimize import core, timeframes as TF
    df_dec, df1, box, vf, n_split, si = _real_inputs()
    bar = TF.get("4h").bar_td

    def pnl(cap_1min, cap_mode):
        m = core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                  {**_BASE, "cap_1min": cap_1min, "cap_mode": cap_mode}, bar, sig_int=si)
        return round(m["pnl"], 2)

    off = pnl(0, "none")
    bars = pnl(600, "bars")
    eod = pnl(0, "eod")
    both = pnl(600, "both")
    assert len({off, bars, eod, both}) == 4, \
        f"cap modes collapsed onto each other (none={off} bars={bars} eod={eod} both={both})"


def test_core_absent_cap_mode_is_byte_identical_to_before():
    """Golden safety: no cap keys at all must behave exactly as cap_1min=0 / cap_mode absent."""
    from optimize import core, timeframes as TF
    df_dec, df1, box, vf, n_split, si = _real_inputs()
    bar = TF.get("4h").bar_td
    a = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(_BASE), bar, sig_int=si)
    b = core.backtest_metrics(df_dec, df1, box, vf, n_split,
                              {**_BASE, "cap_1min": 0, "cap_mode": "none"}, bar, sig_int=si)
    assert a == b


# ---------------------------------------------------------------- engine <-> fast parity, BOTH caps on

def test_engine_fast_parity_with_both_caps_on():
    """The corner the two engines silently disagreed on. Trade-for-trade parity, both caps active."""
    import pandas as pd
    from engine import SimpleStrategy, SimpleStrategyParams
    from optimize import data as data_mod, trading_days
    from optimize.fast_engine import signals_to_int
    from optimize import signals as sig_mod

    df_dec, df1, box, _vf, _n = data_mod.load_inputs("4h")
    si = signals_to_int(sig_mod.decision_signals(df_dec, box))
    MD = df1["Date"].to_numpy()
    et, sl_arr = trading_days.eod_targets(MD, 15)

    CAP = 600
    sp = SimpleStrategyParams(sl_soft_points=60, sl_hard_points=120, tp_hard_points=150,
                              data_path_4h="", data_path_1min="", box_data_path="",
                              flip_entry_direction=False,
                              cap_1min=CAP, cap_mode="both", eod_margin_min=15)
    E0, _ = SimpleStrategy(sp).backtest(df_dec, df1, box, entry_gate=None)
    E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]

    F = fast_backtest(df_dec["Date"].to_numpy(), df_dec["Close"].to_numpy(float), si, None,
                      MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), 60, 120, 150, False,
                      cap_1min=CAP, cap_mode="both", eod_target=et, session_last=sl_arr, m_open=df1["Open"].to_numpy(float))

    assert len(E) == len(F) and len(F) > 0
    diffs = sum(1 for e, f in zip(E, F)
                if pd.Timestamp(e["entry_time"]) != pd.Timestamp(f["entry_time"])
                or e["direction"] != f["direction"] or e["exit_reason"] != f["exit_reason"]
                or pd.Timestamp(e["exit_time"]) != pd.Timestamp(f["exit_time"])
                or abs(e["pnl_points"] - f["pnl_points"]) > 1e-6)
    assert diffs == 0, f"{diffs} engine/fast mismatches with both caps on"
    # both cap kinds must actually fire, or the test proves nothing
    reasons = {t["exit_reason"] for t in F}
    assert "TIME_CAP" in reasons and "END_OF_DAY" in reasons, f"caps never fired: {reasons}"


# ---------------------------------------------------------------- search space

def test_cap_switches_are_counted_dimensions():
    d = OPT.search_dims(split_sltp=False)
    assert d["base_cat"] == 3            # flip, en_cap_bars, en_cap_eod
    assert d["base_int"] == 3            # cooldown, k, cap_1min
    assert d["total"] == sum(v for k, v in d.items() if k != "total")


def test_optimizer_derives_cap_mode_from_the_two_switches():
    assert OPT.derive_cap_mode(False, False) == "none"
    assert OPT.derive_cap_mode(True, False) == "bars"
    assert OPT.derive_cap_mode(False, True) == "eod"
    assert OPT.derive_cap_mode(True, True) == "both"


def test_native_seed_carries_cap_mode():
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    box0 = {"sl_soft": 100, "sl_hard": 150, "tp": 120, "gate_pct": 0, "dd_limit": 0,
            "cooldown": 0, "flip": False, "k": 1}
    s0 = OPT._native_seed(box0, {}, split_sltp=False, b=b)
    assert s0["en_cap_bars"] is False and s0["en_cap_eod"] is False     # no cap -> both switches off
    s1 = OPT._native_seed({**box0, "cap_1min": 400}, {}, split_sltp=False, b=b)
    assert s1["en_cap_bars"] is True and s1["en_cap_eod"] is False      # legacy bars champion
    s2 = OPT._native_seed({**box0, "cap_1min": 400, "cap_mode": "both"}, {}, split_sltp=False, b=b)
    assert s2["en_cap_bars"] is True and s2["en_cap_eod"] is True
