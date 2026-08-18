"""Issue #14 — measure, on a LIVE Optuna study, which indicators the --max-enabled cap actually keeps.

This is the check that caught the bias: the repair kept 'the first max_enabled in REGISTRY order', and
since the original 18 indicators occupy positions 0-17 an original always won the tie. Reasoning about
it is not enough — this reads the trials that were actually scored.

Usage:  python3 -m optimize.perf.check_max_enabled_bias <study_name> [n_sample]
"""
import sys, os, json, collections, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import optuna
from indicators import library

study = sys.argv[1] if len(sys.argv) > 1 else 'adopt14v2treat_4h'
n = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
R = list(library.REGISTRY); ORIG = set(R[:18])
st = optuna.load_study(study_name=study, storage=os.environ['WSH_STORAGE_URL'])
cnt = collections.Counter(); anynew = tot = 0; pos = []
for t in st.trials[:n]:
    keys = [s['key'] for s in t.user_attrs.get('enabled_specs', [])]
    if not keys: continue
    tot += 1
    for k in keys: cnt[k] += 1; pos.append(R.index(k))
    if any(k not in ORIG for k in keys): anynew += 1
print(f'study {study}: {tot} trials with a non-empty enabled set')
print(f'  trials containing ANY new-library indicator: {anynew} ({100*anynew/max(1,tot):.1f}%)')
print(f'  mean registry position kept: {statistics.mean(pos):.1f}  (unbiased expectation ~{(len(R)-1)/2:.0f})')
print(f'  most-kept NEW: {[(k,c) for k,c in cnt.most_common() if k not in ORIG][:8]}')
