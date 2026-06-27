"""Part B1 — unified per-contributor gate-mask producer. Given a contributor cfg + the L1 run, emit
(veto, confirm_count) aligned to NQ decision bars: the single producer Part B2 ANDs/pools into
engine.l2_gate_components. UNWIRED from the engine (no engine import) => golden trivially 6/6. The
committee is 1-min-sourced (matches NQ resolution, I2); identity fills make a disabled/absent
contributor a pure no-op (T3); committee keys are one-enabled-per-key (M1)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from indicators import library, runner                               # noqa: E402
from optimize.l2.contributors import align, loader, registry, state, votes  # noqa: E402

# A confirm_count so large any K passes => B2 reads it as "no confirm constraint" (mirrors runner
# K_eff=0 => all-True identity). Never reached by a real count (max ~= 18 committee + 1 signal).
NO_CONFIRM_CONSTRAINT = np.int64(1 << 30)


def _assert_unique_keys(specs) -> None:
    keys = [s["key"] for s in specs if s.get("enabled")]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate enabled committee keys: {sorted(keys)}")


def contributor_gate_masks(cfg: dict, l1):
    """(veto: bool[n], confirm_count: int64[n]), n=len(l1.df_dec). Disabled =>
    (all-False, all-NO_CONFIRM_CONSTRAINT) = pure no-op."""
    n = len(l1.df_dec)
    if not cfg.get("enabled"):
        return np.zeros(n, dtype=bool), np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    raise NotImplementedError  # Task 2/3 fill the enabled path
