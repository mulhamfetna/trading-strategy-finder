# Technical-Analysis Schools & World Indicator Inventory

**Purpose:** exhaustive prior-art catalog of the *schools* of technical stock/futures trading and the *indicators / tools* each school uses. This is the scoping anchor for the `extra-indicators` workstream. Next steps (which to implement, parametrize, backtest) will be decided on top of this.

**Legend:** `[calc]` = computed indicator (formula, implementable). `[method]` = pattern/discretionary method (not a single formula). `[data]` = external data feed needed. Overlaps noted with → .

---

## 1. Trend-Following / Moving-Average school
The oldest quant school: smooth price, trade in the direction of the smoothed line.

**Moving averages (smoothers):**
- Simple MA (SMA) `[calc]`
- Exponential MA (EMA) `[calc]`
- Weighted MA (WMA) `[calc]`
- Wilder's Smoothing / Smoothed MA (RMA / SMMA) `[calc]`
- Double EMA (DEMA) `[calc]`
- Triple EMA (TEMA) `[calc]`
- Triangular MA (TMA) `[calc]`
- Hull MA (HMA) `[calc]`
- Kaufman Adaptive MA (KAMA) `[calc]`
- MESA Adaptive MA (MAMA/FAMA, Ehlers) `[calc]`
- Fractal Adaptive MA (FRAMA, Ehlers) `[calc]`
- Variable Index Dynamic Average (VIDYA, Chande) `[calc]`
- Arnaud Legoux MA (ALMA) `[calc]`
- Zero-Lag EMA (ZLEMA) `[calc]`
- Least-Squares / Linear-Regression MA (LSMA) `[calc]`
- Jurik MA (JMA) `[calc]`
- T3 (Tillson) `[calc]`
- McGinley Dynamic `[calc]`
- Sine-Weighted MA `[calc]`
- Volume-Weighted MA (VWMA) `[calc]` → Volume
- Elastic Volume-Weighted MA (eVWMA) `[calc]` → Volume
- Guppy Multiple MA (GMMA, ribbon of 12) `[calc]`
- MA Ribbon / MA Envelopes / Displaced MA `[calc]`
- Ehlers filters: SuperSmoother, Roofing, Bandpass, Butterworth `[calc]` → Cycles

**Trend / directional indicators:**
- MACD + MACD Histogram `[calc]`
- Percentage Price Oscillator (PPO) `[calc]`
- Absolute Price Oscillator / Price Oscillator `[calc]`
- ADX / DMI (+DI, −DI, ADXR; Wilder) `[calc]`
- Aroon + Aroon Oscillator `[calc]`
- Parabolic SAR (Wilder) `[calc]`
- Vortex Indicator (VI+ / VI−) `[calc]`
- Supertrend `[calc]`
- TRIX (triple-smoothed ROC) `[calc]`
- Know Sure Thing (KST, Pring) `[calc]`
- Coppock Curve `[calc]`
- Schaff Trend Cycle `[calc]` → Cycles
- Detrended Price Oscillator (DPO) `[calc]`
- Trend Intensity Index `[calc]`
- Linear Regression Slope / Curve / Channel `[calc]` → Stat
- Chande Kroll Stop / Chandelier Exit (ATR trailing) `[calc]`
- QQE (Quantitative Qualitative Estimation) `[calc]`
- Gann HiLo Activator `[calc]` → Gann
- Elder Ray (Bull/Bear Power), Elder Impulse System `[calc]`
- Accumulation Swing Index (ASI) + Swing Index (Wilder) `[calc]`
- EXPMA / DMA / BBI (Asian-retail trend set) `[calc]`

---

## 2. Momentum / Oscillator school
Measure speed & overbought/oversold, hunt divergences.

