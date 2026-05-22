<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #131722;
            --bg-secondary: #1e222d;
            --bg-tertiary: #2a2e39;
            --text-primary: #d1d4dc;
            --text-secondary: #787b86;
            --accent-green: #00c853;
            --accent-red: #ff5252;
            --accent-blue: #2962ff;
            --accent-orange: #ff9800;
            --border-color: #363a45;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
        }
        .header {
            background: var(--bg-secondary);
            padding: 15px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .symbol-name {
            font-size: 18px;
            font-weight: 600;
            color: var(--accent-blue);
        }
        .header-stats {
            display: flex;
            gap: 25px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 16px;
            font-weight: 600;
        }
        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        .main-container {
            display: flex;
            margin-top: 80px;
            height: calc(100vh - 80px);
        }
        .chart-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .sidebar {
            width: 420px;
            background: var(--bg-secondary);
            border-left: 1px solid var(--border-color);
            overflow-y: auto;
            padding: 15px;
        }
        .chart-container {
            flex: 1;
            padding: 10px;
            min-height: 0;
        }
        #main-chart {
            width: 100%;
            height: 100%;
        }
        .panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .panel-header {
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .panel-content {
            padding: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .metric-box {
            background: var(--bg-tertiary);
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }
        .metric-value {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .metric-label {
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        .metric-value.positive { color: var(--accent-green); }
        .metric-value.negative { color: var(--accent-red); }
        .trade-list { max-height: 400px; overflow-y: auto; }
        .trade-item {
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: background 0.2s;
        }
        .trade-item:hover { background: var(--bg-tertiary); }
        .trade-item.winner { border-left: 3px solid var(--accent-green); }
        .trade-item.loser { border-left: 3px solid var(--accent-red); }
        .trade-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .trade-num { font-weight: 600; font-size: 13px; }
        .trade-direction {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .trade-direction.long {
            background: rgba(0, 200, 83, 0.2);
            color: var(--accent-green);
        }
        .trade-direction.short {
            background: rgba(255, 82, 82, 0.2);
            color: var(--accent-red);
        }
        .trade-details {
            font-size: 11px;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }
        .trade-profit { font-weight: 600; font-size: 14px; }
        .trade-profit.win { color: var(--accent-green); }
        .trade-profit.loss { color: var(--accent-red); }
        .trade-indicators {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px dashed var(--border-color);
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 15px;
        }
        .tab {
            padding: 10px 15px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-secondary);
            transition: all 0.2s;
        }
        .tab:hover { color: var(--text-primary); }
        .tab.active {
            color: var(--accent-blue);
            border-bottom-color: var(--accent-blue);
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .log-list { max-height: 300px; overflow-y: auto; }
        .log-item {
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
            font-size: 11px;
        }
        .log-time { color: var(--text-secondary); margin-right: 10px; }
        .log-type {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            margin-right: 10px;
        }
        .log-type.ENTRY {
            background: rgba(0, 200, 83, 0.2);
            color: var(--accent-green);
        }
        .log-type.EXIT {
            background: rgba(255, 152, 0, 0.2);
            color: var(--accent-orange);
        }
        .log-type.METRICS {
            background: rgba(41, 98, 255, 0.2);
            color: var(--accent-blue);
        }
        .rule-item {
            padding: 10px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 12px;
        }
        .rule-title {
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--accent-blue);
        }
        .rule-list { padding-left: 15px; }
        .rule-list li { margin-bottom: 4px; color: var(--text-secondary); }
        .insight-item {
            padding: 10px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 10px;
            font-size: 12px;
        }
        .insight-finding { color: var(--text-primary); margin-bottom: 8px; }
        .insight-finding:before { content: "📊 "; }
        .recommendation { color: var(--accent-green); }
        .recommendation:before { content: "💡 "; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 3px;
        }
        .breakdown-section { margin-bottom: 20px; }
        .breakdown-title {
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .breakdown-title.right { color: var(--accent-green); }
        .breakdown-title.wrong { color: var(--accent-red); }
        .breakdown-item {
            background: var(--bg-tertiary);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .breakdown-header { font-weight: 600; font-size: 12px; margin-bottom: 6px; }
        .breakdown-content {
            font-size: 11px;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        .live-clock { font-size: 12px; color: var(--text-secondary); }
        .params-table { width: 100%; font-size: 11px; }
        .params-table td {
            padding: 6px 0;
            border-bottom: 1px solid var(--border-color);
        }
        .params-table td:first-child { color: var(--text-secondary); }
        .params-table td:last-child { font-weight: 600; color: var(--accent-blue); }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="header-left">
            <div class="symbol-name">NQ E-mini ($2/pt) | Scalping Strategy</div>
            <div class="header-stats">
                <div class="stat-item">
                    <div class="stat-value">Jul 1 - Sep 26, 2025</div>
                    <div class="stat-label">Test Period</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">$10,000</div>
                    <div class="stat-label">Initial Capital</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${{FINAL_CAPITAL}}</div>
                    <div class="stat-label">Final Capital</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" style="color: {{RETURN_COLOR}};">{{RETURN_PREFIX}}{{TOTAL_RETURN}}%</div>
                    <div class="stat-label">Total Return</div>
                </div>
                <div class="stat-item">
                    <div class="live-clock" id="live-clock">--:--:--</div>
                    <div class="stat-label">Simulation Time</div>
                </div>
            </div>
        </div>
    </header>
    
    <div class="main-container">
        <!-- Chart Section -->
        <div class="chart-section">
{{OHLC_SUMMARY}}
            <div class="chart-container">
                <div id="main-chart"></div>
            </div>
        </div>
        
        <!-- Sidebar -->
        <div class="sidebar">
            <!-- Metrics Panel -->
            <div class="panel">
                <div class="panel-header">
                    <span>Performance Metrics</span>
                    <span style="color: var(--accent-green);">★ {{TRADES_COUNT}} Trades</span>
                </div>
                <div class="panel-content">
                    {{METRICS_BLOCK}}
                </div>
            </div>
            
            <!-- Tabs -->
            <div class="tabs">
                <div class="tab active" data-tab="trades">Trades ({{TRADES_COUNT}})</div>
                <div class="tab" data-tab="analysis">Analysis</div>
                <div class="tab" data-tab="playbook">Playbook</div>
                <div class="tab" data-tab="logs">Logs</div>
                <div class="tab" data-tab="insights">Insights</div>
            </div>
            
            <!-- Trades Tab -->
            <div class="tab-content active" id="trades">
                <div class="trade-list">
{{TRADES_HTML}}
                </div>
            </div>
            
            <!-- Analysis Tab -->
            <div class="tab-content" id="analysis">
                <div class="breakdown-section">
                    <div class="breakdown-title right">✓ Right Moves ({{WINNING_COUNT}} Winners)</div>
{{RIGHT_MOVES_HTML}}
                </div>
                
                <div class="breakdown-section">
                    <div class="breakdown-title wrong">✗ Wrong Moves ({{LOSING_COUNT}} Losses)</div>
{{WRONG_MOVES_HTML}}
                </div>
            </div>
            
            <!-- Playbook Tab -->
            <div class="tab-content" id="playbook">
                <div class="rule-item">
                    <div class="rule-title">📈 Long Entry Rules (15min)</div>
                    <ul class="rule-list">
                        <li>RSI(5) &lt; 25 (oversold)</li>
                        <li>Price &gt; EMA 5</li>
                        <li>Volume spike &gt; 1.0x average</li>
                        <li>ML filter confirms signal</li>
                    </ul>
                </div>
                
                <div class="rule-item">
                    <div class="rule-title">📉 Short Entry Rules (15min)</div>
                    <ul class="rule-list">
                        <li>RSI(5) &gt; 75 (overbought)</li>
                        <li>Price &lt; EMA 5</li>
                        <li>Volume spike &gt; 1.0x average</li>
                        <li>ML filter confirms signal</li>
                    </ul>
                </div>
                
                <div class="rule-item">
                    <div class="rule-title">🎯 Exit Rules</div>
                    <ul class="rule-list">
                        <li>Take Profit: +2.4% from entry (4:1 target)</li>
                        <li>Stop Loss: -0.6% from entry</li>
                        <li>Realized R/R: {{RR_DISPLAY}} (from actual trades)</li>
                        <li><strong>Note:</strong> SL exits may exceed -0.6% due to market gaps/slippage - actual exits shown in trade log</li>
                    </ul>
                </div>
                
                <div class="rule-item">
                    <div class="rule-title">📊 Asset Class</div>
                    <ul class="rule-list">
                        <li><strong>Instrument:</strong> NQ - E-mini NASDAQ-100 Futures</li>
                        <li><strong>Exchange:</strong> CME (Chicago Mercantile Exchange)</li>
                        <li><strong>Contract Size:</strong> $2 per point</li>
                        <li><strong>Price Range:</strong> $24,700 - $26,000 (Sep 2025)</li>
                    </ul>
                </div>
                
                <div class="rule-item">
                    <div class="rule-title">🤖 ML Model</div>
                    <ul class="rule-list">
                        <li><strong>Algorithm:</strong> Random Forest Classifier</li>
                        <li><strong>Estimators:</strong> 100 trees, max_depth=10</li>
                        <li><strong>Features:</strong> price_change, price_change_5, volume_change, volume_ma_ratio, RSI</li>
                        <li><strong>Target:</strong> Next candle direction (up/down)</li>
                        <li><strong>Purpose:</strong> Filter signals and improve win rate</li>
                    </ul>
                </div>
                
                <div class="rule-item">
                    <div class="rule-title">⭐ Best Setups</div>
                    <p style="color: var(--text-secondary); margin-bottom: 8px;">
                        <strong>RSI Oversold + Volume Surge:</strong> When RSI drops below 30 with volume spike, high probability bounce.
                    </p>
                    <p style="color: var(--text-secondary); margin-bottom: 8px;">
                        <strong>EMA Bounce:</strong> Price retraces to EMA 5 and bounces with RSI confirmation.
                    </p>
                    <p style="color: var(--text-secondary);">
                        <strong>ML Confirmed Signal:</strong> All signals filtered by ML showed better than average results.
                    </p>
                </div>
            </div>
            
            <!-- Logs Tab -->
            <div class="tab-content" id="logs">
                <div class="log-list">
{{LOGS_HTML}}
                </div>
            </div>
            
            <!-- Insights Tab -->
            <div class="tab-content" id="insights">
{{FINDINGS_HTML}}
{{RECOMMENDATIONS_HTML}}
            </div>
            
            <!-- Parameters Panel -->
            <div class="panel">
                <div class="panel-header">Optimized Parameters</div>
                <div class="panel-content">
                    <table class="params-table">
{{PARAMS_BLOCK}}
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const chartData = {{CHART_JSON}};
        
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                this.classList.add('active');
                document.getElementById(this.dataset.tab).classList.add('active');
            });
        });
        
        function highlightTrade(tradeNum) {
            console.log('Highlight trade:', tradeNum);
        }
        
        function updateClock() {
            const now = new Date();
            document.getElementById('live-clock').textContent = now.toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        
        function createChart() {
            const trace1 = {
                x: chartData.dates,
                open: chartData.opens,
                high: chartData.highs,
                low: chartData.lows,
                close: chartData.closes,
                type: 'candlestick',
                name: 'OHLC',
                increasing: { line: { color: '#00c853' }, fillcolor: '#00c853' },
                decreasing: { line: { color: '#ff5252' }, fillcolor: '#ff5252' },
                xaxis: 'x',
                yaxis: 'y'
            };
            
            const trace2 = {
                x: chartData.dates,
                y: chartData.ema_5,
                type: 'scatter',
                mode: 'lines',
                name: 'EMA 5',
                line: { color: '#00c853', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y'
            };
            
            const trace3 = {
                x: chartData.dates,
                y: chartData.ema_15,
                type: 'scatter',
                mode: 'lines',
                name: 'EMA 15',
                line: { color: '#ff9800', width: 1.5 },
                xaxis: 'x',
                yaxis: 'y'
            };
            
            const rsiTrace = {
                x: chartData.dates,
                y: chartData.rsi,
                type: 'scatter',
                mode: 'lines',
                name: 'RSI (5)',
                line: { color: '#9c27b0', width: 1 },
                xaxis: 'x2',
                yaxis: 'y2'
            };
            
            const volumeTrace = {
                x: chartData.dates,
                y: chartData.volumes,
                type: 'bar',
                name: 'Volume',
                marker: { 
                    color: chartData.volume_spike.map(v => v ? '#00c853' : '#787b86'),
                    opacity: 0.6
                },
                xaxis: 'x',
                yaxis: 'y3'
            };
            
            // Entry markers
            const entryMarkers = chartData.trade_markers.map(t => ({
                x: chartData.dates[t.entry_idx],
                y: t.entry_price,
                type: 'scatter',
                mode: 'markers',
                marker: { 
                    symbol: 'triangle-up',
                    size: 12,
                    color: t.direction === 'long' ? '#00c853' : '#ff5252'
                },
                name: `Entry #{t.entry_idx}: ${t.entry_price.toFixed(0)}`,
                xaxis: 'x',
                yaxis: 'y'
            }));
            
            // Exit markers
            const exitMarkers = chartData.trade_markers.map(t => ({
                x: chartData.dates[t.exit_idx],
                y: t.exit_price,
                type: 'scatter',
                mode: 'markers',
                marker: { 
                    symbol: 'triangle-down',
                    size: 12,
                    color: t.profit_dollars > 0 ? '#00c853' : '#ff5252'
                },
                name: `Exit: ${t.exit_price.toFixed(0)} ({t.profit_dollars > 0 ? '+' : ''}${t.profit_dollars.toFixed(0)})`,
                xaxis: 'x',
                yaxis: 'y'
            }));
            
            const data = [trace1, trace2, trace3, rsiTrace, volumeTrace, ...entryMarkers, ...exitMarkers];
            
            const layout = {
                paper_bgcolor: '#131722',
                plot_bgcolor: '#131722',
                font: { color: '#d1d4dc' },
                showlegend: true,
                legend: { 
                    orientation: 'h',
                    x: 0.5,
                    xanchor: 'center',
                    y: 1.1,
                    bgcolor: 'rgba(0,0,0,0)'
                },
                grid: { 
                    rows: 3,
                    columns: 1,
                    subplots: [['xy', 'x2y2', 'x3y3']],
                    roworder: 'top to bottom'
                },
                xaxis: { 
                    title: 'Time',
                    gridcolor: '#363a45',
                    showgrid: true
                },
                yaxis: { 
                    title: 'Price',
                    gridcolor: '#363a45',
                    showgrid: true,
                    domain: [0.4, 1]
                },
                xaxis2: { 
                    title: '',
                    gridcolor: '#363a45',
                    showgrid: true
                },
                yaxis2: { 
                    title: 'RSI',
                    gridcolor: '#363a45',
                    showgrid: true,
                    range: [0, 100],
                    domain: [0.2, 0.4]
                },
                xaxis3: { 
                    title: '',
                    showgrid: false,
                    showticklabels: false
                },
                yaxis3: { 
                    title: 'Volume',
                    gridcolor: '#363a45',
                    showgrid: true,
                    domain: [0, 0.2]
                },
                margin: { l: 60, r: 20, t: 60, b: 60 },
                height: 700
            };
            
            const config = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                displaylogo: false
            };
            
            Plotly.newPlot('main-chart', data, layout, config);
        }
        
        createChart();
    </script>
</body>
</html>
