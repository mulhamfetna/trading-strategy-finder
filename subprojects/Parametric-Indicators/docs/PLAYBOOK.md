---
name: parametric-indicators-playbook
description: WS-I.6 operational playbook — the single how-to for the parametric-indicator confirmation/veto layer on the box strategy. Current behaviour (post review #1–#4): box trigger + HAR-RV gate + drawdown breaker, 15 indicators as confirm/veto judges with a K-rule, GLOBAL retrace + 1-min wait, N-candle engulfing golf, two-phase SMC generation. How to run, every knob, the guarantees.
type: playbook
status: current
created: 2026-06-08
workstream: WS-I
---

# Parametric-Indicators — Operating Playbook

The single reference for running and reasoning about the indicator layer. Reflects the state after
review items #1–#4 (HAR lags, golf→engulfing, global retrace/wait, 1-min wait). Authoritative for
*behaviour*; deep rationale lives in the linked docs.

## 1. What the system is
The **box strategy is the trigger** (box Stage-1 signal sets direction). On top of it sit two gates
and a judge layer:
- **Volatility gate (HAR-RV):** skip bars whose forecast vol exceeds the `gate_pct` percentile.
- **Drawdown breaker:** halt for `cooldown` trades after the running drawdown hits `dd_limit`
  (global high-water mark kept across the halt).
- **Indicator layer (off by default):** up to 15 indicators each cast a per-bar **confirm / veto /
  neutral** vote vs the box direction; entry is allowed iff **(no active veto) AND (#active confirms
  ≥ K)**. With nothing enabled the system is **exactly** the box+vol strategy (parity-locked).

Decisions on the **decision timeframe** (default 4h); exits walk the **1-minute** path.

## 2. The knobs (all exposed on the dashboard, nothing hardcoded)
**Box / risk:** `sl_soft`, `sl_hard` (≥ sl_soft), `tp`, `gate_pct` (0 = gate OFF), `dd_limit`
(0 = breaker OFF), `cooldown`, `flip`, `window` (full/2025/2026), `dd_cap`, `pv`.

**Confirmation layer (WS-I):**
- **K** — minimum # of active confirms required (error if `K > #enabled confirm-capable`).
- Per indicator: **enabled** (default off), **mode** ∈ {confirm, veto, both}, and its own numeric
  **params** (e.g. RSI n/lower/upper).
- **GLOBAL retrace** (one box: amount + unit ∈ {atr_mult, points}) — applies to ALL indicators.
- **GLOBAL wait bars** (one box) — counts **1-minute** bars; applies to ALL indicators.
- **gen** params for SMC generation: `swing_l`, `golf_n`.

Bad/missing/contradictory values are **never silently clamped** — they raise `ParamError` →
HTTP 400 → a red banner.

## 3. How an entry is decided (per attempted decision bar `idx`, signal from closed bar `idx-1`)
1. **Eligibility (gate):** `vol_gate ∧ ¬veto_mask`. Any enabled veto-capable indicator whose vote at
   `idx-1` is VETO blocks the bar (direction-agnostic vetoes like ADX no-trend use the `BOTH`
   sentinel). Veto is immediate (no wait).
2. **Confirm count:** count enabled confirm-capable indicators voting CONFIRM at `idx-1` (live B1 —
   read on the just-closed bar). Need `≥ K_eff = min(K, #confirm-capable-enabled)`. `K_eff = 0`
   (no confirmers) ⇒ immediate fill.
3. **Fill price/time (GLOBAL retrace + 1-min wait):** one shared level `signal_close ∓ r`
   (`r` = retrace amount in points, or `atr_mult × ATR[idx-1]`). On the 1-minute armed window:
   skip the first `wait_bars` 1-min bars, then — `r>0`: fill at the first eligible 1-min bar that
   touches the level; `r=0`: fill at the wait-th 1-min bar at the signal close. Unfilled in-window ⇒
   re-evaluate next bar (engine carry-mode). `r=0 ∧ wait=0` ⇒ immediate fill at signal close.

## 4. The 15 indicators
- **Trend/MA:** EMATrend, SMATrend, MACD, KeltnerTrend, VWAPTrend
- **Momentum zones:** RSIZone, StochasticZone, MFIZone
- **Breakout/strength/vol:** CCIBreakout, ADXVeto (no-trend → `BOTH` veto), BollingerVeto, OBVTrend
- **SMC:** StructureTrend (HH/HL vs LH/LL), OrderBlock (OB→breaker state machine), FVGConfirm
Each: causal, decision-TF, off by default. Votes are **raw per-decision-bar** (no decision-bar
debounce — wait is the 1-min entry delay of §3).

## 5. Two-phase SMC generation (decision #11)
When any SMC indicator (fvg / order_block / structure_trend) is enabled, structures are generated
first and a **generation report** is emitted (`meta.gen_report`): bar count, FVG counts, swing
counts, order-block bars, and **golf** counts. Golf is **generation-only** (not a vote).

**Golf = N-candle engulfing** (review #2, `golf_n` = N): current candle opposite-colour to **all** N
prior, range-engulfs their combined high–low (wicks), and body ≥ 70% of that prior span →
+1 bullish / −1 bearish. See [[golf-engulfing]].

## 6. Volatility gate internals (HAR-RV)
RV per decision bar = √(Σ 1-min squared log-returns in the bar) × close; HAR forecast
`vf[i] = 0.5·rv[i−1] + 0.3·mean(rv[i−6:i]) + 0.2·mean(rv[i−30:i])` — **lookbacks are candles
(bars), not days**; **1/6/30 is the empirical best fit** for NQ (review #1, [[har-lag-review]]).
The gate threshold is the `gate_pct` percentile of the 2025 (train) forecast.

## 7. Guarantees (do not break)
- **Off-by-default ⇒ exact box parity** — no enabled indicators ⇒ `entry_resolver=None` ⇒
  byte-for-byte the verified engine. Locked: `optimize/test_parity.py` **+$7,735/$3,670/66**,
  `optimize/test_fast_parity.py` OK.
- **Causal / no look-ahead** — votes from closed bars; fills resolve forward on 1-min.
- **No silent fallback** — every bad param surfaces as `ParamError`/HTTP 400.
- Determinism: same inputs + code ⇒ identical outputs.

## 8. Run it
```bash
cd subprojects/Parametric-Indicators
python3 server.py --port 8200        # dashboard + API at http://localhost:8200/
python3 -m pytest tests/ -q          # 78 unit/integration tests
python3 optimize/test_parity.py      # off-by-default parity lock
python3 optimize/test_fast_parity.py # vectorised-engine parity lock
```
Dashboard flow: leave all indicators off → Run → matches the box winner (no vote chips). Enable
indicators, set mode/params + K + the global retrace/wait, Run → per-entry vote chips + the K
summary line; enable an SMC indicator to see the generation report.

## 8b. Dashboard additions (post-WS-I.10)
The dashboard/backtester gained, all parity-safe (indicators-off still reproduces the box winner):
- **Indicators read the 1-MINUTE frame** (dashboard backtester) — every indicator's direction is now
  computed on the 1-minute candles; each decision bar reads the value of its **last-closed 1-minute
  candle** (causal). The box trigger, entry cadence and exits stay on the decision timeframe; only
  the indicators' data source changed. Consequence: an indicator's look-back/warm-up now counts
  **1-minute candles** (e.g. `ema_trend slow=373` ≈ 373 minutes, not 373×4h), so any params tuned as
  decision-TF look-backs mean something very different here. Wired as an optional `src` through
  `runner` (`indicator_source_1min`); the optimiser + parity tests pass no `src` and stay decision-TF
  (parity locks unaffected). Note: computing 15 indicators over the full 1-minute history is heavier
  (~tens of seconds per full-history backtest).
- **All-timeframe backtests** — a **Timeframe** dropdown (1m/2m/5m/15m/1h/2h/4h); `build_payload`
  takes an optional `timeframe` (default 4h) and `strategy.get_bundle(tf)` lazy-loads + caches each
  TF's `(df_dec, df1, box, vf, n_split)`. Single-year windows cold-start indicators — prefer `full`.
- **Per-indicator warm-up** — every indicator stays **NEUTRAL** for its look-back (composites wait
  for the parts they depend on: `ema_trend`=max(fast,slow), `macd`=slow+signal, `keltner`=n,
  `stochastic`=n+d−1, `adx`=2n−1, …). Logged as `WARMUP`/`WARMED` events. Fixes the seeded-EMA
  cold-start "false confidence" (see `../WSI-Case_Study/CASE_STUDY_2026_maxDD.md`). Applied in
  `base.Indicator.vote()` — the single chokepoint for veto/confirm/resolver/attribution.
- **NOENTRY logging** — box signals dropped by a veto or the volatility gate are logged
  (`ENTRY NOT TAKEN — … vetoed by … / skipped by volatility gate`) instead of silently discarded.
  Diagnostic only (opt-in `engine.backtest(blocked_log=…)`); never a trade, never in the ledger.
- **One-click strategy import + saved profiles** — `presets.strategies()` serves the winner + the 7
  per-TF WS-I champions; user profiles persist server-side in `profiles/user_profiles.json`
  (`POST /api/profiles`) and show as `👤 name`. Selecting one fills every field and runs.
- **CSV export** of both logs (event log + trade ledger); a **Save current profile** button;
  errors shown as a **pinned top-of-page banner**.

## 9. Doc map
[[har-lag-review]] (HAR lags) · [[golf-engulfing]] (golf #2) · [[entry-timing-changes]]
(global retrace + 1-min wait #3/#4) · `WS-I.4_DASHBOARD_REPORT.md` (dashboard) ·
`WS-I.3_ENGINE_REPORT.md` (engine) · `RUNNER_BINDING_SEMANTICS.md` (Q1–Q6 binding) ·
`INDICATORS.md` (per-indicator spec). Note: `INDICATOR_DECISIONS.md` is the I.1 freeze; where it
describes per-indicator retrace/wait or the old golf, this playbook + the review docs supersede it.
