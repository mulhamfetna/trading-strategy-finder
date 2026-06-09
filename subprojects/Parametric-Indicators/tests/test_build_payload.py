"""TDD — build_payload indicator wiring: parity when off, behaviour when on, strict validation."""
import copy
import pytest

import strategy
from strategy import ParamError


@pytest.fixture(scope="module")
def inputs():
    try:
        return strategy.load_inputs()
    except Exception as e:
        pytest.skip(f"market data unavailable: {e}")


BASE = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=60, dd_limit=2000,
            cooldown=20, flip=False, window="full")


def _run(inputs, **over):
    p = copy.deepcopy(BASE); p.update(over)
    return strategy.build_payload(*inputs, params=p)


def test_no_indicators_key_is_unchanged(inputs):
    base = _run(inputs)
    with_empty = _run(inputs, indicators=[], k=1)
    assert base["meta"]["summary"] == with_empty["meta"]["summary"]


def test_disabled_indicator_matches_baseline(inputs):
    base = _run(inputs)
    off = _run(inputs, indicators=[{"key": "rsi", "enabled": False}], k=1)
    assert base["meta"]["summary"]["n_taken"] == off["meta"]["summary"]["n_taken"]
    assert base["meta"]["summary"]["pnl"] == off["meta"]["summary"]["pnl"]


def test_enabled_veto_reduces_or_equals_trades(inputs):
    base = _run(inputs)
    veto = _run(inputs, indicators=[{"key": "adx", "enabled": True, "mode": "veto",
                                     "params": {"threshold": 25}}], k=1)
    assert veto["meta"]["summary"]["n_taken"] <= base["meta"]["summary"]["n_taken"]


def test_k_exceeds_confirmers_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[{"key": "rsi", "enabled": True, "mode": "confirm"}], k=3)


def test_unknown_indicator_key_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[{"key": "nope", "enabled": True}], k=1)


def test_bad_k_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[], k=0)


def test_entry_events_carry_vote_attribution(inputs):
    out = _run(inputs, indicators=[{"key": "rsi", "enabled": True, "mode": "confirm"},
                                   {"key": "adx", "enabled": False, "mode": "veto"}], k=1)
    entries = [e for e in out["events"] if e["type"] == "ENTRY"]
    assert entries, "expected entries"
    e0 = entries[0]
    assert "indicators" in e0
    by = {r["key"]: r for r in e0["indicators"]}
    assert "rsi" in by and "adx" in by                # ALL indicators logged (decision #1)
    assert by["rsi"]["active"] == 1 and by["adx"]["active"] == 0   # disabled still logged, active=0
    assert by["rsi"]["vote"] in ("confirm", "veto", "neutral")
    assert "confirm" in e0["text"] or "veto" in e0["text"]         # attribution summary in the line


def test_no_indicators_no_attribution(inputs):
    base = _run(inputs)
    entries = [e for e in base["events"] if e["type"] == "ENTRY"]
    assert entries and all("indicators" not in e for e in entries)


def test_smc_indicator_produces_generation_report(inputs):
    out = _run(inputs, indicators=[{"key": "fvg", "enabled": True, "mode": "confirm"}], k=1,
               gen={"swing_l": 2, "golf_n": 3})
    rep = out["meta"]["gen_report"]
    assert rep is not None and rep["params"] == {"swing_l": 2, "golf_n": 3}
    assert "n_bull_fvg" in rep and rep["bars"] > 0


# --- WS-I dashboard timeframe support ---------------------------------------------------

def test_timeframe_defaults_to_4h_and_matches_legacy(inputs):
    """Omitting timeframe ⇒ 4h ⇒ the parity-locked winner summary (back-compat)."""
    out = _run(inputs)
    assert out["meta"]["params"]["timeframe"] == "4h"
    s = out["meta"]["summary"]
    assert s["pnl"] == 7735.0 and round(s["max_dd"]) == 3670 and s["n_taken"] == 66


