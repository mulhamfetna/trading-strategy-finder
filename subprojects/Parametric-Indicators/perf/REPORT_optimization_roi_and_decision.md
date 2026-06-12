# Backtester Optimization — Status, Remaining Work, ROI & the "Import-Now-or-Hold" Decision

**Date:** 2026-06-12 · branch `dev` (local only, not pushed) · task #210
**Audience:** decision-makers. Written in both **professional** and **baby** language.
**Question answered:** *Where did we reach? How much is left? What does each new update cost, what's
the ROI, is it efficient enough already, and — given we are expanding the system to much more complicated
operations — should we keep optimizing now or hold it for later?*

---

## 0. The verdict in one box

> **We already captured the big, durable win (4h: 36.2 s → 12.1 s, −67%, proven byte-identical). The
> remaining indicator-vectorization steps have LOW marginal ROI and are partly already done by side-effect;
> several would need re-validation the moment the system expands. RECOMMENDATION: HOLD the remaining
> micro-optimizations. Bank the current state, keep the safety net, and resume optimization *after* the
> "more complicated operations" land — but target a different layer (the per-decision-bar loop + the
> optimizer sweep cache), because that is the layer your expansion will actually stress.**

**Baby version:** We already squeezed the orange — most of the juice is out. The few drops left are hard to
get and will spill anyway when we rebuild the kitchen (the expansion). So stop squeezing now, keep the
measuring cups (the tests), and squeeze again later — but a *different* orange that the new recipe needs.

---

## 1. Where we reached (the scorecard)

| Step | Commit | 4h time | Per-fn win | Proven |
|------|--------|--------:|-----------|--------|
| baseline | `f9d6f36` | 36.2 s | — | golden frozen (6 TFs) |
| D — obv | `e764482` | — | 64× | bit-identical |
| A1 — bollinger | `1f1c29f` | — | 40× | bit-identical |
| A2 — cci | `f178ec3` | 25.6 s | 4× | bit-identical |
| E — order_blocks sampled | `08b8c77` | 16.5 s | −9 s | byte-identical |
| C′ — order_blocks numpy | `5d1945e` | **12.1 s** | 2.8× | byte-identical |

**4h backtest: 36.2 s → 12.1 s (−67%). 148 tests passing. Every step proven results-unchanged** via golden
byte-match + frozen-reference equivalence + parity harness. The **safety net itself** (golden baselines,
`_reference.py`, equivalence + parity tests) is the most valuable asset we built — it is reusable forever
and is what makes any *future* optimization cheap and safe.

> **Baby:** We made the 4-hour test almost 3× faster and *proved* the answers never changed. And we built a
> "lie detector" (the tests) that will instantly catch if any future change ever alters a result.

---

## 2. The single most important fact for this decision: there are TWO cost axes

The backtester's time lives in two very different places, and they scale **oppositely** as the system grows:

| Cost axis | What it is | Where it dominates | Status |
|-----------|-----------|--------------------|--------|
| **(A) 1-minute indicator compute** | compute each indicator across all 486,969 one-minute bars, read one value per decision bar | **coarse** TFs (4h/2h/1h) | **mostly DONE** (D/A1/A2/E/C′) |
| **(B) Per-decision-bar `build_payload` loop** | the K-of-N gate + structure + exit walk, executed *per decision bar* | **fine** TFs (5m ≈ 113 s, 2m > 600 s) | **untouched** |

> **Baby:** There are two clocks. Clock A ticks once per indicator over the whole minute-history — we
> already sped that up. Clock B ticks once per *trade decision*; on slow timeframes there are tens of
> thousands of decisions, so Clock B is the real monster — and we have not touched it.

**This is the crux.** Everything we optimized (Phase 1–2) was **axis A**. Axis A is *already efficient enough*
for coarse-TF single backtests and day-to-day iteration. The work that remains in axis A is small. The big
unclaimed prize is **axis B**, and **axis B is exactly the layer that "more complicated operations" will make
heavier** (more indicators, more per-bar logic, more instruments = more per-decision work).

---

## 3. Remaining work inventory — measured, not guessed

Pulled from the real `cProfile` (`optimize/REPORT_backtester_speed_optimization.md` §2) and the current
state of `indicators/classic.py`.

