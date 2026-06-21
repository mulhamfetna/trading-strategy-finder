"""F4 — validate L2 split long/short SL/TP semantics (evidence the lever is correct + meaningful, not
just "it runs"). Documented semantics (see FOLLOWUPS_unified_dashboard.md F4):
  1. split applies to a trade's FINAL (post-flip) direction — long trades use long_*, short use short_*
     (fast_backtest's rule; shared fallback when a side is None);
  2. force_close_on_l1_entry takes PRIORITY — a force-closed L2 trade exits at the L1-entry bar close,
     regardless of its SL/TP, so split never corrupts a force-closed exit;
  3. the DISPLAYED lines (_derive_lines) are per-side too, so the chart matches the actual exit.
"""
import json
import sys
from pathlib import Path

import numpy as np

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import engine, payload

_L2_CHAMP = _PI / "optimize" / "results" / "l2v1_4h_champion.json"


def _ledger_key(led):
    return [(round(t["pnl"], 4), int(t["entry_idx"]), t["direction"]) for t in led]


def test_l2_split_changes_the_l2_book():
    """Asymmetric per-side TP must change the L2 ledger (the lever is LIVE on the L2 layer, not inert)."""
    l1 = payload.run_l1_cached("4h")
    champ = json.loads(_L2_CHAMP.read_text())["params"]
    base = engine.run_l2(l1, champ)
    split = engine.run_l2(l1, {**champ, "long_tp": 30, "short_tp": 200})
    assert _ledger_key(base.ledger) != _ledger_key(split.ledger), "L2 split SL/TP had no effect"


def test_l2_force_close_exits_at_bar_close_not_sltp():
    """Semantics #2: every L1-entry-forced L2 exit happens at that decision bar's CLOSE — independent of
    SL/TP/split. Proven by exit_price == the decision-frame close at exit_time."""
    l1 = payload.run_l1_cached("4h")
    champ = json.loads(_L2_CHAMP.read_text())["params"]
    res = engine.run_l2(l1, {**champ, "long_tp": 25, "short_tp": 25})   # split ON
    dates = l1.df_dec["Date"].to_numpy()
    close = l1.df_dec["Close"].to_numpy(float)
    forced = [t for t in res.ledger if t.get("exit_reason") == "L1-entry"]
    assert forced, "expected at least one force-closed L2 trade"
    for t in forced:
        j = int(np.searchsorted(dates, np.datetime64(t["exit_time"]), side="left"))
        assert abs(float(t["exit_price"]) - close[j]) < 1e-6, "force-close did not exit at the bar close"


def test_derive_lines_split_is_per_side_and_falls_back():
    base = {"sl_soft": 10, "sl_hard": 20, "tp": 30}
    # no split → both sides use the shared values (behavior-preserving)
    assert payload._derive_lines({"entry_price": 1000, "direction": "long"}, base)["tp_hard_line"] == 1030
    assert payload._derive_lines({"entry_price": 1000, "direction": "short"}, base)["tp_hard_line"] == 970
    # split → LONG uses long_tp, SHORT uses short_tp; neither leaks to the other side
    p = {**base, "long_tp": 5, "short_tp": 50}
    assert payload._derive_lines({"entry_price": 1000, "direction": "long"}, p)["tp_hard_line"] == 1005
    assert payload._derive_lines({"entry_price": 1000, "direction": "short"}, p)["tp_hard_line"] == 950
    # a side left None falls back to shared even when the other side is overridden
    p2 = {**base, "long_tp": 5}
    assert payload._derive_lines({"entry_price": 1000, "direction": "short"}, p2)["tp_hard_line"] == 970
