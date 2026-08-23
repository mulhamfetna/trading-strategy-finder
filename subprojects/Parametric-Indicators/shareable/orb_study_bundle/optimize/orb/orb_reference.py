"""WS-ORB (#183) — the standalone opening-range-breakout reference, exactly as pre-registered in
docs/WS-ORB-PREREGISTRATION.md. One contract. No parameters are fitted anywhere.

Input: a 1-minute frame (datetime ET-naive, open, high, low, close, volume), bars labelled by START.

Sessions
  arm A ("cash"):   session id = calendar date; anchor = cash/pit open; flat at the cash close.
  arm B ("globex"): session id = date of the 18:00 bar that starts it (bars with hour >= 18 belong to the
                    NEXT calendar day's session — the engine's convention); anchor 18:00; flat at 16:59.

Opening range: the N one-minute bars starting at the anchor. Void if any bar is missing.
Entry: first 1-minute CLOSE beyond OR high (long) / below OR low (short) after the range completes;
       both sides on the same bar -> no trade that session; fill at the NEXT bar's open; one trade per session.
Rules: R1 stop = opposite OR edge, target = 10R;  R2 stop = 10% of ATR14 (session true range, prior 14
       sessions), no target;  R3 stop = opposite OR edge, target = 50% of the range width.
Exits: evaluated on bar high/low; STOP FIRST when both touched in one bar; a bar that OPENS through the line
       fills at the open (gap rule GAP-01/02); flat at the session's last bar close.
Comparator C1 (Holmberg 2013, arm A only): threshold lines open*(1 +/- rho), rho = mean + sd * 1.645 of the
       trailing 60 sessions' |open->close| log returns; entry on first close beyond a line; flat at close.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Anchors after the pre-registered volume-profile check (optimize/orb/data/anchor_check.json, 2018-2024 median
# volume per minute): declared pit opens confirmed for 7/9; SI's step is 07:00 (08:20 only 2.1x) and HG's is
# 09:00 (08:20 only 1.1x) -> moved per the pre-registration rule, BEFORE any P/L was computed.
CASH_OPEN = {"NQ": "09:30", "ES": "09:30", "RTY": "09:30", "YM": "09:30",
             "GC": "08:20", "SI": "07:00", "HG": "09:00", "CL": "09:00", "NG": "09:00"}
CASH_CLOSE = {"NQ": "16:00", "ES": "16:00", "RTY": "16:00", "YM": "16:00",
              "GC": "13:30", "SI": "13:30", "HG": "13:00", "CL": "14:30", "NG": "14:30"}
WINDOWS = (5, 15, 30, 60)
RULES = ("R1", "R2", "R3")


@dataclass
class Trade:
    session: str
    direction: str
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str
    or_high: float
    or_low: float
    points: float


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def sessionize(df: pd.DataFrame, arm: str, tok: str) -> pd.DataFrame:
    """Add session id, minute-of-session index and the in-session flags."""
    d = df.copy()
    dt = pd.to_datetime(d["datetime"])
    mod = dt.dt.hour * 60 + dt.dt.minute
    if arm == "globex":
        sess_date = (dt + pd.Timedelta(hours=6)).dt.normalize()      # 18:00 -> next day
        anchor = _hm("18:00"); close = _hm("16:59")
        in_sess = np.ones(len(d), dtype=bool)
        # minutes since anchor (18:00 = 0 ... 16:59 next day = 1379)
        msa = np.where(mod >= anchor, mod - anchor, mod + 24 * 60 - anchor)
    else:
        sess_date = dt.dt.normalize()
        anchor = _hm(CASH_OPEN[tok]); close = _hm(CASH_CLOSE[tok])
        in_sess = (mod >= anchor) & (mod <= close)
        msa = mod - anchor
    d["session"] = sess_date.dt.strftime("%Y-%m-%d")
    d["msa"] = msa
    d["in_sess"] = in_sess
    d["dt"] = dt
    return d


def session_atr(sess_ohlc: pd.DataFrame, n: int = 14) -> pd.Series:
    """ATR over prior n sessions from session OHLC (shifted: uses only completed sessions)."""
    h, l, c = sess_ohlc["high"], sess_ohlc["low"], sess_ohlc["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().shift(1)


def run_cell(df: pd.DataFrame, arm: str, tok: str, N: int, rule: str,
             point_value: float = 1.0) -> pd.DataFrame:
    """One (arm, instrument, window, rule) cell -> trade book (one row per trade)."""
    d = sessionize(df, arm, tok)
    d = d[d["in_sess"]]
    trades: list[Trade] = []
    # session OHLC for ATR (rule R2) — built from the in-session bars
    g = d.groupby("session", sort=True)
    sess = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    atr = session_atr(sess) if rule == "R2" else None
    o = d["open"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy(); c = d["close"].to_numpy()
    msa = d["msa"].to_numpy(); dts = d["dt"].to_numpy()
    for sid, idx in g.indices.items():
        m = msa[idx]
        rng = idx[(m >= 0) & (m < N)]
        if len(rng) != N or not np.array_equal(msa[rng], np.arange(N)):
            continue                                           # void range (missing bars)
        orh = h[rng].max(); orl = l[rng].min()
        after = idx[m >= N]
        if len(after) < 2:
            continue
        ca = c[after]
        up = ca > orh; dn = ca < orl
        first = np.argmax(up | dn) if (up | dn).any() else -1
        if first < 0 or (up[first] and dn[first]):
            continue
        direction = "long" if up[first] else "short"
        ei = first + 1                                          # fill at next bar open
        if ei >= len(after):
            continue
        bars = after[ei:]
        entry = o[bars[0]]
        width = orh - orl
        if rule == "R1":
            stop = orl if direction == "long" else orh
            r = abs(entry - stop)
            target = entry + 10 * r if direction == "long" else entry - 10 * r
        elif rule == "R2":
            a = atr.get(sid, np.nan)
            if not np.isfinite(a) or a <= 0:
                continue
            stop = entry - 0.10 * a if direction == "long" else entry + 0.10 * a
            target = np.nan
        else:  # R3
            stop = orl if direction == "long" else orh
            target = entry + 0.5 * width if direction == "long" else entry - 0.5 * width
        if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
            continue                                           # degenerate (entry gapped past the stop)
        exit_price = c[bars[-1]]; exit_i = bars[-1]; reason = "EOD"
        for j in bars:
            oj, hj, lj = o[j], h[j], l[j]
            if direction == "long":
                if lj <= stop:
                    exit_price = oj if oj <= stop else stop; exit_i = j; reason = "STOP"; break
                if np.isfinite(target) and hj >= target:
                    exit_price = oj if oj >= target else target; exit_i = j; reason = "TARGET"; break
            else:
                if hj >= stop:
                    exit_price = oj if oj >= stop else stop; exit_i = j; reason = "STOP"; break
                if np.isfinite(target) and lj <= target:
                    exit_price = oj if oj <= target else target; exit_i = j; reason = "TARGET"; break
        pts = (exit_price - entry) if direction == "long" else (entry - exit_price)
        trades.append(Trade(sid, direction, pd.Timestamp(dts[bars[0]]), float(entry), pd.Timestamp(dts[exit_i]),
                            float(exit_price), reason, float(orh), float(orl), float(pts)))
    out = pd.DataFrame([t.__dict__ for t in trades])
    if len(out):
        out["pnl"] = out["points"] * point_value
    return out


def run_c1(df: pd.DataFrame, tok: str, point_value: float = 1.0, lookback: int = 60, q: float = 1.645) -> pd.DataFrame:
    """Holmberg 2013 comparator on the cash session: threshold = open*(1 +/- rho)."""
    d = sessionize(df, "cash", tok)
    d = d[d["in_sess"]]
    g = d.groupby("session", sort=True)
    sess = g.agg(open=("open", "first"), close=("close", "last"))
    ret = np.log(sess["close"] / sess["open"]).abs()
    rho = (ret.rolling(lookback).mean() + q * ret.rolling(lookback).std()).shift(1)
    o = d["open"].to_numpy(); c = d["close"].to_numpy(); dts = d["dt"].to_numpy()
    trades = []
    for sid, idx in g.indices.items():
        r = rho.get(sid, np.nan)
        if not np.isfinite(r):
            continue
        op = o[idx[0]]; up_l = op * (1 + r); dn_l = op * (1 - r)
        ca = c[idx]
        up = ca > up_l; dn = ca < dn_l
        if not (up | dn).any():
            continue
        first = int(np.argmax(up | dn))
        if first + 1 >= len(idx):
            continue
        direction = "long" if up[first] else "short"
        ei = idx[first + 1]; entry = o[ei]; xi = idx[-1]; exit_price = c[xi]
        pts = (exit_price - entry) if direction == "long" else (entry - exit_price)
        trades.append(Trade(sid, direction, pd.Timestamp(dts[ei]), float(entry), pd.Timestamp(dts[xi]), float(exit_price),
                            "EOD", float(up_l), float(dn_l), float(pts)))
    out = pd.DataFrame([t.__dict__ for t in trades])
    if len(out):
        out["pnl"] = out["points"] * point_value
    return out
