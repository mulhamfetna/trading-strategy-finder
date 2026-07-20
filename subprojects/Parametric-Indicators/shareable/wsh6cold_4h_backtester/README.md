# NQ wsh6cold Backtester (4h · cap_1min=448)

The 4-hour **"box + 1-minute-indicator"** strategy `wsh6cold_4h` — a cold-start optimizer discovery
that pairs a **7-indicator** confirm/veto committee (EMA-trend · MACD · OBV · CCI · Bollinger · ADX ·
CISD) with a **448-bar max-hold time cap** (`cap_1min=448` ≈ ~1.5 trading sessions). The time cap is the
core of its edge: it bleeds losers out before they mature into deep drawdowns, holding **max DD to
$9,589** while the same strategy uncapped sinks to ~$18.8k DD.

> Net P/L **$153,321** · max DD **$9,589 (6.3%)** · 211 trades · 58.3% win · PF **1.99** · payoff 1.43
> — NQ, $20/pt, 1 contract. **Out-of-sample 2026: +$60,488** (DD $8,280 · 60.6% win · PF 2.02).
> Reproduced byte-for-byte by `backtest.py` ($153,321 / $9,589). Triple-confirmed (see PLAYBOOK §7).

## Run it

```bash
pip install -r requirements.txt          # numpy, pandas

python3 backtest.py \
  --decision  NQ_4h.csv \                # 4h candles:  Date,Open,High,Low,Close
  --minute    NQ_1m.csv \                # 1-min candles (exits + indicator votes + time cap)
  --box       NQ_full_data.csv \         # per-day box levels (weekly/monthly columns)
  --champion  champions/4h.json \        # the wsh6cold_4h strategy
  --out       trades_4h.csv
```

Prints the summary and writes a per-trade CSV. `--insample-year` (default 2025) sets the year whose bars
seed the volatility-gate percentile.

**Full strategy write-up: [`PLAYBOOK.md`](PLAYBOOK.md)** — the idea, the exact decision pipeline, every
tuned parameter, the 7 indicators, the exit precedence (incl. the 448-bar cap), the measured in-sample +
out-of-sample performance, how it was found, and the honest caveats (read §8 before trading).

This bundle ships the **exact parity-locked research engine** (refreshed to the time-cap-aware version),
so its numbers match the canonical system.
