---
name: playbook-abdulfattah-1
description: Operator playbook (edition 1) for Abdulfattah — how to run the NQ box+indicator dashboard
  end to end: launch, import a winning strategy, pick a timeframe, read every panel and log line
  (incl. NOENTRY + warm-up), export CSVs, save profiles, and read results honestly. Hands-on; the
  deep theory lives in the linked docs.
type: playbook
status: current
audience: Abdulfattah
edition: 1
workstream: WS-I
---

# Operator Playbook — Abdulfattah · Edition 1

A practical, do-this-then-that guide to running the strategy dashboard. No theory dumps — just how
to drive it and how to read what it tells you. Deeper "why" is linked at the end.

---

## 0. The 60-second mental model

- The **box** decides the *direction* (long/short) on each candle of your chosen **timeframe**.
- Two gates can **block** a trade: a **volatility gate** (skip wild bars) and up to **15 indicators**
  acting as **confirm / veto** judges (entry allowed only if *no veto* AND *at least K confirms*).
- A **drawdown breaker** can halt trading after losses.
- Exits (stop-loss / take-profit) are always resolved on **1-minute** candles.
- With all indicators **off**, it's just the plain box strategy (the "Winner").

That's it. Everything below is how to operate this on the screen.

---

## 1. Start the dashboard

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
python3 server.py --port 8200
```

Open **http://localhost:8200/** in a browser. If you change a setting and the page seems stale,
hard-refresh (Ctrl-Shift-R). If the backend isn't running you'll see a red banner pinned at the top
telling you so.

---

## 2. Load a winning strategy (one click)

Top-left of the settings panel:

1. **Strategy** dropdown → pick one. Options are:
   - **★ Winner — plain box (4h)** — the original box strategy, all indicators off.
   - **WS-I 4h champion … / 2h / 1h / 15m / 5m / 2m / 1m** — the best combo found per timeframe
     (box knobs + tuned indicators + K), labelled with its typical profit.
2. Selecting one **fills every field automatically** (timeframe, SL/TP/gate/breaker, K, and the whole
   indicator panel with each indicator's tuned numbers) **and runs the backtest immediately.**

That's the fastest way to see a known-good setup. To tweak from there, just edit fields and press
**Run Backtest**.

---

## 3. Pick the timeframe & window

- **Timeframe** (Data group): the decision candle — `4h, 2h, 1h, 15m, 5m, 2m, 1m`. Coarser (4h) is
  patient and fast to compute; finer (1m, 2m) is twitchy and **slow to run** (can take minutes).
- **Window**: `full` (2025+2026), `2025`, or `2026` only.

⚠️ **Read this before trusting a window:** `2025`/`2026` are **not clean slices** of `full`. When you
run a single year, the indicators start "cold" (no prior history) and behave differently for their
whole warm-up period. The **`full` run is the trustworthy one**; treat single-year runs as rough.
(See the case study link at the bottom — this exact thing once made 2026 look far riskier than it was.)

---

## 4. Run it & read the top numbers

Press **Run Backtest**. The summary cards show: **P/L, max drawdown, # trades, exposure, win-rate,
profit-factor**, etc.

Two profit ideas you'll see in the reports:
- **Total profit** = one continuous run over the whole period (the headline).
- **Typical profit** = the *median* of several equal time-slices (a consistency check). They are
  **not** multiples of each other — see the linked explainer.

---

## 5. Read the charts

Top to bottom: **price + entry/exit markers + SL/TP lines**, **predicted volatility** (orange line =
gate threshold; bars above it are skipped), **engine state** (1 = trading, 0 = halted by breaker),
**equity curve**, **drawdown (underwater)**. A long flat stretch in equity usually means *no trades
were taken* there (gate/veto/warm-up/breaker), **not** a position being held.

---

## 6. Read the Event Log (this is where the "why" lives)

Each line is time-stamped and colour-coded:

| Tag | Meaning |
|---|---|
| **ENTRY** (blue) | a trade opened — shows direction, price, SL/TP, and `K: x confirm / y veto` |
| **WIN / LOSS** | the trade's exit, reason, P/L, running equity & drawdown |
| **LOCK / UNLOCK / SKIP** | drawdown breaker tripped / released / skipped a trade while halted |
| **NOENTRY** (amber) | a box signal that was **dropped** — `vetoed by <indicators>` or `skipped by volatility gate`. (These are *not* trades; they're shown so nothing is silently hidden.) |
| **WARMING UP / WARMED** (grey/green) | an indicator is still in its warm-up and **not voting yet**, naming what it's waiting for and when it becomes eligible |

**Why an indicator says "WARMING UP":** every indicator needs a look-back of candles before it's
trustworthy (e.g. an EMA(373) needs ~373 candles; a composite like Keltner waits for its EMA *and*
ATR). Until then it stays neutral and logs that it's waiting. If a window is shorter than the
warm-up, you'll see "**NEVER warms up here**" — meaning that indicator is effectively off for that run.

---

## 7. Read the Trade Ledger

A table of every executed trade: entry/exit time, direction, prices, SL/TP lines, exit reason, P/L,
running equity, drawdown, year. This is the audit trail for the summary numbers.

---

## 8. Export the data

- **⬇ CSV** button on the **Event log** → `event_log_<tf>.csv` (every event incl. NOENTRY/warm-up).
- **⬇ CSV** button on the **Trade ledger** → `trade_ledger_<tf>.csv` (every executed trade).
- Both export the **last run shown**, filename tagged with the timeframe.

---

## 9. Save your own setups

- **💾 Save current profile** (top of settings) → name it → it's stored in *this browser* and appears
  under **"My saved profiles"** in the Strategy dropdown, re-loadable like the built-in ones.
- **↺ Reset to winning preset** → back to the plain box Winner.

---

## 10. Honest cautions (please internalise)

1. **n = 1 history.** Everything is one slice of 2025→2026. These are *candidates*, not proof.
2. **Fine timeframes (1m/2m) are weak and slow** — sanity-check trade counts/exposure before trusting.
3. **Single-year windows cold-start the indicators** — use `full` for the real read (§3).
4. **A big total with a weak typical = probably one lucky stretch.** Check the per-slice spread.
5. **Nothing is silently clamped.** A bad/missing field shows a red error banner at the top — fix it.

---

## Where the deeper "why" lives

- `docs/PLAYBOOK.md` — the full technical reference (every knob, the entry decision, guarantees).
- `optimize/reports/WS-I_RESULTS.md` + `WS-I_RESULTS_SIMPLE.md` — the winning combos per timeframe.
- `docs/TYPICAL_VS_TOTAL_PROFIT.md` — total vs typical profit, explained.
- `docs/WS-I_WHAT_WAS_TESTED.md` — what the optimizer actually searched.
- `WSI-Case_Study/CASE_STUDY_2026_maxDD.md` — the cold-start / warm-up case study (§3 above).

_Edition 1. Ask for edition 2 when you want the optimisation/“how the champions were found” workflow added._
