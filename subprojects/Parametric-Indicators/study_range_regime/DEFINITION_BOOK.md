# Definition Book — market structure & ICT/Smart-Money concepts (v1.0, decisions LOCKED)

## LOCKED DECISIONS (clarify gate, 2026-06-15)
- **Scope:** build all of — LL/HL/HH/LH tables **+ IFVG + breaker-block entry + CISD**.
- **Swing basis:** **close-based** pivots (`market_structure`), matching "all closes not high/low".
- **Swing strength:** emit tables at `swing_l ∈ {2, 3, 5}`; headline table uses **3** (balanced).
- **Timeframe:** **4h** decision frame; source = `optimize.sub.data_2024_2026.load_bundle` (2024–2026).
- **CISD = STANDARD** — a close back through the **opening price of the prior delivery leg** (the run of
  consecutive same-colour candles that produced the move). NOT the golf+FVG bundle.
- **Golf candle = the existing STRICT engulfing** (`smc.py::golf_candle`); no size-only variant added.
- **IFVG inversion trigger = a CLOSE beyond the gap** (A4 resolved: close, not wick).
- **Breaker = a CLOSE beyond the OB edge**, then a tradeable **entry zone in the FLIPPED direction**
  (A9 resolved: close-based; colour flips per the user — top OB red→top breaker green, bottom OB green→
  bottom breaker red).
- **Output shape:** one **chronological** labeled table + a small **per-period (M/Q/Y) summary** (A3).



**Purpose:** take the user-supplied concept list, verify each against (a) the **standard** ICT/Smart-Money
definition and (b) the **project's existing implementation** (`indicators/`), and flag every **ambiguity** that
must be resolved before building. Status legend: ✅ agree · ⚠️ partial / needs a decision · ❓ ambiguous · 🆕 not
yet in project. **Nothing here is final until the clarify questions are answered.**

> Notation: the four supplied "tables" — **LL** (lower-low), **HH** (higher-high), **LH** (lower-high),
> **HL** (higher-low) — are *swing-structure labels*. This book also covers the surrounding concepts the user
> listed so they're pinned with one agreed meaning.

---

## 1. Swing-structure labels — LL / HL / HH / LH  *(the new deliverable)*
- **User:** "ll: lower low, hl: higher low, hh: higher high, lh: lower high … all closes not high/low."
- **Standard:** comparing each new **swing high** to the prior swing high → **HH** if higher, **LH** if lower;
  each new **swing low** to the prior swing low → **HL** if higher, **LL** if lower. HH+HL = uptrend
  structure; LH+LL = downtrend; mixed = transition. A *swing* is a local pivot (a high/low with N lower/
  higher bars on each side).
- **Project:** `indicators/smc.py::market_structure(close, swing_l)` finds **close-based** fractal pivots
  (a pivot strictly exceeds the `swing_l` closes on both sides); `structure_trend` already derives HH+HL/LH+LL
  stance. So the *pivots* exist; the **per-swing LL/HL/HH/LH label table does not** (🆕).
- **Agreement:** ✅ on label logic. **User explicitly wants CLOSE-based** ("all closes not high/low") — matches
  `market_structure`. ⚠️ but see ambiguities A1–A3 (basis, strength, timeframe, output shape).

## 2. Retrace / entry-wait
- **User:** "retrace → how many price should I wait to enter; how much time to wait; or both."
- **Standard:** after a signal, wait for price to pull back (retrace) a set distance into a zone (e.g. into an
  FVG / OB / a % of the leg) before entering — a *price* condition; or wait a fixed number of bars — a *time*
  condition; or both.
