# The Winning Strategy — Playbook
### NQ "Box + 1-Minute-Indicator" system · 4h champion (1-min-trained, wsh4)

A complete, shareable description of the strategy that won the WS-I 1-minute-indicator search: what it
trades, why, the exact decision pipeline, the tuned parameters, the measured performance, and how to run
the bundled backtester to reproduce it. No insider context required.

> **Headline (4-hour champion, full research period):**
> **net P/L ≈ $142,200 · max drawdown ≈ $14,080 (9.9% of P/L) · 214 trades · ~69% win · profit factor 1.67.**
> Reproduced byte-for-byte by the bundled `backtest.py` ($142,203). Instrument: **NQ** (E-mini Nasdaq-100
> futures), $20 per index point. Single contract. **One historical period (n=1) — read §9 caveats.**

---

## 1. The idea in one paragraph

Each trading day the market defines a **"box"** — reference support/resistance levels derived from prior
weekly/monthly structure. When price interacts with the box it implies a **direction** (long or short).
That raw directional signal is then **filtered** three ways before it becomes a trade: a **volatility
gate** (only trade when expected volatility is in a favourable regime), a committee of **technical
indicators** voting **confirm/veto** under a **K-of-N rule**, and a portfolio-level **drawdown circuit
breaker** that halts trading after a losing streak. Entries are taken on the decision timeframe (4 hours
for the champion); **exits are resolved on the 1-minute frame** with a dual soft/hard stop-loss and a
take-profit. Critically, the **indicators are computed on the 1-minute frame** (sampled causally at each
decision bar) — that "1-min-trained" regime is what distinguishes this champion and gave the strongest
result.

---

## 2. Vocabulary (plain)

| Term | Meaning |
|------|---------|
| **Decision frame** | The timeframe whose bars trigger trade decisions. Champion = **4h**. |
| **1-minute frame** | The fine frame used to (a) **resolve exits** intrabar and (b) **compute indicator votes**. |
| **Box** | Per-day support/resistance levels (from weekly/monthly structure). The directional trigger. |
| **Volatility gate** | A HAR-RV forecast of volatility; trade only when it's ≤ a percentile threshold. |
| **K-of-N confirm rule** | Of the N enabled confirm-capable indicators, at least **K** must agree with the box direction to enter. |
| **Veto** | An indicator can also block an otherwise-valid entry. |
| **Drawdown breaker** | After equity falls `dd_limit` from its peak, halt for `cooldown` trades. |
| **Soft / hard SL** | Two stop levels: soft (closer, exit on bar close beyond it) and hard (farther, hard stop). |
| **Flip** | Optionally trade the opposite of the box direction (champion: off). |

---

## 3. The decision pipeline (exactly, in order)

For every decision bar (4h):

1. **Box trigger.** From the day's box levels, derive a directional signal `long` / `short` / `none`.
   (No box interaction → no candidate, skip.)

2. **Volatility gate.** A **HAR-RV** model (heterogeneous auto-regression of realized volatility, built
   from 1-minute returns) forecasts the bar's volatility `vf`. Compute a threshold = the **`gate_pct`-th
   percentile** of in-sample volatility. **Trade only if `vf ≤ threshold`** (calm-enough regime). Bars
   above threshold are logged as `NOENTRY (vol gate)` and never traded.

3. **Indicator committee (K-of-N confirm + veto).** Each enabled indicator computes a vote on the
   **1-minute frame**, sampled at the decision bar's **last closed 1-minute candle** (strictly causal —
   no look-ahead). Votes are `+1 confirm` / `-1 veto` / `0 neutral`:
   - **Confirm:** the entry is allowed only if **at least `K`** of the enabled confirm-capable indicators
     agree with the box direction.
   - **Veto:** any indicator in veto mode that disagrees can **block** the entry (logged `NOENTRY (veto)`).
   - Warm-up: each indicator stays neutral until it has enough 1-minute history.

