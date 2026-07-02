# Exogenous Signal-Fusion Wishlist — data to provide + implementation plan

> ⏸️ **PARKED — RETURN TO THIS AFTER THE KALMAN/FUSION STUDY IS CLOSED.**
> This is the **signals** request (corrected): the group of **exogenous, orthogonal market data feeds** I asked the
> user to provide — VIX / vol term structure, market breadth, rates, options skew/flow — for a **regime/risk state**
> that feeds the **policy head** (sizing · SL/TP · sit-out), **not** the box entry direction. Resume pointer, not a
> finished task. Flagged in `WORKSTREAMS.md` (WS-SIG-FUSION) and in auto-memory.
>
> **Not to be confused with** `docs/INDICATOR_INVENTORY_AND_OPEN_ITEMS.md` — that covers the *technical indicators*
> (RSI/FVG/order-blocks/…), which are already built. **This** doc is the *external-signal* wishlist, which is new
> work and blocked on the user supplying data.
>
> **Canonical origin:** `docs/RESEARCH_SIGNAL_FUSION_KALMAN.md` §4–6 (the post-ES-verdict redirect) + the
> state-feature architecture in `docs/superpowers/specs/2026-06-26-cross-instrument-l2-state-feature-layer-design.md`.

---

## 0. Why these signals, and why *now* (the architectural context)

The ES cross-instrument study (`docs/XINST_ES_L1_VERDICT.md`) found ES is **redundant with NQ for entry
direction** — at 4h they carry the same information, so fusing them added nothing. That result did **not** kill
fusion; it **redirected** it:

- **Off** entry-direction and **off** near-duplicate inputs (ES, finer NQ timeframes — all already inside NQ's own
  price; this is also why M1/M2 in the Kalman study struggled).
- **Onto** a **regime / volatility / risk state** estimate that feeds the **policy head** π(state) — *sizing,
  stop/target, and when-to-sit-out* — where a state estimate is genuinely valuable.
- Fed by inputs **genuinely orthogonal to NQ price**, where a diversity premium actually exists.

```mermaid
flowchart TB
  subgraph SRC["exogenous, orthogonal sources (USER PROVIDES)"]
    v["VIX / vol term structure"]; b["market breadth"]; r["rates / DXY"]; o["options skew / flow"]
  end
  SRC --> S["fused latent STATE estimate<br/>(Kalman / factor / HMM, with uncertainty)"]
  S --> P["policy head π(state):<br/>sizing · SL/TP · WHEN-TO-SIT-OUT"]
  P -.->|"NEVER"| E["box entry direction ❌ (ES lesson)"]
  classDef no fill:#f8d7da,stroke:#a94442; class E no;
```

---

## 1. The signals — what, why orthogonal, and what to provide

For each: the **data the user must supply** (I cannot derive any of these from NQ OHLC), the **causal features** I'd
engineer, and the **regime read** it gives the policy head.

### 1.1 VIX / volatility term structure
- **What:** CBOE VIX (30-day implied vol) plus a term-structure pair — VIX9D (9-day) and/or VIX3M (3-month).
- **Orthogonality:** forward-looking *implied* vol and fear premium — not present in realized NQ price.
- **Provide (CSV, 2025–2026, ≥ daily, intraday preferred):** `Date, VIX` and, for the slope, `VIX3M` (and/or
  `VIX9D`).
- **Features (causal):** level z-score; **term-structure slope** `VIX/VIX3M` (>1 = backwardation = stress);
  day-over-day ROC.
- **Regime read:** high-VIX / backwardation → size down or sit out; calm contango → normal.

### 1.2 Market breadth
- **What:** NYSE/Nasdaq breadth — `$TICK`, advance−decline (`$ADD`/`$ADD`), up/down volume (`$TRIN`/`$UVOL`/`$DVOL`),
  % of names above a moving average.
- **Orthogonality:** participation *across* the market; a narrow (mega-cap-only) rally vs a broad one is invisible
  in the NQ index level.
- **Provide (CSV):** `Date, TICK` / `Date, ADD` / `Date, TRIN` (whichever are obtainable), aligned timestamps.
- **Features (causal):** breadth level & z-score; **breadth-vs-price divergence** (price up while breadth weak);
  intraday `$TICK` extremes.
- **Regime read:** weak/divergent breadth → lower-quality environment → sit out or tighten.

