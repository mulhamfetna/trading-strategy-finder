---
name: engine-edits-report
description: Full report of every edit made to the trading engine for the meta-prophet research — what changed, why, what it affects, how, and why it's safe. Headline - the original team-leader-verified engine (src/strategy/simple_strategy.py) was NEVER modified; all changes live in a separate, parity-tested CLONE that adds exactly two optional levers (sl_tp_mult, entry_gate). Technical deep-dive + baby-language version + the exact diff + the proof.
type: reference
---

# Trading-engine edits — full report (for the team-leader review)

> **The one sentence that matters:** the engine you verified with the team leader —
> `src/strategy/simple_strategy.py` — **was not touched at all.** Every research change lives in
> a **separate copy** (`subprojects/meta-prophet/engine_clone/simple_strategy_adaptive.py`) that
> adds **exactly two optional knobs**, both of which are **off by default**, and which a test
> proves leave the behaviour **identical to the verified engine** when off.

---

## 1. TL;DR (read this first)

| Question | Answer |
|---|---|
| Was the verified production engine changed? | **No.** `src/strategy/simple_strategy.py` is byte-for-byte the version the team leader verified (git clean; last commit `d154929`, predates this research). |
| Where are the changes, then? | In a **clone**: `subprojects/meta-prophet/engine_clone/simple_strategy_adaptive.py` — a separate file, used only by the offline research. |
| What exactly was added to the clone? | **Two optional, default-`None` parameters** on `backtest()`: `sl_tp_mult` (scale the stop/target distances per bar) and `entry_gate` (skip entering on chosen bars). Plus docstring text. **Nothing else.** |
| When both are unused? | The clone behaves **identically** to the original — proven by `tests/test_clone_parity.py` (**PASSES**, 1 test). |
| Did this session change any engine? | **No.** This session only *used* the clone; the two levers were added in an earlier phase (EXP-G2). The exit logic, entry logic, look-ahead protection, position size (1 contract), and the flip system are **unchanged**. |

---

## 2. Where everything lives

```
src/strategy/simple_strategy.py                                  ← VERIFIED original. UNTOUCHED.
subprojects/meta-prophet/engine_clone/simple_strategy_adaptive.py ← the clone (original + 2 levers)
subprojects/meta-prophet/tests/test_clone_parity.py               ← proves clone == original (levers off)
```

The clone was made by copying the original verbatim, then adding the two levers. It is **only**
imported by the research scripts (`17_backtest_matrix.py`, `44`, `45`, `18_dashboard_export.py`).
The live system never imports it.

---

## 3. The EXACT diff (original → clone)

This is the complete set of code differences (from `diff`). There are only four hunks:

**(a) Two new optional parameters on `backtest()`** (everything else in the signature is identical):
```python
        sl_tp_mult: Optional[np.ndarray] = None,
        entry_gate: Optional[np.ndarray] = None,
```

**(b) Docstring** explaining them (no behaviour).

**(c) The entry gate** — inserted right after the signal is decided, before a trade opens:
```python
        # ADAPTIVE-CLONE: regime gate. Skip entry on gated-out bars.
        if entry_gate is not None and 0 <= idx < len(entry_gate) and not bool(entry_gate[idx]):
            continue

        # ADAPTIVE-CLONE: per-bar SL/TP multiplier (1.0 => original).
        _m = 1.0
        if sl_tp_mult is not None and 0 <= idx < len(sl_tp_mult):
            _mv = float(sl_tp_mult[idx])
            if np.isfinite(_mv) and _mv > 0:
                _m = _mv
```

**(d) The multiplier `_m` applied to all four exit distances** (the only change to the trade-opening math):
```python
    # long:                                   # original had no "* _m"
    sl_soft_line = close - self.params.sl_soft_points * _m
    sl_hard_line = close - self.params.sl_hard_points * _m
    tp_soft_line = close + self.params.tp_soft_points * _m
    tp_hard_line = close + self.params.tp_hard_points * _m
    # short: the mirror, also each distance * _m
```

That is the entire edit. **No change to the exit walk, the soft/hard fill rules, the look-ahead
guard, the flip logic, or the trade bookkeeping.**

---

## 4. Technical deep-dive — what each lever does, how, why

### 4.1 `sl_tp_mult` — per-bar stop/target scaler
- **What:** an optional array, one number per 4-hour bar. At the bar where a trade opens (`idx`),
  the engine reads `_m = sl_tp_mult[idx]` (guarded: must be finite and > 0, else `_m = 1.0`).
- **How:** it multiplies **all four** stop/target distances (`sl_soft`, `sl_hard`, `tp_soft`,
  `tp_hard`) by the same `_m` at entry. So with `_m = 1.5`, every line sits 50 % farther from the
  entry price; with `_m = 0.5`, half as far. The lines are still placed relative to the entry
  close exactly as before — only the *distance* is scaled.
- **Why multiply ALL FOUR by the SAME factor (this is the safety-critical design choice):** the
  engine enforces ordering constraints `sl_hard ≥ sl_soft` and `tp_hard ≥ tp_soft`. Multiplying
  every distance by one positive number **cannot break that ordering** (scaling preserves
  inequalities), so no constraint check can fail and the exit logic needs no changes. A
  per-line or asymmetric scaler *could* invert the ordering — that's why it was deliberately
  avoided.
- **Effect on results:** wider stops (`_m > 1`) → fewer stop-outs, bigger wins/losses; tighter
  (`_m < 1`) → more stop-outs, smaller per-trade swings. It changes *which exit fires and at what
  price* for each trade, hence P/L. It does **not** change which bars trade, nor the contract size.
