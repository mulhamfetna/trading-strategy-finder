# WS-I.10 data provenance — where everything lives

After the all-timeframe NSGA-III sweep, **everything has been pulled off the AMD server to local**.
Nothing unique remains server-side (the server copy is left only as a redundant backup / resume point).

## What lives where now

| Artifact | Local path | In git? | Notes |
|---|---|:--:|---|
| **Raw study database** | `optimize/studies/wsh.db` | ❌ gitignored | 158 MB SQLite — the master record of **all 20,676 trials** (7 studies `wsh3_<tf>`), every param/value/objective + the full Pareto graph. Source of truth; everything else is derived from it. Gitignored by design (size) — back it up out-of-band if you care about it. |
| Feasible Pareto fronts | `optimize/results/<tf>_wsi_pareto.csv` | ✅ | One row per front point; box knobs + every enabled indicator's tuned internals (45 cols). |
| Front scatter plots | `optimize/results/<tf>_wsi_pareto.png` | ✅ | |
| Cross-TF leaderboard | `optimize/results/wsi_leaderboard.csv` | ✅ | Champion per TF. |
| Champion full recipes | `optimize/results/wsi_champions_full.json` | ✅ | Box + tuned internals per TF champion. |
| Technical report | `optimize/reports/WS-I_RESULTS.md` | ✅ | Table + per-TF full recipe. |
| Plain-language report | `optimize/reports/WS-I_RESULTS_SIMPLE.md` | ✅ | |
| "What was tested" report | `docs/WS-I_WHAT_WAS_TESTED.md` | ✅ | Mermaid + Plotly + recipes. |
| Per-worker run logs | `optimize/server/server_logs/<tf>.log` | ✅ | ~20 MB, raw stdout of the 30 workers. |
| Launch script + output | `optimize/server/server_logs/launch.sh`, `launch.out` | ✅ | Exactly how the detached run was kicked off (worker map, trial split). |

## Per-study trial counts (in `wsh.db`)

| study | trials |
|---|--:|
| wsh3_4h | 3000 |
| wsh3_2h | 3000 |
| wsh3_1h | 3000 |
| wsh3_15m | 3000 |
| wsh3_5m | 3000 |
| wsh3_2m | 2917 |
| wsh3_1m | 2759 |
| **total** | **20,676** |

## Re-deriving / resuming

- Rebuild every CSV/PNG/leaderboard/report from the DB: `python3 optimize/report_wsi.py`.
- The server scratch (`/home/dev/Mulham/wsg-i`) still holds an identical `wsh.db`; to add more trials
  later, `remote_wsi.sh run <extra>` resumes the same studies (Optuna `load_if_exists`).

_Server location (backup): `dev@78.89.209.212:/home/dev/Mulham/wsg-i/Parametric-Indicators/optimize/studies/wsh.db`._
