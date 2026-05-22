import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.main.live_dashboard import get_output_paths


def test_get_output_paths_uses_output_dashboards_directory():
    """Iter 3 (TODO item 11): live dashboard writes to output/dashboards/
    (plural), matching the unified output layout."""
    live_path, equity_path = get_output_paths()

    assert live_path == os.path.join("output", "dashboards", "live_trading_dashboard.html")
    assert equity_path == os.path.join("output", "dashboards", "equity_curve_dashboard.html")
