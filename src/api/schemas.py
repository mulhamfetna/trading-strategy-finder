"""Pydantic request/response schemas for the FastAPI backend.

Single-strategy surface: only the Master Strategy (1-1-2 execution +
Box directional oracle) is exposed.

**No-fallback rule (see docs/CODING_RULES.md):** every field on every
request model is REQUIRED. Pydantic enforces this at the API boundary
and raises ValidationError when a field is missing — the FastAPI
exception handler wraps that into a 422 with structured system_status.

The frontend's DEFAULT_BOX_PARAMS is the *form's* starter state, not an
engine fallback. The form always sends every field.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


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


# ---- /api/backtest/box (master strategy, SSE-streamed) ----

class Metrics(BaseModel):
    """Shape of the `metrics` object inside the SSE `complete` payload.

    `profit_factor` and `sharpe_ratio` are `None` when mathematically
    undefined (no losses for PF; <2 trades or zero variance for Sharpe).
    Frontend renders "N/A" in that case (BUG-011).
    """
    total_profit: float
    profit_factor: Optional[float]
    win_rate: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    total_trades: int
    avg_profit: Optional[float] = Field(...)
    avg_loss: Optional[float] = Field(...)
    expected_value: Optional[float] = Field(...)
    gross_profit: Optional[float] = Field(...)
    gross_loss: Optional[float] = Field(...)
    wins: Optional[int] = Field(...)
    losses: Optional[int] = Field(...)

    model_config = {'extra': 'allow'}


class ScalingParamsModel(BaseModel):
    """Pydantic mirror of src.strategy.scaling_strategy.ScalingParams.

    NO defaults — the no-fallback rule requires every field to be supplied
    explicitly by the caller. The frontend's form pre-populates from
    DEFAULT_SCALING_PARAMS so the user always submits a complete payload;
    the backend rejects partial payloads with 422.
    """
    # §1 Entry distribution & sizing
    total_contracts: int = Field(..., description="Total target position size in contracts.")
    leg1_contracts: int = Field(..., description="Leg-1 contracts (Base Level fill).")
    leg2_contracts: int = Field(..., description="Leg-2 contracts (first pullback fill).")
    leg3_contracts: int = Field(..., description="Leg-3 contracts (deep pullback fill).")
    leg2_pullback_points: float = Field(..., description="Pullback in points before leg-2 fills.")
    leg3_pullback_points: float = Field(..., description="Pullback in points before leg-3 fills.")

    # §2 Big candle exception
    big_candle_threshold_points: float
    big_candle_full_contracts: int
    big_candle_reverses_dir: bool

    # §3 Entry trigger (15-second confirmation; not enforced in 4h-only mode)
    entry_confirmation_timeframe_seconds: int
    entry1_confirmation_candles: int
    entry23_confirmation_candles: int

    # §4 Stop loss
    sl_soft_points: float
    sl_hard_points: float
    soft_sl_confirmation_timeframe_minutes: int
    hard_sl_confirmation_timeframe_seconds: int

    # §5 Take profit
    tp_target_points: float
    tp_watch_threshold_points: float
    tp_confirmation_timeframe_minutes: int

    # Re-entry
    reentry_enabled: bool
    reentry_cooldown_candles: int

    # Instrument constants
    point_value: float


class BoxParamsModel(ScalingParamsModel):
    """ScalingParamsModel + box-specific decision params. All required."""
    # Box-rule decisions
    box_tick_threshold: float

    # Big-Candle vs Box conflict resolution (see MASTER_STRATEGY_GUIDE.md §5).
    big_candle_resolution: Literal['big_candle_wins', 'box_wins', 'skip']


class BoxBacktestRequest(BaseModel):
    """Master-strategy backtest request. Every field required."""
    params: BoxParamsModel
    data_path: str
    box_data_path: str          # unified CSV containing all W* and M* box levels
    # Date range is optional in semantics (None = whole CSV) but the
    # field is REQUIRED — caller must send `null` explicitly.
    start: Optional[str] = Field(...)
    end: Optional[str] = Field(...)
