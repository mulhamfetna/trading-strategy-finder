# UPDATE — Phase E3: expose split long/short SL/TP in the dashboard + finish engine⇄optimizer⇄dashboard sync

**Date:** 2026-06-15. **Goal:** complete the E-series so the **three input surfaces share one parameter set** —
the exact engine (E1), the fast engine + optimizer (E2), and now the **backtester dashboard** (E3). The user
asked to "add the new indicators and SL/TP boxes and assure the backtest engine, the optimizer and the dashboard
are synced and all share the same inputs."

## What was already synced (verified, no change needed)
- **3 new vote indicators — `ifvg`, `breaker`, `cisd`.** The dashboard's indicator panel is **100 % built from
  `/api/config` → `indicators.library.schema()`** (`buildIndicatorPanel()` in `frontend/index.html`). All three
  are registered in `library.REGISTRY` + `SCHEMA`, so they **already render** (enable toggle, mode selector,
  per-indicator params) with nothing hardcoded. The optimizer likewise auto-adds `en_ifvg/en_breaker/en_cisd`
  from the same registry. ⇒ indicators were already three-way synced; E3 only had to add the SL/TP boxes.
- **`veto_as_flip`, global `retrace`/`wait`, `gen swing_l/golf_n`, `k`** — all already on the dashboard.

## The one gap: split long/short SL/TP boxes
E1 (engine `SimpleStrategyParams`) and E2 (`fast_backtest`/`core`/`optimizer --split-sltp`) accept
`long_sl_soft/long_sl_hard/long_tp` + `short_*`, but the **dashboard had no UI for them** (its `params()` sent
only the shared `sl_soft/sl_hard/tp`). E3 adds that UI.

## Every change (with why)
1. **`frontend/index.html` — UI.** At the **top** of the *Entry / exit (points)* value-box container added an
   **"SL/TP mode" dropdown** (`shared` | `split long/short`). The three shared boxes live in `#sharedbox`; the six
   per-side boxes (Long/Short × SL soft/hard/TP) live in a hidden `#splitbox`. *Why (user req):* a dropdown at the
   top of the box container, and in split mode the **shared boxes are hidden** (not left showing) — the dropdown
   swaps one container for the other.
2. **`frontend/index.html` — `params()`.** In **`shared`** mode all six `long_*`/`short_*` are sent as **`null`**;
   in **`split`** mode each per-side box is sent (blank box ⇒ `null`). The shared `sl_soft/sl_hard/tp` are **always
   sent** (the engine requires them); in split mode they're hidden but retain their values. *Why:* `null` ⇒ server
   falls back to the shared value ⇒ `shared` mode is **byte-identical** to a normal run.
3. **`frontend/index.html` — `setForm()`.** A preset/profile carrying any `long_*`/`short_*` value selects **`split`**
   mode (hides `#sharedbox`, shows `#splitbox`) and fills the boxes; otherwise **`shared`**. Shared boxes keep their
   values either way. *Why:* presets round-trip.
4. **`frontend/index.html` — mode-dropdown handler.** Switching to `split` **prefills blank per-side boxes from the
   shared values** (start from the current strategy, tweak one side), hides `#sharedbox`, shows `#splitbox`; back to
   `shared` restores the shared boxes. Marks dirty.
5. **`server.py` — `/api/config` bounds.** Added `long_sl_soft/long_sl_hard/long_tp/short_*` to the `bounds` map
   (`[1, None]`, same as shared). *Why:* keep the dashboard's validation surface aligned with the shared boxes;
   the frontend still hardcodes nothing.

No engine/optimizer code changed in E3 — the backend already accepted these keys (E1/E2). `validate_params`
already validates per-side `hard ≥ soft` when both are set and treats each `None` as "use shared".

## Verification (all green)
- **`validate_params`** — `shared`-mode payload (all six `null`) ≡ a payload with **no** split keys (back-compat);
  `split`-mode payload returns the six per-side floats. ✓
- **`build_payload` end-to-end (4h, window 2026, champion params)** — split-OFF summary is **identical** to a
  plain run (`pnl=3870, n=4`, summary dicts equal); split-ON **diverges** (`pnl=-4105, n=3`). ✓
- **golden byte-match** — 6/6 TFs unchanged (engine untouched; split defaults to shared). ✓

## E3a — reset-to-default-after-run bug + separator + headless E2E (follow-up)
**Bug:** after every Run the form snapped back to defaults / dropped split mode. **Cause:** `build_payload`
hand-builds `meta.params` (echoed back to the dashboard, which calls `setForm(meta.params)`), and it **omitted
the split keys + the global retrace/wait keys**. With no `long_*`/`short_*` coming back, `setForm` computed
`_anySplit=false`, forced the mode dropdown to `shared`, and **cleared the per-side boxes** — so user edits looked
like they had "no effect." The values *did* reach the engine; only the form round-trip was broken.
**Fix (`strategy.py`):** `params_out` now also echoes `retrace_amount/retrace_unit/wait_bars` and all six
`long_*`/`short_*` (from the validated `P`). Shared runs still echo the six as `null` ⇒ form correctly returns to
shared mode.
**Separator (`frontend/index.html`):** added `<hr class="sep">` between the SL/TP value boxes and the
Direction / On-veto selects (+ `.sep` CSS).
**Headless E2E (`tests/e2e_dashboard_inputs.py`):** Playwright drives real google-chrome against a live server,
captures the actual `/api/backtest` POST body, and asserts the form keeps user edits after a run in **both** modes.
**16/16 checks PASS** — incl. "shared: form KEEPS sl_soft=33 after run", "split: mode STILL 'split' after run",
"split: long_sl_soft STILL 120 after run". (Playwright's bundled Chromium is unavailable on ubuntu 26.04, so the
test points at `/usr/bin/google-chrome` via `executable_path`.)

## Three-way sync result (the deliverable)
| Input | Exact engine (E1) | Fast engine + optimizer (E2) | Dashboard (E3) |
|---|---|---|---|
| `ifvg` / `breaker` / `cisd` | ✅ registry | ✅ auto `en_*` | ✅ schema-driven panel |
| shared `sl_soft/sl_hard/tp` | ✅ | ✅ | ✅ |
| split `long_*` / `short_*` | ✅ | ✅ `--split-sltp` | ✅ **SL/TP-mode dropdown + 6 boxes (new)** |
| `veto_as_flip`, retrace/wait, `k`, gen | ✅ | ✅ | ✅ |

## Revert
In `frontend/index.html`: remove the checkbox + `#splitbox` block, the `sp`/`spv` lines and six fields in
`params()`, the `_SPL` block in `setForm()`, and the `#split_sltp` change handler. In `server.py`: drop the six
split keys from `bounds`. Nothing else references the dashboard split UI.