- **Project:** the engine already has a global **retrace** param + **wait bars** (WS-I rev#3 global retrace,
  rev#4 wait counted on 1-min bars). So both axes exist.
- **Status:** ✅ exists; ❓ A6 — for THIS task, is retrace in scope, or documented only?

## 3. Classic indicators — ADX, MACD, RSI, ATR, EMA, SMA, RMA
- **User:** lists them as available indicators.
- **Standard:** ADX = trend-strength (0–100); MACD = EMA(12)−EMA(26) + signal EMA(9); RSI = Wilder
  momentum oscillator (RMA of gains/losses); ATR = Wilder average true range; EMA/SMA/RMA = exponential /
  simple / Wilder-running moving averages (RMA = the smoothing inside RSI & ATR).
- **Project:** all in `indicators/classic.py` (used by the optimizer's confirm/veto layer).
- **Status:** ✅ standard, already implemented. No ambiguity.

## 4. FVG — Fair Value Gap
- **User:** "needs three candles with no trades in between; polish (going high) = bullish, parish (goes down)
  = bearish; the signal will go fast after this tiny stop."
- **Standard:** 3-candle imbalance. **Bullish** FVG: `low[3] > high[1]` (gap = [high[1], low[3]]); **Bearish**:
  `high[3] < low[1]` (gap = [high[3], low[1]]). The middle candle's strong move leaves an untraded gap.
- **Project:** `smc.py::fvg(high, low)` — exactly this (wick-based). ✅
- **Status:** ✅ agree. ("polish"→bullish, "parish"→bearish noted as the user's spelling of bull/bear.)

## 5. IFVG — Inverse Fair Value Gap
- **User:** "ifvg: it went into the fvg and burnt into it → it will go horribly; inversion value gap."
- **Standard:** when price trades **through and closes beyond** an FVG, the FVG is *invalidated* and **inverts**
  — a bullish FVG that fails becomes resistance (bearish IFVG) and vice-versa. Same "burned-into → role flips"
  idea as a breaker.
- **Project:** 🆕 not a named detector (FVG exists; its inversion does not).
- **Status:** ⚠️ A4 — confirm the inversion trigger = a **close** beyond the gap (not just a wick).

## 6. Trend
- **User:** lists "trend" as an indicator.
- **Standard:** direction of structure — can be defined by (a) swing structure (HH+HL vs LH+LL), (b) a moving
  average slope/stack, or (c) a look-back range read (the price-range registry's LOW_TREND/HIGH_TREND).
- **Project:** has **all three** flavours (`structure_trend`, MA indicators, `regime_features` trend).
- **Status:** ❓ A5 — which trend definition is canonical for this task?

## 7. Key levels
- **User:** lists "key levels."
- **Standard:** significant S/R — prior session/period highs & lows, swing points, round numbers, OB/breaker
  edges.
- **Project:** the **price-range registry** (`range_registry.py`) already emits per-M/Q/Y highs & lows = a
  concrete key-level set.
- **Status:** ⚠️ A7 — are "key levels" = the registry's period highs/lows, or a separate (e.g. swing-based or
  round-number) set?

## 8. Order Block (OB)
- **User:** "the lowest/highest point the price touched then went crazy → created HH or LL; all closes not
  high/low. **Top OB** = HH→LL, bearish, **RED** candle → take short (immediately / at middle / at top / or
  wait confirmation). **Bottom OB** = LL→HH, bullish, **GREEN**. Once broken, can't be used as OB again — only
  as breaker."
- **Standard:** the **last opposite-colour candle before a displacement** that breaks structure. Bullish OB =
  last *down* candle before an up-move breaking the prior swing high; bearish OB = last *up* candle before a
  down-move breaking the prior swing low. Measured by body (open–close) or full range — variant choice.
- **Project:** `smc.py::order_blocks(...)` — last down-close before a close **above** the latest swing high
  (bullish OB) / last up-close before a close **below** the latest swing low (bearish OB); **body-based**
  (min/max of open,close); **converts to breaker once price closes beyond it** (then unusable as OB). This
  matches the user's rules incl. "burned-into → breaker" and "closes not high/low." ✅
- **Status:** ✅ strong agreement. ❓ A8 — entry placement (immediate / mid / top of OB / wait-confirm) is a new
  *entry* behaviour, not in the current detector (it only emits an in-zone reaction signal).

## 9. Breaker Block
- **User:** "OB burned into (close on top of the top or under the bottom) → breaker block. **Top OB RED →
  top breaker GREEN; bottom OB GREEN → bottom breaker RED** (colour flips). Concept = same as IFVG inversion."
- **Standard:** a **failed order block**; after the OB is broken, price retests it from the *other* side and it
  acts as S/R in the new direction. Role/colour flips — exactly the user's description.
- **Project:** the OB→breaker **retirement** exists (OB dies when closed-through), but a **tradeable breaker
  entry signal does not** (🆕).
- **Status:** ⚠️ A9 — confirm break trigger = a **close** beyond the OB edge; and that the breaker is then an
  *entry* zone in the flipped direction.

## 10. CISD — Change In State of Delivery
- **User:** "CISD: golf candle (bigger than all previous, configurable N) + fair value gap; **all three** for
  confirmation to take the breaker box."
- **Standard:** CISD = price **closing back through the opening price of the prior delivery leg** (the run of
  consecutive same-colour candles that produced the move) — i.e. a confirmed shift in order-flow direction.
  ICT's CISD is specifically that *close-through-the-leg-open* event, not inherently "golf + FVG."
- **Discrepancy:** the user's CISD = (golf candle) + (FVG) as a confirmation bundle; the standard CISD is the
  delivery-open break. These are *different* triggers. Also "all three" is unclear — which three? Candidate:
  (1) golf candle, (2) FVG, (3) the close-through (CISD proper)?
- **Status:** ❓ A10 — adopt the user's bundle definition, the standard delivery-open definition, or both?

## 11. Golf candle  (= engulfing, in this project)
- **User:** "bigger candle than all the previous ones (configurable how many candles to be bigger than)."
- **Standard:** "golf candle" is **not** a standard term. The closest standard concept is an **engulfing /
  expansion / displacement** candle.
- **Project:** `smc.py::golf_candle(...)` = **N-candle engulfing**: opposite colour to all N priors **and**
  wick-engulfs them **and** body ≥ 70% of the prior N-span (renamed from "golf" in WS-I rev#2).
- **Discrepancy:** the user's plain definition is **size-only** ("bigger than the previous N"); the project adds
  colour + wick-engulf + 70% body. The project version is stricter.
- **Status:** ❓ A11 — keep the strict engulfing definition, or add a looser size-only "big candle" variant?

## 12. Gap
- **User:** "gap → any time there is no trades."
- **Standard:** a price range with no trading (opening gap, or the imbalance inside an FVG). ✅
- **Status:** ✅ agree; FVG is the 3-candle special case of a gap.

---

## Ambiguities to resolve (the clarify gate)
| id | concept | the open question |
|----|---------|-------------------|
| **A1** | swings | basis: **close**-based pivots (project default, user said "all closes") vs **high/low** intrabar pivots? |
| **A2** | swings | **swing strength** `swing_l` (how many bars on each side define a pivot) — what value(s)? |
| **A3** | tables | **timeframe** of the LL/HL/HH/LH tables — 4h decision frame, 1-min, or per calendar M/Q/Y like the registry? And **output shape**: one chronological labeled table, or four separate per-label tables? |
| **A4** | IFVG | inversion trigger = **close** beyond the gap (not a wick)? |
| **A5** | trend | which trend definition is canonical (structure HH/HL · MA · range-registry look-back)? |
| **A6** | retrace | in scope for this task, or documented only? |
| **A7** | key levels | = registry period highs/lows, or a separate set? |
| **A8** | OB entry | entry placement: immediate / middle / top of OB / wait-confirm — build now or document? |
| **A9** | breaker | break trigger = **close** beyond OB edge; breaker = entry zone in flipped direction? |
| **A10** | CISD | user's (golf+FVG) bundle vs standard (close-through delivery-leg open) — which? |
| **A11** | golf | strict engulfing (project) vs looser size-only "big candle" (user's words)? |

**Scope question (S):** is the *immediate* deliverable **only** the LL/HL/HH/LH tables (rest of this book
documented for later), or do you want IFVG / breaker-entry / CISD built in this pass too?
→ **RESOLVED: build all** (tables + IFVG + breaker + CISD).

---

## BUILD STATUS (2026-06-15) — detectors implemented + tested + tables produced
New causal detectors in `indicators/smc.py` (all return per-bar int8 signals unless noted):
- `swing_labels(close, swing_l)` → (kind, label HH/LH/HL/LL, confirmed_at) — the LL/HL/HH/LH labeller.
- `ifvg(high, low, close)` — inverse FVG (close-burns-through → flipped S/R zone).
- `breaker_blocks(open, high, low, close, swing_l)` — OB closed-through → flipped-direction entry zone.
- `cisd(open, close)` — standard Change-In-State-of-Delivery (close through prior delivery-leg open).
Tests: `tests/test_smc.py` +4 (swing labels, IFVG invert, breaker flip, CISD both directions) — **13/13 pass**.
Tables: `structure_tables.py` → `results/structure_swings_l{2,3,5}.csv`, `_summary.csv`, `_events_l3.csv`,
`STRUCTURE_TABLES.md`. Headline swing_l=3 over 2024–26 (4h): 740 pivots — **HH 209 / HL 212 / LH 164 / LL 153**
(HH+HL dominance = the uptrend, consistent with the price-range registry's HIGH_TREND). Engine untouched ⇒
golden byte-match unaffected (new functions only).

**Still open (documented, not built):** OB/breaker *entry-placement* options (immediate/mid/top/wait), retrace
tuning, and wiring any of these new detectors into the optimizer search space (a future `wsh5`-class task).
