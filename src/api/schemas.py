"""Pydantic request/response schemas for the FastAPI backend.

Single-strategy surface: only the Master Strategy (1-1-2 execution +
Box directional oracle) is exposed.

**No-fallback rule:** every field on every request model is REQUIRED. Pydantic enforces this at the API boundary
and raises ValidationError when a field is missing — the FastAPI
exception handler wraps that into a 422 with structured system_status.

The frontend's DEFAULT_BOX_PARAMS is the *form's* starter state, not an
engine fallback. The form always sends every field.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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
    hard_sl_confirmation_timeframe_minutes: int

    # §5 Take profit (fixed; no trail per master strategy spec)
    tp_target_points: float

    # Re-entry
    reentry_enabled: bool
    reentry_cooldown_candles: int

    # Instrument constants
    point_value: float

    # Anchoring mode for SL/TP lines (master strategy §5).
    # 'base'    — lines fixed at `base_level ± thresholds` for trade lifetime.
    # 'average' — lines re-anchor on every leg fill to the running avg.
    anchor_mode: Literal['base', 'average']

    @model_validator(mode='after')
    def _sl_ordering(self):
        """Dashboard ordering invariants (user rule 2026-05-24, MASTER_STRATEGY_GUIDE §4).

        - sl_hard_points > sl_soft_points:                hard is farther out (disaster stop).
        - soft_sl_confirmation_timeframe_minutes >
          hard_sl_confirmation_timeframe_minutes:        soft confirms slower than hard.
        """
        if self.sl_hard_points <= self.sl_soft_points:
            raise ValueError(
                f'sl_hard_points ({self.sl_hard_points}) must be > sl_soft_points '
                f'({self.sl_soft_points}) — hard SL is the disaster stop, farther out.'
            )
        if self.soft_sl_confirmation_timeframe_minutes <= self.hard_sl_confirmation_timeframe_minutes:
            raise ValueError(
                f'soft_sl_confirmation_timeframe_minutes '
                f'({self.soft_sl_confirmation_timeframe_minutes}) must be > '
                f'hard_sl_confirmation_timeframe_minutes '
                f'({self.hard_sl_confirmation_timeframe_minutes}) — soft confirms slower.'
            )
        return self


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
    data_path_1min: str         # 1-min OHLCV — required for dual-timeframe SL/TP
                                # (HARD SL & TP target on 1-min, SOFT SL & trail on 2-min)
    box_data_path: str          # unified CSV containing all W* and M* box levels
    # Date range is optional in semantics (None = whole CSV) but the
    # field is REQUIRED — caller must send `null` explicitly.
    start: Optional[str] = Field(...)
    end: Optional[str] = Field(...)


# ---- /api/backtest/simple (Stage 1 entry + 1-min SL/TP exit) ----

class SimpleBacktestRequest(BaseModel):
    """Simple-strategy backtest request.

    Engine: Stage 1 truth table for entry direction + close-past SL/TP
    on 1-min bars + re-entry gate "next 4h that starts after exit_time".
    See `docs/superpowers/specs/2026-05-26-simple-backtest/notes.md`.
    """
    sl_points: float = Field(..., gt=0, description='SL distance in points from entry close.')
    tp_points: float = Field(..., gt=0, description='TP distance in points from entry close.')
    data_path:       str          # 4h candles
    data_path_1min:  str          # 1-min candles
    box_data_path:   str          # unified W*/M* level CSV
    direction_scope: Literal['both', 'long_only', 'short_only'] = 'both'
    start: Optional[str] = Field(...)
    end:   Optional[str] = Field(...)


# ---- /api/optimize/box (NSGA-II multi-objective optimiser, SSE-streamed) ----

from pydantic import field_validator


class OptimizeSearchSpace(BaseModel):
    """Per-parameter [lower, upper] search bounds.

    `sl_hard_delta` encodes the constraint sl_hard >= sl_soft + 50 structurally —
    Optuna suggests `sl_hard = sl_soft + delta` where delta lies in this range.
    """
    sl_soft_points: List[float] = Field(..., min_length=2, max_length=2)
    sl_hard_delta:  List[float] = Field(..., min_length=2, max_length=2)
    tp_target_points: List[float] = Field(..., min_length=2, max_length=2)

    @field_validator('sl_soft_points', 'sl_hard_delta', 'tp_target_points')
    @classmethod
    def _bounds_ordered(cls, v: List[float]) -> List[float]:
        if v[0] >= v[1]:
            raise ValueError(f'lower must be strictly less than upper, got {v}')
        return v


class OptimizeBudget(BaseModel):
    population_size: int = Field(..., gt=0, description="NSGA-II population per generation.")
    generations:     int = Field(..., gt=0, description="Number of generations.")


class OptimizeFoldsConfig(BaseModel):
    count: int = Field(..., ge=2, description="Walk-forward fold count.")
    min_trades_per_fold: int = Field(..., ge=1, description="Floor below which a fold prunes the trial.")


class OptimizeRequest(BaseModel):
    """Request body for POST /api/optimize/box. Every field required."""
    baseline_params: BoxParamsModel
    search_space:    OptimizeSearchSpace
    budget:          OptimizeBudget
    folds:           OptimizeFoldsConfig
    data_path:       str
    box_data_path:   str            # unified CSV containing all W* / M* levels
    max_duration_s:  int = Field(..., gt=0)


class TrialResult(BaseModel):
    """Payload of `event: trial` (and of pareto-front entries)."""
    trial_number: int
    params:       dict
    values:       List[float] = Field(..., min_length=2, max_length=2)
    state:        Literal['complete', 'pruned']
    pruned_reason: Optional[str] = Field(...)


class ParetoPoint(BaseModel):
    trial_number: int
    params:       dict
    values:       List[float] = Field(..., min_length=2, max_length=2)


class StudySummary(BaseModel):
    """Payload for GET /api/optimize/studies and `event: study_started`."""
    study_id:     str
    trials_done:  int
    trials_total: int
    started_at:   str
    is_complete:  bool
    pareto_size:  int


class StudiesListResponse(BaseModel):
    studies: List[StudySummary]
