#!/usr/bin/env bash
# Issue #14 — closing pipeline for the adopt gate. Runs once both searches finish.
#
# Order matters: extract BEFORE paired/noise (they need the winner's params), and the CONTROL extract
# must carry --scramble-seed. The control asks "what does this search score when the indicators carry
# no information?" — a statement about the whole pipeline under the null — so its holdout has to be
# scored with the SAME placebo votes the search trained on. Scoring a control winner with REAL votes
# silently answers a different question and the number stops being a null.
set -x
cd ~/Mulham/14-adopt-gate/subprojects/Parametric-Indicators || exit 1
source /home/dev/Mulham/wsg-i/pg.env
export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
PY=/home/dev/Mulham/.venv/bin/python3
R=optimize/results
L=optimize/perf/logs
SEED=20260728
mkdir -p "$R" "$L"

$PY -u -m optimize.adopt_gate extract --study adopt14treat_4h --top 5 \
    --out "$R/adoptgate_treatment_4h.json" > "$L/issue14_extract_treatment.log" 2>&1
echo "EXTRACT_TREAT=$?"

$PY -u -m optimize.adopt_gate extract --study adopt14ctrl_4h --top 5 --scramble-seed "$SEED" \
    --out "$R/adoptgate_control_4h.json" > "$L/issue14_extract_control.log" 2>&1
echo "EXTRACT_CTRL=$?"

$PY - "$R/adoptgate_treatment_4h.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
json.dump(d["selected"]["params"], open("/tmp/winner.json", "w"))
print("winner indicators:", d["selected"]["enabled_indicators"])
PYEOF

$PY -u -m optimize.adopt_gate paired --params /tmp/winner.json \
    --out "$R/adoptgate_paired_4h.json" > "$L/issue14_paired.log" 2>&1
echo "PAIRED=$?"

$PY -u -m optimize.adopt_gate noise --params /tmp/winner.json --perms 200 \
    --out "$R/adoptgate_noise_4h.json" > "$L/issue14_noise.log" 2>&1
echo "NOISE=$?"

$PY -u -m optimize.adopt_gate verdict \
    --baseline "$R/adoptgate_baseline_4h.json" \
    --treatment "$R/adoptgate_treatment_4h.json" \
    --control "$R/adoptgate_control_4h.json" \
    --noise-json "$R/adoptgate_noise_4h.json" \
    --paired-json "$R/adoptgate_paired_4h.json" \
    --out "$R/adoptgate_verdict_4h.json" > "$L/issue14_verdict.log" 2>&1
echo "VERDICT=$?"
cat "$L/issue14_verdict.log"
echo '=== GATE FINISHED ==='
