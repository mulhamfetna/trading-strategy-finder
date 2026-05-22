"""Pydantic request/response schemas for the FastAPI backend.

Phase A of the FastAPI + Vue migration. The frontend gets typed
contracts via these models; the backend gets validation for free.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---- /api/strategy/config ----

class StrategyConfig(BaseModel):
    rsi_period: int = 5
    ema_fast: int = 5
    ema_slow: int = 15
    vol_threshold: float = 2.0
    stop_loss: float = 0.6
    take_profit: float = 1.8
    tp_sl_resolution: Literal['conservative', 'optimistic', 'direction-proxy'] = 'conservative'

    tp_sl_resolution_options: List[str] = ['conservative', 'optimistic', 'direction-proxy']
    timeframe_options: List[str] = ['15min']
    dataset_options: List[str] = ['train', 'test']


# ---- /api/candles ----

class Candle(BaseModel):
    """Compact OHLCV row. Short keys to keep WS frames small."""
    t: str = Field(..., description="ISO-format timestamp")
    o: float
    h: float
    l: float
    c: float
    v: int


class CandlesRange(BaseModel):
    start: str
    end: str


class CandlesResponse(BaseModel):
    candles: List[Candle]
    count: int
    range: CandlesRange


# ---- /api/backtest ----

class BacktestRequest(BaseModel):
    start: str
    end: str
    dataset: Literal['train', 'test'] = 'test'
    timeframe: Literal['15min'] = '15min'
    tp_sl_resolution: Literal['conservative', 'optimistic', 'direction-proxy'] = 'conservative'
    stop_loss: float = 0.6
    take_profit: float = 1.8
    initial_capital: float = 10000.0
    fee_per_trade: float = 10.0
    data_path: str = '1min.csv'


class Trade(BaseModel):
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    direction: str
    profit_pct: float
    profit_dollars: float
    capital_after: float
    exit_reason: str
    fees_paid: float


class Metrics(BaseModel):
    total_profit: float
    total_fees: float = 0.0
    profit_factor: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    avg_profit: Optional[float] = None
    avg_loss: Optional[float] = None
    expected_value: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    final_capital: Optional[float] = None
    gross_profit: Optional[float] = None
    net_profit: Optional[float] = None

    model_config = {'extra': 'allow'}  # metrics dict has more keys; accept them


class BacktestResponse(BaseModel):
    metrics: Metrics
    trades: List[Trade]
    candles: List[Candle]
