"""L2 Pass 2 — run the secondary profile over the dropped signals, reusing the EXACT fast_backtest
exit math. L2 may open only at dropped bars where L1 is flat AND L2's own gate passes; any L2 trade
overlapping a later L1 entry is force-closed at that bar (L1 priority). Direction = box direction,
optionally reversed by L2's flip ('reverse is implicit')."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import config                                                       # noqa: E402
from optimize.fast_engine import fast_backtest                     # noqa: E402
from optimize.l2.l1_runner import apply_breaker                    # noqa: E402
from indicators import library, runner                             # noqa: E402
from volatility import gate_threshold                              # noqa: E402


def l2_gate_components(l1, l2_params: dict):
    """L2's per-bar gate components (vol_gate, veto, confirm) computed with L2's params over the SAME
    data L1 used. Identical recipe to core.backtest_metrics' gate construction. Returned separately so
    callers (the causal log builder) can attribute WHY L2 declined a bar; `_l2_gate_masks` ANDs them."""
    d, d1, box = l1.df_dec, l1.df1, l1.box
    n = len(d)
    gate_pct = float(l2_params.get("gate_pct", 0.0))
    K = int(l2_params.get("k", 1))
    vol_gate = np.ones(n, dtype=bool)
    if gate_pct > 0:
        # seed on L1's IN-SAMPLE prefix (vf_seed), NOT l1.vf[:n_split] — the latter is the WINDOWED vf,
        # so for a 2026 window it would reseed on out-of-sample data and diverge.
        seed = l1.vf_seed if l1.vf_seed is not None else l1.vf[:l1.n_split]
        gthr = gate_threshold(seed, len(seed), gate_pct)
        vol_gate = l1.vf[:n] <= gthr
    veto = np.zeros(n, dtype=bool)
    confirm = np.ones(n, dtype=bool)
    specs = [s for s in l2_params.get("indicators", []) if s.get("enabled")]
    if specs:
        inds = library.from_specs(specs)
        src = runner.indicator_source_1min(d, d1, l1.bar_td) if l2_params.get("ind_1min") else None
        votes = runner.compute_votes(d, box, inds, src=src)
        veto = np.asarray(runner.veto_mask(d, box, inds, src=src, votes=votes), dtype=bool)[:n]
        confirm = np.asarray(runner.confirm_mask(d, box, inds, K, src=src, votes=votes), dtype=bool)[:n]
    return vol_gate, veto, confirm


def _l2_gate_masks(l1, l2_params: dict) -> np.ndarray:
    """L2's own per-bar eligibility = vol_gate ∧ ¬veto ∧ confirm≥K (the ANDed components)."""
    vol_gate, veto, confirm = l2_gate_components(l1, l2_params)
    return vol_gate & ~veto & confirm


def force_close_on_l1_entry(cand: list[dict], l1_entries, dec_dates: np.ndarray,
                            dec_close: np.ndarray, pv: float) -> list[dict]:
    """Truncate each candidate at the earliest L1 entry STRICTLY inside (entry_idx, exit_bar). Exit at
    that bar's close, reason 'L1-entry'; P/L recomputed honestly (never dropped)."""
    l1_entries = sorted(int(j) for j in l1_entries)
    out = []
    for t in cand:
        e = int(t["entry_idx"])
        xb = int(np.searchsorted(dec_dates, np.datetime64(t["exit_time"]), side="left"))
        xb = max(xb, e + 1)
        hit = next((j for j in l1_entries if e < j < xb), None)
        if hit is None:
            out.append(t)
            continue
        ep = float(t["entry_price"])
        xp = float(dec_close[hit])
        pts = (xp - ep) if t["direction"] == "long" else (ep - xp)
        tt = dict(t)
        tt["exit_time"] = dec_dates[hit]
        tt["exit_price"] = xp
        tt["exit_reason"] = "L1-entry"
        tt["pnl_points"] = pts
        out.append(tt)
    return out


@dataclass
class L2Result:
    params: dict
    ledger: list
    n_skipped_breaker: int
    n_locks: int
    n_l1_entry_exits: int


def run_l2(l1, l2_params: dict, bar_mask=None, exit_mode: str = "l1_priority") -> L2Result:
    """exit_mode (spec round 1 vs 2):
      'l1_priority' (default, round 1) — when L1 opens during an L2 trade, L2 force-closes (reason
                     'L1-entry'); L1 wins ties.
      'keep_l2'     (round 2 A/B)      — L2 keeps its position to its own SL/TP; the overlapping L1 trade
                     yields. (The combined book then drops the overlapped L1 trades — see round2.compare.)"""
    if exit_mode not in ("l1_priority", "keep_l2"):
        raise ValueError(f"exit_mode must be 'l1_priority' or 'keep_l2' (got {exit_mode!r})")
    d, d1 = l1.df_dec, l1.df1
    n = len(d)
    dec_dates = d["Date"].to_numpy()
    dec_close = d["Close"].to_numpy(float)
    pv = float(config.NQ_POINT_VALUE)

    dropped_mask = np.zeros(n, dtype=bool)
    for ds in l1.dropped_signals:
        dropped_mask[int(ds["idx"])] = True
    l1_flat = ~l1.state_timeline
    l2_gate = dropped_mask & l1_flat & _l2_gate_masks(l1, l2_params)
    if bar_mask is not None:                                  # window L2 to a bar range (in-sample / OOS)
        l2_gate = l2_gate & np.asarray(bar_mask, dtype=bool)[:n]

    _cap_mode = str(l2_params.get("cap_mode") or "none")
    if _cap_mode == "eod":
        from optimize.trading_days import eod_targets
        _eod_t, _eod_sl = eod_targets(d1["Date"].to_numpy(), int(l2_params.get("eod_margin_min", 15) or 15))
    else:
        _eod_t = _eod_sl = None
    cand = fast_backtest(
        dec_dates, dec_close, l1.sig_int, l2_gate,
        d1["Date"].to_numpy(), d1["High"].to_numpy(float),
        d1["Low"].to_numpy(float), d1["Close"].to_numpy(float),
        float(l2_params["sl_soft"]), float(l2_params["sl_hard"]), float(l2_params["tp"]),
        bool(l2_params.get("flip", False)),
        cap_1min=int(l2_params.get("cap_1min", 0) or 0),
        cap_mode=_cap_mode, eod_target=_eod_t, session_last=_eod_sl,
        **{k: l2_params.get(k) for k in ("long_sl_soft", "long_sl_hard", "long_tp",
                                         "short_sl_soft", "short_sl_hard", "short_tp")})

    if exit_mode == "keep_l2":
        cand_fc = cand                                       # L2 runs to its own exit; L1 yields
    else:
        l1_entries = [int(t["entry_idx"]) for t in l1.ledger]
        cand_fc = force_close_on_l1_entry(cand, l1_entries, dec_dates, dec_close, pv)
    taken, skipped, n_locks = apply_breaker(cand_fc, pv, float(l2_params.get("dd_limit", 0.0)),
                                            int(l2_params.get("cooldown", 0)))

    # label direction vs the box and count forced exits
    n_l1_exit = 0
    for t in taken:
        box_long = l1.sig_int[int(t["entry_idx"]) - 1] == 1
        t["l2_dir_vs_box"] = "agree" if (box_long == (t["direction"] == "long")) else "oppose"
        if t["exit_reason"] == "L1-entry":
            n_l1_exit += 1

    return L2Result(params=dict(l2_params), ledger=taken, n_skipped_breaker=skipped,
                    n_locks=n_locks, n_l1_entry_exits=n_l1_exit)
