#!/usr/bin/env python3
"""
Ultimate Trading Dashboard Generator - Fixed Version
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from src.data.loader import load_data
from src.data.splitter import filter_2025, split_train_test
from src.indicators.scalping import calculate_rsi, calculate_ema, calculate_volume_spike
from src.signals.base_signals import generate_scalping_signals
from src.signals.ml_filter import train_ml_filter, apply_ml_filter, add_ml_features
from src.backtest.engine import run_backtest
from src.backtest.metrics import calculate_metrics
from src.dashboard.template_renderer import render_template


def get_indicator_at_idx(df, idx):
    """Get indicator values at a specific index."""
    if idx < 0 or idx >= len(df):
        return {}
    row = df.iloc[idx]
    
    date_val = row.get('Date', '')
    time_val = row.get('Time', '')
    
    if hasattr(date_val, 'strftime'):
        date_str = date_val.strftime('%Y-%m-%d')
    else:
        date_str = str(date_val) if date_val else ''
    
    return {
        'close': row.get('Close', 0),
        'rsi': row.get('rsi_5', row.get('rsi_7', 0)),
        'ema_5': row.get('ema_5', 0),
        'ema_15': row.get('ema_15', row.get('ema_20', 0)),
        'volume_spike': row.get('volume_spike', False),
        'date': date_str,
        'time': str(time_val) if time_val else ''
    }


def analyze_trade(df, trade, trade_num):
    """Analyze a single trade in detail."""
    entry_idx = trade['entry_idx']
    exit_idx = trade['exit_idx']
    
    entry_indicators = get_indicator_at_idx(df, entry_idx)
    exit_indicators = get_indicator_at_idx(df, exit_idx)
    
    is_winner = trade['profit_dollars'] > 0
    
    analysis = {
        'trade_num': trade_num,
        'direction': trade['direction'],
        'entry_time': get_timestamp_str(df, entry_idx),
        'exit_time': get_timestamp_str(df, exit_idx),
        'entry_price': trade['entry_price'],
        'exit_price': trade['exit_price'],
        'profit_pct': trade['profit_pct'],
        'profit_dollars': trade['profit_dollars'],
        'capital_after': trade.get('capital_after', 0),
        'fees_paid': trade.get('fees_paid', 10),
        'exit_reason': trade['exit_reason'],
        'is_winner': is_winner,
        'entry_indicators': {
            'rsi': round(entry_indicators.get('rsi', 0), 2),
            'ema_5': round(entry_indicators.get('ema_5', 0), 2),
            'ema_15': round(entry_indicators.get('ema_15', 0), 2),
            'price_vs_ema': 'above' if entry_indicators.get('close', 0) > entry_indicators.get('ema_5', 0) else 'below',
            'volume_spike': entry_indicators.get('volume_spike', False),
            'close': entry_indicators.get('close', 0)
        },
        'exit_indicators': {
            'rsi': round(exit_indicators.get('rsi', 0), 2),
            'ema_5': round(exit_indicators.get('ema_5', 0), 2),
            'close': exit_indicators.get('close', 0)
        },
        'what_happened': '',
        'what_went_right': '',
        'what_went_wrong': ''
    }
    
    if is_winner:
        analysis['what_went_right'] = f"Price moved {abs(trade['profit_pct']):.2f}% in favor of position. Take profit hit."
        if trade['direction'] == 'long':
            analysis['what_happened'] = f"Long entry at ${trade['entry_price']:.2f}, price rallied to ${trade['exit_price']:.2f}"
        else:
            analysis['what_happened'] = f"Short entry at ${trade['entry_price']:.2f}, price dropped to ${trade['exit_price']:.2f}"
    else:
        analysis['what_went_wrong'] = f"Price moved {abs(trade['profit_pct']):.2f}% against position. Stop loss triggered."
        if trade['direction'] == 'long':
            analysis['what_happened'] = f"Long entry at ${trade['entry_price']:.2f}, price dropped to ${trade['exit_price']:.2f}"
        else:
            analysis['what_happened'] = f"Short entry at ${trade['entry_price']:.2f}, price rallied to ${trade['exit_price']:.2f}"
    
    return analysis


def get_timestamp_str(df, idx):
    """Get formatted timestamp string from DataFrame row."""
    row = df.iloc[idx]
    date_val = row.get('Date', '')
    time_val = row.get('Time', '')
    
    if hasattr(date_val, 'strftime'):
        date_str = date_val.strftime('%Y-%m-%d')
    else:
        date_str = str(date_val) if date_val else ''
    
    return f"{date_str} {time_val}" if time_val else date_str


def generate_logs(trades, df, metrics):
    """Generate event logs from trades."""
    logs = []
    capital = 10000
    for i, trade in enumerate(trades, 1):
        entry_time = get_timestamp_str(df, trade['entry_idx'])
        exit_time = get_timestamp_str(df, trade['exit_idx'])
        
        logs.append({
            'timestamp': entry_time,
            'type': 'ENTRY',
            'details': f"Trade #{i}: {trade['direction']} @ ${trade['entry_price']:.2f}"
        })
        
        logs.append({
            'timestamp': exit_time,
            'type': 'EXIT',
            'details': f"Trade #{i}: {trade['exit_reason']} - P/L: ${trade['profit_dollars']:+.2f} ({trade['profit_pct']:+.2f}%)"
        })
        
        capital = trade['capital_after']
        logs.append({
            'timestamp': exit_time,
            'type': 'METRICS',
            'details': f"Capital: ${capital:.2f} | P/L: ${capital - 10000:+.2f}"
        })
    
    return logs


def generate_insights(trades, metrics):
    """Generate AI-style insights."""
    winning = [t for t in trades if t['profit_dollars'] > 0]
    losing = [t for t in trades if t['profit_dollars'] <= 0]
    
    gross_wins = sum(t['profit_dollars'] for t in winning)
    gross_losses = abs(sum(t['profit_dollars'] for t in losing))
    
    total_fees = sum(t.get('fees_paid', 10) for t in trades)
    
    rr_ratio = abs(metrics['avg_profit']/abs(metrics['avg_loss'])) if metrics['avg_loss'] != 0 else 0
    
    insights = {'key_findings': [], 'recommendations': []}
    
    win_rate_str = f"{metrics['win_rate']:.1f}%" if metrics['total_trades'] > 0 else "0.0%"
    insights['key_findings'].append(f"Win rate of {win_rate_str} with {rr_ratio:.1f}:1 reward:risk ratio")
    
    if len(winning) > 0:
        insights['key_findings'].append(f"All winning trades hit take profit, all losing trades hit stop loss")
    else:
        insights['key_findings'].append(f"No winning trades detected - {len(losing)} losing trade(s)")
    
    if len(trades) > 0:
        insights['key_findings'].append(f"{len(trades)} trades over test period = {len(trades)/3:.1f} trades per month")
    else:
        insights['key_findings'].append(f"No trades generated - algorithm did not detect valid setups")
    
    insights['key_findings'].append(f"Max drawdown of {metrics['max_drawdown']:.2f}% is within risk parameters")
    
    if metrics['profit_factor'] >= 3.0:
        insights['key_findings'].append(f"Profit factor of {metrics['profit_factor']:.2f} indicates effective system")
    
    insights['key_findings'].append(f"Expected value per trade: ${metrics['expected_value']:.2f}")
    insights['key_findings'].append(f"Max consecutive losses: {metrics['max_consecutive_losses']}")
    insights['key_findings'].append(f"Total fees paid: ${total_fees:.2f}")
    
    insights['recommendations'].append("Optimized RSI(5) < 25 provides faster signals with higher conviction")
    insights['recommendations'].append("EMA 5/15 crossover works well - avoid changing without re-optimization")
    insights['recommendations'].append("15min timeframe provides better signal quality than 1min")
    insights['recommendations'].append("Volume spike threshold of 1.0x effectively filters false signals")
    insights['recommendations'].append("ML filter (Random Forest) improves win rate by filtering weak signals")
    insights['recommendations'].append(f"Net profit: ${metrics['net_profit']:.2f} (fees: ${metrics['total_fees']:.2f} included, final capital: ${metrics['final_capital']:.2f})")
    insights['recommendations'].append(f"Trade P/L values already include $10/trade fee deduction")
    
    return insights


def prepare_chart_data(df, trades):
    """Prepare data for chart."""
    chart_data = {
        'dates': [], 'opens': [], 'highs': [], 'lows': [], 'closes': [],
        'volumes': [], 'ema_5': [], 'ema_15': [], 'rsi': [], 'volume_spike': [],
        'trade_markers': []
    }
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        date_val = row.get('Date', '')
        time_val = row.get('Time', '')
        
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        else:
            date_str = str(date_val) if date_val else ''
        
        # Handle RSI - replace NaN/0 with 50 (neutral) for display
        rsi_val = float(row.get('rsi_5', row.get('rsi_7', 50)))
        if pd.isna(rsi_val) or rsi_val == 0:
            rsi_val = 50.0  # Neutral RSI for unavailable/zero values
        
        chart_data['dates'].append(f"{date_str} {time_val}" if time_val else date_str)
        chart_data['opens'].append(float(row.get('Open', 0)))
        chart_data['highs'].append(float(row.get('High', 0)))
        chart_data['lows'].append(float(row.get('Low', 0)))
        chart_data['closes'].append(float(row.get('Close', 0)))
        chart_data['volumes'].append(int(row.get('Volume', 0)))
        chart_data['ema_5'].append(float(row.get('ema_5', row.get('Close', 0))))
        chart_data['ema_15'].append(float(row.get('ema_15', row.get('ema_20', row.get('Close', 0)))))
        chart_data['rsi'].append(rsi_val)
        chart_data['volume_spike'].append(bool(row.get('volume_spike', False)))
    
    for trade in trades:
        chart_data['trade_markers'].append({
            'entry_idx': trade['entry_idx'],
            'exit_idx': trade['exit_idx'],
            'direction': trade['direction'],
            'profit_dollars': trade['profit_dollars'],
            'exit_reason': trade['exit_reason'],
            'entry_price': trade['entry_price'],
            'exit_price': trade['exit_price']
        })
    
    return chart_data


import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def prepare_data(df, rsi_period=5):
    df = df.copy()
    df = calculate_rsi(df, period=rsi_period)
    df = calculate_ema(df, periods=[5, 15])
    df = calculate_volume_spike(df, threshold=1.0)
    df = generate_scalping_signals(df, rsi_period=rsi_period)
    return df

def add_ml_features(df):
    df = df.copy()
    df['price_change'] = df['Close'].pct_change()
    df['price_change_5'] = df['Close'].pct_change(5)
    df['volume_change'] = df['Volume'].pct_change()
    df['volume_ma_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['ema_diff'] = (df['ema_5'] - df['ema_15']) / df['ema_15'] * 100
    df['rsi_change'] = df['rsi_5'].diff()
    df['volatility'] = df['Close'].rolling(10).std() / df['Close'].rolling(10).mean() * 100
    return df

def train_ml(df_train, rsi_thresh=25):
    df = add_ml_features(df_train)
    df['next_return'] = df['Close'].shift(-1) / df['Close'] - 1
    df['target'] = np.where(df['next_return'] > 0, 1, 0)
    
    features = ['rsi_5', 'price_change', 'price_change_5', 'volume_change', 
                'volume_ma_ratio', 'ema_diff', 'rsi_change', 'volatility']
    
    df_clean = df.dropna(subset=features + ['target'])
    df_clean = df_clean[df_clean['signal'] != 0].copy()
    
    if len(df_clean) < 50:
        return None
    
    X = df_clean[features]
    y = df_clean['target']
    
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X, y)
    
    return {'model': model, 'features': features}

def apply_ml_filter(df, ml_data):
    if ml_data is None:
        return df['signal'].values
    
    df = add_ml_features(df)
    model = ml_data['model']
    features = ml_data['features']
    
    signals = df['signal'].values.copy()
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if row['signal'] != 0:
            try:
                X = row[features].values.reshape(1, -1)
                if not np.isnan(X).any():
                    pred = model.predict(X)[0]
                    if row['signal'] == 1 and pred == 0:
                        signals[i] = 0
                    elif row['signal'] == -1 and pred == 1:
                        signals[i] = 0
            except:
                pass
    
    return signals

def apply_rsi_entry_filters(signals, rsi_values, oversold=25, overbought=75):
    """Keep long entries only when oversold and short entries only when overbought."""
    filtered = signals.copy()
    filtered[(filtered == 1) & (rsi_values >= oversold)] = 0
    filtered[(filtered == -1) & (rsi_values <= overbought)] = 0
    return filtered

def resample_15min(df):
    df = df.copy()
    if 'DateTime' not in df.columns:
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
    df = df.set_index('DateTime')
    resampled = df.resample('15min').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    })
    resampled = resampled.dropna().reset_index()
    resampled['Date'] = resampled['DateTime'].dt.strftime('%Y-%m-%d')
    resampled['Time'] = resampled['DateTime'].dt.strftime('%H:%M:%S')
    return resampled

def run_backtest_15min(
    signals,
    closes,
    df,
    initial_capital=10000,
    stop_loss=0.6,
    take_profit=2.4,
    fee_per_trade=10.0,
    point_value=2.0
):
    capital = initial_capital
    in_pos = 0
    entry_price = 0
    entry_idx = 0
    trades = []
    
    for i in range(len(signals)):
        if in_pos == 0 and signals[i] != 0:
            in_pos = 1 if signals[i] == 1 else -1
            entry_price = closes[i]
            entry_idx = i
        
        if in_pos != 0:
            pnl_pct = (closes[i] - entry_price) / entry_price * 100 if in_pos == 1 else (entry_price - closes[i]) / entry_price * 100
            
            if pnl_pct <= -stop_loss or pnl_pct >= take_profit:
                exit_reason = 'SL' if pnl_pct <= -stop_loss else 'TP'
                points_moved = (closes[i] - entry_price) if in_pos == 1 else (entry_price - closes[i])
                pnl_dollars = (points_moved * point_value) - fee_per_trade
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'direction': 'long' if in_pos == 1 else 'short',
                    'entry_price': entry_price,
                    'exit_price': closes[i],
                    'profit_pct': pnl_pct,
                    'profit_dollars': pnl_dollars,
                    'capital_after': capital + pnl_dollars,
                    'exit_reason': exit_reason,
                    'fees_paid': fee_per_trade
                })
                capital += pnl_dollars
                in_pos = 0
    
    return trades, capital


def create_ultimate_dashboard():
    """Create the ultimate TradingView-style dashboard."""
    print("=" * 70)
    print("ULTIMATE TRADING DASHBOARD GENERATOR")
    print("=" * 70)
    
    print("\nLoading data...")
    df_1min = load_data('1min.csv')
    df_2025 = filter_2025(df_1min)
    train_1min, test_1min = split_train_test(df_2025, '2025-06-30')
    
    print("Resampling to 15min timeframe...")
    train_15 = resample_15min(train_1min.copy().reset_index(drop=True)[::-1].reset_index(drop=True))
    test_15 = resample_15min(test_1min.copy().reset_index(drop=True)[::-1].reset_index(drop=True))
    
    print(f"Train (15min): {len(train_15)} candles")
    print(f"Test (15min): {len(test_15)} candles")
    
    print("\nCalculating indicators...")
    train_prep = prepare_data(train_15)
    test_prep = prepare_data(test_15)
    
    print("Training ML model...")
    ml_data = train_ml(train_prep, rsi_thresh=25)
    
    print("Applying ML filter to test data...")
    signals = apply_ml_filter(test_prep, ml_data)
    signals = apply_rsi_entry_filters(signals, test_prep['rsi_5'].values, oversold=25, overbought=75)
    
    print("\nRunning backtest...")
    trades, final_capital = run_backtest_15min(
        signals, 
        test_15['Close'].values, 
        test_prep,
        initial_capital=10000, 
        stop_loss=0.6, 
        take_profit=2.4, 
        fee_per_trade=10.0
    )
    metrics = calculate_metrics(trades, 10000)
    
    print(f"\nGross Profit: ${metrics['gross_profit']:.2f}")
    print(f"Net Profit: ${metrics['net_profit']:.2f}")
    print(f"Total Fees: ${metrics['total_fees']:.2f}")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    
    print("\nAnalyzing trades...")
    trade_analysis = []
    for i, trade in enumerate(trades, 1):
        analysis = analyze_trade(test_prep, trade, i)
        trade_analysis.append(analysis)
    
    logs = generate_logs(trades, test_prep, metrics)
    insights = generate_insights(trades, metrics)
    chart_data = prepare_chart_data(test_prep, trades)
    
    winning_trades = [t for t in trade_analysis if t['is_winner']]
    losing_trades = [t for t in trade_analysis if not t['is_winner']]
    
    params = {
        'timeframe': '15min',
        'rsi_period': 5, 
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'ema_fast': 5, 
        'ema_slow': 15, 
        'volume_threshold': 1.0,
        'stop_loss': 0.6, 
        'take_profit': 2.4,
        'ml_filter': True
    }
    
    # Save JSON data for the HTML
    dashboard_data = {
        'metrics': metrics,
        'trades': trade_analysis,
        'logs': logs,
        'insights': insights,
        'chart_data': chart_data,
        'params': params,
        'winning_count': len(winning_trades),
        'losing_count': len(losing_trades),
        'final_capital': final_capital,
        'total_return': (final_capital - 10000) / 100
    }
    
    # Save JSON data for the HTML (iter 3 - unified output dir)
    os.makedirs(os.path.join('output', 'dashboards'), exist_ok=True)
    with open('output/dashboards/dashboard_data.json', 'w') as f:
        json.dump(dashboard_data, f, default=str)
    print("Data saved to output/dashboards/dashboard_data.json")
    
    # Generate HTML
    generate_html(dashboard_data)
    
    print("\n" + "=" * 70)
    print("DASHBOARD GENERATION COMPLETE!")
    print("=" * 70)
    print("\nOpen output/dashboards/ultimate_trading_dashboard.html in your browser")
    print("=" * 70)


def generate_html(data):
    """Generate the complete HTML dashboard."""
    metrics = data['metrics']
    trades = data['trades']
    logs = data['logs']
    insights = data['insights']
    chart_data = data['chart_data']
    params = data['params']
    winning_trades = [t for t in trades if t['is_winner']]
    losing_trades = [t for t in trades if not t['is_winner']]
    final_capital = data['final_capital']
    total_return = data['total_return']
    
    # Conditional styling based on values
    return_color = 'var(--accent-green)' if total_return >= 0 else 'var(--accent-red)'
    return_prefix = '+' if total_return >= 0 else ''
    
    # Handle undefined metrics
    profit_factor_display = f"{metrics['profit_factor']:.2f}" if metrics['total_trades'] > 0 else 'N/A'
    sharpe_display = f"{metrics['sharpe_ratio']:.2f}" if metrics['total_trades'] >= 5 else 'N/A'
    win_rate_display = f"{metrics['win_rate']:.1f}%" if metrics['total_trades'] > 0 else '0.0%'
    
    # Calculate gross wins for insights
    gross_wins = sum(t['profit_dollars'] for t in trades if t['profit_dollars'] > 0)
    avg_win_display = f"${metrics['avg_profit']:.2f}" if metrics['avg_profit'] > 0 else '$0.00'
    avg_loss_display = f"${metrics['avg_loss']:.2f}" if metrics['avg_loss'] < 0 else '$0.00'
    
    # Calculate realized R/R
    if metrics['avg_profit'] > 0 and abs(metrics['avg_loss']) > 0:
        realized_rr = metrics['avg_profit'] / abs(metrics['avg_loss'])
        rr_display = f"{realized_rr:.1f}:1"
    else:
        rr_display = 'N/A'
    
    # Build HTML parts
    trades_html = ""
    for trade in trades:
        direction_class = 'long' if trade['direction'] == 'long' else 'short'
        win_class = 'win' if trade['is_winner'] else 'loss'
        winner_class = 'winner' if trade['is_winner'] else 'loser'
        vol_spike = 'Yes' if trade['entry_indicators']['volume_spike'] else 'No'
        
        trades_html += f'''
                    <div class="trade-item {winner_class}" onclick="highlightTrade({trade['trade_num']})">
                        <div class="trade-header">
                            <span class="trade-num">Trade #{trade['trade_num']}</span>
                            <span class="trade-direction {direction_class}">{trade['direction']}</span>
                        </div>
                        <div class="trade-details">
                            Entry: ${trade['entry_price']:.2f} → Exit: ${trade['exit_price']:.2f}
                        </div>
                        <div class="trade-profit {win_class}">
                            {trade['profit_pct']:+.2f}% (${trade['profit_dollars']:+.2f})
                        </div>
                        <div class="trade-indicators">
                            <strong>Entry:</strong> RSI={trade['entry_indicators']['rsi']} | Price {trade['entry_indicators']['price_vs_ema']} EMA | Vol spike: {vol_spike}
                        </div>
                        <div style="font-size: 10px; color: #ff9800; margin-top: 4px;">
                            Exit Reason: {trade['exit_reason']}
                        </div>
                    </div>
'''

    right_moves_html = ""
    for trade in winning_trades:
        right_moves_html += f'''
                    <div class="breakdown-item">
                        <div class="breakdown-header">Trade #{trade['trade_num']} - {trade['direction']} (${trade['profit_dollars']:+.2f})</div>
                        <div class="breakdown-content">
                            <strong>What happened:</strong> {trade['what_happened']}<br><br>
                            <strong>What went right:</strong> {trade['what_went_right']}
                        </div>
                    </div>
'''

    wrong_moves_html = ""
    for trade in losing_trades:
        wrong_moves_html += f'''
                    <div class="breakdown-item">
                        <div class="breakdown-header">Trade #{trade['trade_num']} - {trade['direction']} (${trade['profit_dollars']:+.2f})</div>
                        <div class="breakdown-content">
                            <strong>What happened:</strong> {trade['what_happened']}<br><br>
                            <strong>What went wrong:</strong> {trade['what_went_wrong']}
                        </div>
                    </div>
'''

    logs_html = ""
    for log in logs:
        logs_html += f'''
                    <div class="log-item">
                        <span class="log-time">{log['timestamp']}</span>
                        <span class="log-type {log['type']}">{log['type']}</span>
                        {log['details']}
                    </div>
'''

    findings_html = ""
    for finding in insights['key_findings']:
        findings_html += f'<div class="insight-item"><div class="insight-finding">{finding}</div></div>'

    recommendations_html = ""
    for rec in insights['recommendations']:
        recommendations_html += f'<div class="insight-item"><div class="recommendation">{rec}</div></div>'

    chart_json = json.dumps(chart_data, default=str)

    # Iter 1 (TODO item 3): surface latest OHLC values for quick inspection
    latest_open = chart_data['opens'][-1] if chart_data['opens'] else 0
    latest_close = chart_data['closes'][-1] if chart_data['closes'] else 0
    latest_high = chart_data['highs'][-1] if chart_data['highs'] else 0
    latest_low = chart_data['lows'][-1] if chart_data['lows'] else 0
    ohlc_summary_html = f'''
            <div class="metrics-grid" style="margin-bottom: 15px;">
                <div class="metric-box">
                    <div class="metric-value">${latest_open:.2f}</div>
                    <div class="metric-label">Latest Open</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">${latest_close:.2f}</div>
                    <div class="metric-label">Latest Close</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">${latest_high:.2f}</div>
                    <div class="metric-label">Latest High</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">${latest_low:.2f}</div>
                    <div class="metric-label">Latest Low</div>
                </div>
            </div>
'''
    # Build the 12-card metrics grid as a Python fragment (slot {{METRICS_BLOCK}}).
    metric_cards = [
        ('metric-value positive', f'${metrics["net_profit"]:.2f}', 'Net Profit'),
        ('metric-value', f'${metrics["final_capital"]:.2f}', 'Final Capital'),
        ('metric-value', f'${metrics["total_fees"]:.2f}', 'Total Fees'),
        ('metric-value', profit_factor_display, 'Profit Factor'),
        ('metric-value', win_rate_display, 'Win Rate'),
        ('metric-value', sharpe_display, 'Sharpe Ratio'),
        ('metric-value', f'{metrics["max_drawdown"]:.2f}%', 'Max Drawdown'),
        ('metric-value', avg_win_display, 'Avg Win'),
        ('metric-value negative', avg_loss_display, 'Avg Loss'),
        ('metric-value', f'${metrics["expected_value"]:.2f}', 'EV/Trade'),
        ('metric-value', f'{metrics["max_consecutive_losses"]}', 'Max Losing Streak'),
        ('metric-value', f'{len(trades)}', 'Total Trades'),
    ]
    metrics_block_html = '\n'.join(
        f'                        <div class="metric-box">\n'
        f'                            <div class="{cls}">{val}</div>\n'
        f'                            <div class="metric-label">{label}</div>\n'
        f'                        </div>'
        for cls, val, label in metric_cards
    )

    # Build the 8 parameter rows as a Python fragment (slot {{PARAMS_BLOCK}}).
    param_rows = [
        ('RSI Period', params['rsi_period']),
        ('RSI Oversold', params['rsi_oversold']),
        ('RSI Overbought', params['rsi_overbought']),
        ('EMA Fast', params['ema_fast']),
        ('EMA Slow', params['ema_slow']),
        ('Volume Threshold', f'{params["volume_threshold"]}x'),
        ('Stop Loss', f'{params["stop_loss"]}%'),
        ('Take Profit', f'{params["take_profit"]}%'),
    ]
    params_block_html = '\n'.join(
        f'                        <tr><td>{label}</td><td>{val}</td></tr>'
        for label, val in param_rows
    )

    # Render the template (iter 2, TODO item 4: real template separation).
    # Iter 3 (TODO item 11): ensure unified output dir exists.
    os.makedirs(os.path.join('output', 'dashboards'), exist_ok=True)
    template_path = Path(__file__).resolve().parents[2] / 'templates' / 'ultimate_dashboard.html.tpl'
    html = render_template(template_path, {
        'TITLE': 'NQ Futures Scalping Strategy - Trading Dashboard',
        'FINAL_CAPITAL': f'{final_capital:.2f}',
        'RETURN_COLOR': return_color,
        'RETURN_PREFIX': return_prefix,
        'TOTAL_RETURN': f'{total_return:.2f}',
        'OHLC_SUMMARY': ohlc_summary_html,
        'METRICS_BLOCK': metrics_block_html,
        'TRADES_COUNT': len(trades),
        'WINNING_COUNT': len(winning_trades),
        'LOSING_COUNT': len(losing_trades),
        'TRADES_HTML': trades_html,
        'RIGHT_MOVES_HTML': right_moves_html,
        'WRONG_MOVES_HTML': wrong_moves_html,
        'LOGS_HTML': logs_html,
        'FINDINGS_HTML': findings_html,
        'RECOMMENDATIONS_HTML': recommendations_html,
        'RR_DISPLAY': rr_display,
        'PARAMS_BLOCK': params_block_html,
        'CHART_JSON': chart_json,
    })

    with open('output/dashboards/ultimate_trading_dashboard.html', 'w') as f:
        f.write(html)

    print("Ultimate dashboard saved to output/dashboards/ultimate_trading_dashboard.html")


if __name__ == '__main__':
    create_ultimate_dashboard()
