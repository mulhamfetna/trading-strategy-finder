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

from optimize.l2 import l1_runner, engine, dataset   # noqa: E402
from indicators import library                                # noqa: E402

_PROFILES = _PI / "profiles" / "l2_profiles.json"
_L1_PROFILES = _PI / "profiles" / "l1_profiles.json"
_L1_CACHE: dict = {}
_L1_CUSTOM_CACHE: dict = {}      # custom-L1 runs memoised in-process by (tf, params-hash); no disk footprint
# Disk cache for the FROZEN L1 run (deterministic → safe to persist). Keyed by tf + a hash of the lean
# params, so any param change invalidates it. Lives in a temp dir (no git footprint); recomputed if absent.
_DISK_CACHE = Path(tempfile.gettempdir()) / "wsh_l1_cache"
# F2 — bump this whenever L1Result's fields change. It's part of the cache FILENAME, so old-schema
# pickles get a different name and are never loaded (a stale pickle would otherwise unpickle with a
# new field defaulted, e.g. the STEP-3b vf_seed=None bug). Loads also field-check (run_l1_cached).
_L1_CACHE_VER = "v4-instrument"


def _l1_cache_file(tf: str, instrument: str = "NQ") -> Path:
    h = hashlib.sha256((_L1_CACHE_VER + instrument + json.dumps(l1_runner._lean_params(tf), sort_keys=True,
                                                                default=str)).encode()).hexdigest()[:16]
    return _DISK_CACHE / f"l1_{instrument}_{tf}_{_L1_CACHE_VER}_{h}.pkl"


def _l1_custom_cache_file(tf: str, h: str, instrument: str = "NQ") -> Path:
    """Disk-cache path for an ARBITRARY (non-frozen) L1 profile, keyed by the params-hash `h` (computed by
    the caller) + instrument. Same temp dir + version scheme as the frozen cache, so a deterministic candidate
    L1 (e.g. a wsh6cold champion driving an L2 sweep) loads in ~1s on every worker respawn instead of recompute."""
    return _DISK_CACHE / f"l1custom_{instrument}_{tf}_{_L1_CACHE_VER}_{h}.pkl"


_CAUSAL_MEMO: dict = {}            # F3 — share ONE causal pass across the fan-out's per-view calls
_CAUSAL_MEMO_MAX = 8

# task #210 — memoise the RICH L1 build_payload (strategy.build_payload). It recomputes every indicator
# on the 1-minute frame (~8s) and is otherwise rerun on every L1-view request even when params are
# unchanged. It's a deterministic pure function of (tf, l1_engine params) and its result is read-only
# (serialised to JSON), so caching by that key is byte-identical. Bounded LRU-ish like _CAUSAL_MEMO.
_L1_PAYLOAD_MEMO: dict = {}
_L1_PAYLOAD_MEMO_MAX = 8


def _build_l1_payload_memo(l1_engine: dict, tf: str, instrument: str = "NQ"):
    """Memoise strategy.build_payload for the unified L1 view by (instrument, tf, l1_engine-params-hash)."""
    import strategy                                        # the L1 engine (full feature set)
    key = (instrument, tf,
           hashlib.sha256(json.dumps(l1_engine, sort_keys=True, default=str).encode()).hexdigest()[:16])
    r = _L1_PAYLOAD_MEMO.get(key)
    if r is None:
        if len(_L1_PAYLOAD_MEMO) >= _L1_PAYLOAD_MEMO_MAX:
            _L1_PAYLOAD_MEMO.pop(next(iter(_L1_PAYLOAD_MEMO)))
        _tf = l1_engine.get("timeframe") or tf
        r = _L1_PAYLOAD_MEMO[key] = strategy.build_payload(
            *strategy.get_bundle(_tf, instrument), l1_engine, instrument=instrument)
    return r


def _run_causal_memo(l1p: dict, l2p: dict, tf: str, instrument: str = "NQ"):
    """Memoise logbook.run_causal by (instrument, l1p, l2p, tf) so the unified page's three per-view requests
    (l2 + combined send identical params) reuse ONE pass instead of recomputing it. The CausalResult is
    read-only downstream (aggregate/charts only read it), so sharing is safe. Bounded LRU-ish."""
    from optimize.l2 import logbook                       # lazy: logbook imports payload (circular)
    key = (instrument, tf,
           hashlib.sha256(json.dumps([l1p, l2p], sort_keys=True, default=str).encode()).hexdigest()[:16])
    r = _CAUSAL_MEMO.get(key)
    if r is None:
        if len(_CAUSAL_MEMO) >= _CAUSAL_MEMO_MAX:
            _CAUSAL_MEMO.pop(next(iter(_CAUSAL_MEMO)))
        r = _CAUSAL_MEMO[key] = logbook.run_causal(l1p, l2p, tf, instrument)
    return r

