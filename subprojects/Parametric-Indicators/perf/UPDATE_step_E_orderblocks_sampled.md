# Update Report — Phase 3 · Step E: `order_blocks` sampled-overlap

**Date:** 2026-06-11 · branch `dev` · task #210 · **the big 4h win**
**Type:** speed only — **results byte-identical** (golden vote-hash unchanged).

---

## 0. Investigation that preceded this (Option B debunked)
The original plan listed **B — de-duplicate the SMC compute** as a ~9 s win. Profiling the call sites
showed that was a **misread**: `order_blocks` runs **once** on the 1-minute frame (~15 s, necessary) and
once on the decision frame (~0.05 s, for the dashboard report). De-dup saves ~0.05 s → **B dropped.** The
real lever is making the single expensive 1-minute `order_blocks` cheaper — this step.

---

## 1. What changed (plain + professional)

**Professional.** `order_blocks` walks the 1-minute series maintaining live supply/demand zones; at each
bar it (a) updates state — swings, breaks, pruning — and (b) computes a per-bar "in-a-zone" overlap
signal by scanning the live-zone list. In the 1-minute regime, that output is **sampled at only ~one bar
per decision bar** (e.g. ~2,119 of 486,969). Step E adds an optional `signal_at=<indices>`: the **state
still advances every bar** (so the values are unchanged), but the **overlap signal is computed only at the
bars that will actually be read.** The other ~99.5% of bars are left 0 and never read.

**Baby.** The hard chapter still has to be read in order page-by-page (the zones must update every
minute). But we were also *writing a summary on every page* when the teacher only ever reads ~1 page in
240. Now we update our notes every page but only write the summary on the pages that get graded. Same
grades, far less writing.

---

## 2. Before / after

| | Before | After |
|---|---|---|
| `order_blocks` (swing_l 10) on 486,969 bars, 1-min vote path | **16.75 s** | **9.90 s** → **1.7×** |
| `order_blocks(signal_at=None)` (decision-TF path) | reference | **bit-identical** (unchanged) |
| **4h full backtest** | 25.6 s (after A2) | **16.5 s** — and **36.2 s → 16.5 s vs baseline (−54%)** |

---

## 3. Why it's exact (the key argument)
The per-bar overlap value at bar `t` depends only on the **zone state at `t`**, which is built by the
sequential updates that still run on **every** bar. Skipping the overlap *computation* at a bar we never
read cannot change any value we *do* read. Proven two ways:
- unit: `order_blocks(signal_at=S)[S] == order_blocks_ref()[S]` for arbitrary S (empty/all/sparse/
  clustered/endpoints), and unsampled bars are exactly 0;
- integration: the **golden order_block vote-hash is byte-identical** on 4h/2h/1h (the vote samples
  exactly those indices).

The decision-TF path and the optimiser/parity tests pass `signal_at=None` ⇒ full computation ⇒ unchanged.

---

## 4. Code touched / links (narrow blast radius — capability flag, not a broad interface change)

| File | Change |
|------|--------|
| `indicators/smc.py` (`order_blocks`) | + optional `signal_at`; gate the overlap signal by a `want[t]` mask; state loop unchanged |
| `indicators/_reference.py` | + frozen `order_blocks_ref` (original full loop) — the spec |
| `indicators/library.py` (`OrderBlock`) | `_supports_signal_at=True`; `stance(ctx, signal_at)` + `directions(ctx, signal_at)` forward it |
| `indicators/runner.py` (`_vote_from_1min`) | if `ind._supports_signal_at`, pass `signal_at=j_idx[j_idx>=0]` (the sampled 1-min indices) |
| `tests/test_speedopt_equiv.py` | full==ref (size×swing_l) + sampled[S]==ref[S] across S shapes |

No other indicator is touched; non-OrderBlock indicators are called exactly as before.

---

## 5. Verification evidence (all green)

| Gate | Result |
|------|--------|
| Equivalence (full==ref; sampled[S]==ref[S]; unsampled==0) | ✅ 21 passed |
| Real-1m bit-check | ✅ `full==ref` and `sampled[S]==ref[S]` |
| order_blocks micro-benchmark | ✅ 1.7× (16.75 s → 9.90 s) |
| `optimize/test_parity.py` (signal_at=None path) | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **148 passed** (127 prior + 21 new) |
| Golden byte-match 4h/2h/1h (incl. **order_block vote-hash**) | ✅ ALL MATCH |

---

## 6. Reverting Step E
```bash
git revert --no-edit <STEP_E_COMMIT>     # undo just E (keeps D/A1/A2)
git reset --hard f9d6f36                 # or hard-reset to the Phase-0 rollback point
```
`order_blocks_ref` preserves the original for diffing even after revert.

## 7. Status
- ✅ Step E complete, committed, results byte-identical. **4h: 36.2 s → 16.5 s (−54%).**
- Remaining order_blocks cost ≈ 9.9 s is now the **state/pruning loop** (Python `for` over 486,969 bars +
  per-bar list pruning) — only **Numba (C)** or a numpy-zone rewrite shrinks that further.
- ▶️ Next candidates: A3 (finish classics, exact stochastic deque) or Phase 2 **C — Numba** the SMC
  state loop (biggest remaining lever). Pending approval.
