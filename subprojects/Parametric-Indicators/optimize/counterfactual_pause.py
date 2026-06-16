"""Counterfactual pause attribution — does the champion's no-entry pause cost money? READ-ONLY.

For the 4h champion, every blocked box signal (vol-gated / vetoed / confirm<K) is simulated as an ISOLATED
trade with the champion's exact SL/TP exit (reusing fast_backtest), and bucketed into a per-filter P/L
ledger. Box-silent bars (no signal) are characterized by price displacement. Verdict per filter:
over-filtering (positive expectancy ⇒ relaxing is justified) vs correctly filtering (accept the pause).

Run:  python3 -m optimize.counterfactual_pause [--tf 4h] [--out optimize/results/counterfactual_pause_4h.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import config                                              # noqa: E402
from optimize import two_stage as TS                       # noqa: E402
from optimize.fast_engine import fast_backtest             # noqa: E402
from indicators import library, runner                     # noqa: E402

CAUSES = ["box_silence", "vol_gated", "vetoed", "confirm<K", "would_enter"]


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


def load_champion(tf: str = "4h"):
    """Reuse diagnose_pause's setup: champion ctx + the vol/veto/confirm masks + champion params."""
    ctx = TS._Ctx(tf, split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=True)
    if not ctx.has_champion:
        raise SystemExit("no champion seed found (need optimize/results/wsh4_champions_full.json)")
    d, d1, box, vf, n_split = ctx.df_dec, ctx.df1, ctx.box, ctx.vf, ctx.n_split
    bar_td = ctx.tf.bar_td
    cont = ctx.champ_cont
    gate_pct = float(cont["gate_pct"]); K = int(cont["k"])
    params = ctx.build_params(ctx.champ_en, ctx.champ_flip, cont)
    inds = library.from_specs([s for s in params["indicators"] if s.get("enabled")])
    n = len(d)
    sig = np.asarray(ctx.sig_int)[:n]

    vol_gate = np.ones(n, dtype=bool)
    if gate_pct > 0:
        gthr = float(np.percentile(vf[:n_split], gate_pct))
        vol_gate = vf[:n] <= gthr
    src = runner.indicator_source_1min(d, d1, bar_td)
    votes = runner.compute_votes(d, box, inds, src=src)
    veto = np.asarray(runner.veto_mask(d, box, inds, src=src, votes=votes))[:n]
    confirm = np.asarray(runner.confirm_mask(d, box, inds, K, src=src, votes=votes))[:n]
    return dict(ctx=ctx, d=d, d1=d1, box=box, n=n, sig=sig, vol_gate=vol_gate, veto=veto,
                confirm=confirm, params=params, pv=float(config.NQ_POINT_VALUE),
                bar_td=bar_td, gate_pct=gate_pct, K=K)
