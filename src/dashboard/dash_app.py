"""Minimal Dash app for previewing generated HTML dashboards."""

from pathlib import Path

from dash import Dash, html


def _read_dashboard_html(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return f"<html><body><h2>Missing dashboard: {file_path}</h2></body></html>"
    return file_path.read_text(encoding="utf-8")


app = Dash(__name__)
live_output_path = Path.cwd() / "output" / "dashboard" / "live_trading_dashboard.html"
equity_output_path = Path.cwd() / "output" / "dashboard" / "equity_curve_dashboard.html"
live_fallback_path = Path.cwd() / "docs" / "live_trading_dashboard.html"
equity_fallback_path = Path.cwd() / "docs" / "equity_curve_dashboard.html"
live_html = _read_dashboard_html(live_output_path if live_output_path.exists() else live_fallback_path)
equity_html = _read_dashboard_html(equity_output_path if equity_output_path.exists() else equity_fallback_path)

app.layout = html.Div(
    [
        html.H2("Live Trading Dashboard (Preview)"),
        html.Iframe(srcDoc=live_html, style={"width": "100%", "height": "700px"}, id="live-dashboard"),
        html.Hr(),
        html.H3("Equity Curve"),
        html.Iframe(srcDoc=equity_html, style={"width": "100%", "height": "300px"}, id="equity-curve"),
    ]
)


def run_server(host: str = "0.0.0.0", port: int = 8050, debug: bool = True) -> None:
    app.run_server(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
