"""Investigate SI 4h: why 0 feasible, and is there a usable champion under a relaxed drawdown gate?"""
import os, optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
s = optuna.load_study(study_name="si2_4h_SI", storage=os.environ["WSH_STORAGE_URL"])
comp = [t for t in s.trials if t.values is not None and t.user_attrs.get("full_pnl") is not None]
pos = [t for t in comp if t.user_attrs["full_pnl"] > 0]
print(f"si2_4h_SI: {len(s.trials)} trials, {len(comp)} complete, {len(pos)} with positive full P/L")
# rank the positive-P/L trials by drawdown-to-profit ratio (lower = better); feasibility gate is <=0.25
pos.sort(key=lambda t: t.user_attrs["full_dd"] / max(t.user_attrs["full_pnl"], 1e-9))
print("top 6 positive-P/L 4h configs by DD/P&L ratio (gate=0.25):")
for t in pos[:6]:
    fp, fd = t.user_attrs["full_pnl"], t.user_attrs["full_dd"]
    print(f"  #{t.number}: full ${fp:,.0f} | DD ${fd:,.0f} | ratio {fd/max(fp,1e-9):.2f} | "
          f"sl {t.params.get('sl_soft'):.3f} tp {t.params.get('tp'):.3f} gate {t.params.get('gate_pct'):.0f}")
