"""Smoke test for the legacy `app` module-level attribute on
``src/dashboard/dash_app.py``. Iter 8 replaced the iframe-based preview
with a native interactive app; the module-level ``app`` is now built
via ``build_app()`` so existing `python -m src.dashboard.dash_app`
invocations still work."""

import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_dash_app_import_and_layout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("src.dashboard.dash_app")

    assert hasattr(module, "app")
    app = module.app
    assert hasattr(app, "server")

    # New layout (iter 8) is native components, not iframes.
    layout_str = str(app.layout)
    assert "Iframe" not in layout_str
    # The Apply button must be present in the resolver controls.
    assert "apply-btn" in layout_str
