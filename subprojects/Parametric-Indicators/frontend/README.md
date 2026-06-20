# Dashboards — shared module convention

Three dashboards, **one shared codebase** so changes hit all of them:

| File | Role |
|---|---|
| `dashboard_common.css` | **All** dashboard styling (theme, settings panel, cards, panels, charts, log, tables, indicator panel). |
| `dashboard_common.js` | The shared engine: `DB.initDashboard(cfg)` + helpers (chart scaffolding + time-sync + resize, gutter, inline-math, indicator panel + warmup, strategy dropdown, profile save, CSV, dirty/error, run/reset/boot). Panel-scoped indicator helpers `DB.buildPanel(host, schema, onChange)` / `DB.specsOf(host)` / `DB.applySpecsTo(host, specs)` let a page build **multiple** indicator panels (combined.html builds two); the single-panel path delegates to them. `cfg.autoFillSelected` makes the boot fill the form from the selected saved profile. |
| `index.html` | **L1** backtest dashboard (engine view via `/api/backtest` with the full feature set: HAR-RV vol chart, engine-state + drawdown charts, event log, split long/short SL/TP, timeframe/window) **+ a causal per-candle-log panel** (L1 view from `/api/causal_backtest?view=l1`, the single source of truth). Still uses `DB.initDashboard(cfg)` for the engine view. |
| `l2.html` | **L2-only** view from the causal log. Bespoke boot (not `DB.initDashboard`): `POST /api/causal_backtest` with `view:'l2'`. Reports only L2 values (L2 financials + L2's own no-entry taxonomy + per-candle log); L1 is the frozen lean champion. |
| `combined.html` | **Combined** view from the causal log. Bespoke dual-form boot: `POST /api/causal_backtest` with `view:'combined'`. Rule-combined boxes (sum / recompute / max+layer-tag via `DB.boxFromLog`), the Both‖L1‖L2 **gray** toggle (`DB.grayMarkers`/`grayLine` — grays, never hides), per-candle log table + `/api/causal_log.csv`. |

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