### 3.1 What is ALREADY done (don't re-do it)
- **obv, bollinger, cci** — vectorized, bit-identical. ✅
- **order_blocks** — sampled (E) + numpy zones (C′). ✅
- **stochastic %D, mfi window-sums, cci MAD** — already use `sliding_window_view`. ✅ (done by side-effect)
- **rsi, ema, rma** — these are *true O(N) recurrences*; a single sequential pass is already optimal. There
  is nothing to vectorize. ✅ (optimal by nature)

### 3.2 What is LEFT (the honest, short list)

| # | Candidate | What's actually left | Measured cost today | Effort | Risk | Expected win | ROI |
|---|-----------|----------------------|--------------------:|--------|------|-------------|-----|
| **A3** | stochastic `_roll_max`/`_roll_min` (monotonic deque); mfi/adx O(N) passes | only `_roll_max/min` is a true per-bar loop; **it does not appear in the 4h hot list at all** | ~0 s on champion (only matters if a strategy enables stochastic, mostly on fine TFs) | Med (deque exactness) | Med | **≈0–1 s** | **LOW** |
| **MS** | `market_structure` + `structure_trend` vectorization (SMC) | per-bar fractal swing detection (`.all()` on slices) | **3.0 s self + 4.3 s cum** | **High** (stateful SMC) | **High** (core SMC correctness) | ~2–3 s on coarse TFs | **LOW–MED** |
| **F** | cache the param-independent 1-min sampling map across optimizer trials | sampling map recomputed every trial; it never changes within a (TF, dataset) | n/a single backtest; **multiplies across a 5,000-trial sweep** | Med | Low (pure additive cache) | small per-trial × thousands | **HIGH *if* sweeps are imminent** |
| **C** | Numba `@njit` the order_blocks / market_structure loops | the only path to a *big* axis-A cut | the ~5.8 s order_blocks loop | — | — | potentially large | **BLOCKED** (Py 3.14 has no numba wheel; PEP 668 forbids a safe install) |
| **B(axis)** | the per-decision-bar `build_payload` loop (fine TFs) | restructure the per-decision work; the real fine-TF monster | **5m ≈ 113 s, 2m > 600 s** | **Very High** | **Very High** (core hot path) | potentially huge on fine TFs | **HIGH but premature** |

> **Baby:** The leftover indicator chores (A3) are tiny — one of them isn't even on the stopwatch's radar.
> The medium chore (market_structure) is hard, risky, and only saves ~2–3 seconds. The genuinely valuable
> work is (F) a cache that only pays off when you run big optimizer sweeps, and (B) the slow-timeframe
> monster — but (B) is the most dangerous code to touch and would be wasted if we touch it before the
> system's new shape is settled.

---

## 4. Cost of new updates (the part people forget)

Every optimization step carries **three** costs, not one:

1. **Build cost** — engineering time to write it (the table above).
2. **Validation cost** — re-running the full equivalence + golden + parity + pytest gate, and (at phase
   boundaries) the full 6-TF golden check. This is *fixed per step* and non-trivial.
3. **Re-validation-on-change cost** — **the killer for the current decision.** The optimizations are proven
   *byte-identical against frozen golden baselines*. The moment the "more complicated operations" change
   what the strategy computes (new indicators, new gate logic, new instruments), **those golden baselines
   must be re-frozen**, and every optimized function must be re-proven against the *new* reference. Code we
   optimize *now*, on the *old* shape, pays this tax twice — once now, once after the expansion.

> **Baby:** Optimizing code right before you remodel it means you do the careful "did I break anything?"
> dance twice — once for the old kitchen, once for the new one. Cheaper to remodel first, then optimize.

---

## 5. Is it efficient enough already?

> **UPDATE 2026-06-12 — Axis B was implemented (B1–B3b), so the fine-TF picture below has materially
> improved.** The per-decision loop is no longer the wall it was.

**For what we do today: yes on coarse TFs, and now much better on fine TFs.**

- Single coarse-TF backtest (4h/2h/1h): **11–16 s** — fine for interactive iteration.
- Single fine-TF backtest (5m/2m): **was 113 s / 600 s → now 35 s / 89 s** after Axis B (−63 % / −67 %),
  byte-identical. Still the slowest, but no longer prohibitive for a dashboard run.
- Optimizer sweeps are unaffected (they already use `fast_engine`); Axis B sped up the **dashboard +
  standalone backtester** path (`engine.SimpleStrategy` via `build_payload`).

