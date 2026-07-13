"""WS-H — vectorized backtest (numpy), parity-locked to the verified engine (engine.SimpleStrategy).

WHY: the original engine walks 1-min bars in a Python loop (≈1 core, minutes for 1m). This reproduces
the EXACT same decisions but resolves each trade's exit with numpy boolean scans (argmax), turning
minutes into milliseconds — so the whole multi-timeframe search runs locally in seconds.

FAITHFULNESS (must match engine.py exactly — see optimize/test_fast_parity.py):
  • Entry: at decision bar idx (idx≥1), direction = Stage-1 signal of the JUST-CLOSED bar idx-1
    (post-flip), entry price = close[idx-1], entry time = date[idx]. Gated by gate[idx]; one position
    at a time; re-entry only on a decision bar whose date > the last exit time.
  • Exit (resolved on 1-min, lines are absolute point distances):
      Single exit model (flip or not): per-bar priority hard-SL > hard-TP > soft-SL.
        long : SLh low≤ep-slh(fill line) · TPh high≥ep+tp(fill line) · SLs 2 consecutive closes≤ep-sls(fill close)
        short: mirrored.
      flip=True only REVERSES the entry direction (d = -raw); the exit logic is identical (matches engine).
  • "2 consecutive closes" == close past the soft line on bar t AND bar t-1 (the engine's consec≥2,
    which resets on any non-breach → equivalent to a pairwise AND); fill at the 2nd bar's close.
  • Same-bar ties resolved by the priority order above. No look-ahead (scan starts at the 1-min bar
    with Date ≥ entry time).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# signal/direction encoding
LONG, SHORT, HOLD = 1, -1, 0
# exit reason codes
R_SL_HARD, R_TP_HARD, R_SL_SOFT, R_TP_SOFT, R_TIME_CAP, R_END_OF_DAY, R_FORCE_CLOSE = 0, 1, 2, 3, 4, 5, 6
R_NEWS_VETO = 7
REASON_NAME = {R_SL_HARD: "STOP_LOSS_HARD", R_TP_HARD: "TAKE_PROFIT_HARD",
               R_SL_SOFT: "STOP_LOSS_SOFT", R_TP_SOFT: "TAKE_PROFIT_SOFT",
               R_TIME_CAP: "TIME_CAP", R_END_OF_DAY: "END_OF_DAY", R_FORCE_CLOSE: "FORCE_CLOSE",
               R_NEWS_VETO: "NEWS_VETO"}


def signals_to_int(sig_obj: np.ndarray) -> np.ndarray:
    """Map an object array of 'long'/'short'/'hold' to int8 +1/-1/0."""
    out = np.zeros(len(sig_obj), dtype=np.int8)
    out[sig_obj == "long"] = LONG
    out[sig_obj == "short"] = SHORT
    return out


def _first_true(mask: np.ndarray) -> int:
    """Index of first True in mask, or -1 if none."""
    if mask.any():
        return int(np.argmax(mask))
    return -1


def fast_backtest(d_dates: np.ndarray, d_close: np.ndarray, sig_int: np.ndarray,
                  gate: np.ndarray | None,
                  m_dates: np.ndarray, m_high: np.ndarray, m_low: np.ndarray, m_close: np.ndarray,
                  sl_soft: float, sl_hard: float, tp: float, flip: bool,
                  long_sl_soft: float | None = None, long_sl_hard: float | None = None,
                  long_tp: float | None = None,
                  short_sl_soft: float | None = None, short_sl_hard: float | None = None,
                  short_tp: float | None = None, cap_1min: int = 0,
                  cap_mode: str = "none",
                  eod_target: np.ndarray | None = None,
                  session_last: np.ndarray | None = None,
                  intracandle_gate_by_dir: dict | None = None,
                  intracandle_vol_gate: np.ndarray | None = None,
                  intracandle_veto_mask: np.ndarray | None = None,
                  intracandle_max_wait: int = 240,
                  intracandle_force_close: bool = False,
                  intracandle_normal_gate: np.ndarray | None = None,
                  news_target: np.ndarray | None = None,
                  news_profit_exempt_mult: float = 1.0,
                  track_excursions: bool = False) -> list[dict]:
    """Return the list of completed trades (dicts with entry/exit/dir/reason/pnl_points), in order.
    Mirrors engine.SimpleStrategy(...).backtest(...) candidate stream (exit_reason != OPEN).

    Split SL/TP (Q3 / E2): the optional long_*/short_* args give the FINAL post-flip direction its own
    sl_soft/sl_hard/tp. Any that is None falls back to the shared sl_soft/sl_hard/tp ⇒ when none are set,
    long==short==shared ⇒ byte-identical to the pre-split path (locked by test_fast_parity)."""
    n = len(d_dates)
    M = len(m_dates)
    trades: list[dict] = []
    exc_bounds: list[tuple[int, int]] = []   # (entry, exit) 1-min indices — only when track_excursions
    blocked_until = None  # np.datetime64 of last exit; next entry needs date > this
    # resolve per-side points ONCE (shared fallback ⇒ identical when no split given)
    L_sls = sl_soft if long_sl_soft is None else float(long_sl_soft)
    L_slh = sl_hard if long_sl_hard is None else float(long_sl_hard)
    L_tp = tp if long_tp is None else float(long_tp)
    S_sls = sl_soft if short_sl_soft is None else float(short_sl_soft)
    S_slh = sl_hard if short_sl_hard is None else float(short_sl_hard)
    S_tp = tp if short_tp is None else float(short_tp)

    idx = 1
    while idx < n:
        # entry eligibility (mirror engine): signal from idx-1, post-flip; gate[idx]; not blocked
        raw = sig_int[idx - 1]
        d = -raw if flip else raw
        if d == HOLD:
            idx += 1; continue
        et = d_dates[idx]
        if blocked_until is not None and et <= blocked_until:
            idx += 1; continue

        _ic_e = -1                       # >=0 => rescued INTRA-CANDLE entry at this global 1-min bar
        if gate is not None and not gate[idx]:
            # normal gate blocks. Try an intra-candle rescue of a VETOED, vol-passed directional signal:
            # scan this candle's 1-min bars for the first bar where the full gate re-opens (within N).
            if (intracandle_gate_by_dir is not None
                    and intracandle_veto_mask is not None and idx < len(intracandle_veto_mask)
                    and intracandle_veto_mask[idx]
                    and (intracandle_vol_gate is None
                         or (idx < len(intracandle_vol_gate) and intracandle_vol_gate[idx]))):
                c0 = int(np.searchsorted(m_dates, d_dates[idx], side="left"))
                c1 = int(np.searchsorted(m_dates, d_dates[idx + 1], side="left")) if idx + 1 < n else M
                garr = intracandle_gate_by_dir[d]
                limit = min(int(intracandle_max_wait), c1 - c0)
                for o in range(limit):
                    t = c0 + o
                    if t < M and garr[t]:
                        _ic_e = t; break
            if _ic_e < 0:
                idx += 1; continue

        if _ic_e >= 0:
            e = _ic_e; et = m_dates[e]; ep = float(m_close[e])
        else:
            ep = float(d_close[idx - 1])
            e = int(np.searchsorted(m_dates, et, side="left"))    # first 1m bar with Date ≥ entry time
        if e >= M:
            break

        # lines (absolute point distances); per-FINAL-direction split points (shared when no split set)
        if d == LONG:
            sls, slh, tpv = L_sls, L_slh, L_tp
            slh_line, tph_line = ep - slh, ep + tpv
            sls_line, tps_line = ep - sls, ep + tpv           # soft-SL line used; tps_line kept (unused, == hard TP)
        else:
            sls, slh, tpv = S_sls, S_slh, S_tp
            slh_line, tph_line = ep + slh, ep - tpv
            sls_line, tps_line = ep + sls, ep - tpv
        hi, lo, cl = m_high[e:], m_low[e:], m_close[e:]

        # candidate first-hit slice indices for the three exit kinds
        if d == LONG:
            t_slh = _first_true(lo <= slh_line)
            t_tph = _first_true(hi >= tph_line)
            soft_breach = cl <= sls_line   # soft stop-loss (long); flip only reverses entry, not this
        else:
            t_slh = _first_true(hi >= slh_line)
            t_tph = _first_true(lo <= tph_line)
            soft_breach = cl >= sls_line   # soft stop-loss (short); flip only reverses entry, not this
        # soft fires at the 2nd of two consecutive breaching closes
        if soft_breach.size >= 2:
            pair = soft_breach[1:] & soft_breach[:-1]
            t_soft = (int(np.argmax(pair)) + 1) if pair.any() else -1
        else:
            t_soft = -1

        # assemble candidates with their priority, pick earliest (tie → priority order).
        # Single exit model regardless of flip: hard-SL > hard-TP > soft-SL on the ENTERED direction.
        # `flip` only reverses entry (d = -raw above); it no longer swaps "soft" to the TP side.
        # Time caps (max hold): lowest priority. Two INDEPENDENT deadlines that can both be armed:
        #   bars — the Nth traded 1-min bar from entry (bar 1 = slice index 0)
        #   eod  — the session's end-of-trading-day target bar
        # cap_mode: none | bars | eod | both. "both" ⇒ exit at whichever deadline lands FIRST, matching
        # engine.py, which applies the two as separate per-bar checks (engine.py:350 then :354) and so
        # resolves a same-bar tie to the bars cap. We reproduce that tie-break by listing t_bars BEFORE
        # t_eod in `order` (the selection loop below breaks ties by position).
        # back-compat: a bare cap_1min (existing tests/golden) is the bars cap.
        mode = "bars" if (cap_mode == "none" and cap_1min) else cap_mode
        t_bars = ((cap_1min - 1) if (cap_1min and 0 <= cap_1min - 1 < len(cl)) else -1) \
            if mode in ("bars", "both") else -1
        if mode in ("eod", "both") and eod_target is not None:
            g = int(eod_target[e])
            if g < 0:
                t_eod = -1
            else:
                if g < e:
                    g = int(session_last[e])
                t_eod = (g - e) if 0 <= (g - e) < len(cl) else -1
        else:
            t_eod = -1
        # NEWS_VETO — force-flatten on the last bar BEFORE a scheduled high-impact release, unless the
        # trade is already comfortably in profit. news_target[e] is the next force-exit bar (GLOBAL
        # index) at or after the entry bar; it already points at the bar BEFORE the release, so we do
        # not eat the 8.32x release spike (see optimize/fundamentals/window.py::news_exit_targets).
        #
        # `slh` is the hard-stop DISTANCE in points (slh_line = ep -/+ slh), so it is the natural unit
        # for "comfortably in profit": exempt iff open profit >= mult * one stop's worth of risk.
        # Evaluated at the single exit bar, not as a running tally — the engine has no unrealized P/L,
        # and a point-in-time check is all the vectorized model can express. engine.py mirrors this.
        t_news = -1
        if news_target is not None:
            g = int(news_target[e])
            if g >= 0 and 0 <= (g - e) < len(cl):
                ti = g - e
                px = float(cl[ti])
                profit = (px - ep) if d == LONG else (ep - px)
                if not (slh > 0 and profit >= news_profit_exempt_mult * slh):
                    t_news = ti

        # Same-bar tie-breaks, by position in `order`: the price exits win over NEWS_VETO (the market
        # got there first, inside the bar), and NEWS_VETO wins over the time caps. engine.py mirrors
        # this by checking the price exits first, then NEWS_VETO, then the bars/eod caps.
        order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line),
                 (t_soft, R_SL_SOFT, None),
                 (t_news, R_NEWS_VETO, None),
                 (t_bars, R_TIME_CAP, None), (t_eod, R_END_OF_DAY, None)]
        best = None  # (slice_t, priority_rank, reason, fill)
        for rank, (ti, reason, line) in enumerate(order):
            if ti < 0:
                continue
            fill = float(cl[ti]) if line is None else float(line)
            cand = (ti, rank, reason, fill)
            if best is None or ti < best[0]:
                best = cand
            # equal index: keep the earlier-in-`order` (lower rank) = already kept (we only replace on ti<)
        # FORCE-CLOSE variant: a RESCUED (intra-candle) trade yields to the next qualifying NORMAL entry.
        # Find the first later decision-bar boundary with a normal entry; if it falls at/before the natural
        # exit (or the trade would stay OPEN), close the rescued trade at that boundary and let idx re-enter.
        if intracandle_force_close and _ic_e >= 0:
            _fcg = intracandle_normal_gate if intracandle_normal_gate is not None else gate  # full champion gate
            fc_b = -1
            for b in range(idx + 1, n):
                rb = sig_int[b - 1]; db = -rb if flip else rb
                if db == HOLD:
                    continue
                if _fcg is not None and not _fcg[b]:
                    continue
                fc_b = b; break
            if fc_b >= 0:
                be = int(np.searchsorted(m_dates, d_dates[fc_b], side="left"))
                nat_global = (e + best[0]) if best is not None else (M + 1)
                if e < be <= nat_global:
                    fillf = float(d_close[fc_b - 1])
                    pnlf = (fillf - ep) if d == LONG else (ep - fillf)
                    recf = {
                        "entry_idx": idx, "entry_time": et, "entry_price": ep,
                        "direction": "long" if d == LONG else "short",
                        "exit_time": d_dates[fc_b], "exit_price": fillf,
                        "exit_reason": REASON_NAME[R_FORCE_CLOSE], "pnl_points": float(pnlf),
                    }
                    if track_excursions:
                        # MUST record bounds here too: _apply_excursions zips trades against
                        # exc_bounds, so a trade appended without bounds would silently misalign
                        # EVERY subsequent trade's MFE/MAE.
                        exc_bounds.append((e, max(be - 1, e)))
                        recf["bars_1m"] = int(max(be - 1, e) - e + 1)
                    trades.append(recf)
                    idx = fc_b                                # re-process the boundary as a normal entry
                    continue

        if best is None:
            # no exit before end of data → OPEN; engine drops it. Stop (one position; nothing after).
            break

        ti, _rank, reason, fill = best
        xt = m_dates[e + ti]
        pnl_pts = (fill - ep) if d == LONG else (ep - fill)
        rec = {
            "entry_idx": idx, "entry_time": et, "entry_price": ep,
            "direction": "long" if d == LONG else "short",
            "exit_time": xt, "exit_price": fill, "exit_reason": REASON_NAME[reason],
            "pnl_points": float(pnl_pts),
        }
        if track_excursions:
            # Record only the trade's 1-min bounds (two cheap ints). The actual MFE/MAE is computed
            # for EVERY trade at once after the loop — see _apply_excursions. Doing it per-trade cost
            # ~20% CPU, and profiling showed the arithmetic was only 0.8 ms of that: the rest was pure
            # NUMPY DISPATCH OVERHEAD, ~6 tiny numpy calls x 265 trades. One batched call kills it.
            exc_bounds.append((e, e + ti))
            rec["bars_1m"] = int(ti + 1)           # how long it lived, in 1-min bars
        trades.append(rec)
        blocked_until = xt
        # advance to the next decision bar whose date > exit time
        nxt = int(np.searchsorted(d_dates, xt, side="right"))
        idx = max(idx + 1, nxt)

    if track_excursions:
        _apply_excursions(trades, exc_bounds, m_high, m_low)
    return trades


def _apply_excursions(trades: list[dict], bounds: list[tuple[int, int]],
                      m_high: np.ndarray, m_low: np.ndarray) -> None:
    """Compute MFE/MAE for EVERY trade in ONE pair of numpy calls, then stamp them in place.

    MFE — Maximum Favourable Excursion: the best unrealized profit the trade ever saw while open.
    MAE — Maximum Adverse  Excursion: the worst unrealized loss it ever saw while open.
    Both in POINTS, signed from the trade's own view (MFE >= 0, MAE <= 0), so longs and shorts compare.

    WHY reduceat. Doing `hi[:ti+1].max()` per trade cost ~20% CPU — and profiling showed the actual
    arithmetic was only 0.8 ms of it. The rest was numpy's per-call dispatch overhead on tiny arrays.
    np.maximum.reduceat does all segment maxima in a SINGLE call.

    THE INTERLEAVE TRICK. reduceat(arr, idx) reduces the segments [idx[0],idx[1]), [idx[1],idx[2]), …
    So we lay the bounds out as [start0, end0+1, start1, end1+1, …]. The EVEN results are the trades;
    the ODD ones are the gaps between trades, and we throw them away. Trades never overlap (one
    position at a time), so the bounds are non-decreasing, which is what reduceat requires.
    """
    if not bounds:
        return
    if len(bounds) != len(trades):
        # A trade was appended without recording its bounds. zip() would silently truncate and
        # mis-assign every excursion after it — a wrong number that looks plausible. Refuse.
        raise AssertionError(
            f"excursion bounds ({len(bounds)}) != trades ({len(trades)}) — a trade-append path is "
            "missing its exc_bounds.append(). Every MFE/MAE after it would be wrong."
        )
    n = len(m_high)
    b = np.empty(2 * len(bounds), dtype=np.int64)
    b[0::2] = [s for s, _ in bounds]
    b[1::2] = [e + 1 for _, e in bounds]
    np.clip(b, 0, n - 1, out=b)

    seg_hi = np.maximum.reduceat(m_high, b)[0::2]     # one call, all trades
    seg_lo = np.minimum.reduceat(m_low, b)[0::2]

    for tr, hi_, lo_ in zip(trades, seg_hi, seg_lo):
        ep = tr["entry_price"]
        if tr["direction"] == "long":
            mfe, mae = hi_ - ep, lo_ - ep
        else:
            mfe, mae = ep - lo_, ep - hi_
        # Clamp: a gap through the entry price could otherwise flip a sign. The invariants
        # MFE >= 0 >= MAE must hold unconditionally — downstream logic depends on them.
        tr["mfe_points"] = max(float(mfe), 0.0)
        tr["mae_points"] = min(float(mae), 0.0)
