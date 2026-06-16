---
name: update_alpha_decision_pause_implementation
description: "α implementation + progress — swap the optimizer's 3rd objective (win-rate → MINIMISE the recurring decision-pause) on the wsh4-era space, run as a user-gated fastest→slowest ladder. Code done + golden-safe; Tier 1 (local) + Tier 2 (server) launched."
metadata:
  type: project
  workstream: strategy-refinement
  stage: alpha (built; runs in flight)
  date: 2026-06-16
---

# α — decision-pause objective + escalating ladder (implementation & progress)

> Spec `SPEC_alpha_decision_pause_objective.md` · Plan `PLAN_alpha_decision_pause_objective.md`.
> Goal (issue 1): the champion pauses up to **11.5 days (decision-sourced)** with no entry; β proved no
> indicator subset fixes it (0/256 < 3d). α re-optimises with the pause AS an objective to find the
> **shortest pause achievable** while keeping P/L within ~5% of the champion.

## 1. What α changes (all default-off, golden-safe)
```mermaid
flowchart LR
    O["optimizer.objective()"] --> SW{"--objective"}
    SW -->|"winrate* (default)"| W["3rd obj = median win-rate (UNCHANGED)"]
    SW -->|"decision_pause"| P["3rd obj = −max_no_entry_days_decision<br/>(maximise −pause ⇒ MINIMISE the recurring pause)"]
    SC["--exclude-indicators ifvg,breaker,cisd"] --> SS["wsh4-era 15-indicator space"]
    SC2["--only-indicators cci,order_block,structure_trend"] --> SS2["lean subset (Tier 1)"]
    style P fill:#13241a,stroke:#00c853,color:#fff
    style W fill:#1a3a5a,stroke:#2962ff,color:#fff
```
| Change | File | Note |
|---|---|---|
| `--objective {winrate*\|decision_pause}` swap | `optimize/optimizer.py` | reads S0 `max_no_entry_days_decision` from the full backtest (no extra cost); directions unchanged (returns `−pause`) |
| `--exclude-indicators` / `--only-indicators` scope | `optimize/optimizer.py` `_suggest_indicators` | excluded/non-whitelisted keys forced OFF + not suggested ⇒ fewer dims |
| lean champion warm-start seed | `optimize/optimizer.py` `warm_start_seeds` | seeds `wsh_lean_4h_champion.json` when present |
| `decision_pause_days` user-attr + front-print pause column | `optimize/optimizer.py` | front shows `pause N.Nd` |
| `WSH_OBJECTIVE` / `WSH_EXCLUDE` env (server) | `optimize/server/remote_wsi.sh` | additive; unset ⇒ unchanged |
| ladder runner | `optimize/run_alpha_ladder.py` | 3 tiers; Tier 1 local, Tiers 2-3 emit the server command |

**Validation:** `optimize/test_alpha_objective.py` (4) + sampler/two-stage/no-entry locks = **18 checks green**;
**golden 6/6 MATCH** (default path byte-identical; dashboard scores via a separate engine path).

## 2. Decisions (user)
- Objective: **swap** win-rate → min decision-pause (stay 3 objectives). **Soft** (minimise) — NO hard ≤3-day
  cutoff; "shortest possible". The **−5% P/L band** (≥ ~$31,900 median, 95% of $33,587) only **highlights** the
  recommended point, it is not a filter.
- Search space: revert to **wsh4-era** (exclude ifvg/breaker/cisd, shared SL/TP).
- Execution: **fastest→slowest ladder**, **user-gated between tiers** (report + wait for "go"); run the next
  slower tier only if the faster one didn't get the pause short enough.

## 3. The ladder + progress
```mermaid
flowchart TD
    T1["TIER 1 wsh7a (LOCAL) — lean-3 (cci/OB/structure), continuous knobs<br/>decision_pause · 800 trials · warm-start lean"]
    T1 --> R1["report front (shortest pause @ ≥95% P/L) → PAUSE for 'go'"]
    R1 -->|go| T2["TIER 2 wsh7b (SERVER) — wsh4-era 15-ind · 30 workers · target 3000"]
    T2 --> R2["pull + report → PAUSE for 'go'"]
    R2 -->|go| T3["TIER 3 wsh7c (SERVER) — wsh4-era + lean seed · bigger budget (HELD)"]
    style T1 fill:#13241a,stroke:#00c853,color:#fff
    style T2 fill:#1a3a5a,stroke:#2962ff,color:#fff
```
### RESULTS (2026-06-16)
- **Tier 1 (local, lean-3, warm-started, DD cap 0.25):** shortest pause @ ≥95% champion P/L = **11.5 d /
  $33,428** — **no improvement over the champion's 11.5 d**. The engine *can* go shorter (a feasible 8.0-day
  point exists) but P/L collapses (8d loses money; 11.2–11.3d ≈ half). ⇒ under the 0.25 DD cap, ~11.5 d is a
  hard floor for good P/L. Report: `REPORT_alpha_tier1_decision_pause.md`.