- Relative Strength Index (RSI, Wilder) `[calc]`
- Cutler's RSI, Connors RSI, Laguerre RSI (Ehlers) `[calc]`
- Stochastic Oscillator (fast / slow / full; Lane) `[calc]`
- Stochastic RSI `[calc]`
- KDJ (Asian stochastic variant) `[calc]`
- Williams %R `[calc]`
- Commodity Channel Index (CCI, Lambert) `[calc]`
- Momentum (n-period price change) `[calc]`
- Rate of Change (ROC / Price ROC) `[calc]`
- Chande Momentum Oscillator (CMO) `[calc]`
- Ultimate Oscillator (Williams) `[calc]`
- True Strength Index (TSI) `[calc]`
- Relative Vigor Index (RVI/RVGI) `[calc]`
- Stochastic Momentum Index (SMI, Blau) `[calc]`
- Relative Momentum Index (RMI) `[calc]`
- Dynamic Momentum Index (DMI, Chande) `[calc]`
- Fisher Transform (Ehlers) `[calc]`
- Derivative Oscillator, Ergodic Oscillator `[calc]`
- Wave Trend Oscillator (LazyBear) `[calc]`
- Disparity Index `[calc]`
- Balance of Power `[calc]`
- Pretty Good Oscillator `[calc]`
- Awesome / Accelerator Oscillator (Bill Williams) `[calc]` → Bill Williams
- Psychological Line (PSY), BIAS (Asian-retail momentum) `[calc]`

---

## 3. Volatility school
Trade the width of the range / bands.

- Bollinger Bands + %B + BandWidth (Bollinger) `[calc]`
- Average True Range (ATR) + Normalized ATR (Wilder) `[calc]`
- Keltner Channels `[calc]`
- Donchian Channels `[calc]` → Breakout
- STARC Bands, Acceleration Bands, Projection Bands `[calc]`
- Standard Deviation / rolling variance `[calc]` → Stat
- Historical (close-to-close) Volatility `[calc]`
- Parkinson / Garman-Klass / Rogers-Satchell / Yang-Zhang range estimators `[calc]` → Quant
- Chaikin Volatility `[calc]`
- Relative Volatility Index (Dorsey) `[calc]`
- Mass Index (Dorsey) `[calc]`
- Ulcer Index `[calc]`
- Choppiness Index `[calc]`
- Volatility Ratio / Volatility Stop `[calc]`
- TTM Squeeze / Bollinger-in-Keltner squeeze (Carter) `[calc]`
- GARCH / EWMA conditional volatility `[calc]` → Quant
- VIX, VVIX, SKEW, term structure `[data]` → Sentiment

---

## 4. Volume / Money-Flow school
Confirm price with participation.

- On-Balance Volume (OBV, Granville) `[calc]`
- Accumulation/Distribution Line (Williams/Chaikin) `[calc]`
- Chaikin Money Flow (CMF) `[calc]`
- Chaikin Oscillator `[calc]`
- Money Flow Index (MFI) `[calc]` → Momentum
- Price Volume Trend (PVT) `[calc]`
- Volume Price Trend / Trade Volume Index (TVI) `[calc]`
- Negative & Positive Volume Index (NVI / PVI) `[calc]`
- Ease of Movement (EOM/EMV, Arms) `[calc]`
- Force Index (Elder) `[calc]`
- Klinger Volume Oscillator `[calc]`
- Volume Oscillator / Volume ROC `[calc]`
- Volume Zone Oscillator (VZO) `[calc]`
- Demand Index (Sibbet) `[calc]`
- Twiggs Money Flow `[calc]`
- Williams Variable Accumulation/Distribution (WVAD) `[calc]`
- Market Facilitation Index (BW MFI, Bill Williams) `[calc]`
- Better Volume `[calc]`
- Volume-Weighted Average Price (VWAP) + Anchored VWAP + VWAP bands `[calc]`
- Volume Profile / Volume-by-Price (VPOC, HVN/LVN) `[method]` → Market Profile
- Volume Ratio (VR, Asian-retail) `[calc]`

---

