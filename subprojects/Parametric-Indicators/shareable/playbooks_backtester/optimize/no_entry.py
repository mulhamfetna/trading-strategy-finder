"""Pure no-entry-streak metric with warmup-vs-decision attribution (S0). No engine/data deps.

A "gap" is the bar-distance between consecutive entries (plus the leading gap from bar 0 to the first
entry). A gap is DECISION-phase iff its START index >= warmup_decision_bars — so any gap inside/straddling
the one-time warmup region is excluded (warmup is startup cost we do NOT optimize). The trailing gap
(last entry -> end of data) is reported but excluded from the decision figure.
"""
from __future__ import annotations


def no_entry_metrics(entry_indices, n_bars, warmup_decision_bars=0, bar_hours=4.0) -> dict:
    days = lambda bars: round(bars * bar_hours / 24.0, 3)
    idx = sorted(int(i) for i in entry_indices)
    out = {"first_entry_bar": (idx[0] if idx else None),
           "warmup_decision_bars": int(warmup_decision_bars),
           "warmup_days": days(int(warmup_decision_bars))}
    if not idx:
        out.update(max_no_entry_bars=0, max_no_entry_days=0.0,
                   max_no_entry_bars_decision=0, max_no_entry_days_decision=0.0,
                   trailing_no_entry_bars=0, trailing_no_entry_days=0.0, longest_gap_source="none")
        return out
    # (start_idx, length) for the leading gap + each between-entry gap
    gaps = [(0, idx[0])] + [(a, b - a) for a, b in zip(idx, idx[1:])]
    trailing_len = (n_bars - 1) - idx[-1]
    max_bars = max(g[1] for g in gaps)
    longest = max(gaps, key=lambda g: g[1])
    decision = [g for g in gaps if g[0] >= warmup_decision_bars]
    max_dec = max((g[1] for g in decision), default=0)
    out.update(
        max_no_entry_bars=int(max_bars), max_no_entry_days=days(max_bars),
        max_no_entry_bars_decision=int(max_dec), max_no_entry_days_decision=days(max_dec),
        trailing_no_entry_bars=int(trailing_len), trailing_no_entry_days=days(max(0, trailing_len)),
        longest_gap_source=("warmup" if longest[0] < warmup_decision_bars else "decision"))
    return out
