import optuna, os
s = optuna.load_study(study_name='wshic1_4h', storage=os.environ['WSH_STORAGE_URL'])
ts = s.trials
done = [t for t in ts if t.state.name == 'COMPLETE']
ic_on = [t for t in done if t.params.get('intracandle_veto_entry') is True]
print('total:', len(ts), 'complete:', len(done), 'intracandle-ON complete:', len(ic_on))
def feas(t):
    c = t.user_attrs.get('constraint', [1.0]); return all(v <= 0 for v in c)
fon = sorted([t for t in ic_on if feas(t)], key=lambda t: t.user_attrs.get('full_pnl', 0), reverse=True)
foff = sorted([t for t in done if not t.params.get('intracandle_veto_entry') and feas(t)], key=lambda t: t.user_attrs.get('full_pnl', 0), reverse=True)
print('feasible IC-ON:', len(fon), ' feasible IC-OFF:', len(foff))
for lbl, arr in (('IC-ON', fon[:4]), ('IC-OFF', foff[:2])):
    for t in arr:
        ua, p = t.user_attrs, t.params
        print(f"  [{lbl}] fullP/L ${ua.get('full_pnl',0):>8,.0f} DD ${ua.get('full_dd',0):>7,.0f} "
              f"ent~{t.values[2]:.0f} N={p.get('intracandle_max_wait')} fc={p.get('intracandle_force_close')} "
              f"slS{p['sl_soft']:.0f} slH{p['sl_soft']+p['sl_hard_delta']:.0f} tp{p['tp']:.0f} gate{p['gate_pct']:.0f}")
