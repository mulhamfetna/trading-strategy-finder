"""β unit lock — ablate_indicators (enumeration, param-builder, row shape, ranking). Engine mocked."""
import warnings
warnings.filterwarnings("ignore")
from optimize import ablate_indicators as AB


def test_enumerate_256():
    champ = AB.load_champion("4h")
    subs = AB.subsets(champ["enabled_keys"])
    assert len(champ["enabled_keys"]) == 8
    assert len(subs) == 256 and len(set(subs)) == 256
    assert frozenset() in subs and frozenset(champ["enabled_keys"]) in subs


def test_build_params_masks_enabled():
    champ = AB.load_champion("4h")
    keep = frozenset(list(champ["enabled_keys"])[:3])
    p = AB.build_params(champ, keep)
    on = {s["key"] for s in p["indicators"] if s["enabled"]}
    assert on == set(keep)
    assert p["ind_1min"] is True and p["sl_soft"] == champ["box"]["sl_soft"]


def test_eval_row_shape(monkeypatch):
    champ = AB.load_champion("4h")
    monkeypatch.setattr(AB, "_evaluate_full", lambda params: {
        "pnl": 100.0, "max_dd": 10.0, "win": 70.0, "pf": 1.5, "n_taken": 5,
        "max_no_entry_days_decision": 2.0, "max_no_entry_days": 2.0, "longest_gap_source": "decision",
        "warmup_days": 0.1, "data_footprint_candles": 346})
    row = AB.eval_subset(champ, frozenset(list(champ["enabled_keys"])[:2]))
    assert row["n_indicators"] == 2 and set(row["kept"]) <= set(champ["enabled_keys"])
    assert {"pnl", "max_dd", "win", "decision_pause_days", "data_footprint_candles", "kept"} <= set(row)


def test_rank_and_marginal():
    base = {"kept": ["a", "b"], "n_indicators": 2, "dropped": [], "pnl": 100.0, "max_dd": 10.0,
            "win": 70.0, "pf": 1.5, "n_taken": 5, "decision_pause_days": 2.0, "overall_pause_days": 2.0,
            "pause_source": "decision", "warmup_days": 0.1, "data_footprint_candles": 300}
    drop_one = dict(base, kept=["a"], n_indicators=1, dropped=["b"], pnl=98.0)
    ranked = AB.rank([dict(base), dict(drop_one)], baseline_pnl=100.0, drop_bonus=5000.0)
    assert ranked[0]["kept"] == ["a"]                  # 98 + 5000 > 100 ⇒ dropping 1 wins
    assert ranked[0]["delta_pnl_pct"] == -2.0
    marg = AB.marginal_impact([dict(base), dict(drop_one)], ["a", "b"])
    assert "b" in marg and "avg_drop_cost" in marg["b"]
