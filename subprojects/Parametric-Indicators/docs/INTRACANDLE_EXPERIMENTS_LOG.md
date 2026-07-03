# Intra-Candle Vetoed Entry — Master Experiment Log & Follow-On Checklist

*Verbose log of every experiment run for this feature, with implementation steps (files + commits) and full
results, plus the checklist of variants still to test so no promising path is left unexplored. Companion to
`INTRACANDLE_VETO_ENTRY_DECISIONS.md` (the design decisions) and `..._PHASE1_RESULTS.md` (the headline verdict).*

**The feature in one sentence:** when an indicator "judge" **vetoes** a trade setup, instead of throwing it away,
keep it on a sticky note and enter **part-way through the 4-hour candle** the moment the judges allow it.

**Baseline for every comparison — the current champion (feature OFF):**
**214 trades · $142,203 profit · max drawdown $14,082 · 69.2% win rate** (NQ 4h). Win ≈ +$2,400 (120-pt target),
loss ≈ −$3,340 (167-pt stop) ⇒ you must win ~**57.5%** of trades just to break even ("breakeven win rate").

---

## ★ Follow-on checklist — variants to test (so no probability is left untested)

| # | Experiment | What it tests | Status |
|---|---|---|---|
| **E1** | **Force-stop in-candle trades on a normal entry** (force-close) | Give the proven champion trades priority — a normal entry closes an open rescued trade | ✅ **DONE + OOS-validated** (see Exp. 4–6) |
| **E2** | **Re-optimize L1 with in-candle enabled** | Let the optimizer re-tune L1's stop/target + `N` + force-close *together*, with drawdown as an objective, so the extra entries come without the drawdown penalty | ⏳ **IN PROGRESS** (Phase 2c wiring → 2d server run) |
| **E3** | **L1 = exact current champion (in-candle OFF); optimize L2's OWN dedicated settings for the in-candle entries** | Keep the proven L1 champion untouched, and route the rescued in-candle (vetoed) entries into **Layer 2** with L2's *own* optimized stop/target/gate — so the rescued trades never disturb L1 and get handling tuned just for them | ⬜ **TODO** (new; aligns with L2 = manager of L1's dropped signals) |

**Rule for all optimization experiments (E2, E3):** whenever the in-candle feature is enabled, the **wait window
`N`** (how many 1-minute bars a vetoed signal may wait for its second chance) is **also a tunable search
dimension** — alongside force-close on/off and the stop/target settings.

---

## Experiment log (chronological, verbose)

### Exp. 1 — Naive "admit all" (rescued trade blocks normal entries), exact engine
**Purpose:** first measurement — bolt the feature onto the fixed champion, admit *every* vetoed vol-passed signal
whose gate re-opens, and sweep the wait window `N`.
**Implementation:** engine arming inversion (`engine.py`, invert the veto-abort into an arm) + per-1-min gate
(`indicators/runner.py intracandle_gate_arrays`) + pure resolver (`indicators/intracandle.py`) + study harness
(`research/intracandle/run_sweep.py`). TDD; default OFF ⇒ golden 6/6 byte-identical. Commits `61c0852` (engine),
harness commit, `7a3ff11` (verdict).

| N (wait bars) | total | net + | new (rescued) | win% of new | ≥57.5%? | median hold | total P/L | Δ vs champ | max DD |
|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|
| 30 | 322 | +108 | 129 | 50.4% | ❌ | 388m | $73,198 | −$69,005 | $34,553 |
| 60 | 348 | +134 | 160 | 54.4% | ❌ | 402m | $85,398 | −$56,805 | $27,109 |
| 120 | 369 | +155 | 191 | 54.4% | ❌ | 386m | $62,119 | −$80,084 | $31,389 |
| 240 | 384 | +170 | 214 | 57.0% | ❌ | 386m | $87,363 | −$54,840 | $34,434 |

**Went well:** ~2× entries (the mechanism works). **Went wrong:** rescued trades win 50–57% (**below** breakeven)
→ lose money on average; and they **displace profitable champion trades** ("steal the seat", one position at a
time) → total P/L falls $55–80k, drawdown ~3×. **Verdict:** bolt-on onto fixed params underperforms.

### Exp. 2 — Prior-art research (deep-research pass, cited)
**Purpose:** per the deep-research-first rule, mine documented delayed/conditional-entry results before deeper
work. **Result:** rigorous evidence is mixed-to-cautionary (a pullback/retest entry on MNQ won only 19%; a bare
delay destroyed a validated edge), BUT the *winning* variants used multi-condition armed entry (= our full gate),
and re-admitting rejected signals helps mainly by shrinking losers. Blog "confirmation improves win rate" claims
were refuted. Recorded in `INTRACANDLE_VETO_ENTRY_DECISIONS.md` §2.5. **Steered:** enter immediately (no pullback),
short waits, prove breakeven.

### Exp. 3 — Force-close, first cut (buggy)
**Purpose:** test idea E1 — a normal entry force-closes an open rescued trade. **Implementation:** engine
`FORCE_CLOSE` exit + `intracandle_force_close` flag; strategy/harness threading. Commit (force-close variant).
**Result (N=240):** 409 trades, $109,456 (−$32,747 vs champ), 27 force-closes — recovered ~$22k vs Exp. 1. But two
bugs (below) understated it.

### Exp. 4 — Force-close, CORRECTED (the breakthrough)
**Purpose:** fix two bugs found while porting to the fast engine (Exp. 7). **Bugs fixed:** (1) force-close must run
**before** the candle's exit walk (the boundary preempts a mid-candle stop/target of the rescued trade);
(2) "a normal entry qualifies" must use the **full** champion gate (vol ∧ ¬veto ∧ **confirm**), not just
vol ∧ ¬veto. Applied to both engines + `build_payload` (new `intracandle_normal_gate`). Commit `fa6e886`.

| Version (fixed champion params, N=240) | trades | total P/L | vs champion | force-closes |
|---|--:|--:|--:|--:|
| champion (off) | 214 | $142,203 | — | — |
| plain (Exp. 1) | 384 | $87,363 | −$54,840 | — |
| force-close first cut (Exp. 3) | 409 | $109,456 | −$32,747 | 27 |
| **force-close corrected (Exp. 4)** | **423** | **$143,657** | **+$1,454** | 43 |

**Went well (headline):** ~**2× entries (214 → 423) at slightly ABOVE the champion's profit**, on fixed params,
before any re-optimization. The whole problem was "stealing the seat"; giving proven trades priority flips the
feature from −$55k to +$1.5k.

### Exp. 5 — Out-of-sample (2025 train / 2026 test) + drawdown, force-close
**Purpose:** is Exp. 4 real or in-sample luck? Split by year (feature has no tuned params, so this is a fair OOS
read). Commit `617149d`.

| | champion (off): n / P/L / maxDD | force-close (on): n / P/L / maxDD |
|---|--:|--:|
| ALL | 214 / $142,203 / $14,082 | 423 / $143,657 / **$24,902** |
| 2025 (in-sample) | 157 / $113,304 / $10,505 | 292 / $109,356 / $22,726 |
| **2026 (out-of-sample)** | 57 / $28,899 / $14,082 | **131 / $34,301 / $18,511** |

**Went well:** the feature **holds out-of-sample** — 2026 (unseen) shows **2.3× entries and +19% profit** ($34,301
vs $28,899); in-sample 2025 was slightly *lower*, so this is the opposite of over-fitting. **Went wrong:**
**drawdown roughly doubles** (P/L-to-drawdown ratio ~10:1 → ~6:1), degrading the ratio L1 is valued for.
**Verdict:** real and OOS-validated on entries + P/L; drawdown is the one thing re-optimization must control.

### Exp. 6 — Dashboard toggle (usability)
Checkbox + `N` box under the L1 exit-cap control; default OFF ⇒ reproduces the champion. `server.py` forwards
params verbatim. Commit (dashboard toggle).

### Exp. 7 — Fast-engine port + trade-for-trade parity (Phase 2a + 2b)
**Purpose:** the optimizer uses a separate ~200× faster engine with no intra-candle logic. Port the feature there
so the optimizer can search it. **Implementation:** `optimize/fast_engine.py` gains the intra-candle args +
entry/force-close logic; parity locked in `optimize/test_intracandle_parity.py`. Commits `77b3fc9` (2a), `fa6e886`
(2b).

| check | result |
|---|---|
| fast vs exact, feature OFF | 214 == 214, **0 mismatch** ✅ |
| fast vs exact, feature ON | 423/384 == 423/384, **0 mismatch** ✅ |
| force-close, fast vs exact | **0 mismatch** ✅ (after the two Exp. 4 fixes) |
| golden 6/6 (feature off) | byte-identical ✅ |
| existing FAST-PARITY (11 cases) | unchanged ✅ |

**Went well:** the optimizer's fast engine now supports the feature with proven correctness. **Flagged for E2:**
building the per-minute gate computes Smart-Money indicators over the *entire* 1-minute series (~50s/config); the
normal optimizer shortcut (compute only at candle boundaries) can't be used, so a naive per-trial gate would make
a full search take days — **Task 2c must cache/speed this up first.**

---

## Summary so far

The feature is **built, tested, OOS-validated, and safely off-by-default** (golden 6/6). The force-close variant
(E1) already delivers **~2× entries at ≥ champion profit, holding out-of-sample** — the milestone — with the sole
caveat that **drawdown ~doubles**. E2 (re-optimize L1) and E3 (dedicated L2 layer) are the two ways to keep the
entries + profit while controlling drawdown, and both must treat `N` (and force-close) as tunable dimensions.
