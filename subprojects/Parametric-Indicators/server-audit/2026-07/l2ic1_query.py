import optuna, os, json
s = optuna.load_study(study_name='l2ic1_4h', storage=os.environ['WSH_STORAGE_URL'])
done = [t for t in s.trials if t.state.name == 'COMPLETE']
def feas(t):
    c = t.user_attrs.get('constraint', [1.0]); return all(v <= 0 for v in c)
fe = sorted([t for t in done if feas(t)], key=lambda t: t.user_attrs.get('in_pnl', 0), reverse=True)
print(f'l2ic1: total {len(s.trials)} complete {len(done)} feasible {len(fe)}')
for t in fe[:6]:
    ua = t.user_attrs; p = json.loads(ua.get('params', '{}'))
    print(f"  in-P/L ${ua.get('in_pnl',0):>7,.0f} in-DD ${ua.get('in_dd',0):>6,.0f} n={ua.get('in_n')} "
          f"N={p.get('l2_intracandle_max_wait')} slS{p.get('sl_soft',0):.0f} slH{p.get('sl_hard',0):.0f} "
          f"tp{p.get('tp',0):.0f} gate{p.get('gate_pct',0):.0f} flip{p.get('flip')}")
if fe:
    print('BEST_PARAMS ' + json.dumps(json.loads(fe[0].user_attrs['params'])))
