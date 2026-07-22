"""Simple backtest engine — Stage 1 entry + dual-SL/TP exit on 1-min bars.

Single exit model (2026-06-22): `flip_entry_direction` only REVERSES the entry
direction (long↔short); the exit logic is identical either way.

  Entry direction:
    - flip=False: Stage 1 signal verbatim.
    - flip=True:  Stage 1 signal SWAPPED (long↔short). Holds untouched.

  Exit lines (both modes): sl_soft, sl_hard, tp (one take-profit).
    - Hard SL fires on bar EXTREME touching sl_hard_line.
    - Hard TP fires on bar EXTREME touching tp_hard_line.
    - FILL (gap_fills=True, the default since 2026-07-20): at the line, UNLESS the triggering bar
      OPENED already beyond it — then at the OPEN, because no trade ever happened at the line.
      Symmetric: a gap past the stop costs MORE, a gap past the take-profit pays MORE.
      gap_fills=False restores the old fill-at-the-line behaviour (and the old golden numbers).
      Measured impact: 3.2% of stops gap, mean overshoot 128-219 pts. See GAP-01.
    - Soft SL fires on 2 consecutive 1-min closes past sl_soft_line; fill at 2nd close.
    - Per-bar tie-break: hard SL > hard TP > soft SL (loss-first pessimism).
  There is NO soft take-profit. flip=True on signal S == flip=False on ¬S,
  trade-for-trade — see optimize/test_flip_equivalence.py.

  Entry signal at candle level:
        long  iff Stage 1 rule fires long
        short iff Stage 1 rule fires short
        hold  otherwise
    Collapsed: any-long → long, any-short → short, else hold.

  Position size = 1 contract. No ladder. NQ point value = $20.

  Line orientation (depends on the actual post-flip position direction):
    long position:  sl_soft_line, sl_hard_line below entry; tp_hard_line above
    short position: mirrored

  Re-entry gate: after exit at time T, next 4h candle is signal-eligible iff its
  `Date` (4h start) > T. Fresh Stage 1 evaluation; no direction memory.

  The three thresholds (sl_soft, sl_hard, tp_hard) are REQUIRED > 0.
  Constraint: sl_hard >= sl_soft.

Live reference: `docs/strategy/files/simple_strategy.md` (file overview) and
`docs/strategy/references/simple_engine_truth_table.md` (formal decision tables).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from box_lookup import BoxLookup, _MONTHLY_LEVELS, _WEEKLY_LEVELS


_LEVEL_PAIRS = _WEEKLY_LEVELS + _MONTHLY_LEVELS

DirectionScope = Literal['both', 'long_only', 'short_only']
Signal = Literal['long', 'short', 'hold']
ExitReason = Literal[
    'STOP_LOSS_HARD',
    'STOP_LOSS_SOFT',
    'TAKE_PROFIT_HARD',
    'TAKE_PROFIT_SOFT',
    'TIME_CAP',
    'END_OF_DAY',
    'FORCE_CLOSE',
    'NEWS_VETO',
    'OPEN',
]


@dataclass
class SimpleStrategyParams:
    """All values REQUIRED (no-fallback rule).

    Constraint:
      - sl_hard_points >= sl_soft_points (the hard SL line is at or beyond
        the soft SL line)

    The three thresholds (sl_soft, sl_hard, tp_hard) are validated > 0. There is
    a single take-profit (tp_hard_points); `flip_entry_direction` only reverses
    the entry direction, it does not change the exit lines.
    """
    sl_soft_points: float
    sl_hard_points: float
    tp_hard_points: float
    data_path_4h:   str
    data_path_1min: str
    box_data_path:  str
    direction_scope:       DirectionScope = 'both'
    flip_entry_direction:  bool = False
    # Per-direction (split) SL/TP — OPTIONAL. Each None field falls back to the shared *_points above, so a
    # params object that sets none of these is byte-identical to before (golden-locked). When set, the value
    # applies to that FINAL (post-flip) entry direction. Added at the END so positional construction is
    # unaffected. See study_range_regime/ACTION_PLAN_range_regime_sltp.md (Phase E) + UPDATE_engine_split_sltp.md.
    long_sl_soft_points:  Optional[float] = None
    long_sl_hard_points:  Optional[float] = None
    long_tp_hard_points:  Optional[float] = None
    short_sl_soft_points: Optional[float] = None
    short_sl_hard_points: Optional[float] = None
    short_tp_hard_points: Optional[float] = None
    cap_1min: int = 0   # max hold in 1-min bars; 0 = off. Force-close at the Nth bar's close as TIME_CAP.
    cap_mode: str = "none"        # none | bars | eod | both. 'eod' = end-of-trading-day exit (END_OF_DAY);
    #                               'both' = bars AND eod armed together ⇒ exit at whichever lands FIRST
    #                               (same-bar tie ⇒ TIME_CAP, since the bar cap is checked first).
    eod_margin_min: int = 15      # minutes before the 17:00 close to exit on FULL days (eod/both mode).
    # News veto (fundamental analysis, milestone 1). OFF => byte-identical (golden-locked).
    # Stand aside around scheduled high-impact US releases: block new entries inside the window, and
    # force-flatten an open trade that is NOT already comfortably in profit on the last bar BEFORE the
    # release lands (NEWS_VETO). The window was MEASURED, not chosen: the release minute runs 8.32x a
    # normal minute and the market is CALM beforehand, so pre=0 / post=12. See optimize/fundamentals/.
    news_veto: bool = False
    news_pre_min: int = 0         # minutes before the release the window opens (measured: 0)
    news_post_min: int = 12       # minutes after  the release the window closes (measured: 12)
    news_profit_exempt_mult: float = 1.0   # survive the window iff open profit >= this * stop distance
    # Excursion tracking (live unrealized-P/L observation). OFF => byte-identical (golden-locked):
    # the trade dict gains NO new keys, so the golden trade-ledger hash cannot move. Purely
    # observational — it can never change an entry, an exit, or a P/L. Prerequisite for the dynamic
    # stop-loss, which must know how far a trade went FOR us before it went against us.
    track_excursions: bool = False
    # GAP-AWARE FILLS (GAP-01, 2026-07-20). ON => a hard SL/TP whose bar OPENED beyond the
    # line fills at the OPEN, not the line — because no trade ever happened at the line.
    # Symmetric: gaps past the stop cost more, gaps past the take-profit pay more.
    # OFF reproduces the old optimistic fill-at-the-line numbers (and the old golden).
    gap_fills: bool = True
    # Intra-candle entry for vetoed signals (Phase 1). OFF => byte-identical (golden-locked).
    intracandle_veto_entry: bool = False   # arm a vetoed (vol-passed) signal, enter mid-candle when the gate re-opens
    intracandle_max_wait:   int  = 240     # max 1-min bars to wait inside the candle (N); 240 ~= one 4h candle
    intracandle_force_close: bool = False  # variant: a NORMAL entry force-closes an open rescued trade (priority to champion trades)


def _stage1_candle_signal(
    candle: pd.Series,
    box_row: Optional[pd.Series],
) -> Signal:
    """Evaluate Stage 1's truth table for one 4h candle against its mapped
    box-date row. Collapses across all active level pairs:
        any-long  → long
        any-short → short
        else      → hold
    """
    opn   = float(candle['Open'])
    high  = float(candle['High'])
    low   = float(candle['Low'])
    close = float(candle['Close'])

    if close > opn:
        color = 'green'
    elif close < opn:
        color = 'red'
    else:
        color = 'none'

    if box_row is None or color == 'none':
        return 'hold'

    has_long = False
    has_short = False
    for upper_col, lower_col, _label in _LEVEL_PAIRS:
        if upper_col not in box_row.index or lower_col not in box_row.index:
            continue
        u = box_row[upper_col]
        l = box_row[lower_col]
        if pd.isna(u) or pd.isna(l):
            continue
        b_upper = float(u)
        b_lower = float(l)
        touched = (low <= b_upper) and (high >= b_lower)
        if not touched:
            continue
        if color == 'green' and close > b_upper:
            has_long = True
        elif color == 'red' and close < b_lower:
            has_short = True

    if has_long:
        return 'long'
    if has_short:
        return 'short'
    return 'hold'


class SimpleStrategy:
    """Simple backtest engine — Stage 1 entry + dual-SL/TP exit.

    Decoupled from BoxStrategy / ScalingStrategy. Does not share state.
    Reads the same box CSV the old engine reads, but uses Stage 1's
    stateless per-candle rule for entry direction.
    """

    NQ_POINT_VALUE = 20.0  # NQ futures: $20 per point per contract.

    def __init__(self, params: SimpleStrategyParams) -> None:
        for fld in ('sl_soft_points', 'sl_hard_points', 'tp_hard_points'):
            v = getattr(params, fld)
            if v <= 0:
                raise ValueError(f'{fld} must be > 0, got {v}')
        if params.sl_hard_points < params.sl_soft_points:
            raise ValueError(
                f'sl_hard_points ({params.sl_hard_points}) must be >= '
                f'sl_soft_points ({params.sl_soft_points})'
            )
        if params.direction_scope not in ('both', 'long_only', 'short_only'):
            raise ValueError(f'direction_scope invalid: {params.direction_scope}')
        if not isinstance(params.flip_entry_direction, bool):
            raise ValueError(f'flip_entry_direction must be bool, got {type(params.flip_entry_direction)}')
        self.params = params
        # Resolve per-direction (split) SL/TP once. Each side's 4 points = its split field if set, else the
        # shared *_points (⇒ when NO split field is set, _long == _short == shared ⇒ byte-identical). Validate
        # ordering/positivity per side so a split can't sneak in a bad line.
        def _side(side: str):
            ss = getattr(params, f'{side}_sl_soft_points')
            sh = getattr(params, f'{side}_sl_hard_points')
            th = getattr(params, f'{side}_tp_hard_points')
            ss = params.sl_soft_points if ss is None else float(ss)
            sh = params.sl_hard_points if sh is None else float(sh)
            th = params.tp_hard_points if th is None else float(th)
            for nm, v in (('sl_soft', ss), ('sl_hard', sh), ('tp_hard', th)):
                if v <= 0:
                    raise ValueError(f'{side}_{nm}_points must be > 0, got {v}')
            if sh < ss:
                raise ValueError(f'{side}_sl_hard_points ({sh}) must be >= {side}_sl_soft_points ({ss})')
            return (ss, sh, th)
        self._long_pts = _side('long')    # (sl_soft, sl_hard, tp_hard) for FINAL dir == 'long'
        self._short_pts = _side('short')  # …for FINAL dir == 'short'

    def backtest(
        self,
        df_4h: pd.DataFrame,
        df_1min: pd.DataFrame,
        box_df_indexed: pd.DataFrame,
        sl_tp_mult: Optional[np.ndarray] = None,
        tp_mult: Optional[np.ndarray] = None,
        entry_gate: Optional[np.ndarray] = None,
        entry_resolver=None,
        veto_vote_mask: Optional[np.ndarray] = None,   # was `veto_mask` — a trap name; see WHAT BLOCKS below
        blocked_log: Optional[List[Dict]] = None,
        veto_as_flip: bool = False,
        signals: Optional[np.ndarray] = None,
        intracandle_gate_by_dir: Optional[dict] = None,
        intracandle_vol_gate: Optional[np.ndarray] = None,
        intracandle_normal_gate: Optional[np.ndarray] = None,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simple engine.

        ═══════════════════════════════════════════════════════════════════════════════════════════════
        WHAT ACTUALLY BLOCKS AN ENTRY — read this before adding any "veto"-like feature.
        ═══════════════════════════════════════════════════════════════════════════════════════════════
        There is EXACTLY ONE array that stops a new trade opening on a decision bar: `entry_gate`.
        The entry path is `if not entry_gate[idx]: continue`. That is the whole blocking mechanism.

        `veto_vote_mask` DOES NOT BLOCK ANYTHING. It is the per-decision-bar VETO VOTE from the indicator
        layer, and the engine reads it ONLY to:
            • classify WHY a bar was dropped, for `blocked_log` ('veto' vs 'vol_gate') — diagnostic only;
            • arm the intra-candle vetoed-entry rescue (Phase 1);
            • decide which entries to REVERSE under `veto_as_flip`;
            • abort/re-arm a carried setup in the live carry resolver.
        The veto is ALREADY folded into `entry_gate` upstream — `runner.build_layer` returns
        `gate = vol_gate ∧ ¬veto_mask`, and THAT gate is what arrives here as `entry_gate`. So the two
        arrays must be kept CONSISTENT by the caller; passing a `veto_vote_mask` without the matching
        exclusion already baked into `entry_gate` does NOTHING (except in `veto_as_flip` mode, where the
        gate is deliberately vol-only and vetoed bars stay eligible so they can be reversed).

        ⚠️  THIS IS A TRAP THAT ALREADY BIT US. The parameter used to be named `veto_mask`, and during the
        news-veto work the obvious-looking move — "pass a veto_mask to stand aside on release bars" —
        silently did nothing, because the mask was never in `entry_gate`. To stand a bar aside you must
        remove it from `entry_gate` (see `optimize/core._news_window_mask` → `gate = gate & ~nmask`).
        The rename to `veto_vote_mask` exists so the name can no longer imply a blocking power it lacks.

        ADAPTIVE-CLONE additions (absent from the original src engine):
          - sl_tp_mult: optional per-4h-bar array; multiplies all four SL/TP
            distances at entry (scaling all four preserves ordering constraints).
            None or 1.0 => identical to the original.
          - entry_gate: optional per-4h-bar bool array; if entry_gate[idx] is
            False, no new trade opens on that bar. None => identical to original.
          - veto_vote_mask: per-bar indicator veto VOTE. NON-BLOCKING — used for logging / intra-candle
            rescue / veto_as_flip / carry-abort only. See the block above.
        When both are None the clone is behaviourally identical to the original
        (verified by tests/test_clone_parity.py).

        Returns (trades, final_state).
        """
        if df_4h.empty:
            return [], {'open_trade': None}

        # Axis-B (Step B2): optional precomputed per-decision-bar Stage-1 signal array (object dtype,
        # 'long'/'short'/'hold'), aligned 1:1 with df_4h. When supplied, the entry branch reads
        # signals[idx-1] instead of recomputing _stage1_candle_signal + box.loc per bar — proven
        # identical (optimize.signals.decision_signals + tests/test_axisB_signal_equiv.py).
        # None ⇒ ORIGINAL behaviour, byte-for-byte unchanged.
        if signals is not None and len(signals) != len(df_4h):
            raise ValueError(f'signals length {len(signals)} != df_4h length {len(df_4h)}')

        # Axis-B (Step B3a): pre-extract the decision-frame columns used in the loop as numpy arrays
        # ONCE, so the per-bar hot path indexes plain arrays instead of building a pandas Series via
        # df_4h.iloc[idx] (fast_xs) every bar. Date is tz-naive datetime64 (verified) so to_numpy is a
        # zero-copy view and pd.Timestamp(d4_dates[i]) == pd.Timestamp(df_4h['Date'].iloc[i]); Close
        # float matches float(row['Close']) bit-for-bit. (The signals=None path still builds the row
        # for _stage1_candle_signal — unchanged parity.)
        d4_dates = df_4h['Date'].to_numpy()
        d4_close = df_4h['Close'].to_numpy(dtype=float)

        if not df_1min.empty:
            ts_4h_arr = df_4h['Date'].to_numpy()
            ts_1m_arr = df_1min['Date'].to_numpy()
            start_1m = np.searchsorted(ts_1m_arr, ts_4h_arr, side='left')
            start_1m = np.append(start_1m, len(ts_1m_arr))
            # Axis-B (Step B3b): pre-extract the 1-min columns the exit walk reads as numpy arrays ONCE,
            # so _walk_exit_for_4h iterates by index instead of slicing df_1min.iloc[lo:hi] + itertuples
            # every window. Date tz-naive datetime64 (zero-copy view); High/Low/Close are float64. Per-bar
            # values are still wrapped in float()/pd.Timestamp() so trade dicts are bit-identical.
            md_arr = ts_1m_arr
            mh_arr = df_1min['High'].to_numpy(dtype=float)
            ml_arr = df_1min['Low'].to_numpy(dtype=float)
            mc_arr = df_1min['Close'].to_numpy(dtype=float)
            mo_arr = df_1min['Open'].to_numpy(dtype=float)   # gap-aware fills (GAP-01)
            if self.params.cap_mode in ("eod", "both"):
                from optimize.trading_days import eod_targets
                eod_target_arr, session_last_arr = eod_targets(md_arr, self.params.eod_margin_min)
            else:
                eod_target_arr = session_last_arr = None
            # News-veto force-exit targets, built on the SAME 1-min frame the exit walk indexes into
            # (same sharp edge as eod_targets: the indices are into THIS array).
            if self.params.news_veto:
                from optimize.fundamentals import release_calendar as _rc
                from optimize.fundamentals import window as _w
                news_target_arr = _w.news_exit_targets(
                    pd.DataFrame({"Date": md_arr}), _rc.load_calendar(), self.params.news_pre_min)
            else:
                news_target_arr = None
        else:
            start_1m = None
            news_target_arr = None
            md_arr = mh_arr = ml_arr = mc_arr = mo_arr = None
            eod_target_arr = session_last_arr = None

        # Intra-candle vetoed-entry resolver (Phase 1). Built only when the flag is on AND a gate is supplied
        # ⇒ flag off / no gate ⇒ _ic_resolver stays None ⇒ every new branch below is skipped ⇒ byte-identical.
        _ic_resolver = None
        if getattr(self.params, "intracandle_veto_entry", False) and intracandle_gate_by_dir is not None:
            from indicators.intracandle import build_resolver
            _ic_resolver = build_resolver(intracandle_gate_by_dir, min_start=0,
                                          max_wait=int(getattr(self.params, "intracandle_max_wait", 240)))

        trades: List[Dict] = []
        open_trade: Optional[Dict] = None
        blocked_until: Optional[pd.Timestamp] = None
        soft_consec_count: int = 0   # consecutive 1-min closes past the active soft line
        bars_held: int = 0           # 1-min bars at/after entry on the open trade (for the time cap)
        # Excursion tracking (opt-in, params.track_excursions). The running extremes the OPEN trade has
        # reached. They must live out here, not in the exit walk: the walk is re-entered once per
        # decision bar, so a trade spanning several bars would otherwise reset its own history.
        run_hi: float = float('-inf')
        run_lo: float = float('inf')
        armed: Optional[Dict] = None  # carry-mode (entry_resolver) armed-but-unfilled setup
        scope = self.params.direction_scope
        flip = self.params.flip_entry_direction
        # veto_as_flip: a vetoed (but otherwise eligible) signal ENTERS THE OPPOSITE direction
        # instead of being dropped. The caller passes a vol-only entry_gate in this mode (so vetoed
        # bars are not pre-filtered) plus the veto_vote_mask used here to decide which entries to reverse.
        def _opp(d):
            return 'short' if d == 'long' else 'long'

        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit on the currently open
            trade. Single exit model regardless of `flip`: hard-SL > hard-TP > soft-SL on the
            ENTERED direction. `flip` only reverses entry direction (see entry logic below)."""
            nonlocal open_trade, blocked_until, soft_consec_count, bars_held, run_hi, run_lo
            if open_trade is None or start_1m is None:
                return
            lo = int(start_1m[idx])
            hi = int(start_1m[idx + 1])
            d   = open_trade['direction']
            ss  = open_trade['sl_soft_line']
            sh  = open_trade['sl_hard_line']
            th  = open_trade['tp_hard_line']
            ep  = open_trade['entry_price']
            pv  = self.NQ_POINT_VALUE
            entry_time_np = np.datetime64(open_trade['entry_time'])   # for the no-look-ahead skip
            cap = self.params.cap_1min                                 # 0 = off

            for t in range(lo, hi):
                if md_arr[t] < entry_time_np:                          # sub_ts < entry_time (skip pre-entry)
                    continue
                bars_held += 1                                         # bar 1 = first bar at/after entry
                m_high  = float(mh_arr[t])
                m_low   = float(ml_arr[t])
                m_close = float(mc_arr[t])

                # Excursion tracking: the running extremes reached while this trade is open. Updated
                # BEFORE the exit checks, so the exit bar itself is included — mirrors fast_engine,
                # which slices hi[:ti+1] (inclusive of the exit bar).
                if self.params.track_excursions:
                    if m_high > run_hi:
                        run_hi = m_high
                    if m_low < run_lo:
                        run_lo = m_low

                exit_reason: Optional[ExitReason] = None
                fill: Optional[float] = None
                resets_counter = True

                # Single exit model (flip or not): hard-SL > hard-TP > soft-SL on the ENTERED
                # direction. `flip` only reverses entry direction; it no longer swaps "soft" to the
                # TP side. (ts_ stays computed at entry but unused — soft-TP is inactive, as before.)
                # GAP-AWARE FILL (mirrors fast_engine). The TRIGGER is "the bar's extreme reached the
                # line"; the FILL used to be the line itself. Those coincide only when price moves
                # through the level continuously. If the bar OPENED already beyond the level, no trade
                # ever happened at the line — the first available price is the open.
                # SYMMETRIC ON PURPOSE: a gap past the STOP fills WORSE, a gap past the TAKE-PROFIT
                # fills BETTER. Applying it only to stops would inject a pessimistic bias.
                m_open_px = float(mo_arr[t]) if self.params.gap_fills else None

                if d == 'long':
                    if m_low <= sh:
                        exit_reason, fill = 'STOP_LOSS_HARD', sh
                        if m_open_px is not None and m_open_px < fill:
                            fill = m_open_px
                    elif m_high >= th:
                        exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        if m_open_px is not None and m_open_px > fill:
                            fill = m_open_px
                    elif m_close <= ss:
                        soft_consec_count += 1
                        resets_counter = False
                        if soft_consec_count >= 2:
                            exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                else:  # short
                    if m_high >= sh:
                        exit_reason, fill = 'STOP_LOSS_HARD', sh
                        if m_open_px is not None and m_open_px > fill:
                            fill = m_open_px
                    elif m_low <= th:
                        exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        if m_open_px is not None and m_open_px < fill:
                            fill = m_open_px
                    elif m_close >= ss:
                        soft_consec_count += 1
                        resets_counter = False
                        if soft_consec_count >= 2:
                            exit_reason, fill = 'STOP_LOSS_SOFT', m_close

                # NEWS_VETO: force-flatten on the last bar BEFORE a scheduled high-impact release,
                # unless already comfortably in profit. Runs only if no SL/TP/soft fired this bar ⇒ a
                # same-bar tie resolves to the price exit (the market got there first, inside the bar).
                # Checked BEFORE the time caps ⇒ a same-bar tie against those resolves to NEWS_VETO.
                # fast_engine mirrors both by ordering t_news after the price exits and before t_bars.
                #
                # news_target_arr[t] is the next force-exit bar at or after t (GLOBAL 1-min index); it
                # already points at the bar BEFORE the release, so we never eat the 8.32x release spike
                # (optimize/fundamentals/window.py::news_exit_targets explains why that is causal).
                # `sl_dist` is the hard-stop distance in points — the unit "comfortably in profit" is
                # measured in. Point-in-time check, not a running tally: the engine has no unrealized
                # P/L, and only a point check is expressible in fast_engine's vectorized model.
                if (exit_reason is None and news_target_arr is not None):
                    w = int(news_target_arr[t])
                    if w == t:                                    # the force-exit bar is THIS bar
                        sl_dist = abs(ep - open_trade['sl_hard_line'])
                        profit = (m_close - ep) if d == 'long' else (ep - m_close)
                        exempt = (sl_dist > 0
                                  and profit >= self.params.news_profit_exempt_mult * sl_dist)
                        if not exempt:
                            exit_reason, fill, resets_counter = 'NEWS_VETO', m_close, True

                # time cap (max hold): lowest priority — only if no SL/TP/soft fired this bar.
                # Armed for cap_mode none (bare cap_1min, back-compat) / bars / both — NOT for eod-only,
                # where the bar cap must stay silent even if cap_1min carries a stale value (fast_engine
                # has always ignored it there; this makes the exact engine agree).
                if (exit_reason is None and cap > 0 and bars_held >= cap
                        and self.params.cap_mode != "eod"):
                    exit_reason, fill, resets_counter = 'TIME_CAP', m_close, True

                # end-of-day cap: same lowest priority — force-close at the session's EOD target bar.
                # Under "both" this runs only when the bar cap did not already fire this bar ⇒ a same-bar
                # tie resolves to TIME_CAP (fast_engine mirrors this by ordering t_bars before t_eod).
                if (exit_reason is None and self.params.cap_mode in ("eod", "both")
                        and eod_target_arr is not None):
                    e0 = open_trade['entry_e']
                    eg = int(eod_target_arr[e0])
                    if eg >= 0:
                        if eg < e0:
                            eg = int(session_last_arr[e0])
                        if t >= eg:
                            exit_reason, fill, resets_counter = 'END_OF_DAY', m_close, True

                if exit_reason is not None and fill is not None:
                    sub_ts = pd.Timestamp(md_arr[t])                   # materialise the exit timestamp
                    _finalise(open_trade, sub_ts, fill, exit_reason, ep, d, pv)
                    if self.params.track_excursions:                    # THE main exit path
                        _stamp_excursions(open_trade, run_hi, run_lo, bars_held)
                    trades.append(open_trade)
                    blocked_until = sub_ts
                    open_trade = None
                    soft_consec_count = 0
                    run_hi, run_lo = float('-inf'), float('inf')
                    return
                if resets_counter:
                    soft_consec_count = 0

        # NO-LOOK-AHEAD TIMING (spec interpretation):
        # At iteration `idx`, the just-closed 4h bar is df_4h.iloc[idx-1].
        # The new 4h boundary just arrived at df_4h.iloc[idx].Date — that's
        # the entry moment. Entry price = the just-closed bar's close.
        # Walk 1-min bars in window `idx` for exits (all of which post-date
        # the signal). The first iteration (idx=0) has no predecessor and
        # cannot fire a signal — matches the spec's "first-candle warm-up".
        for idx in range(len(df_4h)):
            ts_new_bar_start = pd.Timestamp(d4_dates[idx])

            # Intra-candle entry requires being flat for the WHOLE candle (conservative D3): capture flatness
            # BEFORE the exit walk, so a trade that closes mid-window does not admit an in-trade intra-candle fill.
            flat_at_window_start = open_trade is None

            # FORCE-CLOSE variant (flag-gated): if a RESCUED (intra-candle) trade is open at this boundary AND a
            # NORMAL champion entry qualifies here, close the rescued trade at the boundary and free the seat so the
            # proven normal trade takes priority. Runs BEFORE the exit walk so the boundary preempts the candle's
            # own 1-min bars (a normal entry at the boundary beats a mid-candle SL/TP of the rescued trade).
            if (_ic_resolver is not None and getattr(self.params, 'intracandle_force_close', False)
                    and open_trade is not None and open_trade.get('ic') and idx >= 1):
                if signals is not None:
                    _nsig = signals[idx - 1]
                else:
                    _sc = df_4h.iloc[idx - 1]; _st = pd.Timestamp(d4_dates[idx - 1])
                    try:
                        _br = box_df_indexed.loc[BoxLookup._candle_to_box_date(_st)]
                    except KeyError:
                        _br = None
                    _nsig = _stage1_candle_signal(_sc, _br)
                if flip and _nsig in ('long', 'short'):
                    _nsig = 'short' if _nsig == 'long' else 'long'
                # "a normal entry qualifies" = the FULL champion gate (vol ∧ ¬veto ∧ confirm). entry_gate here is
                # only vol ∧ ¬veto (confirm lives in the resolver), so use the passed full gate when available.
                _ngate = intracandle_normal_gate if intracandle_normal_gate is not None else entry_gate
                _ng = (_ngate is None) or not (0 <= idx < len(_ngate)) or bool(_ngate[idx])
                _nin = (_nsig in ('long', 'short')
                        and not (scope == 'long_only' and _nsig != 'long')
                        and not (scope == 'short_only' and _nsig != 'short'))
                if _nin and _ng:
                    _finalise(open_trade, ts_new_bar_start, float(d4_close[idx - 1]), 'FORCE_CLOSE',
                              open_trade['entry_price'], open_trade['direction'], self.NQ_POINT_VALUE)
                    if self.params.track_excursions:
                        _stamp_excursions(open_trade, run_hi, run_lo, bars_held)
                    trades.append(open_trade)
                    open_trade = None
                    soft_consec_count = 0
                    bars_held = 0
                    run_hi, run_lo = float('-inf'), float('inf')

            # Exit walk for a carry-over trade (1-min bars in this new window).
            _walk_exit_for_4h(idx)

            # Entry decision: needs a just-closed predecessor bar (idx >= 1).
            if open_trade is None and idx >= 1:
                if blocked_until is not None and ts_new_bar_start <= blocked_until:
                    continue
                # Signal is computed from the JUST-CLOSED bar (idx-1), not
                # from the current bar. Box geometry is keyed off the
                # just-closed bar's timestamp.
                if signals is not None:
                    # Step B2: use the precomputed signal of the just-closed bar (idx-1).
                    signal = signals[idx - 1]
                else:
                    # ORIGINAL parity path: build the row only here (it feeds _stage1_candle_signal).
                    signal_candle = df_4h.iloc[idx - 1]
                    signal_ts = pd.Timestamp(d4_dates[idx - 1])
                    box_date = BoxLookup._candle_to_box_date(signal_ts)
                    try:
                        box_row = box_df_indexed.loc[box_date]
                    except KeyError:
                        box_row = None
                    signal = _stage1_candle_signal(signal_candle, box_row)

                # Flip layer (Q-A symmetric flip): swap long↔short BEFORE
                # scope filtering. Holds stay holds.
                if flip and signal in ('long', 'short'):
                    signal = 'short' if signal == 'long' else 'long'

                # ADAPTIVE-CLONE: per-bar SL/TP multiplier (1.0 => original; scales ALL four lines).
                _m = 1.0
                if sl_tp_mult is not None and 0 <= idx < len(sl_tp_mult):
                    _mv = float(sl_tp_mult[idx])
                    if np.isfinite(_mv) and _mv > 0:
                        _m = _mv
                # per-bar TP-ONLY multiplier (1.0 => original; scales only the TP lines, SL untouched).
                # Lets the regime study move TP while pinning SL (Q3b). Default None ⇒ _tm=1 ⇒ identical.
                _tm = 1.0
                if tp_mult is not None and 0 <= idx < len(tp_mult):
                    _tv = float(tp_mult[idx])
                    if np.isfinite(_tv) and _tv > 0:
                        _tm = _tv

                # gate (vol etc.) matches the original: only blocks when set, in-range, and False.
                gated = (entry_gate is None) or not (0 <= idx < len(entry_gate)) or bool(entry_gate[idx])
                vetoed = (veto_vote_mask is not None) and (0 <= idx < len(veto_vote_mask)) and bool(veto_vote_mask[idx])

                # DIAGNOSTIC ONLY (no effect on trades): record fresh in-scope directional signals
                # that the composite gate dropped, so the caller can LOG them instead of silently
                # discarding them. gate = vol ∧ ¬veto, so 'not gated' ⇒ veto (if vetoed) else vol-gate.
                if (blocked_log is not None and signal in ('long', 'short') and not gated
                        and not (scope == 'long_only' and signal != 'long')
                        and not (scope == 'short_only' and signal != 'short')):
                    blocked_log.append({'entry_idx': idx, 'signal_idx': idx - 1,
                                        'direction': signal,
                                        # in veto_as_flip mode a veto never blocks (it reverses),
                                        # so a dropped bar here is always the volatility gate.
                                        'reason': 'veto' if (vetoed and not veto_as_flip) else 'vol_gate'})

                # INTRA-CANDLE vetoed entry (Phase 1, flag-gated). Arm a VETOED, vol-passed, directional signal
                # and enter mid-candle at the first 1-min bar where the FULL gate (¬veto ∧ ≥K confirms) re-opens.
                # Conservative D3: only when flat for the whole candle (flat_at_window_start). Self-contained —
                # no cross-candle carry. _ic_resolver is None when the flag is off ⇒ this block is skipped ⇒ parity.
                ic_entered = False
                if (_ic_resolver is not None and flat_at_window_start and start_1m is not None
                        and signal in ('long', 'short') and vetoed and not veto_as_flip
                        and not (scope == 'long_only' and signal != 'long')
                        and not (scope == 'short_only' and signal != 'short')):
                    _vol_ok = (intracandle_vol_gate is None
                               or not (0 <= idx < len(intracandle_vol_gate))
                               or bool(intracandle_vol_gate[idx]))
                    if _vol_ok:
                        _se = int(start_1m[idx]); _sl = int(start_1m[idx + 1]) - _se
                        _hit = _ic_resolver(1 if signal == 'long' else -1, _se, _sl, is_flat=lambda o: True)
                        if _hit is not None:
                            _o = _hit[0]
                            entry_ts = pd.Timestamp(md_arr[_se + _o])
                            entry_px = float(mc_arr[_se + _o])
                            edir, sidx, vflip = signal, idx - 1, False
                            ic_entered = True

                if ic_entered:
                    pass                                   # entry fields set above; fall through to open the trade
                elif entry_resolver is None:
                    # ORIGINAL parity path (unchanged behaviour): immediate fill at the signal close.
                    if signal == 'hold':
                        continue
                    if scope == 'long_only' and signal != 'long':
                        continue
                    if scope == 'short_only' and signal != 'short':
                        continue
                    if not gated:
                        continue
                    entry_ts = ts_new_bar_start
                    entry_px = float(d4_close[idx - 1])
                    edir, sidx = signal, idx - 1
                    vflip = bool(veto_as_flip and vetoed)
                    if vflip:
                        edir = _opp(edir)              # veto reverses the entry direction
                else:
                    # CARRY MODE (live B1): (re)arm on a fresh gated, non-vetoed directional signal;
                    # carry an unfilled setup across HOLD bars; abort on a fresh veto; supersede on a
                    # new signal. The resolver reads votes LIVE at idx-1 and anchors levels to the
                    # ARMED signal's close.
                    in_scope = (signal in ('long', 'short')
                                and not (scope == 'long_only' and signal != 'long')
                                and not (scope == 'short_only' and signal != 'short'))
                    if in_scope and gated:
                        if vetoed and veto_as_flip:
                            # veto reverses: (re)arm the OPPOSITE direction instead of aborting.
                            armed = {'dir': _opp(signal), 'sidx': idx - 1,
                                     'sclose': float(d4_close[idx - 1]), 'vflip': True}
                        elif not vetoed:
                            armed = {'dir': signal, 'sidx': idx - 1,
                                     'sclose': float(d4_close[idx - 1]), 'vflip': False}
                    if armed is not None and vetoed and not veto_as_flip:
                        armed = None                      # live veto aborts the armed entry (Q4)
                    if armed is None or start_1m is None:
                        continue
                    sub_w = df_1min.iloc[int(start_1m[idx]):int(start_1m[idx + 1])]
                    res = entry_resolver(idx, armed['dir'], armed['sclose'], armed['sidx'],
                                         ts_new_bar_start, sub_w)
                    if res is None:
                        continue                          # keep armed → carry to the next bar
                    entry_ts = pd.Timestamp(res[0])
                    entry_px = float(res[1])
                    edir, sidx = armed['dir'], armed['sidx']
                    vflip = bool(armed.get('vflip'))
                    armed = None

                # per-direction (split) points; _long_pts/_short_pts == shared when no split set ⇒ identical
                if edir == 'long':
                    ss, sh, th = self._long_pts
                    sl_soft_line = entry_px - ss * _m
                    sl_hard_line = entry_px - sh * _m
                    tp_hard_line = entry_px + th * _m * _tm
                else:
                    ss, sh, th = self._short_pts
                    sl_soft_line = entry_px + ss * _m
                    sl_hard_line = entry_px + sh * _m
                    tp_hard_line = entry_px - th * _m * _tm

                open_trade = {
                    'entry_idx':    idx,                       # the new bar
                    'entry_e':      int(start_1m[idx]) if start_1m is not None else 0,  # entry global 1-min index (eod cap)
                    'signal_idx':   sidx,                      # the (armed) signal's just-closed bar
                    'entry_time':   entry_ts,
                    'entry_price':  entry_px,
                    'direction':    edir,
                    'ic':           bool(ic_entered),          # True = rescued intra-candle entry (for force-close)
                    'veto_flip':    bool(vflip),               # entered reversed because of a veto
                    'sl_soft_line': sl_soft_line,
                    'sl_hard_line': sl_hard_line,
                    'tp_hard_line': tp_hard_line,
                    'flip':         flip,
                    'exit_time':    None,
                    'exit_price':   None,
                    'exit_reason':  None,
                    'pnl_points':   None,
                    'pnl_dollars':  None,
                }
                soft_consec_count = 0
                bars_held = 0

                # Exit walk for the same new 4h window (its 1-min bars are
                # all chronologically AFTER the signal — no look-ahead).
                _walk_exit_for_4h(idx)

        if open_trade is not None:
            open_trade['exit_reason'] = 'OPEN'
            trades.append(open_trade)

        final_state = {
            'open_trade': None if trades and trades[-1]['exit_reason'] != 'OPEN' else open_trade,
        }
        return trades, final_state


def _stamp_excursions(trade: Dict, run_hi: float, run_lo: float, bars: int) -> None:
    """Stamp MFE / MAE on a trade dict in place. Opt-in (params.track_excursions).

    MFE — Maximum Favourable Excursion: the BEST unrealized profit this trade ever saw while open.
    MAE — Maximum Adverse  Excursion: the WORST unrealized loss it ever saw while open.

    Both in POINTS, signed from the trade's own point of view (MFE >= 0, MAE <= 0), so a long and a
    short are directly comparable. Clamped, so a gap through the entry can never violate the sign
    invariants. fast_engine computes the identical quantities over hi[:ti+1] / lo[:ti+1].

    Why this matters: the engine has never known how a trade was doing WHILE OPEN — P/L existed only
    at exit. That made "was this stop-out a real move, or did we give back a winner?" unanswerable,
    and the dynamic stop-loss (Task #3) impossible to even express.
    """
    ep = float(trade['entry_price'])
    if trade['direction'] == 'long':
        mfe, mae = run_hi - ep, run_lo - ep
    else:
        mfe, mae = ep - run_lo, ep - run_hi
    trade['mfe_points'] = max(float(mfe), 0.0)
    trade['mae_points'] = min(float(mae), 0.0)
    trade['bars_1m'] = int(bars)


def _finalise(
    trade: Dict,
    exit_ts: pd.Timestamp,
    fill: float,
    reason: ExitReason,
    entry_price: float,
    direction: Signal,
    point_value: float,
) -> None:
    """Stamp the exit fields on a trade dict in place."""
    trade['exit_time']   = exit_ts
    trade['exit_price']  = fill
    trade['exit_reason'] = reason
    if direction == 'long':
        pnl = fill - entry_price
    else:
        pnl = entry_price - fill
    trade['pnl_points']  = pnl
    trade['pnl_dollars'] = pnl * point_value
