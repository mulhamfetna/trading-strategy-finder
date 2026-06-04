---
name: ws-i-parametric-indicators-plan
description: WS-I action plan — introduce a parametric technical-indicator + ICT/SMC confirmation layer into the Parametric-Indicators subproject. Box Stage-1 stays the primary trigger; indicators confirm/veto. 10-phase pipeline (understand → document → engine → dashboard → team-leader sign-off → docs/playbook → vectorize → NSGA-II→III with a 3rd objective (win-rate) → 4h test → all-TF sweep). Detailed analysis, indicator inventory, architecture, open Phase-1 clarifications.
type: plan
status: draft-awaiting-approval
created: 2026-06-04
workstream: WS-I
---

# WS-I — Parametric Indicators: Workstream & Action Plan

> **Scope lock.** All work lives inside `subprojects/Parametric-Indicators/` only. The verified
> production engine (`src/strategy/simple_strategy.py`) and every *other* subproject/dashboard are
> untouched. The tagged branch `wsh-engine` is frozen. Single contract, NQ, $20/pt.

## 1. What this workstream does
Introduce a library of **parametric technical indicators** plus **ICT / Smart-Money-Concept (SMC)**
structures into the box strategy as a **confirmation / veto layer**. The **box Stage-1 signal stays
the primary trigger and direction source**; the new indicators do **not** trade on their own — they
either **confirm** a box entry (allow it) or **veto** it (block it), and a pair of **entry-timing**
controls (price-retrace and time-delay) decide *when/where* a confirmed entry actually fills.

This is run as the user's 10-step pipeline (task.md), mapped to phases **I.1–I.10** below.

### Locked decisions (from clarification round 1)
| # | Decision | Value |
|---|---|---|
| **A** | Indicator set | All 4 families (Trend, Momentum, Volatility, Volume) **+ everything in `indictors.md`** (ICT/SMC) |
| **B** | Integration role | **Confirmation / veto** only (box remains primary trigger & direction) |
| **C** | Optimizer objectives | **3 objectives**: max P/L, min worst-fold DD, **max win-rate** → **NSGA-III** |
| **D** | Step-5 review gate | **Hard pause for your sign-off** after engine+dashboard (I.3–I.4), before docs/vectorize/optimize (I.6–I.10) |

### Confirmed facts
- **Volume is present** in `NQ_4h_*.csv` and `NQ_1m_*.csv` (`datetime,open,high,low,close,volume`) →
  OBV / VWAP / MFI are feasible.
- The box CSV (`NQ_full_data_*.csv`) **already carries dozens of key-level columns** (`dOpen/wOpen/mOpen`,
  daily/weekly/monthly inducement & retracement highs/lows: `DIHD…MTH2…`) — "key levels" should
  **reuse these**, not recompute them.
- **Parity contract:** with every indicator disabled and retrace/time = 0, the composite gate must
  collapse to today's vol-gate-only path → `test_parity.py` / `test_fast_parity.py` keep passing
  (indicators are **off-by-default / neutral**).
- Indicators evaluate on the **decision/entry timeframe** (same bar as the box signal); exits still
  resolve on **1-minute** (unchanged, WS-H rule).

## 2. Indicator inventory (the "understand" target — Phase I.1)
Grouped by complexity. Group A/B are textbook and quick; **Group C is research-grade and carries
real definitional ambiguity** (the `indictors.md` notes are rough) — these drive the Phase-1
clarification backlog (§6).

**Group A — Classic TA (well-defined, vectorizable immediately)**
EMA · SMA · RMA (Wilder) · MACD · RSI · Stochastic · CCI · ADX/DMI · ATR · Bollinger Bands ·
Keltner Channels · OBV · VWAP · MFI.

**Group B — Entry-timing parametrics (`indictors.md` lines 1–3)**
- **Retrace entry** — wait for price to retrace *N* points from the signal before filling.
- **Time-delay entry** — wait *T* bars/minutes after the signal before filling.
- **Both** — combined (whichever/both conditions).

