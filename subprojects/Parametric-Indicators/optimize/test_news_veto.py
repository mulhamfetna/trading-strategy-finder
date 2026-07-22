"""Tasks 3-4 — the news veto blocks entries, force-flattens, and keeps both engines in lockstep."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize import core, data, instruments, signals
from optimize import timeframes as TF
from optimize.fast_engine import signals_to_int
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals import window as W
from perf._common import champion_preset      # the wsi1m_<tf> champions, same source the golden gate uses

_BUNDLE = {}


def _run(tf="4h", inst="NQ", **over):
    """core.backtest_metrics takes SEVEN positional args; wrap it once rather than repeat the call."""
    if (tf, inst) not in _BUNDLE:
        _BUNDLE[(tf, inst)] = data.load_inputs(tf, instrument=inst)
    df_dec, df1, box, vf, n_split = _BUNDLE[(tf, inst)]
    p = dict(champion_preset(tf))
    p.update(over)
    core._clear_caches()
    return core.backtest_metrics(
        df_dec, df1, box, vf, n_split, p, TF.get(tf).bar_td,
        sig_int=signals_to_int(signals.decision_signals(df_dec, box)),
        pv=instruments.point_value(inst),
    )


# ------------------------------------------------------------------ identity (the golden contract)

def test_off_by_default_is_byte_identical():
    """news_veto absent == news_veto=False == today's numbers. If this breaks, the golden 6/6 breaks."""
    base = _run()
    off = _run(news_veto=False)
    assert base["pnl"] == off["pnl"]
    assert base["n_taken"] == off["n_taken"]
    assert base["max_dd"] == off["max_dd"]


# ------------------------------------------------------------------ entry blocking

def test_veto_removes_entries_and_never_adds_any():
    """A veto can only ever REMOVE trades. If it adds one, the mask is inverted or misaligned."""
    off = _run(news_veto=False)
    on = _run(news_veto=True)
    assert on["n_taken"] <= off["n_taken"], "the veto ADDED trades — mask is inverted"
    assert on["n_taken"] < off["n_taken"], "the veto removed nothing — mask never fires"


def test_no_entry_lands_inside_a_release_window():
    """The behavioural assertion: with the veto on, ZERO entries occur inside a window."""
    df_dec = _BUNDLE.get(("4h", "NQ"), data.load_inputs("4h"))[0]
    mask = W.release_window_mask(df_dec, rc.load_calendar(), pre_min=0, post_min=12)
    res = _run(news_veto=True, news_pre_min=0, news_post_min=12)
    entry_idx = np.array([t["entry_idx"] for t in res["trades"]], dtype=int)
    assert not mask[entry_idx].any(), "an entry fired inside a release window"


# ------------------------------------------------------------------ force-flatten + profit exemption
#
# core.backtest_metrics reduces each trade to {pnl, eq, dd, year, entry_idx} — it drops exit_reason.
# We deliberately do NOT widen that dict: the golden gate hashes the trade ledger, so adding fields
# risks breaking the very identity guarantee this feature must preserve. Instead we drive BOTH engines
# directly, which is also a truer test of what was actually changed.

import pandas as pd                                                   # noqa: E402
from engine import SimpleStrategy, SimpleStrategyParams               # noqa: E402
from optimize.fast_engine import fast_backtest                        # noqa: E402

_SS, _SH, _TP, _GP = 30, 40, 60, 60          # the "winner" case from test_fast_parity.CASES


def _both_engines(mult: float = 1.0, pre: int = 0, post: int = 12):
    """Run engine.SimpleStrategy and fast_backtest on the SAME inputs with the news veto armed.
    Returns (exact_trades, fast_trades)."""
    df, df1, box, vf, n = data.load_inputs("4h")
    cal = rc.load_calendar()
    sig = signals_to_int(signals.decision_signals(df, box))

    # the composite gate is the caller's job in this architecture (indicators/runner.py:251,
    # optimize/core.py:273): vol-gate AND NOT release-window.
    base = vf <= float(np.percentile(vf[:n], _GP))
    gate = base & ~W.release_window_mask(df, cal, pre, post)
    tgt = W.news_exit_targets(df1, cal, pre)

    sp = SimpleStrategyParams(sl_soft_points=_SS, sl_hard_points=_SH, tp_hard_points=_TP,
                              data_path_4h="", data_path_1min="", box_data_path="",
                              news_veto=True, news_pre_min=pre, news_post_min=post,
                              news_profit_exempt_mult=mult)
    E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=gate)
    E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]

    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      _SS, _SH, _TP, False,
                      news_target=tgt, news_profit_exempt_mult=mult, m_open=df1["Open"].to_numpy(float))
    return E, F


def test_force_flatten_produces_news_veto_exits():
    E, F = _both_engines(mult=1.0)
    assert any(t["exit_reason"] == "NEWS_VETO" for t in E), "exact engine never force-flattened"
    assert any(t["exit_reason"] == "NEWS_VETO" for t in F), "fast engine never force-flattened"


def test_the_profit_exemption_is_actually_applied():
    """Monotonic in the threshold. mult=0.0 exempts any trade in profit at all, so FEW are killed.
    mult=99.0 exempts almost nothing, so MANY are killed. Equal counts ⇒ the exemption is ignored."""
    _, lenient = _both_engines(mult=0.0)
    _, strict = _both_engines(mult=99.0)
    n_lenient = sum(t["exit_reason"] == "NEWS_VETO" for t in lenient)
    n_strict = sum(t["exit_reason"] == "NEWS_VETO" for t in strict)
    assert n_strict > n_lenient, \
        f"exemption ignored: mult=0 killed {n_lenient}, mult=99 killed {n_strict}"


def test_no_news_veto_exit_lands_ON_a_release_minute():
    """The spike guard, end to end. Every NEWS_VETO exit must be strictly BEFORE its release — if one
    landed on the release minute we would be eating the 8.32x bar on the way out."""
    E, _ = _both_engines(mult=1.0)
    release_times = set(rc.load_calendar()["Date"])
    bad = [t["exit_time"] for t in E
           if t["exit_reason"] == "NEWS_VETO" and pd.Timestamp(t["exit_time"]) in release_times]
    assert not bad, f"{len(bad)} NEWS_VETO exits landed ON the release minute: {bad[:3]}"


# ------------------------------------------------------------------ the parity contract

def test_both_engines_agree_trade_for_trade_with_the_veto_on():
    """optimize/test_fast_parity.py is the canonical contract; this is the news-veto case of it.
    fast_engine SKIPS bars while engine sweeps every bar, so a force-exit is exactly the kind of
    feature that can silently diverge."""
    E, F = _both_engines(mult=1.0)
    assert len(E) == len(F), f"trade count differs: exact={len(E)} fast={len(F)}"
    diffs = [
        (e["entry_time"], e["exit_reason"], f["exit_reason"])
        for e, f in zip(E, F)
        if pd.Timestamp(e["entry_time"]) != pd.Timestamp(f["entry_time"])
        or e["direction"] != f["direction"]
        or e["exit_reason"] != f["exit_reason"]
        or pd.Timestamp(e["exit_time"]) != pd.Timestamp(f["exit_time"])
        or abs(e["pnl_points"] - f["pnl_points"]) > 1e-6
    ]
    assert not diffs, f"{len(diffs)} engine/fast_engine mismatches, first 3: {diffs[:3]}"
