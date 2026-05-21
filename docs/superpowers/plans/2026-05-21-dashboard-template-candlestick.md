# Dashboard Template + Candlestick View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the dashboard HTML into a reusable template, switch the main chart to a candlestick view, and make open/close prices explicit in the dashboard output.

**Architecture:** Keep data preparation in Python, but move the HTML shell into a standalone template file and render it through a small dependency-free template loader. The dashboard should keep producing the same metrics/trade payloads, while the chart presentation changes from close-only emphasis to OHLC candlesticks with a compact open/close summary panel.

**Tech Stack:** Python 3, standard library `string`, pandas, Plotly, pytest

---

## File Structure and Responsibilities

- **Create:** `templates/ultimate_dashboard.html.tpl` — static dashboard shell, CSS, Plotly script, and placeholder tokens.
- **Create:** `src/dashboard/template_renderer.py` — load template files, replace placeholder tokens, and return/write final HTML.
- **Modify:** `ultimate_dashboard.py` — stop hardcoding the full HTML string; build the dashboard context and call the renderer.
- **Modify:** `tests/test_ultimate_dashboard.py` — cover candlestick output and rendered HTML output path.
- **Modify:** `tests/test_dashboard.py` — cover template rendering behavior directly.

### Task 1: Add Failing Tests for Template Rendering and Candlestick Output

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_ultimate_dashboard.py`

- [ ] **Step 1: Write the failing template-rendering test**

```python
from pathlib import Path
from src.dashboard.template_renderer import render_template


def test_render_template_replaces_placeholders(tmp_path):
    template_path = tmp_path / "dashboard.tpl"
    template_path.write_text("Hello {{NAME}} from {{CITY}}", encoding="utf-8")

    rendered = render_template(template_path, {"NAME": "NQ", "CITY": "Chicago"})

    assert rendered == "Hello NQ from Chicago"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_render_template_replaces_placeholders -v`
Expected: FAIL with `ModuleNotFoundError` or missing `render_template`.

- [ ] **Step 3: Write the failing candlestick dashboard test**

```python
import os
import numpy as np
from ultimate_dashboard import generate_html


def test_generate_html_uses_candlestick_chart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("output/dashboard", exist_ok=True)

    data = {
        "metrics": {
            "gross_profit": 0.0,
            "total_fees": 0.0,
            "net_profit": 0.0,
            "total_profit": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "final_capital": 10000.0,
            "expected_value": 0.0,
            "max_consecutive_losses": 0,
        },
        "trades": [],
        "logs": [],
        "insights": {"key_findings": [], "recommendations": []},
        "chart_data": {
            "dates": ["2025-09-01 09:30:00"],
            "opens": [100.0],
            "highs": [101.0],
            "lows": [99.5],
            "closes": [100.5],
            "volumes": [1000],
            "ema_5": [100.25],
            "ema_15": [100.1],
            "rsi": [50.0],
            "volume_spike": [False],
            "trade_markers": [],
        },
        "params": {
            "timeframe": "15min",
            "rsi_period": 5,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "ema_fast": 5,
            "ema_slow": 15,
            "volume_threshold": 1.0,
            "stop_loss": 0.6,
            "take_profit": 2.4,
            "ml_filter": True,
        },
        "final_capital": 10000.0,
        "total_return": 0.0,
    }

    html = generate_html(data)

    assert "candlestick" in html
    assert "Open" in html
    assert "Close" in html
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_generate_html_uses_candlestick_chart -v`
Expected: FAIL because `generate_html` still hardcodes a close-focused chart and does not return rendered HTML.

- [ ] **Step 5: Commit**

```bash
git add tests/test_dashboard.py tests/test_ultimate_dashboard.py
git commit -m "test: add template and candlestick dashboard coverage"
```

### Task 2: Add Dependency-Free Template Renderer

**Files:**
- Create: `src/dashboard/template_renderer.py`
- Create: `templates/ultimate_dashboard.html.tpl`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Implement the minimal renderer**

```python
from pathlib import Path