**Group C — ICT / Smart-Money-Concepts (complex; heavy Phase-1 clarification)**
- **Trend** (structure-based bias).
- **Key levels** (reuse box CSV daily/weekly/monthly opens + inducement/retracement levels).
- **Market structure** — LL / HL / HH / LH swing labels (**close-based**, per the notes).
- **FVG** (Fair Value Gap) — 3-candle imbalance, bullish/bearish; "fast move after the gap."
- **IFVG** (Inverse FVG) — price burned back **into/through** a prior FVG → strong continuation.
- **Order Block (OB)** — top OB (HH→LL, bearish, "red") / bottom OB (LL→HH, bullish, "green");
  identified on **closes**. Once an OB is broken it can **only** be used as a breaker thereafter.
- **Breaker Block** — an OB that price "burned into" (closed beyond); same concept as IFVG.
- **CISD** (Change In State of Delivery) — confirmation via a **"golf candle"** (a candle whose
  body/range exceeds the prior *M* candles, *M* configurable) + FVG; "all three" for breaker entry.
- **Gap** — any interval with no trades.

## 3. Target architecture (new files inside the subproject)
```
Parametric-Indicators/
├── indicators/
│   ├── classic.py        Group A — vectorized TA (numpy/pandas), each → per-bar series/signal
│   ├── smc.py            Group C — FVG/IFVG/OB/breaker/CISD/structure/key-levels detectors
│   ├── timing.py         Group B — retrace + time-delay entry-fill adjusters
│   └── confirm.py        confirmation/veto policy: combine N votes → allow/block a box entry
├── indicator_params.py   typed param schema + bounds (strict; no silent defaults)
├── engine.py             (existing) — entry_gate becomes composite: vol_gate ∧ confirm_vote
├── strategy.py           (existing) — wire indicator params + timing into build_payload
├── optimize/
│   ├── fast_engine.py    (existing) + vectorized confirm-mask + timing applied pre-entry
│   ├── optimizer.py      NSGA-II → NSGA-III; add win-rate objective; indicator on/off + params
│   ├── objectives.py     (new) 3-objective scorer (P/L, worst-DD, win-rate)
│   └── reports/          per-TF Pareto + leaderboard (3-objective)
├── frontend/index.html   independent dashboard — expose every indicator param + confirm policy
├── docs/INDICATORS.md    (new) verbose per-indicator spec (the "documenting pattern")
├── docs/PLAYBOOK.md      (new) end-to-end playbook
└── tests/                parity (off=neutral) + per-indicator reference-vs-vectorized parity
```

**Confirmation/veto mechanics (proposed, to confirm in I.1):** box sets direction at the decision
bar → each *enabled* indicator casts a vote ∈ {confirm, veto, neutral} for that direction →
combine via a configurable policy: **K-of-N agreement** and/or **veto-any** (any veto blocks).
The composite entry mask = `vol_gate ∧ policy(votes)`. Then **timing** (retrace/time) shifts the
fill of an allowed entry. All disabled ⇒ mask = vol_gate, timing = immediate ⇒ **parity holds**.

## 4. Phase plan (maps task.md steps 1→10)
Indicators roll out in **two batches** to de-risk: **Batch 1 = Group A + B** (well-defined, proves
the whole pipeline end-to-end), **Batch 2 = Group C** (ICT/SMC, after Batch 1 is signed off).

| Phase | task.md step | Deliverable | Gate |
|---|---|---|---|
| **I.1** | 1 — understand | Resolve §6 open questions; freeze exact math/rules per indicator | — |
| **I.2** | 2 — document | `docs/INDICATORS.md` — verbose per-indicator spec (what/how/when/why), prior doc pattern | — |
| **I.3** | 3 — engine (manual) | `indicators/*.py` + composite `entry_gate` + timing; manual single-run backtests | — |
| **I.4** | 4 — dashboard | Independent dashboard: **no silent fallbacks**, **every param exposed**, logs/reports show new params | — |
| **I.5** | 5 — verify | Verification report (reports + logs) → **HARD PAUSE for your sign-off** | 🚦 **STOP** |
| **I.6** | 6 — docs/playbook | Full docs + reports + `docs/PLAYBOOK.md` | — |
| **I.7** | 7 — vectorize | Vectorize indicators + confirm-mask into `fast_engine`; **new parity test** (on-indicators: vectorized==reference) | — |
| **I.8** | 8 — NSGA-III | Swap `NSGAIISampler`→`NSGAIIISampler`; add **win-rate** 3rd objective; search space = indicator on/off + params + policy + timing | — |
| **I.9** | 9 — 4h test | Optimizer smoke-run on **4h** only; sanity-check fronts/leaderboard | — |
| **I.10** | 10 — all-TF | Full sweep across all TFs (1m…4h); extract best **combination set per timeframe**; results report | 🚦 confirm before launch |

