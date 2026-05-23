# 📘 Core Strategy Playbook & Backtesting Guide

This document explains the exact rules our algorithm uses to enter, manage, and exit trades. For a new team member doing backtesting, this is your blueprint.

## 1. Entry Distribution & Position Sizing
We do not enter the market with our full position all at once. We scale into the trade across **3 different levels** to get a better average price. 

The total number of contracts depends on the account capital, but **for backtesting purposes, we assume a total size of 4 contracts**.

**The 1-1-2 Scaling Model:**
* **Entry 1 (Base Level):** Enter with **1 contract**.
* **Entry 2 (Pullback):** Enter with **1 contract** when the price goes against us by **100 points**.
* **Entry 3 (Deep Pullback):** Enter with **2 contracts** when the price goes against us by **150 points** (from the base level).

**The Average Price:**
Because we buy heavier at the bottom (2 contracts at the 150-point pullback), our overall **Average Entry Price** is pulled heavily in our favor. For backtesting and risk calculation, we calculate that **the Average Entry Price sits at 75 points away from the original Base Level.**

## 2. The "Big Candle" Exception (> 400)
There is one major exception to the scaling rule above: **Momentum/Volatility Breakouts.**
* If the size of the trigger candle is extremely large (**greater than 400 points**), it means the market has massive momentum.
* **The Rule:** We *do not* scale in. We enter **immediately with the full quantity (all 4 contracts) reversal if green bar we enter short and if reb bar we enter long** at the first level, because the market is unlikely to pull back to give us the 100 or 150-point entries.

## 3. The Entry Trigger (The 15-Second Confirmation)
We do not use limit orders that trigger the millisecond price touches a line. We require time-based confirmation on the **15-second chart** to avoid fake-outs.

* **For Entry 1 (Base Level):** The price must touch the entry level, and we must wait for **three (3) consecutive 15-second candles** to close at or beyond the level. Only then does the algorithm execute the trade.
* **For Entry 2 & Entry 3 (Scaling In):** Because price is moving fast against us, we only wait for **one (1) 15-second candle** to close at the level before executing these backup entries.

## 4. Stop Loss Management (The Dual SL System)
We use a two-tier Stop Loss system to balance between giving the trade room to breathe and protecting the account from crashes.

* **SL 1: The 2-Minute Stop Loss (The Soft Stop)**
  * This is our primary, closer Stop Loss. 
  * However, a simple "touch" does not trigger it. To exit the trade here, we require a **full 2-minute candle to CLOSE** beyond the Stop Loss line. If it only wicks past it and closes back inside, we stay in the trade.
* **SL 2: The 5-Second Stop Loss (The Hard Stop)**
  * This is placed further away and acts as our disaster prevention.
  * If the market is crashing violently, we do not wait for a 2-minute close. If a **5-second candle CLOSES** beyond this line, the system instantly cuts the entire trade.

## 5. Take Profit (TP) & Re-Entry Logic
To make backtesting simple, you can initially assume our Take Profit target is **+150 points** from the entry. However, the actual algorithmic logic is dynamic:

**The Algorithmic Exit Rule:**
1. Once the trade moves into profit by **+50 points**, the system starts watching the **2-minute chart**.
2. If a **2-minute candle closes** beyond that +50 point mark, the system automatically exits the trade to secure the profit.

**The Re-Entry Rule (Continuation):**
* After the system exits the trade for a profit (based on the 2-minute close rule above), the setup is not dead. 
* If the price **pulls back** (retraces) to our original entry zones, the algorithm will **re-enter the trade** with the same rules to catch the next wave of the trend.