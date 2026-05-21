#!/usr/bin/env python3
"""
NASDAQ Trading Algorithm Finder
Main execution script for testing scalping, day trading, and intraday strategies
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data.loader import load_data
from src.data.splitter import filter_2025, split_train_test
from src.indicators.scalping import calculate_rsi, calculate_ema, calculate_volume_spike
from src.indicators.day_trading import calculate_day_trading_indicators
from src.indicators.intraday import calculate_intraday_indicators
from src.signals.base_signals import (
    generate_scalping_signals,
    generate_day_trading_signals,
    generate_intraday_signals
)
from src.signals.ml_filter import train_ml_filter, apply_ml_filter, add_ml_features
from src.backtest.engine import run_backtest
from src.backtest.metrics import calculate_metrics
from src.dashboard.report import generate_comparison_report, generate_error_analysis


def run_scalping_strategy(train_df, test_df, initial_capital=10000):
    """Run scalping strategy on 1min data."""
    print("\n--- Testing Scalping Strategy (1min) ---")
    
    # Optimized parameters from fast_optimizer.py
    train_data = calculate_rsi(train_df.copy(), period=5)
    train_data = calculate_ema(train_data, periods=[5, 15])
    train_data = calculate_volume_spike(train_data, threshold=2.0)
    train_data = generate_scalping_signals(train_data, rsi_period=5)
    train_data = add_ml_features(train_data)
    ml_data = train_ml_filter(train_data)
    
    # CRITICAL FIX: Reverse test data so it's ascending (oldest first)
    # Data was loaded in descending order causing exit before entry timestamps
    test_data = test_df.copy().reset_index(drop=True)[::-1].reset_index(drop=True)
    print(f"  Data reversed for ascending order. First: {test_data.iloc[0]['Date']} {test_data.iloc[0]['Time']}")
    
    test_data = calculate_rsi(test_data, period=5)
    test_data = calculate_ema(test_data, periods=[5, 15])
    test_data = calculate_volume_spike(test_data, threshold=2.0)
    test_data = generate_scalping_signals(test_data, rsi_period=5)
    test_data = add_ml_features(test_data)
    test_data = apply_ml_filter(test_data, ml_data)
    
    trades, final_capital = run_backtest(
        test_data,
        initial_capital=initial_capital,
        stop_loss=0.6,
        take_profit=1.8,
        max_daily_trades=10,
        fee_per_trade=10.0
    )
    
    metrics = calculate_metrics(trades, initial_capital)
    
    print(f"  Net Profit: ${metrics['total_profit']:.2f}")
    print(f"  Total Fees: ${metrics['total_fees']:.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    return trades, metrics


def run_day_trading_strategy(train_df, test_df, initial_capital=10000):
    """Run day trading strategy on 15min data."""
    print("\n--- Testing Day Trading Strategy (15min) ---")
    
    train_data = calculate_day_trading_indicators(train_df.copy())
    train_data = generate_day_trading_signals(train_data)
    train_data = add_ml_features(train_data)
    ml_data = train_ml_filter(train_data)
    
    test_data = calculate_day_trading_indicators(test_df.copy())
    test_data = generate_day_trading_signals(test_data)
    test_data = apply_ml_filter(test_data, ml_data)
    
    trades, final_capital = run_backtest(
        test_data,
        initial_capital=initial_capital,
        stop_loss=1.0,
        take_profit=2.0,
        max_daily_trades=5
    )
    
    metrics = calculate_metrics(trades, initial_capital)
    
    print(f"  Total Profit: ${metrics['total_profit']:.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    return trades, metrics


def run_intraday_strategy(train_df, test_df, initial_capital=10000):
    """Run intraday/swing strategy on 15min data."""
    print("\n--- Testing Intraday/Swing Strategy (15min) ---")
    
    train_data = calculate_intraday_indicators(train_df.copy())
    train_data = generate_intraday_signals(train_data)
    train_data = add_ml_features(train_data)
    ml_data = train_ml_filter(train_data)
    
    test_data = calculate_intraday_indicators(test_df.copy())
    test_data = generate_intraday_signals(test_data)
    test_data = apply_ml_filter(test_data, ml_data)
    
    trades, final_capital = run_backtest(
        test_data,
        initial_capital=initial_capital,
        stop_loss=1.0,
        take_profit=2.0,
        max_daily_trades=3
    )
    
    metrics = calculate_metrics(trades, initial_capital)
    
    print(f"  Total Profit: ${metrics['total_profit']:.2f}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    return trades, metrics


def main():
    print("=" * 60)
    print("NASDAQ Trading Algorithm Finder")
    print("=" * 60)
    
    initial_capital = 10000
    results = {}
    all_trades = {}
    
    try:
        print("\nLoading 1min data...")
        df_1min = load_data('1min.csv')
        df_1min_2025 = filter_2025(df_1min)
        train_1min, test_1min = split_train_test(df_1min_2025, '2025-06-30')
        print(f"  1min data: Train={len(train_1min)}, Test={len(test_1min)}")
        
        print("\nLoading 15min data...")
        df_15min = load_data('NQ_15min_processed.csv')
        df_15min_2025 = filter_2025(df_15min)
        train_15min, test_15min = split_train_test(df_15min_2025, '2025-06-30')
        print(f"  15min data: Train={len(train_15min)}, Test={len(test_15min)}")
        
        if len(train_1min) > 100 and len(test_1min) > 50:
            trades_scalping, metrics_scalping = run_scalping_strategy(train_1min, test_1min, initial_capital)
            results['scalping'] = metrics_scalping
            all_trades['scalping'] = trades_scalping
        else:
            print("\n  Skipping scalping - not enough 2025 data")
        
        if len(train_15min) > 100 and len(test_15min) > 50:
            trades_day, metrics_day = run_day_trading_strategy(train_15min, test_15min, initial_capital)
            results['day_trading'] = metrics_day
            all_trades['day_trading'] = trades_day
            
            trades_intra, metrics_intra = run_intraday_strategy(train_15min, test_15min, initial_capital)
            results['intraday'] = metrics_intra
            all_trades['intraday'] = trades_intra
        else:
            print("\n  Skipping day trading/intraday - not enough 2025 data")
        
        print("\n" + "=" * 60)
        print("COMPARISON RESULTS")
        print("=" * 60)
        
        for strategy, metrics in results.items():
            print(f"\n{strategy.upper()}:")
            print(f"  Total Profit: ${metrics['total_profit']:.2f}")
            print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"  Total Trades: {metrics['total_trades']}")
        
        if results:
            report = generate_comparison_report(results)
            print(f"\n{'=' * 60}")
            print(f"BEST STRATEGY: {report['best_strategy'].upper()}")
            print(f"RECOMMENDATION: {report['recommendation']}")
            print(f"CONFIDENCE: {report['confidence']}")
            print(f"{'=' * 60}")
            
            print("\n--- Error Analysis ---")
            for strategy, trades in all_trades.items():
                error_analysis = generate_error_analysis(trades)
                print(f"{strategy}: {error_analysis['analysis']}")
        
        print("\nDone!")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Make sure 1min.csv and NQ_15min_processed.csv are in the current directory")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()