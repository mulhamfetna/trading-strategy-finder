#!/usr/bin/env python3
"""Jump Model penalty grid — find non-degenerate regimes, test sit-out-calmest-1 vs base."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from regime_baseline import daily_features, stats, TRAIN_END
from jumpmodels.jump import JumpModel

feat = daily_features(sys.argv[1])
tr = feat[feat.index < TRAIN_END]
mu, sd = tr.mean(), tr.std()
Z = ((feat - mu) / sd).to_numpy(); Ztr = ((tr - mu) / sd).to_numpy()
log = pd.read_csv(sys.argv[2]); ent = log[log.decision == "entry"].copy()
ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
ent = ent[ent["date"].isin(feat.index)]
pnl = ent["pnl"].to_numpy(float); base = stats(pnl)
print("base Ret/DD", round(base["rdd"], 2))
for n in (2, 3):
    for pen in (0.0, 1.0, 3.0, 5.0, 10.0):
        jm = JumpModel(n_components=n, jump_penalty=pen, random_state=0, n_init=10)
        jm.fit(Ztr)
        lab = np.asarray(jm.predict_online(Z))
        means = [Z[lab == s, 1].mean() if (lab == s).any() else np.inf for s in range(n)]
        order = np.argsort(means); rank = {s: i for i, s in enumerate(order)}
        reg = pd.Series([rank[s] for s in lab], index=feat.index)
        r = ent["date"].map(reg).to_numpy()
        occ = [int((r == k).sum()) for k in range(n)]
        keep = r >= 1; s = stats(pnl[keep])
        print(f"n={n} pen={pen:>4}: trades/regime={occ}  sit-out-calmest1 Ret/DD {s['rdd']:.2f}  (removed {int((~keep).sum())})")
