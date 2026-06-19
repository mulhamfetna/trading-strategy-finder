"""L2 dashboard backend — orchestration for the dashboard-inside-dashboard (frontend/l2.html).
Runs the cached frozen L1 (lean 4h) + a manual L2 profile, serializes a chart-ready payload, and
persists hand-tuned L2 profiles. server.py is a thin router over this module."""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import tempfile
from pathlib import Path

import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, metrics, dataset   # noqa: E402
from indicators import library                                # noqa: E402

_PROFILES = _PI / "profiles" / "l2_profiles.json"
_L1_PROFILES = _PI / "profiles" / "l1_profiles.json"
_L1_CACHE: dict = {}
_L1_CUSTOM_CACHE: dict = {}      # custom-L1 runs memoised in-process by (tf, params-hash); no disk footprint
# Disk cache for the FROZEN L1 run (deterministic → safe to persist). Keyed by tf + a hash of the lean
# params, so any param change invalidates it. Lives in a temp dir (no git footprint); recomputed if absent.
_DISK_CACHE = Path(tempfile.gettempdir()) / "wsh_l1_cache"


def _l1_cache_file(tf: str) -> Path:
    h = hashlib.sha256(json.dumps(l1_runner._lean_params(tf), sort_keys=True, default=str).encode()).hexdigest()[:16]
    return _DISK_CACHE / f"l1_{tf}_{h}.pkl"

# Deterministic anchor profile (no indicators / no vol gate => take every flat dropped signal).
PERMISSIVE: dict = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
                    "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


class L2ParamError(ValueError):
    """Invalid L2 profile parameter — surfaced to the UI as HTTP 400 (never silently clamped)."""


def run_l1_cached(tf: str = "4h", use_disk: bool = True, params: dict | None = None):
    """L1 run. params=None → the FROZEN lean champion: memoised in-process AND on disk (deterministic),
    so repeat processes load in ~1s instead of recomputing the ~38s 1-min indicator pass. params=<dict>
    → an ARBITRARY L1 profile (combined dashboard): run fresh, memoised in-process by (tf, params-hash);
    NOT disk-cached (the disk key is the lean-param hash). Set use_disk=False to force a fresh recompute."""
    if params is not None:
        h = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]
        key = (tf, h)
        if key not in _L1_CUSTOM_CACHE:
            _L1_CUSTOM_CACHE[key] = l1_runner.run_l1(tf, params=validate_layer_params(params))
        return _L1_CUSTOM_CACHE[key]
    if tf in _L1_CACHE:
        return _L1_CACHE[tf]
    cf = _l1_cache_file(tf)
    if use_disk and cf.exists():
        try:
            with open(cf, "rb") as f:
                r = pickle.load(f)
            _L1_CACHE[tf] = r
            return r
        except Exception:
            pass                                      # corrupt/stale pickle → recompute
    r = l1_runner.run_l1(tf)
    _L1_CACHE[tf] = r
    if use_disk:
        try:
            _DISK_CACHE.mkdir(parents=True, exist_ok=True)
            with open(cf, "wb") as f:
                pickle.dump(r, f)
        except Exception:
            pass                                      # cache write best-effort; never fail the run
    return r


def validate_layer_params(p: dict) -> dict:
    """Validate one layer's levers (L1 or L2 — identical schema); return a clean engine-ready dict
    (window='full'). Raise on any bad/missing value (no silent fallback)."""
    if not isinstance(p, dict):
        raise L2ParamError("params must be an object")

    def num(key, lo=None, hi=None):
        if key not in p or p[key] is None:
            raise L2ParamError(f"missing {key}")
        try:
            v = float(p[key])
        except (TypeError, ValueError):
            raise L2ParamError(f"{key} must be a number")
        if lo is not None and v < lo:
            raise L2ParamError(f"{key} must be >= {lo}")
        if hi is not None and v > hi:
            raise L2ParamError(f"{key} must be <= {hi}")
        return v

    out = dict(
        sl_soft=num("sl_soft", 1e-6), sl_hard=num("sl_hard", 1e-6), tp=num("tp", 1e-6),
        gate_pct=num("gate_pct", 0, 100), dd_limit=num("dd_limit", 0),
        cooldown=int(num("cooldown", 0)), k=int(num("k", 1)),
        flip=bool(p.get("flip", False)), ind_1min=bool(p.get("ind_1min", False)),
        window="full",
    )
    inds = p.get("indicators", [])
    if not isinstance(inds, list):
        raise L2ParamError("indicators must be a list")
    try:
        library.from_specs([s for s in inds if s.get("enabled")])   # validates indicator params
    except Exception as e:
        raise L2ParamError(f"bad indicator config: {e}")
    out["indicators"] = inds
    return out


