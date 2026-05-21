import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.main.live_dashboard import get_output_paths


def test_get_output_paths_uses_output_dashboard_directory():
    live_path, equity_path = get_output_paths()

    assert live_path == "output/dashboard/live_trading_dashboard.html"
    assert equity_path == "output/dashboard/equity_curve_dashboard.html"