def render_template(template_path: Path, values: dict[str, str]) -> str:
    template = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    if "{{" in template or "}}" in template:
        raise KeyError("Unresolved template placeholder")
    return template
```

- [ ] **Step 2: Add a minimal template file**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{TITLE}}</title>
</head>
<body>
  {{BODY}}
</body>
</html>
```

- [ ] **Step 3: Run the renderer test**

Run: `pytest tests/test_dashboard.py::test_render_template_replaces_placeholders -v`
Expected: PASS.

- [ ] **Step 4: Add an error-path test for missing placeholders**

```python
import pytest
from pathlib import Path
from src.dashboard.template_renderer import render_template


def test_render_template_raises_on_missing_placeholder(tmp_path):
    template_path = tmp_path / "dashboard.tpl"
    template_path.write_text("Hello {{NAME}}", encoding="utf-8")

    with pytest.raises(KeyError):
        render_template(template_path, {})
```

- [ ] **Step 5: Run the error-path test**

Run: `pytest tests/test_dashboard.py::test_render_template_raises_on_missing_placeholder -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/template_renderer.py templates/ultimate_dashboard.html.tpl tests/test_dashboard.py
git commit -m "feat(dashboard): add dependency-free template renderer"
```

### Task 3: Refactor Dashboard Generation to Use the Template

**Files:**
- Modify: `ultimate_dashboard.py`
- Modify: `src/dashboard/template_renderer.py`
- Modify: `templates/ultimate_dashboard.html.tpl`
- Modify: `tests/test_ultimate_dashboard.py`

- [ ] **Step 1: Add a test that the generator writes output HTML through the renderer**

```python
import os


def test_generate_html_writes_rendered_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("output/dashboard", exist_ok=True)

    from ultimate_dashboard import generate_html

    data = {
        "metrics": {
            "gross_profit": 0.0,
            "total_fees": 0.0,
            "net_profit": 0.0,
            "total_profit": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "final_capital": 10000.0,
            "expected_value": 0.0,
            "max_consecutive_losses": 0,
        },
        "trades": [],
        "logs": [],
        "insights": {"key_findings": [], "recommendations": []},
        "chart_data": {
            "dates": ["2025-09-01 09:30:00"],
            "opens": [100.0],
            "highs": [101.0],
            "lows": [99.5],
            "closes": [100.5],
            "volumes": [1000],
            "ema_5": [100.25],
            "ema_15": [100.1],
            "rsi": [50.0],
            "volume_spike": [False],
            "trade_markers": [],
        },
        "params": {
            "timeframe": "15min",
            "rsi_period": 5,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "ema_fast": 5,
            "ema_slow": 15,
            "volume_threshold": 1.0,
            "stop_loss": 0.6,
            "take_profit": 2.4,
            "ml_filter": True,
        },
        "final_capital": 10000.0,
        "total_return": 0.0,
    }

    html = generate_html(data)
    assert "<html" in html.lower()
    assert (tmp_path / "output" / "dashboard" / "ultimate_trading_dashboard_test.html").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_generate_html_writes_rendered_output -v`
Expected: FAIL because `generate_html` still embeds the whole HTML string inline and does not return rendered HTML.

- [ ] **Step 3: Move the HTML shell into the template**

```python
from pathlib import Path
from src.dashboard.template_renderer import render_template

def generate_html(data):
    template_path = Path("templates/ultimate_dashboard.html.tpl")
    values = build_template_values(data)
    html = render_template(template_path, values)
    output_path = Path("output/dashboard/ultimate_trading_dashboard_test.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return html
```

- [ ] **Step 4: Update the template placeholders for metrics, trades, logs, insights, and chart JSON**

```html
{{TITLE}}
{{METRICS_GRID}}
{{TRADES_HTML}}
{{LOGS_HTML}}
{{INSIGHTS_HTML}}
{{CHART_JSON}}
{{OHLC_SUMMARY}}
```

- [ ] **Step 5: Run the targeted dashboard tests**

Run: `pytest tests/test_ultimate_dashboard.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ultimate_dashboard.py src/dashboard/template_renderer.py templates/ultimate_dashboard.html.tpl tests/test_ultimate_dashboard.py
git commit -m "refactor(dashboard): render dashboard from template"
```

