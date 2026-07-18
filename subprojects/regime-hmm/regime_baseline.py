#!/usr/bin/env python3
"""Stage 2 baseline: fit a CAUSAL Gaussian HMM on daily NQ features, label the 2024-26 fusion trades
by their LIVE (filtered) regime, and ask: does one regime concentrate the losing trades / the drawdown?

Causality (the X-thread's core rule): parameters fit on TRAIN (pre-2024) only; features standardized with
TRAIN stats; regime at day t = argmax of the FILTERED forward probability (params + observations <= t) —
never the smoothed posterior or the Viterbi path (those see the whole sequence = lookahead).

Also computes a realized-vol TERCILE regime on the same days as an early dumb-control preview.

Inputs:  NQ_1h.csv (2010-26), nq_2426_mtf_log.csv (fusion book).
Run:     python3 regime_baseline.py <NQ_1h.csv> <fusion_log.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM

TRAIN_END = pd.Timestamp("2024-01-01")
STATES = (2, 3, 4)
RESTARTS = 10


def daily_features(nq_1h_csv):
    df = pd.read_csv(nq_1h_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    df["dt"] = pd.to_datetime(df["datetime"])
    df["date"] = df["dt"].dt.normalize()
    df["lr1h"] = np.log(df["close"]).diff()
    g = df.groupby("date")
    daily = pd.DataFrame({
        "close": g["close"].last(),
        "rv": np.sqrt(g["lr1h"].apply(lambda s: np.nansum(s.values ** 2))),   # intraday realized vol
        "volume": g["volume"].sum(),
    }).dropna()
    daily["ret"] = np.log(daily["close"]).diff()
    daily["logrv"] = np.log(daily["rv"].replace(0, np.nan))
    daily["vol_z"] = (daily["volume"] - daily["volume"].rolling(20).mean()) / daily["volume"].rolling(20).std()
    feat = daily[["ret", "logrv", "vol_z"]].dropna()
    return feat


def fit_hmm(Xtr, n, restarts):
    best, best_ll = None, -np.inf
    for seed in range(restarts):
        try:
            m = GaussianHMM(n_components=n, covariance_type="full", n_iter=500, random_state=seed)
            m.fit(Xtr)
            ll = m.score(Xtr)
            if ll > best_ll:
                best_ll, best = ll, m
        except Exception:
            continue
    return best, best_ll


def bic(ll, n, k, T):
    n_params = n * (n - 1) + n * k + n * k * (k + 1) // 2 + (n - 1)  # trans + means + full cov + init
    return -2 * ll + n_params * np.log(T)


def filtered_states(model, X):
    """Causal forward-algorithm filtered regime (argmax), using params + observations up to t only."""
    n, K = model.n_components, X.shape[1]
    em = np.zeros((len(X), n))
    for i in range(n):
        em[:, i] = multivariate_normal.pdf(X, mean=model.means_[i], cov=model.covars_[i], allow_singular=True)
    filt = np.zeros((len(X), n))
    a = model.startprob_ * em[0]; a /= a.sum() or 1
    filt[0] = a
    for t in range(1, len(X)):
        a = (filt[t - 1] @ model.transmat_) * em[t]
        s = a.sum(); a = a / s if s else np.ones(n) / n
        filt[t] = a
    return filt.argmax(1), filt


def dd(pnls):
    eq = np.cumsum(pnls); return float((np.maximum.accumulate(eq) - eq).max()) if len(pnls) else 0.0


def stats(p):
    p = np.asarray(p, float); d = dd(p)
    return dict(n=len(p), pnl=p.sum(), dd=d, rdd=(p.sum() / d if d else float("inf")),
                win=100 * (p > 0).mean() if len(p) else 0)


def main():
    nq_csv = sys.argv[1]; book_csv = sys.argv[2]
    feat = daily_features(nq_csv)
    tr = feat[feat.index < TRAIN_END]
    mu, sd = tr.mean(), tr.std()
    Z = ((feat - mu) / sd).to_numpy()
    Ztr = ((tr - mu) / sd).to_numpy()
    print(f"daily features: {len(feat)} days {feat.index.min().date()}..{feat.index.max().date()}  train={len(tr)}")

    # pick #states by BIC on train
    rows = []
    for n in STATES:
        m, ll = fit_hmm(Ztr, n, RESTARTS)
        if m is None: continue
        b = bic(ll, n, Ztr.shape[1], len(Ztr))
        rows.append((n, ll, b, m)); print(f"  HMM n={n}: logL={ll:.1f} BIC={b:.1f}")
    n_best, _, _, model = min(rows, key=lambda r: r[2])
    print(f"chosen n_states={n_best} (min BIC)")

    reg, filt = filtered_states(model, Z)
    # order regimes by realized-vol emission mean (feature index 1 = logrv), so higher = more turbulent
    order = np.argsort(model.means_[:, 1])
    rank = {s: i for i, s in enumerate(order)}       # 0=calmest ... n-1=most turbulent
    reg_ranked = np.array([rank[s] for s in reg])
    daily_reg = pd.Series(reg_ranked, index=feat.index)

    # realized-vol tercile (dumb-control preview) on the same daily logrv
    rv = feat["logrv"]
    terc = pd.qcut(rv, 3, labels=[0, 1, 2]).astype(int)

    # label fusion trades by entry-day regime
    log = pd.read_csv(book_csv)
    ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent["reg"] = ent["date"].map(daily_reg)
    ent["terc"] = ent["date"].map(terc)
    ent = ent.dropna(subset=["reg"])
    pnl = ent["pnl"].to_numpy(float)

    base = stats(pnl)
    print(f"\n=== fusion trades labeled: {len(ent)} (of {len(log[log.decision=='entry'])}) ===")
    print(f"  ALL: n={base['n']} P/L=${base['pnl']:,.0f} DD=${base['dd']:,.0f} Ret/DD={base['rdd']:.2f} win={base['win']:.1f}%")

    print(f"\n=== HMM regime (0=calmest .. {n_best-1}=most turbulent), conditioned ===")
    for r in range(n_best):
        s = stats(pnl[ent["reg"].to_numpy() == r])
        days = int((daily_reg == r).sum())
        print(f"  regime {r}: trades={s['n']:>4} P/L=${s['pnl']:>9,.0f} DD=${s['dd']:>8,.0f} Ret/DD={s['rdd']:>6.2f} win={s['win']:.0f}%  ({days} days)")
    # sit-out the most turbulent regime
    keep = ent["reg"].to_numpy() < (n_best - 1)
    so = stats(pnl[keep])
    print(f"  SIT-OUT top regime: n={so['n']} P/L=${so['pnl']:,.0f} DD=${so['dd']:,.0f} Ret/DD={so['rdd']:.2f}  (base Ret/DD {base['rdd']:.2f})")

    print(f"\n=== realized-vol tercile (dumb-control preview) ===")
    for r in range(3):
        s = stats(pnl[ent["terc"].to_numpy() == r])
        print(f"  tercile {r}: trades={s['n']:>4} P/L=${s['pnl']:>9,.0f} DD=${s['dd']:>8,.0f} Ret/DD={s['rdd']:>6.2f}")
    keept = ent["terc"].to_numpy() < 2
    st = stats(pnl[keept])
    print(f"  SIT-OUT top tercile: n={st['n']} P/L=${st['pnl']:,.0f} DD=${st['dd']:,.0f} Ret/DD={st['rdd']:.2f}")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