# Deterministic anchor profile (no indicators / no vol gate => take every flat dropped signal).
PERMISSIVE: dict = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
                    "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


class L2ParamError(ValueError):
    """Invalid L2 profile parameter — surfaced to the UI as HTTP 400 (never silently clamped)."""


def run_l1_cached(tf: str = "4h", use_disk: bool = True, params: dict | None = None, instrument: str = "NQ"):
    """L1 run. params=None → the FROZEN lean champion: memoised in-process AND on disk (deterministic),
    so repeat processes load in ~1s instead of recomputing the ~38s 1-min indicator pass. params=<dict>
    → an ARBITRARY L1 profile (combined dashboard): run fresh, memoised in-process by (instrument, tf,
    params-hash). All caches key on instrument so NQ and ES never share an entry. Set use_disk=False to
    force a fresh recompute."""
    if params is not None:
        h = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]
        key = (instrument, tf, h)
        if key in _L1_CUSTOM_CACHE:
            return _L1_CUSTOM_CACHE[key]
        cf = _l1_custom_cache_file(tf, h, instrument)
        if use_disk and cf.exists():
            try:
                with open(cf, "rb") as f:
                    r = pickle.load(f)
                if getattr(r, "vf_seed", None) is None:   # F2: stale schema → recompute (mirror frozen path)
                    raise ValueError("stale L1 cache schema")
                _L1_CUSTOM_CACHE[key] = r
                return r
            except Exception:
                pass                                      # corrupt/stale pickle → recompute
        r = l1_runner.run_l1(tf, params=validate_layer_params(params), instrument=instrument)
        _L1_CUSTOM_CACHE[key] = r
        if use_disk:
            try:                                          # atomic write: 24 workers may race on first launch
                _DISK_CACHE.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=str(_DISK_CACHE), suffix=".tmp", delete=False) as tf_:
                    pickle.dump(r, tf_)
                    tmp = Path(tf_.name)
                tmp.replace(cf)                           # os.replace under the hood → atomic on same fs
            except Exception:
                pass                                      # cache write best-effort; never fail the run
        return r
    fkey = (instrument, tf)
    if fkey in _L1_CACHE:
        return _L1_CACHE[fkey]
    cf = _l1_cache_file(tf, instrument)
    if use_disk and cf.exists():
        try:
            with open(cf, "rb") as f:
                r = pickle.load(f)
            if getattr(r, "vf_seed", None) is None:       # F2 belt-and-suspenders: stale schema → recompute
                raise ValueError("stale L1 cache schema")
            _L1_CACHE[fkey] = r
            return r
        except Exception:
            pass                                      # corrupt/stale pickle → recompute
    r = l1_runner.run_l1(tf, instrument=instrument)
    _L1_CACHE[fkey] = r
    if use_disk:
        try:
            _DISK_CACHE.mkdir(parents=True, exist_ok=True)
            with open(cf, "wb") as f:
                pickle.dump(r, f)
        except Exception:
            pass                                      # cache write best-effort; never fail the run
    return r


_WINDOWS = ("full", "2024", "2025", "2026", "full+20d", "2026+20d")


def _validate_window(w):
    """Window selection (default 'full'). Strict — no silent fallback (mirrors strategy.validate_params)."""
    w = w or "full"
    if w not in _WINDOWS:
        raise L2ParamError(f"window must be one of {'|'.join(_WINDOWS)} (got {w!r})")
    return w


