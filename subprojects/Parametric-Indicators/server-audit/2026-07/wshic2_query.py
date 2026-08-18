import optuna, os
s = optuna.load_study(study_name='wshic2_4h', storage=os.environ['WSH_STORAGE_URL'])
done = [t for t in s.trials if t.state.name == 'COMPLETE']
def feas(t):
    c = t.user_attrs.get('constraint', [1.0]); return all(v <= 0 for v in c)
fe = [t for t in done if feas(t)]
by_pnl = sorted(fe, key=lambda t: t.user_attrs.get('full_pnl', 0), reverse=True)
print(f'wshic2 (forced IC-ON): total {len(s.trials)} complete {len(done)} feasible {len(fe)}')
print('--- best feasible by full P/L ---')
for t in by_pnl[:6]:
    ua, p = t.user_attrs, t.params
    print(f"  full P/L ${ua.get('full_pnl',0):>8,.0f} DD ${ua.get('full_dd',0):>7,.0f} "
          f"({(ua.get('full_dd',0)/ua.get('full_pnl',1)*100):.0f}%) medEnt~{t.values[2]:.0f} "
          f"N={p.get('intracandle_max_wait')} fc={p.get('intracandle_force_close')} "
          f"slS{p['sl_soft']:.0f} slH{p['sl_soft']+p['sl_hard_delta']:.0f} tp{p['tp']:.0f} gate{p['gate_pct']:.0f}")
