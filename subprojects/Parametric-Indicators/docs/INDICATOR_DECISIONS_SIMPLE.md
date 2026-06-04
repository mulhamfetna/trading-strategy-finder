---
name: ws-i-indicator-decisions-simple
description: Plain-language "baby" version of INDICATOR_DECISIONS.md — the same WS-I.1 default choices explained simply, for a quick approve/adjust. The detailed/authoritative version stays in INDICATOR_DECISIONS.md.
type: decision-draft
status: awaiting-approval
created: 2026-06-04
workstream: WS-I
---

# WS-I.1 — Simple version (just approve or tweak)

Plain words. Full detail lives in **`INDICATOR_DECISIONS.md`** (this file just mirrors it simply).
**Big idea:** the box still picks the trade. The indicators are **judges** that either say
**"yes, take it" (confirm)**, **"no, skip it" (veto)**, or **"no opinion"**. If everything is turned
off, the system behaves exactly like today.

---

### How the judges vote
**1.** A trade is taken only if **no judge says no** AND **at least K judges say yes**. We start with
**K = 1** (one yes is enough); the optimizer can make it stricter later. 🟢
> for the backtesting stage one -> 1. for every indicator make sure that it exposes two settings a. the vlaue b. activated -> all defulated to disabled -> 2. the logs will still report all the opinions of all indicators plus a sin (0) as inactive (1) as active -> so i can still see this indictor opitnion but it can be enabled or disbaled -> 3. make k availbe to the dashboard to change its value with defualt state of k=1

**2.** Each indicator can be a "yes-only" judge, a "no-only" judge, or "both." We set sensible
starting jobs (trend tools say yes; volatility tools say no in bad conditions; etc.) and let the
optimizer change them. 🟡
> aproved

### When to actually enter
**3.** Optionally **wait for a small pullback** before entering, measured in "ATR units" (so it works
on any timeframe). Default = **don't wait** (enter immediately). 🟡\
> aproved ; the pillback parameter is not one united value for all indictros ; each indictor have its indepenedent pullback vlaue picker

**4.** Optionally **wait a few bars** before entering. Default = **0 bars**. If the wait isn't met
within **3 bars**, drop the trade (no stale entries). 🟢
> aproved; the waiting paramter is not one united value for all indictors ; each indictro have its own wait for bars value picker ; aprove `Optionally **wait a few bars** before entering. Default = **0 bars**.` delete ```If the wait isn't met
within **3 bars**, drop the trade (no stale entries)``` -> it is condsidered silent fall back;

**5.** If you use both waits, default is **wait for both** before entering. 🟢
> aproved -> make sure to log both values achived and who caused the dession 

### The "smart money" patterns (ICT/SMC)
**6.** **FVG (gap):** a 3-candle price gap. A recent unfilled gap in the trade's direction = a "yes." 🟡
> In trading, an FVG (Fair Value Gap) is a price action concept that highlights a market inefficiency. It appears as a void or untraded space on a candlestick chart when strong, impulsive momentum leaves an imbalance between buyers and sellers. [1, 2, 3, 4, 5]  
How an FVG Forms 
An FVG is identified by looking at a sequence of three consecutive candlesticks. It occurs when the body and wicks of the middle, large candlestick are not fully overlapped by the first and third candlesticks. [1, 2, 4]  
There are two types of FVGs: 
> • Bullish FVG: Forms during a strong upward move. The lowest point (wick) of the third candle is higher than the highest point (wick) of the first candle. This signals a heavy buy-side imbalance. 
> • Bearish FVG: Forms during a strong downward move. The highest point (wick) of the third candle is lower than the lowest point (wick) of the first candle. This signals a heavy sell-side imbalance. [4, 6]  
> How Traders Use FVGs 
Traders use FVGs to spot potential entry, exit, or reversal points. Because the market naturally seeks balanced price action, price often acts like a magnet and retraces (pulls back) to "fill" or "mitigate" this gap before continuing in the original direction. [2, 6, 7]  
A standard trading strategy involves: 
> 1. Identify the FVG: Spot the three-candle imbalance after a strong impulsive move. 
> 2. Wait for the Retracement: Do not chase the move. Wait for the price to naturally pull back to the edge of the FVG zone. 
> 3. Execute: Place a trade in the direction of the original impulsive move once the price enters the FVG zone, setting a stop-loss just past the first candle. [2, 4, 8, 9]  
> Key Things to Keep in Mind 
> • Timeframes: FVGs appear on all timeframes but are considered most reliable and significant when found on higher ones, such as 1-hour, 4-hour, and Daily charts. 
> • Not All FVGs Fill Immediately: The market can bypass FVGs entirely. It is critical to pair FVG zones with proper risk management (e.g., using stop-losses) and other tools like TradingView to confirm the broader market structure. [1, 2, 6, 14, 15]  


