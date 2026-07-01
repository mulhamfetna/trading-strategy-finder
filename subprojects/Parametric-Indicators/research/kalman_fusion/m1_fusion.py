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
