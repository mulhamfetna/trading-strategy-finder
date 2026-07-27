"""Cold-miss accelerator entry points (issue #54, Task 3).

The baseline (`optimize/perf/results/baseline_NQ_4h_smoke3.json`) showed ONE indicator, `dfa`, was ~81%
of all cold-compute time — a triple-nested Python loop calling `np.polyfit` per segment over ~486,969
one-minute bars.

The accelerated implementation now lives WITH the primitive it replaces, in
`indicators/calc/quant.py` (`dfa` = Numba closed-form fast path, `dfa_reference` = the original loop kept
as the parity oracle). This module keeps a thin alias so the benchmarks/tests read naturally and so
`indicators/` never has to import from `optimize/` (layering stays one-way).
"""
from __future__ import annotations

from indicators.calc.quant import dfa as _dfa, dfa_reference as _dfa_reference

__all__ = ["dfa_fast", "dfa_reference"]


def dfa_fast(close, n):
    """Accelerated rolling DFA alpha (Numba closed-form; falls back to the reference without numba)."""
    return _dfa(close, n)


def dfa_reference(close, n):
    """The original triple-nested-loop implementation — the oracle parity is proven against."""
    return _dfa_reference(close, n)
