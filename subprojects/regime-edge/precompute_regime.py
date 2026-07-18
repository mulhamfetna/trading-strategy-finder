#!/usr/bin/env python3
"""Precompute the CAUSAL daily NQ regime (filtered HMM) to a static CSV, so the deployable sizing overlay
needs no hmmlearn/model at run time. Columns: date, regime (0=calmest..n-1=most turbulent, by realized-vol).

Run:  python3 precompute_regime.py <NQ_1h.csv> <out.csv>
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS

feat = daily_features(sys.argv[1])
tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
Z = ((feat-mu)/sd).to_numpy(); Ztr = ((tr-mu)/sd).to_numpy()
best = min(((k,)+(lambda x:(x[1],bic(x[1],k,Ztr.shape[1],len(Ztr)),x[0]))(fit_hmm(Ztr,k,RESTARTS)) for k in (2,3,4)), key=lambda z:z[2])
n, model = best[0], best[3]
reg,_ = filtered_states(model, Z)
order = np.argsort(model.means_[:,1]); rank={s:i for i,s in enumerate(order)}
out = pd.DataFrame({"date": feat.index.astype(str), "regime": [rank[s] for s in reg], "n_regimes": n})
out.to_csv(sys.argv[2], index=False)
print(f"wrote {sys.argv[2]}: {len(out)} days, {n} regimes")
