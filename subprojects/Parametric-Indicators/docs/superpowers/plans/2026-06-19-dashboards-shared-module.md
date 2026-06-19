# Shared-Module Dashboards (full L2 replica) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) tracking.

**Goal:** Make `frontend/l2.html` a **full-featured replica** of the main dashboard, by extracting the shared UI (theme/CSS + chart scaffolding + render + settings/indicator panel + profile-save + CSV + inline-math + resize/gutter) into a **shared module** that BOTH `index.html` and `l2.html` include — so any future change updates both, with no drift.

**Architecture:** Two new files — `frontend/dashboard_common.css` (all shared styles) and `frontend/dashboard_common.js` (a configurable `initDashboard(cfg)` plus all shared helpers). `index.html` and `l2.html` each become a thin shell: the shared HTML skeleton + a small `cfg` object that supplies page-specific bits (API endpoints, header text, which panels, card layout, and an L2-only overlay hook). The L1↔L2 differences are isolated in those `cfg` objects + one `renderOverlays(D)` hook; everything else is shared.

**Tech Stack:** vanilla JS, lightweight-charts@4.1.3 (CDN), the stdlib `server.py` (serves static files fresh per request — no restart needed for frontend changes), pytest (backend route tests only; frontend verified by serve + curl + manual smoke).

## Global Constraints

