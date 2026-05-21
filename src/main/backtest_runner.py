from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, Tuple

import pandas as pd


def resolve_exit_price_and_reason(
    direction: int,
    entry_price: float,
    high: float,
    low: float,
    close: float,
    stop_loss: float,
    take_profit: float,
) -> Tuple[float, str | None]:
    """Resolve the exit price for a sampled candle.

    Conservative policy: if both TP and SL are reachable in the same candle,
    assume the stop loss is hit first.
    """
    if direction == 1:
        sl_price = entry_price * (1 - stop_loss / 100)
        tp_price = entry_price * (1 + take_profit / 100)
        sl_hit = low <= sl_price
        tp_hit = high >= tp_price
    else:
        sl_price = entry_price * (1 + stop_loss / 100)
        tp_price = entry_price * (1 - take_profit / 100)
        sl_hit = high >= sl_price
        tp_hit = low <= tp_price

    if sl_hit and tp_hit:
        return sl_price, "SL"
    if sl_hit:
        return sl_price, "SL"
    if tp_hit:
        return tp_price, "TP"
    return close, None


def compute_coverage_metadata(df: pd.DataFrame, requested_start: str, requested_end: str) -> Dict[str, Any]:
    """Summarize requested vs actual data coverage."""
    if df.empty:
        return {
            "requested_start": requested_start,
            "requested_end": requested_end,
            "actual_start": None,
            "actual_end": None,
            "rows": 0,
            "has_gap": True,
        }

    dates = pd.to_datetime(df["Date"])
    actual_start = dates.min().strftime("%Y-%m-%d")
    actual_end = dates.max().strftime("%Y-%m-%d")

    return {
        "requested_start": requested_start,
        "requested_end": requested_end,
        "actual_start": actual_start,
        "actual_end": actual_end,
        "rows": int(len(df)),
        "has_gap": actual_start != requested_start or actual_end != requested_end,
    }


def _import_dashboard_helpers():
    from ultimate_dashboard import (
        analyze_trade,
        apply_ml_filter,
        apply_rsi_entry_filters,
        generate_insights,
        generate_html,
        generate_logs,
        prepare_chart_data,
        prepare_data,
        run_backtest_15min,
        train_ml,
        resample_15min,
    )

    return {
        "analyze_trade": analyze_trade,
        "apply_ml_filter": apply_ml_filter,
        "apply_rsi_entry_filters": apply_rsi_entry_filters,
        "generate_insights": generate_insights,
        "generate_html": generate_html,
        "generate_logs": generate_logs,
        "prepare_chart_data": prepare_chart_data,
        "prepare_data": prepare_data,
        "run_backtest_15min": run_backtest_15min,
        "train_ml": train_ml,
        "resample_15min": resample_15min,
    }


def build_dashboard_payload_from_splits(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    initial_capital: float = 10000.0,
    stop_loss: float = 0.6,
    take_profit: float = 2.4,
    fee_per_trade: float = 10.0,
    point_value: float = 2.0,
) -> Dict[str, Any]:
    """Build the dashboard payload from train/test splits."""
    helpers = _import_dashboard_helpers()
    from src.backtest.metrics import calculate_metrics

    train_prep = helpers["prepare_data"](train_df)
    test_prep = helpers["prepare_data"](test_df)
    ml_data = helpers["train_ml"](train_prep, rsi_thresh=25)

    signals = helpers["apply_ml_filter"](test_prep, ml_data)
    signals = helpers["apply_rsi_entry_filters"](
        signals,
        test_prep["rsi_5"].values,
        oversold=25,
        overbought=75,
    )

    trades, final_capital = helpers["run_backtest_15min"](
        signals,
        test_prep["Close"].values,
        test_prep,
        initial_capital=initial_capital,
        stop_loss=stop_loss,
        take_profit=take_profit,
        fee_per_trade=fee_per_trade,
        point_value=point_value,
    )
    metrics = calculate_metrics(trades, initial_capital)

    trade_analysis = [
        helpers["analyze_trade"](test_prep, trade, index + 1)
        for index, trade in enumerate(trades)
    ]

    logs = helpers["generate_logs"](trades, test_prep, metrics)
    insights = helpers["generate_insights"](trades, metrics)
    chart_data = helpers["prepare_chart_data"](test_prep, trades)

    winning_trades = [trade for trade in trade_analysis if trade["is_winner"]]
    losing_trades = [trade for trade in trade_analysis if not trade["is_winner"]]

    return {
        "metrics": metrics,
        "trades": trade_analysis,
        "logs": logs,
        "insights": insights,
        "chart_data": chart_data,
        "params": {
            "timeframe": "15min",
            "rsi_period": 5,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "ema_fast": 5,
            "ema_slow": 15,
            "volume_threshold": 1.0,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ml_filter": True,
        },
        "winning_count": len(winning_trades),
        "losing_count": len(losing_trades),
        "final_capital": final_capital,
        "total_return": (final_capital - initial_capital) / 100,
    }


def run_period_backtest(
    df: pd.DataFrame,
    requested_start: str,
    requested_end: str,
    *,
    initial_capital: float = 10000.0,
    stop_loss: float = 0.6,
    take_profit: float = 2.4,
    fee_per_trade: float = 10.0,
    point_value: float = 2.0,
) -> Dict[str, Any]:
    """Run the frozen strategy on a requested date window."""
    helpers = _import_dashboard_helpers()
    from src.backtest.metrics import calculate_metrics
    date_series = pd.to_datetime(df["Date"])
    mask = (date_series >= pd.Timestamp(requested_start)) & (date_series <= pd.Timestamp(requested_end))
    subset = df.loc[mask].copy()

    coverage = compute_coverage_metadata(subset, requested_start, requested_end)
    if subset.empty:
        metrics = calculate_metrics([], initial_capital)
        return {
            "metrics": metrics,
            "trades": [],
            "coverage": coverage,
            "final_capital": initial_capital,
        }

    subset_15 = helpers["resample_15min"](subset.reset_index(drop=True))
    subset_prep = helpers["prepare_data"](subset_15)
    ml_data = helpers["train_ml"](subset_prep, rsi_thresh=25)
    signals = helpers["apply_ml_filter"](subset_prep, ml_data)
    signals = helpers["apply_rsi_entry_filters"](
        signals,
        subset_prep["rsi_5"].values,
        oversold=25,
        overbought=75,
    )

    trades, final_capital = helpers["run_backtest_15min"](
        signals,
        subset_prep["Close"].values,
        subset_prep,
        initial_capital=initial_capital,
        stop_loss=stop_loss,
        take_profit=take_profit,
        fee_per_trade=fee_per_trade,
        point_value=point_value,
    )
    metrics = calculate_metrics(trades, initial_capital)

    return {
        "metrics": metrics,
        "trades": trades,
        "coverage": coverage,
        "final_capital": final_capital,
    }


def save_dashboard_payload(
    dashboard_data: Dict[str, Any],
    output_dir: str = "output/dashboard",
    basename: str = "test",
) -> Dict[str, str]:
    """Persist dashboard JSON and HTML to the output directory."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    json_path = os.path.join(output_dir, f"dashboard_data_{basename}.json")
    html_path = os.path.join(output_dir, f"ultimate_trading_dashboard_{basename}.html")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    helpers = _import_dashboard_helpers()
    helpers["generate_html"](dashboard_data)

    legacy_html = os.path.join("docs", "ultimate_trading_dashboard.html")
    if os.path.exists(legacy_html):
        shutil.copyfile(legacy_html, html_path)

    return {"json_path": json_path, "html_path": html_path}
