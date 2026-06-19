# Dashboards — shared module convention

Three dashboards, **one shared codebase** so changes hit all of them:

| File | Role |
|---|---|
| `dashboard_common.css` | **All** dashboard styling (theme, settings panel, cards, panels, charts, log, tables, indicator panel). |
| `dashboard_common.js` | The shared engine: `DB.initDashboard(cfg)` + helpers (chart scaffolding + time-sync + resize, gutter, inline-math, indicator panel + warmup, strategy dropdown, profile save, CSV, dirty/error, run/reset/boot). Panel-scoped indicator helpers `DB.buildPanel(host, schema, onChange)` / `DB.specsOf(host)` / `DB.applySpecsTo(host, specs)` let a page build **multiple** indicator panels (combined.html builds two); the single-panel path delegates to them. `cfg.autoFillSelected` makes the boot fill the form from the selected saved profile. |
| `index.html` | **L1** backtest dashboard. Uses `dashboard_common.css`. (Its JS is still the original inline script — a follow-up will migrate it onto `DB.initDashboard`; tracked below.) |
| `l2.html` | **L2** second-layer dashboard. A thin page: skeleton + a `cfg` object → `DB.initDashboard(cfg)`. |
| `combined.html` | **L1 + L2 combined** dashboard. Runs both layers in parallel (`/api/combined_backtest`); two editable forms behind a settings nav, 3 box groups (L1 / L2 / combined), an L1‖L2‖Both chart toggle, and a source-labeled merged ledger. Uses the shared CSS + `DB.*` helpers with its own dual-form boot (the single-form `initDashboard` doesn't fit two forms). |

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
