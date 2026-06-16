"""
BoxLookup — loads the unified box CSV (NQ_full_data.csv) and answers:
  1. Which box levels are active for a given candle?
  2. Does a close price generate a LONG, SHORT, or HOLD signal via traversal?
  3. Which specific box level fired, and what were its edges?

Data model (v4+, 2026-05-24):
  Single file with one row per market day (the CLOSING day). Both weekly
  and monthly levels live on the same row (W* and M* columns). Daily (D*)
  columns exist in the raw file but are ignored at load time.

  NQ session cycle (New York time):
    18:00 (day D-1)  →  SESSION OPENS
    17:00 (day D)    →  SESSION CLOSES
    17:00–18:00      →  closed (no trade)

  Candle → box date mapping (_candle_to_box_date):
    candle.hour ≥ 18  →  box_date = candle.date + 1 day
    candle.hour < 18  →  box_date = candle.date
  (17:00–18:00 bars never appear in the NQ_4h data per empirical check.)

Traversal signal rule (v3.1+, 2026-05-23):
  Per (box_row_id, level_name) the lookup tracks:
    - state ∈ {'above', 'below', None}  — last observed side
    - inside_seen: bool                 — has 'inside' been observed since state was last set?

  A signal fires only when the close TRAVERSES the box — meaning:
    1. State was 'above'/'below'
    2. 'inside' was observed at least once since state was set
    3. The current close is on the OPPOSITE side

    above → inside → below : 'short'  (price came down THROUGH the box)
    below → inside → above : 'long'   (price came up THROUGH the box)

  Gap-skips (above → below with no intervening 'inside') do NOT fire — they
  update the state silently. Same-side repeats, transient inside bars, and
  first observations all return 'hold'.

  Every level on the active row is evaluated on every bar so multi-level
  (stacked-box) signals don't get stranded behind a "closest level" pick.

  Aggregate signal uses weekly priority (weekly wins over monthly).
  Returns 'long', 'short', or 'hold' when at least one side is active,
  else None (no active box for either timeframe).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# self-contained shim (was src.exceptions) — standalone subproject
class ConfigurationError(Exception):
    pass


class MissingDataFileError(Exception):
    pass

# (upper_col, lower_col, label)
_WEEKLY_LEVELS: List[Tuple[str, str, str]] = [
    ('WTHU', 'WTHD', 'W-TH'),
    ('WTH2', 'WTH1', 'W-TH sub'),
    ('WRHU', 'WRHD', 'W-RH'),
    ('WIHU', 'WIHD', 'W-IH'),
    ('WILU', 'WILD', 'W-IL'),
    ('WRLU', 'WRLD', 'W-RL'),
    ('WTLU', 'WTLD', 'W-TL'),
    ('WTL1', 'WTL2', 'W-TL sub'),
]

_MONTHLY_LEVELS: List[Tuple[str, str, str]] = [
    ('MTHU', 'MTHD', 'M-TH'),
    ('MTH2', 'MTH1', 'M-TH sub'),
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
    Load the unified box CSV and provide per-candle signal lookup.

    Per the no-fallback rule, EVERY argument is required. Caller (the
    FastAPI endpoint or a test fixture) must supply the file path and the
    tick threshold explicitly.
    """

    def __init__(
        self,
        unified_path: str,
        tick_threshold: float,
    ) -> None:
        self.tick_threshold = tick_threshold
        self._df = self._load(unified_path)
        # Per-(row_id, level_name) traversal state machine.
        # row_id is the pandas Timestamp of the box row's 'Date' field.
        # state ∈ {'above', 'below'}. Missing key == None (haven't observed).
        self._state: Dict[Tuple[pd.Timestamp, str], str] = {}
        # Per-(row_id, level_name): has 'inside' been observed since the
        # state was last set? Required for the traversal rule — a transition
        # only fires if the price ENTERED the box (saw 'inside') between
        # the two opposite-side observations. Defaults to False; reset to
        # False whenever state is set (entry side recorded).
        self._inside_seen: Dict[Tuple[pd.Timestamp, str], bool] = {}

    def reset_state(self) -> None:
        """Clear the traversal state. Idempotent — safe to call repeatedly.
        Call at the start of each backtest run (or each walk-forward fold)
        so state does not leak between runs. After this call, the next
        observation of any (row, level) is treated as the first observation."""
        self._state = {}
        self._inside_seen = {}

    # ------------------------------------------------------------------
    @staticmethod
    def _load(path: str) -> pd.DataFrame:
        """Load unified box CSV, keeping only Date + W* + M* columns.

        Daily (D*) columns and Scraped_At are dropped at parse time — they
        are ignored throughout the codebase. The Date column is normalised
        to midnight and used as the lookup key.
        """
        if not os.path.exists(path):
            raise MissingDataFileError(
                path,
                role='box-data',
                system_status={
                    'hint': 'Place NQ_full_data.csv in the project root.',
                },
            )
        keep = {'Date'}
        for u, l, _ in _WEEKLY_LEVELS + _MONTHLY_LEVELS:
            keep.add(u)
            keep.add(l)
        df = pd.read_csv(
            path,
            usecols=lambda c: c in keep,
            parse_dates=['Date'],
        )
        df = df.sort_values('Date').reset_index(drop=True)
        # Normalise Date to midnight so _candle_to_box_date keys match.
        df['Date'] = df['Date'].dt.normalize()
        return df.set_index('Date', drop=False)

    @staticmethod
    def _candle_to_box_date(ts: pd.Timestamp) -> pd.Timestamp:
        """Map a candle timestamp to its box closing day (the Date tag in the CSV).

        NQ sessions run 18:00 (day D-1) → 17:00 (day D). The CSV tags
        each row with D (the closing day). Candles with hour ≥ 18 have
        started the NEXT session and belong to the following day's box.

        The CSV index is always tz-naive. Strip any timezone from `ts` so
        the lookup key always matches — a tz-aware timestamp would produce
        a tz-aware key that silently misses every row in the index.
        """
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        if ts.hour >= 18:
            return (ts + pd.Timedelta(days=1)).normalize()
        return ts.normalize()

    def _active_row(self, ts: pd.Timestamp) -> Optional[pd.Series]:
        """Return the box row whose closing day matches the candle's session.

        Raises nothing on a miss — returns None when the date is absent
        from the CSV (data gap or candle outside the CSV date range).
        """
        box_date = self._candle_to_box_date(ts)
        try:
            row = self._df.loc[box_date]
            # If the index has duplicate dates (shouldn't happen), take last.
            return row.iloc[-1] if isinstance(row, pd.DataFrame) else row
        except KeyError:
            return None

    def get_active_weekly_box(self, ts: pd.Timestamp) -> Optional[pd.Series]:
        return self._active_row(ts)

    def get_active_monthly_box(self, ts: pd.Timestamp) -> Optional[pd.Series]:
        return self._active_row(ts)

    # ------------------------------------------------------------------
    def _classify(self, close: float, upper: float, lower: float) -> str:
        """Classify a close relative to a box's edges.
        Returns 'above', 'below', or 'inside' (within +/- tick_threshold of the edges).

        Raises ConfigurationError when the box geometry is invalid
        (`upper <= lower`) — no silent fallback; the box CSV must be fixed
        upstream (typically by re-running `scripts/preprocess_boxes.py`)."""
        if upper <= lower:
            raise ConfigurationError(
                f'Box edges are malformed: upper={upper} lower={lower}. '
                f'Each box must have upper > lower (positive height).',
                code='malformed-box-geometry',
                system_status={
                    'upper': upper,
                    'lower': lower,
                    'tick_threshold': self.tick_threshold,
                    'hint': 'Inspect the active box CSV row; re-run scripts/preprocess_boxes.py if the data was corrupted.',
                },
            )
        if close > upper + self.tick_threshold:
            return 'above'
        if close < lower - self.tick_threshold:
            return 'below'
        return 'inside'

    def _step_level(
        self,
        close: float,
        row_date: pd.Timestamp,
        label: str,
        upper: float,
        lower: float,
    ) -> Tuple[str, str]:
        """Advance the per-(row, level) state machine by one bar.
        Returns (signal, side) where:
          - signal ∈ {'long', 'short', 'hold'}
          - side   ∈ {'above', 'below', 'inside'} — classification THIS bar
        """
        side = self._classify(close, upper, lower)
        key = (row_date, label)
        prev_state = self._state.get(key)

        if side == 'inside':
            # Inside is the "entered the box" observation. Mark it so a
            # later opposite-side close counts as a real traversal. State
            # itself is unchanged — the state holds the LAST side observed
            # outside the box.
            if prev_state is not None:
                self._inside_seen[key] = True
            return 'hold', side

        if prev_state is None:
            # First observation — record entry side; no fire.
            self._state[key] = side
            self._inside_seen[key] = False
            return 'hold', side

        if prev_state == side:
            # Same outside side. State doesn't change. Note: if price had
            # dipped into the box and exited back the same side, inside_seen
            # is True — we keep it True so a LATER opposite-side close still
            # counts as a traversal off the inside observation. The user's
            # spec ("stayed inside the box in both situations is considered
            # hold") supports this: only the OPPOSITE-side exit fires.
            return 'hold', side

        # Opposite-side transition. Fire only if 'inside' was observed
        # between the state-set and now (the box was actually entered).
        if not self._inside_seen.get(key, False):
            # Gap-skip — update state silently, no fire.
            self._state[key] = side
            return 'hold', side

        signal = 'short' if prev_state == 'above' else 'long'
        self._state[key] = side
        self._inside_seen[key] = False
        return signal, side

    def _best_level(
        self,
        close: float,
        row: pd.Series,
        levels: List[Tuple[str, str, str]],
    ) -> Optional[Tuple[str, str, float, float, str]]:
        """Evaluate the traversal state machine for EVERY level on the row,
        then choose ONE level to report (the firing level if any traversal
        fired this bar, otherwise the closest level by mid-distance for HOLD).

        Returns (signal, label, upper, lower, side), or None only when no
        level has both edges present in `row`.
        """
        results: List[Tuple[str, str, float, float, str, float]] = []
        row_date = row['Date']
        for upper_col, lower_col, label in levels:
            upper = row.get(upper_col)
            lower = row.get(lower_col)
            if pd.isna(upper) or pd.isna(lower):
                continue
            upper, lower = float(upper), float(lower)
            mid = (upper + lower) / 2.0
            dist = abs(close - mid)
            signal, side = self._step_level(close, row_date, label, upper, lower)
            results.append((signal, label, upper, lower, side, dist))

        if not results:
            return None

        # Firing level (if any) wins. Multiple traversals on the same bar
        # are tie-broken by closest mid-distance.
        firing = [r for r in results if r[0] in ('long', 'short')]
        if firing:
            firing.sort(key=lambda x: x[5])
            sig, label, upper, lower, side, _ = firing[0]
            return sig, label, upper, lower, side

        # No traversal fired — report the closest level for HOLD context.
        results.sort(key=lambda x: x[5])
        sig, label, upper, lower, side, _ = results[0]
        return sig, label, upper, lower, side

    # ------------------------------------------------------------------
    def get_signal(self, close: float, ts: pd.Timestamp) -> Optional[str]:
        """Return 'long', 'short', 'hold', or None.

        - 'long' / 'short': a traversal fired on this bar (weekly priority).
        - 'hold': at least one timeframe has an active box but no traversal fired.
        - None: neither weekly nor monthly has an active box row (data gap).

        NOTE: This call mutates the internal state machine. Call exactly once
        per (close, ts) per backtest run. Use `reset_state()` between runs.
        """
        weekly_row  = self.get_active_weekly_box(ts)
        monthly_row = self.get_active_monthly_box(ts)
        w = self._best_level(close, weekly_row,  _WEEKLY_LEVELS)  if weekly_row  is not None else None
        m = self._best_level(close, monthly_row, _MONTHLY_LEVELS) if monthly_row is not None else None
        if w is None and m is None:
            return None
        w_sig = w[0] if w else None
        m_sig = m[0] if m else None
        # Weekly priority: if weekly fired a directional signal, use it.
        if w_sig in ('long', 'short'):
            return w_sig
        if m_sig in ('long', 'short'):
            return m_sig
        # Neither fired a traversal; at least one side has an active row → 'hold'.
        return 'hold'

    def get_signal_detail(self, close: float, ts: pd.Timestamp) -> Dict[str, Any]:
        """Like get_signal but returns full detail for trade logging.

        Returned `signal` is 'long' / 'short' / 'hold' when at least one side
        has an active box row, else None (no active row anywhere — data gap).

        Per-side `weekly_signal` / `monthly_signal` is 'long' / 'short' / 'hold'
        when that side has an active row, else None.

        `conflict = True` when weekly and monthly fire opposite *directional*
        signals on the same bar.

        NOTE: This call mutates the internal state machine. Call exactly once
        per (close, ts) per backtest run. Use `reset_state()` between runs.
        """
        weekly_row  = self.get_active_weekly_box(ts)
        monthly_row = self.get_active_monthly_box(ts)

        w = self._best_level(close, weekly_row,  _WEEKLY_LEVELS)  if weekly_row  is not None else None
        m = self._best_level(close, monthly_row, _MONTHLY_LEVELS) if monthly_row is not None else None

        w_sig = w[0] if w else None
        m_sig = m[0] if m else None

        # Aggregate: weekly priority for directional fires; otherwise 'hold'
        # if at least one side is active; else None (no active row anywhere).
        if w_sig in ('long', 'short'):
            signal: Optional[str] = w_sig
        elif m_sig in ('long', 'short'):
            signal = m_sig
        elif w_sig is not None or m_sig is not None:
            signal = 'hold'
        else:
            signal = None

        conflict = (
            w_sig in ('long', 'short')
            and m_sig in ('long', 'short')
            and w_sig != m_sig
        )

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
            'weekly_side':       w[4] if w else None,
            'monthly_side':      m[4] if m else None,
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

        Consecutive rows with identical price values for a level are merged
        into a single rectangle. Each session's start_time is 18:00 on the
        day before its Date tag; end_time is 17:00 on its Date tag.
        """
        rects: List[Dict[str, Any]] = []
        start_ts = pd.Timestamp(start)
        end_ts   = pd.Timestamp(end)

        # Filter rows whose session overlaps [start_ts, end_ts].
        # Session D runs: (D-1 18:00) .. (D 17:00).  A row is in range when
        # D-1 < end_ts AND D >= start_ts (i.e. Date > start_ts - 1 day).
        df = self._df
        # Use sort_index() — the Date index is already ordered and using
        # sort_values('Date') would be ambiguous because 'Date' exists as
        # both index name and column when drop=False (raises ValueError on
        # pandas ≥ 1.5).
        in_range = df[
            (df['Date'] > start_ts - pd.Timedelta(days=1)) &
            (df['Date'] <= end_ts + pd.Timedelta(days=1))
        ].sort_index()

        for levels_list, timeframe in [
            (_WEEKLY_LEVELS,  'weekly'),
            (_MONTHLY_LEVELS, 'monthly'),
        ]:
            for upper_col, lower_col, label in levels_list:
                if upper_col not in in_range.columns or lower_col not in in_range.columns:
                    continue
                sub = in_range[[upper_col, lower_col, 'Date']].dropna(
                    subset=[upper_col, lower_col]
                ).copy()
                if sub.empty:
                    continue

                # Group consecutive rows with identical price values.
                # A gap > 4 calendar days starts a new group even if values
                # are the same (handles multi-week coincidences).
                sub['_new_grp'] = (
                    (sub[upper_col] != sub[upper_col].shift(1)) |
                    (sub[lower_col] != sub[lower_col].shift(1)) |
                    (sub['Date'].diff() > pd.Timedelta(days=4))
                )
                sub['_grp'] = sub['_new_grp'].cumsum()

                fill, border = _LEVEL_COLORS[label]
                for _, grp in sub.groupby('_grp', sort=False):
                    upper = float(grp[upper_col].iloc[0])
                    lower = float(grp[lower_col].iloc[0])
                    first_date = grp['Date'].iloc[0]
                    last_date  = grp['Date'].iloc[-1]
                    # Session start = 18:00 on (first_date - 1 day).
                    # midnight - 6h  = 18:00 previous calendar day.
                    box_start = int((first_date - pd.Timedelta(hours=6)).timestamp())
                    # Session end = 17:00 on last_date.
                    box_end   = int((last_date + pd.Timedelta(hours=17)).timestamp())
                    rects.append({
                        'start_time':   box_start,
                        'end_time':     box_end,
                        'upper':        upper,
                        'lower':        lower,
                        'level':        label,
                        'timeframe':    timeframe,
                        'fill_color':   fill,
                        'border_color': border,
                    })
        return rects
