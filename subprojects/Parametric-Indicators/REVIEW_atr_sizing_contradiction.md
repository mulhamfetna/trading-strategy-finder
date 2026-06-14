# Review — "ATR increases PnL" (dashboard) vs "ATR shrinks PnL" (study): which is right & why

**Date:** 2026-06-14 · **Scope:** the new dashboard ATR-multiplier backtester feature
(`strategy.py build_payload`) vs the dynamic-SL/TP study (`optimize/sub/stage2.py`,
`vol_source_compare.py`, `STUDY_sub_optimizer_*.md`). **Method:** systematic-debugging
(root-cause first), every claim reproduced below.

---

## 0. TL;DR — both numbers are real; they measure two different rules on two different datasets

- The study said: **ATR sizing does not beat fixed on profit; it's a drawdown-reducer; 4h-ATR
  was a better driver than 1-min in the shrink-only band.**
- The dashboard shows: **1-minute ATR (defaults) = +21% PnL vs fixed; 4h ATR = −13% PnL.**

**Neither is a code bug in the engine** (fixed mode is byte-identical to golden — re-verified).
The apparent contradiction is fully explained by **the dashboard's permissive DEFAULTS**, which are
*not* the rule the study evaluated:

| lever | study (deployable / honest) | dashboard default | effect of the default |
|------|------------------------------|-------------------|-----------------------|
| **clip band** | `0.33–1.05` (shrink-only) | **`0.30–3.00`** (3× expansion) | lets SL/TP blow up to 3× on vol spikes |
| **1-min ATR period** | `240` (≈ one 4h bar) | **`14`** (= 14 *minutes*) | a noise-period vol estimate |
| **normalization ref** | `mean(ATR over TRAIN)` | **`mean(ATR over FULL series)`** | look-ahead (small, ~6%) |
| **coefficient** | `a` fitted on train (≈0.60) | `atr_mult = 1.0` | different rule entirely |
| **window** | OOS test (> 2025-06) | **full** (all in-sample) | in-sample overstates |
| **data span** | 2024-01 → 2026-05 (3663 bars) | **2025-01 → 2026-05** (2119 bars) | different universe |

**When you put the dashboard ON the study's config, the study's conclusion reappears** (numbers below):
1-min ATR drops *below* fixed, and 4h ATR is ≤ fixed everywhere. **The two systems agree once the
variables are controlled.** The "+21%" is an in-sample, expansion-band, 14-minute-period artifact.

---

## 1. The evidence (all reproduced via `build_payload`, champion `wsi1m_4h`)

### 1a. Dashboard FULL window (2025-01→2026-05, in-sample)
| config | PnL | maxDD | n | win% | mult median (range) |
|--------|----:|------:|--:|-----:|---------------------:|
| **fixed** | **142,203** | **14,082** | 214 | 69.2 | — |
| atr 4h · mult1.0 · clip 0.3–3.0 · p14 *(DEFAULT)* | 123,715 | **30,718** | 216 | 68.1 | 0.94 (0.44–3.00) |
| atr 1m · mult1.0 · clip 0.3–3.0 · p14 *(DEFAULT)* | **172,747** | 20,680 | 226 | 69.9 | 0.64 (0.30–3.00) |
| atr 4h · clip **0.33–1.05** · p14 | 131,317 | 14,795 | 224 | 68.8 | 0.94 (0.44–1.05) |
| atr 1m · clip **0.33–1.05** · p14 | **92,394** | 15,099 | 250 | 66.8 | 0.64 (0.33–1.05) |
| atr 1m · clip 0.3–3.0 · **p240** | 159,395 | 18,945 | 227 | 70.9 | 0.87 (0.30–3.00) |
| atr 1m · clip **0.33–1.05** · **p240** | 143,968 | 14,036 | 234 | 70.5 | 0.87 (0.33–1.05) |

