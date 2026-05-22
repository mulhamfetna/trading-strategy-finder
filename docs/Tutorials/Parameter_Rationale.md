# Parameter Rationale — Ultimate Dashboard

This note explains **what each important value does**, **why it was chosen**, and **how to explain it in an interview**.

## 1. Data window and split

| Parameter | Value | Why it was chosen | If changed |
|---|---:|---|---|
| Input data | `1min.csv` | Gives the highest-detail raw history for scalping experiments. | Using lower-frequency input reduces flexibility and may hide intraday structure. |
| Resample timeframe | `15min` | Reduces noise while keeping enough trade opportunities for a scalping-style system. | Smaller timeframes create more noise; larger timeframes reduce trade frequency. |
| Train/test split date | `2025-06-30` | Creates a time-based split and avoids lookahead leakage. | A random split would leak future market regime information. |
| Initial capital | `10000` | Simple demo capital for comparable reporting. | Results scale in equity terms, but per-contract P/L stays the same. |

## 2. Indicator values

| Parameter | Value | Why it was chosen | Interview explanation |
|---|---:|---|---|
| RSI period | `5` | Very short momentum window for a fast scalping signal. | “I wanted a sensitive oscillator that reacts quickly to short-term exhaustion.” |
| EMA fast | `5` | Captures the immediate trend on 15-min candles. | “It is fast enough to reflect local direction without being pure noise.” |
| EMA slow | `15` | Gives a broader trend anchor on the same timeframe. | “This gives the model a simple fast-vs-slow trend filter.” |
| Volume spike threshold | `1.0x` | Permissive liquidity confirmation: volume must exceed the recent baseline. | “I used a relative volume test rather than an absolute one so the rule adapts across sessions.” |

## 3. Entry thresholds

| Parameter | Value | Why it was chosen | Tradeoff |
|---|---:|---|---|
| RSI oversold | `25` | More conservative than 30, so entries require stronger exhaustion. | Fewer signals, but higher conviction. |
| RSI overbought | `75` | Symmetric short-side confirmation. | Avoids one-sided logic and keeps short entries consistent with long entries. |

Important point:
- The code originally had an asymmetric RSI filter bug; the current version intentionally uses **symmetric long/short filtering**.
- In the interview, say: “I enforced the same logic on both sides so the system treats long and short opportunities consistently.”

## 4. Backtest economics

| Parameter | Value | Why it was chosen | Interview explanation |
|---|---:|---|---|
| Stop loss | `0.6%` | Tight risk control suitable for a scalping-style system. | “I kept the stop tight because the system aims to capture short moves, not hold large adverse swings.” |
| Take profit | `2.4%` | 4:1 reward/risk relative to the stop. | “This forces the strategy to justify each trade with a strong upside target.” |
| Fee per trade | `$10` | Simple fixed-cost model for report clarity. | “It makes the net P/L more realistic than gross-only reporting.” |
| Point value | `2.0` | NQ E-mini futures are worth $2 per point. | “This is the key correction: futures P/L must be measured per contract, not as percent of capital.” |

Important point:
- The dashboard backtest uses **points moved × point value - fees**.
- That is the correct economic model for futures-style trading and is more meaningful than percentage-of-capital P/L.

## 5. ML settings

| Parameter | Value | Why it was chosen | Interview explanation |
|---|---:|---|---|
| Model | RandomForestClassifier | Handles nonlinear interactions and gives a quick, robust baseline. | “I chose a model that is easy to train, hard to break, and simple to justify.” |
| n_estimators | `100` | Enough trees for stability without making training slow. | “This is a standard stable baseline for a small classification problem.” |
| max_depth | `10` | Limits overfitting on a relatively small historical sample. | “I capped depth to prevent the model from memorizing the training set.” |
| random_state | `42` | Reproducibility. | “Same input should produce the same model behavior when I rerun the project.” |
| Minimum training rows | `50` | Avoids training a model on too little data. | “I wanted a guardrail so the model is not built on an unreliable sample.” |

Important point:
- The ML filter is **not** the main signal generator.
- It is a **secondary filter** that removes weak rule-based entries.

## 6. How to explain the choices in one sentence

- RSI 5: fast exhaustion detection.
- EMA 5/15: short-term trend confirmation.
- Volume threshold 1.0x: liquidity confirmation without being too strict.
- RSI 25/75: strong oversold/overbought entry discipline.
- Stop 0.6% / take 2.4%: tight risk with a 4:1 payoff target.
- Point value 2.0: correct futures economics for NQ.
- RandomForest 100 trees, depth 10: stable baseline without overfitting.

## 7. Useful interview phrasing

- “I used short windows because the goal was scalping, not swing trading.”
- “I chose values that are conservative enough to avoid noise, but still produce enough trades for evaluation.”
- “The parameters are not magic numbers; they are a balance between sensitivity, robustness, and interpretable behavior.”
- “The biggest conceptual correction was using contract P/L instead of percent P/L for NQ.”

