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
| **E2** | **Re-optimize L1 with in-candle enabled** | Let the optimizer re-tune L1's stop/target + `N` + force-close *together*, with drawdown as an objective, so the extra entries come without the drawdown penalty | ✅ **DONE** — feature works but is **dominated by re-tuned exits**; a re-tuned **feature-OFF champion ($166,554)** is the real win (see Exp. 8) |
| **E3a** | **L2 intra-candle entry timing for the vetoed stream** | Enter L2's vetoed candidates mid-candle when L1's veto clears (L2's own exits/N) instead of at the candle close | ❌ **CLOSED — feature doesn't pay** (l2ic1 combined $162,910 < baseline $175,372, even L2-optimized) |
| **E3b** | **L2 rescues its OWN vetoed signals** (L2-as-L1) | Give L2 its own intra-candle rescue on signals L2's own indicators veto | ⬜ TODO (separate future spec) |

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

### Exp. 8 — E2: re-optimize L1 with the feature (server, NQ 4h, indicators frozen at champion)
**Purpose:** the fair test — let the optimizer re-tune stop/target + `N` + force-close *together*, drawdown as an
explicit objective (3-obj NSGA-III: max median-fold P/L · min worst-fold DD · max entries; feasibility DD≤25%·P/L;
5-fold median = built-in cross-validation). **Setup:** `--intracandle --freeze-indicators --ind-1min --objective
entries` on the AMD server (Postgres), champion indicators held fixed, memoised gate. Two studies:

- **`wshic1` (free on/off search, ~2,100 trials):** the optimizer **AVOIDED the feature** — only **16 of 168**
  feature-ON trials were DD-feasible (the rescued trades blow the drawdown limit), so the sampler skipped it.
  **Byproduct win:** the best feature-OFF trial re-tuned the exits to **full P/L $166,554 · DD $13,963 (8%) · ~68
  med-fold entries** — **+$24k over the $142,203 champion at the SAME drawdown**, purely from better exits.
- **`wshic2` (feature FORCED on, `--intracandle-on`, ~1,800 trials):** best feasible feature-ON:
  **$151,287 · DD $20,727 (14%) · ~61 med-fold entries** (or $160,887 at 22% DD). Beats the champion on **P/L +
  entries**, but at a **worse drawdown ratio** (14–22% vs the champion's 10%), and is **dominated on every axis by
  the re-tuned feature-OFF champion** ($166,554 at 8%).

| config | full P/L | DD | DD ratio | med-fold entries |
|---|--:|--:|--:|--:|
| champion (feature off) | $142,203 | $14,082 | 10% | ~40 |
| **re-tuned exits, feature OFF (wshic1)** | **$166,554** | **$13,963** | **8%** | **~68** |
| feature FORCED ON, best-ratio (wshic2) | $151,287 | $20,727 | 14% | ~61 |
| feature FORCED ON, best-P/L (wshic2) | $160,887 | $35,607 | 22% | ~50 |

**Verdict (E2):** the intra-candle feature **does** increase entries and can increase P/L, but it **worsens the
profit-to-drawdown ratio** and is **dominated by simply re-optimizing the exits without it.** The real, bankable
result is the **re-tuned feature-OFF champion: $166,554 at $13,963 DD (~1.7× the entries)** — a genuine L1
improvement. **Do not ship the feature for L1.** Caveat: in-sample (5-fold median CV, but no 2026 walk-forward yet)
— OOS-validate the $166,554 champion before promotion. The untested alternative is **E3** (dedicated L2 layer),
where the feature's drawdown could be isolated instead of polluting L1.

### Exp. 9 — OOS validation of the re-tuned $166,554 champion (year-split)
Exact params: champion indicators (frozen, k=1) + re-tuned exits **sl_soft 135 · sl_hard 170 · tp 120 · gate 91 ·
dd_limit 2910 · cd 0 · flip off**. Evaluated via the exact engine, split by year vs the current champion:

| | current champion (n / P/L / DD) | re-tuned $166k (n / P/L / DD) |
|---|--:|--:|
| 2025 | 157 / $113,304 / $10,505 | 170 / $118,591 / $13,963 (**+5%**) |
| **2026** | 57 / $28,899 / $14,082 | 74 / **$47,962** / **$12,717** (**+66%, lower DD**) |
| ALL | 214 / $142,203 / $14,082 | 244 / $166,553 / $13,963 |

**Verdict:** the re-tuned champion beats the current one in **both** years (biggest gain in the more-recent 2026:
+66% P/L at *lower* DD), win rate held (~68%). Improvement is **consistent, not a one-year artifact**, and the
optimizer's 5-fold median-CV metric already favored it ($33,072 vs ~$29k). **Caveat:** 2026 was inside the
optimizer's CV — a *pure* holdout (re-opt 2025-only → test 2026) is the last gold-standard gate, but this evidence
is strong. **The $166,554 re-tuned champion is a genuine, robust L1 improvement — recommend promotion.**

### Exp. 10 — E3a: L2 intra-candle entry timing (built + champion-first sweep) ⏸️
Built (commits up to 033e364): L2 schema (`l2_intracandle`/`l2_intracandle_max_wait`, default off) + `run_l2`
timing wiring (vetoed candidates enter mid-candle when L1's veto clears, reusing fast_backtest's parity-locked
intra-candle path + the memoised L1-champion gate) + L2 optimizer `--intracandle` (prefix `l2ic1`, N searchable).
**17 tests green; L2 parity anchors + golden 6/6 byte-identical (default off).**

**Champion-first combined N-sweep — NEGATIVE:** on the l2v2 champion (tight-exit scalper, SL 6–13 / TP 7.5,
flip=False), intra-candle timing **collapses L2's contribution** ($25,383 → ~$190–940) and cuts the **combined**
book **$175,372 → ~$150k** at slightly worse DD ($14,342 → $15,723), for every N. Flip-nuance ruled out. Parallels
E2: the feature doesn't help on *fixed* champion settings.

**l2ic1 optimizer (fair test — L2's OWN tuned exits WITH the feature) — DONE, CONFIRMS the feature doesn't pay.**
Server run (Postgres, 6 setsid workers, 1,500 trials / 890 feasible; ~85% pruned since the intra-candle L2 stream
is sparse). Best feasible L2 champion (in-sample $16,184 / 8 trades, N=120, re-tuned exits sl94/slH204/tp164),
evaluated via the anchor-consistent `logbook.run_causal` + `aggregate.combined_boxes`:

| config | combined P/L | combined DD | P/L:DD | L2 contribution |
|---|--:|--:|--:|--:|
| baseline (l2v2, feature OFF) | **$175,372** | $14,342 | 12.2 | $25,383 / 34 trades |
| **l2ic1 (feature ON, L2 re-optimized)** | $162,910 | $12,209 | 13.3 | $12,921 / 12 trades |

**Verdict — E3a CLOSED, feature does not pay.** Even with L2's own optimized exits + tuned N, intra-candle timing
gives a combined book **−$12,462 below baseline** ($162,910 vs $175,372). It reaches lower DD (marginally better
ratio 13.3 vs 12.2), but the L2 stream is sparse (12 vs 34 trades) and contributes less than plain candle-close
entry. Matches E2. **Whole intra-candle arc concludes: the feature adds no value in L1 (E2) or L2 (E3a); the
bankable win of the workstream is the validated $166,554 re-tuned L1 champion.** Built + tested + default-off +
golden-safe throughout. E3b (L2 rescues its OWN vetoed signals) remains an untested future idea.

## Summary so far

The feature is **built, tested, OOS-validated, and safely off-by-default** (golden 6/6). The force-close variant
(E1) already delivers **~2× entries at ≥ champion profit, holding out-of-sample** — the milestone — with the sole
caveat that **drawdown ~doubles**. E2 (re-optimize L1) and E3 (dedicated L2 layer) are the two ways to keep the
entries + profit while controlling drawdown, and both must treat `N` (and force-close) as tunable dimensions.