Read it:
- **4h ATR never beats fixed** (124k or 131k < 142k) — direction matches the study.
- **1-min "+21%" (172k) is the joint effect of the 14-minute period AND the 3× band.**
  - Restore the study band (1.05) at p14 → **collapses to 92k (−35%)**.
  - Restore the study period (240) → with band 3.0 = 159k, with band 1.05 = **144k ≈ fixed**.
  - i.e. moving from dashboard-default (p14, clip3.0 → 172k) to study-config (p240, clip1.05 → 144k)
    **erases almost the entire surplus** and lands on top of fixed.

### 1b. Dashboard OOS window (2026 only — the closest match to how the study evaluated)
| config | PnL | maxDD | n | win% |
|--------|----:|------:|--:|-----:|
| **fixed** | **28,899** | 14,082 | 57 | 66.7 |
| atr 4h · clip 0.3–3.0 · p14 | 24,340 (−16%) | 14,250 | 57 | 66.7 |
| atr 4h · clip 0.33–1.05 · p14 | 21,814 (−25%) | 13,955 | 58 | 65.5 |
| atr 1m · clip 0.3–3.0 · p14 | **33,189 (+15%)** | **18,825 (+34%)** | 58 | 67.2 |
| atr 1m · clip 0.33–1.05 · p240 | 22,559 (−22%) | 14,698 | 59 | 67.8 |

Read it: **OOS, the ONLY config that beats fixed is the same permissive 1m default (+15%) — and it
buys that profit with +34% drawdown.** Every honest config (shrink band and/or proper period)
*loses* to fixed — exactly the study's conclusion ("ATR shrinks PnL; it's a risk-reducer, not a
profit rule").

### 1c. Look-ahead ref magnitude
`build_payload` uses `ref = mean(ATR over the WHOLE window)`; the honest value is `mean(ATR over TRAIN)`:

| source | full-mean ref | train-only ref | ratio |
|--------|--------------:|---------------:|------:|
| 4h p14 | 162.81 | 154.58 | 1.053 |
| 1m p14 | 9.73 | 9.10 | 1.068 |
| 1m p240 | 9.52 | 8.96 | 1.062 |

