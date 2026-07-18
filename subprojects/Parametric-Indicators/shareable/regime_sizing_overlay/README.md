# Regime Sizing Overlay — NQ volatility size-ramp (EXPERIMENTAL CANDIDATE)

A **self-contained, reproduce-to-the-dollar** bundle for the one surviving result of the volatility/regime
research arc. Unlike the champion bundles, this is **not an entry strategy** — it is a **sizing overlay** that
sits on top of an existing trade book: it changes *how big* each trade is, never *whether* it is taken.

> ⚠️ **EXPERIMENTAL CANDIDATE — not a confirmed edge.** The *signal* is validated (it beats 96% of random
> regime→size maps, helps 4/5 purged folds and all 3 years), but the **dollar magnitude is unconfirmed** on our
> single 2024–26 book: a block-bootstrap of the uplift gives a 90% CI of **[−$21k, +$61k]**, which includes
> zero. **Off by default. Do not change deployed defaults on it.**

## The headline

| | Profit | max Drawdown | Return/DD |
|---|--:|--:|--:|
| flat book (baseline) | $151,872 | $27,508 | 5.52 |
| **+ regime size-ramp** *(at EQUAL risk)* | **$162,228** | **$27,508** (held) | **5.90** |
| **Δ** | **+$10,356 (+6.8%)** | — | +0.38 |

"Equal risk" means the ramped book is scaled so its **max-drawdown equals the flat book's** — so this is more
profit for *identical* risk, not more profit for more risk.

## The idea in one line
Our box strategy is **vol-seeking** — it earns its best risk-adjusted return in the *most turbulent* market
regime and loses only in the calmest. So **size WITH volatility** (bigger when turbulent, smaller when calm).
The textbook move — *inverse*-volatility targeting — does the opposite and **hurts** (Return/DD 4.06 vs 5.52).

## Run it

```bash
pip install -r requirements.txt        # numpy, pandas (verify.py needs neither — stdlib only)

python3 verify.py                      # reproduce every documented number to the dollar (9/9 PASS)

# apply the overlay to your own trade book
python3 apply_regime_sizing.py <book.csv> regime/nq_daily_regime.csv            # OFF -> unchanged
python3 apply_regime_sizing.py <book.csv> regime/nq_daily_regime.csv --enable   # ON  -> ramped, equal-risk
```

`verify.py` is the guarantee: it recomputes the overlay from the bundled fixture and **fails loudly** if any
figure drifts by more than a dollar.

## What's in the bundle

| Path | What |
|---|---|
| `verify.py` | reproduces every documented number to the dollar (stdlib only) |
| `apply_regime_sizing.py` | the overlay itself — `--enable` (default OFF ⇒ book returned unchanged) |
| `configs/NQ_regime_sizing.json` | the config + `expected` numbers + the full `validation` record |
| `regime/nq_daily_regime.csv` | the **static causal regime artifact** (4,977 days, 4 regimes) |
| `reference/nq_2426_fusion_entries.csv` | the validated 539-trade reference book (datetime, pnl, layer) |
| `MANIFEST.json` | one-line summary in the same shape as the champion manifests |

## The rule (exactly what it does)

1. For each trade, look up the **day's regime** in the static artifact (0 = calmest … 3 = most turbulent).
2. Multiply that trade's P/L by a **linear ramp**: calmest **0.5×** → most turbulent **1.5×**.
3. **Normalize** the whole book by `flat_maxDD / ramped_maxDD` so max-drawdown lands back on the flat book's.

The regime artifact is produced by a **Gaussian HMM (4 states)** on *daily* NQ features — log-return, log
intraday realized-volatility, 20-day volume z-score — with parameters fit on **pre-2024 data only**, and each
day's state taken as the **filtered** (causal forward-algorithm) argmax. States are ranked by realized-vol
emission mean. Nothing in the pipeline sees the future.

## Data you provide (to run on your own book)

| File | Columns |
|---|---|
| `<book>.csv` | `datetime,pnl` (one row per entry; `decision`/`position_owner` optional) |

`datetime` may be `YYYY-MM-DD HH:MM:SS` **or** a Unix epoch integer — both are handled.

## ⚠️ When NOT to use this

- **Not on other instruments.** The regime artifact is **NQ-derived**. Re-derive it per instrument.
- **Not per-layer.** Validated on the **combined 1h+4h fusion** book. It helps the L2 (4h) layer
  independently, but **hurts L1 (1h) standalone** — L1's best regime is *mid*, not the most turbulent.
- **Not as a confirmed edge.** The magnitude is inside the noise on one year of trades. Treat the number as a
  *direction*, not a promise.
- **Not under a hard drawdown cap without the normalization.** Un-normalized, the ramp raises absolute
  drawdown ($27.5k → $31.0k). The equal-risk scaling is what keeps risk constant.

## What would upgrade it to "confirmed"
A **longer, bear-inclusive trade book** — which needs the 2010–2023 box levels we don't currently have. With
those, the bootstrap CI either tightens above zero (confirmed) or it doesn't (killed). Until then: candidate.

Full write-up: **`WINNER_PLAYBOOK.pdf`** (verbose report — every validation and integration test, with the
live dashboard run).
