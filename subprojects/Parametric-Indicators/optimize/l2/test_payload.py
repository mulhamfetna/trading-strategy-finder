import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import payload, l1_runner, engine, metrics


PERMISSIVE = dict(sl_soft=149.8, sl_hard=167.1, tp=120.2, gate_pct=0.0, dd_limit=0.0,
                  cooldown=0, flip=False, k=1, ind_1min=False, indicators=[])


def test_get_l1_caches_same_object():
    a = payload.get_l1("4h")
    b = payload.get_l1("4h")
    assert a is b                      # cached — no second ~38s run


def test_build_l2_payload_keys_and_summary_match_metrics():
    p = payload.build_l2_payload(PERMISSIVE, "4h")
    for key in ("meta", "candles", "l1_spans", "dropped", "l2_trades",
                "l2_equity", "combined_equity", "l1_equity"):
        assert key in p, f"missing {key}"

    # summary blocks equal the metrics functions on the same run
    l1 = payload.get_l1("4h")
    res = engine.run_l2(l1, PERMISSIVE)
    assert p["meta"]["summary"]["l2"] == metrics.score(res)
    assert p["meta"]["summary"]["combined"] == metrics.combined(l1, res)
    assert isinstance(p["meta"]["run_ms"], int)

    # L1 context block
    assert p["meta"]["l1"]["n_trades"] == len(l1.ledger)
    assert p["meta"]["l1"]["dropped"] == len(l1.dropped_signals)

    # series sanity
    assert len(p["candles"]) == len(l1.df_dec)
    assert p["meta"]["l1"]["dropped"] == len(p["dropped"])
    assert all(t["l2_dir_vs_box"] in ("agree", "oppose") for t in p["l2_trades"])
    assert all(set(c) == {"time", "open", "high", "low", "close"} for c in p["candles"][:3])


def test_l2_trades_carry_computed_sl_tp_lines():
    p = payload.build_l2_payload(PERMISSIVE, "4h")
    if p["l2_trades"]:
        t = p["l2_trades"][0]
        for k in ("sl_soft_line", "sl_hard_line", "tp_hard_line"):
            assert k in t
        # long: tp above entry, sl below; short: mirrored
        if t["direction"] == "long":
            assert t["tp_hard_line"] > t["entry_price"] > t["sl_hard_line"]
        else:
            assert t["tp_hard_line"] < t["entry_price"] < t["sl_hard_line"]
