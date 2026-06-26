"""Contributor voter channels for L2 (Spec §5) — all aligned to NQ decision bars, oriented to NQ box_dir.

§5b — indicator committee: the FULL 18-indicator registry computed on the CONTRIBUTOR's own bars via the
instrument-agnostic MarketContext, sampled at the aligned contributor bar per NQ decision bar, and oriented
to NQ's box_dir (reusing runner._vote_from_1min verbatim — the ES decision frame plays the source-frame
role, j_es the sampling index). A +1 always means 'agrees with the NQ entry direction'.

§5a — composite signal voter (state → vote), BOTH encodings searchable:
  signal_stance       (i)  directional stance + mode (reuses votes.stance_directions)
  signal_truthtable   (ii) full 6-cell (NQ-long,NQ-short) × (ES-long,ES-short,ES-hold) truth table

The committee mask builders MIRROR runner.veto_mask/confirm_mask EXACTLY (same any-OR veto, same ≥K_eff
confirm, same entry-bar shift out[1:]=raw[:-1]) so Part B can AND/pool them with NQ's masks with zero new
conventions. All builders are identity-when-disabled (veto all-False, confirm all-True / no contribution)
— the unit-level guarantee behind the contributors-OFF byte-parity invariant (Spec §8.1)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from indicators import library, runner                           # noqa: E402
from indicators import votes as ind_votes                        # noqa: E402
from indicators.base import CONFIRM, VETO, HOLD, BOTH            # noqa: E402

_DIR_STR = {1: "long", -1: "short"}
_ST_STR = {1: "long", -1: "short", 0: "hold"}


# ---- §5b indicator committee -----------------------------------------------------------------------

def committee_votes(es_df_dec: pd.DataFrame, j_es, nq_box_dir, specs):
    """Run the committee on the contributor's decision bars, oriented to NQ box_dir. Returns
    ({id(ind): int8 vote[] of len(j_es)}, inds) for ENABLED indicators (votes ∈ {+1 CONFIRM, -1 VETO, 0})."""
    es_ctx = runner.market_context(es_df_dec)
    inds = library.from_specs([s for s in specs if s.get("enabled")])
    bd = np.asarray(nq_box_dir, dtype=np.int8)
    j = np.asarray(j_es, dtype=np.int64)
    votes_d = {ind.key: runner._vote_from_1min(ind, es_ctx, j, bd)
               for ind in inds if ind.config.enabled}
    return votes_d, inds


def committee_veto_mask(votes_d: dict, inds, n: int) -> np.ndarray:
    """Any-OR veto among enabled veto-capable indicators, entry-bar-aligned (out[idx]=veto@idx-1; idx0=
    False). No veto-capable enabled indicator ⇒ all-False identity. Mirrors runner.veto_mask."""
    out = np.zeros(n, dtype=bool)
    vetoers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("veto", "both")]
    if not vetoers:
        return out
    raw = np.zeros(n, dtype=bool)
    for ind in vetoers:
        raw |= (votes_d[ind.key][:n] == VETO)
    out[1:] = raw[:-1]
    return out


def committee_confirm_count(votes_d: dict, inds, n: int) -> np.ndarray:
    """Per-SIGNAL-bar count of CONFIRM votes among enabled confirm-capable indicators (UNshifted; Part B
    pools/aligns it for the MERGED/OR topologies)."""
    confirmers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    cc = np.zeros(n, dtype=np.int64)
    for ind in confirmers:
        cc += (votes_d[ind.key][:n] == CONFIRM).astype(np.int64)
    return cc


def committee_confirm_mask(votes_d: dict, inds, k: int, n: int) -> np.ndarray:
    """≥K_eff confirm gate, entry-bar-aligned (out[idx]=count@idx-1≥K_eff; idx0=True). K_eff=min(k,
    #confirmers); 0 confirmers ⇒ all-True identity. Mirrors runner.confirm_mask."""
    out = np.ones(n, dtype=bool)
    confirmers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    k_eff = min(int(k), len(confirmers))
    if k_eff <= 0:
        return out
    cc = committee_confirm_count(votes_d, inds, n)
    ok = cc >= k_eff
    out[1:] = ok[:-1]
    return out
