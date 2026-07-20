"""Pure no-entry attribution + longest-run helpers (entry-pause visibility). No engine/data deps.

Decomposes why the system isn't entering, per decision bar, into:
  box_silence  — the box produced no long/short signal at all
  gate_block   — box signalled, but the volatility gate blocked it
  indic_block  — box signalled, gate passed, but an indicator vetoed OR < K confirmers
  would_enter  — gate fully open (an entry opportunity)
and reports the longest consecutive run of each (+ the longest open-position hold).
"""
from __future__ import annotations

import numpy as np


def longest_run(mask) -> int:
    """Length of the longest run of True in a boolean array."""
    best = cur = 0
    for v in np.asarray(mask, dtype=bool):
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    return int(best)


def per_bar_cause(sig, vol_gate, veto, confirm):
    """Attribute each decision bar (priority): no_signal → vol_gated → vetoed → confirm<K → would_enter.
    Returns (box_silence, gate_block, indic_block, would_enter) boolean masks."""
    sig = np.asarray(sig)
    cand = sig != 0
    vol_gate = np.asarray(vol_gate, dtype=bool)
    veto = np.asarray(veto, dtype=bool)
    confirm = np.asarray(confirm, dtype=bool)
    box_silence = ~cand
    gate_block = cand & ~vol_gate
    indic_block = cand & vol_gate & (veto | ~confirm)
    would_enter = cand & vol_gate & ~veto & confirm
    return box_silence, gate_block, indic_block, would_enter


def _dur(bars, bar_seconds) -> dict:
    secs = int(bars) * int(bar_seconds)
    return {"bars": int(bars), "seconds": secs, "hours": int(secs // 3600), "days": round(secs / 86400.0, 2)}


def pause_metrics(sig, vol_gate, veto, confirm, bar_seconds, trade_spans=None) -> dict:
    """The 4 visibility metrics. trade_spans = list of (entry_idx, exit_idx) for the position-hold figure."""
    box_silence, gate_block, indic_block, _ = per_bar_cause(sig, vol_gate, veto, confirm)
    hold_bars = max((int(b) - int(a) for a, b in (trade_spans or [])), default=0)
    return {"box_silence": _dur(longest_run(box_silence), bar_seconds),
            "gate_noentry": _dur(longest_run(gate_block), bar_seconds),
            "indicator_noentry": _dur(longest_run(indic_block), bar_seconds),
            "position_hold": _dur(hold_bars, bar_seconds)}


def pause_totals(sig, vol_gate, veto, confirm, bar_seconds, trade_spans=None) -> dict:
    """TOTAL candle counts (not longest run) for the same no-entry characters as pause_metrics, plus
    total bars spent in an open position. box_silence/gate/indicator are mutually exclusive per bar, so
    noentry_total == box_silence_total + gate_noentry_total + indicator_noentry_total. trade_spans =
    list of (entry_idx, exit_idx); position_hold_total sums their lengths."""
    box_silence, gate_block, indic_block, _ = per_bar_cause(sig, vol_gate, veto, confirm)
    bs, gb, ib = int(box_silence.sum()), int(gate_block.sum()), int(indic_block.sum())
    hold = int(sum(max(0, int(b) - int(a)) for a, b in (trade_spans or [])))
    return {"box_silence_total": _dur(bs, bar_seconds),
            "gate_noentry_total": _dur(gb, bar_seconds),
            "indicator_noentry_total": _dur(ib, bar_seconds),
            "position_hold_total": _dur(hold, bar_seconds),
            "noentry_total": _dur(bs + gb + ib, bar_seconds)}
