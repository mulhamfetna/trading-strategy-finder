"""H.6 — walk-forward fold scoring (TASK.md D4).

Splits the decision frame into K equal-CALENDAR-TIME-span folds and scores a single parameter set
across them. Per-trial objective (for NSGA-II, H.7):
  objective = (median fold P/L, worst-fold maxDD)
  - median P/L rewards consistency across regimes (not one lucky fold);
  - worst-fold maxDD is the conservative drawdown (TASK.md §9-d).

Causality: the volatility GATE threshold for each scored fold is frozen on the data BEFORE that
fold (expanding causal reference). Fold 0 is therefore a warmup/reference only and is NOT scored;
folds 1..K-1 are scored. A trial is INVALID (pruned) if any scored fold has < min_trades trades.

State isolation: each fold runs an independent backtest_metrics() call (the engine + breaker carry
no state between calls), so folds never leak equity/breaker state into one another.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize.core import backtest_metrics  # noqa: E402

_MIN_BARS_PER_FOLD = 30


def split_folds(df_dec: pd.DataFrame, k: int) -> list[tuple[int, int]]:
    """Return k (lo, hi) index ranges splitting df_dec into equal calendar-time spans.
    Equal-time (not equal-count) so each fold covers the same wall-clock duration."""
    if k < 2:
        raise ValueError("fold count must be >= 2")
    t = pd.to_datetime(df_dec["Date"]).to_numpy()
    t0, t1 = t[0], t[-1]
    edges = [t0 + (t1 - t0) * (j / k) for j in range(k + 1)]
    ranges = []
    for j in range(k):
        lo = int(np.searchsorted(t, edges[j], side="left"))
        hi = int(np.searchsorted(t, edges[j + 1], side="left")) if j < k - 1 else len(t)
        ranges.append((lo, hi))
    return ranges


def score_walkforward(df_dec, df1, box, vf, params, bar_duration,
                      k: int = 5, min_trades: int = 5, sig_int=None, contrib=None) -> dict:
    """Score one parameter set across K folds. Returns dict with the objective + per-fold detail.
    sig_int: optional precomputed per-decision-bar signal array (full length) — sliced per fold to
    avoid recomputing the param-independent signals on every trial."""
    ranges = split_folds(df_dec, k)
    folds = []
    valid = True
    # EARLY PRUNE: a trial is invalid iff ANY scored fold has < min_trades (or too few bars). The
    # moment that happens the trial is already doomed (the caller raises TrialPruned and skips the
    # full-period backtest), so we BREAK out of the fold loop instead of computing the remaining
    # folds. This is result-identical — the valid/invalid verdict and every kept (valid) trial's
    # objectives are unchanged; only wasted compute on doomed trials is saved. (Optuna's statistical
    # median/ASHA pruners are single-objective only and don't apply to this 3-objective study, so
    # this deterministic early-exit is the multi-objective-safe equivalent.)
    for j, (lo, hi) in enumerate(ranges):
        if j == 0:
            continue  # fold 0 = causal gate reference / warmup; not scored
        if hi - lo < _MIN_BARS_PER_FOLD:
            valid = False
            folds.append({"fold": j, "skipped": "too few bars"})
            break
        fdec = df_dec.iloc[lo:hi].reset_index(drop=True)
        fvf = vf[lo:hi]
        fsig = sig_int[lo:hi] if sig_int is not None else None
        # contributor masks (full-length) sliced to this fold — same cadence as sig_int (computed once
        # per trial over the full frame; absent ⇒ None ⇒ unchanged path).
        cfold = None
        if contrib is not None:
            cfold = {"veto": np.asarray(contrib["veto"])[lo:hi],
                     "parsed": [(cc[lo:hi], k_es, has) for (cc, k_es, has) in contrib["parsed"]],
                     "topology": contrib["topology"]}
        gate_ref = vf[:lo] if lo > 0 else fvf            # causal: gate frozen on prior data
        p = dict(params); p["window"] = "full"
        m = backtest_metrics(fdec, df1, box, fvf, len(fdec), p, bar_duration,
                             gate_ref_vf=gate_ref, sig_int=fsig, contrib=cfold)
        m["fold"] = j
        folds.append(m)
        if m.get("n_taken", 0) < min_trades:
            valid = False
            break                                        # doomed trial ⇒ stop scoring further folds

    scored = [f for f in folds if "pnl" in f]
    if not scored:
        return {"valid": False, "median_pnl": 0.0, "worst_dd": 0.0, "median_win": 0.0,
                "total_pnl": 0.0, "folds": folds}
    pnls = np.array([f["pnl"] for f in scored])
    dds = np.array([f["max_dd"] for f in scored])
    wins = np.array([f.get("win", 0.0) for f in scored])   # per-fold win-rate %
    return {
        "valid": valid,
        "median_pnl": float(np.median(pnls)),
        "worst_dd": float(dds.max()),
        "median_win": float(np.median(wins)),               # WS-I.8 3rd objective (win-rate)
        "total_pnl": float(pnls.sum()),
        "n_folds_scored": len(scored),
        "folds": folds,
    }
