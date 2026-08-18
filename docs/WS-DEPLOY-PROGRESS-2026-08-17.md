# PROGRESS UPDATE — WS-DEPLOY · 2026-08-17 · stage FINISHED, preserved unmerged

**State: COMPLETE and FROZEN on the isolated branch.** Per the owner: `deploy-news` is finished and
is being saved/kept **without merging into main**; the research worktree (`legacy18`) continues
separately. This document is the dated pin of where everything stands.

## The one-paragraph summary
Both owner-approved deployment decisions are built and proven in isolation: the **release executor**
(the confirmed news trade, replay-parity-exact to the study evidence, native qty), the **regime
monitor** (net-stressed rolling-24 CPI gate, sticky), and the **engine qty hook** (byte-identical at
qty=1, golden gate untouched). The dashboard serves the branch **byte-identically to production**.
The with-vs-without measurement showed **+31% profit for +6.6% drawdown** on the same system. The
scaling studies took the layer to 5/10/20 contracts: D3 found the quiet-entry-second wall and
measured the window's depth; D4 validated the **worked (VWAP) entry** that removes it — NQ keeps
96% of its edge, RTY improves +24%, **combined qty=20 pace ≈ $330k/yr (2024→2026, net stressed)**.
Everything is packaged in the shareable bundle **v1.1.0** (zip, self-verifying).

## Where everything lives
| artifact | path |
|---|---|
| the shareable bundle (zip, 22 files) | `playbooks/news-release-long-bundle-v1.1.0.zip` |
| executive summary / playbook / stage status / scaling findings | `playbooks/news-release-long/*.md` |
| champion spec + expected numbers | `playbooks/news-release-long/champion.json` (v1.1.0) |
| self-verifying portable backtester | `playbooks/news-release-long/portable_backtester.py` (`--verify` = PASS, both instruments) |
| D3/D4 evidence + dashboard screenshots | `playbooks/news-release-long/evidence/` (also `deploy_out_d3/`, `deploy_out_d4/`, `docs/verification/`) |
| bilingual visual reports | `docs/SCALE-CONTEXT-REPORT-BILINGUAL.html` · `docs/STRESSED-COSTS-REPORT-BILINGUAL.html` |
| the code | `src/deploy/` (executor · schedule · monitor · scaling_study · worked_entry_study) + the engine qty hook |
| the battery | `tests/test_deploy_isolation.py` (18/18) |

## The paper trail
Issues: **#127** (the contract + full proof scoreboard — PINNED) · #128 D1 · #129 D2 · #131 D3 ·
#132 D4 · draft PR **#130** (draft by contract). Every step is a dated comment on those issues.

## Preservation
This state is frozen as the annotated tag **`ws-deploy-v1.1.0-rc1`** and published as a GitHub
**pre-release** (bundle zip attached) — immutable regardless of later branch work. ⛔ The merge into
`dev`/`main` (and therefore a full `vX.Y.Z` release) remains gated on the owner's explicit
instruction on #127. Until then: isolated, paper-only, preserved.

## What re-verifies this stage at any future date
1. `python3 playbooks/news-release-long/portable_backtester.py --bars-1s <NQ_1s.csv> --instrument NQ --verify`
2. `python3 -m pytest tests/test_deploy_isolation.py` (18 tests)
3. the golden gate (`perf/check_golden.py`) — must stay ALL MATCH
4. the claims ledger on the research branch (`optimize/verify/run.py`) — 27/27 at freeze time
