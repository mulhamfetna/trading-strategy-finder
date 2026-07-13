"""H.1 — timeframe-parametric, metrics-only backtest core.

This is the optimiser's fast path: it runs the SAME verified clone engine + the SAME volatility
gate + the SAME global-high-water-mark drawdown breaker as the dashboard's `strategy.build_payload`,
but (a) parameterised by the *decision-bar duration* (so any entry timeframe works — the only 4h
assumption removed is the hardcoded `+4h` 1m-window bound), and (b) returns only the summary metrics
+ the taken-trade list (no chart series), so thousands of trials run quickly.

Parity contract (locked by test_parity.py): with bar_duration = 4h and the winner params, this
reproduces `strategy.build_payload`'s summary bit-for-bit (+$7,735 / $3,670 maxDD / 66 trades).

Exits are unchanged — always resolved on the 1-minute frame inside the engine.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# the parent subproject modules use top-level imports (engine, box_lookup, ...)
_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import config  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int  # noqa: E402
from optimize import signals as _sig  # noqa: E402


# --- per-run memo of the param-INDEPENDENT 1-minute indicator source + per-config indicator votes -----
# backtest_metrics re-slices df_dec/df1 per fold, so the heavy market_context(df1) build AND the SMC vote
# computation (ifvg/breaker are ~90% of per-trial cost, per the README) were redone on EVERY trial even
# though each fold's window recurs identically across trials. We memoise by a CONTENT signature of the
# (decision, 1-minute) slice — stable across trials for a fixed dataset — so the source builds once per
# fold and each indicator config's votes compute once. Result-neutral: identical inputs ⇒ identical
# arrays (mirrors the L2 engine cache + the ES gate cache, both parity-locked). Expensive SMC indicators
# have tiny config spaces (no params / swing_l∈1..20) ⇒ the vote memo stays small + high-hit. Mirrors
# optimize/l2/contributors/gate.py's module-level caches (incl. a _clear_caches() test seam).
_SRC_MEMO: dict = {}
_VOTE_MEMO: dict = {}
_IC_DIR_MEMO: dict = {}   # per-(1-min slice, indicator) FULL 1-min directions for the intra-candle gate
_EOD_MEMO: dict = {}      # per-(1-min slice, margin) end-of-day target bars — param-independent, so one
#                           build per fold serves every trial (eod_targets is a Python loop over sessions)
_NEWS_MASK_MEMO: dict = {}  # per-(decision slice, pre, post, calendar) release-window ENTRY-BLOCK mask
_NEWS_TGT_MEMO: dict = {}   # per-(1-min slice, pre, calendar) NEWS_VETO force-EXIT target bars


def _news_calendar(params: dict):
    """The release calendar this run should use.

    `_news_calendar_override` lets the null test (optimize/fundamentals/run_nulltest.py) swap in a FAKE
    calendar without touching the committed CSV. Absent ⇒ the real one.
    """
    cal = params.get("_news_calendar_override")
    if cal is None:
        from optimize.fundamentals import release_calendar as _rc
        cal = _rc.load_calendar()
    return cal


def _news_window_mask(params: dict, d):
    """bool[len(d)] where a NEW ENTRY must be blocked, or None when the news veto is off.

    None ⇒ the caller leaves `gate` untouched ⇒ byte-identical to pre-feature (golden-locked).
    """
    if not params.get("news_veto"):
        return None
    pre = int(params.get("news_pre_min", 0))
    post = int(params.get("news_post_min", 12))
    key = (len(d), str(d["Date"].iloc[0]), str(d["Date"].iloc[-1]), pre, post,
           id(params.get("_news_calendar_override")))
    if key not in _NEWS_MASK_MEMO:
        from optimize.fundamentals import window as _w
        _NEWS_MASK_MEMO[key] = _w.release_window_mask(d, _news_calendar(params), pre, post)
    return _NEWS_MASK_MEMO[key]


def _clear_caches() -> None:
    _SRC_MEMO.clear()
    _VOTE_MEMO.clear()
    _IC_DIR_MEMO.clear()
    _EOD_MEMO.clear()
    _NEWS_MASK_MEMO.clear()
    _NEWS_TGT_MEMO.clear()


def _slice_sig(d, d1, bar_duration):
    """Hashable CONTENT signature of a (decision, 1-minute) window pair for a fixed dataset: each frame's
    (length, first, last) timestamp + the bar duration. Same fold across trials ⇒ same signature; two
    genuinely different contiguous time-slices from one source cannot collide (a slice is determined by
    its length + endpoints)."""
    dd = d["Date"].to_numpy("datetime64[ns]").view("int64")
    md = d1["Date"].to_numpy("datetime64[ns]").view("int64")
    de = (int(dd[0]), int(dd[-1])) if len(dd) else (0, 0)
    me = (int(md[0]), int(md[-1])) if len(md) else (0, 0)
    return (len(dd), de[0], de[1], len(md), me[0], me[1], str(bar_duration))


def _cached_source(d, d1, bar_duration):
    """Memoised runner.indicator_source_1min — built once per distinct slice, reused across trials."""
    from indicators import runner
    key = _slice_sig(d, d1, bar_duration)
    src = _SRC_MEMO.get(key)
    if src is None:
        src = runner.indicator_source_1min(d, d1, bar_duration)
        _SRC_MEMO[key] = src
    return src


def _cached_votes(d, d1, box, inds, src, bar_duration):
    """runner.compute_votes drop-in (dict keyed by id(ind)) with a per-(slice, config) memo, backed by a
    disk cache (vote_cache) so cold computes (ifvg/breaker) persist across processes + respawns. Returned
    arrays are read-only downstream (veto/confirm masks copy), so sharing them is safe. Result-neutral."""
    from indicators import runner
    from optimize import vote_cache
    base = _slice_sig(d, d1, bar_duration)
    use1 = src is not None
    ctx = bdir = None                                    # built lazily, only on a real (memo+disk) miss
    out = {}
    for ind in inds:
        if not ind.config.enabled:
            continue
        c = ind.config
        params_t = tuple(sorted(c.params.items()))
        key = (base, use1, ind.key, c.mode, params_t)
        v = _VOTE_MEMO.get(key)
        if v is None:
            dkey = vote_cache.disk_key(base, use1, ind.key, c.mode, params_t)
            v = vote_cache.get(dkey)
            if v is None:
                if ctx is None:
                    from indicators.runner import market_context, box_direction_int
                    ctx = market_context(d); bdir = box_direction_int(d, box)
                v = runner._ind_vote(ind, ctx, bdir, src)
                vote_cache.put(dkey, v)
            _VOTE_MEMO[key] = v
        out[id(ind)] = v
    return out


def _contributor_gate(d, d1, box, vfw, vf, n_split, gate_ref_vf, gate_pct, params,
                      bar_duration, contrib, lo, hi):
    """Entry gate for the cross-instrument contributor path (L1 opt-in): vol_gate ∧ (NQ veto/confirm
    COMBINED with the precomputed contributor masks by topology). The expensive ES committee is NOT
    recomputed here — it lives in `contrib` (precomputed once per trial over the full frame); only the
    cheap NQ masks are computed on this window, then combined via the shared contributors/combine helper."""
    import numpy as np
    from indicators import library, runner
    from optimize.l2.contributors import combine
    gate_vol = None
    if gate_pct > 0:
        ref = gate_ref_vf if gate_ref_vf is not None else vf[:n_split]
        gate_vol = vfw <= float(np.percentile(ref, gate_pct))
    base = gate_vol if gate_vol is not None else np.ones(len(d), dtype=bool)
    specs = params.get("indicators") or []
    inds = library.from_specs(specs) if specs else []
    if inds and any(i.config.enabled for i in inds):
        src = _cached_source(d, d1, bar_duration) if params.get("ind_1min") else None
        votes = _cached_votes(d, d1, box, inds, src, bar_duration)
        nq_veto = runner.veto_mask(d, box, inds, src=src, votes=votes)
        nq_confirm = runner.confirm_mask(d, box, inds, int(params.get("k", 1)), src=src, votes=votes)
        nq_cc, nq_nconf = runner.confirm_count(d, box, inds, src=src, votes=votes)
    else:
        m = len(d)
        nq_veto = np.zeros(m, dtype=bool); nq_confirm = np.ones(m, dtype=bool)
        nq_cc = np.zeros(m, dtype=np.int64); nq_nconf = 0
    veto = nq_veto | np.asarray(contrib["veto"])[lo:hi]
    parsed = [(cc[lo:hi], k_es, has) for (cc, k_es, has) in contrib["parsed"]]
    return combine.combine_eligibility(base, veto, nq_confirm, nq_cc, int(params.get("k", 1)),
                                       nq_nconf, parsed, contrib["topology"])


def _cached_ic_gate(d1, inds, k):
    """Per-1-min-bar full-gate arrays {+1,-1} for the intra-candle feature, matching
    runner.intracandle_gate_arrays but MEMOISED per (1-min slice, indicator, params): the expensive full-1-min
    SMC direction compute happens once per distinct indicator config, so a search that holds indicators fixed
    (the E2 case) pays it ONCE across all trials."""
    from indicators import runner
    from indicators.base import BOTH
    base = _ic_slice_sig(d1)
    confirmers = [i for i in inds if i.config.enabled and i.config.mode in ("confirm", "both")]
    vetoers = [i for i in inds if i.config.enabled and i.config.mode in ("veto", "both")]
    k_eff = min(int(k), len(confirmers))
    n1 = len(d1)
    ctx1 = [None]

    def dirs(ind):
        key = (base, ind.key, tuple(sorted(ind.config.params.items())))
        v = _IC_DIR_MEMO.get(key)
        if v is None:
            if ctx1[0] is None:
                ctx1[0] = runner.market_context(d1)
            v = runner._dirs_1min(ind, ctx1[0])
            _IC_DIR_MEMO[key] = v
        return v

    out = {}
    for dsign in (+1, -1):
        conf = np.zeros(n1, dtype=np.int64); veto = np.zeros(n1, dtype=bool)
        for ind in confirmers:
            c, _ = dirs(ind); conf += ((c == dsign) | (c == BOTH)).astype(np.int64)
        for ind in vetoers:
            _, v = dirs(ind); veto |= ((v == dsign) | (v == BOTH))
        out[dsign] = (~veto) & (conf >= k_eff) if k_eff > 0 else (~veto)
    return out


def _ic_slice_sig(d1):
    return (len(d1), str(d1["Date"].iloc[0]) if len(d1) else "", str(d1["Date"].iloc[-1]) if len(d1) else "")


def backtest_metrics(
    df_dec: pd.DataFrame,
    df1: pd.DataFrame,
    box: pd.DataFrame,
    vf: np.ndarray,
    n_split: int,
    params: dict,
    bar_duration: pd.Timedelta,
    *,
    gate_ref_vf: np.ndarray | None = None,
    sig_int: np.ndarray | None = None,
    gate_used: np.ndarray | None = None,
    contrib: dict | None = None,
    pv: float = config.NQ_POINT_VALUE,
) -> dict:
    """Run one backtest on an arbitrary decision timeframe; return summary metrics + trades.

    Args:
      df_dec:   decision-frame OHLCV (any timeframe); needs 'Date','Open','High','Low','Close'.
      df1:      1-minute OHLCV (exit resolution + realized vol). Unchanged across timeframes.
      box:      box-level frame indexed by normalized Date.
      vf:       HAR-RV forecast aligned 1:1 with df_dec rows.
      n_split:  index splitting the first calendar segment (e.g. 2025) from the rest; the gate
                threshold is frozen on vf[:n_split] (causal) unless gate_ref_vf is given.
      params:   {sl_soft, sl_hard, tp, gate_pct, dd_limit, cooldown, flip, window}.
      bar_duration: decision-bar length (e.g. pd.Timedelta(hours=4)); replaces the hardcoded +4h.
      gate_ref_vf:  optional explicit reference array for the gate percentile (walk-forward, H.6).
                    Defaults to vf[:n_split].

    Returns dict(pnl, pnl_2025, pnl_2026, max_dd, n_taken, n_candidates, n_skipped_breaker,
                 win, pf, n_locks, exposure, trades).
    """
    sl_soft = float(params["sl_soft"]); sl_hard = float(params["sl_hard"]); tp = float(params["tp"])
    gate_pct = float(params["gate_pct"]); dd_limit = float(params["dd_limit"])
    cooldown = int(params["cooldown"]); flip = bool(params["flip"])
    window = params.get("window", "full")
    # Split SL/TP (Q3 / E2): optional per-direction overrides. Absent ⇒ None ⇒ fast_backtest uses the shared
    # sl_soft/sl_hard/tp for both sides ⇒ byte-identical to the pre-split path (golden + fast-parity locked).
    _split = {k: (float(params[k]) if params.get(k) is not None else None) for k in
              ("long_sl_soft", "long_sl_hard", "long_tp", "short_sl_soft", "short_sl_hard", "short_tp")}
    cap_1min = int(params.get("cap_1min", 0) or 0)    # max-hold (traded 1-min bars); 0 = off (bars cap)
    # Time-cap mode: none | bars | eod | both. This MUST be threaded to fast_backtest below — it used to be
    # dropped here, so a trial recorded as an EOD champion was in fact SCORED with no EOD cap at all.
    cap_mode = str(params.get("cap_mode") or "none")
    eod_margin = int(params.get("eod_margin_min", 15) or 15)

    N = len(df_dec)
    lo, hi = {"full": (0, N), "2025": (0, n_split), "2026": (n_split, N)}[window]
    d = df_dec.iloc[lo:hi].reset_index(drop=True)
    if d.empty:
        return _empty()
    t0 = d["Date"].iloc[0]
    t1 = d["Date"].iloc[-1] + bar_duration            # generalised: was hardcoded +4h
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    vfw = vf[lo:hi]

    # Gate. A precomputed `gate_used` (Stage-1 sub-optimizer freeze-once) bypasses the vol+indicator
    # recompute entirely — it ALREADY encodes vol_gate ∧ ¬veto ∧ confirm≥K, computed once over the full
    # series (so warm-up is correct) and sliced to this window. Default None ⇒ compute exactly as before
    # (parity preserved; golden unaffected).
    ic_gate_by_dir = ic_vol_gate = ic_veto_mask = ic_normal_gate = None   # intra-candle inputs (None ⇒ off)
    if gate_used is not None:
        gate = np.asarray(gate_used, dtype=bool)[lo:hi]
    elif contrib is not None:
        # Cross-instrument contributor path (L1 opt-in). Default (contrib=None) is byte-identical.
        gate = _contributor_gate(d, d1, box, vfw, vf, n_split, gate_ref_vf, gate_pct, params,
                                 bar_duration, contrib, lo, hi)
    else:
        # Volatility gate threshold frozen on the reference segment (causal); 0 => no gate.
        gate = None
        if gate_pct > 0:
            ref = gate_ref_vf if gate_ref_vf is not None else vf[:n_split]
            gthr = float(np.percentile(ref, gate_pct))
            gate = vfw <= gthr

        # WS-I.7 indicator layer (optional): fold veto + confirm into the gate as a per-bar mask.
        # gate_used = vol_gate ∧ ¬veto ∧ confirm≥K. Off/absent ⇒ gate unchanged (parity). The fast path
        # treats confirm/veto as an immediate-fill GATE; retrace/wait + live-carry stay in the exact
        # engine (dashboard). NSGA search over which indicators help runs on this gate.
        specs = params.get("indicators") or []
        if specs:
            from indicators import library, runner
            inds = library.from_specs(specs)
            if any(i.config.enabled for i in inds):
                base = gate if gate is not None else np.ones(len(d), dtype=bool)
                # params["ind_1min"]=True ⇒ indicators read the 1-minute frame (sampled at each decision
                # bar's last-closed minute); else decision-TF (default, unchanged). Votes computed ONCE
                # and shared by the veto + confirm masks.
                src = _cached_source(d, d1, bar_duration) if params.get("ind_1min") else None
                votes = _cached_votes(d, d1, box, inds, src, bar_duration)
                vmask = runner.veto_mask(d, box, inds, src=src, votes=votes)
                cmask = runner.confirm_mask(d, box, inds, int(params.get("k", 1)), src=src, votes=votes)
                gate = base & ~vmask & cmask
                # News veto: a scheduled high-impact release can only ever REMOVE eligibility. Absent /
                # off ⇒ _news_window_mask returns None ⇒ gate untouched ⇒ byte-identical (golden-locked).
                nmask = _news_window_mask(params, d)
                if nmask is not None:
                    gate = gate & ~nmask
                # Intra-candle vetoed entry (optional). Build the per-1-min gate (memoised) + pass the vol gate
                # (base), veto mask, and full composite gate. Off/absent ⇒ ic_* stay None ⇒ fast path unchanged.
                if params.get("intracandle_veto_entry"):
                    ic_gate_by_dir = _cached_ic_gate(d1, inds, int(params.get("k", 1)))
                    ic_vol_gate = np.asarray(base, dtype=bool)
                    ic_veto_mask = np.asarray(vmask, dtype=bool)
                    ic_normal_gate = np.asarray(gate, dtype=bool)

    # precomputed signals (param-independent) sliced to the window; else compute on the slice
    si = sig_int[lo:hi] if sig_int is not None else signals_to_int(_sig.decision_signals(d, box))

    # End-of-day cap targets. eod_targets returns indices INTO THE ARRAY IT IS GIVEN, so it must be built
    # on the SLICED d1 (the same frame handed to fast_backtest) — building it on the full df1 would point
    # at the wrong bars. Param-independent given (slice, margin) ⇒ memoised across trials of the same fold.
    m1_dates = d1["Date"].to_numpy()

    # News-veto force-exit targets. Same sharp edge as eod_targets: news_exit_targets returns indices
    # INTO THE ARRAY IT IS GIVEN, so it must be built on the SLICED d1 (the frame handed to
    # fast_backtest), not the full df1. Param-independent given (slice, pre) ⇒ memoised across trials.
    news_target = None
    if params.get("news_veto"):
        nk = (_slice_sig(d, d1, bar_duration), int(params.get("news_pre_min", 0)),
              id(params.get("_news_calendar_override")))
        if nk not in _NEWS_TGT_MEMO:
            from optimize.fundamentals import window as _w
            _NEWS_TGT_MEMO[nk] = _w.news_exit_targets(
                d1, _news_calendar(params), int(params.get("news_pre_min", 0)))
        news_target = _NEWS_TGT_MEMO[nk]

    eod_target = session_last = None
    if cap_mode in ("eod", "both"):
        ek = (_slice_sig(d, d1, bar_duration), eod_margin)
        if ek not in _EOD_MEMO:
            from optimize.trading_days import eod_targets
            _EOD_MEMO[ek] = eod_targets(m1_dates, eod_margin)
        eod_target, session_last = _EOD_MEMO[ek]
        if eod_target is None:
            # fast_engine would silently fall back to a bars cap here — refuse instead of mis-scoring.
            raise ValueError(f"cap_mode={cap_mode!r} requires end-of-day targets, but none could be built")

    cand = fast_backtest(
        d["Date"].to_numpy(), d["Close"].to_numpy(float), si, gate,
        m1_dates, d1["High"].to_numpy(float),
        d1["Low"].to_numpy(float), d1["Close"].to_numpy(float),
        sl_soft, sl_hard, tp, flip, cap_1min=cap_1min,
        cap_mode=cap_mode, eod_target=eod_target, session_last=session_last,
        intracandle_gate_by_dir=ic_gate_by_dir, intracandle_vol_gate=ic_vol_gate,
        intracandle_veto_mask=ic_veto_mask, intracandle_normal_gate=ic_normal_gate,
        intracandle_max_wait=int(params.get("intracandle_max_wait", 240)),
        intracandle_force_close=bool(params.get("intracandle_force_close", False)),
        news_target=news_target,
        news_profit_exempt_mult=float(params.get("news_profit_exempt_mult", 1.0)),
        **_split)
    # fast_backtest returns completed trades already in entry order (no OPEN trades)

    # Global-HWM drawdown breaker overlay (identical math to strategy.build_payload).
    use_brk = dd_limit > 0
    peak = eq = 0.0
    locked = False
    cd = 0
    skipped = 0
    n_locks = 0
    taken = []
    for t in cand:
        pnl = float(t["pnl_points"]) * pv
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False           # keep GLOBAL high-water mark (no peak reset)
            else:
                skipped += 1
                continue
        eq += pnl
        peak = max(peak, eq)
        dd = peak - eq
        taken.append({"pnl": pnl, "eq": eq, "dd": dd,
                      "year": pd.Timestamp(t["exit_time"]).year, "entry_idx": int(t["entry_idx"])})
        if use_brk and dd >= dd_limit:
            locked = True
            cd = cooldown
            n_locks += 1

    if not taken:
        out = _empty(); out["n_candidates"] = len(cand); out["n_skipped_breaker"] = skipped
        return out

    pnl_arr = np.array([t["pnl"] for t in taken])
    yr = np.array([t["year"] for t in taken])
    eq_arr = np.array([t["eq"] for t in taken])
    uw = np.maximum.accumulate(eq_arr) - eq_arr
    wins = pnl_arr[pnl_arr > 0]; losses = pnl_arr[pnl_arr < 0]
    # S0: warmup-attributed no-entry-streak (additive — never changes existing values).
    from optimize.no_entry import no_entry_metrics
    from indicators import library as _lib
    _specs = [s for s in params.get("indicators", []) if s.get("enabled")]
    try:
        _warm_native = max((i.warmup_bars() for i in _lib.from_specs(_specs)), default=0)
    except Exception:
        _warm_native = 0
    _bar_min = bar_duration.total_seconds() / 60.0
    # ind_1min => warmup is in 1-MIN candles -> convert to decision bars; else already decision bars.
    _warm_dec = math.ceil(_warm_native / _bar_min) if params.get("ind_1min") else int(_warm_native)
    _ne = no_entry_metrics([t["entry_idx"] for t in taken], n_bars=len(df_dec),
                           warmup_decision_bars=_warm_dec, bar_hours=bar_duration.total_seconds() / 3600.0)
    _ne["data_footprint_candles"] = int(_warm_native)        # issue 3: live-trader history buffer
    _ne["warmup_frame"] = "1min" if params.get("ind_1min") else "decision"
    return dict(
        pnl=float(pnl_arr.sum()),
        pnl_2025=float(pnl_arr[yr == config.YEARS[0]].sum()),
        pnl_2026=float(pnl_arr[yr == config.YEARS[1]].sum()),
        max_dd=float(uw.max()),
        n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped,
        exposure=round(100 * len(taken) / max(len(cand), 1), 1),
        win=round(100 * (pnl_arr > 0).mean(), 1),
        pf=(round(float(wins.sum() / abs(losses.sum())), 2)
            if len(losses) and losses.sum() != 0 else None),
        payoff=(round(float(wins.mean() / abs(losses.mean())), 2)
                if len(wins) and len(losses) else None),   # avg win / |avg loss| (reward-to-risk)
        n_locks=n_locks,
        trades=taken,
        **_ne,
    )


def _empty() -> dict:
    return dict(pnl=0.0, pnl_2025=0.0, pnl_2026=0.0, max_dd=0.0, n_taken=0, n_candidates=0,
                n_skipped_breaker=0, exposure=0.0, win=0.0, pf=None, n_locks=0, trades=[])
