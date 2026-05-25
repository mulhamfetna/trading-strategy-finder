# Stage 2 scatter dashboard — design

**Status:** approved 2026-05-25
**Scope:** single deliverable — a static HTML dashboard for visually exploring `reverse_signals_full.csv`. Stage 2 internals (`generate_stage2.py`, tests, CSV schema, docs) are untouched. Main project (`src/`, `frontend/`, `tests/`, `docs/graphics/`) is untouched.

## Goal

Let the user pick any two columns of `reverse_signals_full.csv` as X and Y from dropdowns and see a scatter plot, colored green/red by `first_signal`. Successor to the static matplotlib scatter at `subprojects/signals/stage2/plots/scatter_tp_vs_sl.py`, which is fixed to `tp` vs `sl`.

This is the first piece of Stage 3 ("inspect Stage 2 output for manageability") from `sub-projects-preprint.md`.

## Deliverables

- `subprojects/signals/stage2/dashboard/index.html` — the only new file. Self-contained.

No new Python code. No new tests. No changes to CSV files, generators, or existing docs.

## Architecture

Single static HTML page with inline CSS and inline JavaScript. Plotly.js loaded from CDN. CSV loaded at page-load time via `fetch('../reverse_signals_full.csv')` relative to `index.html`.

```
index.html
  │
  ├── on DOMContentLoaded
  │     └── fetch ../reverse_signals_full.csv
  │           └── parse → { columns: [...], rows: [{col: val, ...}, ...] }
  │                 └── populate two <select>s with all 21 column names
  │                       └── render initial scatter (X=tp, Y=sl)
  │
  └── on either <select> change
        └── Plotly.react(div, [longTrace, shortTrace], layout)
              where each trace's x/y arrays are pulled from the parsed rows
              filtered by first_signal == 'long' / 'short'
```

## Components

### CSV parser (~15 lines, inline)

Split on `\n`, split each row on `,`. First row is header. Numeric columns parsed via `Number(v)` — values that round-trip to a finite number become numbers, everything else stays as the original string. No quoted-field handling needed: Stage 2 writes plain CSV with no embedded commas or quotes (verified by inspection of `_OUT_COLS` — only ISO datetimes, signal enums, semicolon-joined ids, and numbers).

### UI

```
┌──────────────────────────────────────────────────────────┐
│ Stage 2 — reverse_signals_full.csv (370 rows)            │
│                                                          │
│  X axis: [tp ▾]    Y axis: [sl ▾]                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  │              Plotly scatter                        │  │
│  │              green = long, red = short             │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  185 long · 185 short · X=tp, Y=sl                       │
└──────────────────────────────────────────────────────────┘
```

Both `<select>` elements list all 21 column names. Defaults: X=`tp`, Y=`sl`.

### Plotly traces

Two `scattergl` traces (gl handles 370 points trivially but stays fast if dataset grows):
- `longs`: `marker.color = 'green'`, points where `first_signal === 'long'`.
- `shorts`: `marker.color = 'red'`, points where `first_signal === 'short'`.

Both traces use `mode: 'markers'`, `marker.size: 6`, `marker.opacity: 0.6`.

Hover template includes: `first_datetime`, `first_signal`, `first_box_type`, `last_box_type`, plus the two selected axes.

Layout: axis titles match selected columns. `dragmode: 'pan'`. Plotly auto-handles categorical/datetime axes when given string values, so the `all 21 columns` choice works without special-casing.

## Data flow

```
reverse_signals_full.csv (file)
   │ fetch()
   ▼
text → split → header[], rows[]
   │
   ▼
columns[] = header
data[]    = rows mapped to {col: numeric-or-string, ...}
   │
   ▼
populate X and Y <select>s (one <option> per column name)
   │
   ▼  (on change OR initial render)
xCol, yCol ← selected values
longs  = data.filter(r => r.first_signal === 'long')
shorts = data.filter(r => r.first_signal === 'short')
   │
   ▼
Plotly.react(plotDiv, [
   { name: 'long',  x: longs.map(r => r[xCol]),  y: longs.map(r => r[yCol]),  marker: {color: 'green'} },
   { name: 'short', x: shorts.map(r => r[xCol]), y: shorts.map(r => r[yCol]), marker: {color: 'red'} },
], layout)
```

## Error handling

System-boundary only:
- If `fetch` fails (file missing, served without HTTP), replace plot area with the message `"Could not load ../reverse_signals_full.csv — serve via 'python3 -m http.server'."`
- If the CSV has fewer than 1 data row, show `"CSV is empty."` in the plot area.

No other defensive code. Internal data shape is trusted — we control the producer.

## How to run

```
cd subprojects/signals/stage2
python3 -m http.server 8000
# open http://localhost:8000/dashboard/
```

The server must be rooted at `subprojects/signals/stage2/` (one level above `dashboard/`) because `python3 -m http.server` refuses to serve files outside its root, and the page needs to fetch `../reverse_signals_full.csv`. A `file://` open will also fail because of browser CORS on the CSV fetch. The HTTP server is one line and needs no install.

## Out of scope (deliberate YAGNI)

- Selectable CSVs (locked to `reverse_signals_full.csv`)
- Filtering controls beyond X/Y choice
- Selectable color column (locked to `first_signal` green/red)
- Download/export
- URL state / shareable views
- Tests (thin viewer; behavior is "what Plotly renders")
- Build step, npm dependencies, bundler
- Backend / API

## Verification at completion

1. `python3 -m http.server 8000` from `subprojects/signals/stage2/`, then open `http://localhost:8000/dashboard/`
2. Open browser, confirm the default `tp` vs `sl` scatter renders with 185 green and 185 red points
3. Change X to `holds_between`, confirm plot re-renders
4. Change Y to `first_datetime`, confirm Plotly switches to a datetime y-axis
5. Confirm Stage 2 tests still pass (`pytest subprojects/signals/stage2/tests/`) — should be untouched since no Stage 2 code changes
