"""P4 regression lock — MAP-Elites archive (optimize/map_elites.py).

Run directly:  python3 -m optimize.test_map_elites
(Plain-assert script; pure-logic tests run instantly, the archive smoke uses the fast decision-TF frame.)

Locks: behavior-descriptor binning, continuous-space bounds, mutation stays in-bounds + actually changes the
genotype, and the run() loop executes end-to-end producing a (possibly empty) archive without raising.
"""
from __future__ import annotations

import random
import warnings
warnings.filterwarnings("ignore")

from optimize import map_elites as ME
from optimize import two_stage as TS
from indicators import library

_CTX = None
def _ctx():
    global _CTX
    if _CTX is None:
        _CTX = TS._Ctx("4h", split_sltp=False, ind_1min=False, folds=5, min_trades=5, warm_start=True)
    return _CTX


def test_behavior_binning():
    # worst_dd $5,000 → bucket 2 ($5000//2000); 8 indicators → axis 8
    assert ME.behavior({"worst_dd": 5000.0}, 8) == (2, 8)
    # very large DD caps at DD_BIN_CAP
    assert ME.behavior({"worst_dd": 999_999.0}, 3)[0] == ME.DD_BIN_CAP


def test_cont_space_within_bounds():
    ctx = _ctx(); space = ME.cont_space(ctx)
    assert {"sl_soft", "sl_hard_delta", "tp", "gate_pct", "dd_limit", "cooldown", "k"} <= set(space)
    for nm, (lo, hi, is_int) in space.items():
        assert lo <= hi


def test_mutate_stays_in_bounds_and_changes():
    ctx = _ctx(); space = ME.cont_space(ctx); rng = random.Random(0)
    en = {k: False for k in library.REGISTRY}
    cont = {nm: lo for nm, (lo, hi, _i) in space.items()}
    child_en, child_flip, child_cont = ME._mutate((en, False, cont), space, rng)
    # at least one indicator bit toggled
    assert any(child_en[k] for k in library.REGISTRY)
    # every knob within bounds
    for nm, (lo, hi, is_int) in space.items():
        assert lo <= child_cont[nm] <= hi


def test_split_space_has_split_knobs():
    ctx = TS._Ctx("4h", split_sltp=True, ind_1min=False, folds=5, min_trades=5, warm_start=True)
    space = ME.cont_space(ctx)
    assert {"long_sl_soft", "short_tp", "long_tp", "short_sl_soft"} <= set(space)


def test_run_executes_and_returns_archive():
    # decision-TF (fast); archive may be empty (1-min champion infeasible here) but run must not raise
    r = ME.run("4h", n_evals=12, ind_1min=False, warm_start=True, seed=1)
    assert set(r) >= {"coverage", "archive", "best_overall", "safest", "simplest"}
    assert isinstance(r["coverage"], int)


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t(); print(f"  ok  {t.__name__}")
    print(f"P4 MAP-ELITES OK — {len(tests)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
