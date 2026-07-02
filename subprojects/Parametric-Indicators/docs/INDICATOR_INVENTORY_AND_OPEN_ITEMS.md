# Indicator Inventory & Open Items — status report

> ⏸️ **PARKED — RETURN TO THIS AFTER THE KALMAN/FUSION STUDY IS CLOSED.**
> This report answers "what were the indicators, and how is each implemented," inventories the full WS-I
> indicator system against the user's original `indictors.md` brain-dump, and lists the **genuinely open
> decisions** that still need the user before further indicator work. It is a *resume pointer*, not a finished
> task. Flagged in `WORKSTREAMS.md` (progress watcher) and in auto-memory.
>
> **Origin:** the user asked "you mentioned a group of indicators you wanted me to provide — what were they and
> how will you implement each?" The exact prior request message predates the current session context and was not
> recoverable from the transcripts; this report reconstructs the substance from the source of truth
> (`/mnt/data/projects/trading/indictors.md`) cross-referenced with the implemented system (`docs/INDICATORS.md`,
> approved 2026-06-04).

---

## 0. TL;DR

The "group of indicators" is the user's **`indictors.md`** brain-dump. It was turned into the **WS-I indicator
system** and is **almost entirely already implemented** — approved 2026-06-04, documented in `docs/INDICATORS.md`,
parity-locked (all-off ⇒ byte-identical to the box+vol-gate strategy; `test_parity.py`/`test_fast_parity.py`). So
"how I plan to implement each" is, for most items, **past tense**. What remains is a short list of **open product
decisions** (§3) and **one unbuilt refactor** (global retrace/wait, §3.2).

---

## 1. What the user provided → how each is implemented

### 1.1 Group A — classical indicators
Computed on the decision/entry timeframe; each is a **judge** voting confirm / veto / neutral **relative to the box
direction**. All default OFF; a trade fires iff *(no active veto)* **and** *(≥ K active confirms)*, K default 1.

| Indicator | Status | Implementation (math + vote) — see `INDICATORS.md` §§3–16 |
|---|---|---|
| **SMA / EMA** | ✅ | Price-vs-line + fast/slow stack; confirm in-direction, neutral when hugging the line |
| **RMA** (Wilder) | ✅ | EMA with `α = 1/n`; the smoothing engine inside RSI/ATR (rarely standalone) |
| **MACD** | ✅ | `EMA₁₂ − EMA₂₆`, signal `EMA₉`; crossover/acceleration = momentum confirm |
| **RSI** | ✅ | 0–100 gain/loss oscillator (RMA-smoothed); >50 bullish, extremes warn |
| **Stochastic** | ✅ | %K/%D of range position; overbought/oversold |
| **CCI** | ✅ | `(price − SMA)/(0.015·mean-dev)`; extremes flag stretch |
| **ADX / DMI** | ✅ | Trend-strength gate: veto if `ADX < thr` (chop); confirm if `ADX ≥ thr` **and** `+DI/−DI` agrees |
| **ATR** | ✅ | True-range RMA; **veto** outside a vol band; also the **unit for retrace** (`atr_mult`) and Keltner width |
| **Bollinger** | ✅ | `SMA ± k·σ`; veto entry into the far band (mean-revert), optional breakout confirm |
| **Keltner** | ✅ | `EMA ± k·ATR` (smoother envelope); trend-follow + squeeze detection with Bollinger |
| **OBV** | ✅ | Signed cumulative volume; divergence context |
| **VWAP** | ✅ | Volume-weighted average price; intraday confirm/veto |
| **MFI** | ✅ | Volume-weighted RSI; overbought/oversold *with* volume |

### 1.2 Group C — ICT / Smart-Money-Concepts (the discretionary "provide" set)
These encode trader knowledge that **cannot be derived from OHLC without the user's exact rules** — which is
precisely why they had to be *provided*. `indictors.md` supplied the definitions (close-based structure, burn
semantics, golf-candle threshold, the "all three" breaker stack). All detectors are **causal** (closed bars only);
external key levels come from the offline pipeline.