### Task 4: Switch Chart to Candlestick View and Add OHLC Summary

**Files:**
- Modify: `ultimate_dashboard.py`
- Modify: `tests/test_ultimate_dashboard.py`

- [ ] **Step 1: Add a chart payload test that checks OHLC candlestick data**

```python
def test_generate_html_uses_ohlc_candles():
    data = {
        "metrics": {
            "gross_profit": 0.0,
            "total_fees": 0.0,
            "net_profit": 0.0,
            "total_profit": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "final_capital": 10000.0,
            "expected_value": 0.0,
            "max_consecutive_losses": 0,
        },
        "trades": [],
        "logs": [],
        "insights": {"key_findings": [], "recommendations": []},
        "chart_data": {
            "dates": ["2025-09-01 09:30:00"],
            "opens": [100.0],
            "highs": [101.0],
            "lows": [99.5],
            "closes": [100.5],
            "volumes": [1000],
            "ema_5": [100.25],
            "ema_15": [100.1],
            "rsi": [50.0],
            "volume_spike": [False],
            "trade_markers": [],
        },
        "params": {
            "timeframe": "15min",
            "rsi_period": 5,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "ema_fast": 5,
            "ema_slow": 15,
            "volume_threshold": 1.0,
            "stop_loss": 0.6,
            "take_profit": 2.4,
            "ml_filter": True,
        },
        "final_capital": 10000.0,
        "total_return": 0.0,
    }
    html = generate_html(data)

    assert "type: 'candlestick'" in html
    assert "Open" in html
    assert "High" in html
    assert "Low" in html
    assert "Close" in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_generate_html_uses_ohlc_candles -v`
Expected: FAIL until the Plotly trace is switched from line to candlestick.

- [ ] **Step 3: Replace the close-line trace with a candlestick trace**

```python
candlestick_trace = {
    "x": chartData.dates,
    "open": chartData.opens,
    "high": chartData.highs,
    "low": chartData.lows,
    "close": chartData.closes,
    "type": "candlestick",
    "name": "OHLC",
}
```

- [ ] **Step 4: Add an OHLC summary card to the dashboard body**

```python
ohlc_summary = f"""
<div class="metric-box">
  <div class="metric-value">${chart_data['opens'][-1]:.2f}</div>
  <div class="metric-label">Latest Open</div>
</div>
<div class="metric-box">
  <div class="metric-value">${chart_data['closes'][-1]:.2f}</div>
  <div class="metric-label">Latest Close</div>
</div>
"""
```

- [ ] **Step 5: Run the dashboard tests again**

Run: `pytest tests/test_ultimate_dashboard.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ultimate_dashboard.py tests/test_ultimate_dashboard.py
git commit -m "feat(dashboard): add candlestick OHLC chart"
```

### Task 5: Regenerate the Dashboard Artifact and Validate Output

**Files:**
- Modify: `output/dashboard/ultimate_trading_dashboard_test.html`
- Modify: `output/dashboard/dashboard_data_test.json`
- Modify: `README.md` only if the output path needs a short note

- [ ] **Step 1: Regenerate the dashboard from the refactored code**

Run:
```bash
python3 ultimate_dashboard.py
```

Expected:
- `output/dashboard/dashboard_data_test.json` exists
- `output/dashboard/ultimate_trading_dashboard_test.html` exists
- rendered HTML includes the candlestick chart and OHLC summary

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add output/dashboard/dashboard_data_test.json output/dashboard/ultimate_trading_dashboard_test.html README.md
git commit -m "docs+build: regenerate dashboard after template refactor"
```

---

## Spec-to-Plan Coverage Check

- Template extraction: **Task 1 + Task 2 + Task 3**
- Candlestick OHLC view: **Task 1 + Task 4 + Task 5**
- Explicit open/close visibility: **Task 1 + Task 4**
- Dependency-free renderer: **Task 2**
- Regenerated artifacts and regression safety: **Task 5**
