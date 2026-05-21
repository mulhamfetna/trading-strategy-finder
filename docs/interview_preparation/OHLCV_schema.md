OHLCV stands for Open, High, Low, Close, and Volume. It is the standard database schema used to store financial market data over specific time intervals (e.g., 1-minute, 1-hour, or 1-day bars). [1, 2, 3] 
## Core Database Schema
A standard SQL implementation for an OHLCV data table uses this structure:

CREATE TABLE market_data (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(12) NOT NULL,
    open_price NUMERIC(18, 4) NOT NULL,
    high_price NUMERIC(18, 4) NOT NULL,
    low_price NUMERIC(18, 4) NOT NULL,
    close_price NUMERIC(18, 4) NOT NULL,
    volume NUMERIC(18, 4) NOT NULL,
    PRIMARY KEY (timestamp, ticker)
);

## Data Field Breakdown

* Timestamp: The exact start time of the data interval.
* Ticker / Symbol: The asset identifier (e.g., AAPL, BTCUSD).
* Open: The price at the start of the interval.
* High: The highest price reached during the interval.
* Low: The lowest price reached during the interval.
* Close: The final price at the end of the interval.
* Volume: The total number of shares or coins traded. [4, 5, 6] 

## Optional Extended Fields
For advanced trading systems, developers often append these fields:

* Adjusted Close: Price adjusted for stock splits and dividends.
* Trades Count: Total number of unique executions during the window.
* VWAP: Volume-Weighted Average Price for institutional benchmarking.

------------------------------
If you are setting this up, let me know your database type (e.g., PostgreSQL, TimescaleDB, MongoDB) and your target timeframe (e.g., real-time streaming or historical daily data) so I can optimize the indexing strategy for you.

[1] [https://databento.com](https://databento.com/docs/schemas-and-data-formats/ohlcv)
[2] [https://blog.amberdata.io](https://blog.amberdata.io/ohlcv-data-accessing-historical-cryptocurrency-data-for-backtesting)
[3] [https://www.coinapi.io](https://www.coinapi.io/blog/how-to-read-crypto-candlestick-charts-using-ohlcv-data)
[4] [https://developer.mescius.com](https://developer.mescius.com/spreadjs/docs/features/data-charts/chart-types/ohlc-charts)
[5] [https://docs.bitquery.io](https://docs.bitquery.io/docs/trading/crypto-price-api/crypto-ohlc-candle-k-line-api/)
[6] [https://www.coinapi.io](https://www.coinapi.io/learn/glossary/ohlcv)
