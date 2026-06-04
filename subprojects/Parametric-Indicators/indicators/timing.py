"""Retrace-fill entry resolver (decision #3/#5, 2026-06-04).

Retrace sets the ENTRY PRICE: as price pulls back from the signal close, each confirming indicator's
confirm goes live when the 1-minute path first reaches ITS OWN retrace level (long: signal_close−r;
short: +r). The trade fills at the **K-th confirm's level** — the level of the indicator whose
pullback completes the K rule. retrace=0 ⇒ level == signal_close ⇒ touched on the first bar ⇒
immediate fill at the signal close (parity).

This module is the pure resolver; engine wiring (entry time/price/exit-walk-start) is layered on top
with the retrace=0 ⇒ identity carve-out.
"""
from __future__ import annotations

import numpy as np


def resolve_retrace_entry(direction, signal_close, levels, m_low, m_high, m_dates, k):
    """direction: +1 long / -1 short. levels: per-confirming-indicator price levels. m_low/m_high/
    m_dates: the 1-minute path within the armed window (after the signal, before it is superseded).
    Returns (fill_time, fill_price) when the K-th distinct level is touched, else None (unfilled).

    Long: level L touched when low ≤ L; within a bar deeper levels activate later, so higher L first.
    Short: level L touched when high ≥ L; lower L first within a bar."""
    long = direction > 0
    activated = set()
    count = 0
    for b in range(len(m_dates)):
        newly = [i for i, L in enumerate(levels)
                 if i not in activated and (m_low[b] <= L if long else m_high[b] >= L)]
        # within-bar activation order = depth of pullback: long → highest level first; short → lowest
        newly.sort(key=lambda i: levels[i], reverse=long)
        for i in newly:
            activated.add(i)
            count += 1
            if count >= k:
                return (m_dates[b], levels[i])
    return None
