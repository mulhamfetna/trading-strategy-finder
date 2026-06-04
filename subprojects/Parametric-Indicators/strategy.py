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
from volatility import vol_forecast

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
    if params["window"] not in ("full", "2025", "2026"):
        raise ParamError(f"window must be one of full|2025|2026 (got {params['window']!r})")
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
    return dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp, gate_pct=gate_pct, dd_limit=dd_limit,
                cooldown=int(cooldown), flip=bool(params["flip"]), window=params["window"],
                dd_cap=dd_cap, pv=pv, indicators=list(specs), k=k, gen=gen)


def build_payload(df4, df1, box, vf, n2025, params=None):
    P = validate_params(params)
    sl_soft, sl_hard, tp = P["sl_soft"], P["sl_hard"], P["tp"]
    cooldown, flip = P["cooldown"], P["flip"]
    gate_pct, dd_limit, window = P["gate_pct"], P["dd_limit"], P["window"]
    dd_cap, pv = P["dd_cap"], P["pv"]

    N = len(df4)
    lo, hi = {"full": (0, N), "2025": (0, n2025), "2026": (n2025, N)}[window]
    d4 = df4.iloc[lo:hi].reset_index(drop=True)
    t0, t1 = d4["Date"].iloc[0], d4["Date"].iloc[-1] + pd.Timedelta(hours=4)
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    vfw = vf[lo:hi]

    gthr = gate = None
    if gate_pct > 0:
        gthr = float(np.percentile(vf[:n2025], float(gate_pct)))
        gate = vfw <= gthr

    # WS-I indicator confirmation layer (off by default ⇒ identical to the pure box strategy).
    specs, k_rule, gen_params = P["indicators"], P["k"], P["gen"]
    entry_resolver = veto_mask = gen_report = None
    gate_used = gate
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
        gate_used, entry_resolver, veto_mask = runner.build_layer(d4, box, inds, k_rule, base)
        if any(i.config.enabled and i.key in ("fvg", "order_block", "structure_trend") for i in inds):
            ctx = runner.market_context(d4)
            gen_report = generate.generate_structures(
                ctx, int(gen_params.get("swing_l", 2)), int(gen_params.get("golf_n", 3)))["report"]

    sp = SimpleStrategyParams(sl_soft_points=sl_soft, sl_hard_points=sl_hard, tp_soft_points=tp,
                              tp_hard_points=tp, data_path_4h="", data_path_1min="",
                              box_data_path="", flip_entry_direction=flip)
    trades, _ = SimpleStrategy(sp).backtest(d4, d1, box, entry_gate=gate_used,
                                            entry_resolver=entry_resolver, veto_mask=veto_mask)
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
        events.append({"time": et, "type": "ENTRY", "text": f"{t['direction'].upper()} @ {t['entry_price']:.1f} | {gtxt} | SLsoft {t['sl_soft_line']:.1f}/SLhard {t['sl_hard_line']:.1f}/TP {t['tp_hard_line']:.1f}"})
        eq += pnl; peak = max(peak, eq); dd = peak - eq
        events.append({"time": xt, "type": "WIN" if pnl > 0 else "LOSS", "text": f"exit @ {t['exit_price']:.1f} via {t['exit_reason']} | P/L {pnl:+,.0f} | equity ${eq:,.0f} | DD ${dd:,.0f}"})
        eqc.append({"time": xt, "value": round(eq, 2)})
        rec = {k: t[k] for k in ("entry_price", "exit_price", "direction", "exit_reason", "sl_soft_line", "sl_hard_line", "tp_soft_line", "tp_hard_line")}
        rec.update(entry_time=et, exit_time=xt, pnl=round(pnl, 2), equity=round(eq, 2), dd=round(dd, 2), year=pd.Timestamp(t["exit_time"]).year)
        taken.append(rec)
        if use_brk and dd >= ddl:
            locked = True; cd = cooldown
            events.append({"time": xt, "type": "LOCK", "text": f"🔒 LOCK — DD ${dd:,.0f} ≥ ${ddl:,.0f}; halt {cooldown} trades"})

    candles = [{"time": _ts(d4["Date"].iloc[i]), "open": float(d4["Open"].iloc[i]), "high": float(d4["High"].iloc[i]),
                "low": float(d4["Low"].iloc[i]), "close": float(d4["Close"].iloc[i])} for i in range(len(d4))]
    vol = [{"time": _ts(d4["Date"].iloc[i]), "value": round(float(vfw[i]), 1)} for i in range(len(d4))]
    eqa = np.array([e["value"] for e in eqc]) if eqc else np.array([0.0]); uw = np.maximum.accumulate(eqa) - eqa
    drawdown = [{"time": eqc[i]["time"], "value": -round(float(uw[i]), 2)} for i in range(len(eqc))]
    pnl = np.array([t["pnl"] for t in taken]) if taken else np.array([]); yr = np.array([t["year"] for t in taken]) if taken else np.array([])
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    summary = dict(pnl=float(pnl.sum()) if len(pnl) else 0.0,
                   pnl_2025=float(pnl[yr == config.YEARS[0]].sum()) if len(pnl) else 0.0,
                   pnl_2026=float(pnl[yr == config.YEARS[1]].sum()) if len(pnl) else 0.0,
                   n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped,
                   exposure=round(100 * len(taken) / max(len(cand), 1), 1),
                   win=round(100 * (pnl > 0).mean(), 1) if len(pnl) else 0.0,
                   pf=round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() != 0 else None,
                   avg_win=round(float(wins.mean()), 0) if len(wins) else 0, avg_loss=round(float(losses.mean()), 0) if len(losses) else 0,
                   max_dd=round(float(uw.max()), 0) if len(eqc) else 0.0, n_locks=sum(1 for e in events if e["type"] == "LOCK"))
    params_out = dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp, gate_pct=(None if gthr is None else float(gate_pct)),
                      gate_thr=(None if gthr is None else round(gthr, 0)), dd_limit=(ddl if use_brk else None),
                      cooldown=cooldown, dd_cap=dd_cap, pv=pv, flip=flip, window=window,
                      indicators=specs, k=k_rule, gen=gen_params)
    return dict(meta=dict(params=params_out, summary=summary, split_ts=_ts(df4.iloc[n2025]["Date"]),
                          gen_report=gen_report),
                candles=candles, vol=vol, gate_thr=(gthr if gthr is not None else 0), state=state,
                trades=taken, equity=eqc, drawdown=drawdown, events=sorted(events, key=lambda e: e["time"]))