**Conclusion:** the common development loop (coarse-TF backtests) was already fast; **Axis B has now also
halved-to-two-thirds the fine-TF single-backtest cost**, byte-identical. What remains under the fine-TF time
is the shared Axis-A indicator compute (~flat ~15 s, already optimized) plus the per-trade event-assembly
loop — both lower-ROI and outside the engine. The original "hold the micro-opts" guidance (§7) still stands
for A3 / market_structure; the high-value Axis-B target the report flagged has been delivered.

---

## 6. The expansion lens — why "more complicated operations" flips the calculus

You told me the system is expanding to much more complicated operations. That single fact changes the
ranking of everything above:

- **It DEVALUES the remaining axis-A micro-steps (A3, market_structure).** They save ~0–3 s on coarse TFs
  *and* will need re-proving against new golden baselines after the expansion. Low ROI → negative ROI if done now.
- **It INFLATES the value of axis B (the per-decision loop).** More indicators / more per-bar logic / more
  instruments all pour straight into Clock B. A rewrite there compounds across every future strategy. **But**
  it must be done *on the new shape*, not the old one — so it is the right *target*, wrong *time*.
- **It makes the SAFETY NET the hero.** The golden/equivalence/parity harness is what lets you expand
  *without fear of silent result drift*. That is already built and is the thing to **carry forward and
  extend** as you add operations — far more valuable right now than any further micro-optimization.

> **Baby:** You're about to make the engine bigger and more complex. Don't polish the old small parts now —
> they'll be replaced or revalidated anyway. Instead, keep the safety harness on while you build the big new
> parts, and save the serious speed work for the new heavy part (Clock B) once it exists.

---

## 7. Recommendation — per item, explicit

| Item | Decision | Why |
|------|----------|-----|
| **Bank current state (D/A1/A2/E/C′)** | ✅ **KEEP — it's done, proven, committed** | −67% on coarse TFs, byte-identical, zero downside |
| **A3 (stochastic deque / mfi / adx)** | ⏸️ **HOLD** | not in the hot list; ~0–1 s; re-validation tax after expansion |
| **market_structure / structure_trend vectorization** | ⏸️ **HOLD** | high effort + high risk on core SMC for ~2–3 s; revalidate after expansion |
| **C (Numba)** | ⛔ **BLOCKED here** | no Py-3.14 wheel + PEP 668; revisit only on a controlled env/venv |
| **F (sampling-map cache)** | 🟡 **DO ONLY IF a large sweep is imminent AND sampling logic is frozen** | pure additive cache, low risk, high *sweep* ROI; otherwise hold |
| **Axis B (per-decision loop, fine TFs)** | 🎯 **DEFER, then prioritize — but AFTER the expansion lands** | the real prize; must be built on the new system shape, not the old |
| **Safety net (golden/equiv/parity)** | ✅ **CARRY FORWARD & EXTEND** | the asset that makes the expansion safe; add baselines for new operations |

**Net:** **import nothing further right now.** Resume optimization after the new operations are in place,
and at that point go straight for **F (if sweeping)** and **axis B**, re-freezing golden baselines first.

---

## 8. Safety / revert posture (unchanged, restated)

- All work is local on `dev`, **not pushed**. Nothing is exposed.
- Revert any single step: `git revert <sha>`. Hard-reset to pre-optimization: `git reset --hard f9d6f36`.
- The current checkpoint (`5d1945e`) is clean: 148 tests green, all golden vote-hashes byte-identical.
- Each step has its own `perf/UPDATE_step_*.md` with before/after + revert instructions.

---

## 9. One-paragraph executive summary

We have captured the large, durable speed win on the common path (coarse-TF backtests, 36.2 s → 12.1 s,
−67%), and proven it changes no results. What remains in the layer we optimized is small (~0–3 s of hard,
risky work that the hot-path profiler barely registers) and would have to be re-validated the instant the
system grows. The genuinely valuable future work lives in a *different* layer — the per-decision-bar loop
that dominates fine timeframes and the optimizer sweep cache — and that work should be done **on the new,
more-complicated system, not the current one**. Therefore the efficient choice is to **hold further
optimization now**, keep and extend the safety net through the expansion, and resume with a sharper, more
valuable target afterward.
