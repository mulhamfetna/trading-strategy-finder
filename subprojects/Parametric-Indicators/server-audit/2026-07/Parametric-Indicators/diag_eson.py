import optuna, os, copy, time
from optuna.trial import FixedTrial
optuna.logging.set_verbosity(optuna.logging.WARNING)
from optimize.l2 import optimize as l2opt, engine, metrics, payload
from optimize import optimizer as OPT

t0 = time.time(); print("loading study...", flush=True)
s = optuna.load_study(study_name="l2es1_4h", storage=os.environ["WSH_STORAGE_URL"])
onp = [t for t in s.trials if t.params.get("es_enabled") is True]
print(f"  loaded {len(s.trials)} trials in {time.time()-t0:.0f}s; ES-on={len(onp)}", flush=True)

caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
cap = int(caps["4h"]["cooldown_cap"]); b = bounds["4h"]
print("building candidate L1 (wsh6cold)...", flush=True); t1 = time.time()
l1 = l2opt._l1_params_from_champion("optimize/results/wsh6cold_4h_champion.json", "4h")
l1run = payload.run_l1_cached("4h", params=l1)
print(f"  L1 built in {time.time()-t1:.0f}s", flush=True)

# sample up to 5 pruned ES-on configs: measure trade count ES-on vs same config ES-off
for i, t in enumerate(onp[:5]):
    params = l2opt.suggest_l2_params(FixedTrial(t.params), b, cap, contrib_tokens=("ES",))
    on = metrics.score(engine.run_l2(l1run, params))
    p2 = copy.deepcopy(params); p2["contributors"][0]["enabled"] = False
    off = metrics.score(engine.run_l2(l1run, p2))
    c = params["contributors"][0]
    ncomm = sum(1 for x in c["committee"] if x.get("enabled"))
    print(f"[{i}] topo={params['contributor_topology']:>12} k_es={c['k_es']} enc={c['signal']['encoding']:>10} "
          f"state={c['state_def']:>9} ncomm={ncomm:2d} | ES-ON n={on['n']:3d} PL=${on['pnl']:>9,.0f} "
          f"|| ES-OFF n={off['n']:3d} PL=${off['pnl']:>9,.0f}", flush=True)