def test_explicit_4h_equals_default(inputs):
    assert _run(inputs)["meta"]["summary"] == _run(inputs, timeframe="4h")["meta"]["summary"]


def test_bad_timeframe_rejected(inputs):
    with pytest.raises(ParamError):
        _run(inputs, timeframe="3m")


@pytest.mark.parametrize("tf", ["2h", "1h", "15m"])
def test_other_timeframes_run_and_echo(tf):
    """Non-4h timeframes load their own decision frame and produce a coherent payload."""
    try:
        bundle = strategy.get_bundle(tf)
    except Exception as e:
        pytest.skip(f"timeframe data unavailable: {e}")
    p = copy.deepcopy(BASE); p["timeframe"] = tf
    out = strategy.build_payload(*bundle, params=p)
    assert out["meta"]["params"]["timeframe"] == tf
    assert len(out["candles"]) == len(bundle[0])          # one candle per decision bar
    assert out["meta"]["summary"]["n_candidates"] >= 0    # ran without error


# --- NOENTRY logging: dropped signals are logged, not silently discarded ----------------

def test_noentry_events_logged_for_veto_and_gate(inputs):
    """A veto-capable indicator + an active vol gate ⇒ some box signals are dropped and must appear
    as NOENTRY events (reason in the text), without becoming trades or touching the summary."""
    out = _run(inputs, gate_pct=60,
               indicators=[{"key": "adx", "enabled": True, "mode": "veto"}], k=1)
    ne = [e for e in out["events"] if e["type"] == "NOENTRY"]
    assert ne, "expected some NOENTRY (dropped-signal) events"
    assert all(e["text"].startswith("ENTRY NOT TAKEN") for e in ne)
    assert any("veto" in e["text"] for e in ne) or any("volatility gate" in e["text"] for e in ne)
    # NOENTRY is logs-only: never a trade, never in the ledger
    ne_ts = {e["time"] for e in ne}
    assert not (ne_ts & {t["entry_time"] for t in out["trades"]})


def test_noentry_does_not_change_summary(inputs):
    """Turning on the diagnostic log must not alter P/L, maxDD or trade count (it only adds events)."""
    out = _run(inputs)                      # default winner box, gate on
    s = out["meta"]["summary"]
    assert s["pnl"] == 7735.0 and round(s["max_dd"]) == 3670 and s["n_taken"] == 66


# --- indicator warm-up: wait for the look-back (and its dependencies) before voting -----------

def test_indicator_neutral_during_warmup():
    """An indicator votes NEUTRAL for its first warmup_bars bars (composites = max/stack of parts),
    then may vote. ema_trend(fast=20, slow=50) ⇒ warmup 50."""
    import numpy as np
    from indicators import library
    from indicators.base import IndicatorConfig, MarketContext
    n = 200
    close = np.linspace(100, 200, n)              # clean uptrend ⇒ would confirm long once warmed
    ctx = MarketContext(open=close, high=close + 1, low=close - 1, close=close,
                        volume=np.ones(n), session_id=np.zeros(n, dtype=int))
    box_dir = np.ones(n, dtype=np.int8)           # box says long every bar
    ind = library.build("ema_trend", IndicatorConfig(enabled=True, mode="confirm",
                                                     params={"fast": 20, "slow": 50}))
    assert ind.warmup_bars() == 50
    v = ind.vote(ctx, box_dir)
    assert (v[:50] == 0).all(), "must be neutral through the warm-up window"
    assert (v[50:] != 0).any(), "must vote after warming up"


def test_warmup_events_logged(inputs):
    out = _run(inputs, indicators=[{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                    "params": {"fast": 20, "slow": 50}}], k=1)
    warm = [e for e in out["events"] if e["type"] == "WARMUP"]
    done = [e for e in out["events"] if e["type"] == "WARMED"]
    assert warm and done
    assert "WARMING UP" in warm[0]["text"] and "ema_trend" in warm[0]["text"]
    assert "EMA(20)" in warm[0]["text"] and "EMA(50)" in warm[0]["text"]   # names the dependency
