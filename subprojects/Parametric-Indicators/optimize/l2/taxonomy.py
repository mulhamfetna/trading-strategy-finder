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


def taxonomy_l1(result) -> dict:
    log = result.log

    def cnt(pred):
        return sum(1 for r in log if pred(r))

    no_box_signal = cnt(lambda r: r.box_cause == "box_silence")
    gate_rejected = cnt(lambda r: r.box_cause == "vol_gated")
    indicator_veto = cnt(lambda r: r.box_cause == "vetoed")
    indicator_no_confirm = cnt(lambda r: r.box_cause == "confirm<K")
    passed_all_gates = cnt(lambda r: r.box_cause == "would_enter")

    out = {
        "no_box_signal": _box(no_box_signal),
        "gate_rejected": _box(gate_rejected),
        "indicator_veto": _box(indicator_veto),
        "indicator_no_confirm": _box(indicator_no_confirm),
        "passed_all_gates": _box(passed_all_gates),
        "n_classified": int(result.n - 1),
    }
    return out
