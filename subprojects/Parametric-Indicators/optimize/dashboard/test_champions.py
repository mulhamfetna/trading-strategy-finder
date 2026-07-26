import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import champions


def test_load_all_flattens_per_instrument_tf_and_ranks(tmp_path):
    # NQ (base file, no suffix) + ES (suffixed)
    (tmp_path / "best_champions_full.json").write_text(json.dumps({
        "4h": {"full_pnl": 148670.2, "full_dd": 12284.0, "win": 67.0, "median_pnl": 41174.7,
               "box": {"sl_soft": 128.5, "cap_mode": "bars"}, "indicators": {"macd": {}, "vwap": {}}},
        "1h": {"full_pnl": 50000.0, "full_dd": 8000.0, "win": 60.0, "median_pnl": 12000.0,
               "box": {}, "indicators": {"rsi": {}}},
    }))
    (tmp_path / "best_champions_full_ES.json").write_text(json.dumps({
        "4h": {"full_pnl": 200000.0, "full_dd": 20000.0, "win": 65.0, "median_pnl": 30000.0,
               "box": {}, "indicators": {}},
    }))
    rows = champions.load_all(results_dir=tmp_path)
    assert len(rows) == 3
    assert rows[0]["instrument"] == "ES" and rows[0]["pnl"] == 200000.0     # ranked by P/L desc
    nq4h = next(r for r in rows if r["instrument"] == "NQ" and r["tf"] == "4h")
    assert nq4h["n_indicators"] == 2 and nq4h["indicators"] == ["macd", "vwap"]
    assert nq4h["box"]["cap_mode"] == "bars" and nq4h["deployed"] is True


def test_load_all_missing_dir_is_empty(tmp_path):
    assert champions.load_all(results_dir=tmp_path / "nope") == []
