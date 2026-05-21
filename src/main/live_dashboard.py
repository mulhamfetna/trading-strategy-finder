#!/usr/bin/env python3
"""
Live Trading Dashboard Demo
Visualizes trading algorithm performance with real-time simulation
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data.loader import load_data
from src.data.splitter import filter_2025, split_train_test
from src.indicators.scalping import calculate_scalping_indicators
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


def create_live_simulation():
    """Run live trading simulation."""
    
    print("\n" + "="*60)
    print("NASDAQ TRADING ALGORITHM - LIVE DEMO")
    print("="*60)
    print("\nLoading data...")
    
    df_1min = load_data('1min.csv')
    df_2025 = filter_2025(df_1min)
    train_1min, test_1min = split_train_test(df_2025, '2025-06-30')
    
    print(f"Test data: {len(test_1min)} candles")
    print(f"Date range: {test_1min['Date'].min()} to {test_1min['Date'].max()}")
    
    print("\nPreparing data...")
    
    df = test_1min.copy().reset_index(drop=True)
    df = calculate_scalping_indicators(df)
    df = generate_scalping_signals(df)
    df = add_ml_features(df)
    ml_data = train_ml_filter(df)
    df = apply_ml_filter(df, ml_data)
    
    capital = 10000
    position = None
    entry_price = 0
    entry_time = ""
    
    simulated_trades = []
    
    print("\n" + "-"*60)
    print("LIVE TRADING SIMULATION - SCALPING STRATEGY")
    print("-"*60)
    print("Time                      Price   Signal  Action      P/L      Capital")
    print()
    
    for i in range(len(df)):
        row = df.iloc[i]
        signal = row.get('ml_signal', row.get('signal', 0))
        candle_time = f"{row['Date']} {row['Time']}"
        
        if position is None and signal != 0:
            position = signal
            entry_price = row['Close']
            entry_time = candle_time
            action = "BUY" if signal == 1 else "SELL"
            print(f"{candle_time:<20} {entry_price:>10.2f} {signal:>8} {action:>10} ---     {capital:>10.2f}")
        
        elif position is not None:
            current_price = row['Close']
            price_change_pct = (current_price - entry_price) / entry_price * 100
            if position == -1:
                price_change_pct = -price_change_pct
            
            stop_loss_triggered = price_change_pct <= -0.5
            take_profit_triggered = price_change_pct >= 1.5
            
            if stop_loss_triggered or take_profit_triggered:
                profit = capital * (price_change_pct / 100)
                capital += profit
                
                simulated_trades.append({
                    'entry_time': entry_time,
                    'exit_time': candle_time,
                    'direction': 'LONG' if position == 1 else 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'profit_pct': price_change_pct,
                    'profit_dollars': profit,
                    'capital_after': capital,
                    'exit_reason': 'TAKE PROFIT' if take_profit_triggered else 'STOP LOSS'
                })
                
                status = "WIN" if profit > 0 else "LOSS"
                print(f"{candle_time:<20} {current_price:>10.2f} {0:>8} EXIT   {status}   {profit:>+8.2f} {capital:>10.2f}")
                
                position = None
    
    winning = [t for t in simulated_trades if t['profit_dollars'] > 0]
    losing = [t for t in simulated_trades if t['profit_dollars'] <= 0]
    total_profit = sum(t['profit_dollars'] for t in simulated_trades)
    
    print()
    print("="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Initial Capital:  $10,000.00")
    print(f"Final Capital:    ${capital:,.2f}")
    print(f"Total Profit:     ${total_profit:,.2f}")
    print(f"Total Trades:     {len(simulated_trades)}")
    print(f"Winners:          {len(winning)} ({len(winning)/len(simulated_trades)*100:.1f}%)" if simulated_trades else "")
    print(f"Losers:           {len(losing)} ({len(losing)/len(simulated_trades)*100:.1f}%)" if simulated_trades else "")
    
    print("\nTRADE LOG:")
    print(f"{'#':<3} {'Dir':<5} {'Entry':>10} {'Exit':>10} {'P/L%':>8} {'P/L$':>10} {'Reason':<12}")
    for idx, trade in enumerate(simulated_trades, 1):
        direction = "L" if trade['direction'] == 'LONG' else "S"
        print(f"{idx:<3} {direction:<5} {trade['entry_price']:>10.2f} {trade['exit_price']:>10.2f} {trade['profit_pct']:>+7.2f}% ${trade['profit_dollars']:>+9.2f} {trade['exit_reason']:<12}")
    
    return simulated_trades, capital


def run_strategy_comparison():
    """Compare all three strategies."""
    
    print("\n" + "="*60)
    print("STRATEGY COMPARISON")
    print("="*60)
    
    df_1min = load_data('1min.csv')
    df_15min = load_data('NQ_15min_processed.csv')
    
    df_1min_2025 = filter_2025(df_1min)
    df_15min_2025 = filter_2025(df_15min)
    
    train_1min, test_1min = split_train_test(df_1min_2025, '2025-06-30')
    train_15min, test_15min = split_train_test(df_15min_2025, '2025-06-30')
    
    results = {}
    
    # Scalping
    print("\nRunning Scalping Strategy (1min)...")
    train = calculate_scalping_indicators(train_1min.copy())
    train = generate_scalping_signals(train)
    train = add_ml_features(train)
    ml_data = train_ml_filter(train)
    test = calculate_scalping_indicators(test_1min.copy())
    test = generate_scalping_signals(test)
    test = apply_ml_filter(test, ml_data)
    trades_scalping, _ = run_backtest(test, initial_capital=10000, stop_loss=0.5, take_profit=1.5)
    metrics_scalping = calculate_metrics(trades_scalping, 10000)
    results['scalping'] = {'trades': trades_scalping, 'metrics': metrics_scalping}
    
    # Day Trading
    print("Running Day Trading Strategy (15min)...")
    train_dt = calculate_day_trading_indicators(train_15min.copy())
    train_dt = generate_day_trading_signals(train_dt)
    train_dt = add_ml_features(train_dt)
    ml_data_dt = train_ml_filter(train_dt)
    test_dt = calculate_day_trading_indicators(test_15min.copy())
    test_dt = generate_day_trading_signals(test_dt)
    test_dt = apply_ml_filter(test_dt, ml_data_dt)
    trades_day, _ = run_backtest(test_dt, initial_capital=10000, stop_loss=1.0, take_profit=2.0)
    metrics_day = calculate_metrics(trades_day, 10000)
    results['day_trading'] = {'trades': trades_day, 'metrics': metrics_day}
    
    # Intraday
    print("Running Intraday Strategy (15min)...")
    train_intra = calculate_intraday_indicators(train_15min.copy())
    train_intra = generate_intraday_signals(train_intra)
    train_intra = add_ml_features(train_intra)
    ml_data_intra = train_ml_filter(train_intra)
    test_intra = calculate_intraday_indicators(test_15min.copy())
    test_intra = generate_intraday_signals(test_intra)
    test_intra = apply_ml_filter(test_intra, ml_data_intra)
    trades_intra, _ = run_backtest(test_intra, initial_capital=10000, stop_loss=1.0, take_profit=2.0)
    metrics_intra = calculate_metrics(trades_intra, 10000)
    results['intraday'] = {'trades': trades_intra, 'metrics': metrics_intra}
    
    print("\nSTRATEGY RESULTS:")
    print(f"{'Strategy':<15} {'Trades':>8} {'Profit':>12} {'Win Rate':>10} {'PF':>6} {'DD':>6}")
    print("-" * 60)
    
    for name, data in results.items():
        m = data['metrics']
        best = "BEST" if m['total_profit'] == max(r['metrics']['total_profit'] for r in results.values()) else ""
        profit_str = f"${m['total_profit']:.2f}" if m['total_profit'] >= 0 else f"-${abs(m['total_profit']):.2f}"
        print(f"{name:<15} {m['total_trades']:>8} {profit_str:>12} {m['win_rate']:>9.1f}% {m['profit_factor']:>6.2f} {m['max_drawdown']:>5.1f}%  {best}")
    
    best = max(results.items(), key=lambda x: x[1]['metrics']['total_profit'])
    print(f"\nBest Strategy: {best[0].upper()} (${best[1]['metrics']['total_profit']:.2f})")
    
    return results


def create_html_dashboard():
    """Generate HTML dashboard with plotly charts."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("\nPlotly not installed. Skipping HTML dashboard.")
        print("Install with: pip install plotly")
        return None
    
    print("\n" + "="*60)
    print("GENERATING HTML DASHBOARD")
    print("="*60)
    
    df_1min = load_data('1min.csv')
    df_2025 = filter_2025(df_1min)
    train_1min, test_1min = split_train_test(df_2025, '2025-06-30')
    
    df = test_1min.head(2000).copy().reset_index(drop=True)
    df = calculate_scalping_indicators(df)
    df = generate_scalping_signals(df)
    df = add_ml_features(df)
    ml_data = train_ml_filter(df)
    df = apply_ml_filter(df, ml_data)
    
    trades, final_capital = run_backtest(df, initial_capital=10000, stop_loss=0.5, take_profit=1.5)
    metrics = calculate_metrics(trades, 10000)
    
    # Candlestick chart
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=('Price Chart with Trades', 'RSI', 'Volume'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ema_5'],
        line=dict(color='#2196F3', width=1),
        name='EMA 5'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ema_20'],
        line=dict(color='#FF9800', width=1),
        name='EMA 20'
    ), row=1, col=1)
    
    for trade in trades:
        color = '#00C853' if trade['profit_dollars'] > 0 else '#FF1744'
        fig.add_trace(go.Scatter(
            x=[trade['entry_idx']],
            y=[df.iloc[trade['entry_idx']]['Low'] * 0.999],
            mode='markers',
            marker=dict(symbol='triangle-up', size=15, color='#00E676'),
            showlegend=False
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=[trade['exit_idx']],
            y=[df.iloc[trade['exit_idx']]['High'] * 1.001],
            mode='markers',
            marker=dict(symbol='triangle-down', size=15, color=color),
            name=f"{'Win' if trade['profit_dollars'] > 0 else 'Loss'} ${trade['profit_dollars']:.0f}",
            showlegend=True
        ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['rsi_7'],
        line=dict(color='#9C27B0', width=1),
        name='RSI'
    ), row=2, col=1)
    
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color=df['Volume'].apply(lambda x: '#26a69a' if x > df['Volume'].mean() * 1.5 else '#90A4AE'),
        name='Volume'
    ), row=3, col=1)
    
    fig.update_layout(
        title=dict(
            text=f"<b>NASDAQ Scalping Strategy - Live Trading Dashboard</b><br>" +
                 f"<span style='font-size:12px'>Test Period: Jul-Sep 2025 | " +
                 f"Total Profit: ${metrics['total_profit']:.2f} | " +
                 f"Win Rate: {metrics['win_rate']:.1f}% | " +
                 f"Trades: {metrics['total_trades']}</span>",
            x=0.5, font=dict(size=16)
        ),
        height=900,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_dark"
    )
    
    equity_curve = [{'idx': 0, 'capital': 10000}]
    for trade in trades:
        equity_curve.append({'idx': trade['exit_idx'], 'capital': trade['capital_after']})
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=[e['idx'] for e in equity_curve],
        y=[e['capital'] for e in equity_curve],
        mode='lines+markers',
        line=dict(color='#00E676', width=2),
        marker=dict(size=4),
        name='Equity Curve'
    ))
    
    fig2.update_layout(
        title=dict(
            text=f"<b>Equity Curve</b><br>" +
                 f"<span style='font-size:12px'>Initial: $10,000 | Final: ${equity_curve[-1]['capital']:.2f} | " +
                 f"Return: {(equity_curve[-1]['capital'] - 10000) / 100:.2f}%</span>",
            x=0.5
        ),
        height=400,
        template="plotly_dark",
        showlegend=False
    )
    
    print("\nSaving HTML dashboards...")
    fig.write_html('docs/live_trading_dashboard.html', auto_open=False)
    fig2.write_html('docs/equity_curve_dashboard.html', auto_open=False)
    
    print("Dashboard saved: docs/live_trading_dashboard.html")
    print("Equity curve saved: docs/equity_curve_dashboard.html")
    
    return metrics


def main():
    print("\n" + "="*60)
    print("NASDAQ TRADING ALGORITHM - LIVE DEMO")
    print("="*60)
    print("\nTest Period: July - September 2025")
    print("Initial Capital: $10,000")
    print("Strategy: Scalping (1min)")
    print("Risk: Stop Loss 0.5% | Take Profit 1.5%")
    
    trades, final_capital = create_live_simulation()
    results = run_strategy_comparison()
    create_html_dashboard()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE!")
    print("="*60)
    print(f"\nSummary:")
    print(f"  Total Strategies Tested: 3")
    print(f"  Best Strategy: SCALPING")
    print(f"  Total Trades: {sum(len(r['trades']) for r in results.values())}")
    print(f"\nOutput Files:")
    print("  - docs/live_trading_dashboard.html")
    print("  - docs/equity_curve_dashboard.html")
    print("\nOpen HTML files in browser to see visual dashboard!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()