import optuna, os, json
optuna.logging.set_verbosity(optuna.logging.WARNING)
s = optuna.load_study(study_name="wshes1_4h", storage=os.environ["WSH_STORAGE_URL"])
ts = [t for t in s.trials if t.values]
def feas(t): return t.user_attrs.get("constraint", [1.0])[0] <= 0
def es(t): return t.params.get("es_enabled") is True
on  = [t for t in ts if es(t)]
off = [t for t in ts if not es(t)]
fon  = [t for t in on  if feas(t)]
foff = [t for t in off if feas(t)]
print(f"total_with_values={len(ts)}  feasible={sum(feas(t) for t in ts)}")
print(f"ES-ON : trials={len(on):5d}  feasible={len(fon):4d}")
print(f"ES-OFF: trials={len(off):5d}  feasible={len(foff):4d}")

def best(g):  # best feasible by objective[0] = median fold P/L
    g = [t for t in g if feas(t)]
    if not g: return None
    return max(g, key=lambda t: t.values[0])
def show(tag, t):
    if t is None: print(f"{tag}: (no feasible)"); return
    fp = t.user_attrs.get("full_pnl"); fd = t.user_attrs.get("full_dd")
    print(f"{tag}: medianFoldPL=${t.values[0]:,.0f}  worstFoldDD=${-t.values[1]:,.0f}  win={t.values[2]:.1f}%  "
          f"| full-period PL=${fp:,.0f} DD=${fd:,.0f}  es_enabled={es(t)}")
bon, boff = best(fon), best(foff)
print("\n--- best feasible by median fold P/L ---")
show("ES-ON best ", bon)
show("ES-OFF best", boff)

# Pareto front composition
front = s.best_trials
fr_on = [t for t in front if es(t)]
print(f"\nPareto front size={len(front)}  ES-on on front={len(fr_on)}  ES-off on front={len(front)-len(fr_on)}")
# overall best-median-PL feasible champion + its key ES config (if on)
champ = best(ts)
print("\n--- overall champion (best feasible median fold P/L) ---")
show("CHAMPION", champ)
if champ is not None and es(champ):
    p = champ.params
    on_inds = [k[6:] for k in p if k.startswith("es_en_") and p[k] is True]
    print(f"  champion ES: topology={p.get('contributor_topology')} state={p.get('es_state')} "
          f"k_es={p.get('es_k_es')} sig_enc={p.get('es_sig_enc')} committee_on={on_inds}")
