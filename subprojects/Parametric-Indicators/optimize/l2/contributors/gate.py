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

# In-process memo of the PARAM-INDEPENDENT contributor inputs + 1-minute indicator source, keyed by
# (token, tf). These are pure functions of the instrument's data — rebuilding them every optimizer trial
# (the ~75s the ES committee cost a fresh trial) is wasted work. Memoising is result-neutral by
# construction (proven by the contributors suite + golden staying byte-identical). Only the per-trial,
# param-DEPENDENT indicator votes recompute. _clear_caches() lets tests measure cold vs warm.
_INPUT_CACHE: dict = {}
_SRC_CACHE: dict = {}


def _clear_caches() -> None:
    _INPUT_CACHE.clear()
    _SRC_CACHE.clear()


def _cached_inputs(token: str, tf: str):
    key = (token, tf)
    if key not in _INPUT_CACHE:
        _INPUT_CACHE[key] = loader.load_contributor_inputs(token, tf)
    return _INPUT_CACHE[key]


def _cached_source(token: str, tf: str, es, bar_td):
    key = (token, tf)
    if key not in _SRC_CACHE:
        _SRC_CACHE[key] = runner.indicator_source_1min(es.df_dec, es.df1, bar_td)
    return _SRC_CACHE[key]


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

    es = _cached_inputs(cfg["token"], cfg.get("tf", "4h"))
    bar_td = l1.bar_td
    nq_box_dir = np.asarray(l1.sig_int, dtype=np.int8)
    j_dec = align.align_decbars(l1.df_dec["Date"].to_numpy(),
                                es.df_dec["Date"].to_numpy(), bar_td)   # NQ-decbar -> ES-decbar idx

    com_veto, com_cc_entry, n_confirmers = _committee_masks(cfg, es, j_dec, nq_box_dir, n, bar_td)
    sig_cvote, sig_veto, sig_has_confirm = _signal_masks(cfg, es, j_dec, nq_box_dir, n)

    veto = com_veto | sig_veto
    n_confirm_sources = n_confirmers + (1 if sig_has_confirm else 0)
    if n_confirm_sources == 0:
        confirm_count = np.full(n, NO_CONFIRM_CONSTRAINT, dtype=np.int64)
    else:
        confirm_count = com_cc_entry + sig_cvote.astype(np.int64)
    return veto, confirm_count


def _signal_masks(cfg, es, j_dec, nq_box_dir, n):
    """(confirm_vote: bool[n], veto: bool[n], has_confirm: bool) for the composite signal voter, entry-
    bar-aligned. ES net state (touch|traversal) is gathered onto NQ bars (hold fill) then run through the
    chosen encoding. encoding 'none' => pure no-op."""
    enc = cfg.get("signal", {}).get("encoding", "none")
    if enc == "none":
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), False
    if cfg.get("state_def", "touch") == "touch":
        es_state = state.touch_state(es.df_dec, es.delivery)
    else:
        c = registry.get_contributor(cfg["token"])
        es_state = state.traversal_state(es.df_dec, c.box_csv, c.tick_threshold)
    nq_es_state = align.gather_to_nq(es_state, j_dec, fill=0)        # NQ-decbar -> ES state (hold fill)
    sig = cfg["signal"]
    if enc == "stance":
        mode = sig["mode"]
        cvote, veto = votes.signal_stance(nq_box_dir, nq_es_state, mode)
        return cvote, veto, mode in ("confirm", "both")
    if enc == "truthtable":
        # keys may be ("long","short") tuples (direct cfg) or "long|short" strings (JSON-safe, from the
        # optimizer — the objective json.dumps()es params, and JSON dict keys must be strings).
        def _key(k):
            return tuple(k.split("|")) if isinstance(k, str) else tuple(k)
        table = {_key(k): v for k, v in sig["table"].items()}
        cvote, veto = votes.signal_truthtable(nq_box_dir, nq_es_state, table)
        return cvote, veto, any(v == "confirm" for v in table.values())
    raise ValueError(f"invalid signal encoding {enc!r}")


def _committee_masks(cfg, es, j_dec, nq_box_dir, n, bar_td):
    """(veto: bool[n] entry-shifted, confirm_count_entry: int64[n] entry-shifted, n_confirmers).
    Runs the contributor's indicator committee 1-MINUTE-sourced (I2 seam) and NQ-aligned."""
    com_specs = [s for s in cfg.get("committee", []) if s.get("enabled")]
    _assert_unique_keys(com_specs)
    if not com_specs:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=np.int64), 0
    inds = library.from_specs(com_specs)
    es_ctx1, j_es1 = _cached_source(cfg["token"], cfg.get("tf", "4h"), es, bar_td)
    j_nq = align.gather_to_nq(j_es1, j_dec, fill=-1)        # NQ-decbar -> ES-1min idx (causal; <0 => none)
    votes_d = {ind.key: runner._vote_from_1min(ind, es_ctx1, j_nq, nq_box_dir) for ind in inds}
    com_veto = votes.committee_veto_mask(votes_d, inds, n)          # already entry-shifted
    cc_raw = votes.committee_confirm_count(votes_d, inds, n)        # UNshifted (per-signal-bar)
    cc_entry = np.zeros(n, dtype=np.int64)
    cc_entry[1:] = cc_raw[:-1]                                      # shift to entry bar
    n_confirmers = len([i for i in inds if i.config.enabled and i.config.mode in ("confirm", "both")])
    return com_veto, cc_entry, n_confirmers
