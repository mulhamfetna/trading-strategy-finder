"""Boxes + CSV derived STRICTLY from the per-candle log (Task 4) — the single source of truth.

`boxes_for_layer(result, layer, bar_seconds)` returns the SAME box keys the standalone L1/L2 dashboards
render, computed by filtering the causal log to one layer:
  - financials (pnl/max_dd/win/pf) from that layer's entry rows (exit-ordered for DD);
  - the no-entry STREAK boxes from each bar's `box_cause` (longest run);
  - the `*_total` boxes from `box_cause` over ALL of the layer's bars (incl. open_trade/force_closed),
    mirroring legacy `pause_totals` which counts regardless of in-position state;
  - `position_hold` from the layer's in-position spans;
  - `warmup`/`indicator_req` from `result.warmup[layer]` (config-derived — the documented exception);
  - `n_locks`/`n_skipped` from `result.counts[layer]` (engine-event scalars — like warmup); `n_candidates`
    and `exposure` are then log-derived (`n_taken + n_skipped`).

`box_cause` → pause category mapping is EXACT vs legacy: box_silence↔~cand, vol_gated↔gate_block,
{vetoed,confirm<K}↔indic_block (same priority as counterfactual_pause.attribute / pause_streaks)."""
from __future__ import annotations

import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd

from optimize import pause_streaks

_BLOCKED = {"vol_gated", "vetoed", "confirm<K"}          # box signalled but blocked (no-entry streak set)
_GATE = {"vol_gated"}
_INDIC = {"vetoed", "confirm<K"}


def _financials(entries: list) -> dict:
    ex = sorted(entries, key=lambda r: (r.exit_time if r.exit_time is not None else 0))
    pnls = np.array([r.pnl for r in ex], dtype=float)
    if len(pnls):
        eq = np.cumsum(pnls)
        max_dd = float((np.maximum.accumulate(eq) - eq).max())
    else:
        max_dd = 0.0
    wins, losses = pnls[pnls > 0], pnls[pnls < 0]
    return dict(
        pnl=float(pnls.sum()) if len(pnls) else 0.0,
        max_dd=max_dd,
        win=round(100 * float((pnls > 0).mean()), 1) if len(pnls) else 0.0,
        pf=(round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() != 0 else None),
        n_taken=len(entries),
    )


def _noentry_streak(rows: list, bar_seconds: int) -> dict:
    """Longest run of consecutive BLOCKED box-signal bars (gate/veto/confirm<K), reset by an entry
    opportunity (would_enter); box-silence neither extends nor breaks it. Matches the standalone box."""
    best_n = 0
    best_s = best_e = None
    cur = 0
    cur_s = None
    for r in rows:
        c = r.box_cause
        if c in _BLOCKED:
            if cur == 0:
                cur_s = r
            cur += 1
            if cur > best_n:
                best_n, best_s, best_e = cur, cur_s, r
        elif c == "would_enter":
            cur = 0
    days = round((best_e.time - best_s.time) / 86400.0, 1) if best_n else 0.0
    start = pd.Timestamp(best_s.time, unit="s").strftime("%Y-%m-%d") if best_n else None
    return {"n": best_n, "days": days, "start": start}


def boxes_for_layer(result, layer: str, bar_seconds: int) -> dict:
    log = result.log
    entries = [r for r in log if r.layer == layer and r.decision == "entry"]
    out = _financials(entries)

    # per-bar masks from box_cause (over ALL bars — matches legacy pause_totals/pause_metrics)
    bc = [r.box_cause for r in log]
    box_sil = np.array([c == "box_silence" for c in bc], dtype=bool)
    gate = np.array([c in _GATE for c in bc], dtype=bool)
    indic = np.array([c in _INDIC for c in bc], dtype=bool)
    pos = np.array([r.position_owner == layer for r in log], dtype=bool)

    streak = _noentry_streak(log, bar_seconds)
    out.update(
        noentry_streak_n=streak["n"], noentry_streak_days=streak["days"], noentry_streak_start=streak["start"],
        box_silence=pause_streaks._dur(pause_streaks.longest_run(box_sil), bar_seconds),
        gate_noentry=pause_streaks._dur(pause_streaks.longest_run(gate), bar_seconds),
        indicator_noentry=pause_streaks._dur(pause_streaks.longest_run(indic), bar_seconds),
        position_hold=pause_streaks._dur(pause_streaks.longest_run(pos), bar_seconds),
        box_silence_total=pause_streaks._dur(int(box_sil.sum()), bar_seconds),
        gate_noentry_total=pause_streaks._dur(int(gate.sum()), bar_seconds),
        indicator_noentry_total=pause_streaks._dur(int(indic.sum()), bar_seconds),
        position_hold_total=pause_streaks._dur(int(pos.sum()), bar_seconds),
        noentry_total=pause_streaks._dur(int(box_sil.sum() + gate.sum() + indic.sum()), bar_seconds),
    )

    counts = (result.counts or {}).get(layer.lower(), {})
    n_skipped = int(counts.get("n_skipped", 0))
    n_candidates = out["n_taken"] + n_skipped
    out.update(
        n_candidates=n_candidates,
        n_locks=int(counts.get("n_locks", 0)),
        exposure=round(100 * out["n_taken"] / max(n_candidates, 1), 1),
    )
    w = (result.warmup or {}).get(layer.lower(), {})
    out["warmup"] = pause_streaks._dur(int(w.get("warmup_bars", 0)), bar_seconds)
    out["indicator_req"] = pause_streaks._dur(int(w.get("indicator_req_bars", 0)), bar_seconds)
    return out


_CSV_COLS = ["i", "time", "datetime", "layer", "decision", "reason", "box_cause", "event_type",
             "direction", "box_dir", "entry_price", "exit_time", "exit_price", "exit_reason",
             "pnl", "equity", "dd", "in_position", "position_owner", "l2_reason"]


def log_to_csv(log: list):
    """Return (header, rows) for the full per-candle log — exported as CSV (the `layer` column lets L1/L2
    be separated in a spreadsheet). One row per candle."""
    header = ["i", "time", "layer", "decision"] + [c for c in _CSV_COLS if c not in ("i", "time", "layer", "decision")]
    rows = []
    for r in log:
        dt = pd.Timestamp(r.time, unit="s").strftime("%Y-%m-%d %H:%M")
        rec = {"i": r.i, "time": r.time, "datetime": dt, "layer": r.layer or "", "decision": r.decision,
               "reason": r.reason, "box_cause": r.box_cause or "", "event_type": r.event_type or "",
               "direction": r.direction or "", "box_dir": r.box_dir or "",
               "entry_price": r.entry_price if r.entry_price is not None else "",
               "exit_time": r.exit_time if r.exit_time is not None else "",
               "exit_price": r.exit_price if r.exit_price is not None else "",
               "exit_reason": r.exit_reason or "", "pnl": r.pnl, "equity": r.equity, "dd": r.dd,
               "in_position": r.in_position, "position_owner": r.position_owner or "",
               "l2_reason": r.l2_reason or ""}
        rows.append([rec[c] for c in header])
    return header, rows