## 5. Ichimoku Kinko Hyo school (Japanese)
A single self-contained system.
- Tenkan-sen (conversion line) `[calc]`
- Kijun-sen (base line) `[calc]`
- Senkou Span A & B → Kumo (cloud) `[calc]`
- Chikou Span (lagging span) `[calc]`
- Cloud thickness / twist / flat-Kijun magnets `[method]`

---

## 6. Candlestick / Japanese price-action school
Single- & multi-bar reversal/continuation shapes.
- Single: Doji (+ dragonfly/gravestone/long-legged), Hammer, Hanging Man, Shooting Star, Inverted Hammer, Marubozu, Spinning Top `[method]`
- Two-bar: Bullish/Bearish Engulfing, Harami (+ cross), Piercing, Dark Cloud Cover, Tweezer top/bottom, Kicker `[method]`
- Three-bar: Morning/Evening Star, Three White Soldiers, Three Black Crows, Three Inside/Outside, Abandoned Baby `[method]`
- Continuation: Rising/Falling Three Methods, Tasuki, Windows (gaps) `[method]`
- Derived charts: Heikin-Ashi `[calc]`, Candle Volume `[calc]`

---

## 7. Classical charting / Dow Theory school (Edwards & Magee)
- Dow Theory tenets (trend confirmation, phases) `[method]`
- Support / Resistance, Trendlines, Channels `[method]`
- Reversals: Head & Shoulders (+ inverse), Double/Triple Top & Bottom, Rounding, Diamond `[method]`
- Continuation: Triangles (asc/desc/symmetrical), Flags, Pennants, Wedges, Rectangles, Cup & Handle, Broadening `[method]`
- Gaps: common / breakaway / runaway / exhaustion / island `[method]`

---

## 8. Pivot / Level-calculation school
Formula-derived intraday support/resistance.
- Floor (Classic) Pivots: PP, R1–R3, S1–S3 `[calc]`
- Woodie's Pivots `[calc]`
- Camarilla Pivots `[calc]`
- Fibonacci Pivots `[calc]`
- DeMark Pivots `[calc]` → DeMark
- Central Pivot Range (CPR) `[calc]`

---

## 9. Fibonacci / Harmonic-pattern school
- Fibonacci retracements / extensions / projections `[calc]`
- Fibonacci fans / arcs / time zones / channels / spiral `[calc]`
- Fibonacci clusters / confluence `[method]`
- Harmonic patterns: ABCD, Gartley, Butterfly, Bat (+ Alt Bat), Crab (+ Deep Crab), Cypher, Shark, Three Drives, 5-0 `[method]`

---

## 10. Elliott Wave school
- Impulse (1-2-3-4-5) & corrective (A-B-C) counts `[method]`
- Diagonals, triangles, WXY/WXYXZ combinations `[method]`
- Wave-degree labeling; Fibonacci ratio targets within waves `[method]`
- Elliott Wave Oscillator (5/34 momentum proxy) `[calc]`

---

## 11. Gann school (W.D. Gann)
- Gann Angles (1×1, 2×1, 1×2, …) & Gann Fan `[calc]`
- Square of 9 / Square of 144 / Hexagon chart `[calc]`
- Gann Box, Gann retracements (1/8 & 1/3 divisions) `[calc]`
- Time cycles / anniversary & "natural" dates `[method]`
- Gann HiLo Activator `[calc]` → Trend

---

## 12. Cycle / Spectral / Ehlers DSP school (Hurst, Ehlers)
Treat price as signal, extract dominant cycle.
- Hurst nominal cycle model / cyclic RSI `[method]`
- Fourier / spectral analysis, MESA (max-entropy) `[calc]`
- Hilbert Transform: dominant cycle period, phase, trend mode (Ehlers) `[calc]`
- Sine Wave & Even Better Sinewave (Ehlers) `[calc]`
- Cyber Cycle, Center-of-Gravity Oscillator (Ehlers) `[calc]`
- Instantaneous Trendline, Cycle Period (Ehlers) `[calc]`
- Bandpass / Roofing / SuperSmoother filters (Ehlers) `[calc]`
- Schaff Trend Cycle `[calc]`
- Empirical Mode Decomposition (EMD) `[calc]`
- Hurst exponent (R/S analysis), DFA — persistence/mean-reversion measure `[calc]` → Quant