def validate_layer_params(p: dict) -> dict:
    """Validate one layer's levers (L1 or L2 — identical schema); return a clean engine-ready dict.
    window defaults to 'full' (the frozen default round-trips so run_causal/build_view_payload still hit
    the cached oracle). Raise on any bad/missing value (no silent fallback)."""
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
        window=_validate_window(p.get("window", "full")),
        cap_1min=int(num("cap_1min", 0)) if p.get("cap_1min") not in (None, "") else 0,
        cap_mode=(str(p.get("cap_mode") or "none")),
        eod_margin_min=int(num("eod_margin_min", 15)) if p.get("eod_margin_min") not in (None, "") else 15,
    )
    # optional split long/short SL/TP overrides — each None => fall back to the shared sl_soft/sl_hard/tp
    # (so the default carries all-None and is byte-identical + the use_frozen round-trip still holds).
    for side in ("long", "short"):
        for base in ("sl_soft", "sl_hard", "tp"):
            v = p.get(f"{side}_{base}")
            if v in (None, ""):
                out[f"{side}_{base}"] = None
            else:
                fv = float(v)
                if fv <= 0:
                    raise L2ParamError(f"{side}_{base} must be > 0")
                out[f"{side}_{base}"] = fv
        ss, sh = out[f"{side}_sl_soft"], out[f"{side}_sl_hard"]
        if ss is not None and sh is not None and sh < ss:
            raise L2ParamError(f"{side}_sl_hard ({sh}) must be >= {side}_sl_soft ({ss})")
    # back-compat: a bare cap_1min>0 with no explicit mode is the bars cap.
    if out["cap_mode"] == "none" and out["cap_1min"] > 0:
        out["cap_mode"] = "bars"
    inds = p.get("indicators", [])
    if not isinstance(inds, list):
        raise L2ParamError("indicators must be a list")
    try:
        library.from_specs([s for s in inds if s.get("enabled")])   # validates indicator params
    except Exception as e:
        raise L2ParamError(f"bad indicator config: {e}")
    out["indicators"] = inds
    _validate_contributors(p, out)
    return out


_TOPOLOGIES = ("separate_and", "merged", "or_boost")
_STATE_DEFS = ("touch", "traversal")
_SIG_ENCODINGS = ("none", "stance", "truthtable")
_SIG_MODES = ("confirm", "veto", "both")
_TT_CELLS = ("confirm", "veto", "ignore")


def _validate_contributors(p: dict, out: dict) -> None:
    """Keep + validate the optional cross-instrument contributor block (Spec §6). ABSENT/empty ⇒ leave
    `out` untouched ⇒ byte-identical contributor-free L2 (golden 6/6 preserved). Mirrors the optimizer's
    _suggest_contributor shape so a hand-built dashboard cfg and a searched trial validate identically."""
    raw = p.get("contributors")
    if not raw:
        return
    if not isinstance(raw, list):
        raise L2ParamError("contributors must be a list")
    topo = str(p.get("contributor_topology", "separate_and"))
    if topo not in _TOPOLOGIES:
        raise L2ParamError(f"contributor_topology must be one of {'|'.join(_TOPOLOGIES)} (got {topo!r})")
    clean = []
    for c in raw:
        if not isinstance(c, dict):
            raise L2ParamError("each contributor must be an object")
        token = str(c.get("token") or "").strip()
        if not token:
            raise L2ParamError("contributor missing token")
        state_def = str(c.get("state_def", "touch"))
        if state_def not in _STATE_DEFS:
            raise L2ParamError(f"contributor state_def must be one of {'|'.join(_STATE_DEFS)} "
                               f"(got {state_def!r})")
        try:
            k_es = int(c.get("k_es", 1))
        except (TypeError, ValueError):
            raise L2ParamError("contributor k_es must be an integer")
        if k_es < 1:
            raise L2ParamError("contributor k_es must be >= 1")
        sig = dict(c.get("signal") or {})
        enc = str(sig.get("encoding", "none"))
        if enc not in _SIG_ENCODINGS:
            raise L2ParamError(f"contributor signal.encoding must be one of {'|'.join(_SIG_ENCODINGS)} "
                               f"(got {enc!r})")
        if enc == "stance":
            mode = str(sig.get("mode", ""))
            if mode not in _SIG_MODES:
                raise L2ParamError(f"contributor signal.mode must be one of {'|'.join(_SIG_MODES)} "
                                   f"(got {mode!r})")
        if enc == "truthtable":
            table = sig.get("table") or {}
            if not isinstance(table, dict):
                raise L2ParamError("contributor signal.table must be an object")
            for v in table.values():
                if v not in _TT_CELLS:
                    raise L2ParamError(f"truth-table cell must be one of {'|'.join(_TT_CELLS)} (got {v!r})")
        com = c.get("committee", [])
        if not isinstance(com, list):
            raise L2ParamError("contributor committee must be a list")
        try:
            library.from_specs([s for s in com if s.get("enabled")])   # validates ES committee params
        except Exception as e:
            raise L2ParamError(f"bad contributor committee config: {e}")
        clean.append({"token": token, "enabled": bool(c.get("enabled", False)),
                      "tf": str(c.get("tf", "4h")), "state_def": state_def, "k_es": k_es,
                      "signal": {"encoding": enc, "mode": sig.get("mode"),
                                 "table": sig.get("table") or {}},
                      "committee": com})
    out["contributor_topology"] = topo
    out["contributors"] = clean


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