The look-ahead shifts the multiplier ~5–7% (2026 was more volatile, so the full mean is higher →
multiplier slightly *smaller*). It is a **genuine methodological leak**, but small, and it pushes
*against* the increase — so it is **not** the cause of the contradiction (it's a separate defect, §2).

---

## 2. Which result is "correct"?

**For the deployment question ("does ATR sizing beat the fixed champion?"), the STUDY is the correct
answer.** It is OOS, has no look-ahead, fits the coefficient on train, and uses deployable bounds.
Its verdict holds and is reconfirmed above: **no honest ATR rule beats fixed on profit; it lowers
drawdown at a profit cost; 4h-ATR ≤ fixed always.**

**The dashboard "+21%" is correct arithmetic but an invalid comparison** for that question, because it
is (a) in-sample, (b) on a different 2025–26-only span, (c) using an expansion band the study
deliberately excluded, (d) using a 14-*minute* ATR for the "1-minute" source, and (e) carrying a small
look-ahead in the reference. It is a useful *exploration* tool, not evidence that ATR beats fixed.

**Why the order flipped (4h>1m in the study, 1m>4h on the dashboard):** the study ran 1-min as
ATR(240) in a shrink-only band; the dashboard runs 1-min as ATR(14) in an expansion band. ATR(14) on
1-min is a fast, spiky estimator that, when allowed to *expand* TP up to 3×, occasionally lets winners
run far on this particular (short, in-sample) span. Give it the study's period and band and the 1-min
advantage vanishes (§1a: 144k ≈ fixed; §1b OOS: −22%).

---

## 3. System inconsistencies found (the "4h-ATR-vs-1-min-indicators" class of bug)

The user's instinct was right: the new feature reintroduces the *same family* of inconsistency we hit
before (indicators agreed on 1-minute, ATR silently stayed 4h). Three concrete defects:

### R1 — **Look-ahead in the normalization reference** *(real bug)*
`strategy.py:342` → `ref = float(np.nanmean(atrv))` averages ATR over the **entire** window, including
**future** bars, then divides every per-bar multiplier by it. The multiplier at bar *i* therefore
depends on volatility that hasn't happened yet. Magnitude here ~6% (§1c), but it is a true leak and
violates the project's "no look-ahead" invariant. **The study avoided this** (`vol[:tr_hi].mean()`).
→ Fix: normalize by a *causal* reference (expanding/rolling mean, or a fixed train-window mean).

### R2 — **1-minute ATR period default is regime-inconsistent** *(same class as the old bug)*
The period input defaults to **14 for both sources**. On the 4h frame 14 bars ≈ 56 h (sensible). On
the 1-minute frame 14 bars = **14 minutes** — a different volatility regime entirely, and *not* what
the 1-min-indicator architecture uses. The study's 1-min vol is ATR(240) (≈ one 4h bar), and the UI
hint even says "1-min≈240" — but the field does not change when you switch the source. This is exactly
the "we agreed on 1-minute but the scale is still wrong" inconsistency. → Fix: auto-set the period
default per source (4h→14, 1m→240) when the source changes, or block/warn on a clearly-too-short 1-min
period.

### R3 — **Default clip band contradicts the study's deployable bounds** *(questionable default)*
Default `0.30–3.00` lets SL_hard reach 167×3 ≈ **501 pts** and TP 120×3 ≈ **361 pts** — far outside any
guard the optimizer ever searched (the study established the binding, sensible band is **0.33–1.05**,
shrink-only). The "+21%" is largely this expansion mining in-sample structure. → Fix: default the upper
clip to ~1.05 (or surface a clear "expansion allowed beyond optimizer-explored range" warning).

### Non-bugs (documented limitations, not defects)
- **Symmetric scaling:** the multiplier scales all four lines (SL soft/hard, TP soft/hard) by the same
  factor. Asymmetric independent SL/TP sizing would need an engine extension — the study already noted
  this. Consistent between both systems.
- **`atr_mult=1.0` vs fitted `a≈0.60`:** not a bug; just means the dashboard default is a *different
  rule* than the study's opt1. Worth a UI note so users don't read the dashboard number as "opt1".
- **Engine correctness:** fixed mode is byte-identical to all 6 golden baselines (re-verified). The ATR
  path's engine math (per-bar `sl_tp_mult`) is sound; the issues are in the *multiplier construction*
  and *defaults*, not the engine.

---

## 4. Recommendation
> **STATUS (2026-06-14): R1, R2, R3 APPLIED.** `strategy.py:342` ref → causal expanding mean (no
> look-ahead); validator + UI clip default → shrink-only `0.33–1.05`; UI auto-sets `atr_period`
> 14↔240 with the source, labels the unit "bars", and warns when clip-max > 1.05. Golden baselines
> re-verified byte-identical (fixed mode unchanged). Post-fix the dashboard 1-min honest config lands
> on fixed (144k ≈ 142k) and the inflated "+21%" is no longer reproducible — exactly as the council ruled.

1. **Fix R1 (look-ahead ref)** — it's a true correctness defect; make the reference causal.
2. **Fix R2 (1-min period default)** — auto-switch 14↔240 with the source; it's the recurring
   consistency bug and silently misleads.
3. **Reconsider R3 default band** — default to the study's deployable `0.33–1.05` (expansion off), or
   warn loudly when the band exceeds the optimizer-explored range.
4. **Add a one-line UI note**: "ATR mode is exploratory; OOS-validated verdict (study) is that ATR
   sizing reduces drawdown, not profit — see STUDY_sub_optimizer." 
5. Keep the **fixed champion** as the deployed strategy; use 1-min HAR-RV `vf` (not 4h/1m ATR) if a
   drawdown-reducer is ever shipped, per the study's consistency addendum.

## 5. Reproduce
All numbers: `build_payload` on `get_bundle('4h')` with the champion `wsi1m_4h` preset, varying
`sltp_mode/atr_source/atr_period/atr_mult/atr_clip_lo/atr_clip_hi/window`. Look-ahead ref: compare
`nanmean(atrv)` vs `nanmean(atrv[:n2025])`. Study side: `STUDY_sub_optimizer_guarded.md` §5b +
`vol_source_compare.py`.
