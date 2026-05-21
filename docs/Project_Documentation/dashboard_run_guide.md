# Dashboard Run Guide

## Dash Live Preview App

### Prerequisites

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python -m src.dashboard.dash_app
```

Open: `http://127.0.0.1:8050/`

### Expected Outcome

1. The page loads a **Live Trading Dashboard (Preview)** section.
2. The first iframe shows `output/dashboard/live_trading_dashboard.html` (or a missing-file message).
3. The second iframe shows `output/dashboard/equity_curve_dashboard.html` (or a missing-file message).
4. The server stays running until you stop it with `Ctrl+C`.
