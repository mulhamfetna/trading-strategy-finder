"""Generate the interactive Plotly charts embedded in the WS-I reference docs (real data).

Outputs standalone HTML (plotly.js via CDN) into this folder:
  votes_distribution.html  — per-indicator confirm/veto/neutral counts on real NQ 4h (INDICATOR_LOGIC)
  engine_vs_fast.html      — measured backtest wall-time: Python engine vs vectorized (VECTORIZATION)
  nsga3_feasibility.html   — smoke trials: full P/L vs full DD + the 25% feasibility line (NSGA3)
  nsga3_objectives_3d.html — smoke trials in the 3 objective axes (NSGA3)

Run:  python3 subprojects/Parametric-Indicators/docs/charts/make_charts.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)


def _save(fig, name):
    p = os.path.join(_HERE, name)
    fig.write_html(p, include_plotlyjs="cdn", full_html=True)
    print("wrote", os.path.relpath(p, _ROOT))
    return fig


def votes_distribution():  # returns the figure (also saves the standalone html)
    import strategy
    from indicators import library, runner
    from indicators.base import IndicatorConfig
    df4, df1, box, vf, n = strategy.load_inputs()
    ctx = runner.market_context(df4); bdir = runner.box_direction_int(df4, box)
    keys = list(library.REGISTRY)
    conf, veto, neu = [], [], []
    for k in keys:
        meta = library.SCHEMA[k]
        ind = library.build(k, IndicatorConfig(enabled=True, mode=meta["mode"],
                                               params={p["name"]: p["default"] for p in meta["params"]}))
        v = ind.vote(ctx, bdir)
        sig = bdir != 0
        conf.append(int(((v == 1) & sig).sum()))
        veto.append(int(((v == -1) & sig).sum()))
        neu.append(int(((v == 0) & sig).sum()))
    fig = go.Figure()
    fig.add_bar(name="confirm", x=keys, y=conf, marker_color="#2e7d32")
    fig.add_bar(name="veto", x=keys, y=veto, marker_color="#b71c1c")
    fig.add_bar(name="neutral", x=keys, y=neu, marker_color="#9e9e9e")
    fig.update_layout(barmode="stack", title="Per-indicator votes on signalling bars (NQ 4h, default params)",
                      xaxis_title="indicator", yaxis_title="# decision bars (box has a direction)",
                      template="plotly_white", legend_title="vote")
    return _save(fig, "votes_distribution.html")


def engine_vs_fast():
    from optimize import data, signals
    from optimize.fast_engine import fast_backtest, signals_to_int
    from engine import SimpleStrategy, SimpleStrategyParams
    df, df1, box, vf, n = data.load_inputs("4h")
    si = signals_to_int(signals.decision_signals(df, box))
    g = vf <= float(np.percentile(vf[:n], 60))
    sp = SimpleStrategyParams(sl_soft_points=30, sl_hard_points=40, tp_soft_points=60, tp_hard_points=60,
                              data_path_4h="", data_path_1min="", box_data_path="", flip_entry_direction=False)
    DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
    MD, MH = df1["Date"].to_numpy(), df1["High"].to_numpy(float)
    ML, MC = df1["Low"].to_numpy(float), df1["Close"].to_numpy(float)
    t0 = time.time(); SimpleStrategy(sp).backtest(df, df1, box, entry_gate=g); t_eng = time.time() - t0
    t0 = time.time(); fast_backtest(DD, DC, si, g, MD, MH, ML, MC, 30, 40, 60, False); t_fast = time.time() - t0
    fig = go.Figure(go.Bar(x=["Python engine", "vectorized (numpy)"], y=[t_eng * 1000, t_fast * 1000],
                           marker_color=["#5472d3", "#2e7d32"],
                           text=[f"{t_eng*1000:.0f} ms", f"{t_fast*1000:.1f} ms"], textposition="outside"))
    fig.update_layout(title=f"One 4h backtest: Python engine vs vectorized ({t_eng/max(t_fast,1e-9):.0f}× faster)",
                      yaxis_title="wall-clock (ms, log)", yaxis_type="log", template="plotly_white")
    return _save(fig, "engine_vs_fast.html")


def _smoke_trials():
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    s = optuna.load_study(study_name="wsh3_4h", storage=f"sqlite:///{os.path.join(_ROOT,'optimize','studies','wsh.db')}")
    rows = []
    for t in s.trials:
        if t.values is None:
            continue
        ua = t.user_attrs
        fp, fd = ua.get("full_pnl"), ua.get("full_dd")
        if fp is None:
            continue
        feas = fp > 0 and fd <= 0.25 * fp
        rows.append(dict(med_pnl=t.values[0], worst_dd=-t.values[1], win=t.values[2],
                         full_pnl=fp, full_dd=fd, feasible=feas))
    return pd.DataFrame(rows)


def nsga3_feasibility():
    d = _smoke_trials()
    if d.empty:
        print("no smoke trials — skip feasibility chart"); return
    fig = go.Figure()
    for feas, color, nm in [(True, "#2e7d32", "feasible (DD≤25%·P/L)"), (False, "#b71c1c", "infeasible")]:
        sub = d[d["feasible"] == feas]
        fig.add_scatter(x=sub["full_pnl"], y=sub["full_dd"], mode="markers", name=nm,
                        marker=dict(size=10, color=color, opacity=0.8),
                        hovertemplate="P/L $%{x:,.0f}<br>DD $%{y:,.0f}<extra></extra>")
    xmax = max(1.0, float(d["full_pnl"].max()))
    fig.add_scatter(x=[0, xmax], y=[0, 0.25 * xmax], mode="lines", name="DD = 25% · P/L",
                    line=dict(dash="dash", color="#555"))
    fig.update_layout(title="I.9 smoke (4h): full-period P/L vs max DD — feasibility line",
                      xaxis_title="full-period P/L ($)", yaxis_title="full-period max DD ($)",
                      template="plotly_white")
    return _save(fig, "nsga3_feasibility.html")


def nsga3_objectives_3d():
    d = _smoke_trials()
    if d.empty:
        print("no smoke trials — skip 3d chart"); return
    fig = go.Figure(go.Scatter3d(
        x=d["med_pnl"], y=d["worst_dd"], z=d["win"], mode="markers",
        marker=dict(size=5, color=d["feasible"].map({True: 1, False: 0}),
                    colorscale=[[0, "#b71c1c"], [1, "#2e7d32"]], opacity=0.85),
        hovertemplate="medP/L $%{x:,.0f}<br>worstDD $%{y:,.0f}<br>win %{z:.0f}%<extra></extra>"))
    fig.update_layout(title="I.9 smoke (4h): the 3 objectives (green=feasible)",
                      scene=dict(xaxis_title="median fold P/L ($)", yaxis_title="worst-fold DD ($)",
                                 zaxis_title="median win-rate (%)"), template="plotly_white")
    return _save(fig, "nsga3_objectives_3d.html")


if __name__ == "__main__":
    votes_distribution()
    engine_vs_fast()
    nsga3_feasibility()
    nsga3_objectives_3d()
    print("done.")
