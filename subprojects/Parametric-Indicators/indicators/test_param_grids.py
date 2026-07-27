"""Guard against off-grid float params (#32): Optuna warns when a stepped FloatDistribution's range
isn't divisible by step, or when a fixed/warm-start value isn't on the grid. Every stepped float param's
range AND default must sit on its own grid so no such warning is ever emitted."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators import library


def _stepped_floats():
    for key, spec in library.SCHEMA.items():
        for p in spec.get("params", []):
            lo, hi, st = p.get("min"), p.get("max"), p.get("step")
            if None in (lo, hi, st) or not isinstance(st, float):
                continue
            yield key, p, float(lo), float(hi), float(st)


def _on_grid(x, lo, st):
    n = (x - lo) / st
    return abs(n - round(n)) < 1e-9


def test_every_float_range_is_divisible_by_step():
    bad = [(k, p["name"], lo, hi, st) for k, p, lo, hi, st in _stepped_floats() if not _on_grid(hi, lo, st)]
    assert not bad, f"range not divisible by step: {bad}"


def test_every_float_default_is_on_grid():
    bad = [(k, p["name"], p["default"], lo, st)
           for k, p, lo, hi, st in _stepped_floats() if not _on_grid(float(p["default"]), lo, st)]
    assert not bad, f"default off its step grid: {bad}"
