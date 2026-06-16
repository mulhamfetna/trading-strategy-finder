---
name: spec_counterfactual_pause_attribution
description: "Evidence-first investigation into the champion's no-entry pause — simulate every gate-/veto-/confirm-blocked box signal as an isolated trade (champion exit logic), tally per-filter expectancy, and characterize box-silent windows by price displacement. Answers 'is the pause costing money?' per filter BEFORE any gate/entry redesign. Read-only; golden untouched."
metadata:
  type: project
  workstream: gate-redesign
  status: SPEC (approved design → writing-plans)
  date: 2026-06-16
---

# SPEC — Counterfactual pause attribution (does the no-entry pause cost money?)

## 0. Why
The pause diagnosis (`diagnose_pause.py`) flipped the premise: the champion's ~14-day no-entry stretches are
**box-silence ~71% + confirm<K ~22%**, NOT the vol gate (~4%). Before risking a gate/entry redesign, the
user's directive is **evidence-first: prove the pause actually costs money**, per filter. This task simulates
what each blocked signal *would* have done and produces a clean per-filter P/L ledger + a verdict.

## 1. Decisions (approved)
| # | Decision |
|---|---|
| D1 | **Success = prove it costs money first.** Output is a verdict per filter (over-filtering vs correctly filtering), not a redesign. |
| D2 | **All causes, full attribution, across ALL pauses** — every blocked bar in the full period, not just the longest gap. |
| D3 | **Methodology A — isolated per-signal counterfactual.** Each blocked signal simulated as a STANDALONE trade (no portfolio interaction). |
| D4 | **Reuse the real engine's exit** (one-signal array, gate open, breaker off) — NOT a re-implementation — so exits are provably faithful. |
| D5 | **box-silence** (no direction ⇒ no trade) is measured by **price displacement** (MFE/MAE over a horizon), not a simulated trade. |
| D6 | **Read-only.** New script only; no change to the engine / strategy / optimizer ⇒ golden 6/6 unaffected. |
| D7 | Scope = the **4h champion** (the production headline). |

## 2. Component — `optimize/counterfactual_pause.py`
A standalone analysis script mirroring `diagnose_pause.py`'s champion-loading and per-bar attribution.

**2.1 Setup (reuse diagnose_pause):** load the 4h champion via `two_stage._Ctx(tf="4h", ind_1min=True,
warm_start=True)`; recompute `sig` (box direction ±1/0), `vol_gate` (causal `vf ≤ gthr` on `vf[:n_split]`),
`veto`/`confirm` masks (1-minute source, `compute_votes` once). Attribute each bar by priority:
`no_signal` → `vol_gated` → `vetoed` → `confirm<K` → `would_enter`.

**2.2 Isolated trade simulator** `simulate_blocked(entry_idx, direction) -> trade`:
Build a signals array of length N that is the box signal at `entry_idx` only (0 elsewhere), run
`SimpleStrategy(sp).backtest(d4, d1, box, entry_gate=ones, veto_mask=None, blocked_log=[], signals=that_array)`
with the champion's `sl_soft/sl_hard/tp/pv` and **drawdown breaker OFF** (so the single trade is never
skipped). Return the one resulting closed trade (entry/exit time+price, exit_reason, `pnl_points`×pv, MFE/MAE
if available, else derived from the 1-min path). Each blocked signal is simulated **independently** ⇒ no
one-position-at-a-time suppression, no breaker, no cross-trade interaction.

**2.3 Bucket + aggregate:** for each filter bucket (`vol_gated`, `vetoed`, `confirm<K`): `n`, win%,
avg P/L, total P/L, median MFE/MAE. Benchmark against the champion's own taken-trade avg P/L (from a normal
`build_payload` run) as the "is this as good as a real trade?" yardstick.

**2.4 box-silence displacement** `silence_displacement(idx, horizon H)`:
for each `no_signal` bar, over the next `H` decision bars compute MFE = max(High)−Close[idx] and
MAE = Close[idx]−min(Low) (points). Report the distribution + the **fraction of silent bars whose |displacement|
exceeded the champion's `tp`** (a genuine missed directional move) vs chop. `H` = the **median taken-trade
duration in decision bars** (derived from the champion run; documented in the report — not a magic number).

**2.5 Verdict per bucket:**
- avg P/L **≥ ~champion avg** and total **strongly positive** ⇒ **OVER-FILTERING** (this filter is costing
  money; relaxing it is justified → triggers a targeted Approach-B system sweep as a follow-up task).
- avg P/L **≤ 0 or ≪ champion avg** ⇒ **CORRECTLY FILTERING** (the pause is doing its job here; accept it).

## 3. Outputs
- **`study_range_regime/REPORT_counterfactual_pause.md`** — verbose, with a **Mermaid** ledger/verdict diagram
  (per-filter bars → over/correct verdict), the box-silence displacement summary, and the overall conclusion
  (which lever, if any, is worth pursuing).
- **`optimize/results/counterfactual_pause_4h.csv`** — one row per simulated blocked trade
  (`cause, entry_time, exit_time, direction, entry_price, exit_price, exit_reason, pnl, mfe, mae`).

## 4. Testing (correctness anchor)
- **`optimize/test_counterfactual_pause.py`:**
  1. **Parity** (the key lock): take an *actually-taken* champion signal, run it through `simulate_blocked`,
     assert the resulting P/L equals that trade's P/L from a real `build_payload` run (proves the isolated
     exit ≡ the real engine's exit).
  2. **Bucketing** on a synthetic mask set: every blocked bar lands in exactly one bucket; counts reconcile
     with the attribution histogram.
- **Golden** `perf/check_golden.py` 6/6 — must remain MATCH (no engine/strategy change; this is read-only).

## 5. Files
```
optimize/counterfactual_pause.py                 # NEW: the analysis script
optimize/test_counterfactual_pause.py            # NEW: parity + bucketing locks
study_range_regime/REPORT_counterfactual_pause.md  # NEW: verbose report (Mermaid)
optimize/results/counterfactual_pause_4h.csv     # NEW: per-signal counterfactual ledger (generated)
study_range_regime/PAUSED_gate_redesign_brainstorm.md  # UPDATE: record the resolution + next lever
SYSTEM_UPDATES_MEGADOC.md                        # UPDATE: index entry
```

## 6. Non-goals
- **No engine/strategy/optimizer change** — purely an offline study (read-only).
- **No gate/entry REDESIGN** — this DECIDES whether a redesign is warranted and which lever. The system-level
  filter-relaxation sweep (Approach B) and any box-trigger change are **separate follow-up tasks**, gated on
  this study's verdict.
- **No multi-timeframe sweep** — 4h champion only (the production headline); other TFs out of scope here.
