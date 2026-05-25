# Stage 2 scatter dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single self-contained HTML page that loads `subprojects/signals/stage2/reverse_signals_full.csv`, lets the user pick X and Y axes from dropdowns of all 21 column names, and renders a Plotly scatter with green/red coloring by `first_signal`.

**Architecture:** One static HTML file with inline CSS + JS. Plotly.js from CDN. CSV loaded once via `fetch()`, parsed inline (no library), rendered with `Plotly.react()` on each dropdown change. No backend, no build step, no Python code, no new tests.

**Tech Stack:** HTML5, vanilla JavaScript (ES2020), Plotly.js v2.35.2 from CDN.

**Spec reference:** `docs/superpowers/specs/2026-05-25-stage2-scatter-dashboard-design.md`

**Sample CSV header (for reference in tasks):**
```
first_datetime,first_open,first_high,first_low,first_close,first_signal,first_box_id,first_box_type,last_datetime,last_open,last_high,last_low,last_close,last_signal,last_box_id,last_box_type,window_high,window_low,tp,sl,holds_between
```

---

### Task 1: Create dashboard directory + HTML skeleton with CDN

**Files:**
- Create: `subprojects/signals/stage2/dashboard/index.html`

This task lays down the page shell: head with Plotly CDN, body with the two `<select>`s, the plot div, the status line, and inline CSS. JavaScript is a stub that runs on load and logs "ready".

- [ ] **Step 1: Create the directory**

```bash
mkdir -p subprojects/signals/stage2/dashboard
```

- [ ] **Step 2: Write `index.html` with the page shell**

Create `subprojects/signals/stage2/dashboard/index.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Stage 2 — reverse_signals_full.csv</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 24px; color: #222; }
    h1 { font-size: 18px; font-weight: 600; margin: 0 0 16px; }
    .controls { display: flex; gap: 24px; align-items: center; margin-bottom: 16px; }
    .controls label { font-size: 14px; }
    .controls select { font: inherit; padding: 4px 8px; min-width: 200px; }
    #plot { width: 100%; height: 70vh; border: 1px solid #ddd; }
    #status { margin-top: 12px; font-size: 13px; color: #555; }
    .error { color: #b00020; font-weight: 500; padding: 24px; }
  </style>
</head>
<body>
  <h1 id="title">Stage 2 — reverse_signals_full.csv</h1>
  <div class="controls">
    <label>X axis: <select id="x-select"></select></label>
    <label>Y axis: <select id="y-select"></select></label>
  </div>
  <div id="plot"></div>
  <div id="status"></div>

  <script>
    'use strict';
    document.addEventListener('DOMContentLoaded', () => {
      console.log('dashboard ready');
    });
  </script>
</body>
</html>
```

- [ ] **Step 3: Sanity check — open the file via a local server**

```bash
cd subprojects/signals/stage2/dashboard
python3 -m http.server 8765 &
sleep 1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8765/index.html
kill %1 2>/dev/null
```
Expected output: `200`

- [ ] **Step 4: Commit**

```bash
git add subprojects/signals/stage2/dashboard/index.html
git commit -m "feat(stage2): add dashboard page shell"
```

---

### Task 2: Inline CSV parser + load on DOMContentLoaded

**Files:**
- Modify: `subprojects/signals/stage2/dashboard/index.html` (replace the `<script>` block)

Adds the fetch+parse pipeline. After this task, opening the page should log the parsed columns and row count to the console; nothing visible changes yet.

- [ ] **Step 1: Replace the `<script>` block with the CSV-loading version**

Find the `<script>...</script>` block at the bottom of `index.html` and replace it with this exact content:

