"""boxes_for_layer + log_to_csv — boxes derived strictly from the per-candle log, matching the legacy
standalone-dashboard box values."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import logbook, aggregate, payload

_BS = 4 * 3600


def test_l1_boxes_from_log_match_known_values():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    b = aggregate.boxes_for_layer(res, "L1", bar_seconds=_BS)
    assert round(b["pnl"]) == 149989 and b["n_taken"] == 255
    assert round(b["max_dd"]) == 15491
    # totals computed from box_cause over ALL bars (incl. in-position) — matches legacy pause_totals
    assert b["box_silence_total"]["bars"] == 1290
    assert b["noentry_total"]["bars"] == (b["box_silence_total"]["bars"]
        + b["gate_noentry_total"]["bars"] + b["indicator_noentry_total"]["bars"])
    # no-entry streak matches the standalone box (35 signals from 2025-04-02)
    assert b["noentry_streak_n"] == 35 and b["noentry_streak_start"] == "2025-04-02"
    # warmup/indicator_req config-derived and positive (lean champion uses 1-min indicators)
    assert b["warmup"]["bars"] > 0 and b["indicator_req"]["bars"] == b["warmup"]["bars"]
    # exposure = n_taken / (n_taken + n_skipped); locks from engine counts
    assert b["n_candidates"] >= b["n_taken"] and 0 <= b["exposure"] <= 100


def test_l2_boxes_from_log_for_champion():
    import json
    champ = json.load(open(str(_PI / "optimize/results/l2v1_4h_champion.json")))["params"]
    res = logbook.run_causal(payload.l1_default_params("4h"), champ, "4h")
    b = aggregate.boxes_for_layer(res, "L2", bar_seconds=_BS)
    assert b["n_taken"] == 80 and round(b["pnl"]) == 78391 and round(b["max_dd"]) == 8961


def test_log_to_csv_has_layer_and_reason_columns():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    header, rows = aggregate.log_to_csv(res.log)
    assert header[:4] == ["i", "time", "layer", "decision"]
    assert "reason" in header and "box_cause" in header
    assert len(rows) == res.n
    # the layer column lets L1/L2 be separated downstream
    li = header.index("layer")
    assert {r[li] for r in rows} <= {"L1", "L2", ""}
