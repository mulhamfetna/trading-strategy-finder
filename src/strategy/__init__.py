"""Strategy package — 1-1-2 scaling + Box-signal variant.

Every numeric decision is exposed via ScalingParams / BoxStrategyParams.
"""

from src.strategy.scaling_strategy import ScalingParams, ScalingStrategy
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams
from src.strategy.box_lookup import BoxLookup

__all__ = ['ScalingParams', 'ScalingStrategy', 'BoxStrategy', 'BoxStrategyParams', 'BoxLookup']
