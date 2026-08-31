# #197 — ES re-selection on the corrected box: the report

**Date:** 2026-08-31 · **Pre-registration:** `docs/WS-ES197-PREREGISTRATION.md` + two dated pre-results
amendments · **Claim:** `ES197-RETAIN-ALL-SIX` (ledger 78/78) · **Evidence:** `optimize/es197/data/`
(decision JSON, the fresh champion set, six Pareto CSVs, leaderboard; studies in `wsh-pg`, prefixes
`es197` — the recorded failure — and `es197b`).

## 0. One paragraph

The six deployed ES champions were selected on a box with one day of lookahead (#179), so we re-ran the
selection honestly: one fresh campaign per timeframe on the corrected box, in the incumbents' own search
space and at their own budget, judged by a rule frozen before any trial. **Verdict: RETAIN all six.** The
fresh champions beat the incumbents on no slot under the rule — 2h came closest (better median, inside the
fold-SE margin), 5m beat the incumbent but is gate-dark, 2m beat a negative incumbent but cannot pay the
friction. The reassuring reading: the incumbents, despite their flawed selection data, hold up on the
corrected box ($8k–$17k median-fold net@$25 on the four slots that matter). The deployed set, the #195
allowlist, and the LIVE-PROTOCOL are all unchanged. The campaign also produced a hard bonus finding for
#90: a full-registry (165-indicator, 454-param) cold search is structurally infeasible — **0 feasible in
~2,900 trials/study** — while the original 18-indicator space is 44–80% feasible; that first attempt is
kept in the database as the record.

## 1. The decisions (median-fold net at $25/rt, corrected box, 5 folds)

| TF | incumbent median | fold SE | fresh median | blocked by | decision |
|---|---|---|---|---|---|
| 4h | **$13,108** | $5,647 | $9,939 | fresh worse | RETAIN |
| 2h | $15,385 | $5,678 | **$19,470** | inside the SE margin | RETAIN |
| 1h | **$17,333** | $2,937 | $15,743 | fresh worse | RETAIN |
| 15m | **$8,031** | $1,293 | $7,378 | fresh worse | RETAIN |
| 5m | −$1,040 | $730 | **$3,861** | gate-dark (entry rate < 5%) | RETAIN |
| 2m | −$3,060 | $1,094 | −$497 | gross < 2× friction; net@$25 < 0 | RETAIN |

Three near-adopts, three *different* blocking clauses — the falsifier the claim pins (a rubber-stamp rule
would fail uniformly or adopt everything).

## 2. Campaign integrity
- Budget and search space were both corrected by **dated amendments before any objective value existed**
  (0 feasible trials in the first campaign = nothing was observed): 5,900 trials/slot (the incumbents' own
  `cap1` norm, verified from the database) in the original-18 space (54 dims — the incumbents' 58-59-param era).
- Feasibility in the corrected space: 2,595–4,722 COMPLETE per study (44–80%), fronts of 120–437.
- Two latent crashes fixed on the way: the optimizer's end-of-run print and `report_wsi`'s extraction both
  assumed `dd_limit`/`cooldown` params that were retired from the search on 2026-08-01 — every
  post-retirement campaign would have hit them.
- The random-trial control never ran (no ADOPT fired); its implementation was corrected regardless
  (it must score the trial's full indicator set, not a stripped one).

## 3. Consequences
- `best_champions_full_ES.json` unchanged; #195 allowlist unchanged (no input changed → no amendment).
- LIVE-PROTOCOL §8: the "#197 outcomes folded in" prerequisite is now met (retain-all).
- WS-ESCPI's ES legs: no re-check triggered (the deployed ES params did not change).
- #90 gains the strongest evidence it has: the post-growth registry needs search recalibration before any
  full-registry campaign; the unadopted 5m/2h observations are candidate seeds for that future work.

## 4. Reproduce
```
# server: studies es197b_<tf>_ES in wsh-pg (prefix es197 = the recorded infeasible attempt)
WSI_STUDY_PREFIX=es197b WSI_INSTRUMENT=ES python3 optimize/report_wsi.py 4h 2h 1h 15m 5m 2m
WSI_INSTRUMENT=ES python3 optimize/build_champions_from_pareto.py optimize/results/es197b_champions_full_ES.json 4h 2h 1h 15m 5m 2m
python3 optimize/es197/es197_decide.py            # the frozen rule → es197_decision.json
python3 optimize/verify/run.py                     # ES197-RETAIN-ALL-SIX, 78/78
```
