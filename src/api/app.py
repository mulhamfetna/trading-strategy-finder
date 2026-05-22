"""FastAPI app entry point. Phase A of the FastAPI + Vue migration.

Run locally:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

The frontend (phase B) will hit these endpoints. CORS is permissive in
dev so a Vue Vite dev server at localhost:5173 can talk to us.
"""

from __future__ import annotations

import os
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    BacktestRequest,
    BacktestResponse,
    Candle,
    CandlesRange,
    CandlesResponse,
    Metrics,
    StrategyConfig,
    Trade,
)
from src.backtest.metrics import calculate_metrics
from src.data.loader import load_data
from src.data.splitter import filter_by_date_range, split_train_test
from src.strategy.backtester import Backtester
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
