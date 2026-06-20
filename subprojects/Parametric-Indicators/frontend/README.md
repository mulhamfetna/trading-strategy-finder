# Dashboards — shared module convention

Three dashboards, **one shared codebase** so changes hit all of them:

| File | Role |
|---|---|
| `dashboard_common.css` | **All** dashboard styling (theme, settings panel, cards, panels, charts, log, tables, indicator panel). |
| `dashboard_common.js` | The shared engine: `DB.initDashboard(cfg)` + helpers (chart scaffolding + time-sync + resize, gutter, inline-math, indicator panel + warmup, strategy dropdown, profile save, CSV, dirty/error, run/reset/boot). Panel-scoped indicator helpers `DB.buildPanel(host, schema, onChange)` / `DB.specsOf(host)` / `DB.applySpecsTo(host, specs)` let a page build **multiple** indicator panels (combined.html builds two); the single-panel path delegates to them. `cfg.autoFillSelected` makes the boot fill the form from the selected saved profile. |
| `dashboard.html` | **THE unified app** — served at `/`. Three result tabs (🍃 L1 · 🔁 L2 · Σ Combined). ONE Run fires the three causal views (`POST /api/causal_backtest` view=l1/l2/combined), caches each, and renders the active tab — switching tabs is instant (no re-fetch). Each tab shows its box set (L1 **18** / L2 **20** / Combined **17**) + engine charts from the causal run (vol + gate-threshold / engine-state / drawdown / equity / event log via `optimize/l2/charts.py`) + the per-candle log; the full engine form per layer includes the **window** picker (full/2024/2025/2026/+20d) and **split long/short SL/TP**. Bespoke multi-pane boot (not `DB.initDashboard`). |


> The three standalone pages — `index.html` (L1), `l2.html` (L2), `combined.html` (Combined) — were
> **retired into `dashboard.html`**. Every box/chart they showed lives in the unified app's tabs
> (L1 18 / L2 20 / Combined 17, browser-verified). The `/api/combined_config` + `/api/causal_backtest`
> routes they used are unchanged and still power the unified page.

**Causal log-first model:** all three are projections of ONE per-candle log (`optimize/l2/logbook.run_causal` → `aggregate.boxes_for_layer`/`combined_boxes`). Boxes are computed FROM the log; charts/CSV project the same log. See `optimize/l2/REPORT_causal_logfirst.md`. Shared causal helpers on `DB`: `boxFromLog`, `flatAreaSeries`, `grayMarkers`, `grayLine` (pure; node-tested in `test_dashboard_common.cjs`).

## The rule (update both at once)
- **Styling / shared widgets / shared behavior** → edit `dashboard_common.{css,js}` **only**. Both dashboards pick it up (the server serves static files fresh per request — just reload the page, no restart).
- **Page-specific bits** (which API endpoints, which chart panels, how the payload maps to series, the metric cards) live in each page's `cfg`/`render()` — these differ because L1 and L2 return different payloads, and that's intentional.

## How a page wires itself (l2.html is the reference)
```js
const cfg = {
  endpoints: { config, backtest, profiles },   // the page's API
  panels: [ { id, height, build:(chart)=>seriesHandles } ],
  params(){ /* form -> request body */ },
  setForm(P){ /* preset -> form */ },
  render(D, H){ /* payload D -> charts via H[panelId].series + cards/tables */ },
  onConfig(c){ /* page-specific config handling; return a default preset or null */ },
};
DB.initDashboard(cfg);
```

## Follow-up (open)
`index.html` JS is not yet migrated onto `DB.initDashboard` (kept as-is to avoid risking the proven L1 dashboard without a visual check). Its **CSS is already shared**. To finish the DRY: port index's `render()`/`params()`/`setForm()` into an L1 `cfg` (same as l2.html), verify a 4h backtest renders identically in the browser, then delete the duplicated inline helpers. After that, **every** dashboard change is a single edit in `dashboard_common.*`.
