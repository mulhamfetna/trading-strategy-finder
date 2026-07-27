# Design: Calc-Indicator Library Expansion (WS-EXTRA-IND)

**Date:** 2026-07-25
**Branch / worktree:** `extra-indicators`
**Status:** Approved design → implementation planning
**Author:** Mulham Fetna (see `/home/mulham-fetna/.claude/CLAUDE.md` for attribution links)

---

## 1. Goal

Expand the system's technical-indicator library from the current ~18 to a comprehensive set of
**faithful, single-OHLCV computable indicators** ("calc" indicators from
`docs/extra-indicators/INDICATOR-SCHOOLS-INVENTORY.md`), fully wired into all three surfaces —
**backtester, dashboard, and optimizer** — with each indicator entering as a **confirm/veto vote**
on the primary box signal (the existing WS-I paradigm).

Approved scope decisions (2026-07-25):
1. **Role:** confirm/veto votes only — indicators never originate an entry.
2. **Granularity:** one class + one registry key per named indicator (families NOT collapsed).
3. **Optimizer:** all indicators enter the global auto-search (already automatic via the registry loop).
4. **Tiering:** build **Tier-1 (~125, faithful pure-numpy) now**; **defer Tier-2 (~22, hard/approximate/extra-input)**.
5. **K-cap guardrail:** add a "max simultaneously-enabled indicators" knob to the optimizer. **Approved.**
6. **TA-Lib as a test-only oracle** (dev dependency, never a runtime import). **Approved.**

## 2. Architecture (verified, parity-free)

Every indicator is **written once** and auto-propagates. Verified against the current code:

| Surface | Mechanism | File evidence |
|---|---|---|
| Backtester (both engines) | Votes computed in the shared `indicators/` layer, folded into `entry_gate`; **`fast_engine` consumes precomputed masks, does NOT re-implement** | `engine.py:258`, `optimize/fast_engine.py` (mask args only) |
| Dashboard | Panel built dynamically from `library.schema()` — no hardcoding | `indicators/library.py:383` |
| Optimizer | `_suggest_indicators()` loops **the whole `REGISTRY`** — new keys auto-enter the search; `search_dims` counts `len(REGISTRY)` | `optimize/optimizer.py:56,201` |

Consequence: **no per-indicator edits to engine, dashboard, or optimizer wiring.** Parity is
structural because both engines read the same folded vote mask, and `optimize/test_indicator_parity.py`
already guards it.

### 2.1 Per-indicator work unit (the repeated pattern)

```
1. primitive  → vectorized numpy function (indicators/calc/<school>.py)
2. class      → StanceIndicator (trend/breakout → sign stance) OR Indicator (zone/veto via votes.py)
                + warmup_bars()  (mandatory, no default guessing)
3. registry   → one REGISTRY entry + one SCHEMA entry {label, default mode, params[{default,min,max,step}]}
4. test       → one reference-value unit test (values from TA-Lib/pandas-ta offline, hardcoded)
```

Both base patterns already exist (`StanceIndicator`, `Indicator`) — **no new abstraction is added.**

## 3. Module layout (keeps files focused)

`classic.py` and `library.py` would balloon; split instead:

```
indicators/
  calc/                      # pure vectorized primitives, no framework imports
    ma.py  trend.py  osc.py  vol.py  volume.py  levels.py
  lib_ma.py  lib_trend.py  lib_osc.py  lib_vol.py  lib_volume.py  lib_levels.py  lib_bw.py  lib_quant.py
  library.py                 # imports each lib_* module; aggregates REGISTRY + SCHEMA
```

Each `lib_<school>.py` contributes its own `{key: class}` sub-registry and `{key: schema}` sub-schema;
`library.py` merges them. Adding a school = add a module + one import/merge line.

## 4. Tier-1 build manifest (~125 indicators)

Base pattern: **S** = StanceIndicator, **Z** = zone/oscillator `Indicator`, **V** = veto-only `Indicator`.
Default mode shown; all remain optimizer-tunable.