4. **Entry.** If the box gives a direction, the gate passes, and the K-rule is satisfied with no veto,
   **enter at the decision bar** in the box direction (or its opposite if `flip` is on — champion: off).

5. **Exit (resolved on the 1-minute frame).** From entry, three exit lines are active:
   - **Take-profit (`tp`)** — exit at +`tp` points.
   - **Soft stop (`sl_soft`)** — the nearer stop; exit at the bar close once breached.
   - **Hard stop (`sl_hard`)** — the farther, absolute stop.
   The 1-minute candles after entry are scanned in order; the **first** line touched determines the exit
   (price, time, reason). This dual-stop design lets the trade survive a wick to the soft line while the
   hard line caps the worst case.

6. **Drawdown circuit breaker (portfolio level).** Track running equity and its peak. When the
   **drawdown ≥ `dd_limit`**, **lock** trading for `cooldown` subsequent candidate trades (logged `SKIP`),
   then unlock — keeping the global high-water mark. This caps losing-streak bleed. (Champion: very large
   `dd_limit` ≈ $4,747 and `cooldown` 0 → the breaker rarely binds at 1-contract size, but it is part of
   the system and matters at scale / on rougher data.)

7. **Cooldown between trades** prevents same-bar re-entry; one position at a time, single contract.

---

## 4. The champion parameters (4h, 1-min-trained)

**Box / risk knobs** (points are NQ index points; $20 each):

| Param | Value | Meaning |
|-------|------:|---------|
| `sl_soft` | 149.8 | soft stop distance (points) |
| `sl_hard` | 167.1 | hard stop distance (points) |
| `tp` | 120.2 | take-profit distance (points) |
| `gate_pct` | 86.9 | volatility-gate percentile (trade when vf ≤ 86.9th pct) |
| `dd_limit` | 4747 | breaker trips at $4,747 drawdown |
| `cooldown` | 0 | trades halted after a trip |
| `flip` | false | trade the box direction (not reversed) |
| `K` | 1 | at least 1 confirm-capable indicator must agree |

**Indicator committee (8 enabled), tuned on the 1-minute frame:**

| Indicator | Tuned params | Role |
|-----------|--------------|------|
| **SMA trend** | fast 346 / slow 339 | trend filter (fast vs slow SMA) |
| **Bollinger** | n 45, k 4.3 | volatility-band mean-reversion/breakout |
| **Keltner** | n 40, m 5.0 | ATR-band channel |
| **CCI** | n 138, threshold 35 | momentum/extreme |
| **MFI** | n 39, lower 26, upper 87 | money-flow over/under |
| **OBV** | slope 18 | on-balance-volume trend |
| **Order block** (SMC) | swing_l 10 | smart-money supply/demand zone |
| **Structure trend** (SMC) | swing_l 6 | market-structure (HH/HL vs LH/LL) bias |

(Every other indicator in the library is **off** for this champion. The exact, machine-readable spec is
`champions/4h.json`.)

---

## 5. Measured performance (full research period, single contract)

| Metric | 4h champion |
|--------|------------:|
| Net P/L | **$142,203** |
| Max drawdown | $14,082 (**9.9%** of P/L) |
| Trades taken | 214 (100% of candidates) |
| Win rate | 69.2% |
| Profit factor | 1.67 |
| Avg win / avg loss | +$2,404 / −$3,236 |
| Breaker locks | 57 |
| Longest no-entry streak | 35 signals / 14.2 days (from 2025-04-02) |

The standout property is the **drawdown efficiency**: ~$142k of P/L against a ~$14k worst peak-to-trough,
i.e. drawdown ≈ **10%** of total profit, with a ~69% hit rate.

---

## 6. The other timeframe champions (same system, different decision frame)

All six are bundled (`champions/<tf>.json`) and run identically — just point `--decision` at the matching
timeframe's candles.

