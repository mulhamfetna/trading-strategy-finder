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

    es = loader.load_contributor_inputs(cfg["token"], cfg.get("tf", "4h"))
    bar_td = l1.bar_td
    nq_box_dir = np.asarray(l1.sig_int, dtype=np.int8)
    j_dec = align.align_decbars(l1.df_dec["Date"].to_numpy(),
                                es.df_dec["Date"].to_numpy(), bar_td)   # NQ-decbar -> ES-decbar idx

    com_veto, com_cc_entry, n_confirmers = _committee_masks(cfg, es, j_dec, nq_box_dir, n, bar_td)

    veto = com_veto
    if n_confirmers == 0:
        confirm_count = np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    else:
        confirm_count = com_cc_entry
    return veto, confirm_count


def _committee_masks(cfg, es, j_dec, nq_box_dir, n, bar_td):
    """(veto: bool[n] entry-shifted, confirm_count_entry: int64[n] entry-shifted, n_confirmers).
    Runs the contributor's indicator committee 1-MINUTE-sourced (I2 seam) and NQ-aligned."""
    com_specs = [s for s in cfg.get("committee", []) if s.get("enabled")]
    _assert_unique_keys(com_specs)
    if not com_specs:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=np.int64), 0
    inds = library.from_specs(com_specs)
    es_ctx1, j_es1 = runner.indicator_source_1min(es.df_dec, es.df1, bar_td)
    j_nq = align.gather_to_nq(j_es1, j_dec, fill=-1)        # NQ-decbar -> ES-1min idx (causal; <0 => none)
    votes_d = {ind.key: runner._vote_from_1min(ind, es_ctx1, j_nq, nq_box_dir) for ind in inds}
    com_veto = votes.committee_veto_mask(votes_d, inds, n)          # already entry-shifted
    cc_raw = votes.committee_confirm_count(votes_d, inds, n)        # UNshifted (per-signal-bar)
    cc_entry = np.zeros(n, dtype=np.int64)
    cc_entry[1:] = cc_raw[:-1]                                      # shift to entry bar
    n_confirmers = len([i for i in inds if i.config.enabled and i.config.mode in ("confirm", "both")])
    return com_veto, cc_entry, n_confirmers