---

## 13. Wyckoff school
Supply/demand via "Composite Man" logic.
- Accumulation / Distribution schematics & phases (A–E) `[method]`
- Events: Selling/Buying Climax, Automatic Rally, Secondary Test, Spring, Upthrust (UTAD), SOS/SOW `[method]`
- Effort vs Result (price/volume) `[method]`
- Wyckoff Wave, Optimism-Pessimism (O-P) Index, Force Index `[calc]`
- Relative Strength (vs market), Point & Figure counts `[method]` → P&F

---

## 14. Market Profile / Auction-Market-Theory school (Steidlmayer)
- TPO (Time-Price-Opportunity) profile `[method]`
- Point of Control (POC) / Naked POC `[calc]`
- Value Area (VAH / VAL, ~70%) `[calc]`
- Initial Balance (IB) `[calc]`
- Profile shapes (b / P / D / balanced) `[method]`
- Single prints, excess, poor highs/lows `[method]`
- Composite / merged profiles `[method]`
- Volume Profile (VPOC, HVN/LVN) `[calc]` → Volume

---

## 15. Order-Flow / Market-Microstructure school
Sub-bar, needs tick/DOM data.
- Depth of Market (DOM) / order-book ladder `[data]`
- Footprint / bid-ask cluster charts `[data]`
- Cumulative Volume Delta (CVD) + delta divergence `[calc]`
- Volume Delta per bar `[calc]`
- Time & Sales (tape reading), speed of tape `[data]`
- Absorption / Exhaustion / Iceberg detection `[method]`
- Order-Flow Imbalance, Trade Imbalance `[calc]`
- Liquidity heatmaps `[data]`
- VPIN (Volume-synchronized Prob. of Informed Trading) `[calc]` → Quant

---

## 16. DeMark school (Tom DeMark)
- TD Sequential (Setup 1-9 + Countdown 1-13) `[calc]`
- TD Combo `[calc]`
- TD Lines (auto trendlines) `[calc]`
- TD Range Expansion Index (REI) `[calc]`
- TD DeMarker I / II `[calc]`
- TDST support/resistance levels `[calc]`
- TD Pressure, TD Differential, TD Camouflage `[calc]`

---

## 17. Point & Figure school
- P&F chart (X/O columns), box size & reversal `[calc]`
- Patterns: double/triple top & bottom breakouts, bullish/bearish signal, catapult `[method]`
- Price objectives: horizontal & vertical counts `[calc]`
- Bullish Percent Index (P&F breadth) `[calc]` → Breadth

---

## 18. Alternative-charting school (price/volume/time re-bucketing)
- Renko `[calc]`
- Kagi `[calc]`
- Three-Line Break `[calc]`
- Range bars / Tick charts / Volume bars `[calc]`
- Heikin-Ashi `[calc]` → Candlestick

---

## 19. Bill Williams / Chaos-Theory school
- Alligator (3 displaced smoothed MAs) `[calc]`
- Fractals (5-bar) `[calc]`
- Awesome Oscillator (AO) `[calc]`
- Accelerator/Decelerator Oscillator (AC) `[calc]`
- Gator Oscillator `[calc]`
- Market Facilitation Index `[calc]` → Volume
- "Zone" & "Wiseman" trade logic `[method]`

---

## 20. Breadth / Market-Internals school
Index-level, needs constituent data.
- Advance/Decline Line & Ratio `[data]`
- McClellan Oscillator & Summation Index `[data]`
- TRIN / Arms Index `[data]`
- TICK, TIKI `[data]`
- New Highs − New Lows / High-Low Index `[data]`
- % of stocks above 50/200-day MA `[data]`
- Bullish Percent Index `[data]`
- Up/Down Volume & Volume ratio `[data]`
- Absolute Breadth Index, Hindenburg Omen, Zweig Breadth Thrust `[data]`

