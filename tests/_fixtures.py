"""Shared test fixtures.

The no-fallback rule (docs/CODING_RULES.md) makes every strategy
parameter required at every layer (Pydantic, dataclass, function arg).
Tests that previously relied on dataclass defaults (`ScalingParams()`)
must now supply every field. These helpers do that uniformly so every
test produces a consistent baseline that mirrors the playbook defaults.
"""

from __future__ import annotations

from typing import Any, Dict

from src.strategy.scaling_strategy import ScalingParams
from src.strategy.box_strategy import BoxStrategyParams


# Playbook defaults — kept HERE (test-only) so production code never
# imports them by accident. Changing one of these only affects test
# baselines.
PLAYBOOK_SCALING_DEFAULTS: Dict[str, Any] = {
    # §1
    'total_contracts': 4,
    'leg1_contracts': 1,
    'leg2_contracts': 1,
    'leg3_contracts': 2,
    'leg2_pullback_points': 100.0,
    'leg3_pullback_points': 150.0,
    # §2
    'big_candle_threshold_points': 400.0,
    'big_candle_full_contracts': 4,
    'big_candle_reverses_dir': True,
    # §3
    'entry_confirmation_timeframe_seconds': 15,
    'entry1_confirmation_candles': 3,
    'entry23_confirmation_candles': 1,
    # §4
    'sl_soft_points': 200.0,
    'sl_hard_points': 300.0,
    'soft_sl_confirmation_timeframe_minutes': 2,
    'hard_sl_confirmation_timeframe_minutes': 1,
    # §5
    'tp_target_points': 150.0,
    'tp_watch_threshold_points': 50.0,
    'tp_confirmation_timeframe_minutes': 2,
    # Re-entry
    'reentry_enabled': True,
    'reentry_cooldown_candles': 1,
    # Instrument
    'point_value': 2.0,
}

PLAYBOOK_BOX_EXTRA: Dict[str, Any] = {
    'box_data_path': 'NQ_full_data.csv',
    'box_tick_threshold': 0.75,
    'big_candle_resolution': 'big_candle_wins',
}


def scaling_params(**overrides: Any) -> ScalingParams:
    """Build a fully-populated ScalingParams with playbook defaults.
    Pass overrides as kwargs to vary specific fields per test."""
    fields = {**PLAYBOOK_SCALING_DEFAULTS, **overrides}
    return ScalingParams(**fields)


def box_strategy_params(**overrides: Any) -> BoxStrategyParams:
    """Build a fully-populated BoxStrategyParams with playbook defaults."""
    fields = {**PLAYBOOK_SCALING_DEFAULTS, **PLAYBOOK_BOX_EXTRA, **overrides}
    return BoxStrategyParams(**fields)


def box_params_dict(**overrides: Any) -> Dict[str, Any]:
    """Same as box_strategy_params but returns the dict (for JSON
    request bodies in API tests)."""
    return {**PLAYBOOK_SCALING_DEFAULTS, **PLAYBOOK_BOX_EXTRA, **overrides}
