"""FastAPI app entry point. Phase A of the FastAPI + Vue migration.

Run locally:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

The frontend (phase B) will hit these endpoints. CORS is permissive in
dev so a Vue Vite dev server at localhost:5173 can talk to us.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import asdict
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    BacktestRequest,
    BacktestResponse,
    Candle,
    CandlesRange,
    CandlesResponse,
    Metrics,
    ScalingBacktestRequest,
    StrategyConfig,
    Trade,
)
from src.backtest.metrics import calculate_metrics
from src.data.loader import load_data
from src.data.splitter import filter_by_date_range, split_train_test
from src.strategy.backtester import Backtester
from src.strategy.scaling_strategy import ScalingParams, ScalingStrategy
from src.strategy.scalping_strategy import ScalpingStrategy


app = FastAPI(
    title="NQ Trading Dashboard API",
    description=(
        "Backend for the FastAPI + Vue dashboard. Wraps the existing "
        "Strategy/Backtester pipeline (iter 7) behind REST endpoints."
    ),
    version="2.0.0-dev",
)

# Permissive CORS for development. Lock down in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- helpers ---------------------------------------------------------

_DEFAULT_SPLIT = '2025-06-30'


def _load_and_filter(
    data_path: str,
    start: str,
    end: str,
    dataset: str,
) -> pd.DataFrame:
    """Shared load + date-range filter + train/test split. Raises
    HTTPException with the appropriate status code on failures."""
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail=f"data file not found: {data_path}")

    try:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid date format; use YYYY-MM-DD")

    if start_ts > end_ts:
        raise HTTPException(
            status_code=400,
            detail=f"start ({start}) is after end ({end})",
        )

    try:
        df = load_data(data_path)
    except Exception as exc:  # noqa: BLE001 - we surface message to caller
        raise HTTPException(status_code=500, detail=f"failed to load {data_path}: {exc}")

    df = filter_by_date_range(df, start=start, end=end)
    if len(df) == 0:
        # Empty isn't a 4xx - it's a valid empty range. Caller decides.
        return df

    # 1min CSVs load newest-first; reverse to ascending.
    df = df.reset_index(drop=True)[::-1].reset_index(drop=True)

    if dataset in ('train', 'test'):
        train_df, test_df = split_train_test(df, split_date=_DEFAULT_SPLIT)
        df = train_df if dataset == 'train' else test_df

    return df.reset_index(drop=True)


def _candles_from_df(df: pd.DataFrame) -> List[Candle]:
    """Convert an OHLCV DataFrame to a list of Candle models."""
    if len(df) == 0:
        return []
    timestamps: List[str]
    if 'Date' in df.columns and 'Time' in df.columns:
        timestamps = [f"{d}T{t}" for d, t in zip(df['Date'].astype(str), df['Time'].astype(str))]
    elif 'Date' in df.columns:
        timestamps = df['Date'].astype(str).tolist()
    elif 'timestamps' in df.columns:
        timestamps = df['timestamps'].astype(str).tolist()
    else:
        timestamps = [str(i) for i in range(len(df))]

    return [
        Candle(
            t=timestamps[i],
            o=float(df.iloc[i]['Open']),
            h=float(df.iloc[i]['High']),
            l=float(df.iloc[i]['Low']),
            c=float(df.iloc[i]['Close']),
            v=int(df.iloc[i].get('Volume', 0)),
        )
        for i in range(len(df))
    ]


# ---- endpoints -------------------------------------------------------

@app.get("/api/strategy/config", response_model=StrategyConfig)
def get_strategy_config() -> StrategyConfig:
    """Return the v1 strategy defaults + the enumerations the frontend
    needs to populate dropdowns/radios."""
    return StrategyConfig()


@app.get("/api/candles", response_model=CandlesResponse)
def get_candles(
    start: str = Query(..., description="Inclusive YYYY-MM-DD."),
    end: str = Query(..., description="Inclusive YYYY-MM-DD."),
    dataset: str = Query('test', description="train | test"),
    data_path: str = Query('1min.csv', description="Path to OHLCV CSV."),
) -> CandlesResponse:
    df = _load_and_filter(data_path, start=start, end=end, dataset=dataset)
    candles = _candles_from_df(df)
    return CandlesResponse(
        candles=candles,
        count=len(candles),
        range=CandlesRange(start=start, end=end),
    )


@app.post("/api/backtest", response_model=BacktestResponse)
def post_backtest(req: BacktestRequest) -> BacktestResponse:
    df = _load_and_filter(req.data_path, start=req.start, end=req.end, dataset=req.dataset)

    if len(df) == 0:
        return BacktestResponse(
            metrics=Metrics(**calculate_metrics([], req.initial_capital)),
            trades=[],
            candles=[],
        )

    strat = ScalpingStrategy()  # v1.0.0 defaults
    bt = Backtester(
        initial_capital=req.initial_capital,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        fee_per_trade=req.fee_per_trade,
        tp_sl_resolution=req.tp_sl_resolution,
    )

    try:
        prepared = strat.prepare(df)
        trades, _ = bt.run(prepared)
    except Exception as exc:  # noqa: BLE001 - surface pipeline failure as 500
        raise HTTPException(status_code=500, detail=f"pipeline failed: {exc}")

    metrics_dict = calculate_metrics(trades, req.initial_capital)
    candles = _candles_from_df(prepared)

    return BacktestResponse(
        metrics=Metrics(**metrics_dict),
        trades=[Trade(**t) for t in trades],
        candles=candles,
    )


@app.get("/api/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "version": app.version}


# ---- /api/backtest/scaling (phase C2, Server-Sent Events) ----------

_SENTINEL_DONE = object()


def _sse_format(event_type: str, data: Any) -> str:
    """Format a single Server-Sent Events frame."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _scaling_event_stream(req: ScalingBacktestRequest) -> Iterator[str]:
    """Generator that runs the scaling backtest in a worker thread and
    yields SSE frames as progress + complete + error events.

    Progress events are throttled: at most ~100 over the whole run, so
    long backtests don't flood the client.
    """
    start_wall = time.perf_counter()

    # --- Load + filter (outside the worker so we can fail fast w/ error event) ---
    if not os.path.exists(req.data_path):
        yield _sse_format('error', {'detail': f'data file not found: {req.data_path}'})
        return

    try:
        df = load_data(req.data_path)
    except Exception as exc:  # noqa: BLE001
        yield _sse_format('error', {'detail': f'failed to load {req.data_path}: {exc}'})
        return

    if req.start and req.end:
        try:
            df = filter_by_date_range(df, start=req.start, end=req.end)
        except Exception as exc:  # noqa: BLE001
            yield _sse_format('error', {'detail': f'date filter failed: {exc}'})
            return

    if len(df) == 0:
        yield _sse_format('error', {'detail': 'no candles in the requested range'})
        return

    df = df.reset_index(drop=True)

    # --- Bridge sync strategy callbacks -> SSE generator via a Queue ---
    q: "queue.Queue[Any]" = queue.Queue(maxsize=512)

    params_dict = req.params.model_dump()
    strat = ScalingStrategy(params=ScalingParams(**params_dict))

    progress_every = max(1, len(df) // 100)  # ~100 progress events total
    last_emitted_idx = [-progress_every]

    def on_progress(event: Dict) -> None:
        idx = event['current_idx']
        # Throttle: emit at most every `progress_every` candles, plus the last.
        if (
            idx - last_emitted_idx[0] >= progress_every
            or idx == event['total'] - 1
        ):
            q.put(('progress', event))
            last_emitted_idx[0] = idx

    def worker():
        try:
            trades, _state = strat.backtest(df, on_progress=on_progress)
            elapsed_ms = int((time.perf_counter() - start_wall) * 1000)
            # Build the complete payload.
            candles = _candles_from_df(df)
            metrics = _scaling_metrics(trades)
            complete_payload = {
                'metrics': metrics,
                'trades': [_trade_to_jsonable(t) for t in trades],
                'candles': [c.model_dump() for c in candles],
                'elapsed_ms': elapsed_ms,
            }
            q.put(('complete', complete_payload))
        except Exception as exc:  # noqa: BLE001
            q.put(('error', {'detail': f'backtest failed: {exc}'}))
        finally:
            q.put(_SENTINEL_DONE)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = q.get()
        if item is _SENTINEL_DONE:
            break
        event_type, data = item
        yield _sse_format(event_type, data)


def _scaling_metrics(trades: List[Dict]) -> Dict[str, float]:
    """Build a metrics dict for the scaling strategy trades.

    Different shape from src/backtest/metrics.py::calculate_metrics
    because scaling trades carry profit_points + contracts + multi-leg
    entries. Keep the canonical keys the frontend expects.
    """
    n = len(trades)
    if n == 0:
        return {
            'total_profit': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'expected_value': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'wins': 0,
            'losses': 0,
        }
    wins = [t for t in trades if t['profit_dollars'] > 0]
    losses = [t for t in trades if t['profit_dollars'] <= 0]
    gross_profit = sum(t['profit_dollars'] for t in wins)
    gross_loss = sum(t['profit_dollars'] for t in losses)
    total_profit = gross_profit + gross_loss
    avg_profit = (gross_profit / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    # Equity curve for drawdown + Sharpe
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    returns: List[float] = []
    for t in trades:
        equity += t['profit_dollars']
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
        returns.append(t['profit_dollars'])
    # Sharpe: mean / std of trade-level returns (no annualization here)
    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std = var ** 0.5
    sharpe = (mean_r / std) if std > 0 else 0.0
    return {
        'total_profit': total_profit,
        'total_trades': n,
        'win_rate': len(wins) / n * 100.0,
        'profit_factor': (gross_profit / abs(gross_loss)) if gross_loss < 0 else 0.0,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'expected_value': mean_r,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'wins': len(wins),
        'losses': len(losses),
    }


def _trade_to_jsonable(trade: Dict) -> Dict:
    """Coerce numpy / pandas scalar types in the trade dict to plain floats."""
    return {
        'entry_idx': int(trade['entry_idx']),
        'exit_idx': int(trade['exit_idx']),
        'direction': trade['direction'],
        'avg_entry_price': float(trade['avg_entry_price']),
        'exit_price': float(trade['exit_price']),
        'contracts': int(trade['contracts']),
        'profit_points': float(trade['profit_points']),
        'profit_dollars': float(trade['profit_dollars']),
        'exit_reason': trade['exit_reason'],
        'legs': trade.get('legs', []),
    }


@app.post("/api/backtest/scaling")
def post_scaling_backtest(req: ScalingBacktestRequest):
    """Run the 1-1-2 scaling backtest as a Server-Sent Events stream.

    Events:
      event: progress    { current_idx, total, percent, phase, trades_so_far,
                            pnl_so_far, win_rate_so_far,
                            current_position, current_legs_filled }
      event: complete    { metrics, trades, candles, elapsed_ms }
      event: error       { detail }

    The frontend connects via fetch() with a ReadableStream reader.
    EventSource doesn't support POST so we don't use it client-side.
    """
    return StreamingResponse(
        _scaling_event_stream(req),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # disable buffering when behind nginx
        },
    )
