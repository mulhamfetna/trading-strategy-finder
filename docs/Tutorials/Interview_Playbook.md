Interview Playbook — Ultimate Dashboard (Data Scientist candidate)

Purpose
- Help the candidate present the project clearly in a 7–10 minute walkthrough and answer technical questions in the final interview.

Structure
1) 1-minute elevator pitch
2) 7–10 minute demo walkthrough (slides + live demo) — script below
3) Key talking points and metrics to emphasize
4) Practice Q&A with model answers and timers
5) Demo checklist (commands & smoke-tests)
6) Study docs: Parameter_Rationale.md and Technical_Spec_Walkthrough.md

1-minute elevator pitch
- "Built a reproducible pipeline that generates rule-based signals, filters them with an ML model, runs per-contract backtests on NQ futures, and produces an interactive dashboard that explains trades and provides a playbook for integration into live systems."

Demo walkthrough script (7–10 minutes)
- 0:00–0:30: Quick context (team goal, data, instrument)
- 0:30–1:30: Problem statement & approach (rules + ML + per-contract P/L)
- 1:30–3:00: Show dashboard: metrics header, key numbers (net profit, final capital, win rate, profit factor)
- 3:00–5:00: Walk one winning trade and one losing trade (use analyze_trade narratives)
- 5:00–6:30: Explain ML filter role and features (why it helps)
- 6:30–7:30: Discuss limitations, reproducibility, and next steps for production
- 7:30–10:00: Q&A and live code pointer (where to find code and how to run it)

10-slide outline
1. Title & one-line problem
2. Data & instrument (NQ, 1-min → 15-min) + train/test split
3. Pipeline diagram (load → indicators → signals → ML filter → backtest → dashboard)
4. Rule set (RSI, EMA, volume spike)
5. ML filter design (features, model choice, target)
6. Backtest economics (per-contract P/L, fees, stop/take values)
7. Results: key metrics & trade count
8. Example trades: winner vs loser (screenshots + narrative)
9. Limitations & mitigations
10. Next steps & handoff to integrator

Demo checklist (commands)
- pip install -r requirements.txt
- python3 ultimate_dashboard.py  # writes docs/dashboard_data.json and docs/ultimate_trading_dashboard.html
- Open docs/ultimate_trading_dashboard.html in browser

Files to show during interview
- ultimate_dashboard.py, src/indicators/scalping.py, src/signals/ml_filter.py, src/backtest/engine.py

Saving and next actions
- File saved at docs/interview_preparation/Interview_Playbook.md
- Next: study Parameter_Rationale.md first, then Technical_Spec_Walkthrough.md.
