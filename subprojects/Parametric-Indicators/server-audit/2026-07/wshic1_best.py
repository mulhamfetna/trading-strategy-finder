import optuna, os, json
s = optuna.load_study(study_name='wshic1_4h', storage=os.environ['WSH_STORAGE_URL'])
done = [t for t in s.trials if t.state.name == 'COMPLETE']
def feas(t):
    c = t.user_attrs.get('constraint', [1.0]); return all(v <= 0 for v in c)
off = [t for t in done if not t.params.get('intracandle_veto_entry') and feas(t)]
best = max(off, key=lambda t: t.user_attrs.get('full_pnl', 0))
print('BEST_FULL_PNL', best.user_attrs.get('full_pnl'))
print('MED_FOLD_PNL', best.values[0], 'WORST_DD', -best.values[1], 'MED_ENTRIES', best.values[2])
print('PARAMS', json.dumps(best.params))
print('UA', json.dumps({k: best.user_attrs.get(k) for k in ('full_pnl','full_dd','median_win','median_entries','decision_pause_days')}))