- **Off switch:** `None` (or all-`1.0`) → every `_m = 1.0` → the `* _m` is a no-op → identical to
  the original.

### 4.2 `entry_gate` — per-bar "trade or sit out" switch
- **What:** an optional boolean array, one flag per 4-hour bar.
- **How:** after the signal is computed for a bar, if `entry_gate[idx]` is `False`, the engine
  `continue`s — **no new trade opens on that bar.** A bar that *is* allowed behaves exactly as
  before.
- **Why:** lets the research "sit out" chosen bars (e.g. the most volatile/dangerous ones) without
  altering any trade that does open.
- **Effect on results:** reduces the number of trades (and removes their P/L); every surviving
  trade is byte-for-byte what the original would have produced. It does **not** modify open trades,
  exits, or size.
- **Off switch:** `None` → the gate check is skipped entirely → identical to the original.

### 4.3 Causality (no look-ahead)
The engine simply reads `array[idx]` for the current bar — it never peeks at future bars. The
*arrays themselves* are built causally by the research (the HAR volatility forecast uses only past
bars; the gate threshold is fixed on 2025/train data). So enabling the levers preserves the
original engine's strict no-look-ahead property (the look-ahead guard from commit `601efb2` is
untouched).

---

## 5. Why these edits were made (the research motivation)
The meta-prophet study found that **price is unpredictable but volatility is predictable**. To
*test* whether a volatility forecast can improve risk-adjusted results, we needed to (a) make stops
breathe with predicted volatility (`sl_tp_mult`) and (b) skip the most volatile bars
(`entry_gate`). Doing this on the live engine would have put unverified research behaviour into the
production path. Instead we **cloned** the verified engine and added only these two switches, so:
- the verified engine stays pristine for the team,
- the research is fully isolated and reproducible,
- and the clone can be proven equivalent to the original whenever the switches are off.

(The **single-contract** rule is preserved: neither lever changes contract count — that's why the
position-sizing idea was deliberately *excluded*. And the **flip** toggle used in Workstream G is
*not* a clone addition — `flip_entry_direction` already exists in the verified original, commit
`d154929`.)

---

## 6. Why it's safe — the proof
- **Parity test:** `tests/test_clone_parity.py` runs both engines on the real data with the levers
  off and asserts **identical trades and P/L**. It **PASSES** (`1 passed in 3.52s`). So "levers off
  ⇒ same as verified engine" is not a claim, it's a checked fact.
- **Default off:** both parameters default to `None`; any existing caller gets the original behaviour.
- **Minimal surface:** the diff is 4 small hunks, all additive; no original line of logic was
  rewritten except appending `* _m` (a no-op when `_m == 1`).
- **Original untouched in git:** `git status` shows `src/strategy/simple_strategy.py` clean.

---

## 7. Baby-language version

Think of the trading engine as a **recipe** the team leader already approved. We did **not** edit
that recipe. We **photocopied** it and, on the photocopy only, added **two optional dials**:

1. **A "stop-distance" dial (`sl_tp_mult`).** Normally the safety net and the profit target sit a
   fixed distance from where we bought. This dial lets us move *both* the net and the target
   farther out or closer in — together, by the same amount — depending on how stormy the market is
   expected to be. Turn the dial to "1" (the default) and it's exactly the original recipe. We move
   all the lines by the *same* amount on purpose, so the "net must be at least as far as the soft
   net" rule can never get broken.

2. **A "skip this bar" switch (`entry_gate`).** For each 4-hour candle we can say "don't take a
   trade here" (e.g. skip the wildest, most dangerous moments). If we don't flip the switch, every
   trade is exactly what the original would have done.

Both dials start in the "do nothing" position. We even ran a checker that proves: **with the dials
off, the photocopy gives the *exact same trades and profit* as the approved recipe.** So the team
leader's verified engine is safe and unchanged; the photocopy with dials is only used for
experiments, off to the side.

---

## 8. What did NOT change (so the team can be sure)
- Entry rule (Stage-1 signal, from the just-closed bar — no look-ahead). **Unchanged.**
- Exit model (soft/hard SL + soft/hard TP, the 2-consecutive-1-min-close soft rule, hard-on-touch).
  **Unchanged.**
- The flip-entry-direction mirror system. **Unchanged** (and it's original, not a clone addition).
- Position size = **1 contract**. **Unchanged.**
- 1-minute sub-bar exit search and tie-break priority. **Unchanged.**
- The original file `src/strategy/simple_strategy.py`. **Untouched.**

---

## 9. One-paragraph summary
For the research we never edited the team-leader-verified engine
(`src/strategy/simple_strategy.py`); we made an isolated **clone** and added exactly **two optional,
default-off knobs**: `sl_tp_mult`, which scales all four stop/target distances of a trade by one
positive per-bar number (so it can widen/tighten stops with forecast volatility without ever
breaking the stop-ordering rules), and `entry_gate`, a per-bar on/off switch that lets the strategy
skip entering on chosen bars (e.g. the most volatile ones) without altering any trade that does
open. Both default to "do nothing", neither changes the 1-contract size or any exit/entry/look-ahead
logic, and a parity test proves that with the knobs off the clone produces identical trades and P/L
to the verified engine. These knobs exist purely so the volatility research (Workstream G) could be
tested in isolation; the production engine the team approved is unchanged.
