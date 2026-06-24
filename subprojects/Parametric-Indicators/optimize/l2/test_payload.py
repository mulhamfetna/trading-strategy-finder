import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2 import payload


def test_validate_accepts_permissive_and_sets_window_full():
    p = payload.validate_l2_params(dict(payload.PERMISSIVE))
    assert p["window"] == "full"
    assert p["sl_soft"] == 149.8 and p["tp"] == 120.2
    assert p["cooldown"] == 0 and p["k"] == 1 and p["flip"] is False
    assert p["indicators"] == []


def test_validate_rejects_bad_params():
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": -1})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "gate_pct": 150})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": None})
    with pytest.raises(payload.L2ParamError):   # unknown indicator key -> from_specs raises -> wrapped
        payload.validate_l2_params({**payload.PERMISSIVE,
                                    "indicators": [{"key": "not_a_real_indicator", "enabled": True,
                                                    "mode": "both", "params": {}}]})


def test_l1_cache_returns_same_object():
    a = payload.run_l1_cached("4h")
    b = payload.run_l1_cached("4h")
    assert a is b
    assert len(a.ledger) == 255


def test_l1_disk_cache_survives_memory_clear():
    payload.run_l1_cached("4h")                       # warms in-memory + disk
    assert payload._l1_cache_file("4h").exists()      # persisted to the disk cache
    payload._L1_CACHE.clear()                          # drop the in-process memo
    r = payload.run_l1_cached("4h")                    # must reload from disk (no recompute)
    assert len(r.ledger) == 255


def test_save_and_load_l2_profile_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "_PROFILES", tmp_path / "l2_profiles.json")
    profs = payload.save_l2_profile("mine", dict(payload.PERMISSIVE))
    assert "mine" in profs
    assert payload.load_l2_profiles()["mine"]["tp"] == 120.2
    with pytest.raises(payload.L2ParamError):
        payload.save_l2_profile("", dict(payload.PERMISSIVE))


def test_custom_l1_differs_from_frozen_and_is_memoised():
    """run_l1_cached with a NON-lean L1 profile produces a different L1 book (proves L1 is editable),
    and is memoised in-process by params-hash."""
    frozen = payload.run_l1_cached("4h")
    custom_params = {**payload.PERMISSIVE, "gate_pct": 50, "flip": True}
    a = payload.run_l1_cached("4h", params=custom_params)
    b = payload.run_l1_cached("4h", params=dict(custom_params))
    assert a is b                                        # memoised by hash
    assert a is not frozen
    assert a.params != frozen.params                     # genuinely a different L1 profile


def test_l1_default_params_is_lean_champion_schema():
    p = payload.l1_default_params("4h")
    assert p["window"] == "full" and p["ind_1min"] is True
    assert isinstance(p["indicators"], list) and any(s.get("enabled") for s in p["indicators"])


def test_save_and_load_l1_profile_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "_L1_PROFILES", tmp_path / "l1_profiles.json")
    profs = payload.save_l1_profile("leanish", dict(payload.PERMISSIVE))
    assert "leanish" in profs and payload.load_l1_profiles()["leanish"]["tp"] == 120.2


def test_unified_l1_view_bundles_engine_payload_plus_log():
    """The unified L1 view (build_view_payload view=l1 + l1_engine=strategy params) returns the engine's
    full payload (vol/state/drawdown/events/trades) PLUS the causal per-candle log + log-derived boxes,
    and the log boxes equal the engine summary (consistent)."""
    import sys as _sys
    _sys.path.insert(0, str(_PI))
    import strategy
    sp = dict(strategy.WINNER) if hasattr(strategy, "WINNER") else None
    import config
    sp = {**config.WINNER, "timeframe": "4h", "window": "full", "indicators": [], "k": 1,
          "veto_as_flip": False, "gen": {"swing_l": 2, "golf_n": 3}, "retrace_amount": 0,
          "retrace_unit": "points", "wait_bars": 0}
    eng = payload._layer_from_strategy(sp)
    out = payload.build_view_payload(eng, {}, "4h", "l1", l1_engine=sp)
    for k in ("vol", "state", "drawdown", "events", "candles", "trades", "log"):
        assert k in out, k
    assert out["meta"]["view"] == "l1" and out["meta"]["n"] == len(out["log"])
    assert round(out["meta"]["boxes"]["pnl"]) == round(out["meta"]["summary"]["pnl"])   # log == engine


def test_layer_from_strategy_maps_core():
    import config
    sp = {**config.WINNER, "indicators": [], "k": 1}
    lp = payload._layer_from_strategy(sp)
    assert lp["window"] == "full" and lp["ind_1min"] is True and lp["sl_soft"] == config.WINNER["sl_soft"]


def test_derive_lines_short_mirrors_long():
    line = payload._derive_lines(
        {"entry_price": 1000.0, "direction": "short"},
        {"sl_soft": 10.0, "sl_hard": 20.0, "tp": 30.0})
    assert line == {"sl_hard_line": 1020.0, "sl_soft_line": 1010.0, "tp_hard_line": 970.0}


def test_dedupe_keeps_last_and_sorts():
    out = payload._dedupe([{"time": 3, "value": 1}, {"time": 1, "value": 2}, {"time": 3, "value": 9}])
    assert out == [{"time": 1, "value": 2}, {"time": 3, "value": 9}]


def test_serialize_log_row_has_all_fields():
    """verbose-logs: _serialize_log_row emits every LogRow field (23)."""
    from optimize.l2 import logbook
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    row = payload._serialize_log_row(res.log[0])
    for k in ("i","time","layer","decision","reason","box_cause","event_type","direction","box_dir",
              "entry_price","exit_time","exit_price","exit_reason","pnl","equity","dd","in_position",
              "position_owner","l2_reason","text","veto_flip","would_be_pnl","indicators"):
        assert k in row, f"missing {k}"


def test_view_payload_carries_taxonomy():
    p = payload.build_view_payload(payload.l1_default_params("4h"), dict(payload.PERMISSIVE),
                                   "4h", view="l1")
    tax = p["meta"]["taxonomy"]
    assert tax["entered"]["count"] == 255
    assert tax["n_classified"] == p["meta"]["n"] - 1