---

## 21. Sentiment / Contrarian & Positioning school
- Put/Call Ratio `[data]`
- VIX / VVIX / SKEW / term structure `[data]` → Volatility
- Commitments of Traders (COT) positioning `[data]`
- AAII survey, Investors Intelligence Bull/Bear, NAAIM Exposure `[data]`
- CNN Fear & Greed Index `[data]`
- Short interest / short ratio, margin debt, insider transactions, fund flows `[data]`

---

## 22. Intermarket / Relative-Strength / Rotation school (Murphy)
- Comparative Relative Strength (ratio charts, e.g. SPX/Gold) `[calc]`
- Mansfield RS, Dorsey Relative Strength `[calc]`
- Relative Rotation Graphs (RRG: RS-Ratio & RS-Momentum) `[calc]`
- Sector-rotation / business-cycle models `[method]`
- Cross-asset correlation matrices; yield-curve & spread signals `[calc]` `[data]`
- IBD/Minervini RS Rating (percentile rank) `[calc]`
- Alpha / Beta vs benchmark `[calc]` → Quant

---

## 23. Statistical / Quant / Mean-Reversion school
- Z-score / rolling standardization `[calc]`
- Linear regression, regression channels (Raff), slope/R² `[calc]`
- Kalman filter (adaptive trend) `[calc]`
- Cointegration & pairs spread, ADF stationarity test `[calc]`
- Ornstein-Uhlenbeck fit, half-life of mean reversion `[calc]`
- Autocorrelation / partial autocorrelation `[calc]`
- Hurst exponent / fractal dimension `[calc]` → Cycles
- Principal Component Analysis, factor exposures `[calc]`
- Rolling correlation / beta `[calc]`
- Performance stats used as filters: Sharpe, Sortino, Calmar `[calc]`
- ML feature families (lagged returns, rolling moments, entropy, wavelets) `[calc]`

---

## 24. Median-Line / Andrews school
- Andrews Pitchfork (median line + parallels) `[calc]`
- Schiff & Modified Schiff Pitchforks `[calc]`
- Reaction/warning lines, sliding parallels `[calc]`

---

## 25. Smart-Money-Concepts / ICT school (modern price-action)
- Market Structure: Break of Structure (BOS), Change of Character (CHoCH) `[method]`
- Order Blocks (+ Breaker & Mitigation blocks) `[method]`
- Fair Value Gaps (FVG) / Imbalances `[calc]`  ← *(note: you already have a gold-FVG result on file)*
- Liquidity pools & sweeps (buy-side/sell-side), stop hunts, inducement `[method]`
- Premium/Discount zones, Optimal Trade Entry (OTE, Fib-based) `[method]`
- Displacement, Killzones (session-timing) `[method]`

---

## 26. Seasonality / Calendar-effect school
- Monthly & day-of-week seasonality, turn-of-month `[calc]`
- "Sell in May", Santa Claus rally, January effect `[method]`
- Presidential / 4-year & decennial cycles `[method]`
- Holiday & options-expiration (OPEX) effects `[method]`

---

## Cross-cutting notes
- **Asian-retail TA bundle** (very common on Chinese/Korean platforms) reuses many above under local names: KDJ, MACD, BOLL, BIAS, PSY, VR, WR, CCI, DMA, TRIX, EXPMA, BBI, DMI, WVAD, ASI, BRAR, CR, OBOS.
- **"Indicator" vs "method":** roughly half of these schools trade *patterns/structure* (`[method]`) not formulas — implementable only as heuristic detectors, not one-line calcs.
- **Data-gated:** breadth, sentiment, intermarket, and order-flow schools need feeds beyond OHLCV (`[data]`) — relevant to what we can realistically add to the current engine.

---

*Compiled as the prior-art pass for `extra-indicators`. Awaiting direction on which schools/indicators to prioritize, parametrize, and backtest.*
