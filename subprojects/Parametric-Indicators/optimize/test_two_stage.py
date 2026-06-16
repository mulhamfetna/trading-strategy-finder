"""P3 regression lock — two-stage decomposition (optimize/two_stage.py).

Run directly:  python3 -m optimize.test_two_stage
(Plain-assert script; uses the fast decision-TF frame so it runs in seconds.)

Locks the mechanism contract:
  • run() rejects an unknown --stage-b engine BEFORE loading data (cheap guard)
  • Stage A always force-includes the champion's exact indicator pattern as shortlist slot 0
  • both Stage-B engines (cmaes, gp) execute without raising and return a dict-or-None cleanly
  • build_params() produces a well-formed engine param dict from (en, flip, cont)
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

from optimize import two_stage as TS
from indicators import library

_CTX = None
def _ctx():
    global _CTX
    if _CTX is None:                       # decision-TF (fast), warm-started → champion frozen
        _CTX = TS._Ctx("4h", split_sltp=False, ind_1min=False, folds=5, min_trades=5, warm_start=True)
    return _CTX


def test_bad_engine_rejected_before_data_load():
    try:
        TS.run("4h", stage_b_engine="banana")     # must raise before any heavy work
    except ValueError as e:
        assert "unknown stage-b engine" in str(e) and "banana" in str(e)
        return
    raise AssertionError("run() must reject an unknown --stage-b engine")


def test_stage_a_shortlist_forces_champion_slot0():
    ctx = _ctx()
    sl = TS.run_stage_a(ctx, n_trials=6, top_k=2, seed=1)
    assert len(sl) >= 1, "shortlist must be non-empty"
    slot0 = sl[0]
    # slot 0 must equal the champion's exact en-pattern + flip
    for k in library.REGISTRY:
        assert bool(slot0[k]) == bool(ctx.champ_en[k]), f"slot0 differs from champion at {k}"
    assert bool(slot0["flip"]) == bool(ctx.champ_flip)


def test_both_engines_run_clean():
    ctx = _ctx()
    champ_pattern = {**{k: ctx.champ_en[k] for k in library.REGISTRY}, "flip": ctx.champ_flip}
    for eng in ("cmaes", "gp"):
        out = TS.run_stage_b(ctx, champ_pattern, eng, n_trials=4, seed=1)
        assert out is None or isinstance(out, dict), f"{eng} returned {type(out)}"
        if isinstance(out, dict):
            assert {"median_pnl", "full_pnl", "full_dd", "params", "en_flip"} <= set(out)


def test_build_params_shape():
    ctx = _ctx()
    en = {k: ctx.champ_en[k] for k in library.REGISTRY}
    p = ctx.build_params(en, ctx.champ_flip, ctx.champ_cont)
    assert p["sl_hard"] >= p["sl_soft"] and p["tp"] > 0
    assert len(p["indicators"]) == len(library.REGISTRY)
    assert isinstance(p["k"], int) and isinstance(p["cooldown"], int)


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t(); print(f"  ok  {t.__name__}")
    print(f"P3 TWO-STAGE OK — {len(tests)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
