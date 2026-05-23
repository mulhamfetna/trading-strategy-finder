"""
BoxLookup — loads the shifted weekly/monthly box CSVs and answers:
  1. Which box levels are active for a given date?
  2. Does a close price generate a LONG, SHORT, or no signal?
  3. Which specific box level fired, and what were its edges?

Signal rule:
  close > upper + tick_threshold  →  'long'
  close < lower − tick_threshold  →  'short'
  otherwise                       →  None (hold)

Both weekly AND monthly must agree on direction.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.exceptions import MissingDataFileError

# (upper_col, lower_col, label)
_WEEKLY_LEVELS: List[Tuple[str, str, str]] = [
    ('WTHU', 'WTHD', 'W-TH'),
    ('WTH1', 'WTH2', 'W-TH sub'),
    ('WRHU', 'WRHD', 'W-RH'),
    ('WIHU', 'WIHD', 'W-IH'),
    ('WILU', 'WILD', 'W-IL'),
    ('WRLU', 'WRLD', 'W-RL'),
    ('WTLU', 'WTLD', 'W-TL'),
    ('WTL1', 'WTL2', 'W-TL sub'),
]

_MONTHLY_LEVELS: List[Tuple[str, str, str]] = [
    ('MTHU', 'MTHD', 'M-TH'),
    ('MTH1', 'MTH2', 'M-TH sub'),
    ('MRHU', 'MRHD', 'M-RH'),
    ('MIHU', 'MIHD', 'M-IH'),
    ('MILU', 'MILD', 'M-IL'),
    ('MRLU', 'MRLD', 'M-RL'),
    ('MTLU', 'MTLD', 'M-TL'),
    ('MTL1', 'MTL2', 'M-TL sub'),
]

# Chart fill / border color per box label (returned as-is to frontend)
_LEVEL_COLORS: Dict[str, Tuple[str, str]] = {
    'W-TH':     ('rgba(255,152,0,0.12)',  'rgba(255,152,0,0.80)'),
    'W-TH sub': ('rgba(255,152,0,0.07)',  'rgba(255,152,0,0.50)'),
    'W-RH':     ('rgba(41,98,255,0.12)',  'rgba(41,98,255,0.80)'),
    'W-IH':     ('rgba(0,188,212,0.10)',  'rgba(0,188,212,0.70)'),
    'W-IL':     ('rgba(233,30,99,0.10)',  'rgba(233,30,99,0.70)'),
    'W-RL':     ('rgba(255,82,82,0.12)',  'rgba(255,82,82,0.80)'),
    'W-TL':     ('rgba(183,28,28,0.12)',  'rgba(183,28,28,0.80)'),
    'W-TL sub': ('rgba(183,28,28,0.07)',  'rgba(183,28,28,0.50)'),
    # Monthly: same hues, softer so weekly levels are easy to distinguish
    'M-TH':     ('rgba(255,152,0,0.06)',  'rgba(255,152,0,0.45)'),
    'M-TH sub': ('rgba(255,152,0,0.03)',  'rgba(255,152,0,0.25)'),
    'M-RH':     ('rgba(41,98,255,0.06)',  'rgba(41,98,255,0.45)'),
    'M-IH':     ('rgba(0,188,212,0.05)',  'rgba(0,188,212,0.35)'),
    'M-IL':     ('rgba(233,30,99,0.05)',  'rgba(233,30,99,0.35)'),
    'M-RL':     ('rgba(255,82,82,0.06)',  'rgba(255,82,82,0.45)'),
    'M-TL':     ('rgba(183,28,28,0.06)',  'rgba(183,28,28,0.45)'),
    'M-TL sub': ('rgba(183,28,28,0.03)',  'rgba(183,28,28,0.25)'),
}

class BoxLookup:
    """
    Load shifted box CSVs and provide per-candle signal lookup.

    Per the no-fallback rule, EVERY argument is required. Caller (the
    FastAPI endpoint or a test fixture) must supply the file paths,
    the tick threshold, and both window-day values explicitly.
    """

    def __init__(
        self,
        week_path: str,
        month_path: str,
        tick_threshold: float,
        weekly_window_days: int,
        monthly_window_days: int,
    ) -> None:
        self.tick_threshold = tick_threshold
        self.weekly_window_days = weekly_window_days
        self.monthly_window_days = monthly_window_days
        self._weekly  = self._load(week_path,  window_days=weekly_window_days)
        self._monthly = self._load(month_path, window_days=monthly_window_days)

    # ------------------------------------------------------------------
    @staticmethod
    def _load(path: str, window_days: int) -> pd.DataFrame:
        if not os.path.exists(path):
            raise MissingDataFileError(
                path,
                role='box-data',
                system_status={
                    'hint': 'Run scripts/preprocess_boxes.py first.',
                    'window_days': window_days,
                },
            )
        df = pd.read_csv(path, parse_dates=['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        df['_end'] = df['Date'] + pd.Timedelta(days=window_days)
        return df

    def _active_row(self, df: pd.DataFrame, ts: pd.Timestamp) -> Optional[pd.Series]:
        mask = (df['Date'] <= ts) & (df['_end'] > ts)
        rows = df[mask]
        return rows.iloc[-1] if not rows.empty else None

    def get_active_weekly_box(self, ts: pd.Timestamp) -> Optional[pd.Series]:
        return self._active_row(self._weekly, ts)

    def get_active_monthly_box(self, ts: pd.Timestamp) -> Optional[pd.Series]:
        return self._active_row(self._monthly, ts)

    # ------------------------------------------------------------------
    def _best_level(
        self,
        close: float,
        row: pd.Series,
        levels: List[Tuple[str, str, str]],
    ) -> Optional[Tuple[str, str, float, float]]:
        """Return (direction, label, upper, lower) for the closest firing level,
        or None if no level fires."""
        candidates: List[Tuple[float, str, str, float, float]] = []
        for upper_col, lower_col, label in levels:
            upper = row.get(upper_col)
            lower = row.get(lower_col)
            if pd.isna(upper) or pd.isna(lower):
                continue
            upper, lower = float(upper), float(lower)
            mid  = (upper + lower) / 2.0
            dist = abs(close - mid)
            if close > upper + self.tick_threshold:
                candidates.append((dist, 'long',  label, upper, lower))
            elif close < lower - self.tick_threshold:
                candidates.append((dist, 'short', label, upper, lower))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        _, direction, label, upper, lower = candidates[0]
        return direction, label, upper, lower

    # ------------------------------------------------------------------
    def get_signal(self, close: float, ts: pd.Timestamp) -> Optional[str]:
        """Return 'long', 'short', or None.
        Fires as soon as price crosses ONE box level (weekly takes priority).
        """
        weekly_row  = self.get_active_weekly_box(ts)
        monthly_row = self.get_active_monthly_box(ts)
        w = self._best_level(close, weekly_row,  _WEEKLY_LEVELS)  if weekly_row  is not None else None
        m = self._best_level(close, monthly_row, _MONTHLY_LEVELS) if monthly_row is not None else None
        if w is not None:
            return w[0]
        if m is not None:
            return m[0]
        return None

    def get_signal_detail(self, close: float, ts: pd.Timestamp) -> Dict[str, Any]:
        """Like get_signal but returns full detail for trade logging.

        Adds a `conflict` flag (FIX-21): the weekly and monthly sides fire
        independently, so they may produce opposite directions. The aggregate
        `signal` resolves the conflict by weekly-priority (see get_signal),
        but the conflict flag lets the UI label the trade with
        "weekly fired despite monthly disagreement" rather than silently
        hiding the disagreement.
        """
        weekly_row  = self.get_active_weekly_box(ts)
        monthly_row = self.get_active_monthly_box(ts)

        w = self._best_level(close, weekly_row,  _WEEKLY_LEVELS)  if weekly_row  is not None else None
        m = self._best_level(close, monthly_row, _MONTHLY_LEVELS) if monthly_row is not None else None

        w_sig   = w[0] if w else None
        m_sig   = m[0] if m else None
        signal  = w_sig if w_sig is not None else m_sig
        conflict = w_sig is not None and m_sig is not None and w_sig != m_sig

        return {
            'signal':            signal,
            'weekly_signal':     w_sig,
            'monthly_signal':    m_sig,
            'conflict':          conflict,
            'weekly_level':      w[1] if w else None,
            'monthly_level':     m[1] if m else None,
            'weekly_upper':      w[2] if w else None,
            'weekly_lower':      w[3] if w else None,
            'monthly_upper':     m[2] if m else None,
            'monthly_lower':     m[3] if m else None,
            'weekly_box_start':  str(weekly_row['Date'].date())  if weekly_row  is not None else None,
            'monthly_box_start': str(monthly_row['Date'].date()) if monthly_row is not None else None,
        }

    # ------------------------------------------------------------------
    def get_box_rects(
        self,
        start: str,
        end: str,
    ) -> List[Dict[str, Any]]:
        """Return all box-level rectangles overlapping [start, end] for chart rendering.

        Each rect: { start_time, end_time, upper, lower, level, timeframe,
                     fill_color, border_color }
        where times are unix integer seconds.
        """
        rects: List[Dict[str, Any]] = []
        start_ts = pd.Timestamp(start)
        end_ts   = pd.Timestamp(end)

        for df, levels, timeframe in [
            (self._weekly,  _WEEKLY_LEVELS,  'weekly'),
            (self._monthly, _MONTHLY_LEVELS, 'monthly'),
        ]:
            mask = (df['_end'] > start_ts) & (df['Date'] <= end_ts)
            for _, row in df[mask].iterrows():
                box_start = int(row['Date'].timestamp())
                box_end   = int(row['_end'].timestamp())
                for upper_col, lower_col, label in levels:
                    upper = row.get(upper_col)
                    lower = row.get(lower_col)
                    if pd.isna(upper) or pd.isna(lower):
                        continue
                    fill, border = _LEVEL_COLORS.get(label, ('rgba(128,128,128,0.05)', 'rgba(128,128,128,0.3)'))
                    rects.append({
                        'start_time':   box_start,
                        'end_time':     box_end,
                        'upper':        float(upper),
                        'lower':        float(lower),
                        'level':        label,
                        'timeframe':    timeframe,
                        'fill_color':   fill,
                        'border_color': border,
                    })
        return rects
