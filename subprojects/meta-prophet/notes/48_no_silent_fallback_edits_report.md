---
name: no-silent-fallback-edits-report
description: Change report (where/when/why/how) for the WS-G standalone hardening — strict server-side parameter validation with no silent clamping or hidden defaults, every parameter exposed to the user, and backend errors surfaced verbatim to the UI. Commit 67df254. Companion to notes/47 (breaker fix).
type: reference
---

# Edits Report — no silent fallback / expose all params / error reporting to UI (commit `67df254`)

This is the **change log** for the hardening of the standalone WS-G app: exactly **when**,
**where**, **why**, and **how** each edit was made. It follows the breaker-fix report
(`notes/47`) and applies to the self-contained subproject `subprojects/wsg-strategy/`.

---

## WHEN
- **Commit:** `67df254` — "fix(wsg-strategy): no silent fallback — strict param validation + errors surfaced to UI"
- **Date:** 2026-06-03 17:06 (+03:00) · **Author:** Mulham Fetna · **Pushed:** `origin/dev`
- **Scope:** 3 files, +122 / −21 lines.
- **Parent:** `08bf2e6` (the breaker edits report, `notes/47`).

## WHY (one sentence)
The app **silently clamped or defaulted bad/missing parameters** and only showed failures in a
muted status line — so a user could run a backtest with quietly-altered inputs and never know,
and the frontend **embedded the "winner" defaults as hardcoded literals** that could drift from
`config.py`. The request: *no silent fallback, every parameter exposed with no hardcoded values,
and error reporting integrated into the UI.*

## HOW (the change, by category)

### 1. Strict server-side validation — raise, never clamp (`strategy.py`)
A new exception + validator replace all implicit coercion/clamping:
```python
class ParamError(ValueError):
    """Invalid/missing strategy parameter. Surfaced to the UI; values are NEVER silently
    clamped or defaulted — a bad input is an error the user must see."""

def validate_params(params):
    # all required params must be present; each value type-checked; bounds enforced; RAISES.
```
Rules enforced (each raises `ParamError` with a user-facing message, no clamping):
- all of `sl_soft, sl_hard, tp, gate_pct, dd_limit, cooldown, flip, window` **must be present**;
- every numeric field must parse as a number;
- `sl_soft > 0`, `tp > 0`, `sl_hard ≥ sl_soft`, `gate_pct ∈ [0,100]`, `dd_limit ≥ 0`,
  `cooldown` a non-negative integer, `window ∈ {full, 2025, 2026}`.
- Instrument constants `dd_cap` and `pv` are **exposed** and default to `config` **only when
  omitted** (and then must be `> 0`). `build_payload()` was rewired through `validate_params`,
  and the point value `pv` now drives the P/L conversion (no hardcoded ×20); `params_out` echoes
  `dd_cap` + `pv` back so the UI shows exactly what ran.

### 2. Config endpoint — the frontend hardcodes nothing (`server.py`)
```
GET /api/config -> {preset, dd_cap, pv, bounds, windows}
```
The "winner" defaults now live in `config.py` and travel to the browser at runtime.

### 3. User-facing HTTP errors (`server.py`)
`POST /api/backtest` now distinguishes:
- `ParamError`  → **HTTP 400** `{"error": "Invalid parameter: …"}` (logged `param error: …`);
- any other failure → **HTTP 500** `{"error": "Backtest failed: …"}` (with traceback to stderr).

### 4. Expose every parameter + surface errors in the UI (`frontend/index.html`)
- Added **Max-DD cap ($)** and an **Instrument → Point value ($)** field, plus a red **error
  banner** (`#err`).
- `params()` now sends `dd_cap` + `pv`; `setForm()` populates them.
- **Boot** and **Reset** fetch `/api/config` and fill the form from it — the previous hardcoded
  `setForm({…sl_soft:30,…dd_limit:2000,cooldown:20…})` literal in the reset handler is gone. A
  static `file://` view falls back **only** to the embedded saved-run params.
- `run()` shows the server's **exact** message in the banner, distinguishing a connection failure
  ("start the backend …") from a rejected parameter ("Backtest rejected: …") instead of the old
  muted status line.

## WHERE (every file)
| File | What changed | ± |
|---|---|---|
| `wsg-strategy/strategy.py` | `ParamError` + `validate_params()`; `build_payload` rewired; `pv`-driven P/L; `dd_cap`/`pv` echoed | +51 / −9 |
| `wsg-strategy/server.py` | new `GET /api/config`; 400 on `ParamError`, 500 otherwise; docstring | +16 / −2 |
| `wsg-strategy/frontend/index.html` | `dd_cap` + `pv` fields + error banner; `params()`/`setForm()`; `/api/config`-driven boot+reset; `run()` error surfacing | +55 / −10 |

**Not touched (deliberately):** the verified production engine (`src/strategy/simple_strategy.py`),
the parity-tested clone's entry/exit logic, the main dashboard/backend, and the candle/box graphic
mechanism. Only the standalone app's parameter/IO layer changed — the engine itself is unchanged.

## VERIFICATION (live server, 9 cases)
| # | Request | Expected | Result |
|---|---|---|---|
| 1 | `GET /api/config` | preset + dd_cap + pv + bounds + windows | ✅ all defaults exposed |
| 2 | valid winner run | 200 + full payload | ✅ +$7,735 / $3,670 / 66 trades |
| 3 | `sl_hard < sl_soft` | 400 | ✅ "sl_hard (30) must be ≥ sl_soft (40)" |
| 4 | missing `tp` | 400 | ✅ "missing parameter(s): tp" |
| 5 | `gate_pct = 150` | 400 | ✅ "gate_pct must be in [0,100]" |
| 6 | non-numeric `sl_soft` | 400 | ✅ "'sl_soft' must be a number, got 'abc'" |
| 7 | empty body `{}` | 400 | ✅ "no parameters supplied …" |
| 8 | `window = 2024` | 400 | ✅ "window must be one of full\|2025\|2026" |
| 9 | custom `dd_cap=4000, pv=2` | echoed, not defaulted | ✅ dd_cap 4000 · pv 2 |

No value was silently clamped in any case; every rejection carried a clear, user-facing message.

## RESULT
| | before | after |
|---|---|---|
| bad/missing param | silently clamped/defaulted, run proceeds | **HTTP 400 with a clear message; no run** |
| where defaults live | hardcoded literals in the HTML | **`config.py`, delivered via `/api/config`** |
| point value | hardcoded ×20 | **`pv` parameter (exposed, default 20)** |
| errors shown to user | muted status line only | **red banner with the server's exact message** |
| `dd_cap` / `pv` | not user-editable | **editable form fields, echoed back in payload** |

## One-paragraph summary (baby)
On 2026-06-03 (commit `67df254`) we made the standalone strategy app **honest about its inputs**.
Before, if you typed a bad or missing number it would quietly fix it for you and run anyway, and
the "winner" settings were copy-pasted into the web page where they could silently fall out of
sync with the real config. Now the server **rejects** any bad input with a plain-English reason
(shown in a red box on the page), every knob — including the drawdown cap and the dollar-per-point
value — is a real editable field, and the page asks the server for the defaults instead of
guessing. Nothing is changed behind your back; what you see is what ran.

## Scope note / follow-up
This hardening applies to the standalone `wsg-strategy/` "system" as requested. The two sibling
dashboards (`meta-prophet/dashboard_winner/` and `winner_dashboard/`) still use the old
`DEFAULTS`-merge + clamp pattern in their `winner_backtest.py`; propagating the same
validation/error-handling there is a candidate follow-up (confirm scope first).