```html
  <script>
    'use strict';

    const CSV_PATH = '../reverse_signals_full.csv';
    const plotDiv = document.getElementById('plot');
    const statusDiv = document.getElementById('status');
    const xSel = document.getElementById('x-select');
    const ySel = document.getElementById('y-select');

    function showError(msg) {
      plotDiv.innerHTML = `<div class="error">${msg}</div>`;
    }

    function parseCsv(text) {
      const lines = text.trim().split('\n');
      if (lines.length < 2) return { columns: [], rows: [] };
      const columns = lines[0].split(',');
      const rows = lines.slice(1).map(line => {
        const cells = line.split(',');
        const obj = {};
        for (let i = 0; i < columns.length; i++) {
          const raw = cells[i];
          const num = Number(raw);
          obj[columns[i]] = (raw !== '' && Number.isFinite(num)) ? num : raw;
        }
        return obj;
      });
      return { columns, rows };
    }

    let DATA = null;

    document.addEventListener('DOMContentLoaded', async () => {
      try {
        const resp = await fetch(CSV_PATH);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const text = await resp.text();
        DATA = parseCsv(text);
        if (DATA.rows.length === 0) {
          showError('CSV is empty.');
          return;
        }
        console.log('loaded', DATA.columns.length, 'cols,', DATA.rows.length, 'rows');
        document.getElementById('title').textContent =
          `Stage 2 — reverse_signals_full.csv (${DATA.rows.length} rows)`;
      } catch (e) {
        showError(`Could not load ${CSV_PATH} — serve via 'python3 -m http.server'. (${e.message})`);
      }
    });
  </script>
```

- [ ] **Step 2: Verify in browser**

Run:
```bash
cd subprojects/signals/stage2/dashboard
python3 -m http.server 8765
```
Open `http://localhost:8765/` in a browser. Open the JS console (F12). Expected console output: `loaded 21 cols, 370 rows`. Title should read `Stage 2 — reverse_signals_full.csv (370 rows)`. Stop the server with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add subprojects/signals/stage2/dashboard/index.html
git commit -m "feat(stage2): load and parse CSV on page load"
```

---

### Task 3: Populate dropdowns + render initial scatter

**Files:**
- Modify: `subprojects/signals/stage2/dashboard/index.html` (extend the `DOMContentLoaded` handler and add `render()`)

After this task, opening the page should show the two filled dropdowns (defaulting to X=tp, Y=sl) and a green/red scatter of all 370 points.

- [ ] **Step 1: Add `populateSelects()` and `render()` functions**

Inside the `<script>` block, immediately above the `document.addEventListener('DOMContentLoaded', ...)` line, insert these two functions:

```js
    function populateSelects(columns, defaultX, defaultY) {
      for (const col of columns) {
        const optX = document.createElement('option');
        optX.value = col; optX.textContent = col;
        if (col === defaultX) optX.selected = true;
        xSel.appendChild(optX);

        const optY = document.createElement('option');
        optY.value = col; optY.textContent = col;
        if (col === defaultY) optY.selected = true;
        ySel.appendChild(optY);
      }
    }

    function render() {
      if (!DATA) return;
      const xCol = xSel.value;
      const yCol = ySel.value;
      const longs  = DATA.rows.filter(r => r.first_signal === 'long');
      const shorts = DATA.rows.filter(r => r.first_signal === 'short');

      const makeTrace = (rows, name, color) => ({
        type: 'scattergl',
        mode: 'markers',
        name,
        x: rows.map(r => r[xCol]),
        y: rows.map(r => r[yCol]),
        marker: { color, size: 6, opacity: 0.6 },
        text: rows.map(r =>
          `${r.first_datetime} → ${r.last_datetime}<br>` +
          `${r.first_signal} → ${r.last_signal}<br>` +
          `first_box_type: ${r.first_box_type}<br>` +
          `last_box_type:  ${r.last_box_type}`
        ),
        hovertemplate: `%{text}<br>${xCol}: %{x}<br>${yCol}: %{y}<extra></extra>`,
      });

      const layout = {
        margin: { l: 60, r: 20, t: 20, b: 50 },
        xaxis: { title: { text: xCol } },
        yaxis: { title: { text: yCol } },
        dragmode: 'pan',
        legend: { orientation: 'h', y: -0.15 },
      };

      Plotly.react(plotDiv, [makeTrace(longs, 'long', 'green'), makeTrace(shorts, 'short', 'red')], layout);

      statusDiv.textContent = `${longs.length} long · ${shorts.length} short · X=${xCol}, Y=${yCol}`;
    }
