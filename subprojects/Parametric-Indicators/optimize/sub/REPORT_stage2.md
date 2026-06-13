# Sub-Optimizer — Stage 2: three dynamic-SL/TP rules, out-of-sample vs the fixed champion

**Date:** 2026-06-13 · branch `dev` · runner `optimize/sub/stage2.py`
**Setup:** dynamic SL/TP = a per-4h-bar multiplier on the champion's base SL/TP via the engine's `sl_tp_mult`
hook (SL & TP scale together; shape = champion's). Rules fit on **TRAIN 2024-01…2025-06**, judged on
**TEST 2025-07…2026-05** vs the fixed champion on the same TEST window.
**Correctness:** parity anchor passes — `mult≡1` reproduces the fixed champion exactly
(**$108,748 / 342 trades** over the full 29mo; dyn == core). So the engine path is exact.

---

## 1. Out-of-sample results (TEST window)

| rule | P/L | maxDD | n | win% | DD/PL | ret/DD | vs fixed |
|------|----:|------:|--:|-----:|------:|-------:|---------:|
| **fixed champion** | $67,627 | $16,204 | 122 | 67.2 | 24% | 4.17 | — |
| **opt1 — ATR-multiple** | $62,001 | **$11,057** | 141 | **70.2** | **18%** | **5.61** | −$5,626 |
| opt2 — robustified | $57,514 | $30,975 | 110 | 65.5 | 54% | 1.86 | −$10,113 |
| opt3 — aggregate | **$111,464** | $55,748 | 61 | 68.9 | 50% | 2.00 | +$43,837 |

Rule fits: opt1 `a=0.60, ATR_ref=133`; opt2 `scale≈+9.7e-03·ATR−0.22`; opt3 `scale≈+6.9e-03·ATR+1.82`.

---

## 2. The honest verdict (drawdown-aware — this is the *drawdown-capped* strategy)

Raw P/L alone is **the wrong yardstick** here: the strategy's identity is its **drawdown discipline**
(selected under DD ≤ 25 % of P/L). Reading the table through that lens:

- **opt3 (aggregate) has the highest P/L (+65 %) but BREACHES the risk budget** — its fit clips to ~3× SL/TP
  (much bigger bets), giving **50 % DD/PL (2× the 25 % budget)** on only **61 trades (half the count)**. That's
  not a better strategy, it's a **higher-risk regime**; for a drawdown-capped system it's a disqualifier, and
  on 61 trades it's fragile.
- **opt2 (robustified) is worst** — higher DD (54 % DD/PL), lower P/L. The "robust" narrow-scale fit didn't help.
- **opt1 (ATR-multiple) is the only dynamic rule that stays within the 25 % DD budget (18 %)** and is the
  **best risk-adjusted (ret/DD 5.61 vs fixed 4.17)** — it cut drawdown by **−32 % ($16.2k→$11.1k)** and raised
  win-rate (+3 pts), for a small P/L give-up (−8 %).

> **So "the best" depends on the objective:**
> - **Most raw P/L:** opt3 — but it breaks the drawdown budget (not a clean win). ❌ for this strategy.
> - **Best risk-adjusted / within budget:** **opt1 (ATR-multiple)** — lower DD, higher win-rate, ret/DD beats
>   fixed; but it does **not** beat fixed on P/L. ✔ defensible, as a *risk-reduction* choice.
> - **Do nothing:** the **fixed champion remains competitive** ($67.6k, 24 % DD/PL).

**Recommendation:** **none of the three is a clear winner that beats fixed on P/L while respecting the
drawdown budget.** opt1 (ATR-multiple) is the only sound dynamic candidate and is attractive *for lower
drawdown*, not higher return. I would **not ship opt3** (breaks the DD discipline). If the goal is "more
return," the data does not support a dynamic SL/TP rule that delivers it safely.

---

## 3. Caveats (why this isn't conclusive)
- **Single train/test split**, TEST n = 61–141 trades → limited statistical power; opt3's edge especially is
  driven by a handful of big trades after 3× clipping.
- Consistent with **Stage 1**: the per-window optima carried little signal, so the fit-based rules (opt2/opt3)
  inherit that noise; only the theory rule (opt1, ATR-multiple) behaves sensibly.
- `sl_tp_mult` scales SL & TP **together** (single factor) — independent SL/TP scaling (engine extension) was
  not tested (Stage-1 showed SL & TP don't co-move cleanly, so it's unlikely to help without more data).

---

## 4. Suggested next step (your call)
1. **Adopt opt1 (ATR-multiple) for drawdown reduction** — re-validate first over **multiple rolling
   train/test splits** + a **DD-constrained objective** before shipping (it's a risk trade, not a P/L win).
2. **Keep fixed** — simplest; it already respects the budget and the dynamic rules don't safely beat it.
3. **Defer** dynamic SL/TP until more out-of-sample data accumulates (the signal is currently too weak).

My recommendation: **(2) keep fixed for now**, with **opt1 as the documented fallback** if drawdown becomes
the priority — and only after multi-split re-validation. Do **not** adopt opt3.

---

## 5. Artifacts
- `optimize/sub/stage2.py` — the harness (3 rules + risk-aware verdict; parity-anchored at mult≡1).
- TEST/TRAIN split, ATR(14) on the 4h frame, freeze-once champion layer (reused from Stage 1).
