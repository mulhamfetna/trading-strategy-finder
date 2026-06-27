"""Single source of truth for combining NQ's gate ingredients with cross-instrument contributor confirm
masks by topology. Factored from engine._l2_eligibility so the L1 fast path and the L2 engine share ONE
implementation (no divergence). Operates on plain arrays — engine-agnostic.

The caller OR-s each contributor's veto into `veto` BEFORE calling (the L2 engine and L1 path both already
hold the contributor veto masks); `parsed` carries confirm info only: a list of
(confirm_count: int64[n], k_es: int, has_confirm: bool). A no-confirm-source contributor uses a sentinel
count (gate.NO_CONFIRM_CONSTRAINT) so `ccount >= k_es` is always True ⇒ a pure no-op in every topology."""
from __future__ import annotations
import numpy as np


def combine_eligibility(vol_gate, veto, nq_confirm, nq_cc, k, nq_nconf, parsed, topology):
    """(vol_gate ∧ ¬veto ∧ confirm). Confirm by topology:
      separate_and — nq_confirm ∧ each (ccount >= k_es)
      merged       — pooled (nq_cc + Σ has-confirm ccount) >= min(k, #sources); idx0 identity True
      or_boost     — nq_confirm ∨ any (ccount >= k_es)"""
    n = len(vol_gate)
    if topology == "separate_and":
        confirm = np.asarray(nq_confirm, dtype=bool).copy()
        for ccount, k_es, _has in parsed:
            confirm = confirm & (ccount >= k_es)
    elif topology == "merged":
        pooled = np.asarray(nq_cc, dtype=np.int64).copy()
        n_sources = int(nq_nconf)
        for ccount, _k_es, has in parsed:
            if has:
                pooled = pooled + ccount
                n_sources += 1
        k_m = min(int(k), n_sources)
        confirm = np.ones(n, dtype=bool)
        if k_m > 0:
            confirm[1:] = pooled[1:] >= k_m
    elif topology == "or_boost":
        boost = np.zeros(n, dtype=bool)
        for ccount, k_es, has in parsed:
            if has:
                boost |= (ccount >= k_es)
        confirm = np.asarray(nq_confirm, dtype=bool) | boost
    else:
        raise ValueError(f"unsupported contributor_topology {topology!r}")
    return np.asarray(vol_gate, dtype=bool) & ~np.asarray(veto, dtype=bool) & confirm
