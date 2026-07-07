"""Two-phase generation (decision #11): build all OHLC-derived SMC structures for a run, plus a
generation report. In the dashboard the user sets the gen-params and presses Backtest → this phase
runs first (with its own report/log) → then the backtest consumes the structures. In the optimizer
the gen-params are tunable, so this is re-run (ideally memoized) per trial.

External weekly/monthly key-level boxes are NOT generated here — they come from the offline pipeline
(NQ_full_data.csv). This module only covers structures derivable from the decision-TF candles.
"""
from __future__ import annotations

import numpy as np

from . import smc
from .base import MarketContext


def generate_structures(ctx: MarketContext, swing_l: int = 2, golf_n: int = 3) -> dict:
    """Compute every OHLC-derived SMC structure once. Returns a dict with the raw arrays under
    'structures' and a human-facing 'report' (counts) for the generation-phase log. Deterministic."""
    bull, bear, fvg_lo, fvg_hi = smc.fvg(ctx.high, ctx.low)
    sh, sl = smc.market_structure(ctx.close, swing_l)
    trend = smc.structure_trend(ctx.close, swing_l)
    ob = smc.order_blocks(ctx.open, ctx.high, ctx.low, ctx.close, swing_l)
    golf = smc.golf_candle(ctx.open, ctx.high, ctx.low, ctx.close, golf_n)  # +1 bull / -1 bear / 0
    structures = {
        "bull_fvg": bull, "bear_fvg": bear, "fvg_lo": fvg_lo, "fvg_hi": fvg_hi,
        "swing_high": sh, "swing_low": sl, "structure_trend": trend,
        "order_block": ob, "golf": golf,
    }
    report = {
        "bars": len(ctx),
        "params": {"swing_l": int(swing_l), "golf_n": int(golf_n)},
        "n_bull_fvg": int(bull.sum()), "n_bear_fvg": int(bear.sum()),
        "n_swing_high": int(sh.sum()), "n_swing_low": int(sl.sum()),
        "n_golf": int((golf != 0).sum()),
        "n_golf_bull": int((golf == 1).sum()), "n_golf_bear": int((golf == -1).sum()),
        "n_ob_bull_bars": int((ob == 1).sum()), "n_ob_bear_bars": int((ob == -1).sum()),
    }
    return {"structures": structures, "report": report}
