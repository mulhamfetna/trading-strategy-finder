# Indicators split: Leading vs Lagging (165-indicator library)

**Status:** ✅ APPROVED + WIRED (issue #30). Decision: **three groups** (Leading / Lagging / **Filter-Regime**), hybrids kept as classified below, volume labelled **Leading**. The classification is emitted by `library.schema()` as a `lead_lag` field per indicator (`leading`/`lagging`/`filter`) and the dashboard indicator picker can now **group by cadence** and **filter by cadence** (a per-row badge shows each indicator's class), alongside the existing **family** grouping.

---

## 1. The two definitions (plain language)

- **Lagging indicator** — *follows* price. It is built from an average / cumulative sum / trailing calculation of **past** prices, so it turns **after** the move has already begun. Its job is **confirmation** ("the trend is real, and up"). Trade-off: reliable, but late. → *Moving averages, MACD, ADX, Supertrend, Bollinger…*
- **Leading indicator** — tries to *precede* price. It reacts to the **rate of change / stretch / cycle phase** of price and fires **before or at** the turn, so it can **anticipate** ("momentum is fading — a reversal is near"). Trade-off: early, but noisier / more false signals. → *RSI, Stochastic, pivots, order blocks, Awesome Oscillator…*

**Rule of thumb used here:** classify by the indicator's **core mechanism**, not by how a trader happens to use it.
- Averages / cumulative sums / trailing stops / regression on past bars → **Lagging**.
- Momentum (rate-of-change), overbought/oversold oscillators, pre-drawn price levels, cycle/phase and reversal detectors, mean-reversion, volume-flow divergence → **Leading**.

## 2. The honest caveat: a third, non-directional axis

A large block of this library does **not** predict *direction* at all — it measures **regime / volatility / relationship**, and in this system those are wired as **veto filters** ("don't trade when it's too choppy / decoupled"). They sit on the *lagging* side by construction (computed from past bars), but calling them "lagging **direction** signals" is misleading. They are flagged **⚙ Filter** below.

Two more markers:
- **◑ Hybrid** — genuinely debatable; placed in the group its *core* leans toward, with a one-line reason.
- Volume indicators are marked **Leading** by the accumulation/distribution convention (volume is said to precede price), but in practice most act as **confirming** tools — treat that group's "Leading" label as "leading-or-confirming."

**So the practical picture is three buckets, not two:** **Leading**, **Lagging**, and **⚙ Filter/Regime** (non-directional). Section 6 recommends how to present that in the dashboard.

---

## 3. Quick reference — the two groups (flat lists)

### 🟢 LEADING (anticipate the turn)
`rsi` `stochastic` `mfi` `cci` `obv` · `order_block` `fvg` `ifvg` `breaker` `cisd`
`rsi_cutler` `rsi_connors` `stoch_rsi` `kdj` `williams_r` `cmo` `ultimate_osc` `smi` `rmi` `cmo_chande_dmi` `wavetrend` `pgo` `psy` `momentum` `roc` `disparity` `bias` `balance_of_power` `tsi` `rvgi` `fisher` `derivative_osc` `ergodic_osc`
`qqe`◑ `elder_ray`◑ · `rvi_dorsey`
`ad_line` `cmf` `chaikin_osc` `pvt` `tvi` `nvi` `pvi` `eom` `force_index` `klinger` `vol_osc` `demand_index` `twiggs_mf` `wvad` `bw_mfi` `vzo`
`ichimoku_cloud` `pivot_floor` `pivot_woodie` `pivot_demark` `pivot_camarilla` `pivot_fib` `cpr`
`fractals` `awesome_osc`◑ `accel_osc` `elliott_wave_osc`◑
`zscore` `demarker` `td_rei`
`roofing`◑ `bandpass` `laguerre_rsi` `schaff_trend_cycle` `cyber_cycle` `center_of_gravity` `sinewave` `hilbert_cycle` `td_sequential` `td_combo` `ou_halflife`◑
`rolling_beta` `cointegration` `pca_factor`◑

### 🔵 LAGGING (confirm the trend)
`ema_trend` `sma_trend` `macd`◑ `vwap` `keltner` `bollinger`⚙ `adx`⚙ `structure_trend`
`wma` `rma` `dema` `tema` `tma` `hma` `zlema` `sine_wma` `lsma` `vwma` `kama` `vidya` `alma` `t3` `mcginley` `evwma` `gmma` `ma_envelope` `ma_displaced`
`ppo` `apo` `di_cross` `aroon`◑ `aroon_osc`◑ `psar` `vortex` `supertrend` `trix`◑ `kst` `coppock` `dpo`◑ `trend_intensity` `linreg_slope` `linreg_channel` `chandelier`⚙ `chande_kroll`⚙ `elder_impulse`◑ `asi` `expma` `dma` `bbi`
`donchian`◑ `anchored_vwap` `ichimoku_tk_cross` `ichimoku_chikou` `alligator` `gator`
`super_smoother` `frama` `mama_fama`◑ `jma` `emd`◑ `kalman`

### ⚙ FILTER / REGIME (non-directional — sit on the lagging side, but gate rather than point)
Volatility: `atr_norm` `stddev` `hist_vol` `parkinson` `garman_klass` `rogers_satchell` `yang_zhang` `ulcer` `vol_ratio` `starc` `accel_bands` `proj_bands` `chaikin_vol` `mass_index`◑ `choppiness`◑ `ttm_squeeze`◑
Statistical/regime: `hurst_exp` `dfa` `autocorr` `linreg_r2` `efficiency_ratio` `garch_ewma` `rolling_corr` `volume_ratio_asia`

*(If you want a strict two-way split for the dashboard, the ⚙ Filter set folds into **Lagging**; §6.)*

---

## 4. Full breakdown, by family (traceable)

`class`: **L**=Leading · **G**=laGging · **⚙**=Filter/regime · **◑**=hybrid (note).

### builtin (18)
| key | label | class | why |
|---|---|---|---|
| ema_trend | EMA trend | G | moving average |
| sma_trend | SMA trend | G | moving average |
| macd | MACD | G ◑ | MA difference (lag); histogram *divergence* can lead |
| vwap | VWAP | G | cumulative volume-weighted average (a reference level) |
| keltner | Keltner | G | EMA + ATR bands |
| obv | OBV | L | volume-flow; accumulation precedes price / diverges early |
| cci | CCI breakout | L | momentum oscillator (deviation from mean) |
| rsi | RSI | L | momentum / overbought-oversold |
| stochastic | Stochastic | L | position-in-range momentum |
| mfi | MFI | L | volume-weighted RSI |
| bollinger | Bollinger (veto) | G ⚙ | SMA + σ bands; squeeze *can* anticipate expansion |
| adx | ADX (veto) | G ⚙ | trend-**strength** filter, non-directional |
| structure_trend | Structure trend (SMC) | G | trend structure confirms after the swing |
| order_block | Order block (SMC) | L | pre-drawn supply/demand zone → anticipates reaction |
| fvg | Fair value gap (SMC) | L | imbalance zone price is expected to revisit |
| ifvg | Inverse FVG (SMC) | L | flipped imbalance → anticipatory |
| breaker | Breaker block (SMC) | L | failed OB → reversal zone |
| cisd | CISD delivery shift (SMC) | L | change-in-state-of-delivery → early reversal cue |

### ma — moving averages (19) — **all Lagging by definition**
`wma` `rma` `dema` `tema` `tma` `hma` `zlema` `sine_wma` `lsma` `vwma` `kama` `vidya` `alma` `t3` `mcginley` `evwma` `gmma` `ma_envelope`(⚙ on its overextension-veto side) `ma_displaced` → **G**.
*Note:* the adaptive / "reduced-lag" ones (`hma`, `zlema`, `t3`, `kama`, `vidya`, `alma`, `dema`, `tema`) still **lag** — they just lag *less*. They are not leading.

### oscillator (23) — **all Leading**
`rsi_cutler` `rsi_connors` `stoch_rsi` `kdj` `williams_r` `cmo` `ultimate_osc` `smi` `rmi` `cmo_chande_dmi` `wavetrend` `pgo` `psy` `momentum` `roc` `disparity` `bias` `balance_of_power` `tsi`◑ `rvgi` `fisher` `derivative_osc` `ergodic_osc`◑ → **L**.
*◑ note:* `tsi` and `ergodic_osc` are **double-smoothed** momentum — leading in intent, but the smoothing adds lag.

### trend (24) — mostly Lagging
| key | label | class | why |
|---|---|---|---|
| ppo / apo | PPO / APO | G | MACD-family (MA difference) |
| di_cross | DMI ±DI cross | G | directional movement, smoothed |
| aroon / aroon_osc | Aroon / Aroon Osc | G ◑ | trend-family, but flags new trends relatively early |
| psar | Parabolic SAR | G | trailing stop-and-reverse |
| vortex | Vortex | G | trend via true-range sums |
| supertrend | Supertrend | G | ATR trailing trend |
| trix | TRIX | G ◑ | triple-smoothed (very lagging); zero-cross/divergence can lead |
| kst | Know Sure Thing | G | summed, smoothed ROC |
| coppock | Coppock Curve | G | long, smoothed momentum |
| dpo | Detrended Price Osc | G ◑ | detrended **cycle** tool; centered/displaced, not real-time predictive |
| trend_intensity | Trend Intensity | G ⚙ | strength gauge |
| linreg_slope / linreg_channel | Lin-Reg slope / channel | G / G⚙ | regression on past bars |
| chandelier / chande_kroll | Chandelier / Chande-Kroll | G ⚙ | ATR trailing **stops** |
| qqe | QQE | **L** ◑ | RSI core (leading) wrapped in a smoothed ATR band |
| elder_ray | Elder Ray | **L** ◑ | bull/bear power (price − EMA); diverges ahead of turns |
| elder_impulse | Elder Impulse | G ◑ | EMA + MACD state → trend/momentum blend |
| asi | Accum. Swing Index | G | cumulative swing → trend |
| expma / dma / bbi | EXPMA / DMA / BBI | G | MA crosses / averages of MAs |

### volatility (18) — **⚙ Filter/regime** (non-directional), lagging by construction
`atr_norm` `stddev` `hist_vol` `parkinson` `garman_klass` `rogers_satchell` `yang_zhang` `ulcer` `vol_ratio` `starc` `accel_bands` `proj_bands` `chaikin_vol` → **G⚙** (measure realized range; used as vetoes).
`mass_index`◑ `choppiness`◑ `ttm_squeeze`◑ → **G⚙**, but **anticipatory**: they are used to *pre-empt* a volatility **expansion** (a leading use, for volatility not direction).
`donchian` → **G ◑** (channel midline lags; a channel **breakout** is an early/leading trigger).
`rvi_dorsey` (Relative Volatility Index) → **L** (a volatility-based *momentum oscillator*).

### volume (18) — **Leading-or-confirming** (accumulation precedes price)
`ad_line` `cmf` `chaikin_osc` `pvt` `tvi` `nvi` `pvi` `eom`◑ `force_index` `klinger` `vol_osc`◑ `demand_index` `twiggs_mf` `wvad` `bw_mfi`◑ `vzo` → **L** (flow / divergence).
`anchored_vwap` → **G** (cumulative average from an anchor — a lagging reference level).
`volume_ratio_asia` → **⚙** (session-relative volume → regime filter).

### levels (9) — pre-drawn price levels → mostly Leading
| key | label | class | why |
|---|---|---|---|
| ichimoku_tk_cross | Tenkan/Kijun cross | G | midpoint-MA cross → lags |
| ichimoku_cloud | Kumo cloud | **L** | spans projected **26 bars forward** → forward-looking |
| ichimoku_chikou | Chikou span | G | lagging span (price shifted 26 **back**) |
| pivot_floor / woodie / demark / camarilla / fib | pivots | **L** | levels computed **before** the session for expected S/R |
| cpr | Central Pivot Range | **L** | next-session value area, pre-drawn |

### bill_williams (6)
| key | label | class | why |
|---|---|---|---|
| alligator | Alligator | G | three smoothed MAs |
| gator | Gator Osc | G | Alligator-derived (MA convergence) |
| fractals | Williams Fractals | **L** | local reversal pivots |
| awesome_osc | Awesome Osc | **L** ◑ | momentum (MA-of-median difference) |
| accel_osc | Accelerator Osc | **L** | acceleration of momentum → leads AO |
| elliott_wave_osc | Elliott Wave Osc | **L** ◑ | MA-difference momentum used to time waves |

### quant (8)
| key | label | class | why |
|---|---|---|---|
| zscore | Z-Score | **L** | standardized stretch → mean-reversion signal |
| demarker | DeMarker | **L** | exhaustion oscillator |
| td_rei | TD Range Expansion Index | **L** | range-expansion → reversal timing |
| hurst_exp | Hurst Exponent | ⚙ | persistence/regime (trending vs mean-reverting) |
| dfa | DFA exponent | ⚙ | detrended-fluctuation regime measure |
| autocorr | Autocorrelation | ⚙ | serial-dependence regime filter |
| linreg_r2 | Lin-Reg R² | ⚙ | trend-**quality** (how linear), non-directional |
| efficiency_ratio | Kaufman Efficiency Ratio | ⚙ | trend efficiency (signal/noise) filter |

### dsp — Ehlers / cycle / signal-processing (18)
| key | label | class | why |
|---|---|---|---|
| super_smoother | SuperSmoother | G | low-lag smoother (still an average) |
| frama | Fractal Adaptive MA | G | adaptive MA |
| mama_fama | MESA Adaptive MA | G ◑ | adaptive MA (low-lag, but MA) |
| jma | Jurik MA | G | low-lag smoother |
| kalman | Kalman trend | G | recursive state estimate of the mean |
| emd | Ehlers EMD | G ◑ | decomposition → trend **and** cycle mode |
| roofing | Roofing filter | **L** ◑ | band-passes the tradeable **cycle** |
| bandpass | Band-Pass | **L** | isolates the dominant cycle |
| laguerre_rsi | Laguerre RSI | **L** | fast, low-lag RSI |
| schaff_trend_cycle | Schaff Trend Cycle | **L** | cycle-normalized MACD → early turns |
| cyber_cycle | Cyber Cycle | **L** | cycle-component extractor |
| center_of_gravity | Center of Gravity | **L** | near-zero-lag turning-point oscillator |
| sinewave | Sine Wave | **L** | cycle **phase** → calls the turn ahead of price |
| hilbert_cycle | Hilbert dominant cycle | **L** ⚙ | measures the cycle (used as a veto) |
| td_sequential | TD Sequential | **L** | counts toward an exhaustion **reversal** |
| td_combo | TD Combo | **L** | perfected reversal count |
| ou_halflife | OU half-life | **L** ◑ | mean-reversion speed → anticipates reversion (veto here) |
| garch_ewma | EWMA/GARCH vol | ⚙ | volatility **forecast** filter |

### cross_series (4) — relational (need a reference instrument)
| key | label | class | why |
|---|---|---|---|
| rolling_beta | Cross-beta lead | **L** | uses the reference's move to lead this instrument |
| cointegration | Pair spread z-score | **L** | spread mean-reversion → anticipatory |
| pca_factor | PCA common factor | **L** ◑ | common-factor direction (leading-ish) |
| rolling_corr | Cross-correlation | ⚙ | decoupling **filter** (veto), non-directional |

---

## 5. Counts

| Bucket | Count | Notes |
|---|---:|---|
| 🟢 Leading | **80** | oscillators (23) + volume-flow (16) + leading builtin/SMC (10) + dsp cycle/reversal (11) + levels (7) + bill-williams momentum (4) + quant osc (3) + cross-series (3) + `qqe`/`elder_ray` (2) + `rvi_dorsey` (1) |
| 🔵 Lagging | **61** | all MAs (19) + trend-followers (22) + lagging builtin (8) + dsp smoothers (6) + `alligator`/`gator` (2) + `ichimoku` tk/chikou (2) + `donchian` (1) + `anchored_vwap` (1) |
| ⚙ Filter / Regime | **24** | volatility vetoes (16) + statistical/regime (`hurst_exp` `dfa` `autocorr` `linreg_r2` `efficiency_ratio` = 5) + `garch_ewma` + `volume_ratio_asia` + `rolling_corr` |
| **Total** | **165** | 80 + 61 + 24 |

*(Exact members are the tables above. Note: the `G⚙` items — `bollinger` `adx` `trend_intensity` `linreg_channel` `chandelier` `chande_kroll` — are counted under **Lagging**; they're MA/ATR/stop-based and directional-ish, so they stay lagging even though they act as vetoes. The 24 in the Filter bucket are the *purely* non-directional ones.)*

## 6. Recommendation for the dashboard (when you approve)

Two viable groupings for the indicator picker:

- **Option A — strict two groups (as you asked):** **Leading** and **Lagging**, with the ⚙ Filter/regime set folded into **Lagging** (they are computed from past data and used as confirmation/vetoes). Simple; matches "leading vs lagging."
- **Option B — three groups (more honest):** **Leading**, **Lagging**, **Filter/Regime**. The third bucket is exactly the volatility + statistical vetoes; separating them makes it obvious they gate rather than point. *(Recommended — it also maps cleanly onto how the optimizer already treats them as vetoes.)*

Either way: keep the existing **family** grouping too, and add lead/lag as a second toggle/tag (an indicator has both a family *and* a lead/lag class), so you can select e.g. "all Leading oscillators" or "Lagging MAs only."

**Open questions for you:**
1. Option **A** (2 groups) or **B** (3 groups, recommended)?
2. Any specific ◑-hybrids you want moved (e.g. treat `qqe`/`elder_ray` as Lagging with their trend family, or `donchian` as Leading for breakouts)?
3. Should volume be labelled **Leading** (accumulation-precedes-price convention) or a separate **Confirming** tag?
