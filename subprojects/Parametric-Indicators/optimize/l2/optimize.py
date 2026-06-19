"""L2 optimizer (round 1) — NSGA-III over L2 profiles on the frozen L1's dropped signals, scored
full-period in-sample (2025) with an OOS holdout (2026) per spec option-3. Reuses optimize.optimizer's
sampler / indicator search space / feasibility constraint; persists under prefix l2v1."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import engine, metrics, payload          # noqa: E402
from optimize import optimizer as OPT                      # noqa: E402


def WINDOWS(l1) -> dict:
    """In-sample = first calendar segment (2025); OOS holdout = the rest (2026)."""
    n = len(l1.df_dec)
    return {"in": (0, int(l1.n_split)), "oos": (int(l1.n_split), n)}


def score_window(l1, l2_params: dict, lo: int, hi: int) -> dict:
    """metrics.score for the L2 book restricted to decision bars [lo, hi)."""
    n = len(l1.df_dec)
    mask = np.zeros(n, dtype=bool)
    mask[int(lo):int(hi)] = True
    return metrics.score(engine.run_l2(l1, l2_params, bar_mask=mask))


def suggest_l2_params(trial, b: dict, cap: int) -> dict:
    """Engine-ready L2 param dict from an Optuna trial — mirrors optimizer.objective's space (shared
    SL/TP; indicators on the 1-minute frame to match the lean L1 regime)."""
    sl_soft = trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
    delta = trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1]))
    tp = trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1]))
    gate_pct = trial.suggest_float("gate_pct", 0.0, 100.0)
    dd_limit = trial.suggest_float("dd_limit", 0.0, OPT.DD_LIMIT_MAX)
    cooldown = trial.suggest_int("cooldown", 0, cap)
    flip = trial.suggest_categorical("flip", [False, True])
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial)]
    k_rule = trial.suggest_int("k", 1, 5)
    return dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                dd_limit=dd_limit, cooldown=int(cooldown), flip=bool(flip), window="full",
                indicators=specs, k=int(k_rule), ind_1min=True)