### 4.1 Moving-average trends — `lib_ma.py` (19) — pattern S, mode confirm
`wma`, `rma` (Wilder/SMMA), `dema`, `tema`, `tma` (triangular), `hma` (Hull), `kama` (Kaufman),
`vidya` (Chande), `alma`, `zlema`, `lsma` (linear-reg MA), `t3` (Tillson), `mcginley`, `sine_wma`,
`vwma`, `evwma`, `gmma` (Guppy ribbon alignment), `ma_envelope`, `ma_displaced`.
*Params: fast/slow (or n) + variant-specific (e.g. kama fast/slow/er-period, alma offset/sigma).*

### 4.2 Trend / directional — `lib_trend.py` (24)
`ppo` (S), `apo` (S), `di_cross` (±DI, S), `aroon` (S), `aroon_osc` (S), `psar` (S), `vortex` (S),
`supertrend` (S), `trix` (S), `kst` (S), `coppock` (S), `dpo` (S), `trend_intensity` (S),
`linreg_slope` (S), `linreg_channel` (S/V), `chandelier` (V), `chande_kroll` (V), `qqe` (S),
`elder_ray` (S), `elder_impulse` (S), `asi` (S, accumulation swing), `expma` (S), `dma` (S), `bbi` (S).

### 4.3 Momentum / oscillator — `lib_osc.py` (23)
`rsi_cutler` (Z), `rsi_connors` (Z), `stoch_rsi` (Z), `kdj` (Z), `williams_r` (Z), `momentum` (S),
`roc` (S), `cmo` (Z), `ultimate_osc` (Z), `tsi` (S), `rvgi` (S), `smi` (Z), `rmi` (Z),
`cmo_chande_dmi` (Z), `fisher` (S), `derivative_osc` (S), `ergodic_osc` (S), `wavetrend` (Z),
`disparity` (S), `balance_of_power` (S), `pgo` (Z), `psy` (Z), `bias` (S).

### 4.4 Volatility — `lib_vol.py` (18)
`atr_norm` (V), `donchian` (S), `starc` (V), `accel_bands` (V), `proj_bands` (V), `stddev` (V),
`hist_vol` (V), `parkinson` (V), `garman_klass` (V), `rogers_satchell` (V), `yang_zhang` (V),
`chaikin_vol` (V), `rvi_dorsey` (Z), `mass_index` (V), `ulcer` (V), `choppiness` (V),
`vol_ratio` (V), `ttm_squeeze` (V).

### 4.5 Volume — `lib_volume.py` (18)
`ad_line` (S), `cmf` (S), `chaikin_osc` (S), `pvt` (S), `tvi` (S), `nvi` (S), `pvi` (S),
`eom` (S), `force_index` (S), `klinger` (S), `vol_osc` (S), `vzo` (Z), `demand_index` (S),
`twiggs_mf` (S), `wvad` (S), `bw_mfi` (S), `anchored_vwap` (S), `volume_ratio_asia` (Z).

### 4.6 Ichimoku / pivots / Bill Williams — `lib_levels.py` + `lib_bw.py` (15)
Ichimoku: `ichimoku_tk_cross` (S), `ichimoku_cloud` (S), `ichimoku_chikou` (S).
Pivots (price-vs-level stance): `pivot_floor` (S), `pivot_woodie` (S), `pivot_camarilla` (S),
`pivot_fib` (S), `pivot_demark` (S), `cpr` (S).
Bill Williams: `alligator` (S), `fractals` (S), `awesome_osc` (S), `accel_osc` (S), `gator` (S),
plus `elliott_wave_osc` (S, 5/34).

### 4.7 Cycles / DeMark / quant (Tier-1 subset) — `lib_quant.py` (8)
`zscore` (Z), `hurst_exp` (V, persistence gate), `dfa` (V), `autocorr` (V), `demarker` (Z),
`td_rei` (Z), `linreg_r2` (V), `efficiency_ratio` (S).

**Tier-1 total ≈ 125** (19 + 24 + 23 + 18 + 18 + 15 + 8).

