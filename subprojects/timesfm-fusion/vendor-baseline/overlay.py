#!/usr/bin/env python3
"""OVERLAY experiment: can a TimesFM filter improve the REFERENCE strategy's Return/DD?

We take the reference backtester's ACTUAL trade log (its real entries + realized P/L), align each
trade to the TimesFM forecast available at the bar *before* entry (strictly causal), and test simple
filters that DROP trades:
  - agree : keep a trade only if TimesFM's median direction agrees with the trade's direction
  - volgate: keep a trade only if TimesFM's forecast uncertainty (band) at entry is below a percentile

Filters are tuned on the first 70% of trades (TRAIN) and applied to the last 30% (TEST). We compare
the filtered TEST book against the reference's own unfiltered TEST book — same trades, minus the ones
TimesFM vetoes. If Return/DD rises while most P/L survives, the overlay adds value.

    python overlay.py ES 1h
    python overlay.py NQ 1h
Requires the (instrument)_1h_full TimesFM forecast cache (run run_diag first).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from tfm.data import DEFAULT_DATA_DIR, INSTRUMENTS, load_tf
from tfm.forecast_cache import forecast_arrays
from tfm.forecaster import get_forecaster
from tfm.strategy import _DECILE_SPAN_SIGMAS

LOG_NAME = {"ES": "es_run_mtf_log.csv", "NQ": "nq_run_mtf_log.csv"}


def _stats(pnls: np.ndarray) -> dict:
    n = len(pnls)
    if n == 0:
        return dict(n=0, pnl=0.0, dd=0.0, ret_dd=0.0, win=0.0, pf=0.0)
    eq = np.cumsum(pnls)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    wins = pnls[pnls > 0]; losses = pnls[pnls < 0]
    pf = float(wins.sum() / -losses.sum()) if losses.sum() != 0 else float("inf")
    return dict(n=n, pnl=float(pnls.sum()), dd=dd,
                ret_dd=float(pnls.sum() / dd) if dd else float("inf"),
                win=100.0 * len(wins) / n, pf=pf)


def _fmt(s: dict, tag: str) -> str:
    rd = "inf" if s["ret_dd"] == float("inf") else f"{s['ret_dd']:.2f}"
    pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
    return (f"  {tag:22} n={s['n']:>4}  pnl=${s['pnl']:>10,.0f}  "
            f"maxDD=${s['dd']:>9,.0f}  ret/DD={rd:>6}  win={s['win']:.0f}%  PF={pf}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    inst_name = (sys.argv[1] if len(sys.argv) > 1 else "ES").upper()
    tf = sys.argv[2] if len(sys.argv) > 2 else "1h"
    horizon = int(sys.argv[3]) if len(sys.argv) > 3 else 24

    inst = INSTRUMENTS[inst_name]
    df = load_tf(inst_name, tf)
    close = df["close"].to_numpy(float)
    idx_of_time = {pd.Timestamp(t): k for k, t in enumerate(df["datetime"])}

    med, qlo, qhi = forecast_arrays(df, get_forecaster("timesfm"), 512, horizon,
                                    cache_key=f"{inst_name}_{tf}_full")
    sigma = (qhi - qlo) / _DECILE_SPAN_SIGMAS
    rel_sigma = sigma / close       # STATIONARY volatility fraction (price level drifts over time)
    tfm_dir = np.sign(med - close)  # median-vs-close drift direction at each bar

    # --- load the reference strategy's real trades ---
    log = pd.read_csv(DEFAULT_DATA_DIR / LOG_NAME[inst_name])
    ent = log[log["decision"] == "entry"].copy()
    ent["datetime"] = pd.to_datetime(ent["datetime"])

    rows = []
    for _, r in ent.iterrows():
        k = idx_of_time.get(pd.Timestamp(r["datetime"]))
        if k is None or k - 1 < 0 or np.isnan(med[k - 1]):
            # no causal forecast available at the pre-entry bar -> keep trade, no veto info
            rows.append((r["datetime"], r["pnl"], 0, np.nan, np.nan))
            continue
        d = 1 if str(r["direction"]).lower() == "long" else -1
        agree = int(np.sign(tfm_dir[k - 1]) == d)
        rows.append((r["datetime"], float(r["pnl"]), agree, float(rel_sigma[k - 1]), d,
                     str(r.get("position_owner", ""))))

    tr = pd.DataFrame(rows, columns=["dt", "pnl", "agree", "sigma", "dir", "owner"]).sort_values("dt")
    tr = tr.reset_index(drop=True)
    cut = int(round(len(tr) * 0.70))
    train, test = tr.iloc[:cut], tr.iloc[cut:]

    # sigma percentile thresholds from TRAIN only
    valid_sig = train["sigma"].dropna()
    print(f"=== OVERLAY — {inst_name} {tf} (TimesFM filter on the reference's own trades) ===")
    print(f"  total ref trades: {len(tr)}   train {len(train)} / test {len(test)}\n")

    def apply(mask_col_fn, sub):
        keep = mask_col_fn(sub)
        return _stats(sub["pnl"].to_numpy()[keep])

    # candidate filters, tuned on TRAIN by ret/DD, then shown on TEST
    candidates = {}
    candidates["baseline (all)"] = (lambda s: np.ones(len(s), bool))
    candidates["agree-only"] = (lambda s: (s["agree"].to_numpy() == 1) | s["sigma"].isna().to_numpy())
    for pct in (80, 60, 40):
        thr = float(np.percentile(valid_sig, pct)) if len(valid_sig) else np.inf
        candidates[f"volgate<=p{pct}"] = (lambda s, thr=thr: (s["sigma"].to_numpy() <= thr) | s["sigma"].isna().to_numpy())
        candidates[f"agree & vol<=p{pct}"] = (
            lambda s, thr=thr: (((s["agree"].to_numpy() == 1) & (s["sigma"].to_numpy() <= thr)) | s["sigma"].isna().to_numpy()))

    print("-- TRAIN (filter selection) --")
    train_scores = {}
    for name, fn in candidates.items():
        st = apply(fn, train); train_scores[name] = st
        print(_fmt(st, name))

    # pick best non-baseline by TRAIN ret/DD that keeps >=60% of baseline trades
    base_n = train_scores["baseline (all)"]["n"]
    best = max((k for k in candidates if k != "baseline (all)"),
               key=lambda k: (train_scores[k]["ret_dd"] if train_scores[k]["n"] >= 0.5 * base_n else -1))

    print("\n-- TEST (out-of-sample) --")
    print(_fmt(apply(candidates["baseline (all)"], test), "baseline (all)"))
    print(_fmt(apply(candidates[best], test), f"BEST: {best}"))

    # --- CAUSAL expanding-window gate over the WHOLE period (no tuning, no peeking) ---
    # For each trade, threshold = percentile of PRIOR trades' rel_sigma (expanding, min 40 history).
    # Fully causal: a live system would know exactly this. This is the most honest single number.
    print("\n-- CAUSAL expanding gate over FULL period (no in-sample tuning) --")
    sig = tr["sigma"].to_numpy()
    pnl = tr["pnl"].to_numpy()
    for pct in (85, 75, 65):
        keep = np.ones(len(tr), bool)
        for j in range(len(tr)):
            hist = sig[:j][~np.isnan(sig[:j])]
            if np.isnan(sig[j]) or len(hist) < 40:
                continue  # not enough history -> don't veto
            keep[j] = sig[j] <= np.percentile(hist, pct)
        print(_fmt(_stats(pnl[keep]), f"causal vol<=p{pct}"))
    print(_fmt(_stats(pnl), "baseline (all)"))

    # --- CAUSAL vol-target SIZING (scale size inversely with forecast vol, don't just drop) ---
    # size_i = clip(target / rel_sigma_i, lo, hi), target = expanding median of prior rel_sigma.
    # Scaling 1 contract -> f contracts scales that trade's P/L (and its DD contribution) by f.
    print("\n-- CAUSAL vol-target sizing (expanding median target) --")
    for lo, hi in ((0.5, 2.0), (0.33, 3.0)):
        size = np.ones(len(tr))
        for j in range(len(tr)):
            hist = sig[:j][~np.isnan(sig[:j])]
            if np.isnan(sig[j]) or len(hist) < 40:
                continue
            size[j] = np.clip(np.median(hist) / sig[j], lo, hi)
        print(_fmt(_stats(pnl * size), f"size in [{lo},{hi}]"))

    # --- ROBUSTNESS: canonical causal p80 gate, per-quarter + dropped-trade profile ---
    keep80 = np.ones(len(tr), bool)
    for j in range(len(tr)):
        hist = sig[:j][~np.isnan(sig[:j])]
        if not np.isnan(sig[j]) and len(hist) >= 40:
            keep80[j] = sig[j] <= np.percentile(hist, 80)
    dropped = ~keep80
    print("\n-- ROBUSTNESS: causal p80 gate across 4 chronological quarters --")
    qidx = np.array_split(np.arange(len(tr)), 4)
    for qi, q in enumerate(qidx, 1):
        b = _stats(pnl[q]); g = _stats(pnl[q][keep80[q]])
        brd = "inf" if b["ret_dd"] == float("inf") else f"{b['ret_dd']:.1f}"
        grd = "inf" if g["ret_dd"] == float("inf") else f"{g['ret_dd']:.1f}"
        print(f"  Q{qi}: baseline retDD={brd:>5} (n={b['n']}, pnl=${b['pnl']:,.0f})  ->  "
              f"gated retDD={grd:>5} (n={g['n']}, pnl=${g['pnl']:,.0f})")
    dp = tr.loc[dropped]
    print(f"\n  dropped {int(dropped.sum())} trades, net ${pnl[dropped].sum():,.0f} "
          f"(kept {int(keep80.sum())} net ${pnl[keep80].sum():,.0f})")
    if len(dp):
        print(f"    by owner: " + ", ".join(f"{o}={int((dp['owner']==o).sum())}"
              for o in dp['owner'].unique()))
        print(f"    long={int((dp['dir']==1).sum())} short={int((dp['dir']==-1).sum())}  "
              f"win%={100*(dp['pnl']>0).mean():.0f}  avg${dp['pnl'].mean():,.0f}")


if __name__ == "__main__":
    main()
