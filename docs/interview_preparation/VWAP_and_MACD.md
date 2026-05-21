## VWAP (Volume-Weighted Average Price)
VWAP is a trading benchmark that gives the average price an asset has traded at throughout the day, based on both volume and price.
## How it Works
Unlike a standard moving average, VWAP gives more weight to price levels with high trading volume.

* If a stock trades at $100 with 1,000,000 shares, and later at $101 with only 100 shares, the VWAP will stay very close to $100.
* It resets at the beginning of each trading day or session.

## Why Traders Use It

* Intraday Support/Resistance: Day traders view the VWAP line as a key psychological level. Prices often bounce off it.
* Institutional Benchmark: Large funds use VWAP to measure execution quality. Buying below the day's VWAP is considered a good entry; buying above it is considered paying a premium.

------------------------------
## MACD (Moving Average Convergence Divergence)
MACD is a trend-following momentum indicator that shows the relationship between two moving averages of an asset’s price.
## How it Works
The MACD indicator consists of three components calculated from your OHLCV data:

   1. MACD Line: The difference between a fast EMA (usually 12 periods) and a slow EMA (usually 26 periods).
   2. Signal Line: An EMA of the MACD line itself (usually 9 periods).
   3. Histogram: The visual distance between the MACD Line and the Signal Line.

## Why Traders Use It

* Trend Direction: When the MACD line is above zero, the short-term momentum is bullish. Below zero, it is bearish.
* Crossover Signals: A bullish signal is triggered when the MACD line crosses above the Signal Line. A bearish signal is triggered when it crosses below.

------------------------------
## Pandas Implementation
Here is how you can calculate both indicators using the pandas methods (ewm, rolling, expand) we discussed earlier:

import pandas as pd
# --- 1. VWAP Calculation ---# VWAP requires cumulative typical price * volume divided by cumulative volumetypical_price = (df['High'] + df['Low'] + df['Close']) / 3
df['vwap'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
# --- 2. MACD Calculation ---# Step 1: Calculate the Fast and Slow EMAsema12 = df['Close'].ewm(span=12, adjust=False).mean()ema26 = df['Close'].ewm(span=26, adjust=False).mean()
# Step 2: Calculate MACD Line and Signal Line
df['macd_line'] = ema12 - ema26
df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
# Step 3: Calculate Histogram
df['macd_hist'] = df['macd_line'] - df['macd_signal']

------------------------------
Would you like to see how to code a complete strategy backtest that combines VWAP for intraday direction and the MACD for entry signals?

