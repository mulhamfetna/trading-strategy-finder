"""Find the GC 4h winning trial in the study and diff its ACTUAL params against the deployed champion JSON."""
import json, os, optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

url = os.environ["WSH_STORAGE_URL"]
s = optuna.load_study(study_name="gc1_4h_GC", storage=url)
feas = [t for t in s.trials if t.values and t.user_attrs.get("full_pnl") is not None
        and t.user_attrs.get("constraint", [1])[0] <= 0]
feas.sort(key=lambda t: t.values[0], reverse=True)
champ = feas[0]
print(f"WINNING TRIAL #{champ.number}: median={champ.values[0]:.0f} full_pnl={champ.user_attrs['full_pnl']:.0f} "
      f"full_dd={champ.user_attrs['full_dd']:.0f}")
print("\n--- trial.params (what the optimizer ACTUALLY scored) ---")
for k in sorted(champ.params):
    print(f"  {k} = {champ.params[k]}")

print("\n--- deployed champion JSON (wsh4_champions_full_GC.json['4h']) ---")
cj = json.load(open("optimize/results/wsh4_champions_full_GC.json"))["4h"]
print("  box:", json.dumps(cj["box"]))
print("  indicators:", json.dumps(cj["indicators"]))