_TF_SET = ("4h", "2h", "1h", "15m", "5m", "2m")          # the decision TFs (1m excluded — not in the champion sweep)
_WSH4_CHAMPS = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full.json"


def _champion_layer_params(tf: str, entry: dict) -> dict:
    """Engine-ready L1 layer params from a {box, indicators} champion entry. L1 champions run on the
    1-minute frame, so ind_1min is forced True (mirrors optimize.optimize._l1_params_from_champion)."""
    import presets                                          # noqa: E402 (top-level module on sys.path)
    lp = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    lp["ind_1min"] = True
    return validate_layer_params(lp)


def l1_default_params(tf: str = "4h") -> dict:
    """The 'best L1' preset for a TF, in the layer-param schema the forms speak. 4h = the frozen lean
    champion (unchanged); other TFs = that TF's deployed champion from wsh4_champions_full.json."""
    if tf == "4h":
        return validate_layer_params(l1_runner._lean_params(tf))
    champs = json.loads(_WSH4_CHAMPS.read_text())
    if tf not in champs:
        raise L2ParamError(f"no L1 champion for tf={tf!r} (known: {sorted(champs)})")
    return _champion_layer_params(tf, champs[tf])


def l2_default_params() -> dict:
    """The 'best L2' preset = the most recently saved L2 profile (the promoted extend champion), else PERMISSIVE."""
    profs = load_l2_profiles()
    if profs:
        return list(profs.values())[-1]
    return dict(PERMISSIVE)


def _scaled_permissive(instrument: str) -> dict:
    """The PERMISSIVE anchor with point-denominated fields scaled to the instrument's price (scale-free
    fields untouched). Gives non-NQ a runnable, sane default; the user tunes from there."""
    from optimize import instruments
    sf = instruments.scale_factor(instrument)
    p = dict(PERMISSIVE)
    for f in ("sl_soft", "sl_hard", "tp", "dd_limit"):
        if p.get(f) is not None:
            p[f] = round(float(p[f]) * sf, 4)
    return validate_layer_params(p)


def _instrument_champions_path(instrument: str) -> Path:
    """Per-instrument optimized-champions file (same naming the optimizer writes). NQ uses _WSH4_CHAMPS."""
    suf = "" if instrument == "NQ" else f"_{instrument}"
    return _WSH4_CHAMPS.with_name(f"wsh4_champions_full{suf}.json")


def instrument_l1_default(instrument: str = "NQ", tf: str = "4h") -> dict:
    """L1 default for an instrument. NQ → the real per-TF champion (unchanged). Non-NQ → that instrument's
    OPTIMIZED champion (results/wsh4_champions_full_<INST>.json) when present for the TF, else the
    price-scaled permissive default."""
    if instrument == "NQ":
        return l1_default_params(tf)
    cf = _instrument_champions_path(instrument)
    if cf.exists():
        try:
            champs = json.loads(cf.read_text())
            if tf in champs:
                return _champion_layer_params(tf, champs[tf])
        except Exception:
            pass                                          # malformed/partial → fall back
    return _scaled_permissive(instrument)


def instrument_l2_default(instrument: str = "NQ") -> dict:
    """L2 default. NQ → the promoted L2 champion / permissive; non-NQ → scaled-permissive (no L2 champion)."""
    if instrument == "NQ":
        return l2_default_params()
    return _scaled_permissive(instrument)


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
    """SL/TP line levels for display only (entry_price ± points; engine fill convention). Split-aware:
    a trade's FINAL direction uses its per-side long_*/short_* override when set (else the shared
    value) — so the drawn lines match what fast_backtest actually used for the exit (F4)."""
    ep = float(t["entry_price"]); side = t["direction"]

    def pick(base):                                          # per-side override ⇒ shared fallback
        v = p.get(f"{side}_{base}")
        return float(v) if v not in (None, "") else float(p[base])

    sl_hard, sl_soft, tp = pick("sl_hard"), pick("sl_soft"), pick("tp")
    if side == "long":
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