### 1.3 Rates / dollar
- **What:** 2y & 10y Treasury yields, **curve slope** `10y − 2y`, and DXY (dollar index).
- **Orthogonality:** the macro risk-on/off backdrop that drives multi-day regime shifts in equity-index behaviour.
- **Provide (CSV):** `Date, UST2Y, UST10Y` and `Date, DXY` (daily is fine).
- **Features (causal):** curve-slope level & sign; yield ROC; DXY trend (reuse the M2 Kalman `velocity_z` on DXY).
- **Regime read:** rapid rate moves / curve regime → risk-off caution for the policy head.

### 1.4 Options skew / flow
- **What:** equity/index put-call ratio, 25-delta risk-reversal (skew), and — if available — dealer **gamma
  exposure (GEX)** / positioning.
- **Orthogonality:** tail-risk pricing and dealer hedging pressure (pin vs squeeze) — orthogonal to spot price.
- **Provide (CSV):** `Date, PutCallRatio` (most obtainable); `Date, Skew25d` and `Date, GEX` if a source exists.
- **Features (causal):** put/call percentile & z; skew percentile; GEX sign (positive = mean-reverting/pinned,
  negative = trending/volatile).
- **Regime read:** extreme skew / negative GEX → volatile regime → wider stops or sit out.

---

## 2. Implementation pipeline (shared, causal, TDD, off the golden path)

1. **Ingest** each feed as a CSV → a small `exogenous/` loader that timestamp-aligns to the NQ decision bars using
   the **last value closed ≤ the signal bar** (the same no-look-ahead `searchsorted` alignment as M1/M2 in the
   Kalman study). Missing days forward-filled with an explicit staleness flag.
2. **Feature layer** — per signal, emit level / z-score / slope / percentile columns; all causal, all logged.
3. **⭐ Cheap one-feature pre-test FIRST** (`RESEARCH_SIGNAL_FUSION_KALMAN.md` §5 — the gate before any build):
   > Does conditioning on **any single** orthogonal feature (e.g. a VIX regime bucket) improve **risk-adjusted**
   > return — via **sizing or sit-out** — vs the unconditioned champion?
   Run it walk-forward (the study's hard-won discipline). **If no single feature moves the needle → STOP;** fusion
   sophistication won't manufacture signal.
4. **Only if a feature passes** → fuse several into a latent state (Kalman / factor / HMM with uncertainty) →
   **policy head π(state)**: position size, SL/TP scaling, sit-out. **Never** the box entry direction.
5. **Parity:** exogenous layer entirely off the production path; policy-head off ⇒ byte-identical champion; golden
   6/6 must stay green (the invariant held through the entire Kalman study).

---

## 3. What's blocking (the "provide" ask, restated)

**I need the data feeds.** In priority order (each is independently useful for the §2.3 pre-test):

1. **VIX (+ VIX3M)** — highest signal-to-effort; the classic regime variable.
2. **Put/Call ratio** — widely available, strong tail-risk read.
3. **Breadth ($TICK / $ADD / $TRIN)** — best if intraday.
4. **Rates (2y/10y) + DXY** — daily is fine.

Format: CSV, one header row, UTC or ET timestamps stated, covering **2025-01 → 2026 (present)** to match the
research window. Even **one** feed (VIX) is enough to run the decisive §2.3 pre-test and decide whether the whole
fusion direction is worth building.

---

## 4. Resume sequence (when this un-parks)

1. User provides ≥ 1 feed (start with VIX).
2. Build the `exogenous/` causal loader + feature layer (TDD).
3. Run the **single-feature sizing/sit-out pre-test**, walk-forward, vs the $153,321 champion.
4. Pre-test passes → build the fusion state + policy head. Pre-test fails → record the verdict and close, same as
   the Kalman study.

*Cross-refs: `docs/RESEARCH_SIGNAL_FUSION_KALMAN.md` (origin), `docs/XINST_ES_L1_VERDICT.md` (why not ES),
`docs/superpowers/specs/2026-06-26-cross-instrument-l2-state-feature-layer-design.md` (state-feature / policy-head
architecture), `docs/KALMAN_FUSION_TRIALS_DEEPDIVE.md` (the causal-alignment + walk-forward machinery to reuse),
`WORKSTREAMS.md` (WS-SIG-FUSION).*
