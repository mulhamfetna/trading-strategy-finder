import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_dash_app_import_and_layout(monkeypatch, tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    html_file = docs / "live_trading_dashboard.html"
    html_file.write_text("<html><body><h1>TEST DASHBOARD</h1></body></html>", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("src.dashboard.dash_app")

    assert hasattr(module, "app")
    app = module.app
    assert hasattr(app, "server")

    layout_str = str(app.layout)
    assert "Iframe" in layout_str or "live-dashboard" in layout_str
