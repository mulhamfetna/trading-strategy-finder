# Multi-Timeframe Layer-Fusion Backtester (primary tf + secondary tf, one instrument)

Trade two timeframes of one instrument at once — a **primary** (priority) layer + a **secondary** that fills
the primary's idle windows, each with its own profile, on one shared 1-contract account. Self-contained: it
bundles the **exact parity-locked research engine** (`optimize/l2/` + the fusion core `optimize/l2/mtf.py`)
and reproduces the canonical numbers **byte-for-byte** — not a re-implementation.

| Instrument | Primary | Secondary | **Combined** | Trades |
|---|---|---|--:|--:|
| **ES** ($50/pt) | 1h | 4h | **$71,800** | 264 |
| **NQ** ($20/pt) | 1h | 4h | **$173,789** | 481 |

See **`PLAYBOOK.md`** for how the fusion works (primary-priority + force-close), why combined ≠ the sum of the
two layers, and the validity caveats.

## Run it

```bash
pip install -r requirements.txt          # numpy, pandas

# The bundle ships CODE + CHAMPIONS, not the multi-year CSVs. Point the loader at your data tree:
export WSH_DATA_BASE=/path/to/trading            # NQ: <RAW_DIR>/NQ_<tf>.csv + NQ_1m.csv;
                                                 # ES: subprojects/all-stocks-signals/instruments.py + ALL_STOCKS data
export WSG_DATA_ROOT=/path/to/trading/data       # NQ box levels: full_data/NQ_full_data.csv
# (defaults target the original research layout under /mnt/data/projects/trading)

python3 backtest_mtf.py                           # ES 1h+4h  → COMBINED $71,800 (264 trades)
python3 backtest_mtf.py --instrument NQ           # NQ 1h+4h  → COMBINED $173,789 (481 trades)
python3 backtest_mtf.py --instrument ES --primary-tf 1h --secondary-tf 4h --out-prefix run
```

Each run prints the PRIMARY / SECONDARY / COMBINED summary and writes the full per-candle log (the single
source of truth, master grid = the finer timeframe) to `<prefix>_mtf_log.csv`.

## Options

| flag | default | meaning |
|---|---|---|
| `--instrument` | `ES` | `ES` or `NQ` (same engine, different candles/boxes/economics) |
| `--primary-tf` | `1h` | primary (priority) timeframe — **must be finer-or-equal** to the secondary |
| `--secondary-tf` | `4h` | secondary (gap-fill) timeframe |
| `--out-prefix` | `mtf` | output CSV prefix |

## What's bundled

- `backtest_mtf.py` — the entry point.
- `optimize/l2/mtf.py` — the fusion core (`run_dual_tf`: primary-priority merge + force-close on the master grid).
- `optimize/l2/{logbook,engine,l1_runner,payload,aggregate,...}.py` — the parity-locked causal engine.
- `optimize/{fast_engine,signals,trading_days,instruments,data}.py`, `indicators/`, `box_lookup.py`,
  `volatility.py`, `presets.py`, `config.py` — the vendored strategy stack.
- `optimize/results/wsh4_champions_full{,_ES}.json`, `champions/` — the per-timeframe champions.

## Requirements

Python 3, `numpy`, `pandas` (`pip install -r requirements.txt`). No network, no GPU.