def _layer_from_strategy(sp: dict) -> dict:
    """Map index.html's full strategy params → the L1 layer schema run_causal uses (single SL/TP core;
    1-min indicators). The engine charts/boxes for the unified L1 view come from strategy.build_payload;
    this layer projection drives the per-candle causal log."""
    return validate_layer_params({
        "sl_soft": sp.get("sl_soft"), "sl_hard": sp.get("sl_hard"), "tp": sp.get("tp"),
        "gate_pct": sp.get("gate_pct", 0) or 0, "dd_limit": sp.get("dd_limit", 0) or 0,
        "cooldown": sp.get("cooldown", 0) or 0, "flip": bool(sp.get("flip", False)),
        "cap_1min": sp.get("cap_1min", 0) or 0,
        "cap_mode": sp.get("cap_mode", "none") or "none",
        "eod_margin_min": sp.get("eod_margin_min", 15) or 15,
        "indicators": sp.get("indicators", []), "k": sp.get("k", 1),
        # honor the settings-panel "Indicators on 1-min" dropdown (default True = 1-min frame); was hardcoded True
        "ind_1min": bool(sp.get("ind_1min", True))})


def _serialize_log_row(r) -> dict:
    """Compact per-candle log row for the dashboard table + the full payload (one per candle)."""
    return {"i": r.i, "time": r.time, "layer": r.layer, "decision": r.decision, "reason": r.reason,
            "box_cause": r.box_cause, "event_type": r.event_type, "direction": r.direction,
            "box_dir": r.box_dir, "entry_price": r.entry_price, "exit_time": r.exit_time,
            "exit_price": r.exit_price, "exit_reason": r.exit_reason,
            "pnl": round(r.pnl, 2), "equity": r.equity, "dd": r.dd, "in_position": r.in_position,
            "position_owner": r.position_owner, "l2_reason": r.l2_reason,
            "text": r.text, "veto_flip": r.veto_flip, "would_be_pnl": r.would_be_pnl,
            "indicators": r.indicators}


