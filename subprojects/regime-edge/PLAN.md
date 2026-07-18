# Regime-edge program — verbose to-do list (3 experiments, cycled one-by-one)

**Branch:** `research-regime-edge` (off dev). **Opened 2026-07-18.**
**Why this exists:** the vol-model line is exhausted — three independent methods (TimesFM, Chronos-2,
HMM/Jump-Model) agree that **volatility/uncertainty gating does not help the box-fusion strategy**, because
the strategy is **vol-seeking** (it earns in turbulent markets). So we stop testing "skip the uncertain
trades" and instead test the three directions that still have a *real mechanism*. Each runs through the
**same reporting system** (prior-art → reproduce/baseline → dumb-control → robustness → verdict), one at a
time, with its own report docs.

Plain-language note: "the strategy" = our box-breakout + multi-indicator fusion on NQ (Nasdaq-100 futures).
"Return/DD" = total profit ÷ worst peak-to-trough loss (higher = better, less painful). "Regime" = what kind
of market it is (calm vs turbulent), inferred from data. "Causal / filtered" = using only past data, no
peeking at the future (or the backtest is a lie).

---

## Experiment 1 — NQ concentration as a NON-vol regime signal
**The idea (verbose).** The Nasdaq-100 is dominated by a handful of mega-cap tech names (the "top 7" are
~half the index). When the index is being dragged by just those few names, it behaves differently than when
gains are broad. **Concentration** measures that — and it is *orthogonal* to price volatility (a market can
be calm but extremely concentrated, or volatile but broad). Our own earlier finding — NQ is ~1.3–1.5× more
volatile than ES because of this tech concentration — makes this the most on-point non-vol signal to try.

**Hypothesis.** High-concentration periods are a distinct regime where the box strategy's edge differs; using
concentration to size or sit out could help where a vol signal could not (because it carries *different*
information).

**How to measure it without a paid API.** A clean, free, derivable proxy: the ratio of the **equal-weight**
Nasdaq-100 (ETF **QQEW**) to the **cap-weight** Nasdaq-100 (ETF **QQQ**). When QQQ outruns QQEW, a few big
names dominate = high concentration; the QQQ/QQEW ratio's level/slope is the concentration regime. Both ETFs
have long free daily history (e.g. stooq CSV). Fallback: a mega-cap basket (AAPL+MSFT+NVDA+…) ÷ QQQ.

**Protocol.** PRIOR_ART (does concentration/breadth predict index behavior; source the QQQ/QQEW data
causally) → BASELINE (build the daily concentration series 2024–26, label fusion trades) → DUMB CONTROL (does
it beat a trivial breadth proxy / our own realized-vol?) → ROBUSTNESS (per-year, random-label control,
filtered-only) → VERDICT (concentration → size/sit-out?). **Data risk:** needs QQQ+QQEW history; try free
sources; if blocked, park with the blocker stated.

## Experiment 2 — Sizing, not veto (upsize where the strategy earns)
**The idea (verbose).** Every vol/regime test so far *removed* trades (a veto), which hurt because the
strategy earns in turbulent regimes. Flip it: instead of skipping trades, **change the position size** by
regime — bigger in the turbulent regime (where Return/DD is best), smaller in the calm regime (the only
losing one). Same trades, re-weighted. This directly uses the regime discovery instead of fighting it.

**Hypothesis.** Regime-scaled sizing lifts risk-adjusted return without the veto's damage — because it keeps
the good high-vol trades and merely leans into them.

**Protocol.** Reuse the causal HMM regime labels already computed (`research-regime-hmm`). BASELINE: apply a
size multiplier per regime (e.g. calm 0.5×, mid 1×, turbulent 1.5×) to the 2024–26 fusion P/L; measure
Return/DD, and crucially **max-drawdown scales with size** so account for it honestly. DUMB CONTROL: vs a
flat size, and vs a realized-vol-scaled size (classic vol-targeting). ROBUSTNESS: the multipliers must be
chosen **out-of-sample** (not tuned on the same book — that's the overfit trap that sank the Jump-Model
penalty); per-year; a random-regime-multiplier control. VERDICT.
**Honest caveat up front:** sizing multipliers are easy to overfit on one book (n=1). The multipliers must be
set a-priori or on a train slice, and must clear the random control — else it's curve-fitting.

## Experiment 3 — Apply the regime/vol gate to a vol-HURT layer (L2 / mean-reversion)
**The idea (verbose).** A high-vol veto backfired on our *breakout* strategy because breakouts love
volatility. But the same veto has a **real mechanism** on a strategy that volatility *hurts* — e.g. a
mean-reversion / fade strategy (which gets run over in trends/turbulence), or **our L2 layer** (which manages
L1's dropped/vetoed signals and may have different vol sensitivity). Point the (already-built) TimesFM/
Chronos/HMM vol signal at *that* book and see if it finally helps.

**Hypothesis.** On a vol-hurt strategy, skipping high-vol trades removes the trades that volatility ruins →
the vol gate helps here even though it hurt the breakout.

**Protocol.** Identify a vol-hurt book we can generate (the L2 layer's trade log, or a simple NQ
mean-reversion baseline). PRIOR_ART (confirm the strategy is vol-hurt) → BASELINE (apply the existing
vol/regime gate) → DUMB CONTROL → ROBUSTNESS (per-year/random/filtered-only) → VERDICT.
**Data/scope risk:** needs the L2 trade log (server) or building a mean-reversion baseline; scope-check first.

---

## Order & branch structure
Cycle in the user's order **1 → 2 → 3**, one at a time, each producing `docs/<exp>/{PRIOR_ART,REPRO,
ROBUSTNESS}.md` + a verdict, updating this program's `EXPERIMENTS_LOG.md`. All three share this
`research-regime-edge` branch (they're one coherent "does a regime/exogenous signal help via a mechanism"
program). Server compute only. Carry every lesson: **a favorable single window means nothing** — dumb-control
+ random control + per-year before any GO; **choose any tunable out-of-sample**; **check the gated/scaled
max-DD**, not just Return/DD.

## Expected outcomes (honest priors)
- **#1 concentration:** genuinely different information → the most likely to show *something* (or cleanly
  nothing); main risk is data sourcing.
- **#2 sizing:** plausible but overfit-prone on n=1; the random control + OOS multiplier selection is the test.
- **#3 vol-hurt layer:** the vol gate's best shot at a real mechanism; hinges on having a vol-hurt book.

## Tasks: #108 (concentration), #111 (sizing), #112 (vol-hurt layer).
