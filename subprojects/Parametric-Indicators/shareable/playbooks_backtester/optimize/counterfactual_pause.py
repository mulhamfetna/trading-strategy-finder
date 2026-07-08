"""Minimal bundle version of optimize.counterfactual_pause — only the pure `attribute` labeller the causal
L1 runner needs (byte-identical to the research function). The full research module also imports the
optimizer (optuna) for pause-streak studies; that heavy dependency is unused for a backtest and omitted
here so the shareable bundle stays light (numpy + pandas only)."""
import numpy as np


def attribute(sig, vol_gate, veto, confirm):
    """Label every ENTRY bar idx (1..n-1) by why it did/didn't enter. The signal is read from idx-1
    (engine convention); the gate masks are applied at idx. Returns an object array length n (cause[0]=None)."""
    sig = np.asarray(sig)
    vol_gate = np.asarray(vol_gate, dtype=bool)
    veto = np.asarray(veto, dtype=bool)
    confirm = np.asarray(confirm, dtype=bool)
    n = len(sig)
    cause = np.full(n, None, dtype=object)
    for idx in range(1, n):
        if sig[idx - 1] == 0:
            cause[idx] = "box_silence"
        elif not vol_gate[idx]:
            cause[idx] = "vol_gated"
        elif veto[idx]:
            cause[idx] = "vetoed"
        elif not confirm[idx]:
            cause[idx] = "confirm<K"
        else:
            cause[idx] = "would_enter"
    return cause
