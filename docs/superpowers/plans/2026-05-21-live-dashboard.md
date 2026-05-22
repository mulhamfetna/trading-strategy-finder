# Live Dashboard (Dash) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight Dash-based live dashboard that serves the generated HTML dashboards and offers a live preview endpoint, implemented TDD-first and non-invasive to existing generation code.

**Architecture:** Implement a minimal Dash app that embeds the existing generated HTML dashboards (docs/live_trading_dashboard.html and docs/equity_curve_dashboard.html) via iframes. Keep the Dash app in src/dashboard/dash_app.py and an entrypoint in src/main/live_dashboard_app.py, so tests and CI can import the app without running the server. No refactor of existing generators is required.

**Tech Stack:** Python 3.14, Dash (plotly/dash), pytest for tests.

---

### Task 1: Add failing test for Dash app existence

**Files:**
- Create: `tests/test_dash_app.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dash_app.py
import os
import sys
import importlib

# Ensure repo root is importable in test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_dash_app_import_and_layout(monkeypatch, tmp_path):
    # Ensure docs HTML exists for the app to read
    docs = tmp_path / 'docs'
    docs.mkdir()
    html_file = docs / 'live_trading_dashboard.html'
    html_file.write_text('<html><body><h1>TEST DASHBOARD</h1></body></html>', encoding='utf-8')

    # Monkeypatch cwd to tmp_path so the app finds docs/ in working dir
    monkeypatch.chdir(tmp_path)

    # Import the app module (should create a `dash_app` object)
    module = importlib.import_module('src.dashboard.dash_app')

    assert hasattr(module, 'app')
    app = module.app
    # Dash apps have a server attribute
    assert hasattr(app, 'server')

    # Layout should include an Iframe (html.Iframe) or a component with id 'live-dashboard'
    layout_str = str(app.layout)
    assert 'Iframe' in layout_str or 'live-dashboard' in layout_str
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```
pytest tests/test_dash_app.py -q
```
Expected: FAIL with ModuleNotFoundError or ImportError because `src.dashboard.dash_app` does not yet exist.

- [ ] **Step 3: Commit the test**

```bash
git add tests/test_dash_app.py
git commit -m "test(dash): add failing test for Dash app import and layout" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```


### Task 2: Implement the Dash app (minimal, iframe-based)

**Files:**
- Create: `src/dashboard/dash_app.py`
- Ensure: `src/dashboard/__init__.py` exists (create if missing)

- [ ] **Step 1: Implement app**

Create `src/dashboard/dash_app.py` with the following content:

```python
# src/dashboard/dash_app.py
"""Minimal Dash app that embeds existing generated HTML dashboards via iframes.
This keeps the implementation non-invasive: the generator still writes static HTML,
and Dash merely offers a live preview and lightweight controls later.
"""
import os
from pathlib import Path

try:
    from dash import Dash, html
except Exception:
    # If Dash isn't installed, provide a helpful error when running the server.
    Dash = None
    html = None


def _read_dashboard_html(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"<html><body><h2>Missing dashboard: {p}</h2></body></html>"
    return p.read_text(encoding='utf-8')


# Create app only if Dash is available; tests will import this module and expect `app` attr
if Dash is not None:
    app = Dash(__name__)

    # Attempt to read the docs HTML and embed via iframe
    live_html = _read_dashboard_html(os.path.join(os.getcwd(), 'docs', 'live_trading_dashboard.html'))
    equity_html = _read_dashboard_html(os.path.join(os.getcwd(), 'docs', 'equity_curve_dashboard.html'))

    app.layout = html.Div([
        html.H2('Live Trading Dashboard (Preview)'),
        # Use iframe with srcDoc so the server does not need to serve static files separately
        html.Iframe(srcDoc=live_html, style={'width': '100%', 'height': '700px'}, id='live-dashboard'),
        html.Hr(),
        html.H3('Equity Curve'),
        html.Iframe(srcDoc=equity_html, style={'width': '100%', 'height': '300px'}, id='equity-curve')
    ])
else:
    app = None


def run_server(host='0.0.0.0', port=8050, debug=True):
    if app is None:
        raise RuntimeError('Dash is not installed. Install with: pip install dash')
    app.run_server(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
```

- [ ] **Step 2: Ensure package init exists**

If `src/dashboard/__init__.py` is missing, create an empty file to make imports work.

```bash
mkdir -p src/dashboard
touch src/dashboard/__init__.py
```

- [ ] **Step 3: Run tests**

Run:
```
pytest tests/test_dash_app.py -q
```
Expected: PASS

- [ ] **Step 4: Commit implementation**

```bash
git add src/dashboard/dash_app.py src/dashboard/__init__.py
git commit -m "feat(dashboard): add minimal Dash app embedding generated HTML dashboards" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```


### Task 3: Developer guide & run instructions

**Files:**
- Modify: `docs/Project_Documentation/dashboard_run_guide.md` (or create if missing) — add a short section describing how to run the Dash app.

- [ ] **Step 1: Install dependency**

Run (recommended inside venv):
```
pip install dash
```

- [ ] **Step 2: Start the app**

Run:
```
python -m src.dashboard.dash_app
```
Open browser: http://127.0.0.1:8050/

- [ ] **Step 3: Non-blocking dev run (optional)**

For development with autoreload, use `python -m src.dashboard.dash_app` with `debug=True` (default in run_server). If running in CI without display, tests import the module and will not start the server.


### Self-review checklist

1. Spec coverage: This plan implements a live preview for existing generated dashboards without refactoring generators. If later the user wants interactive controls (time-range, resolver, training/test toggle), add a follow-up plan.

2. Placeholder scan: No placeholders remain — tests and implementation code are explicit.

3. Type consistency: All functions and module names used are consistent within tasks.


---

Plan saved to `docs/superpowers/plans/2026-05-21-live-dashboard.md`.

Two execution options:
1. Subagent-driven (recommended) — dispatch a subagent per task using superpowers:subagent-driven-development.
2. Inline Execution — proceed now in this session; I can implement Task 1 and Task 2 (test + implementation) and run tests.

Which execution mode? (Reply with "Subagent" or "Inline")
