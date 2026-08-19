# STAGE STATUS — news-release-long (updated 2026-08-19, v5.4.2)

**All stages COMPLETE and SHIPPED.** v5.3.0 (NQ/RTY deployed + qty≤20 worked) → v5.4.0
(ES CPI shipped, #139) → v5.4.1 (YM CPI acquired via the RQ-7 execution gate, #147) → v5.4.2
(ES ≤20 / YM ≤5 scaled tiers, #141/#150). Every claim ledger-bound (40/40 both machines);
evidence under `evidence/` incl. `scaling_esym/`. The original stage report follows.

# STAGE STATUS REPORT — WS-DEPLOY (the full picture at 2026-08-17)
**Branch `feat/ws-deploy-news-executor` · worktree `/mnt/data/projects/trading/deploy-news` ·
server `~/Mulham/deploy-news` · draft PR #130 · issues #127 (contract) #128 (D1) #129 (D2) #131 (D3) #132 (D4)**

## 0 · The contract this stage runs under
The owner approved the two deployment decisions **conditionally** (2026-08-16): isolated branch,
the full verification walk, **merge only on an explicit owner instruction on #127** — the
auto-merge rule is overridden for this workstream. Everything below happened inside that contract;
nothing has touched `dev`/`main`; everything is paper.

## 1 · What is built (all on the isolated branch)
| component | what it does |
|---|---|
| `src/deploy/release_executor.py` | the confirmed trade exactly as pre-registered (#117): replay + paper modes, native qty/multi-leg, self-contained 1s loader; outputs carry `net_stressed_usd`; generalized bracket (worked-entry capable, default path byte-identical) |
| `src/deploy/schedule.py` + `release_schedule.csv` | the release schedule, verbatim replication of the study's event selection (329 confirmed) |
| `src/deploy/regime_monitor.py` | rolling 24-CPI-event **net-stressed** mean < $0 ⇒ STAND-DOWN, sticky, owner-cleared only |
| `src/deploy/scaling_study.py` · `worked_entry_study.py` | D3/D4 measurement machinery |
| engine hook | `SimpleStrategyParams.qty` (default 1 — byte-identical; dollars scale, points per-contract) |
| `tests/test_deploy_isolation.py` | the 18-test isolation battery |
| this bundle | playbook · portable verifier · champion.json · scaling findings · reports · evidence |

## 2 · The proof scoreboard (every line green or honestly annotated)
| proof | result |
|---|---|
| executor replay vs committed study evidence | **NQ 327/327 exact · RTY 238/238 exact** (+1 diagnosed study-side tie-break extra); 2024+ subset **81/81, $36,209.52 to the cent** |
| qty linearity | **to the cent** at 3/5/10/20, every event, both instruments |
| falsifiers | schedule +10min ⇒ parity destroyed (0/654) · D4 window +360s ⇒ NQ +$429→−$534 · D3 volume physics present (33×/18.6×) · paper mode: 0 intents on no-release windows |
| regime monitor | mechanism proofs green; era-walk stands down exactly where history was negative (2020-10→2021-02); GO now (+$1,231 roll24); **net-stressed input** proven by test |
| engine safety | golden gate **ALL BASELINES MATCH** (optimizer untouched); repo suite green |
| dashboard | branch instance renders **byte-identical to production** (650,547 chars equal); report pages captured (in `evidence/`) |
| portfolio value | with-vs-without, same window: **+31.1% P&L, +6.6% DD, corr +0.098** |
| scaling (D3/D4) | entry-second wall found & measured; worked entry validated (NQ −4%, RTY +24%); qty≤20 volume-feasible at 1.3–2.5% window participation |

## 3 · Catches made during this stage (the machinery still earning its keep)
1. The schedule generator's stable sort silently dropped 2 shared-minute CPI events vs the study's
   tie-break — caught against committed evidence BEFORE any parity run.
2. The RTY parity diagnosis exposed that the ORIGINAL study's per-instrument selections disagree at
   one shared minute (2026-03-06) — a documented study finding, gate refined to score it precisely.
3. The regime monitor was consuming GROSS P&L — switched to net-stressed under the owner's
   stressed-costs approval (a gross-positive/net-negative regime now stands down; tested).
4. The blanket `*.csv`/`*.html` ignore ate deliverables twice more — each un-ignored explicitly.
5. The worktree initially sat OUTSIDE the trading root — moved inside
   (`/mnt/data/projects/trading/deploy-news`) and the placement rule made permanent.

## 4 · Open items — exactly two owner gates, plus the standing blind spots
| item | owner |
|---|---|
| ⛔ merge instruction on #127 (nothing ships without it) | **owner** |
| broker margin at qty 10–20 (six-figure commitment; verify current rates) | **owner** |
| live execution gateway (paper intents only today) + a live worked-order (POV/TWAP) implementation for qty ≥ 5 | future scope, after merge |
| book depth / queue position beyond bar data; sweep-second slippage beyond 4 ticks | declared blind spots (need tick/live data) |
| era dependence of the premium | mitigated by the monitor, not removed |

## 5 · If the owner says "merge" tomorrow — what happens, in order
1. PR #130 → `dev` (the branch is green against everything measurable).
2. The executor runs in **paper** on the schedule (~31 events/yr per instrument), monitor armed.
3. Live qty=1–2 requires only a gateway; qty≥5 additionally requires the worked-order implementation
   validated in D4's model; qty=10–20 also the margin check.
4. The annual ledger re-run and the rolling monitor keep the numbers honest after we stop looking.
