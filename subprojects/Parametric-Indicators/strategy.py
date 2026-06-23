"""Self-contained strategy service for the WS-G drawdown-capped strategy.

Loads the market data, computes the HAR-RV volatility forecast, runs the (copied, parity-tested)
single-contract engine with the chosen parameters, applies the causal drawdown circuit-breaker,
and returns a full dashboard payload. NO imports from the wider repo — only the local modules
(engine, box_lookup, loader, volatility) + config.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from loader import load_data
from engine import SimpleStrategy, SimpleStrategyParams
from volatility import vol_forecast, gate_threshold
from optimize import timeframes as TF
from optimize.signals import decision_signals

PV = config.NQ_POINT_VALUE


def _ts(dt): return int(pd.Timestamp(dt).timestamp())


def load_inputs():
    """Load 4h/1m/box for all configured years + the HAR-RV forecast. Returns (df4,df1,box,vf,n2025)."""
    f4, f1, fb = [], [], []
    for yr in config.YEARS:
        d = config.DATA_ROOT / f"{yr}_data"
        a = load_data(str(d / f"NQ_4h_{yr}.csv")); a["_year"] = yr
        b = load_data(str(d / f"NQ_1m_{yr}.csv"))
        c = pd.read_csv(d / f"NQ_full_data_{yr}.csv"); c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
        f4.append(a); f1.append(b); fb.append(c)
    df4 = pd.concat(f4).sort_values("Date").reset_index(drop=True)
    df1 = pd.concat(f1).sort_values("Date").reset_index(drop=True)
    box = pd.concat(fb).drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    n2025 = int((df4["_year"] == config.YEARS[0]).sum())
    vf = vol_forecast(df4, df1)
    return df4, df1, box, vf, n2025


def load_year_bundle(yr: int):
    """Load a SINGLE calendar year as a self-contained (df4, df1, box, vf, n) bundle. Used for the
    isolated 2024 window so it never touches the 2025+2026 bundle (keeps those results byte-identical
    + parity-locked). n = len(df4) (no second segment; the whole bundle is one window)."""
    d = config.DATA_ROOT / f"{yr}_data"
    a = load_data(str(d / f"NQ_4h_{yr}.csv")); a["_year"] = yr
    b = load_data(str(d / f"NQ_1m_{yr}.csv"))
    c = pd.read_csv(d / f"NQ_full_data_{yr}.csv"); c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    df4 = a.sort_values("Date").reset_index(drop=True)
    df1 = b.sort_values("Date").reset_index(drop=True)
    box = c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    vf = vol_forecast(df4, df1)
    return df4, df1, box, vf, len(df4)


def load_inputs_plus20d():
    """4h bundle for the +last-20-days windows: 2025 (standard, unchanged) + 2026-with-20d.
    Mirrors load_inputs() but swaps the 2026 files for the combined ones (build_plus20d_data.py).
    n2025 still counts only the 2025 decision bars, so 'full+20d'/'2026+20d' slice exactly like
    'full'/'2026' — just with the extra June-2026 tail. The 2025 prefix is byte-identical, and
    vol_forecast is causal, so every existing window stays unaffected."""
    f4, f1, fb = [], [], []
    spec = [(2025, "NQ_4h_2025.csv", "NQ_1m_2025.csv", "NQ_full_data_2025.csv"),
            (2026, "NQ_4h_2026_with20d.csv", "NQ_1m_2026_with20d.csv", "NQ_full_data_2026_with20d.csv")]
    for yr, f4n, f1n, fbn in spec:
        d = config.DATA_ROOT / f"{yr}_data"
        a = load_data(str(d / f4n)); a["_year"] = yr
        b = load_data(str(d / f1n))
        c = pd.read_csv(d / fbn); c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
        f4.append(a); f1.append(b); fb.append(c)
    df4 = pd.concat(f4).sort_values("Date").reset_index(drop=True)
    df1 = pd.concat(f1).sort_values("Date").reset_index(drop=True)
    box = pd.concat(fb).drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    n2025 = int((df4["_year"] == config.YEARS[0]).sum())
    vf = vol_forecast(df4, df1)
    return df4, df1, box, vf, n2025


def load_inputs_plus20d_tf(tf_name: str):
    """Non-4h +20d bundle: mirrors optimize.data.load_inputs but reads the NQ_<tf>_with20d.csv
    all-history files + the combined shared box (build_plus20d_data.py)."""
    import os
    from pathlib import Path
    base = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
    raw = base / TF.RAW_DIR
    tf = TF.get(tf_name)
    df_dec = load_data(str(raw / f"NQ_{tf.name}_with20d.csv")).sort_values("Date").reset_index(drop=True)
    df1 = load_data(str(raw / "NQ_1m_with20d.csv")).sort_values("Date").reset_index(drop=True)
    c = pd.read_csv(config.DATA_ROOT / "full_data" / "NQ_full_data_with20d.csv")
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    box = c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    vf = vol_forecast(df_dec, df1, bar_minutes=tf.minutes)
    n_split = int((df_dec["Date"].dt.year == config.YEARS[0]).sum())
    return df_dec, df1, box, vf, n_split


_BUNDLE_CACHE_20D: dict = {}


def get_bundle_plus20d(tf_name: str | None):
    """Cached (df_dec, df1, box, vf, n_split) bundle for a TF, INCLUDING the last-20-days tail.
    4h uses the per-year backend; every other TF uses the all-history backend (same split as
    get_bundle). Unknown TF → ParamError (no silent fallback)."""
    tf_name = tf_name or "4h"
    if tf_name not in TF.TIMEFRAMES:
        raise ParamError(f"timeframe must be one of {list(TF.TIMEFRAMES)} (got {tf_name!r})")
    if tf_name not in _BUNDLE_CACHE_20D:
        _BUNDLE_CACHE_20D[tf_name] = (load_inputs_plus20d() if tf_name == "4h"
                                      else load_inputs_plus20d_tf(tf_name))
    return _BUNDLE_CACHE_20D[tf_name]


# Per-decision-timeframe bundle cache. 4h reuses the parity-locked per-year split files above;
# every other timeframe is loaded from the all-history per-TF source via the optimizer's loader
# (optimize/data.py), which produces the identical (df_dec, df1, box, vf, n_split) shape. Each TF
# is loaded at most once, on first request, then cached for the life of the process.
_BUNDLE_CACHE: dict = {}


def get_bundle(tf_name: str | None):
    """Return the cached (df_dec, df1, box, vf, n_split) bundle for a decision timeframe.
    Raises ParamError for an unknown timeframe (no silent fallback)."""
    tf_name = tf_name or "4h"
    if tf_name not in TF.TIMEFRAMES:
        raise ParamError(f"timeframe must be one of {list(TF.TIMEFRAMES)} (got {tf_name!r})")
    if tf_name not in _BUNDLE_CACHE:
        if tf_name == "4h":
            _BUNDLE_CACHE[tf_name] = load_inputs()
        else:
            from optimize.data import load_inputs as _load_tf
            _BUNDLE_CACHE[tf_name] = _load_tf(tf_name)
    return _BUNDLE_CACHE[tf_name]


class ParamError(ValueError):
    """Invalid/missing strategy parameter. Surfaced to the UI; values are NEVER silently
    clamped or defaulted — a bad input is an error the user must see."""


def validate_params(params):
    """Strict validation. Raises ParamError (no silent fallback). Returns a typed dict.
    Required strategy params must all be present; instrument constants (dd_cap, pv) are
    exposed too and default to config only when omitted."""
    if not params:
        raise ParamError("no parameters supplied — the UI must send all strategy parameters")
    required = ("sl_soft", "sl_hard", "tp", "gate_pct", "dd_limit", "cooldown", "flip", "window")
    missing = [k for k in required if k not in params or params[k] is None or params[k] == ""]
    if missing:
        raise ParamError("missing parameter(s): " + ", ".join(missing))

    def _num(k):
        try:
            return float(params[k])
        except (TypeError, ValueError):
            raise ParamError(f"'{k}' must be a number, got {params[k]!r}")

    sl_soft, sl_hard, tp = _num("sl_soft"), _num("sl_hard"), _num("tp")
    gate_pct, dd_limit, cooldown = _num("gate_pct"), _num("dd_limit"), _num("cooldown")
    if sl_soft <= 0:              raise ParamError(f"sl_soft must be > 0 (got {sl_soft})")
    if tp <= 0:                   raise ParamError(f"tp must be > 0 (got {tp})")
    if sl_hard < sl_soft:         raise ParamError(f"sl_hard ({sl_hard}) must be ≥ sl_soft ({sl_soft})")
    if not 0 <= gate_pct <= 100:  raise ParamError(f"gate_pct must be in [0,100] (got {gate_pct}); 0 = gate OFF")
    if dd_limit < 0:              raise ParamError(f"dd_limit must be ≥ 0 (got {dd_limit}); 0 = breaker OFF")
    if cooldown < 0 or cooldown != int(cooldown):
        raise ParamError(f"cooldown must be a non-negative integer (got {params['cooldown']!r})")
    if params["window"] not in ("full", "2024", "2025", "2026", "full+20d", "2026+20d"):
        raise ParamError("window must be one of full|2024|2025|2026|full+20d|2026+20d "
                         f"(got {params['window']!r})")
    # decision timeframe (optional; defaults to 4h so existing callers are unchanged).
    timeframe = params.get("timeframe") or "4h"
    if timeframe not in TF.TIMEFRAMES:
        raise ParamError(f"timeframe must be one of {list(TF.TIMEFRAMES)} (got {timeframe!r})")
    dd_cap = float(params["dd_cap"]) if params.get("dd_cap") not in (None, "") else config.DD_CAP
    pv = float(params["pv"]) if params.get("pv") not in (None, "") else config.NQ_POINT_VALUE
    if dd_cap <= 0:               raise ParamError(f"dd_cap must be > 0 (got {dd_cap})")
    if pv <= 0:                   raise ParamError(f"pv (point value) must be > 0 (got {pv})")
    # WS-I indicator confirmation layer (optional; absent ⇒ pure box strategy = parity).
    specs = params.get("indicators") or []
    if not isinstance(specs, (list, tuple)):
        raise ParamError("'indicators' must be a list of indicator specs")
    try:
        k = int(params["k"]) if params.get("k") not in (None, "") else 1
    except (TypeError, ValueError):
        raise ParamError(f"'k' must be an integer (got {params.get('k')!r})")
    if k < 1:                     raise ParamError(f"k must be ≥ 1 (got {k})")
    gen = params.get("gen") or {}
    if not isinstance(gen, dict):
        raise ParamError("'gen' must be an object of generation params")
    # WS-I GLOBAL entry timing (one value each, applied to ALL indicators — notes #3/#4).
    try:
        retrace_amount = float(params.get("retrace_amount") or 0.0)
    except (TypeError, ValueError):
        raise ParamError(f"'retrace_amount' must be a number (got {params.get('retrace_amount')!r})")
    if retrace_amount < 0:
        raise ParamError(f"retrace_amount must be ≥ 0 (got {retrace_amount})")
    retrace_unit = params.get("retrace_unit") or "atr_mult"
    if retrace_unit not in ("atr_mult", "points"):
        raise ParamError(f"retrace_unit must be one of ('atr_mult','points') (got {retrace_unit!r})")
    try:
        wait_bars = int(params.get("wait_bars") or 0)
    except (TypeError, ValueError):
        raise ParamError(f"'wait_bars' must be an integer (got {params.get('wait_bars')!r})")
    if wait_bars < 0:
        raise ParamError(f"wait_bars must be ≥ 0 (got {wait_bars}); counts 1-minute bars")
    # NOTE: the dynamic SL/TP "sizing mode" (ATR multiplier) was REMOVED on 2026-06-15 — the derived/dynamic
    # SL/TP avenue was studied and closed (see STUDY_relative_feasibility.md / STUDY_fixed_window_sltp_mapping.md
    # / COUNCIL_RULING_atr_sizing.md). SL/TP are always FIXED point values now. The engine retains a neutral
    # `sl_tp_mult` hook (default None) ONLY for the archived research script optimize/sub/stage2.py; the
    # dashboard/backtester never sets it. See REMOVAL_sltp_sizing_mode.md.
    # Optional SPLIT long/short SL/TP (Q3 / E2): a side's 3 values, each None ⇒ falls back to the shared
    # sl_soft/sl_hard/tp ⇒ byte-identical (golden presets never set them). hard ≥ soft validated per side.
    split = {}
    for side in ("long", "short"):
        ss = params.get(f"{side}_sl_soft"); sh = params.get(f"{side}_sl_hard"); st = params.get(f"{side}_tp")
        for nm, v in ((f"{side}_sl_soft", ss), (f"{side}_sl_hard", sh), (f"{side}_tp", st)):
            if v is not None and (not isinstance(v, (int, float)) or v <= 0):
                raise ParamError(f"'{nm}' must be a number > 0 when set (got {v!r})")
        if ss is not None and sh is not None and float(sh) < float(ss):
            raise ParamError(f"{side}_sl_hard ({sh}) must be ≥ {side}_sl_soft ({ss})")
        split[f"{side}_sl_soft"] = None if ss is None else float(ss)
        split[f"{side}_sl_hard"] = None if sh is None else float(sh)
        split[f"{side}_tp"] = None if st is None else float(st)
    return dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp, gate_pct=gate_pct, dd_limit=dd_limit,
                cooldown=int(cooldown), flip=bool(params["flip"]), window=params["window"],
                timeframe=timeframe, dd_cap=dd_cap, pv=pv, indicators=list(specs), k=k, gen=gen,
                retrace_amount=retrace_amount, retrace_unit=retrace_unit, wait_bars=wait_bars,
                veto_as_flip=bool(params.get("veto_as_flip")), **split)


_WINDOW_LOHI = {"full": lambda N, n: (0, N), "2024": lambda N, n: (0, N),
                "2025": lambda N, n: (0, n), "2026": lambda N, n: (n, N),
                "full+20d": lambda N, n: (0, N), "2026+20d": lambda N, n: (n, N)}


def window_slice(df4, df1, box, vf, n2025, window, timeframe):
    """Resolve a window selection to its windowed dataset + the pre-window gate references.

    Bundle-swaps for the ISOLATED windows (2024 -> load_year_bundle, +20d -> get_bundle_plus20d) then
    physically slices [lo:hi]. Returns:
      (d4, d1, vfw)  — the WINDOWED decision frame, 1-min frame and vol-forecast (what the engine runs on)
      (df4, vf, n2025, box) — the POST-swap FULL references (the gate must seed on vf[:n2025]; split_ts
                              uses df4/n2025 — these are NEVER the sliced versions)
      (lo, hi)       — the slice bounds.
    Shared by strategy.build_payload AND optimize.l2.l1_runner.run_l1 so windowed L1 numbers match
    byte-for-byte across both engines (4h data sources are verified identical). The gate is seeded on
    the unsliced vf[:n2025] here-or-by-caller, never on the windowed vfw."""
    bar_td = TF.get(timeframe).bar_td
    if window == "2024":
        df4, df1, box, vf, n2025 = load_year_bundle(2024)
    elif window in ("full+20d", "2026+20d"):
        df4, df1, box, vf, n2025 = get_bundle_plus20d(timeframe)
    N = len(df4)
    lo, hi = _WINDOW_LOHI[window](N, n2025)
    d4 = df4.iloc[lo:hi].reset_index(drop=True)
    t0, t1 = d4["Date"].iloc[0], d4["Date"].iloc[-1] + bar_td
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    vfw = vf[lo:hi]
    return d4, d1, vfw, df4, vf, n2025, box, lo, hi


def build_payload(df4, df1, box, vf, n2025, params=None):
    P = validate_params(params)
    sl_soft, sl_hard, tp = P["sl_soft"], P["sl_hard"], P["tp"]
    cooldown, flip = P["cooldown"], P["flip"]
    gate_pct, dd_limit, window = P["gate_pct"], P["dd_limit"], P["window"]
    dd_cap, pv = P["dd_cap"], P["pv"]

    # decision-bar duration generalises the old hardcoded "+4h" 1-minute slice bound to any TF.
    bar_td = TF.get(P["timeframe"]).bar_td

    # window selection (bundle-swap for the isolated 2024/+20d windows + physical slice) — shared with
    # l1_runner.run_l1 so windowed L1 numbers match byte-for-byte across both engines. df4/vf/n2025/box
    # are rebound to the POST-swap FULL frames (split_ts + the gate seed use them, never the sliced d4).
    d4, d1, vfw, df4, vf, n2025, box, lo, hi = window_slice(df4, df1, box, vf, n2025, window, P["timeframe"])

    gthr = gate = None
    if gate_pct > 0:
        gthr = gate_threshold(vf, n2025, gate_pct)
        gate = vfw <= gthr

    # WS-I indicator confirmation layer (off by default ⇒ identical to the pure box strategy).
    specs, k_rule, gen_params = P["indicators"], P["k"], P["gen"]
    g_retr, g_runit, g_wait = P["retrace_amount"], P["retrace_unit"], P["wait_bars"]
    entry_resolver = veto_mask = gen_report = None
    gate_used = gate
    attrib = None    # per-entry indicator vote attribution (decision #1/#5)
    if specs:
        from indicators import library, runner, generate
        try:
            inds = library.from_specs(specs)
        except Exception as e:   # IndicatorParamError etc. → surface to the UI as a ParamError
            raise ParamError(str(e))
        n_confirm = sum(1 for i in inds
                        if i.config.enabled and i.config.mode in ("confirm", "both"))
        if n_confirm > 0 and k_rule > n_confirm:
            raise ParamError(f"k={k_rule} exceeds the {n_confirm} enabled confirm-capable indicator(s)")
        base = gate if gate is not None else np.ones(len(d4), dtype=bool)
        # INDICATORS READ THE 1-MINUTE FRAME: directions are computed on d1 and each decision bar
        # samples its last-closed 1-minute candle (causal). Box trigger/cadence/exits unchanged;
        # warm-up now counts 1-minute candles. (src=None would keep the decision-TF behaviour.)
        ind_src = runner.indicator_source_1min(d4, d1, bar_td)
        # compute each ENABLED indicator's per-decision-bar vote ONCE (skip disabled — they don't
        # trade) and reuse it for the veto gate, the confirm resolver AND the attribution log.
        _votes = runner.compute_votes(d4, box, inds, src=ind_src)
        gate_used, entry_resolver, veto_mask = runner.build_layer(
            d4, box, inds, k_rule, base,
            retrace_amount=g_retr, retrace_unit=g_runit, wait_bars=g_wait,
            src=ind_src, votes=_votes, veto_as_flip=P["veto_as_flip"])
        if any(i.config.enabled and i.key in ("fvg", "order_block", "structure_trend") for i in inds):
            ctx = runner.market_context(d4)
            gen_report = generate.generate_structures(
                ctx, int(gen_params.get("swing_l", 2)), int(gen_params.get("golf_n", 3)))["report"]

        def attrib(sidx):
            # EVERY indicator's opinion at the signal bar; disabled ⇒ neutral (not computed).
            sidx = int(sidx)
            rows = []
            for i in inds:
                vv = _votes.get(id(i))
                v = int(vv[sidx]) if (vv is not None and 0 <= sidx < len(vv)) else 0
                rows.append({"key": i.key, "active": int(i.config.enabled), "mode": i.config.mode,
                             "vote": ("confirm" if v == 1 else "veto" if v == -1 else "neutral"),
                             "params": dict(i.config.params)})
            return rows

    # Optional split long/short SL/TP (Q3/E2). Each None ⇒ engine falls back to the shared points ⇒
    # byte-identical. Per-side tp maps to the single tp_hard (the fast path / champion use one tp).
    _sp_split = {}
    for side in ("long", "short"):
        if P[f"{side}_sl_soft"] is not None: _sp_split[f"{side}_sl_soft_points"] = P[f"{side}_sl_soft"]
        if P[f"{side}_sl_hard"] is not None: _sp_split[f"{side}_sl_hard_points"] = P[f"{side}_sl_hard"]
        if P[f"{side}_tp"] is not None:
            _sp_split[f"{side}_tp_hard_points"] = P[f"{side}_tp"]
    sp = SimpleStrategyParams(sl_soft_points=sl_soft, sl_hard_points=sl_hard,
                              tp_hard_points=tp, data_path_4h="", data_path_1min="",
                              box_data_path="", flip_entry_direction=flip, **_sp_split)
    # Step B2 (Axis B): precompute the param-independent Stage-1 signal ONCE (vectorized) and feed it to
    # the engine so it does NOT recompute _stage1_candle_signal + box.loc per decision bar. Byte-identical
    # (optimize.signals.decision_signals ≡ engine._stage1_candle_signal — see tests/test_axisB_signal_equiv.py).
    sig_arr = decision_signals(d4, box)

    # SL/TP are FIXED point values (the dynamic "sizing mode" was removed 2026-06-15 — see
    # REMOVAL_sltp_sizing_mode.md). The engine keeps a neutral `sl_tp_mult` hook but the dashboard never sets
    # it, so it stays None ⇒ byte-identical to the golden baselines.
    blocked = []   # diagnostic: directional signals the gate dropped (logged, not traded)
    trades, _ = SimpleStrategy(sp).backtest(d4, d1, box, entry_gate=gate_used,
                                            entry_resolver=entry_resolver, veto_mask=veto_mask,
                                            blocked_log=blocked, veto_as_flip=P["veto_as_flip"],
                                            signals=sig_arr)
    cand = sorted([t for t in trades if t.get("exit_reason") not in (None, "OPEN")],
                  key=lambda t: pd.Timestamp(t["entry_time"]))

    use_brk = dd_limit > 0; ddl = dd_limit
    peak = eq = 0.0; locked = False; cd = 0; skipped = 0
    taken, events, state, eqc = [], [], [], []
    for t in cand:
        et, xt = _ts(t["entry_time"]), _ts(t["exit_time"]); pnl = float(t["pnl_points"]) * pv
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False  # FIX: keep GLOBAL high-water mark (no peak reset)
                events.append({"time": et, "type": "UNLOCK", "text": f"UNLOCK — cooldown done; global peak ${peak:,.0f} kept"})
            else:
                state.append({"time": et, "value": 0}); skipped += 1
                events.append({"time": et, "type": "SKIP", "text": f"LOCKED — skip {t['direction']} @ {t['entry_price']:.1f} (would-be {pnl:+,.0f}); {cd} left"})
                continue
        state.append({"time": et, "value": 1})
        gtxt = "no gate" if gthr is None else f"gate OK (vol {vfw[int(t['entry_idx'])]:.0f} ≤ {gthr:.0f})"
        ind_rows = attrib(t["signal_idx"]) if (attrib and "signal_idx" in t) else None
        itxt = ""
        if ind_rows:
            act = [r for r in ind_rows if r["active"]]
            nc = sum(1 for r in act if r["vote"] == "confirm")
            nv = sum(1 for r in act if r["vote"] == "veto")
            itxt = f" | K={k_rule}: {nc} confirm / {nv} veto of {len(act)} active"
        vftxt = " · REVERSED (veto→flip)" if t.get("veto_flip") else ""
        ev = {"time": et, "type": "ENTRY",
              "text": f"{t['direction'].upper()} @ {t['entry_price']:.1f} | {gtxt} | "
                      f"SLsoft {t['sl_soft_line']:.1f}/SLhard {t['sl_hard_line']:.1f}/TP {t['tp_hard_line']:.1f}{itxt}{vftxt}"}
        if ind_rows:
            ev["indicators"] = ind_rows
        events.append(ev)
        eq += pnl; peak = max(peak, eq); dd = peak - eq
        events.append({"time": xt, "type": "WIN" if pnl > 0 else "LOSS", "text": f"exit @ {t['exit_price']:.1f} via {t['exit_reason']} | P/L {pnl:+,.0f} | equity ${eq:,.0f} | DD ${dd:,.0f}"})
        eqc.append({"time": xt, "value": round(eq, 2)})
        rec = {k: t[k] for k in ("entry_price", "exit_price", "direction", "exit_reason", "sl_soft_line", "sl_hard_line", "tp_hard_line")}
        rec["veto_flip"] = bool(t.get("veto_flip"))
        rec.update(entry_time=et, exit_time=xt, pnl=round(pnl, 2), equity=round(eq, 2), dd=round(dd, 2), year=pd.Timestamp(t["exit_time"]).year)
        taken.append(rec)
        if use_brk and dd >= ddl:
            locked = True; cd = cooldown
            events.append({"time": xt, "type": "LOCK", "text": f"🔒 LOCK — DD ${dd:,.0f} ≥ ${ddl:,.0f}; halt {cooldown} trades"})

    # Directional box signals that the gate dropped → log as NOENTRY (was silently discarded).
    # reason 'veto' (an indicator vetoed) or 'vol_gate' (HAR-RV gate skipped the bar). LOGS ONLY —
    # these are NOT trades and do NOT touch equity/drawdown/summary.
    for b in blocked:
        bt = _ts(d4["Date"].iloc[int(b["entry_idx"])])
        ev = {"time": bt, "type": "NOENTRY", "reason": ("vetoed" if b["reason"] == "veto" else "vol_gated")}
        if b["reason"] == "veto":
            vetoers = ""
            if attrib:
                rows = attrib(b["signal_idx"])
                vetoers = ",".join(r["key"] for r in rows if r["active"] and r["vote"] == "veto")
            ev["text"] = (f"ENTRY NOT TAKEN — {b['direction'].upper()} vetoed"
                          + (f" by {vetoers}" if vetoers else "") + " (indicator veto)")
            if attrib:
                ev["indicators"] = rows
        else:
            ev["text"] = (f"ENTRY NOT TAKEN — {b['direction'].upper()} skipped by volatility gate"
                          + ("" if gthr is None else f" (vol {vfw[int(b['entry_idx'])]:.0f} > {gthr:.0f})"))
        events.append(ev)

    # Warm-up notices (logs): each enabled indicator stays NEUTRAL for its look-back; composites
    # wait for the parts they depend on. Indicators read the 1-MINUTE frame, so warm-up counts
    # 1-MINUTE candles (dates come from d1). Log when warming starts (what it waits for) + eligible.
    if specs:
        nmin = len(d1); t0e = _ts(d4["Date"].iloc[0])
        for ind in inds:
            if not ind.config.enabled:
                continue
            w = int(ind.warmup_bars())
            if w <= 0:
                continue
            if w < nmin:
                first_dt = pd.Timestamp(d1["Date"].iloc[w]).strftime("%Y-%m-%d %H:%M")
                events.append({"time": t0e, "type": "WARMUP",
                               "text": f"⏳ WARMING UP — {ind.key} inactive for the first {w} one-minute "
                                       f"candles (waiting for {ind.warmup_deps()} to finish); first eligible {first_dt}"})
                events.append({"time": _ts(d1["Date"].iloc[w]), "type": "WARMED",
                               "text": f"✅ {ind.key} warmed up — now eligible to vote "
                                       f"(waited {w} one-minute candles for {ind.warmup_deps()})"})
            else:
                events.append({"time": t0e, "type": "WARMUP",
                               "text": f"⏳ WARMING UP — {ind.key} needs {w} one-minute candles but this "
                                       f"window has only {nmin} → it NEVER warms up here (waiting for {ind.warmup_deps()})"})

    candles = [{"time": _ts(d4["Date"].iloc[i]), "open": float(d4["Open"].iloc[i]), "high": float(d4["High"].iloc[i]),
                "low": float(d4["Low"].iloc[i]), "close": float(d4["Close"].iloc[i])} for i in range(len(d4))]
    vol = [{"time": _ts(d4["Date"].iloc[i]), "value": round(float(vfw[i]), 1)} for i in range(len(d4))]
    eqa = np.array([e["value"] for e in eqc]) if eqc else np.array([0.0]); uw = np.maximum.accumulate(eqa) - eqa
    drawdown = [{"time": eqc[i]["time"], "value": -round(float(uw[i]), 2)} for i in range(len(eqc))]
    pnl = np.array([t["pnl"] for t in taken]) if taken else np.array([]); yr = np.array([t["year"] for t in taken]) if taken else np.array([])
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]

    # Longest consecutive NON-ENTRY streak: the longest run of entry opportunities that did NOT
    # become a trade — NOENTRY (vol-gate/veto drops) or SKIP (drawdown-breaker halts) — with no
    # taken ENTRY interrupting it. Reported two ways: number of skipped signals + the calendar
    # span (days) from the first to the last non-entry in that run.
    _opp = sorted((e for e in events if e["type"] in ("ENTRY", "NOENTRY", "SKIP")),
                  key=lambda e: e["time"])
    _best_n = _cur_n = 0; _best_t0 = _best_t1 = _cur_t0 = None
    for e in _opp:
        if e["type"] == "ENTRY":
            _cur_n = 0; _cur_t0 = None
        else:
            if _cur_n == 0:
                _cur_t0 = e["time"]
            _cur_n += 1
            if _cur_n > _best_n:
                _best_n, _best_t0, _best_t1 = _cur_n, _cur_t0, e["time"]
    noentry_days = round((_best_t1 - _best_t0) / 86400.0, 1) if _best_n else 0.0
    noentry_start = (pd.Timestamp(_best_t0, unit="s").strftime("%Y-%m-%d") if _best_n else None)

    # --- entry-pause visibility (additive; does NOT touch trades/equity/PnL/DD) ---
    # Decompose, per decision bar, WHY no entry happened — box-silence vs vol-gate vs indicator block —
    # and the longest consecutive run of each (+ the longest open-position hold). Pure post-trade summary.
    from optimize import pause_streaks
    _n = len(d4)
    _sig = np.array([1 if s == "long" else -1 if s == "short" else 0 for s in sig_arr[:_n]], dtype=int)
    _volg = np.asarray(gate, dtype=bool)[:_n] if gate is not None else np.ones(_n, dtype=bool)
    _veto = np.asarray(veto_mask, dtype=bool)[:_n] if veto_mask is not None else np.zeros(_n, dtype=bool)
    _cmask = None
    if specs and any(i.config.enabled for i in inds):
        from indicators import runner as _runner
        _cmask = np.asarray(_runner.confirm_mask(d4, box, inds, k_rule, src=ind_src, votes=_votes),
                            dtype=bool)[:_n]
    _conf = _cmask if _cmask is not None else np.ones(_n, dtype=bool)
    _bar_secs = int(bar_td.total_seconds())
    _spans = [(0, max(1, round((_ts(t["exit_time"]) - _ts(t["entry_time"])) / _bar_secs)))
              for t in cand if t.get("exit_time") is not None]
    _pm = pause_streaks.pause_metrics(_sig, _volg, _veto, _conf, _bar_secs, trade_spans=_spans)
    _pt = pause_streaks.pause_totals(_sig, _volg, _veto, _conf, _bar_secs, trade_spans=_spans)

    # The missing confirm<K NOENTRY events: the engine's blocked_log only carries veto/vol_gate, so a box
    # signal that passed the vol gate + had no veto but failed the K-confirmer test was silently dropped.
    # Surface it (logs only — not a trade).
    if _cmask is not None:
        _cand = _sig != 0
        for i in np.flatnonzero(_cand & _volg & ~_veto & ~_conf):
            i = int(i)
            events.append({"time": _ts(d4["Date"].iloc[i]), "type": "NOENTRY", "reason": "confirm<K",
                           "text": f"ENTRY NOT TAKEN — {'LONG' if _sig[i] > 0 else 'SHORT'} blocked: "
                                   f"fewer than K={k_rule} confirmers"})

    summary = dict(pnl=float(pnl.sum()) if len(pnl) else 0.0,
                   pnl_2025=float(pnl[yr == config.YEARS[0]].sum()) if len(pnl) else 0.0,
                   pnl_2026=float(pnl[yr == config.YEARS[1]].sum()) if len(pnl) else 0.0,
                   n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped,
                   exposure=round(100 * len(taken) / max(len(cand), 1), 1),
                   win=round(100 * (pnl > 0).mean(), 1) if len(pnl) else 0.0,
                   pf=round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() != 0 else None,
                   payoff=round(float(wins.mean() / abs(losses.mean())), 2) if len(wins) and len(losses) else None,
                   avg_win=round(float(wins.mean()), 0) if len(wins) else 0, avg_loss=round(float(losses.mean()), 0) if len(losses) else 0,
                   max_dd=round(float(uw.max()), 0) if len(eqc) else 0.0, n_locks=sum(1 for e in events if e["type"] == "LOCK"),
                   noentry_streak_n=_best_n, noentry_streak_days=noentry_days, noentry_streak_start=noentry_start,
                   box_silence=_pm["box_silence"], position_hold=_pm["position_hold"],
                   gate_noentry=_pm["gate_noentry"], indicator_noentry=_pm["indicator_noentry"],
                   noentry_total=_pt["noentry_total"], box_silence_total=_pt["box_silence_total"],
                   position_hold_total=_pt["position_hold_total"], gate_noentry_total=_pt["gate_noentry_total"],
                   indicator_noentry_total=_pt["indicator_noentry_total"])
    params_out = dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp, gate_pct=(None if gthr is None else float(gate_pct)),
                      gate_thr=(None if gthr is None else round(gthr, 0)), dd_limit=(ddl if use_brk else None),
                      cooldown=cooldown, dd_cap=dd_cap, pv=pv, flip=flip, window=window,
                      timeframe=P["timeframe"], indicators=specs, k=k_rule, gen=gen_params,
                      veto_as_flip=P["veto_as_flip"],
                      # echo the global entry-timing + split long/short SL/TP back so the dashboard form
                      # round-trips faithfully (without these the UI reverts retrace/wait + drops split mode).
                      retrace_amount=P["retrace_amount"], retrace_unit=P["retrace_unit"], wait_bars=P["wait_bars"],
                      long_sl_soft=P["long_sl_soft"], long_sl_hard=P["long_sl_hard"], long_tp=P["long_tp"],
                      short_sl_soft=P["short_sl_soft"], short_sl_hard=P["short_sl_hard"], short_tp=P["short_tp"])
    return dict(meta=dict(params=params_out, summary=summary,
                          split_ts=_ts(df4.iloc[min(n2025, len(df4) - 1)]["Date"]),
                          gen_report=gen_report),
                candles=candles, vol=vol, gate_thr=(gthr if gthr is not None else 0), state=state,
                trades=taken, equity=eqc, drawdown=drawdown, events=sorted(events, key=lambda e: e["time"]))