```

- [ ] **Step 2: Call `populateSelects()` and `render()` after the CSV loads**

Inside the existing `DOMContentLoaded` handler, immediately after the `document.getElementById('title').textContent = ...` line, append:

```js
        populateSelects(DATA.columns, 'tp', 'sl');
        render();
```

- [ ] **Step 3: Verify in browser**

Run `python3 -m http.server 8765` from the dashboard directory and open `http://localhost:8765/`.
Expected:
- Both dropdowns populated with the 21 column names
- X defaults to `tp`, Y to `sl`
- Scatter renders with ~185 green dots (long) and ~185 red dots (short)
- Status line: `185 long · 185 short · X=tp, Y=sl`

Stop the server with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add subprojects/signals/stage2/dashboard/index.html
git commit -m "feat(stage2): render initial tp/sl scatter with green/red coloring"
```

---

### Task 4: Wire up dropdown change handlers

**Files:**
- Modify: `subprojects/signals/stage2/dashboard/index.html` (add two `change` listeners)

After this task, changing X or Y re-renders the plot instantly.

- [ ] **Step 1: Attach the listeners after the initial `render()` call**

Inside the `DOMContentLoaded` handler, immediately after the `render();` line added in Task 3, append:

```js
        xSel.addEventListener('change', render);
        ySel.addEventListener('change', render);
```

- [ ] **Step 2: Verify in browser**

Run the server again, open the page.
- Change X dropdown to `holds_between` — plot re-renders, X axis shows integers 0–16. Status line updates.
- Change Y dropdown to `first_datetime` — plot re-renders with a datetime Y axis (Plotly auto-detects).
- Change X to `first_signal` — Plotly renders a categorical X axis with two ticks `long` and `short`.

Stop the server.

- [ ] **Step 3: Commit**

```bash
git add subprojects/signals/stage2/dashboard/index.html
git commit -m "feat(stage2): re-render scatter on dropdown change"
```

---

### Task 5: Final verification + Stage 2 regression check

**Files:** none modified. Pure verification.

- [ ] **Step 1: Confirm Stage 2 tests are still green (no Stage 2 code was touched, but verify)**

```bash
python3 -m pytest subprojects/signals/stage2/tests/ -q
```
Expected: `36 passed` in ~1–2 seconds.

- [ ] **Step 2: Walk through the spec's verification checklist**

Run `python3 -m http.server 8000` from `subprojects/signals/stage2/dashboard/`. In a browser:
1. Confirm default `tp` vs `sl` scatter with 185 green + 185 red points.
2. Change X to `holds_between` — plot re-renders.
3. Change Y to `first_datetime` — Y becomes datetime axis.
4. Hover any point — tooltip shows datetime, signals, box_types, and the selected axes.
5. Stop the server.

- [ ] **Step 3: Final status report**

State explicitly:
- HTML file path: `subprojects/signals/stage2/dashboard/index.html`
- File size and line count: `wc -l subprojects/signals/stage2/dashboard/index.html`
- Stage 2 test count: `36 passed`
- Whether the browser checklist (Step 2) passed end-to-end — if you could not actually open a browser, say so explicitly rather than claiming success.

No further commit needed unless verification surfaced a fix.

---

## Out of scope reminders

Do **not** in this plan:
- Touch any file in `src/`, `frontend/`, `tests/`, `docs/graphics/`
- Touch `generate_stage2.py`, the existing Stage 2 tests, the matplotlib `plots/` script, or any CSV
- Add Python dependencies, npm dependencies, or a build step
- Create additional dashboards, configs, or wrapper scripts
- Write new automated tests (the spec explicitly excludes them)
