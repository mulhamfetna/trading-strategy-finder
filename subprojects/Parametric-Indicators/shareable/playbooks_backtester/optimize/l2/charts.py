"""Per-layer engine-style chart series, derived STRICTLY from ONE causal run (CausalResult + the
L1Result for the vol-forecast array). This is what lets the unified dashboard show the engine charts
(vol / vol-gate line / engine-state / equity / drawdown / event log) on the L2 and Combined tabs —
which have NONE today — without spinning up a second engine. Charts and boxes therefore come from the
same windowed causal pass, so they cannot disagree.

Shapes match what the frontend already consumes from strategy.build_payload:
  vol       : [{time, value}]  — the HAR-RV forecast (market; same series for every layer)
  gate_thr  : float | None     — the layer's vol-gate threshold (a horizontal line); None when gate off
  state     : [{time, value}]  — sparse engine-state: 1 at a taken entry, 0 at a breaker-locked skip
  equity    : [{time, value}]  — the layer's running equity (per-layer booked; combined = merged book)
  drawdown  : [{time, value}]  — the layer's underwater drawdown
  events    : [{time, type, text}] — ENTRY / SKIP rows from the log (entry/exit/lock attribution)

NOTE (never-degrade): the L1 tab keeps strategy.build_payload's RICHER event log (would-be P/L on
skips + per-indicator vote chips), which run_causal defers. charts.py is the source for L2/Combined
(and an L1 fallback) — its event log carries the entry/skip events the causal log records.
"""
from __future__ import annotations

import numpy as np

from volatility import gate_threshold


def _layer_params(result, layer: str) -> dict:
    return result.l1_params if layer in ("L1", "combined") else result.l2_params


def charts_for_layer(result, l1, layer: str) -> dict:
    """Engine chart series for one layer ('L1' | 'L2' | 'combined') from the causal run."""
    log = result.log
    vf = np.asarray(l1.vf)

    # vol — the market HAR-RV forecast, one point per candle (same for every layer).
    vol = [{"time": r.time, "value": round(float(vf[r.i]), 1)} for r in log if r.i < len(vf)]

    # vol-gate threshold (scalar) for this layer — seeded on the IN-SAMPLE prefix (l1.vf_seed), so it is
    # window-correct by construction (the STEP 3b fix).
    gp = float(_layer_params(result, layer).get("gate_pct", 0) or 0)
    seed = l1.vf_seed if l1.vf_seed is not None else vf[: l1.n_split]
    gate_thr = round(gate_threshold(seed, len(seed), gp), 1) if gp > 0 else None

    # equity + drawdown.
    if layer == "combined":
        entries = sorted((r for r in log if r.decision == "entry"), key=lambda r: (r.exit_time or 0))
        eq = peak = 0.0
        equity, drawdown = [], []
        for r in entries:                                  # recompute over the MERGED book (exit-ordered)
            eq += r.pnl
            peak = max(peak, eq)
            equity.append({"time": r.exit_time, "value": round(eq, 2)})
            drawdown.append({"time": r.exit_time, "value": round(peak - eq, 2)})
    else:
        entries = [r for r in log if r.layer == layer and r.decision == "entry"]   # equity/dd pre-booked
        equity = [{"time": r.exit_time, "value": r.equity} for r in entries]
        drawdown = [{"time": r.exit_time, "value": r.dd} for r in entries]

    # engine-state (breaker): 1 at a taken entry of this layer; 0 at a breaker-locked skip. Skips are
    # recorded only for L1 (would_enter → breaker_locked), so they appear on L1 + combined, not L2.
    in_layer_entry = (lambda r: r.decision == "entry") if layer == "combined" \
        else (lambda r: r.decision == "entry" and r.layer == layer)
    skip_here = layer in ("L1", "combined")
    state, events = [], []
    for r in log:
        if in_layer_entry(r):
            state.append({"time": r.time, "value": 1})
            txt = r.text or f"{(r.direction or '').upper()} @ {r.entry_price:.1f}" if r.entry_price else r.text
            events.append({"time": r.time, "type": "ENTRY", "text": txt,
                           "indicators": r.indicators or []})
        elif skip_here and r.event_type == "SKIP":
            state.append({"time": r.time, "value": 0})
            wb = "" if r.would_be_pnl is None else f" (would-be {r.would_be_pnl:+,.0f})"
            events.append({"time": r.time, "type": "SKIP", "text": (r.text or f"LOCKED — breaker skip{wb}"),
                           "indicators": []})

    return {"vol": vol, "gate_thr": gate_thr, "state": state,
            "equity": equity, "drawdown": drawdown, "events": events}