# back-compat alias (L2 callers, tests)
validate_l2_params = validate_layer_params


def load_l2_profiles() -> dict:
    if not _PROFILES.exists():
        return {}
    try:
        d = json.loads(_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l2_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise L2ParamError("profile name is required")
    validate_layer_params(preset)                    # reject garbage (no silent save)
    profs = load_l2_profiles()
    profs[name] = preset
    _PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES.write_text(json.dumps(profs, indent=1))
    return profs


def load_l1_profiles() -> dict:
    if not _L1_PROFILES.exists():
        return {}
    try:
        d = json.loads(_L1_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l1_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise L2ParamError("profile name is required")
    validate_layer_params(preset)
    profs = load_l1_profiles()
    profs[name] = preset
    _L1_PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _L1_PROFILES.write_text(json.dumps(profs, indent=1))
    return profs


def l1_default_params(tf: str = "4h") -> dict:
    """The 'best L1' preset = the frozen lean champion, in the layer-param schema the forms speak."""
    return validate_layer_params(l1_runner._lean_params(tf))


def l2_default_params() -> dict:
    """The 'best L2' preset = the most recently saved L2 profile (the promoted extend champion), else PERMISSIVE."""
    profs = load_l2_profiles()
    if profs:
        return list(profs.values())[-1]
    return dict(PERMISSIVE)


def _epoch(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def _dedupe(series: list) -> list:
    """lightweight-charts needs unique, sorted times; keep the last value per timestamp."""
    last = {}
    for pt in series:
        last[pt["time"]] = pt["value"]
    return [{"time": t, "value": last[t]} for t in sorted(last)]


def _spans_from_timeline(state_timeline, dec_dates) -> list:
    """Contiguous [from,to] epoch spans where L1 is in-position (for chart shading)."""
    spans = []
    n = len(state_timeline)
    i = 0
    while i < n:
        if state_timeline[i]:
            j = i
            while j < n and state_timeline[j]:
                j += 1
            spans.append({"from": _epoch(dec_dates[i]), "to": _epoch(dec_dates[min(j, n - 1)])})
            i = j
        else:
            i += 1
    return spans


def _derive_lines(t: dict, p: dict) -> dict:
    """SL/TP line levels for display only (entry_price ± points; engine fill convention)."""
    ep = float(t["entry_price"])
    sl_hard = float(p["sl_hard"]); sl_soft = float(p["sl_soft"]); tp = float(p["tp"])
    if t["direction"] == "long":
        return {"sl_hard_line": ep - sl_hard, "sl_soft_line": ep - sl_soft, "tp_hard_line": ep + tp}
    return {"sl_hard_line": ep + sl_hard, "sl_soft_line": ep + sl_soft, "tp_hard_line": ep - tp}


def _equity_series(ledger: list) -> list:
    rows = sorted(ledger, key=lambda t: pd.Timestamp(t["exit_time"]))
    out = []
    eq = 0.0
    for t in rows:
        eq += float(t["pnl"])
        out.append({"time": _epoch(t["exit_time"]), "value": round(eq, 2)})
    return _dedupe(out)


def _combined_equity_series(l1_ledger: list, l2_ledger: list) -> list:
    merged = [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l1_ledger] \
        + [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l2_ledger]
    merged.sort(key=lambda x: x[0])
    out = []
    eq = 0.0
    for ts, pnl in merged:
        eq += pnl
        out.append({"time": int(ts.timestamp()), "value": round(eq, 2)})
    return _dedupe(out)


def _serialize_trade(t: dict, p: dict, layer: str) -> dict:
    """Common chart/log row for an L1 or L2 trade (epoch times, prices, P/L, SL/TP display lines)."""
    row = {"layer": layer,
           "entry_time": _epoch(t["entry_time"]), "exit_time": _epoch(t["exit_time"]),
           "direction": t["direction"], "entry_price": float(t["entry_price"]),
           "exit_price": float(t["exit_price"]), "exit_reason": t["exit_reason"],
           "pnl": round(float(t["pnl"]), 2)}
    if "l2_dir_vs_box" in t:
        row["l2_dir_vs_box"] = t["l2_dir_vs_box"]
    row.update(_derive_lines(t, p))
    return row


def build_combined_payload(l1_params: dict, l2_params: dict, tf: str = "4h") -> dict:
    """Combined dashboard backend: run an EDITABLE L1 + an L2 over its dropped signals, and serialize a
    chart-ready payload that reports BOTH layers and the combined book. Boxes come in 3 groups
    (L1 alone / L2 alone / combined); trades are merged into one source-labeled ledger."""
    l1p = validate_layer_params(l1_params)
    l2p = validate_layer_params(l2_params)
    l1 = run_l1_cached(tf, params=l1p)
    res = engine.run_l2(l1, l2p)
    ds = dataset.build_dataset(l1)
    dec_dates = l1.df_dec["Date"].to_numpy()

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
               for d, o, h, lo, c in zip(l1.df_dec["Date"], l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]
    dropped = [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"],
                "l1_flat": (not bool(l1.state_timeline[d["idx"]]))} for d in l1.dropped_signals]
    l1_trades = [_serialize_trade(t, l1p, "L1") for t in l1.ledger]
    l2_trades = [_serialize_trade(t, l2p, "L2") for t in res.ledger]
    # one merged ledger, sorted by exit, each row carrying its source layer (for the labeled log + CSV)
    merged = sorted(l1_trades + l2_trades, key=lambda r: r["exit_time"])

    return {
        "meta": {
            "summary": {"l1": metrics.score(l1), "l2": metrics.score(res),
                        "combined": metrics.combined(l1, res)},
            "dropped_counts": {"veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                               "total": len(ds), "flat_candidates": len(ds.flat_candidates())},
        },
        "candles": candles,
        "l1_spans": _spans_from_timeline(l1.state_timeline, dec_dates),
        "dropped": dropped,
        "l1_trades": l1_trades,
        "l2_trades": l2_trades,
        "ledger": merged,
        "l1_equity": _equity_series(l1.ledger),
        "l2_equity": _equity_series(res.ledger),
        "combined_equity": _combined_equity_series(l1.ledger, res.ledger),
    }


def build_l2_payload(l2_params: dict, tf: str = "4h") -> dict:
    p = validate_l2_params(l2_params)
    l1 = run_l1_cached(tf)
    res = engine.run_l2(l1, p)
    ds = dataset.build_dataset(l1)
    dec_dates = l1.df_dec["Date"].to_numpy()

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
               for d, o, h, lo, c in zip(l1.df_dec["Date"], l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]
    dropped = [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"],
                "l1_flat": (not bool(l1.state_timeline[d["idx"]]))} for d in l1.dropped_signals]
    l2_trades = []
    for t in res.ledger:
        row = {"entry_time": _epoch(t["entry_time"]), "exit_time": _epoch(t["exit_time"]),
               "direction": t["direction"], "entry_price": float(t["entry_price"]),
               "exit_price": float(t["exit_price"]), "exit_reason": t["exit_reason"],
               "pnl": round(float(t["pnl"]), 2), "l2_dir_vs_box": t.get("l2_dir_vs_box", "agree")}
        row.update(_derive_lines(t, p))
        l2_trades.append(row)

    return {
        "meta": {
            "l1": {"n_trades": len(l1.ledger), "pnl": round(sum(t["pnl"] for t in l1.ledger), 2)},
            "summary": {"l2": metrics.score(res), "combined": metrics.combined(l1, res)},
            "dropped_counts": {"veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                               "total": len(ds), "flat_candidates": len(ds.flat_candidates())},
        },
        "candles": candles,
        "l1_spans": _spans_from_timeline(l1.state_timeline, dec_dates),
        "dropped": dropped,
        "l2_trades": l2_trades,
        "l2_equity": _equity_series(res.ledger),
        "l1_equity": _equity_series(l1.ledger),
        "combined_equity": _combined_equity_series(l1.ledger, res.ledger),
    }
