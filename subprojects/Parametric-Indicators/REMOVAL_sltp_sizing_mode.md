# Removal — SL/TP "sizing mode" (ATR multiplier) from dashboard + backtester

**Date:** 2026-06-15 · **Why:** the dynamic/derived SL/TP avenue was studied and **closed** (no robustness
gain, no OOS profit edge — `STUDY_relative_feasibility.md`, `STUDY_fixed_window_sltp_mapping.md`,
`COUNCIL_RULING_atr_sizing.md`, `COUNCIL_RULING_reoptimization.md`). With the feature unused and the decision
to keep **fixed** SL/TP, the sizing-mode UI + backtester logic are removed to keep the surface clean. SL/TP are
now always fixed point values.

**Result:** golden byte-match **MATCH on all 6 timeframes** (fixed mode provably unchanged); dashboard serves
with no sizing box; the dynamic-SL/TP **research scripts remain runnable** (engine hook kept — see §3).

---

## 1. What was removed — every change

### 1a. `frontend/index.html`
| # | Removed | Was |
|---|---------|-----|
| 1 | The entire **"SL/TP sizing" `sgroup`** | Mode `<select id=sltp_mode>` (fixed/atr) + `#atrbox` (atr_source, atr_period, atr_mult, atr_clip_lo/hi) + 2 hint lines incl. `#atrwarn` |
| 2 | The **multiplier chart panel** | `<div id="multpanel">…<div id="sltp_mult_chart">` |
| 3 | Chart factory entry | `,multC=mk('sltp_mult_chart',120)` dropped from the `mk(...)` chain |
| 4 | Chart series | `const multLine=…,multRef=…` line |
| 5 | Render block | `const _sm=D.sltp_mult…; multLine.setData…; multRef.setData…` (2 lines) |
| 6 | `setForm()` ATR block | the 6 `$('atr_*')`/`$('sltp_mode')` default-setters + the `toggleAtr()` call → `setForm` now ends after `applyIndicatorSpecs` |
| 7 | Functions | `toggleAtr()` and `syncAtrPeriod()` (+ their R2/R3 comments) |
| 8 | `params()` fields | `sltp_mode, atr_source, atr_period, atr_mult, atr_clip_lo, atr_clip_hi` keys |
| 9 | Listeners | `sltp_mode`→toggleAtr, `atr_source`→syncAtrPeriod, `atr_clip_hi`→toggleAtr |

### 1b. `strategy.py`
| # | Removed | Was |
|---|---------|-----|
| 10 | `validate_params` ATR block | parsing/validation of `sltp_mode` (fixed/atr), `atr_source` (4h/1m), `atr_period`, `atr_mult`, `atr_clip_lo/hi` |
| 11 | `validate_params` return keys | the 6 `sltp_mode=…, atr_*` entries dropped from the returned dict |
| 12 | `build_payload` ATR computation | the whole `if P["sltp_mode"]=="atr": …` block (4h/1m ATR, causal expanding-mean ref, clip → `sl_tp_mult`, `sltp_mult_series`) |
| 13 | Engine call | dropped `sl_tp_mult=sl_tp_mult` kwarg → `SimpleStrategy(sp).backtest(…, signals=sig_arr)` |
| 14 | `params_out` keys | the 6 `sltp_mode/atr_*` echo fields dropped |
| 15 | Return payload | `sltp_mult=sltp_mult_series` dropped from the response dict |

Replaced #10/#12 with short NOTE comments pointing to this doc.

## 2. What was intentionally NOT touched
- **`retrace_unit == "atr_mult"`** — a *different* feature (the global retrace amount's unit ∈ {atr_mult, points}); preserved everywhere (champions JSON, validate_params, indicators).
- **Champions / profiles / presets** — none carried `sltp_mode` (verified), so no data migration needed.
- **The inline-math feature** (`FEATURE_inline_math_inputs.md`) — independent, untouched.

## 3. The engine `sl_tp_mult` hook — deliberately KEPT
`engine.py SimpleStrategy.backtest(sl_tp_mult=None)` and its per-bar `_m` multiply still exist. Rationale:
- It defaults to **None** ⇒ the multiply is `× 1.0` ⇒ **byte-identical** to golden (the dashboard never sets it now).
- It is still consumed by the **archived dynamic-SL/TP research** script `optimize/sub/stage2.py:eval_dynamic`
  (and `vol_source_compare.py`, `fixed_window_subopt.py`). Removing it would break the committed evidence base
  for no benefit. It is a neutral low-level hook, not a user feature.

## 4. Verification
- **Golden byte-match: ✅ all 6 TFs MATCH** (4h $142,203/n=214, 2h, 1h, 15m, 5m, 2m) — fixed mode unchanged.
- `validate_params` returns **no** `atr/sltp` keys; `import strategy` OK.
- `optimize.sub.stage2` still imports (`eval_dynamic` present) — research intact.
- Frontend: script/style tags balanced; zero occurrences of `sltp_mode/atrbox/multpanel/sltp_mult_chart/atr_*`.
- Dashboard restarted: HTTP 200, served page has **no** "SL/TP sizing" box.

## 5. Revert
`git revert` this commit restores the feature (the engine hook never left). The dynamic-SL/TP studies/docs
remain as the historical record of why it was closed.
