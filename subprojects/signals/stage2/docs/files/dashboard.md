---
name: stage2_dashboard
description: subprojects/signals/stage2/dashboard/index.html — interactive X/Y scatter viewer for reverse_signals_full.csv
type: file
---

# dashboard/index.html

Self-contained static HTML page that loads `reverse_signals_full.csv` and renders a Plotly scatter with user-selectable X and Y columns. Successor to the static matplotlib script at `subprojects/signals/stage2/plots/scatter_tp_vs_sl.py` (which is locked to `tp` vs `sl`).

First component of Stage 3 (manageability inspection of the Stage 2 dataset), per `sub-projects-preprint.md`. See [[stage2_output_schema]] for the column list it operates over.

## Files

- `subprojects/signals/stage2/dashboard/index.html` — the only file. Inline CSS + JS, no build step, no other assets.

## Dependencies

- **Plotly.js v2.35.2** — loaded from `https://cdn.plot.ly/plotly-2.35.2.min.js` at page load. No npm, no bundler.
- **Browser only.** Modern Chromium / Firefox / Safari. No Node, no Python serving runtime beyond `http.server`.

## How to run

```
cd subprojects/signals/stage2
python3 -m http.server 8000
# open http://localhost:8000/dashboard/
```

The server **must root at `subprojects/signals/stage2/`**, not inside `dashboard/`. `python3 -m http.server` refuses to serve files outside its root, and the page fetches `../reverse_signals_full.csv` (one level up from itself).

`file://` opens will not work — the CSV `fetch()` is blocked by browser CORS rules unless served over HTTP.

## UI

```
┌──────────────────────────────────────────────────────────┐
│ Stage 2 — reverse_signals_full.csv (372 rows)            │
│                                                          │
│  X axis: [tp ▾]    Y axis: [sl ▾]                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Plotly scatter (scattergl)            │  │
│  │              green = long, red = short             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  186 long · 186 short · X=tp, Y=sl                       │
└──────────────────────────────────────────────────────────┘
```

- **Title bar** updates after CSV load to show row count.
- **Two `<select>`s** — both populated with all 21 column names from the CSV header. Defaults: X=`tp`, Y=`sl`.
- **Plot area** — 70vh tall, `scattergl` traces with `dragmode: 'pan'`.
- **Status line** — long/short counts and the current X/Y columns.

## Internals

```
DOMContentLoaded
  │
  ▼
fetch('../reverse_signals_full.csv')
  │
  ▼
parseCsv(text) — split on '\n' and ',' ; Number(v) coercion for numeric cells
  │
  ▼
{ columns: [21 names], rows: [372 objects] }   ←  stored in DATA
  │
  ▼
populateSelects(columns, 'tp', 'sl')           ←  builds <option>s
  │
  ▼
render()                                        ←  builds two scattergl traces
  │                                                 (long → green, short → red)
  ▼                                                 calls Plotly.react()
xSel / ySel 'change' listener  ──────────────→  render()
```

### CSV parser

Inline, ~15 lines. Splits on `\n`, then on `,`. Header row → `columns[]`. Each subsequent row → `{col_name: value}` where `value = Number(v)` if it round-trips to a finite number, else the original string. No quoted-field handling — Stage 2 writes plain CSV with no embedded commas or quotes (verified against the 21-column `_OUT_COLS` in `generate_stage2.py`).

### Plotly trace shape

Two `scattergl` traces are rendered per call:

| Trace | Filter | Marker color |
|---|---|---|
| `long`  | `r.first_signal === 'long'`  | `green` |
| `short` | `r.first_signal === 'short'` | `red`   |

Markers: `size: 6`, `opacity: 0.6`. Hover template includes anchor + reverse datetimes, both signals, and `first_box_type` / `last_box_type`, plus the two selected axes.

When the user selects a string column (`first_signal`, `first_box_id`, `first_box_type`, etc.) or a datetime column, Plotly auto-detects axis type — no special-casing in the JS.

## Error handling

System-boundary only:

| Condition | Behavior |
|---|---|
| `fetch` fails (non-2xx, network error, file:// open) | Plot area replaced with `Could not load ../reverse_signals_full.csv — serve via 'python3 -m http.server'. (<reason>)` |
| CSV parses to 0 data rows                            | Plot area replaced with `CSV is empty.`                                                                              |

No defensive code beyond this. Internal data shape is trusted — the producer is `generate_stage2.py` and the schema is locked by [[generate_stage2_real_data]].

## What this file does NOT include

- Filter controls beyond X/Y choice
- Multiple CSVs (locked to `reverse_signals_full.csv`)
- Selectable color column (locked to `first_signal`)
- Download / export / URL state
- Automated tests — the spec explicitly excludes them. Verification is manual against the spec's checklist.

## .gitignore note

The project-wide `.gitignore` ignores `*.html` (output artifacts). The dashboard is whitelisted via `!subprojects/signals/stage2/dashboard/*.html`. Adding more HTML files to this directory is the supported extension path; HTML elsewhere remains ignored.
