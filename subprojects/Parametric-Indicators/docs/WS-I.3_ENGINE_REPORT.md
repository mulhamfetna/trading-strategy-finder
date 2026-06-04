---
name: ws-i3-engine-report
description: WS-I.3 completion report — the parametric-indicator confirmation/veto engine layer built on top of the box strategy. Architecture, the 15 indicators, the confirm/veto K-rule, retrace-fill + carry-across-bars engine change, full test/parity evidence, file map, and what's deferred to I.4/I.5. Off-by-default ⇒ exact box parity (locked on real data).
type: report
status: complete
created: 2026-06-04
workstream: WS-I
---

# WS-I.3 — Indicator Engine Layer: Completion Report

## 1. What was built
A complete **confirmation / veto layer** on top of the box strategy. The box still sets direction
and is the primary trigger; indicators are judges that **confirm** (allow) or **veto** (block) a box
entry, and a per-indicator **retrace** can move the *fill price* to a pulled-back level. Everything is
**off by default** — with no enabled indicator the system reproduces today's box+vol-gate strategy
**exactly** (parity locked on real data).

Built test-first (TDD): **65 unit/integration tests green**, and the two original engine parity
locks still pass unchanged.

## 2. Architecture (OOP-first, per the directive)
```
box signal (engine, idx-1)         indicators/ (the new layer)
        │                          ┌─ classic.py   14 TA primitives (causal numpy)
        ▼                          ├─ smc.py       FVG · structure · golf · OB→breaker
   direction d ──► votes ──────────┤  votes.py     value-series → confirm_dir/veto_dir
        │           (per indicator) ├─ library.py   15 Indicator classes + REGISTRY/build()
        │                          ├─ base.py      IndicatorConfig (strict) · Indicator.vote ·
        │                          │               apply_wait (wait_bars debounce)
        ▼                          ├─ confirm.py   K-rule aggregate() + build_gate()
   composite gate ◄────────────────┤  timing.py    resolve_retrace_entry (K-th level)
   = vol ∧ no-veto                 ├─ generate.py  two-phase SMC generator + report
        │                          └─ runner.py    market_context · box_direction · composite_gate ·
        ▼                                          build_entry_resolver (live-B1 binding)
   engine.SimpleStrategy.backtest(entry_gate=…, entry_resolver=…, veto_mask=…)
        │   (entry_resolver=None ⇒ byte-for-byte the verified engine ⇒ PARITY)
        ▼
   trades (1-min exits, unchanged)
```

## 3. The 15 indicators (all decision-TF, causal, off by default)
- **Trend / MA:** EMATrend, SMATrend, MACD, KeltnerTrend, VWAPTrend
- **Momentum (mean-reversion zones):** RSIZone, StochasticZone, MFIZone
- **Breakout / strength / vol:** CCIBreakout, ADXVeto (no-trend → direction-agnostic veto via `BOTH`),
  BollingerVeto (veto on band-stretch), OBVTrend
- **SMC:** StructureTrend (HH/HL vs LH/LL), OrderBlock (OB→breaker state machine), FVGConfirm
Each exposes `value` + `enabled` (default off) + `mode∈{confirm,veto,both}` + per-indicator
`retrace` + `wait_bars`; always computes & logs its opinion with an `active` flag.

## 4. Decision semantics implemented (all frozen-approved)
- **K-rule:** entry allowed iff (no active veto) AND (#active confirms ≥ K). `apply_wait` debounces
  confirms by `wait_bars` (veto immediate).
- **Retrace = fill price** (`timing.resolve_retrace_entry`): as price pulls back, confirms activate at
  their levels; the trade fills at the **K-th confirm's level**. `retrace=0` ⇒ immediate at signal
  close.
- **Runner-binding (RUNNER_BINDING_SEMANTICS.md):** Q1 `K>N_confirm` → `ParamError`; Q2 veto-only →
  waive confirm; **Q3/Q4 LIVE per closed decision bar (B1)** + live veto-abort; Q5 gate=eligibility /
  resolver=K-count; Q6 confirm = live-reading AND wait AND retrace.
- **Carry-across-bars (engine carry mode):** an armed-but-unfilled setup persists across HOLD bars,
  re-reading votes/veto each closed bar, aborting on a fresh veto, superseding on a new signal.

## 5. Parity & causality guarantees
- **All-off ⇒ exact box parity** — `entry_resolver=None`/no enabled indicator path is byte-for-byte
  the verified engine. Locked: `test_parity.py` **+$7,735 / $3,670 / 66**, `test_fast_parity.py` OK.
- **Causal** — indicator readings from closed bars only; retrace level-touches resolve on 1-min;
  swings/OBs confirmed `L` bars late; no look-ahead.
- **No silent fallback** — bad params raise `ParamError`/`IndicatorParamError` to the surface.

## 6. Test evidence (65 tests)
| Suite | n | Covers |
|---|---:|---|
| test_classic | 15 | hand-computed / contract math for all 14 primitives (+ caught an `rma` NaN bug) |
| test_confirm | 14 | config validation, vote mapping (confirm/veto/both, BOTH), K-rule, wait debounce |
| test_library | 7 | stance helper, EMA/ADX behaviour, registry, build_gate parity |
| test_smc | 8 | FVG bull/bear+zones, structure swings, golf, structure-trend, order-block, FVG-active |
| test_timing | 6 | retrace resolver (K-th level, depth order, r=0 immediate, unfilled, short) |
| test_generate | 3 | two-phase generator structures + report counts + determinism |
| test_integration | 12 | real-data: all-off==vol-gate, engine-trades-identical, retrace0/pts fills, **carry**, **veto-abort**, subset |

## 7. File map (all under `subprojects/Parametric-Indicators/`)
`indicators/{classic,smc,votes,base,confirm,library,timing,generate,runner}.py` ·
`engine.py` (added `entry_resolver`+`veto_mask` carry mode, guarded) · `tests/test_*.py` ·
docs: `INDICATORS.md`, `INDICATOR_DECISIONS.md` (+ simple), `RUNNER_BINDING_SEMANTICS.md`, this report.

## 8. Deferred (not part of I.3 logic)
- **`strategy.build_payload` wiring** → the **I.4 dashboard** backend (expose every param, the
  two-phase generate→backtest reports/logs, per-trade vote attribution).
- **I.5 hard sign-off** follows I.4.
- Vectorization of the indicator path into `fast_engine` (I.7) and NSGA-III + win-rate (I.8) come
  later; the live-B1 carry semantics will inform the vectorized port.

## 9. Commits
`6664ca5` (foundation) → `238e2ed` (FVG + semantics) → `85b29ca` (retrace resolver + hook + wait) →
`4cf2391` (live-B1 binding + carry engine). All on `dev`.
