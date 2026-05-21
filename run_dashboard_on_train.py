# Runner: generate ultimate dashboard on the training split without editing repo code
import json
import shutil
import os

import ultimate_dashboard as ud

OUTPUT_JSON = 'docs/dashboard_data_train.json'
OUTPUT_HTML_COPY = 'docs/ultimate_trading_dashboard_train.html'

# Load and filter
df_1min = ud.load_data('1min.csv')
df_2025 = ud.filter_2025(df_1min)
train_1min, test_1min = ud.split_train_test(df_2025, split_date='2025-06-30')

# Use training split as the 'test' target for dashboard generation
# Resample to 15min and prepare
train_15 = ud.resample_15min(train_1min.copy().reset_index(drop=True)[::-1].reset_index(drop=True))
train_prep = ud.prepare_data(train_15)

# Train ML on training set and apply it to the same training set to produce signals
ml_model = ud.train_ml(train_prep)
signals = ud.apply_ml_filter(train_prep, ml_model)

# Apply RSI entry filters
signals = ud.apply_rsi_entry_filters(signals, train_prep['rsi_5'].values)

# Run backtest on training prices using the same defaults used by ultimate_dashboard
trades, final_capital = ud.run_backtest_15min(signals, train_15['Close'].values, train_prep,
                                            initial_capital=10000, stop_loss=0.6, take_profit=2.4,
                                            fee_per_trade=10.0, point_value=2.0)

# Calculate metrics
metrics = ud.calculate_metrics(trades, initial_capital=10000)

# Prepare chart data and insights via the same helpers used by ultimate_dashboard
chart_data = ud.prepare_chart_data(train_prep, trades)
insights = ud.generate_insights(trades, metrics) if hasattr(ud, 'generate_insights') else {}

# Compose dashboard payload similar to create_ultimate_dashboard
dashboard_data = {
    'title': 'Ultimate Trading Dashboard (TRAINING DATA)',
    'timeframe': '15min',
    'metrics': metrics,
    'trades': [ud.analyze_trade(train_prep, t, i+1) for i,t in enumerate(trades)],
    'logs': ud.generate_logs(trades, train_prep, metrics),
    'chart_data': chart_data,
    'insights': insights,
    'params': {
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
    },
    'final_capital': final_capital,
    'total_return': (final_capital - 10000) / 100
}

# Write JSON payload
os.makedirs('docs', exist_ok=True)
with open(OUTPUT_JSON, 'w') as f:
    json.dump(dashboard_data, f, indent=2, default=str)
print(f'Wrote dashboard JSON to {OUTPUT_JSON}')

# Generate HTML using the repository's generator (it writes to docs/ultimate_trading_dashboard.html)
ud.generate_html(dashboard_data)

# Copy the generated HTML to a training-specific filename to avoid overwriting the existing dashboard
orig_html = 'docs/ultimate_trading_dashboard.html'
if os.path.exists(orig_html):
    shutil.copyfile(orig_html, OUTPUT_HTML_COPY)
    print(f'Copied generated HTML to {OUTPUT_HTML_COPY}')
else:
    print('Expected generated HTML not found:', orig_html)
