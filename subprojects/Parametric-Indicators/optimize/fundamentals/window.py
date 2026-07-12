"""Measure the volatility envelope around scheduled releases; build the masks the engines consume.

Two products:
  1. measure_envelope / derive_bounds  — the window is MEASURED from the data, never chosen. We do
     not pick "15 minutes each side" because 15 is a round number; we ask the data when the
     disturbance actually starts and when it actually decays.
  2. release_window_mask / news_exit_targets — what the engines actually eat.

ALIGNMENT CONTRACT (mirrors indicators/runner.py:188): the decision-frame mask is ENTRY-BAR aligned.
mask[idx] describes the bar you would ENTER on; its signal came from bar idx-1. mask[0] is always
False. Getting this shift wrong introduces look-ahead.

SELF-VALIDATION: measure_envelope doubles as the calendar's proof. If a FRED release_id or an
Eastern clock time in fetch_calendar.py were wrong, the measured spike would not land on offset 0
and optimize/test_release_window.py::test_envelope_peaks_at_offset_zero fails.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def measure_envelope(df1: pd.DataFrame, cal: pd.DataFrame,
                     pre: int = 60, post: int = 60) -> pd.DataFrame:
    """Mean absolute 1-minute return at each minute-offset from a release, vs the all-day baseline.

    Returns a frame indexed by offset_min in [-pre, +post] with columns
    ['mean_abs_ret_bp', 'baseline_bp', 'ratio', 'n'].
      mean_abs_ret_bp : average |1-min return| in basis points at that offset
      baseline_bp     : the same statistic over ALL minutes (the "normal minute")
      ratio           : mean_abs_ret_bp / baseline_bp  -- 1.0 == an ordinary minute
      n               : how many releases actually had a bar at that offset
    """
    close = df1["Close"].to_numpy(dtype=np.float64)
    ret_bp = np.zeros(len(close), dtype=np.float64)
    ret_bp[1:] = np.abs(np.diff(close) / close[:-1]) * 10_000.0   # basis points
    baseline = float(ret_bp[1:].mean())

    minute_index = pd.Index(df1["Date"])
    rows = []
    for off in range(-pre, post + 1):
        stamps = cal["Date"] + pd.Timedelta(minutes=off)
        pos = minute_index.get_indexer(stamps)          # -1 where that minute does not exist
        pos = pos[pos >= 0]
        m = float(ret_bp[pos].mean()) if len(pos) else float("nan")
        rows.append({"offset_min": off, "mean_abs_ret_bp": m, "baseline_bp": baseline,
                     "ratio": m / baseline, "n": len(pos)})
    return pd.DataFrame(rows).set_index("offset_min")


def derive_bounds(env: pd.DataFrame, threshold: float = 1.5) -> tuple[int, int]:
    """The contiguous run of elevated volatility that brackets offset 0.

    pre_min  = minutes BEFORE the release that volatility is already elevated.
    post_min = minutes AFTER  the release that it stays elevated.

    Raises if offset 0 itself is not elevated — that means the calendar timestamps are wrong, and
    silently returning (0, 0) would hide it.
    """
    hot = env["ratio"] >= threshold
    if not bool(hot.get(0, False)):
        raise ValueError(
            f"offset 0 has ratio {env.loc[0, 'ratio']:.2f} < {threshold} — the release minute is "
            "not unusually volatile, so the calendar timestamps are almost certainly wrong"
        )

    pre_min = 0
    while (-(pre_min + 1)) in hot.index and bool(hot[-(pre_min + 1)]):
        pre_min += 1
    post_min = 0
    while (post_min + 1) in hot.index and bool(hot[post_min + 1]):
        post_min += 1
    return pre_min, post_min


def _window_edges(cal: pd.DataFrame, pre_min: int, post_min: int):
    starts = (cal["Date"] - pd.Timedelta(minutes=pre_min)).to_numpy(dtype="datetime64[ns]")
    ends = (cal["Date"] + pd.Timedelta(minutes=post_min)).to_numpy(dtype="datetime64[ns]")
    return starts, ends


def release_window_mask(df_dec: pd.DataFrame, cal: pd.DataFrame,
                        pre_min: int, post_min: int) -> np.ndarray:
    """bool[len(df_dec)] — True where a NEW ENTRY must be blocked. Entry-bar aligned.

    A decision bar is 'in a release window' if its own timestamp falls inside one. We then shift by
    one bar (out[1:] = raw[:-1]; out[0] = False) so the flag lands on the bar you would ENTER on --
    the same convention as indicators/runner.py:188. Without the shift we would be acting on a bar
    that has not closed yet: look-ahead.
    """
    n = len(df_dec)
    raw = np.zeros(n, dtype=bool)
    if len(cal) == 0:
        return raw                      # identity: no releases, no blocking

    d = df_dec["Date"].to_numpy(dtype="datetime64[ns]")
    starts, ends = _window_edges(cal, pre_min, post_min)
    for s, e in zip(starts, ends):
        raw |= (d >= s) & (d <= e)

    out = np.zeros(n, dtype=bool)
    out[1:] = raw[:-1]
    out[0] = False
    return out


def news_exit_targets(df1: pd.DataFrame, cal: pd.DataFrame, pre_min: int) -> np.ndarray:
    """int64[len(df1)] — for each 1-min bar, the index of the NEXT window-open at or after it, or -1.

    The engines force-flatten AT the window open, not inside it: once the storm has started we are
    already too late. -1 means 'no release ahead of this bar' => no forced exit.

    Mirrors the shape of optimize/trading_days.py::eod_targets, which is the template this whole
    feature follows.
    """
    n = len(df1)
    tgt = np.full(n, -1, dtype=np.int64)
    if len(cal) == 0:
        return tgt                      # identity

    m = df1["Date"].to_numpy(dtype="datetime64[ns]")
    starts, _ = _window_edges(cal, pre_min, 0)
    # first 1-min bar at or after each window open
    open_idx = np.searchsorted(m, starts, side="left")
    open_idx = np.unique(open_idx[(open_idx >= 0) & (open_idx < n)])
    if len(open_idx) == 0:
        return tgt

    # for every bar, the next window-open at or after it
    pos = np.searchsorted(open_idx, np.arange(n), side="left")
    valid = pos < len(open_idx)
    tgt[valid] = open_idx[pos[valid]]
    return tgt


def envelope_at_clock_time(df1: pd.DataFrame, hhmm: str, weekday_only: bool = True) -> float:
    """Diagnostic for the ISM gap (see fetch_calendar.py).

    Our calendar has no 10:00 events, because FRED does not carry ISM and we refuse to guess its
    dates. This answers the question that gap raises: is 10:00 unusually volatile ANYWAY? If it is,
    we are leaving something on the table and should source ISM properly. If it is not, the gap is
    costing us nothing.

    Returns the ratio of the mean |1-min return| at `hhmm` to the all-minute baseline.
    """
    close = df1["Close"].to_numpy(dtype=np.float64)
    ret_bp = np.zeros(len(close), dtype=np.float64)
    ret_bp[1:] = np.abs(np.diff(close) / close[:-1]) * 10_000.0
    baseline = float(ret_bp[1:].mean())

    t = df1["Date"]
    # np.array(..., copy=True): pandas hands back a read-only view, and `&=` needs a writable buffer.
    sel = np.array((t.dt.strftime("%H:%M") == hhmm).to_numpy(), dtype=bool, copy=True)
    if weekday_only:
        sel &= np.asarray(t.dt.weekday < 5, dtype=bool)
    return float(ret_bp[sel].mean() / baseline) if sel.any() else float("nan")
