"""Causal log-first core (Tasks 2-3 of the rebuild).

`run_causal` produces ONE complete per-candle log — the single source of truth from which every
dashboard box, chart and CSV is later derived. Single shared account, L1 priority, L2 force-closed on
an L1 entry.

Parity by construction: the actual trades come from the EXISTING oracle engines — `l1_runner.run_l1`
(L1) and `engine.run_l2` (L2, l1_priority) — which already encode the single-account causal semantics
(L2 only on L1's dropped+flat bars; force-close on a later L1 entry). `run_causal` walks the decision
bars in time order and emits a `LogRow` per bar that PROJECTS those results: who (if anyone) entered,
and for a non-entry, why and which layer. Because the trades are the oracle's, L1/L2 P/L, DD, counts
and the force-closed subset match the legacy path exactly (see test_logbook.py).

`LogRow` is a strict SUPERSET of today's strategy.py event fields (additive rule): event_type mirrors
ENTRY/WIN/LOSS/LOCK/UNLOCK/SKIP/NOENTRY/WARMUP/WARMED; box_cause preserves the underlying box/gate/veto/
confirm cause even on open_trade/force_closed rows (legacy pause_totals counts those bars).

Fields populated by run_causal now: i, time, layer, decision, reason, box_cause, event_type, direction,
box_dir, entry/exit prices+time, exit_reason, pnl (full precision), equity, dd (per-layer running),
in_position, position_owner, l2_reason. DEFERRED display fields — present in the schema (so the superset
is frozen) but populated only when the dashboards are wired (Tasks 8-10), NOT by run_causal yet:
`text` (human-readable line), `indicators` (per-bar vote detail), `veto_flip` (REVERSED annotation),
and `would_be_pnl` (the SKIP/breaker-skipped candidate's would-be P/L — needs the engine to surface the
skipped candidate's pnl, which apply_breaker currently discards). None affect trade parity.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd

from optimize.l2 import l1_runner, engine, payload
from indicators import library


@dataclass
class LogRow:
    i: int
    time: int
    layer: str | None
    decision: str            # "entry" | "nonentry"
    reason: str              # entered|box_silence|vol_gated|vetoed|confirm<K|open_trade|force_closed|breaker_locked|breaker_unlocked|warmup|warmed
    box_cause: str | None = None     # underlying L1 box/gate/veto/confirm cause, kept even when in-position
    event_type: str | None = None    # ENTRY|WIN|LOSS|LOCK|UNLOCK|SKIP|NOENTRY|WARMUP|WARMED (superset of strategy.py)
    text: str = ""
    direction: str | None = None
    box_dir: str | None = None
    veto_flip: bool = False
    indicators: list = field(default_factory=list)
    entry_price: float | None = None
    exit_time: int | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    would_be_pnl: float | None = None
    pnl: float = 0.0
    equity: float = 0.0
    dd: float = 0.0
    in_position: bool = False
    position_owner: str | None = None
    l2_reason: str | None = None     # L2's own decision on a bar it evaluated (dropped + L1-flat): entered|vol_gated|vetoed|confirm<K|passed


@dataclass
class CausalResult:
    tf: str
    l1_params: dict
    l2_params: dict
    log: list
    n: int
    dec_dates: object
    warmup: dict = field(default_factory=dict)   # {l1:{warmup_bars,indicator_req_bars}, l2:{...}}


def _epoch(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def _state_timeline(ledger: list, dec_dates: np.ndarray, n: int) -> np.ndarray:
    """Per-bar in-position mask for a ledger (same [entry_idx, exit_bar) convention as build_state_timeline)."""
    in_pos = np.zeros(n, dtype=bool)
    for t in ledger:
        e = int(t["entry_idx"])
        xb = int(np.searchsorted(dec_dates, np.datetime64(t["exit_time"]), side="left"))
        in_pos[e:min(max(xb, e + 1), n)] = True
    return in_pos


def _warmup_for(params: dict) -> dict:
    on = [s for s in params.get("indicators", []) if s.get("enabled")]
    if not on:
        return {"warmup_bars": 0, "indicator_req_bars": 0}
    inds = library.from_specs(on)
    mx = max(int(ind.warmup_bars()) for ind in inds)
    return {"warmup_bars": mx, "indicator_req_bars": mx}


def _l2_reason(eligible_eval: bool, entered: bool, vol_gate: bool, veto: bool, confirm: bool) -> str | None:
    """Why L2 acted/declined on a bar it evaluated (dropped signal AND L1 flat). None if not evaluated."""
    if not eligible_eval:
        return None
    if entered:
        return "entered"
    if not vol_gate:
        return "vol_gated"
    if veto:
        return "vetoed"
    if not confirm:
        return "confirm<K"
    return "passed"          # L2 gate passed but no open (e.g. already in an L2 position / breaker)


def run_causal(l1_params: dict, l2_params: dict, tf: str = "4h", bar_mask=None) -> CausalResult:
    """Single causal pass → complete per-candle log. l1_params=None or the frozen-lean default uses the
    cached frozen L1 (byte-identical to the oracle); any other dict runs an arbitrary L1."""
    l1p = payload.validate_layer_params(l1_params)
    l2p = payload.validate_layer_params(l2_params)
    # frozen default → cached oracle; else custom L1 (memoised by hash inside run_l1_cached)
    use_frozen = (l1p == payload.l1_default_params(tf))
    l1 = payload.run_l1_cached(tf) if use_frozen else payload.run_l1_cached(tf, params=l1p)
    res = engine.run_l2(l1, l2p)                                   # l1_priority + force-close (the oracle)

    n = len(l1.df_dec)
    dec_dates = l1.df_dec["Date"].to_numpy()
    l1_state = np.asarray(l1.state_timeline, dtype=bool)[:n]
    l2_state = _state_timeline(res.ledger, dec_dates, n)
    l1_entry = {int(t["entry_idx"]): t for t in l1.ledger}
    l2_entry = {int(t["entry_idx"]): t for t in res.ledger}
    cause = l1.cause
    sig = np.asarray(l1.sig_int)[:n]
    dropped = {int(d["idx"]) for d in l1.dropped_signals}          # veto + vol_gate bars (the L2 candidate set)
    vg, vt, cf = engine.l2_gate_components(l1, l2p)                # L2's own gate decomposition

    log: list[LogRow] = []
    for i in range(n):
        ts = _epoch(dec_dates[i])
        c = cause[i] if i < len(cause) else None
        box_dir = "long" if (i > 0 and sig[i - 1] == 1) else ("short" if (i > 0 and sig[i - 1] == -1) else None)
        t1, t2 = l1_entry.get(i), l2_entry.get(i)
        if t1 is not None:
            log.append(LogRow(i=i, time=ts, layer="L1", decision="entry", reason="entered", box_cause=c,
                              event_type="ENTRY", direction=t1["direction"], box_dir=box_dir,
                              entry_price=float(t1["entry_price"]), exit_time=_epoch(t1["exit_time"]),
                              exit_price=float(t1["exit_price"]), exit_reason=t1["exit_reason"],
                              pnl=float(t1["pnl"]), in_position=True, position_owner="L1"))
        elif t2 is not None:
            log.append(LogRow(i=i, time=ts, layer="L2", decision="entry", reason="entered", box_cause=c,
                              event_type="ENTRY", direction=t2["direction"], box_dir=box_dir,
                              entry_price=float(t2["entry_price"]), exit_time=_epoch(t2["exit_time"]),
                              exit_price=float(t2["exit_price"]), exit_reason=t2["exit_reason"],
                              pnl=float(t2["pnl"]), in_position=True, position_owner="L2",
                              l2_reason="entered"))
        else:
            if l1_state[i]:
                reason, owner, ev = "open_trade", "L1", "NOENTRY"
            elif l2_state[i]:
                reason, owner, ev = "open_trade", "L2", "NOENTRY"
            elif c == "would_enter":
                reason, owner, ev = "breaker_locked", None, "SKIP"   # L1 would-enter but breaker/cooldown skipped it
            else:
                reason, owner, ev = (c or "box_silence"), None, "NOENTRY"
            l2r = _l2_reason(i in dropped and not l1_state[i], False, bool(vg[i]), bool(vt[i]), bool(cf[i]))
            log.append(LogRow(i=i, time=ts, layer=owner, decision="nonentry", reason=reason, box_cause=c,
                              event_type=ev, box_dir=box_dir, in_position=bool(l1_state[i] or l2_state[i]),
                              position_owner=owner, l2_reason=l2r))

    # per-layer running equity + underwater drawdown, booked in exit-time order and written back onto the
    # entry row (so the log carries each layer's equity curve directly — used by the chart tasks).
    for lyr in ("L1", "L2"):
        rows = sorted([r for r in log if r.layer == lyr and r.decision == "entry"], key=lambda r: r.exit_time)
        eq = peak = 0.0
        for r in rows:
            eq += r.pnl
            peak = max(peak, eq)
            r.equity = round(eq, 2)
            r.dd = round(peak - eq, 2)

    return CausalResult(tf=tf, l1_params=l1p, l2_params=l2p, log=log, n=n, dec_dates=dec_dates,
                        warmup={"l1": _warmup_for(l1p), "l2": _warmup_for(l2p)})