Each batch passes through I.1–I.7; the optimizer phases (I.8–I.10) run once on the **union** of
enabled indicators after both batches are signed off.

## 5. Cross-cutting requirements (every phase)
- **No silent fallbacks** — bad/missing indicator params raise `ParamError` to the UI (extends the
  existing strict-validation pattern in `strategy.py`).
- **All parameters exposed** in the dashboard; nothing hardcoded.
- **Logs/reports updated** to surface each new param + each indicator's per-trade vote.
- **Parity preserved** when indicators are off (regression-locked).
- **Vectorized** path must be trade-for-trade identical to a readable reference implementation.
- Studies DB / CSVs git-ignored (regenerable); single contract; no server password committed.

## 6. Open questions to resolve at the start of Phase I.1 (the "understand" gate)
These come straight from the ambiguity in `indictors.md`; I'll bring them to you before coding.

**Confirmation policy**
1. Combine rule: **K-of-N agreement**, strict **AND of all enabled**, or **veto-any**? Is K a search param?
2. Which indicators may **veto** vs only **confirm**? Same list or split?

**Entry timing (Group B)**
3. Retrace units — **points / ticks / % / ATR-multiple**? Measured from the signal candle's close?
4. Time-delay units — **decision bars** or **minutes**? Max wait before the signal expires?
5. "Both" — require **both** conditions, or **first-to-trigger**?

**ICT / SMC (Group C)**
6. **FVG** exact rule — bullish = `low[t] > high[t-2]` (3-candle gap)? Confirm fill/mitigation rule.
7. **IFVG / breaker** — "burned into" = a **close** beyond the zone, or a wick touch?
8. **Order block** — precise pick: the last opposite-color candle before the impulse, on **closes**?
   Confirm the "broken OB → breaker-only, never OB again" state machine.
9. **CISD golf candle** — bigger by **body** or **full range**? Default *M* (prior-candle count)?
   Do all three (golf + FVG + structure) need to agree, or is it configurable?
10. **Market structure** — swing detection method (fractal lookback *L*?), confirmed it's close-based.
11. **Key levels** — which of the box CSV columns count as tradeable levels, and what's the
    confirm/veto rule (e.g., veto longs into a level within X pts)?
12. **Trend** — defined by structure (HH/HL sequence), an MA stack, or both?

**Optimizer**
13. Win-rate objective — plain trade win-rate, or a **min-trade-count-guarded** win-rate (so the
    optimizer can't game it with 3 cherry-picked trades)? (I recommend guarded.)
14. Indicator on/off toggles in the search → expect a large space; confirm NSGA-III pop-size/trials
    budget per TF (WS-H used 1200/TF).

## 7. Risks & mitigations
- **Overfitting explodes** with on/off toggles + many params (recall WS-H's fine-TF mirage) →
  walk-forward scoring kept; win-rate guarded by min-trades; report auto-flags degenerate corners.
- **ICT/SMC definitional drift** → freeze exact rules in `docs/INDICATORS.md` *before* coding (I.1/I.2),
  each with a reference implementation + unit test.
- **Timing breaks parity** (it shifts fills) → off-by-default; dedicated parity test for timing=0.
- **Look-ahead** in structure/OB detection → all detectors causal (only closed bars), asserted in tests.

## 8. Immediate next step
Begin **Phase I.1** by resolving §6 with you (you = team leader). On your go, I'll start the
clarification pass and then write `docs/INDICATORS.md` (I.2). No engine code until the rules are frozen.