| TF | full P/L | DD (% of P/L) | win% | K | #ind |
|----|---------:|---------------|-----:|:-:|:----:|
| **4h** 🏆 | $142,203 | 9.9% | 69% | 1 | 8 |
| 1h | ~$96,000 | ~17.6% | 52% | 4 | 8 |
| 2h | ~$92,000 | ~17.7% | 51% | 3 | 8 |
| 15m | ~$77,000 | ~10.5% | 51% | 3 | 8 |
| 2m | ~$29,700 | ~11.0% | 64% | 1 | 7 |
| 5m | ~$24,000 | ~19.3% | 63% | 1 | 7 |

(P/L figures are the research full-period numbers; the bundled backtester reproduces them on the same
data — verified to 0.4% for 5m and 0.02% for 4h.)

---

## 7. How it was found

A multi-objective **NSGA-III** evolutionary search (Optuna) explored the full space — box risk knobs,
which indicators to enable, each indicator's internals, and K — across **~5,000+ trials per timeframe**,
scored by **5-fold walk-forward** validation. Three objectives were maximised simultaneously: **median
fold P/L**, **−worst-fold drawdown**, and **median win-rate**, under a hard feasibility constraint
(**full-period drawdown ≤ 25% of P/L**). The champion is the top of the feasible Pareto front by median
fold P/L. Indicators were evaluated on the **1-minute frame** (`--ind-1min`), which materially beat the
decision-frame-indicator regime.

---

## 8. Reproduce it — run the bundled backtester

```bash
pip install -r requirements.txt          # numpy, pandas

python3 backtest.py \
  --decision  NQ_4h.csv \                # decision-frame candles: Date,Open,High,Low,Close
  --minute    NQ_1m.csv \                # 1-minute candles:        Date,Open,High,Low,Close
  --box       NQ_full_data.csv \         # per-day box levels (weekly/monthly level columns)
  --champion  champions/4h.json \        # the tuned strategy
  --out       trades_4h.csv
```

It prints the summary (P/L, DD, win, PF, …) and writes a per-trade CSV. For another timeframe, swap
`--decision` to that timeframe's candles and `--champion champions/<tf>.json`. `--insample-year` (default
2025) sets which year's bars seed the volatility-gate percentile — set it to your data's first/in-sample
year. **This bundle ships the exact parity-locked research engine**, so its numbers match the canonical
system (not an approximation).

---

## 9. Honest caveats — read before trading

- **n = 1.** These are *in-sample-optimised* parameters on **one** historical period. Strong backtest
  numbers from a large evolutionary search **overstate** live expectancy. Treat as a research result, not
  a deployment-ready edge. Validate out-of-sample / forward before risking capital.
- **Single contract, no costs modelled.** P/L is gross of commissions, slippage, and financing. The
  $20/point multiplier and fills are idealised (exit at the touched line on 1-minute data).
- **Drawdown is path-dependent.** $14k worst-case here; at multiple contracts it scales linearly.
- **Indicator regime matters.** These were tuned with indicators on the **1-minute** frame; running them
  with decision-frame indicators will NOT reproduce the result.
- **Box construction is part of the edge.** The per-day box levels (the `--box` file) encode prior
  weekly/monthly structure; results depend on that exact construction.
- **Survivorship/selection bias.** The champion is the *winner* of thousands of trials — the very act of
  picking the best inflates apparent performance.

---

## 10. Files in this bundle

```
backtest.py            standalone CLI runner (calls the real engine)
champions/<tf>.json    tuned strategy presets (4h,2h,1h,15m,5m,2m) — full machine-readable spec
strategy.py engine.py box_lookup.py loader.py volatility.py config.py   the parity-locked engine
indicators/            the indicator library (classic + SMC) + the 1-minute voting layer
optimize/              timeframes + the box-signal/fast-exit helpers the engine needs
requirements.txt       numpy, pandas
README.md              quick start
PLAYBOOK.md            this document
```
