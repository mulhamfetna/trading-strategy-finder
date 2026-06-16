# NQ Lean 3-Indicator Backtester (4h)

The 4-hour "box + 1-minute-indicator" champion, stripped to its **three** highest-value indicators
(**CCI · Order Block · Structure Trend**). Same engine, same box, same risk knobs as the 8-indicator
champion — five indicators removed. On the full research period it earns **$149,989 (+5.5%)** while needing
**60% less warm-up data** (138-candle footprint vs 346).

> Net P/L **$149,989** · max DD **$15,491 (10.3%)** · 255 trades · 67.8% win · PF 1.56 — NQ, $20/pt, 1 contract.
> Reproduced byte-for-byte by `backtest.py`. **Full-period ablation result — not yet fold/OOS-validated.**

## Run it

```bash
pip install -r requirements.txt          # numpy, pandas

python3 backtest.py \
  --decision  NQ_4h.csv \                # 4h candles:  Date,Open,High,Low,Close
  --minute    NQ_1m.csv \                # 1-min candles (exits + indicator votes)
  --box       NQ_full_data.csv \         # per-day box levels (weekly/monthly columns)
  --champion  champions/lean_4h.json \   # the lean 3-indicator strategy
  --out       trades_lean_4h.csv
```

Prints the summary and writes a per-trade CSV. `--insample-year` (default 2025) sets the year whose bars seed
the volatility-gate percentile.

**Full strategy write-up: [`PLAYBOOK.md`](PLAYBOOK.md)** — the idea, the exact decision pipeline, every tuned
parameter, the measured performance, how it was found, and the honest caveats (read §9 before trading).

This bundle ships the **exact parity-locked research engine**, so its numbers match the canonical system.
