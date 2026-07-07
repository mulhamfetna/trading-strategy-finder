"""Phase-1 intra-candle veto-entry resolver. Pure: given per-1-min-bar gate arrays (one per direction),
find the first bar inside the candle where the gate is open AND the engine is flat, within the wait window N.
Causal by construction (gate arrays are a forward series; we only read the current candle's bars)."""
from __future__ import annotations


def build_resolver(gate_by_dir, min_start, max_wait):
    """gate_by_dir: {+1: bool[n1], -1: bool[n1]}. Returns resolver(direction_int, start_e, sub_len, is_flat)
    -> (fill_offset,) | None. fill_offset is the first o in [0, min(max_wait, sub_len)) where the gate for
    direction_int is True at global 1-min bar start_e+o AND is_flat(o) is True; else None."""
    def resolver(direction_int, start_e, sub_len, is_flat):
        gate = gate_by_dir[int(direction_int)]
        limit = min(int(max_wait), int(sub_len))
        for o in range(limit):
            g = start_e + o
            if g < min_start or g >= len(gate):
                continue
            if gate[g] and is_flat(o):
                return (o,)
        return None
    return resolver
