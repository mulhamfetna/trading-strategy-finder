"""The three PRE-REGISTERED context splits. All causal: computable at 08:29 on the release morning.

Exactly three, fixed in the spec before any number was seen. A wider sweep would re-enter the
multiple-comparisons trap Exp 43's Bonferroni correction already caught this project in.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

UNLABELLED = ""


def label_c1_policy_regime(sur: pd.DataFrame, ret_col: str, k: int) -> np.ndarray:
    """C1 (PRIMARY) -- 'good news is good' vs 'good news is bad', from the market's own recent behaviour.

    For release i, take the STRICTLY PRIOR k releases and compute the Spearman correlation between their
    surprise and their forward return. Positive => the market has lately been treating good news as good.

    Deliberately NOT a hard-coded 2022 break: that would borrow the answer from the literature ("Fearing
    the Fed" tells us to expect a flip around then, so splitting on that date would be assuming what we
    are trying to measure). This proxy is knowable in real time, so a positive result would be actionable
    rather than hindsight.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    z = sur["surprise_z"].to_numpy(dtype=float)
    r = sur[ret_col].to_numpy(dtype=float)
    n = len(sur)
    out = np.full(n, UNLABELLED, dtype=object)
    for i in range(k, n):
        zz, rr = z[i - k:i], r[i - k:i]
        ok = ~np.isnan(zz) & ~np.isnan(rr)
        if ok.sum() < 3:
            continue
        rho = spearmanr(zz[ok], rr[ok]).statistic
        if np.isnan(rho):
            continue
        out[i] = "POS" if rho > 0 else "NEG"
    return out


def label_c2_vol_regime(sur: pd.DataFrame, regime_csv: Path) -> np.ndarray:
    """C2 -- calm vs turbulent, reusing the causal HMM daily labels from the regime-edge workstream.

    Those labels were built causally (each day's regime uses only prior data), so reusing them adds no
    look-ahead. A release whose date is absent from the label file is left UNLABELLED rather than guessed.
    """
    reg = pd.read_csv(regime_csv, parse_dates=["date"])
    m = dict(zip(reg["date"].dt.normalize(), reg["regime"]))
    med = float(np.median(reg["regime"].to_numpy(dtype=float)))
    out = np.full(len(sur), UNLABELLED, dtype=object)
    for i, ts in enumerate(sur["Date"]):
        g = m.get(pd.Timestamp(ts).normalize())
        if g is None:
            continue
        out[i] = "CALM" if float(g) <= med else "TURBULENT"
    return out


def label_c3_trend(sur: pd.DataFrame, df1: pd.DataFrame, ma_days: int) -> np.ndarray:
    """C3 -- is price above or below its trailing ma_days moving average at the release?

    The MA is evaluated on the last daily close STRICTLY BEFORE the release day, so nothing from the
    release day itself (let alone after the print) can enter the label.
    """
    if ma_days < 2:
        raise ValueError(f"ma_days must be >= 2, got {ma_days}")
    px = df1[["Date", "Close"]].copy()
    px["day"] = pd.DatetimeIndex(px["Date"]).normalize()
    daily = px.groupby("day")["Close"].last().sort_index()
    ma = daily.rolling(ma_days).mean()

    days = daily.index.to_numpy()
    out = np.full(len(sur), UNLABELLED, dtype=object)
    for i, ts in enumerate(sur["Date"]):
        day = pd.Timestamp(ts).normalize()
        j = int(np.searchsorted(days, np.datetime64(day)))   # first index >= day
        if j == 0:
            continue                                          # no prior day at all
        last = days[j - 1]
        m, c = ma.get(last, np.nan), daily.get(last, np.nan)
        if np.isnan(m) or np.isnan(c):
            continue
        out[i] = "UP" if c > m else "DOWN"
    return out
