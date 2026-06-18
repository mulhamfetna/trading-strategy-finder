"""L2 dashboard orchestrator — the L2 analogue of strategy.build_payload. Runs the CACHED frozen L1
once per process, applies an L2 profile via the built run_l2, scores it (standalone + combined
guardrail), and serializes everything the l2.html charts need. Pure (no HTTP). Also: L2-profile store."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, metrics, dataset        # noqa: E402

_L2_PROFILES = _PI / "profiles" / "l2_profiles.json"
_l1_cache: dict = {}


def get_l1(tf: str = "4h"):
    """Run the frozen lean L1 once per process; cache by timeframe (first call ~38s)."""
    if tf not in _l1_cache:
        _l1_cache[tf] = l1_runner.run_l1(tf)
    return _l1_cache[tf]


def _epoch(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def _spans(state_timeline: np.ndarray, dec_dates: np.ndarray) -> list[dict]:
    """Contiguous True runs of the L1 in-position timeline -> [{from, to}] in epoch seconds."""
    out = []
    n = len(state_timeline)
    i = 0
    while i < n:
        if state_timeline[i]:
            j = i
            while j + 1 < n and state_timeline[j + 1]:
                j += 1
            out.append({"from": _epoch(dec_dates[i]), "to": _epoch(dec_dates[j])})
            i = j + 1
        else:
            i += 1
    return out


def _equity(trades: list[dict]) -> list[dict]:
    """Cumulative equity points at each trade's exit_time (sorted)."""
    pts = sorted(((_epoch(t["exit_time"]), float(t["pnl"])) for t in trades), key=lambda x: x[0])
    out, cum = [], 0.0
    for ts, pnl in pts:
        cum += pnl
        out.append({"time": ts, "value": round(cum, 2)})
    return out


def _l2_trade_rows(trades: list[dict], l2_params: dict) -> list[dict]:
    """Serialize L2 trades + compute SL/TP lines from entry_price ± params (fast_backtest trades do
    not carry the lines; the slow engine does — we reconstruct them deterministically)."""
    ss = float(l2_params["sl_soft"]); sh = float(l2_params["sl_hard"]); tp = float(l2_params["tp"])
    rows = []
    for t in trades:
        ep = float(t["entry_price"])
        is_long = t["direction"] == "long"
        rows.append({
            "entry_time": _epoch(t["entry_time"]), "exit_time": _epoch(t["exit_time"]),
            "direction": t["direction"], "entry_price": ep, "exit_price": float(t["exit_price"]),
            "sl_soft_line": ep - ss if is_long else ep + ss,
            "sl_hard_line": ep - sh if is_long else ep + sh,
            "tp_hard_line": ep + tp if is_long else ep - tp,
            "exit_reason": t["exit_reason"], "pnl": round(float(t["pnl"]), 2),
            "l2_dir_vs_box": t.get("l2_dir_vs_box", "agree"),
        })
    return rows


def build_l2_payload(l2_params: dict, tf: str = "4h") -> dict:
    t0 = time.time()
    l1 = get_l1(tf)
    res = engine.run_l2(l1, l2_params)
    ds = dataset.build_dataset(l1)
    dec_dates = l1.df_dec["Date"].to_numpy()

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo),
                "close": float(c)}
               for d, o, h, lo, c in zip(dec_dates, l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]
    dropped = [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"]}
               for d in l1.dropped_signals]

    meta = {"summary": {"l2": metrics.score(res), "combined": metrics.combined(l1, res)},
            "l1": {"n_trades": len(l1.ledger),
                   "pnl": round(sum(t["pnl"] for t in l1.ledger), 2),
                   "dropped": len(ds), "veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                   "flat_candidates": len(ds.flat_candidates())},
            "params": dict(l2_params, timeframe=tf),
            "run_ms": round((time.time() - t0) * 1000)}

    return {"meta": meta, "candles": candles,
            "l1_spans": _spans(l1.state_timeline, dec_dates),
            "dropped": dropped,
            "l2_trades": _l2_trade_rows(res.ledger, l2_params),
            "l2_equity": _equity(res.ledger),
            "combined_equity": _equity(list(l1.ledger) + list(res.ledger)),
            "l1_equity": _equity(l1.ledger)}


# --- L2-profile store (mirrors presets.load_user_profiles/save_user_profile) ------------------------
def load_l2_profiles() -> dict:
    if not _L2_PROFILES.exists():
        return {}
    try:
        d = json.loads(_L2_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l2_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("L2 profile name is required")
    profs = load_l2_profiles()
    profs[name] = preset
    _L2_PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _L2_PROFILES.write_text(json.dumps(profs, indent=1))
    return profs


def l2_config(tf: str = "4h") -> dict:
    """Drives the L2 form: indicator schema, the fixed-L1 summary, and saved L2 profiles."""
    from indicators import library
    l1 = get_l1(tf)
    ds = dataset.build_dataset(l1)
    return {"indicator_schema": library.schema(),
            "l1": {"label": "lean 4h champion (frozen)", "n_trades": len(l1.ledger),
                   "dropped": len(ds), "veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                   "flat_candidates": len(ds.flat_candidates())},
            "profiles": load_l2_profiles()}
