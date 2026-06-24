"""Candle-classification taxonomy boxes — per-node {count, pnl?} derived STRICTLY from the per-candle
causal log (CausalResult.log). No engine touch; additive instrumentation only.

L1 tree (partition by box_cause over all rows; bar 0 has cause None and is excluded):
  no_box_signal(box_silence) | gate_rejected(vol_gated) | indicator_veto(vetoed)
  | indicator_no_confirm(confirm<K) | passed_all_gates(would_enter)
The passed_all_gates bucket splits into entered / passed_skipped(breaker_locked) / passed_in_position.
entered's trades split by exit_reason; TIME_CAP splits into win/loss.
"""
from __future__ import annotations


def _box(count, pnl=None):
    return {"count": int(count)} if pnl is None else {"count": int(count), "pnl": round(float(pnl), 2)}


_EXIT_KEYS = {"TAKE_PROFIT_HARD": "tp_exit", "STOP_LOSS_SOFT": "sl_soft_exit",
              "STOP_LOSS_HARD": "sl_hard_exit", "TIME_CAP": "time_cap_exit"}


def _exit_boxes(entries: list) -> dict:
    """{tp_exit, sl_soft_exit, sl_hard_exit, time_cap_exit, time_cap_win, time_cap_loss} from entry rows."""
    agg = {k: [0, 0.0] for k in _EXIT_KEYS}
    tcw = [0, 0.0]
    tcl = [0, 0.0]
    for r in entries:
        k = r.exit_reason
        if k in agg:
            agg[k][0] += 1
            agg[k][1] += r.pnl
        if k == "TIME_CAP":
            (tcw if r.pnl > 0 else tcl)[0] += 1
            (tcw if r.pnl > 0 else tcl)[1] += r.pnl
    out = {name: _box(agg[k][0], agg[k][1]) for k, name in _EXIT_KEYS.items()}
    out["time_cap_win"] = _box(tcw[0], tcw[1])
    out["time_cap_loss"] = _box(tcl[0], tcl[1])
    return out


def taxonomy_l1(result) -> dict:
    log = result.log

    def cnt(pred):
        return sum(1 for r in log if pred(r))

    no_box_signal = cnt(lambda r: r.box_cause == "box_silence")
    gate_rejected = cnt(lambda r: r.box_cause == "vol_gated")
    indicator_veto = cnt(lambda r: r.box_cause == "vetoed")
    indicator_no_confirm = cnt(lambda r: r.box_cause == "confirm<K")
    passed_all_gates = cnt(lambda r: r.box_cause == "would_enter")

    l1_entries = [r for r in log if r.layer == "L1" and r.decision == "entry"]
    entered = len(l1_entries)
    entered_pnl = sum(r.pnl for r in l1_entries)

    skipped_rows = [r for r in log if r.reason == "breaker_locked"]   # would_enter & flat, breaker/cooldown
    passed_skipped = len(skipped_rows)
    skipped_pnl = sum((r.would_be_pnl or 0.0) for r in skipped_rows)

    passed_in_position = passed_all_gates - entered - passed_skipped  # would_enter while a trade was open

    out = {
        "no_box_signal": _box(no_box_signal),
        "gate_rejected": _box(gate_rejected),
        "indicator_veto": _box(indicator_veto),
        "indicator_no_confirm": _box(indicator_no_confirm),
        "passed_all_gates": _box(passed_all_gates),
        "entered": _box(entered, entered_pnl),
        "passed_skipped": _box(passed_skipped, skipped_pnl),
        "passed_in_position": _box(passed_in_position),
        "n_classified": int(result.n - 1),
    }
    out.update(_exit_boxes(l1_entries))
    return out


_L2_REASON = {"vol_gated": "gate_rejected", "vetoed": "indicator_veto",
              "confirm<K": "indicator_no_confirm", "passed": "passed_no_open", "entered": "entered"}


def taxonomy_l2(result) -> dict:
    log = result.log
    l2_entries = [r for r in log if r.layer == "L2" and r.decision == "entry"]

    parts = {k: 0 for k in _L2_REASON}
    for r in log:
        if r.l2_reason in parts:
            parts[r.l2_reason] += 1

    out = {name: _box(parts[reason]) for reason, name in _L2_REASON.items() if name != "entered"}

    entered_pnl = sum(r.pnl for r in l2_entries)
    out["entered"] = _box(len(l2_entries), entered_pnl)
    out["l2_evaluated"] = _box(sum(parts.values()))

    exits = _exit_boxes(l2_entries)
    fc = [r for r in l2_entries if r.exit_reason == "L1-entry"]
    exits["l1_entry_exit"] = _box(len(fc), sum(r.pnl for r in fc))
    out.update(exits)

    l1_drops = sum(1 for r in log if r.box_cause in ("vetoed", "vol_gated"))
    out["forwarded_but_l1_in_position"] = _box(l1_drops - out["l2_evaluated"]["count"])
    out["n_classified"] = int(out["l2_evaluated"]["count"])
    return out
