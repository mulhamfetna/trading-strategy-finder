"""Self-contained realized-volatility + HAR forecast (no repo imports).

Reproduces the meta-prophet computation exactly for the default 4h bar:
  per decision bar:  rv_pts = sqrt( sum of 1-min squared log-returns within the bar ) * bar_close
  HAR forecast (causal):  vf[i] = 0.5*rv[i-1] + 0.3*mean(rv[i-6:i]) + 0.2*mean(rv[i-30:i])

The HAR forecast `vf` drives the volatility GATE (skip bars whose vf is above a percentile).

WS-H.2 — timeframe generalisation: the realized-vol WINDOW is now the decision-bar duration
(`bar_minutes`, default 240 = 4h), so the same RV-from-1m-closes computation works for any entry
timeframe. The HAR lookback stays in *decision-bar units* (1 / 6 / 30 bars) by design (TASK.md §5.2):
the gate only needs a monotone, causal vol proxy, and keeping bar-count windows makes the gate
self-consistent per timeframe. Default args reproduce the verified 4h forecast exactly (parity-locked).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rv_pts(df4: pd.DataFrame, df1: pd.DataFrame, bar_minutes: int = 240) -> np.ndarray:
    """Per-decision-bar realized volatility in points, from the 1-min closes.

    bar_minutes: decision-bar duration in minutes (240 = 4h, the default/verified case).

    Vectorised (searchsorted binning) — O(M log N) instead of O(N·M); essential for fine
    timeframes (1m has ~487k decision bars). Each 1-min return is assigned to the decision bar
    whose [start, start+dur) window contains it (gaps excluded, exactly as the original per-bar
    `(mt >= T) & (mt < end)` mask), then squared returns are summed per bar. rv[i] = sqrt(sum) *
    close[i], left NaN where fewer than 2 returns fall in the window (matches the original len>1).
    Parity-locked against the 4h winner (test_parity.py).
    """
    m = df1[["Date", "Close"]].copy()
    m["lr"] = np.log(m["Close"] / m["Close"].shift(1))
    mt = m["Date"].to_numpy()
    lr = m["lr"].to_numpy(float)
    starts = df4["Date"].to_numpy()
    closes = df4["Close"].to_numpy(float)
    n = len(starts)
    dur = np.timedelta64(int(bar_minutes), "m")

    # decision-bar index for each 1-min timestamp: last start <= mt
    idx = np.searchsorted(starts, mt, side="right") - 1
    in_win = np.zeros(len(mt), dtype=bool)
    ok = idx >= 0
    # within the bar's OWN window [start, start+dur) — excludes 1m bars sitting in a gap
    in_win[ok] = mt[ok] < (starts[idx[ok]] + dur)
    valid = in_win & ~np.isnan(lr)

    sq = np.zeros(n)
    cnt = np.zeros(n, dtype=np.int64)
    np.add.at(sq, idx[valid], lr[valid] ** 2)
    np.add.at(cnt, idx[valid], 1)
    # Coarser TFs need ≥2 intrabar returns (cnt>=2 ≡ the original cnt>1 → 4h parity preserved).
    # The 1-min decision frame degenerates to ≤1 return per bar (the bar IS a 1-min bar), so accept
    # the single-bar return there — rv becomes that bar's |log-return|·close, a valid vol proxy that
    # HAR then smooths over 1/6/30 bars.
    min_returns = 1 if bar_minutes <= 1 else 2
    rv = np.where(cnt >= min_returns, np.sqrt(sq) * closes, np.nan)
    return rv


def har_forecast(rv: np.ndarray) -> np.ndarray:
    """Causal HAR-RV forecast (uses only past bars). Warmup filled with the median.
    Lookback windows are in decision-bar units (1 / 6 / 30 bars) — see module docstring."""
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    n = len(rv)
    vf = np.full(n, np.nan)
    for i in range(n):
        if i >= 30:
            vf[i] = 0.5 * rv[i - 1] + 0.3 * rv[i - 6:i].mean() + 0.2 * rv[i - 30:i].mean()
    return np.where(np.isfinite(vf), vf, np.nanmedian(vf))


def vol_forecast(df4: pd.DataFrame, df1: pd.DataFrame, bar_minutes: int = 240) -> np.ndarray:
    """HAR-RV forecast for an arbitrary decision timeframe (bar_minutes); default 4h."""
    return har_forecast(compute_rv_pts(df4, df1, bar_minutes=bar_minutes))


def gate_threshold(vf: np.ndarray, n_split: int, gate_pct: float) -> float:
    """The causal volatility-gate threshold: the gate_pct-th percentile of the IN-SAMPLE prefix
    vf[:n_split]. Single source of truth for the seed used by strategy.build_payload,
    l1_runner.run_l1, engine.run_l2, counterfactual_pause and diagnose_pause — so window selection
    can NEVER accidentally re-seed the gate on a windowed/sliced vf (it must always seed on the
    pre-window prefix). Callers keep their own `if gate_pct > 0` guard and apply `vf <= gthr`
    against whichever range (full or windowed) they gate."""
    return float(np.percentile(vf[:n_split], float(gate_pct)))


def gate_thresholds_recal(vf, dates, n_split: int, gate_pct: float, recal_months: int,
                          seed_len: int | None = None, random_pct_seed: int = 0):
    """#198 — per-bar CAUSAL gate thresholds under a fixed recalibration cadence.

    Frozen behaviour (recal_months <= 0) is NOT handled here — callers keep gate_threshold(). This
    function returns an array thr[0:n] where:
      * bars before the first recalibration boundary carry the FROZEN threshold
        percentile(vf[:n_split], gate_pct)  — identical to today's seed;
      * a boundary is the FIRST bar of every recal_months-th calendar month strictly after the bar at
        n_split-1 (calendar convention, never tuned);
      * at each boundary b the threshold becomes percentile(vf[b-L:b], pct) with L = seed_len (default:
        n_split, the same window LENGTH as the frozen seed) — strictly past bars only (causal);
      * random_pct_seed > 0 replaces pct at each boundary with rng.uniform(5, 95) from
        default_rng(random_pct_seed) — the #198 churn control. gate_pct is used otherwise; it is never
        re-fit here (that would be optimization, #186's territory).
    """
    import numpy as _np
    import pandas as _pd
    vf = _np.asarray(vf, dtype=float)
    n = len(vf)
    L = int(seed_len or n_split)
    frozen = float(_np.percentile(vf[:n_split], float(gate_pct)))
    thr = _np.full(n, frozen, dtype=float)
    if recal_months <= 0 or n_split >= n:
        return thr
    months = _pd.PeriodIndex(_pd.DatetimeIndex(_pd.to_datetime(_np.asarray(dates)[:n])), freq="M")
    first_bar_of_month = _np.r_[True, months[1:] != months[:-1]]
    rng = _np.random.default_rng(random_pct_seed) if random_pct_seed > 0 else None
    anchor = None                                     # the month ordinal of the first post-seed boundary
    cur = frozen
    for i in range(n_split, n):
        if first_bar_of_month[i]:
            ordinal = months[i].year * 12 + months[i].month
            if anchor is None:
                anchor = ordinal
            if (ordinal - anchor) % int(recal_months) == 0 and i >= L:
                pct = float(rng.uniform(5, 95)) if rng is not None else float(gate_pct)
                cur = float(_np.percentile(vf[i - L:i], pct))
        thr[i] = cur
    return thr
