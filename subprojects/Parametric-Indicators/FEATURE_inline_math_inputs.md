# Feature — Inline math in dashboard value boxes

**Date:** 2026-06-15 · **Scope:** `frontend/index.html` only (no backend/engine change). · **Status:** live.

Every numeric input in the backtester's settings panel now accepts a **math expression** (e.g. `149.8*1.1`,
`(167.1+175)/2`, `120*0.85`, `40-5`) instead of only a bare number. The expression is evaluated to a number
automatically, so you can scale/offset a value without reaching for a calculator.

---

## 1. Why
Tuning by hand constantly means "what's 10% wider than 149.8?" or "half-way between two stops?". Before, you had
to compute it elsewhere and paste the result. Now you type the arithmetic directly in the box.

## 2. What you can type
- **Operators:** `+  -  *  /` and parentheses `( )`, decimals, and scientific notation (`1e3`).
- **Examples:**
  | type this | becomes |
  |---|---|
  | `150+20` | `170` |
  | `149.8*1.1` | `164.78` |
  | `(167.1+175)/2` | `171.05` |
  | `120*0.85` | `102` |
  | `40-5` | `35` |
- A plain number (`167.1`) still works exactly as before.

## 3. When it evaluates
The expression is computed (and the box rewritten to the numeric result) at three moments:
1. **On blur** — when you click/Tab out of the box.
2. **On Enter** — pressing Enter inside the box.
3. **Right before every Run** — `params()` calls `commitMath()` first, so even an un-blurred expression is
   resolved before the backtest reads it. You can type `120*1.1` and hit **Run Backtest** directly.

## 4. Safety & validation
- **Sandboxed evaluation.** Only the character set `0-9 . e E ( ) + - * / whitespace` is allowed through; the
  expression is screened by a regex *before* evaluation. Anything else (letters, `;`, `,`, `[]`, backticks,
  hex like `0x10`, statements like `1;alert(1)`) is **rejected** — no arbitrary code can run. (This is also a
  local, single-user dashboard.)
- **Invalid → red border, never silent.** A bad expression turns the box border **red** (`input.matherr`) and
  the text is left as-is for you to fix — consistent with the project's "no silent clamp" rule. A division by
  zero / non-finite result is treated as invalid.
- **Float tidy-up.** Results are cleaned of binary-float noise (`149.8*1.1` → `164.78`, not `164.780000…3`).
- **Downstream unchanged.** The box ends up holding a plain number, so server-side `validate_params` sees the
  same numeric input it always did and still enforces every rule (e.g. `sl_hard ≥ sl_soft`, integer `cooldown`,
  `0 ≤ gate_pct ≤ 100`). Inline math is purely an input convenience; it changes no result.

## 5. Coverage
Applies to **all** value boxes in the settings panel — SL soft/hard, take-profit, gate %, drawdown trigger,
cooldown, max-DD cap, point value, K, global retrace/wait, gen params, the ATR sizing fields, **and** the
dynamically-built per-indicator parameter boxes. Dropdowns (timeframe/window/mode/flip) and checkboxes are
untouched.

## 6. How it works (implementation notes)
- `mathify(root)` converts every `<input type="number">` in a root to a text input tagged `.mathnum` (numeric
  inputs reject operator characters, so text is required), preserving `min/max/step` into `data-*`. Called once
  over the settings panel at load and again after the indicator panel is (re)built, so dynamic fields are
  covered.
- `evalMath(raw)` → `{ok, val}`: regex-screens then evaluates via a strict `Function(...)`; returns `ok:false`
  on any disallowed/failed input. `commitField(el)` writes the tidied result (or flags `.matherr`).
- Delegated `focusout` + `Enter` handlers commit a field; `commitMath()` commits all `.mathnum` fields and runs
  at the start of `params()` before any value is read.

## 7. Use it
Hard-refresh the dashboard tab (**Ctrl+Shift+R**) to load the new script, then type e.g. `120*1.1` into the
Take-profit box and Tab out — it resolves to `132`.
