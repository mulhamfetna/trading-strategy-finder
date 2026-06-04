"""TDD — retrace-fill entry resolver (K-th confirm's level)."""
import numpy as np

from indicators.timing import resolve_retrace_entry


def test_long_k1_fills_at_first_touched_level():
    # S=100, levels 98 & 95; price descends; K=1 -> first touch (98) on bar 11
    out = resolve_retrace_entry(+1, 100.0, [98.0, 95.0],
                                m_low=[99, 97, 94], m_high=[100, 99, 96], m_dates=[10, 11, 12], k=1)
    assert out == (11, 98.0)


def test_long_k2_fills_at_second_level():
    out = resolve_retrace_entry(+1, 100.0, [98.0, 95.0],
                                m_low=[99, 97, 94], m_high=[100, 99, 96], m_dates=[10, 11, 12], k=2)
    assert out == (12, 95.0)


def test_long_same_bar_orders_by_depth():
    # bar 11 touches both 98 and 95; deeper (95) activates after 98
    out1 = resolve_retrace_entry(+1, 100.0, [98.0, 95.0],
                                 m_low=[99, 94], m_high=[100, 99], m_dates=[10, 11], k=1)
    out2 = resolve_retrace_entry(+1, 100.0, [98.0, 95.0],
                                 m_low=[99, 94], m_high=[100, 99], m_dates=[10, 11], k=2)
    assert out1 == (11, 98.0)
    assert out2 == (11, 95.0)


def test_retrace_zero_fills_immediately_at_signal_close():
    # level == signal close ⇒ touched on bar 0 ⇒ immediate fill at S (parity behaviour)
    out = resolve_retrace_entry(+1, 100.0, [100.0],
                                m_low=[99.5], m_high=[100.5], m_dates=[10], k=1)
    assert out == (10, 100.0)


def test_unfilled_returns_none():
    out = resolve_retrace_entry(+1, 100.0, [90.0],
                                m_low=[99, 98, 97], m_high=[100, 99, 98], m_dates=[10, 11, 12], k=1)
    assert out is None


def test_short_fills_on_rally():
    out = resolve_retrace_entry(-1, 100.0, [102.0, 105.0],
                                m_low=[99, 101, 104], m_high=[101, 103, 106], m_dates=[10, 11, 12], k=1)
    assert out == (11, 102.0)