| User's term (from `indictors.md`) | Status | Implementation — see `INDICATORS.md` §§17–25 |
|---|---|---|
| **FVG** — "three candles, no trades between; polish/parish; price goes fast after" | ✅ | Bullish `low[t] > high[t-2]` → zone `[high[t-2], low[t]]` (mirror bearish). Confirm on **retrace into** an unmitigated same-dir gap; veto firing into an opposing one |
| **IFVG** — "went into the FVG and burnt into it → goes hard" | ✅ | An FVG whose far side is **closed** through flips polarity → continuation signal in the new direction (wicks don't count — closes only) |
| **Order block** — "lowest point then went crazy → HH/LL; all **closes** not high/low" | ✅ | Last opposite-**close** candle before a close-based structure break; zone = body (or wick). **State machine**: valid until price closes beyond → converts to breaker |
| **Breaker block** — "burned OB, same concept as IFVG; all three for confirmation" | ✅ | Produced by the OB state machine on close-through. **Confirmation stack** `breaker_confirm ∈ {golf_only, golf+fvg, all_three}`, **default `all_three`** (golf **+** FVG **+** structure break) |
| **CISD / golf candle** — "bigger candle than the previous N; controllable N" | ✅ | Golf candle = body `|close − open|` > **max body of prior `golf_n`** candles (`golf_n` tunable, default 3). CISD = golf closing beyond the prior range in the new direction |
| **LL / HL / HH / LH** — market structure | ✅ | Close-based swings, confirmed **L bars late** (no look-ahead, L default 2). HH/HL = uptrend, LH/LL = downtrend; drives BOS + OB detection |
| **Trend** | ✅ | Two switchable sub-engines: **MA-stack** (default) *or* **structure** (HH/HL vs LH/LL) — dashboard switch, no nested branches |
| **Key levels** — "weekly + monthly; daily ignored" | ✅ | Loaded from `NQ_full_data.csv` via `box_lookup.py`; veto entries firing **into** an opposing active level within `level_buffer` (default 0.5·ATR). Opens first; other columns available, off by default |
| **Gap** — "any time there is no trades" | ✅ | Session/zero-volume + calendar detection (NQ 17:00–18:00, weekends); optional veto across a large gap |

### 1.3 Entry timing — retrace + wait (`indictors.md` lines 1–3)
"How much price should I wait (retrace) / how much time (wait) / or both."

| Feature | Status | Implementation — `INDICATORS.md` §2 |
|---|---|---|
| **Retrace** | ✅ (per-indicator) | Limit-style pullback in `points` or `atr_mult` (default `atr_mult`, amount 0). Resolved on the 1-min series: each indicator's confirm goes live at **its own** level (long `close − r`, short `close + r`). Trade fills at the **K-th confirm's level**. `retrace=0` ⇒ immediate fill (parity) |
| **Wait (bars)** | ✅ (per-indicator) | Confirm withheld until `wait_bars` after the signal; armed signal valid until it fills **or the next box signal supersedes it** (logged `superseded, unfilled`) |
| **Global retrace + wait** | ⬜ **NOT built** | See §3.2 — `notes.md` asks to collapse the per-indicator controls into **one global retrace box + one global wait box** |

---

## 2. Parity & causality guarantees (already enforced)

- **No look-ahead:** every reading uses only closed bars up to the signal bar; swings/OBs confirmed `L` bars late.
- **Decision-TF in, 1-min exits:** indicators evaluate on the entry TF; exits still resolve on 1-minute (WS-H rule).
  Indicators never touch the exit path.
- **All-off ⇒ parity:** every indicator disabled + retrace/wait = 0 ⇒ collapses to today's vol-gate-only path.
- **No silent fallback:** invalid params raise `ParamError`; disabled indicators still log their opinion (`active=0`).

---

## 3. Open items — what still needs the user (the actual "return-to" work)

### 3.1 Product decisions (defaults chosen; confirm or change)
1. **Order-block / breaker entry timing.** `indictors.md`: *"immediately, or at the middle, or at the top of the
   order block, or wait confirmation."* Currently defaults to **wait-confirmation** (`all_three`). → *Decide the
   shipped default and whether entry-position (immediate/mid/top) becomes a tunable search dimension.*
2. **`golf_n`** (candles a golf candle must exceed). Default **3**. → *Confirm, or expose as a search parameter.*
3. **Key-level columns.** Weekly/monthly **opens** are active; inducement/retracement `W*`/`M*` highs/lows are
   available but off. → *Decide which to activate.*
4. **Breaker confirmation stack default.** `all_three` per your words; `golf_only`/`golf+fvg` also available.
   → *Confirm `all_three` is the default you want.*

### 3.2 The one unbuilt refactor — global retrace + wait ⬜
`notes.md` item: make retrace and wait **global** (one value each, applied to all indicators) instead of
per-indicator. **Plan:** add two engine-level params (`global_retrace`, `global_wait`) that override the
per-indicator values when set; walk every indicator's confirm path for conflicts; keep `all-off ⇒ parity`; add a
parity test that per-indicator = global when values match. Est. small–medium, isolated to the entry-resolver hook.

### 3.3 Optional companion study — indicator ablation
`notes.md`: take the $153,321 champion, turn off activated indicators, try combinations, keep the droppable ones
for ≤ 5% P/L loss. Tooling already exists: **`optimize/ablate_indicators.py`**. This directly serves the user's
stated goal of *fewer indicators without much sacrifice*. Not blocked on any decision above.

---

## 4. Recommended resume sequence (when this un-parks)

1. Get the four §3.1 decisions from the user (5-minute conversation).
2. Build the **global retrace + wait** refactor (§3.2) — the only concrete unbuilt piece.
3. Run the **ablation study** (§3.3) to prune the indicator set on the current champion.
4. Feed survivors + confirmed defaults back into the optimizer search space.

*Cross-refs: source brain-dump `/mnt/data/projects/trading/indictors.md`; implemented spec `docs/INDICATORS.md`
(approved 2026-06-04); frozen decisions `docs/INDICATOR_DECISIONS.md`; user backlog `/mnt/data/projects/trading/notes.md`;
ablation tool `optimize/ablate_indicators.py`; register `WORKSTREAMS.md` (WS-I).*
