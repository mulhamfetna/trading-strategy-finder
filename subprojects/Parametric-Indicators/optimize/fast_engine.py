"""WS-H — vectorized backtest (numpy), parity-locked to the verified engine (engine.SimpleStrategy).

WHY: the original engine walks 1-min bars in a Python loop (≈1 core, minutes for 1m). This reproduces
the EXACT same decisions but resolves each trade's exit with numpy boolean scans (argmax), turning
minutes into milliseconds — so the whole multi-timeframe search runs locally in seconds.

FAITHFULNESS (must match engine.py exactly — see optimize/test_fast_parity.py):
  • Entry: at decision bar idx (idx≥1), direction = Stage-1 signal of the JUST-CLOSED bar idx-1
    (post-flip), entry price = close[idx-1], entry time = date[idx]. Gated by gate[idx]; one position
    at a time; re-entry only on a decision bar whose date > the last exit time.
  • Exit (resolved on 1-min, lines are absolute point distances):
      NORMAL  (flip=False): per-bar priority hard-SL > hard-TP > soft-SL.
        long : SLh low≤ep-slh(fill line) · TPh high≥ep+tp(fill line) · SLs 2 consecutive closes≤ep-sls(fill close)
        short: mirrored.
      FLIPPED (flip=True): direction swapped at entry; priority hard-TP > hard-SL > soft-TP, soft on
        the TP side (tp_soft = tp). sl_soft is inactive (matches engine).
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
R_SL_HARD, R_TP_HARD, R_SL_SOFT, R_TP_SOFT = 0, 1, 2, 3
REASON_NAME = {R_SL_HARD: "STOP_LOSS_HARD", R_TP_HARD: "TAKE_PROFIT_HARD",
               R_SL_SOFT: "STOP_LOSS_SOFT", R_TP_SOFT: "TAKE_PROFIT_SOFT"}


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
                  short_tp: float | None = None) -> list[dict]:
    """Return the list of completed trades (dicts with entry/exit/dir/reason/pnl_points), in order.
    Mirrors engine.SimpleStrategy(...).backtest(...) candidate stream (exit_reason != OPEN).

    Split SL/TP (Q3 / E2): the optional long_*/short_* args give the FINAL post-flip direction its own
    sl_soft/sl_hard/tp. Any that is None falls back to the shared sl_soft/sl_hard/tp ⇒ when none are set,
    long==short==shared ⇒ byte-identical to the pre-split path (locked by test_fast_parity)."""
    n = len(d_dates)
    M = len(m_dates)
    trades: list[dict] = []
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
        if gate is not None and not gate[idx]:
            idx += 1; continue
        et = d_dates[idx]
        if blocked_until is not None and et <= blocked_until:
            idx += 1; continue
        ep = float(d_close[idx - 1])

        # lines (absolute point distances); per-FINAL-direction split points (shared when no split set)
        if d == LONG:
            sls, slh, tpv = L_sls, L_slh, L_tp
            slh_line, tph_line = ep - slh, ep + tpv
            sls_line, tps_line = ep - sls, ep + tpv           # soft on SL side (normal) / TP side (flip)
        else:
            sls, slh, tpv = S_sls, S_slh, S_tp
            slh_line, tph_line = ep + slh, ep - tpv
            sls_line, tps_line = ep + sls, ep - tpv

        e = int(np.searchsorted(m_dates, et, side="left"))    # first 1m bar with Date ≥ entry time
        if e >= M:
            break
        hi, lo, cl = m_high[e:], m_low[e:], m_close[e:]

        # candidate first-hit slice indices for the three exit kinds
        if d == LONG:
            t_slh = _first_true(lo <= slh_line)
            t_tph = _first_true(hi >= tph_line)
            soft_breach = (cl <= sls_line) if not flip else (cl >= tps_line)
        else:
            t_slh = _first_true(hi >= slh_line)
            t_tph = _first_true(lo <= tph_line)
            soft_breach = (cl >= sls_line) if not flip else (cl <= tps_line)
        # soft fires at the 2nd of two consecutive breaching closes
        if soft_breach.size >= 2:
            pair = soft_breach[1:] & soft_breach[:-1]
            t_soft = (int(np.argmax(pair)) + 1) if pair.any() else -1
        else:
            t_soft = -1

        # assemble candidates with their priority, pick earliest (tie → priority order)
        if not flip:
            order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line), (t_soft, R_SL_SOFT, None)]
        else:
            order = [(t_tph, R_TP_HARD, tph_line), (t_slh, R_SL_HARD, slh_line), (t_soft, R_TP_SOFT, None)]
        best = None  # (slice_t, priority_rank, reason, fill)
        for rank, (ti, reason, line) in enumerate(order):
            if ti < 0:
                continue
            fill = float(cl[ti]) if line is None else float(line)
            cand = (ti, rank, reason, fill)
            if best is None or ti < best[0]:
                best = cand
            # equal index: keep the earlier-in-`order` (lower rank) = already kept (we only replace on ti<)
        if best is None:
            # no exit before end of data → OPEN; engine drops it. Stop (one position; nothing after).
            break

        ti, _rank, reason, fill = best
        xt = m_dates[e + ti]
        pnl_pts = (fill - ep) if d == LONG else (ep - fill)
        trades.append({
            "entry_idx": idx, "entry_time": et, "entry_price": ep,
            "direction": "long" if d == LONG else "short",
            "exit_time": xt, "exit_price": fill, "exit_reason": REASON_NAME[reason],
            "pnl_points": float(pnl_pts),
        })
        blocked_until = xt
        # advance to the next decision bar whose date > exit time
        nxt = int(np.searchsorted(d_dates, xt, side="right"))
        idx = max(idx + 1, nxt)
    return trades