**7.** **"Burned into":** only counts when a candle **closes** past the level (a wick poking through
doesn't count) — matches your "all closes, not highs/lows." 🟢
> aproved

**8.** **Order block → breaker:** find the last opposite candle before a big move. Once price
**closes past** that block, it flips into a "breaker" and can only be used that way after — exactly
your rule. 🟡
> aproved

**9.** **Golf candle / CISD:** a candle bigger (body) than the last **3** candles. To trade a breaker
we default to needing **all three** confirmations (golf + gap + structure), like your note says —
can loosen later. 🟡
> not only three; the user can choose k number of cadles ; should be exposed to the dashboard ;

**10.** **Market structure (HH/HL/LH/LL):** found from closing prices, confirmed a couple bars later
so we never peek into the future. 🟢
> aproved

**11.** **Key levels:** start with just the **daily/weekly/monthly opens**. Rule: don't enter a trade
heading straight into one of these levels from the wrong side. The many other level columns stay
**off** until you tell me which matter. 🔴 *(most worth your eye)*
> needs explination further -> curruntly for the boxs cvs we have we are only considering weekly and monthly boxs and we are curruntly ignorin daily boxs -> for the new intredced boxs as indicatros they should not be generted on the fly while backtesting -> it should be generted using indepent generetor like the one generted the signals prevuisly and being extraxted as csv files then imported in the dasboard backend and front end (worth further invistgation if there is any paramters that rules the genertaion of those or they are united over all paramters)

**12.** **Trend:** default to reading trend from **structure** (the HH/HL pattern); can switch to
moving-average style later. 🟡
> both implemented in the engine indeopnelty as two subenignnis (to reduce complexy and nesty code by generteing two entities and choose the one using if statme by lookign at the user choice) and the swtich is using the dahboard option ; and defualt to moving avarge and can be swithced to strucutre 

### The optimizer
**13.** **Win-rate goal:** only counts if a period has **at least 10 trades**, so it can't cheat by
taking 2 lucky trades. 🟢
> aproved

**14.** **NSGA-III run size:** population 100, ~1500 tries per timeframe. The big all-timeframes run
still waits for your go. 🟢
aproved

### Standard settings
RSI 14 · MACD 12/26/9 · ATR 14 · ADX 14 · Bollinger 20/2 · Stochastic 14/3/3 · etc. — normal textbook
values, all tunable by the optimizer.
> all values tunable by the optimizer and exposed to the dashboard also and can be tuned by the user in the manuale backtest stage before the optimizer 
---

**To approve:** say "approved" — or just point at the numbered items you want changed (the 🔴/🟡 ones
are the ones I'd most like your eyes on, especially **#11 key levels**). Then I write the full
indicator spec and start building. No code until you say go.


> general note -> to reduce comlplixty and nested systems we are using the metality of build each possiblity alone then the user is choosing which engine to use ; insteade of stacking hundred of nested contitions and inersected probalities -> follow OOP structre mainly and switch to FF whcn it is more effective 
