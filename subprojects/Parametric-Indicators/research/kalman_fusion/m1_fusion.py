"""M1 — champion-signal fusion (directional classifier for the champion's dropped 4h signals).
Phase 2a: static weighted vote over finer NQ timeframes. Reuses the Phase-1 rig + M0 ceiling.
Causal by construction (finer bar CLOSED <= 4h signal-bar close); exits unchanged (payoff pinned)."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401  (path insert)
from optimize import data as data_mod
from optimize import signals as sig_mod
from optimize import timeframes as TF
from optimize.fast_engine import signals_to_int


def finer_tf_directions(C, tfs=("1h", "15m", "5m")):
    """int8[n, T] causal box-direction observations: one column per finer TF (last bar CLOSED <= the 4h
    signal bar's close) + a final '4h' column = the 4h box direction read at i-1."""
    dec_start = C["d"]["Date"].to_numpy("datetime64[ns]")        # 4h bar START; contiguous ⇒ bar i start == bar i-1 close
    n = int(C["n"])
    cols_data = []
    for tf in tfs:
        d, _, box, _, _ = data_mod.load_inputs(tf, "NQ")
        dirs = signals_to_int(sig_mod.decision_signals(d, box)).astype(np.int8)
        ftd = TF.get(tf).bar_td.to_timedelta64()
        finer_close = d["Date"].to_numpy("datetime64[ns]") + ftd  # finer bar CLOSE time
        # last finer bar whose CLOSE <= the 4h signal-bar (i-1) close (== 4h bar i start). searchsorted only
        # looks backward ⇒ look-ahead safe.
        j = np.searchsorted(finer_close, dec_start, side="right") - 1
        col = np.where(j >= 0, dirs[np.clip(j, 0, len(dirs) - 1)], 0).astype(np.int8)
        cols_data.append(col)
    # 4h voter = the 4h box direction read at i-1 (the signal bar); bar 0 has no predecessor ⇒ 0.
    sig = np.asarray(C["sig"]).astype(np.int8)[:n]
    four_h = np.zeros(n, dtype=np.int8)
    four_h[1:] = np.sign(sig[:-1]).astype(np.int8)
    Z = np.column_stack(cols_data + [four_h]).astype(np.int8)
    return Z, list(tfs) + ["4h"]


import config                                    # noqa: E402
from research.kalman_fusion.ceiling import signal_outcomes


def n_split(C) -> int:
    return int((C["d"]["Date"].dt.year == config.YEARS[0]).sum())


def profitable_side(C, idxs) -> np.ndarray:
    o = signal_outcomes(C, idxs)                 # native(+1 long) vs opposite(-1 short) $ P/L
    ps = np.zeros(len(idxs), dtype=np.int8)
    both = ~np.isnan(o["native"]) & ~np.isnan(o["opposite"])
    ps[both & (o["native"] >= o["opposite"])] = 1
    ps[both & (o["native"] < o["opposite"])] = -1
    only_nat = ~np.isnan(o["native"]) & np.isnan(o["opposite"]); ps[only_nat] = 1
    only_opp = np.isnan(o["native"]) & ~np.isnan(o["opposite"]); ps[only_opp] = -1
    return ps


def fit_weights(Z, C, idxs_is) -> np.ndarray:
    """Per-column reliability weight from 2025 dropped signals: max(0, 2*hit_rate - 1)."""
    idxs_is = list(idxs_is)
    ps = profitable_side(C, idxs_is)
    T = Z.shape[1]
    w = np.zeros(T, dtype=float)
    for t in range(T):
        hits = tot = 0
        for k, i in enumerate(idxs_is):
            d = int(Z[i, t]); s = int(ps[k])
            if d != 0 and s != 0:
                tot += 1; hits += (d == s)
        hr = (hits / tot) if tot else 0.5
        w[t] = max(0.0, 2.0 * hr - 1.0)
    return w


from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped


def fused(z_row, w):
    z = np.asarray(z_row, dtype=float); w = np.asarray(w, dtype=float)
    score = float(np.dot(w, z))
    denom = float(np.sum(np.abs(w) * (z != 0)))
    conv = (abs(score) / denom) if denom > 0 else 0.0
    return int(np.sign(score)), min(1.0, conv)


def policy(C, Z, w, theta):
    n = int(C["n"])
    admit = np.asarray(cp._engine_gate(C)).copy()
    direction = np.zeros(n, dtype=np.int8)
    for i in eligible_dropped(C)["idxs"]:
        d, conv = fused(Z[i], w)
        if d != 0 and conv > theta:
            admit[i] = True
            direction[i - 1] = d
    return admit, direction


import pandas as pd                              # noqa: E402
from research.kalman_fusion import rig           # noqa: E402
from research.kalman_fusion.metrics import summarize


def evaluate_m1(C, Z, w, theta):
    admit, direction = policy(C, Z, w, theta)
    book = rig.run_book(C, admit, direction)
    yr0 = config.YEARS[0]
    is_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year == yr0]
    oos_p = [t["pnl"] for t in book if pd.Timestamp(t["entry_time"]).year != yr0]
    ed = eligible_dropped(C)
    ns = n_split(C)
    is_elig = sum(1 for i in ed["idxs"] if i < ns) + \
              sum(1 for t in cp.champion_taken_trades(C) if pd.Timestamp(t["entry_time"]).year == yr0)
    oos_elig = ed["n_eligible"] - is_elig
    return (summarize(is_p, n_eligible=max(1, is_elig)),
            summarize(oos_p, n_eligible=max(1, oos_elig)))
