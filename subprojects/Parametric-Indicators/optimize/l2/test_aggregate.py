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
    champ = json.load(open(str(_PI / "optimize/results/l2v2_4h_champion.json")))["params"]
    res = logbook.run_causal(payload.l1_default_params("4h"), champ, "4h")
    b = aggregate.boxes_for_layer(res, "L2", bar_seconds=_BS)
    # l2v2 champion (reverse-entry-only engine, re-opt 2026-06-22)
    assert b["n_taken"] == 34 and round(b["pnl"]) == 25383 and round(b["max_dd"]) == 7136
    # L2 taxonomy is from L2's OWN perspective (l2_reason), not L1's box_cause:
    # L2 never sees box_silence (it only acts on box signals L1 dropped), so its box_silence_total is 0.
    assert b["box_silence_total"]["bars"] == 0
    # L2's totals invariant still holds and L2 evaluated some bars (gate/indicator counts are real)
    assert b["noentry_total"]["bars"] == (b["gate_noentry_total"]["bars"]
        + b["indicator_noentry_total"]["bars"])


def test_combined_boxes_apply_per_box_rules():
    import json
    import numpy as np
    from optimize.l2 import l1_runner, engine, metrics
    champ = json.load(open(str(_PI / "optimize/results/l2v1_4h_champion.json")))["params"]
    res = logbook.run_causal(payload.l1_default_params("4h"), champ, "4h")
    c = aggregate.combined_boxes(res, bar_seconds=_BS)
    l1 = aggregate.boxes_for_layer(res, "L1", _BS)
    l2 = aggregate.boxes_for_layer(res, "L2", _BS)
    # SUM boxes (no layer tag)
    assert c["pnl"]["value"] == round(l1["pnl"] + l2["pnl"], 2) and "layer" not in c["pnl"]
    assert c["n_taken"]["value"] == l1["n_taken"] + l2["n_taken"]
    assert c["n_candidates"]["value"] == l1["n_candidates"] + l2["n_candidates"]
    assert c["n_locks"]["value"] == l1["n_locks"] + l2["n_locks"]
    assert c["uplift"]["value"] == round(l2["pnl"], 2)
    # max_dd RECOMPUTED from merged exit-ordered equity == legacy metrics.combined oracle (not a loose bound)
    legacy_l1 = l1_runner.run_l1("4h")
    legacy_l2 = engine.run_l2(legacy_l1, champ)
    assert round(c["max_dd"]["value"]) == round(metrics.combined(legacy_l1, legacy_l2)["max_dd"])
    assert c["max_dd"]["value"] <= round(l1["max_dd"] + l2["max_dd"], 2) + 1e-6
    # win/pf recomputed from the COMBINED trade set
    entries = [r for r in res.log if r.decision == "entry"]
    wins = [r.pnl for r in entries if r.pnl > 0]
    losses = [r.pnl for r in entries if r.pnl < 0]
    assert c["win"]["value"] == round(100 * len(wins) / max(len(entries), 1), 1)
    assert c["pf"]["value"] == (round(sum(wins) / abs(sum(losses)), 2) if losses else None)
    # payoff ratio = avg win / |avg loss|, recomputed from the COMBINED trade set
    exp_payoff = (round((sum(wins) / len(wins)) / abs(sum(losses) / len(losses)), 2)
                  if wins and losses else None)
    assert c["payoff"]["value"] == exp_payoff
    # per-layer boxes also carry payoff (avg win / |avg loss|)
    for bx in (l1, l2):
        assert "payoff" in bx
    # MAX boxes tagged with the producing layer
    assert c["noentry_streak_n"]["value"] == max(l1["noentry_streak_n"], l2["noentry_streak_n"])
    assert c["noentry_streak_n"]["layer"] in ("L1", "L2") and c["warmup"]["layer"] in ("L1", "L2")
    # guardrails kept; totals deferred from combined
    for k in ("l1_only_dd", "uplift", "dd_not_worse", "n_l1_entry_exits"):
        assert k in c
    assert not any(k.endswith("_total") for k in c)


def test_log_to_csv_has_layer_and_reason_columns():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    header, rows = aggregate.log_to_csv(res.log)
    assert header[:4] == ["i", "time", "layer", "decision"]
    assert "reason" in header and "box_cause" in header
    assert len(rows) == res.n
    # the layer column lets L1/L2 be separated downstream
    li = header.index("layer")
    assert {r[li] for r in rows} <= {"L1", "L2", ""}


def test_log_to_csv_has_all_verbose_columns_and_json_indicators():
    """verbose-logs: CSV header carries all 23 columns; the indicators cell is JSON."""
    import json as _json
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    header, rows = aggregate.log_to_csv(res.log)
    for col in ("entry_price", "exit_price", "text", "veto_flip", "would_be_pnl", "indicators"):
        assert col in header, f"CSV missing {col}"
    ind_i = header.index("indicators")
    cells = [r[ind_i] for r in rows if r[ind_i] not in ("", "[]")]
    assert cells and isinstance(_json.loads(cells[0]), list), "indicators cell not JSON list"
