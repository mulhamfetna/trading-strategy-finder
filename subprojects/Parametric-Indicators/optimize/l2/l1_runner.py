"""L2 Pass 1 — run the FROZEN lean 3-indicator champion (L1) and emit everything L2 needs:
the taken-trade ledger (with the same drawdown breaker as core.backtest_metrics), the per-bar
no-entry attribution, the isolated dropped-signal log (veto + vol-gate only), and the L1 flat/
in-position state timeline. L1's engine bytes are never touched (golden stays green)."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import config                                                       # noqa: E402
import presets                                                      # noqa: E402
from optimize import data as data_mod, timeframes as TF, signals as sig_mod   # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int     # noqa: E402
from optimize.counterfactual_pause import attribute                # noqa: E402
from indicators import library, runner                             # noqa: E402
from volatility import gate_threshold                              # noqa: E402


def _lean_params(tf: str = "4h") -> dict:
    """Build the L1 engine-param dict from optimize/results/wsh_lean_4h_champion.json via presets._all_specs."""
    c = presets._champions_lean().get(tf)
    if not c:
        raise SystemExit("missing optimize/results/wsh_lean_4h_champion.json (the L1 source of truth)")
    box = c["box"]
    specs, _gen = presets._all_specs(c.get("indicators", {}))
    return dict(sl_soft=float(box["sl_soft"]), sl_hard=float(box["sl_hard"]), tp=float(box["tp"]),
                gate_pct=float(box["gate_pct"]), dd_limit=float(box["dd_limit"]),
                cooldown=int(box["cooldown"]), flip=bool(box["flip"]), window="full",
                k=int(box["k"]), ind_1min=True, indicators=specs)


LEAN_4H_PARAMS: dict = _lean_params("4h")


def _votes_by_bar(votes: dict, inds, n: int) -> list:
    """Per-bar [{key, vote, active}] for every enabled indicator. The vote int (from compute_votes)
    encodes confirm(+1)/veto(-1)/neutral(0) relative to the box direction — same convention the rich
    L1 view uses (strategy.attrib). `inds` here are already the enabled set, so active=True."""
    out = [[] for _ in range(n)]
    for ind in inds:
        if not ind.config.enabled:
            continue
        arr = votes.get(id(ind))
        if arr is None:
            continue
        for i in range(min(n, len(arr))):
            v = int(arr[i])
            vote = "confirm" if v == 1 else "veto" if v == -1 else "neutral"
            out[i].append({"key": ind.key, "vote": vote, "active": True})
    return out


def apply_breaker(cand: list[dict], pv: float, dd_limit: float, cooldown: int):
    """Global-HWM drawdown-breaker overlay — identical math to optimize.core.backtest_metrics
    (lines 125-150). Returns (taken, n_skipped, n_locks); each taken dict = the fast_backtest trade
    dict + 'pnl' (dollars), 'eq', 'dd'."""
    use_brk = dd_limit > 0
    peak = eq = 0.0
    locked = False
    cd = 0
    skipped = 0
    n_locks = 0
    taken: list[dict] = []
    for t in cand:
        pnl = float(t["pnl_points"]) * pv
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False
            else:
                skipped += 1
                continue
        eq += pnl
        peak = max(peak, eq)
        dd = peak - eq
        tt = dict(t)
        tt["pnl"] = pnl
        tt["eq"] = eq
        tt["dd"] = dd
        taken.append(tt)
        if use_brk and dd >= dd_limit:
            locked = True
            cd = cooldown
            n_locks += 1
    return taken, skipped, n_locks


def build_state_timeline(taken: list[dict], dec_dates: np.ndarray, n: int) -> np.ndarray:
    """Per-decision-bar L1 position state. A trade occupies [entry_idx, exit_bar), where exit_bar is the
    first decision bar at/after exit_time (and at least entry_idx+1, so the entry bar is always occupied)."""
    in_pos = np.zeros(n, dtype=bool)
    for t in taken:
        e = int(t["entry_idx"])
        xb = int(np.searchsorted(dec_dates, np.datetime64(t["exit_time"]), side="left"))
        xb = max(xb, e + 1)
        in_pos[e:min(xb, n)] = True
    return in_pos


@dataclass
class L1Result:
    tf: str
    params: dict
    df_dec: pd.DataFrame
    df1: pd.DataFrame
    box: pd.DataFrame
    vf: np.ndarray
    n_split: int
    bar_td: pd.Timedelta
    sig_int: np.ndarray
    vol_gate: np.ndarray
    veto: np.ndarray
    confirm: np.ndarray
    ledger: list           # taken trade dicts (post-breaker, full fields + pnl/eq/dd)
    cause: np.ndarray      # per-bar attribution (object array; cause[0] is None)
    dropped_signals: list  # [{idx, ts, box_dir, reason}] for veto + vol_gate only
    state_timeline: np.ndarray  # bool, True = L1 in-position
    vf_seed: np.ndarray = None  # the IN-SAMPLE vf prefix (vf_full[:n2025]) the gate seeds on; survives
                                # windowing so L2 (engine.run_l2) seeds on 2025 even for a 2026 window
    n_candidates: int = 0       # pre-breaker candidate trades (for exposure %)
    n_skipped_breaker: int = 0  # candidates the breaker skipped
    n_locks: int = 0            # number of breaker lock events
    votes_by_bar: list = field(default_factory=list)   # per-bar [{key,vote,active}] for every enabled indicator
    skipped_would_be: dict = field(default_factory=dict)  # {bar_idx: would_be_pnl $} for breaker-skipped candidates


def run_l1(tf: str = "4h", params: dict | None = None) -> L1Result:
    """params=None → the FROZEN lean champion (default; golden + disk-cache stay valid). Pass a dict to
    run an ARBITRARY L1 profile (combined dashboard: L1 editable) — same engine, same schema as L2
    (sl_soft/sl_hard/tp/gate_pct/dd_limit/cooldown/flip/k/ind_1min/indicators)."""
    params = _lean_params(tf) if params is None else dict(params)
    df_dec, df1, box, vf, n_split = data_mod.load_inputs(tf)
    bar_td = TF.get(tf).bar_td
    # window selection (default full): physically slice the data via the SHARED helper so windowed L1
    # numbers match strategy.build_payload byte-for-byte (4h sources verified identical). The gate seeds
    # on the PRE-window in-sample prefix vf_seed — NEVER on the windowed vf — and L2 inherits the window
    # because it runs on this (now windowed) df_dec.
    window = (params.get("window") or "full")
    if window != "full":
        import strategy                                       # lazy (acyclic): the shared window slicer
        df_dec, df1, vf, _df_full, _vf_full, n_split, box, _lo, _hi = strategy.window_slice(
            df_dec, df1, box, vf, n_split, window, tf)
        vf_seed = np.asarray(_vf_full)[:n_split]              # in-sample prefix from the POST-swap full vf
        vf = np.asarray(vf)                                   # the engine runs on the WINDOWED vf
    else:
        vf_seed = np.asarray(vf)[:n_split]
    n = len(df_dec)
    sig_int = np.asarray(signals_to_int(sig_mod.decision_signals(df_dec, box)))[:n]

    # vol gate seeded on the IN-SAMPLE prefix (vf_seed), applied on the (windowed) vf — causal.
    vol_gate = np.ones(n, dtype=bool)
    if params["gate_pct"] > 0:
        gthr = gate_threshold(vf_seed, len(vf_seed), params["gate_pct"])
        vol_gate = vf[:n] <= gthr

    inds = library.from_specs([s for s in params["indicators"] if s.get("enabled")])
    src = runner.indicator_source_1min(df_dec, df1, bar_td) if params["ind_1min"] else None
    votes = runner.compute_votes(df_dec, box, inds, src=src)
    veto = np.asarray(runner.veto_mask(df_dec, box, inds, src=src, votes=votes), dtype=bool)[:n]
    confirm = np.asarray(runner.confirm_mask(df_dec, box, inds, int(params["k"]), src=src, votes=votes),
                         dtype=bool)[:n]

    engine_gate = vol_gate & ~veto & confirm
    dec_dates = df_dec["Date"].to_numpy()
    cand = fast_backtest(
        dec_dates, df_dec["Close"].to_numpy(float), sig_int, engine_gate,
        df1["Date"].to_numpy(), df1["High"].to_numpy(float),
        df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
        params["sl_soft"], params["sl_hard"], params["tp"], params["flip"],
        **{k: params.get(k) for k in ("long_sl_soft", "long_sl_hard", "long_tp",
                                      "short_sl_soft", "short_sl_hard", "short_tp")})
    pv = float(config.NQ_POINT_VALUE)
    taken, _skipped, _locks = apply_breaker(cand, pv, params["dd_limit"], params["cooldown"])

    cause = attribute(sig_int, vol_gate, veto, confirm)
    dropped = []
    for idx in range(1, n):
        if cause[idx] in ("vetoed", "vol_gated"):
            dropped.append({"idx": idx,
                            "ts": pd.Timestamp(dec_dates[idx]),
                            "box_dir": "long" if sig_int[idx - 1] == 1 else "short",
                            "reason": "veto" if cause[idx] == "vetoed" else "vol_gate"})
    state_timeline = build_state_timeline(taken, dec_dates, n)
    skipped_would_be = {int(t["entry_idx"]): float(t["pnl_points"]) * pv for t in cand
                        if int(t["entry_idx"]) < len(cause) and cause[int(t["entry_idx"])] == "would_enter"}

    return L1Result(tf=tf, params=params, df_dec=df_dec, df1=df1, box=box, vf=vf, n_split=n_split,
                    bar_td=bar_td, sig_int=sig_int, vol_gate=vol_gate, veto=veto, confirm=confirm,
                    ledger=taken, cause=cause, dropped_signals=dropped, state_timeline=state_timeline,
                    vf_seed=vf_seed,
                    n_candidates=len(cand), n_skipped_breaker=_skipped, n_locks=_locks,
                    votes_by_bar=_votes_by_bar(votes, inds, n), skipped_would_be=skipped_would_be)
