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


def _bar_category(row, layer: str) -> str:
    """Per-bar no-entry category FROM THIS LAYER'S perspective: box_silence|gate|indicator|opportunity|none.
    L1 reads its own box_cause; L2 reads its own per-bar decision (l2_reason) on the bars it evaluated —
    so L2's streak/total boxes reflect L2's gate/veto, not L1's market view (Task-4 review fix)."""
    if layer == "L1":
        c = row.box_cause
        if c == "box_silence":
            return "box_silence"
        if c in _GATE:
            return "gate"
        if c in _INDIC:
            return "indicator"
        if c == "would_enter":
            return "opportunity"
        return "none"
    c = row.l2_reason                       # L2: only set on bars L2 evaluated (dropped + L1-flat)
    if c in _GATE:
        return "gate"
    if c in _INDIC:
        return "indicator"
    if c in ("entered", "passed"):
        return "opportunity"
    return "none"                           # bars L2 didn't evaluate (incl. L1 box_silence — N/A for L2)


def _noentry_streak(rows: list, cats: list, bar_seconds: int) -> dict:
    """Longest run of consecutive BLOCKED bars (gate/indicator), reset by an entry opportunity;
    box_silence/none neither extend nor break it. Layer-aware via `cats`."""
    best_n = 0
    best_s = best_e = None
    cur = 0
    cur_s = None
    for r, c in zip(rows, cats):
        if c in ("gate", "indicator"):
            if cur == 0:
                cur_s = r
            cur += 1
            if cur > best_n:
                best_n, best_s, best_e = cur, cur_s, r
        elif c == "opportunity":
            cur = 0
    days = round((best_e.time - best_s.time) / 86400.0, 1) if best_n else 0.0
    start = pd.Timestamp(best_s.time, unit="s").strftime("%Y-%m-%d") if best_n else None
    return {"n": best_n, "days": days, "start": start}


def boxes_for_layer(result, layer: str, bar_seconds: int) -> dict:
    log = result.log
    entries = [r for r in log if r.layer == layer and r.decision == "entry"]
    out = _financials(entries)

    # per-bar no-entry category from THIS layer's perspective, over ALL bars (matches legacy pause_totals)
    cats = [_bar_category(r, layer) for r in log]
    box_sil = np.array([c == "box_silence" for c in cats], dtype=bool)
    gate = np.array([c == "gate" for c in cats], dtype=bool)
    indic = np.array([c == "indicator" for c in cats], dtype=bool)
    pos = np.array([r.position_owner == layer for r in log], dtype=bool)

    streak = _noentry_streak(log, cats, bar_seconds)
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


def _merged_dd(log: list) -> float:
    """Max underwater of the merged L1+L2 equity, cumulated in EXIT-time order (matches metrics.combined)."""
    ex = sorted([r for r in log if r.decision == "entry"], key=lambda r: (r.exit_time or 0))
    pnls = np.array([r.pnl for r in ex], dtype=float)
    if not len(pnls):
        return 0.0
    eq = np.cumsum(pnls)
    return float((np.maximum.accumulate(eq) - eq).max())


def combined_boxes(result, bar_seconds: int) -> dict:
    """Per-box combination rules for the combined view (NOT uniform max):
      sum      → pnl, n_taken (trades), n_candidates, breaker locks  (no layer tag)
      recompute→ max_dd (merged EXIT-ordered equity), win, pf, exposure  (from the combined trade set)
      max+tag  → all streak boxes + warmup + indicator_req  (which layer produced the larger)
      guardrail→ l1_only_dd, uplift, dd_not_worse, n_l1_entry_exits  (kept; additive)
      excluded → all *_total keys (deferred — kept only in the individual views)."""
    log = result.log
    l1 = boxes_for_layer(result, "L1", bar_seconds)
    l2 = boxes_for_layer(result, "L2", bar_seconds)

    def mx_num(key):
        a, b = l1[key], l2[key]
        return {"value": max(a, b), "layer": ("L1" if a >= b else "L2")}

    def mx_dur(key):
        a, b = l1[key], l2[key]
        win_l1 = a["bars"] >= b["bars"]
        return {"value": (a if win_l1 else b), "layer": ("L1" if win_l1 else "L2")}

    entries = [r for r in log if r.decision == "entry"]
    pnls = np.array([r.pnl for r in entries], dtype=float)
    wins, losses = pnls[pnls > 0], pnls[pnls < 0]
    win = round(100 * float((pnls > 0).mean()), 1) if len(pnls) else 0.0
    pf = round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() != 0 else None
    n_taken = l1["n_taken"] + l2["n_taken"]
    n_candidates = l1["n_candidates"] + l2["n_candidates"]
    combined_pnl = round(l1["pnl"] + l2["pnl"], 2)
    merged_dd = round(_merged_dd(log), 2)

    out = {
        # sum (no layer tag)
        "pnl": {"value": combined_pnl},
        "n_taken": {"value": n_taken},
        "n_candidates": {"value": n_candidates},
        "n_locks": {"value": l1["n_locks"] + l2["n_locks"]},
        # recompute from the combined trade set
        "max_dd": {"value": merged_dd},
        "win": {"value": win},
        "pf": {"value": pf},
        "exposure": {"value": round(100 * n_taken / max(n_candidates, 1), 1)},
        # max + producing-layer tag
        "noentry_streak_n": mx_num("noentry_streak_n"),
        "box_silence": mx_dur("box_silence"),
        "gate_noentry": mx_dur("gate_noentry"),
        "indicator_noentry": mx_dur("indicator_noentry"),
        "position_hold": mx_dur("position_hold"),
        "warmup": mx_dur("warmup"),
        "indicator_req": mx_dur("indicator_req"),
        # guardrails (kept — additive; present in today's combined.html)
        "l1_only_dd": {"value": round(l1["max_dd"], 2)},
        "uplift": {"value": round(l2["pnl"], 2)},          # L2's exact contribution (L1/L2 trades disjoint)
        "dd_not_worse": {"value": merged_dd <= round(l1["max_dd"], 2)},
        "n_l1_entry_exits": {"value": sum(1 for r in log if r.layer == "L2" and r.exit_reason == "L1-entry")},
    }
    # the no-entry-streak's days/start follow the winning layer
    streak_layer = out["noentry_streak_n"]["layer"]
    src = l1 if streak_layer == "L1" else l2
    out["noentry_streak_days"] = {"value": src["noentry_streak_days"], "layer": streak_layer}
    out["noentry_streak_start"] = {"value": src["noentry_streak_start"], "layer": streak_layer}
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
