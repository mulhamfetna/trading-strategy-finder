"""Precompute cross-instrument contributor (veto, confirm_count) masks ONCE per trial over the full decision
frame, for the L1 fast path. Reuses optimize.l2.contributors.gate via a lightweight L1-like adapter. Returns
None when no contributor is enabled (caller stays byte-identical)."""
from __future__ import annotations
from types import SimpleNamespace
import numpy as np

from optimize.l2.contributors import gate


def precompute_contributor_masks(params, df_dec, df1, box, sig_int, bar_td):
    """Return {"veto": bool[n], "parsed": [(ccount int64[n], k_es int, has_confirm bool), ...],
    "topology": str} aggregated across enabled contributors, or None if none enabled. `veto` is the OR of
    every enabled contributor's veto; `parsed` is confirm-only (combine.combine_eligibility consumes it).
    `box` is accepted for signature symmetry; ES resolves its own box via the registry (unused here)."""
    contribs = [c for c in (params.get("contributors") or []) if c.get("enabled")]
    if not contribs:
        return None
    l1 = SimpleNamespace(df_dec=df_dec, df1=df1, bar_td=bar_td, sig_int=np.asarray(sig_int))
    n = len(df_dec)
    veto = np.zeros(n, dtype=bool)
    parsed = []
    for cfg in contribs:
        cveto, ccount = gate.contributor_gate_masks(cfg, l1)
        veto |= cveto
        has = not bool((ccount == gate.NO_CONFIRM_CONSTRAINT).all())
        parsed.append((ccount, int(cfg.get("k_es", 1)), has))
    return {"veto": veto, "parsed": parsed,
            "topology": str(params.get("contributor_topology", "separate_and"))}