## 5. Tier-2 — deferred (~22), documented not built

Reason each is deferred (faithfulness / statefulness / extra input):

- **MA/DSP:** `mama_fama`, `frama`, `jma` (proprietary), Ehlers `super_smoother`, `roofing`, `bandpass`.
- **Trend/momentum:** `schaff_trend_cycle`, `laguerre_rsi`.
- **Volatility:** `garch_ewma`.
- **Cycles/Ehlers DSP:** `hilbert_cycle`, `sinewave`, `cyber_cycle`, `center_of_gravity`, `emd`.
- **DeMark (stateful):** `td_sequential`, `td_combo`.
- **Quant:** `kalman`.
- **Cross-series (needs 2nd instrument in `MarketContext`):** `cointegration`, `rolling_corr`,
  `rolling_beta`, `pca_factor`, `ou_halflife`.

Deferral rationale: each either cannot be made faithful in pure numpy without silent approximation
(violates the no-silent-defaults rule), is stateful enough to threaten engine parity, or requires a
`MarketContext` extension to carry a second series. Follow-up spec will pick these up.

## 6. Optimizer-at-scale guardrails (⚠️ required by process memory)

150 enable-flags in one search is a combinatorial + multiple-comparisons hazard. Machinery mostly
already exists; this section is **wiring + one small knob**, not new algorithms.

1. **K-cap on simultaneous enables** — new optimizer knob bounding how many indicators a trial may
   enable (e.g. `--max-enabled K`). Small change in `_suggest_indicators` (reject/repair trials over
   the cap). Keeps the search sparse and interpretable.
2. **School-group masks** — reuse existing `only=()/exclude=()` args + `contributor_masks` so a study
   can optionally scope to one school without removing the global option.
3. **MAP-Elites + two-stage sampler** — already COMPLETE in the optimizer; reuse as the large-space tool.
4. **Speed** — vectorize every primitive; reuse existing memoization (candidate-L1 cache) and the
   recurrence relations in `optimize/RESEARCH_indicator_recurrence_relations.md` for O(1) rolling updates.
5. **Mandatory adopt-gate** — **no indicator/champion is adopted** without: power analysis + noise
   check + dumb control + OOS verification. Non-negotiable (multiple-comparisons trap over 125 candidates).

## 7. Rollout & verification

- **Batches by school** (build/merge cadence — all still land in the one global registry):
  `feat/extra-ind-<school>` → tests + parity green → merge to `dev`. Order: MA → oscillators →
  trend → volatility → volume → levels/BW → quant.
- **TDD, one reference-value test per indicator.** Oracle = TA-Lib / pandas-ta computed **offline**;
  expected values hardcoded into the test. **TA-Lib is `requirements-dev` only — never a runtime import.**
  This is the exact guard against the class of bug that flipped NG's sign (`round(x,4)` precision).
- **Extend `optimize/test_indicator_parity.py`** to auto-sweep every new registry key (fast==engine).
- **Dashboard smoke:** after each batch, verify the new indicators render in the panel from `schema()`
  and toggle correctly (per the UI-verification memory: browser, not API; `--ind-1min`).

## 8. Out of scope

- Tier-2 indicators (§5) — separate follow-up.
- The frozen vendored copy `shareable/wsh6cold_4h_backtester/indicators/` — left pinned.
- Standalone-signal or L2-feature roles (explicitly rejected in Q1).
- Any change to the box signal, exit logic, or sizing.

## 9. Success criteria

1. ~125 Tier-1 indicators registered; each appears in `schema()` and is optimizer-searchable.
2. Every indicator has a passing reference-value test vs an offline TA-Lib/pandas-ta oracle.
3. `test_indicator_parity.py` green across all new keys (fast_engine == engine.py).
4. Optimizer runs with the K-cap knob; a scoped study over any school completes.
5. No runtime dependency on TA-Lib; no silent defaults introduced.
6. Dashboard renders and toggles the new panel entries (browser-verified, `--ind-1min`).