- **Do NOT break the working main dashboard.** After Task 2, `index.html` must behave **identically** (same panels, charts, log, settings, profile save, CSV, gutter, inline-math). Verify by serving + running a 4h backtest and eyeballing parity, and `perf/check_golden.py` must stay **6/6** (frontend-only changes can't affect golden, but run it as the safety net).
- **DRY / single source:** any shared style or behavior lives ONLY in `dashboard_common.{css,js}`. Page files carry only their `cfg` + skeleton. A future change to shared UI is one edit.
- **L2 semantics (full UI, honest backend):** `l2.html` shows the full settings experience; the L2 backend (`run_l2`) currently honors `gate_pct`, K, SL/TP, `dd_limit`, `cooldown`, `flip`, indicators. Controls L1 has that `run_l2` ignores (`window` is fixed full-period via the L2 windowing; `retrace`/`wait`/`veto_as_flip`/`dd_cap`/`pv`) are shown but labeled "not used by L2 (round 1)" via a `cfg.disabledFields` list (greyed) — no silent dead controls (preserves the project's no-silent-fallback norm while giving the full visual experience).
- **Frontend only.** No engine/optimizer/Python changes except, if needed, additive fields in the L2 payload (none expected). `server.py` already serves any `frontend/*.{js,css}` (the static handler serves by suffix).
- **Commit only at the step that says so; stage by path.** Branch `dev`. Never stage `frontend/data.js` (pre-existing) or repo-root secrets.

---

### Task 1: Extract `dashboard_common.css` + `dashboard_common.js` (additive — touch no page yet)

**Files:**
- Create: `frontend/dashboard_common.css`
- Create: `frontend/dashboard_common.js`

**Interfaces produced (the `dashboard_common.js` public API both pages call):**
- `DBHelpers` — `TH`, `COMMON`, `dt(t)`, `money(n)`, `card(v,k,cls)`, `evalMath`, `commitMath`, `mathify(root)`, `showErr(msg)`, `markDirty()`, `markClean()`, `csvDownload(name,text)`, `toCSV(h,rows)`.
- `initCharts(specs)` → `{charts, byId, fitCharts}` — `specs` is an array of `{id, height, series:[…]}`; returns created chart/series handles keyed by id. (Replaces index.html lines 222–242.)
- `initGutter()` — the resizable settings panel (index lines 246–253), no-op if `#gutter` absent.
- `buildIndicatorPanel(sch, hooks)` / `indicatorSpecs()` / `applyIndicatorSpecs(specs)` — the indicator panel (index 402–467), parameterized by a host id (default `indpanel`).
- `wireProfiles(cfg)` — strategy dropdown + save profile + reset (index 556–635), using `cfg.endpoints.profiles`/`config`.
- `initDashboard(cfg)` — boot: fetch `cfg.endpoints.config`, build panel + TF dropdown + strategy dropdown, then `cfg.boot()`.

- [ ] **Step 1: Create `dashboard_common.css`** — move the entire `<style>` block from `index.html` lines 9–105 verbatim into this file (it is all generic; nothing page-specific). Leave a 1-line comment header noting it is shared by index.html + l2.html.

- [ ] **Step 2: Create `dashboard_common.js`** — move the shared JS verbatim, wrapped as an exported namespace. Port, unchanged in behavior: `TH`/`COMMON` (220–221); `initCharts` generalising `mk`/`seg` + series creation + the time-sync + `fitCharts` + ResizeObserver (222–242); `initGutter` (246–253); `dt`/`money`/`card` (255–257); the inline-math block `evalMath`/`commitField`/`commitMath`/`mathify` + focusout/keydown listeners (338–364); `showErr`/`markDirty`/`markClean` (469–474); indicator panel `buildIndicatorPanel`/`indicatorSpecs`/`applyIndicatorSpecs`/`recomputeWarmup`/`fmtDur` (400–467); profile/dropdown/CSV helpers (530–594). Expose them on a global `DB` object. `$ = id=>document.getElementById(id)` stays global.

- [ ] **Step 3: Syntax check** — `node --check frontend/dashboard_common.js` (Expected: no output / exit 0). If `node` unavailable, load it in a throwaway HTML via the browser console is out of scope; instead `python3 -c "import esprima"` is not available — rely on the Task 2 live-serve smoke to catch syntax errors.

- [ ] **Step 4: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add frontend/dashboard_common.css frontend/dashboard_common.js
git commit -m "feat(dashboard): extract shared dashboard_common.{css,js} (no page rewired yet)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Rewire `index.html` onto the shared module (identical behavior)

**Files:**
- Modify: `frontend/index.html` (replace the inline `<style>` with a `<link>`; replace the shared inline JS with `<script src="dashboard_common.js">` + a small L1 `cfg`; keep the L1-specific `render(D)` + the HTML skeleton).

**Interfaces consumed:** all of `DB.*` from Task 1.

- [ ] **Step 1:** Replace `index.html` `<style>…</style>` (lines 8–106) with `<link rel="stylesheet" href="dashboard_common.css">`.
- [ ] **Step 2:** Add `<script src="dashboard_common.js"></script>` before the page `<script>`; delete the now-duplicated shared functions from the page script, calling `DB.initCharts([...L1 panel specs...])`, `DB.initGutter()`, `DB.buildIndicatorPanel(...)`, etc. Keep L1's `render(D)` (the L1 payload→series mapping, lines 259–333) and L1 `params()`/`setForm()` (page-specific field set). Define the L1 `cfg = {endpoints:{config:'/api/config', backtest:'/api/backtest', profiles:'/api/profiles'}, …}`.
- [ ] **Step 3: Live parity smoke.** `curl -s localhost:8200/ -o /dev/null -w "%{http_code}\n"` (200); then in the browser run a **4h backtest** and confirm: all cards (4 groups), price+vol+state+equity+dd charts, event log, trade ledger, gutter resize, strategy import, save profile, CSV all work exactly as before.
- [ ] **Step 4: Golden** — `python3 perf/check_golden.py` → 6/6 (safety net).
- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "refactor(dashboard): index.html uses dashboard_common.{css,js} — identical behavior

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Rebuild `l2.html` as a full replica on the shared module

**Files:**
- Modify (rewrite): `frontend/l2.html`

**Interfaces consumed:** `DB.*`; L2 endpoints `/api/l2_config`, `/api/l2_backtest`, `/api/l2_profiles`.

- [ ] **Step 1:** New `l2.html` = the same skeleton (header + aside settings + main panels) + `dashboard_common.{css,js}`, with an L2 `cfg`:
  - `endpoints:{config:'/api/l2_config', backtest:'/api/l2_backtest', profiles:'/api/l2_profiles'}`.
  - Header shows the fixed L1 context (`l1_label`, L1 trades/PnL from `/api/l2_config`).
  - `disabledFields:['window','retrace','wait','veto_as_flip','dd_cap','pv']` → greyed + "not used by L2 (round 1)" titles.
  - Full settings groups (SL/TP incl. split, gate, dd-breaker, confirmation, **full indicator panel**) — identical widgets to L1.
  - `params()` builds the L2 body (the focused levers `run_l2` honors).
- [ ] **Step 2: L2 `render(D)`** — reuse the shared charts; map the L2 payload: price (candles + dropped markers by reason + L2 trade markers agree/oppose + `L1-entry` flag + derived SL/TP lines + L1-flat shading) + **equity panel overlaying combined vs L1-only vs L2**; cards = L2-standalone + combined guardrail; L2 ledger + dropped-signal table panels. (Port from the current `l2.html` render, now on the shared chart handles.)
- [ ] **Step 3: Live smoke.** Serve; open `/l2.html`; **Run L2** with the lean/permissive profile; confirm the full experience renders (all panels, full settings, indicator panel, save profile) and the L2 overlays are correct.
- [ ] **Step 4: Backend route tests still green** — `python3 -m pytest optimize/l2/test_l2_server.py -q` (the routes are unchanged) + `python3 perf/check_golden.py` → 6/6.
- [ ] **Step 5: Commit**

```bash
git add frontend/l2.html
git commit -m "feat(l2): l2.html is now a full-featured replica on dashboard_common (DRY, both in sync)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Doc the shared-module convention (both stay in sync)

**Files:**
- Modify: `optimize/l2/UPDATE_l2_dashboard.md` (note the shared-module architecture + the rule: future dashboard changes go in `dashboard_common.*`, hitting both pages).
- Create/append: a short `frontend/README.md` note — "index.html + l2.html share dashboard_common.{css,js}; edit the common file to update both; page files hold only their cfg + page-specific render()."

- [ ] **Step 1:** Write the note(s).
- [ ] **Step 2: Commit**

```bash
git add optimize/l2/UPDATE_l2_dashboard.md frontend/README.md
git commit -m "docs(dashboard): record the shared-module convention — edit dashboard_common to update both dashboards

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-check
- Full replica → Task 3 builds l2.html with the same skeleton + shared module + full settings/indicator panel. ✅
- Update-both / DRY → Tasks 1–2 put all shared UI in `dashboard_common.*`; Task 4 documents the rule. ✅
- Don't break main → Task 2 step 3–4 parity smoke + golden. ✅
- No silent dead controls → `cfg.disabledFields` greys L2-unused controls with a reason. ✅
- Frontend-only / golden-safe → server serves static files; golden run each code task as the net. ✅