def build_view_payload(l1_params: dict, l2_params: dict, tf: str = "4h", view: str = "combined",
                       instrument: str = "NQ", l1_engine: dict | None = None) -> dict:
    """Causal log-first payload for one VIEW (l1 | l2 | combined). Boxes are derived from the per-candle
    log (aggregate.*); charts/log/CSV all project the SAME log. Separated views carry only their layer's
    trades; the combined view carries both (the frontend grays the opposite layer).

    UNIFIED L1 view: when `l1_engine` (the full strategy-param dict) is given with view='l1', the payload
    is the engine's complete L1 dashboard payload (strategy.build_payload — vol/state/drawdown/events/
    split-SL-TP/window, nothing lost) PLUS the causal per-candle log + the log-derived L1 boxes. So
    index.html runs entirely off /api/causal_backtest with no feature loss, boxes consistent with the log."""
    from optimize.l2 import logbook, aggregate, charts, taxonomy  # inline: logbook imports payload (avoid circular)
    from optimize import timeframes as TF
    from optimize import signals as _signals
    if view not in ("l1", "l2", "combined"):
        raise L2ParamError(f"view must be l1|l2|combined (got {view!r})")

    if view == "l1" and l1_engine:
        import strategy                                  # the L1 engine (full feature set)
        l1p = validate_layer_params(l1_params)
        res = _run_causal_memo(l1p, dict(PERMISSIVE), tf, instrument)  # causal log for the L1 layer (memoised)
        bar_secs = int(TF.get(tf).bar_td.total_seconds())
        cached = _build_l1_payload_memo(l1_engine, tf, instrument)   # rich engine payload (memoised — the ~8s pass)
        base = dict(cached); base["meta"] = dict(cached["meta"])     # shallow copy: per-request fields below must
        base["log"] = [_serialize_log_row(r) for r in res.log]       #   not mutate the cached object
        base["meta"]["boxes"] = aggregate.boxes_for_layer(res, "L1", bar_secs)   # log-derived (== engine summary)
        base["meta"]["taxonomy"] = taxonomy.taxonomy_l1(res)
        _l1u = (run_l1_cached(tf, instrument=instrument)
                if (instrument == "NQ" and tf == "4h" and l1p == l1_default_params(tf))
                else run_l1_cached(tf, params=l1p, instrument=instrument))
        base["meta"]["box_counts"] = _signals.box_fire_stats(_l1u.df_dec, _l1u.box)
        base["meta"]["n"] = res.n
        base["meta"]["view"] = "l1"
        return base
    l1p = validate_layer_params(l1_params)
    l2p = validate_layer_params(l2_params)
    res = _run_causal_memo(l1p, l2p, tf, instrument)
    # The frozen-lean disk-cached run only exists for NQ-4h; for other TFs/instruments the default L1 is a
    # params dict, so we must always pass params there (run_l1_cached() with no params runs the NQ-4h lean).
    l1 = (run_l1_cached(tf, instrument=instrument)
          if (instrument == "NQ" and tf == "4h" and l1p == l1_default_params(tf))
          else run_l1_cached(tf, params=l1p, instrument=instrument))
    ds = dataset.build_dataset(l1)
    bar_secs = int(TF.get(tf).bar_td.total_seconds())
    dec_dates = l1.df_dec["Date"].to_numpy()

    boxes = (aggregate.combined_boxes(res, bar_secs) if view == "combined"
             else aggregate.boxes_for_layer(res, view.upper(), bar_secs))
    # per-layer engine charts (vol/gate_thr/state/equity/drawdown/events) from the SAME causal run, so the
    # L2 + Combined tabs get engine charts they never had — charts and boxes can't disagree (one pass).
    engine_charts = charts.charts_for_layer(res, l1, "combined" if view == "combined" else view.upper())

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
               for d, o, h, lo, c in zip(l1.df_dec["Date"], l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]

    def _trade_row(r):
        p = l1p if r.layer == "L1" else l2p
        row = {"layer": r.layer, "entry_time": r.time, "exit_time": r.exit_time, "direction": r.direction,
               "entry_price": float(r.entry_price), "exit_price": float(r.exit_price),
               "exit_reason": r.exit_reason, "pnl": round(r.pnl, 2)}
        row.update(_derive_lines({"entry_price": r.entry_price, "direction": r.direction}, p))
        return row

    entry_rows = [r for r in res.log if r.decision == "entry"]
    all_trades = [_trade_row(r) for r in entry_rows]
    if view == "l1":
        trades = [t for t in all_trades if t["layer"] == "L1"]
    elif view == "l2":
        trades = [t for t in all_trades if t["layer"] == "L2"]
    else:
        trades = sorted(all_trades, key=lambda t: t["exit_time"])

    def _eq(layer):
        rows = sorted([r for r in res.log if r.layer == layer and r.decision == "entry"], key=lambda r: r.exit_time)
        return _dedupe([{"time": r.exit_time, "value": r.equity} for r in rows])
    merged = sorted(entry_rows, key=lambda r: r.exit_time)
    comb_eq, eq = [], 0.0
    for r in merged:
        eq += r.pnl
        comb_eq.append({"time": r.exit_time, "value": round(eq, 2)})

    return {
        "meta": {"view": view, "n": res.n, "boxes": boxes,
                 "taxonomy": (taxonomy.taxonomy_combined(res) if view == "combined"
                              else taxonomy.taxonomy_l2(res) if view == "l2"
                              else taxonomy.taxonomy_l1(res)),
                 "box_counts": _signals.box_fire_stats(l1.df_dec, l1.box),
                 "dropped_counts": {"veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                                    "total": len(ds), "flat_candidates": len(ds.flat_candidates())}},
        "candles": candles,
        "l1_spans": _spans_from_timeline(l1.state_timeline, dec_dates),
        "dropped": [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"],
                     "l1_flat": (not bool(l1.state_timeline[d["idx"]]))} for d in l1.dropped_signals],
        "trades": trades,
        "l1_equity": _eq("L1"),
        "l2_equity": _eq("L2"),
        "combined_equity": _dedupe(comb_eq),
        "engine": engine_charts,
        "log": [_serialize_log_row(r) for r in res.log],
    }

