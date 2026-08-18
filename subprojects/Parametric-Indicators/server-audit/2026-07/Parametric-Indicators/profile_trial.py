"""Split per-trial wall-clock into ask (sampler) / compute (score) / tell (Postgres write), against the
real store. Solo worker (no contention) — a first cut at whether the optimizer is compute- or overhead-bound
post-memoization."""
import warnings, time, os, sys, json; warnings.filterwarnings("ignore")
import optuna; optuna.logging.set_verbosity(optuna.logging.WARNING)
from optimize.l2 import optimize as l2opt
from optimize import optimizer as OPT, storage as study_storage

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
tf = "4h"
caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
cap = int(caps[tf]["cooldown_cap"]); b = bounds[tf]
# candidate L1 (wsh6cold) — the §7 path
l1p = l2opt._l1_params_from_champion("optimize/results/wsh6cold_4h_champion.json", tf)
l1 = l2opt.payload.run_l1_cached(tf, params=l1p)
w = l2opt.WINDOWS(l1)
# warm the memo (mid-run steady state)
l2opt.score_window(l1, l2opt.suggest_l2_params(optuna.trial.FixedTrial({}), b, cap) if False else
                   {"sl_soft":150.,"sl_hard":167.,"tp":120.,"gate_pct":0.,"dd_limit":0.,"cooldown":0,
                    "flip":False,"window":"full","k":1,"ind_1min":True,"cap_1min":0,"indicators":[]}, *w["in"])

url = os.environ.get("WSH_STORAGE_URL") or "sqlite:////tmp/prof.db"
storage = optuna.storages.RDBStorage(url=url, engine_kwargs=study_storage.engine_kwargs(url)) \
    if not str(url).startswith("sqlite") else url
study = optuna.create_study(study_name="proftrial_4h", storage=storage,
                            directions=["maximize","maximize","maximize"],
                            sampler=OPT.make_sampler("nsga3", 1, lambda t: t.user_attrs.get("constraint",[1.0]), 3),
                            load_if_exists=True)
print(f"store = {'POSTGRES' if 'postgres' in str(url) else 'sqlite'} ; N={N} trials (solo)")
t_ask = t_comp = t_tell = 0.0
t0 = time.perf_counter()
for i in range(N):
    t = time.perf_counter(); trial = study.ask(); t_ask += time.perf_counter() - t
    t = time.perf_counter()
    params = l2opt.suggest_l2_params(trial, b, cap)
    s_in = l2opt.score_window(l1, params, *w["in"])
    vals = (float(s_in["pnl"]), -float(s_in["max_dd"]), float(s_in["win"]))
    trial.set_user_attr("constraint", [float(s_in["max_dd"] - 0.25*s_in["pnl"])])
    t_comp += time.perf_counter() - t
    t = time.perf_counter(); study.tell(trial, vals); t_tell += time.perf_counter() - t
tot = time.perf_counter() - t0
ms = lambda x: x/N*1000
print(f"per-trial: ASK(sampler)={ms(t_ask):6.1f}ms  COMPUTE(score)={ms(t_comp):6.1f}ms  "
      f"TELL(store write)={ms(t_tell):6.1f}ms  | TOTAL={ms(tot):6.1f}ms")
print(f"shares:    ask={100*t_ask/tot:4.0f}%   compute={100*t_comp/tot:4.0f}%   tell={100*t_tell/tot:4.0f}%   "
      f"other={100*(tot-t_ask-t_comp-t_tell)/tot:4.0f}%")
print(f"=> {'OVERHEAD-bound (ask+tell)' if (t_ask+t_tell)>t_comp else 'COMPUTE-bound'}")
try: optuna.delete_study(study_name="proftrial_4h", storage=storage)
except Exception: pass
