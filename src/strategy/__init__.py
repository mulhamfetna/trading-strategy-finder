"""Strategy package (iter 7, TODO item 6b).

Hybrid OOP/FP layout per the refactor policy in
docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md:

- Stateful with lifecycle: OOP (this package).
- Pure transforms (indicators, signals, metrics): stay FP in
  src/indicators, src/signals, src/backtest/metrics.
"""

from src.strategy.scalping_strategy import ScalpingStrategy
from src.strategy.backtester import Backtester

__all__ = ['ScalpingStrategy', 'Backtester']
