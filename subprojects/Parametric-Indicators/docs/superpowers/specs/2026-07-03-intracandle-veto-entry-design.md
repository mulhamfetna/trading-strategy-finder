# Design — Intra-Candle Entry for Vetoed Signals (L1)

**Date:** 2026-07-03 · **Type:** feature (entry-increasing, L1) · **Status:** design approved, spec under review ·
**Anchor:** NQ 4h champion ($142,203 / 214; also wsh6cold $153,321). Worksheet:
`docs/INTRACANDLE_VETO_ENTRY_DECISIONS.md`. Prior-art research folded into that worksheet §2.5.

Serves the current direction: **increase entries toward near-zero-day-hold, L1 first, held-or-better quality.**

---

## 1. Goal & question

**Today:** a box signal an indicator **vetoes** is dropped forever. **Proposed:** keep the vetoed signal **armed**
and re-evaluate the **full entry gate** on the **1-minute bars inside its 4h candle**; enter at the first bar where
the gate opens (`¬veto ∧ ≥K confirms`) **while flat**. So vetoed signals get a **second, intra-candle chance**.

**Question this feature answers (Phase 1):** across wait windows `N`, do the rescued vetoed signals **clear the
57.5% breakeven** out-of-sample, adding entries at **held-or-better payoff** — or does the delay let the move
exhaust (the key risk the prior-art research flagged)?

**Non-goals (Phase 1):** no optimizer/fast-engine support (Phase 2, gated on Phase 1); no retrace/pullback wait
(evidence: pullback entries were catastrophic on MNQ); no direction flip; no change to vol-gated drops; production
default unchanged.

## 2. Decisions (locked)

| # | Decision |
|---|---|
| **D0** | Disableable — dashboard checkbox **directly under the time-cap control**, **default OFF**; also an engine/param flag so the optimizer can toggle it (Phase 2). Off ⇒ byte-identical champion. |
| **D1** | Entry trigger = the **full champion gate evaluated on the 1-min bar**: `¬veto ∧ (#confirms ≥ K)` (vol-gate is per-candle, already passed). |
| **D2** | Wait window = tunable **`N` 1-min bars** (also ends if superseded — but a new box signal only fires at the 4h close, so within one candle the window is just `N`). |
| **D3** | If not flat when the gate opens → **keep waiting** for the first bar that is gate-open **and** flat, within `N`; **log** deferred/dropped counts. |
| **D4** | Enter **immediately at the qualifying 1-min bar's close** — **no** added retrace/pullback. |
| **D5** | Scope = **vetoed signals that PASSED the vol-gate** (a vol-gated signal can never re-qualify intra-candle, since the gate still includes the per-candle vol-gate — so we only arm signals whose sole block was the indicator veto). |
| **D6** | **Keep the original box direction** (no flip). |
| **D7** | Phase-1 study **sweeps `N ∈ {30, 60, 120, 240}`** (measure the decay curve; don't pick one). |
| **D8** | **One armed signal at a time**; a new box signal (next candle) supersedes. |
| **D9** | **Champion study first**; optimizer only if Phase 1 clears the bar. |

## 3. Mechanism — reuse the existing carry-mode resolver, inverted

The exact engine (`engine.py`) already has a **carry mode**: when an `entry_resolver` is supplied it **arms** a
gated non-vetoed signal, walks the candle's 1-min sub-window, and fills via the resolver — and a **live veto
aborts** the armed entry (`engine.py:460`). This feature **inverts** that abort into an **arm**:

1. **Arm a vetoed directional signal** (today these are dropped at `:460`). Store `{dir, sidx, sclose}` — `dir` is
   the original box direction (D6).
2. **New resolver `intracandle_veto_entry`**: over the candle's 1-min bars `sub_w` (capped at `N`, D2/D7),
   evaluate the **full gate on each 1-min bar `t`** for the armed direction — `¬veto(t) ∧ (#confirm(t) ≥ K)` —
   using the **per-1-min-bar indicator directions the runner already computes** (see §4). Return the **first bar's
   close** where the gate is open **and the engine is flat** (D1/D3/D4); else `None` (keep armed / expire at `N`).
3. Entry, exits, and logging then proceed exactly as any other trade (1-min-resolved SL/TP; box-native direction).

**Causality:** the gate at bar `t` uses only indicator values on 1-min bars `≤ t` (the runner's directions are a
forward causal series). No look-ahead — same guarantee as the decision-bar path, just sampled at every 1-min bar
instead of only the candle close.

**D3 interleaving (the one delicate part):** "keep waiting until flat" means the armed signal must survive across
1-min bars while a prior trade's **exit walk** runs in the same window. Implementation must carry `armed` through
the exit walk and only attempt the gated fill on bars where `open_trade is None`. Flagged for the plan.

## 4. Components / files

- **`indicators/runner.py`** — add a helper `gate_at_1min(...)` (or extend `indicator_source_1min`) exposing the
  **per-1-min-bar** gate boolean for a given direction, reusing the `cdir1/vdir1` full-series directions already
  computed inside `_vote_from_1min` (currently only *sampled* at `j_idx` decision-bar closes). Pure, causal.
- **`engine.py`** — new `intracandle_veto_entry` resolver + arm-the-vetoed-signal branch (guarded by the D0 flag;
  flag off ⇒ existing code path untouched ⇒ parity). Carry `armed` across the exit walk (D3).
- **Study harness** (`optimize/counterfactual_pause.py` or a small `research/`-style runner) — run the champion
  with the flag on across `N ∈ {30,60,120,240}`; emit the metrics table.
- **Dashboard** (`frontend/dashboard.html` + `server.py`) — the D0 checkbox under the time-cap control (wired in
  Phase 1 so the study is reproducible from the UI; default off).

## 5. Testing (TDD, off the golden path)

1. **Off ⇒ parity:** flag off → `perf/check_golden.py` 6/6 byte-identical (the hard gate).
2. **Causality:** gate at bar `t` unchanged when 1-min bars `> t` are mutated (no look-ahead).
3. **Arms only vetoed signals** (D5); non-vetoed path unchanged.
4. **First-qualifying-bar fill** (D4): a synthetic veto that clears at bar `t` enters at `t`'s close, not earlier/later.
5. **Keep-waiting-until-flat** (D3): with a prior trade open until bar `u`, a signal whose gate opens at `t<u`
   enters at the first flat gate-open bar ≥ `u` (within `N`), and the deferral is logged.
6. **Expiry at `N`** and **direction preserved** (D6).

## 6. Phase 1 report → gate to Phase 2

Metrics vs the champion, per `N`: **entries added**, **win-rate of the added entries vs 57.5% breakeven**, payoff,
total P/L, **hold-time distribution** (the zero-day-hold goal), max-DD. **Proceed to Phase 2 (optimizer/fast-engine
+ search `N` and the on/off flag) only if** added entries clear breakeven at held-or-better payoff on the champion
(and ideally OOS). Otherwise record the verdict and stop — same discipline as the Kalman study.