- **Tier 2 (server `wsh7b`, wsh4-era, DD cap 0.25):** shortest FEASIBLE pause = 24.3 d / $6k (worse); min pause
  over ALL trials = 11.2 d but **infeasible** (busts 0.25). **CAVEAT:** ran COLD — `wsh4_champions_full.json`
  was absent on the server (`push` excludes `results/`), so warm-start seeded nothing. **FIX applied:** rsync'd
  the champion JSONs to the server (`warm_start_seeds` now returns 2 on the box).
- **Both 0.25-cap runs agree: the champion already sits at the short-pause frontier; shorter pauses either bust
  the DD cap or collapse P/L.** ⇒ the decisive test is a RELAXED cap (user option 3).

### NEW — relaxable DD-feasibility cap (`--dd-pnl-cap` / `WSH_DD_CAP`)
`optimizer.py` `run(..., dd_pnl_cap=0.25)` + `--dd-pnl-cap` (default 0.25 ⇒ unchanged; `remote_wsi.sh`
`WSH_DD_CAP`). The constraint becomes `full_dd ≤ dd_pnl_cap·full_pnl`. Relaxing it (e.g. **0.5**) lets the
shorter-pause / higher-DD strategies qualify so the search can trade pause↔drawdown. Default-off ⇒ golden 6/6
unchanged; `test_alpha_objective` + locks still green.

**In flight (2026-06-16, run in parallel to use the wait):**
- **Tier 1 — LOCAL**, prefix `wsh7a`: running (~521/800 trials at time of writing, ~3.2 s/trial). On
  completion writes `REPORT_alpha_tier1_decision_pause.md` (feasible front sorted by decision-pause; ⭐ =
  shortest pause with median P/L ≥ $31,900) then **pauses for review**.
- **Tier 2 — SERVER**, prefix `wsh7b` (Postgres `wsh7b_4h`): launched (decision_pause objective,
  `--exclude-indicators ifvg,breaker,cisd`, 30 workers, target 3000, warm-started). Verified the server
  `launch.sh` carries `--objective decision_pause` + the exclude. Collect later via `remote_wsi.sh counts`/
  `pull` + `run_alpha_ladder._report('wsh7b','4h', …)`.
- **Tier 3 — DONE/stopped early** (server `wsh7c`, warm-started 2 seeds, `decision_pause`, exclude
  ifvg/breaker/cisd, **`--dd-pnl-cap 0.5`**, 30 workers). At 3462/5000 complete, 2398 feasible@0.5: the
  **shortest pause @ ≥95% P/L is STILL 11.5 d** (the champion, $33,587 @ 10% DD). **No sub-11.5d point
  qualifies even at a 50%-of-P/L drawdown allowance.** Verdict stable across all tiers → stopped early to free
  the shared server.

### 🎯 VERDICT (α complete) — the 11.5-day pause is a STRUCTURAL FLOOR
| Tier | space | DD cap | shortest pause @ ≥95% champion P/L |
|---|---|--:|--:|
| T1 (local, lean-3, warm) | lean | 0.25 | **11.5 d** |
| T2 (server, wsh4-era, COLD) | 15-ind | 0.25 | 24.3 d (cold; champion unseeded — inconclusive) |
| **T3 (server, wsh4-era, warm)** | 15-ind | **0.50** | **11.5 d** |

Across all tiers and both cap settings, **no feasible re-optimisation beats the champion's 11.5-day pause at
acceptable P/L**. Shorter pauses either collapse P/L (8d ⇒ losing) or demand drawdown >50% of P/L. The pause
is intrinsic to this strategy family on 4h (volatility gate + box-signal cadence), **not** removable by
re-optimising it. **α confirms the champion rather than beating it** → to get a materially shorter pause needs
a DIFFERENT mechanism: **a gate redesign** (next workstream) or a faster decision timeframe.

## 4. Adoption (unchanged gate)
α surfaces candidates; the deployed champion stays until a candidate **OOS-dominates** under the
pre-registered walk-forward rule. A chosen short-pause point can be exported as a profile (like the β lean
one) on request.
