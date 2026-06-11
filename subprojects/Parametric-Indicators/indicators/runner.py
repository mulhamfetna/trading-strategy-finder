"""Wire the indicator confirmation layer into the box strategy's per-bar entry gate.

The engine (engine.SimpleStrategy) enters at decision bar `idx` using the signal of the JUST-CLOSED
bar `idx-1`. So an indicator's confirm/veto for that entry must be read from bar `idx-1` (causal).
`composite_gate` builds the per-bar indicator allow-mask (aligned to the signal bar) and ANDs it with
the existing volatility gate.

Parity: with no ENABLED indicator the allow-mask is all-True ⇒ the composite gate == the vol gate
exactly, so the engine reproduces today's behaviour (regression-locked in tests/test_integration.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import classic
from .base import CONFIRM, MarketContext
from .confirm import build_gate
from .timing import resolve_retrace_entry, resolve_entry_1min


def market_context(df: pd.DataFrame) -> MarketContext:
    """Build a MarketContext from a decision-timeframe OHLCV frame (session = calendar day)."""
    sess = pd.to_datetime(df["Date"]).dt.normalize().astype("int64").to_numpy()
    return MarketContext(
        open=df["Open"].to_numpy(float), high=df["High"].to_numpy(float),
        low=df["Low"].to_numpy(float), close=df["Close"].to_numpy(float),
        volume=df["Volume"].to_numpy(float) if "Volume" in df.columns else np.zeros(len(df)),
        session_id=sess,
    )


def box_direction_int(df: pd.DataFrame, box: pd.DataFrame) -> np.ndarray:
    """Per-decision-bar box signal as int8 (+1 long / -1 short / 0 hold)."""
    from optimize import signals as _sig
    from optimize.fast_engine import signals_to_int
    return signals_to_int(_sig.decision_signals(df, box))


# --- optional 1-MINUTE indicator source -------------------------------------------------------
# When supplied, indicators compute their direction on the 1-minute frame and each decision bar
# reads the value of its LAST CLOSED 1-minute candle (causal). The box trigger, entry cadence and
# exits stay on the decision timeframe; only the indicators' data source changes. Warm-up then
# counts 1-MINUTE candles. Build one with indicator_source_1min(df_dec, df1, bar_td) and pass it as
# `src=` to veto_mask / confirm_mask / build_entry_resolver / build_layer. src=None ⇒ decision-TF
# behaviour (unchanged; the optimiser + parity tests never pass src).

def _decbar_1min_index(dec_dates: np.ndarray, min_dates: np.ndarray, bar_td: pd.Timedelta) -> np.ndarray:
    """For each decision bar i, the index of the LAST 1-minute bar inside its window
    [start_i, start_i + bar_td) — the 1-minute candle that closes that decision bar. -1 if none."""
    starts = np.asarray(dec_dates, dtype="datetime64[ns]")
    md = np.asarray(min_dates, dtype="datetime64[ns]")
    ends = starts + np.timedelta64(int(bar_td / pd.Timedelta(minutes=1)), "m")
    j = np.searchsorted(md, ends, side="left") - 1          # last 1-min bar strictly before window end
    jj = np.clip(j, 0, len(md) - 1)
    in_win = (j >= 0) & (md[jj] >= starts)                  # must actually fall in this bar's window
    return np.where(in_win, j, -1)


def indicator_source_1min(df_dec: pd.DataFrame, df1: pd.DataFrame, bar_td: pd.Timedelta):
    """Return a src tuple (ctx_1min, j_idx) for the 1-minute indicator mode (see note above)."""
    ctx_1m = market_context(df1)
    j_idx = _decbar_1min_index(df_dec["Date"].to_numpy(), df1["Date"].to_numpy(), bar_td)
    return (ctx_1m, j_idx)


def _vote_from_1min(ind, ctx_1m, j_idx, box_dir) -> np.ndarray:
    """Per-decision-bar vote for `ind` using its direction computed on the 1-MINUTE context and
    sampled at each decision bar's closing 1-minute candle, compared to the decision box direction.
    Mirrors base.Indicator.vote exactly (including the warm-up, now in 1-MINUTE candles)."""
    from .base import CONFIRM, VETO, HOLD, BOTH
    # Step E (task #210): for indicators that support it (OrderBlock), tell directions() the exact
    # 1-minute bars whose value will be READ (the decision bars' sampled candles), so it computes its
    # costly per-bar overlap signal only there. State still advances every bar ⇒ identical at those bars.
    if getattr(ind, "_supports_signal_at", False):
        cdir1, vdir1 = ind.directions(ctx_1m, signal_at=j_idx[j_idx >= 0])
    else:
        cdir1, vdir1 = ind.directions(ctx_1m)
    cdir1 = np.asarray(cdir1).copy(); vdir1 = np.asarray(vdir1).copy()
    w = min(int(ind.warmup_bars()), len(cdir1))             # warm-up counts 1-minute candles here
    if w > 0:
        cdir1[:w] = 0; vdir1[:w] = 0
    n = len(j_idx)
    cdir = np.zeros(n, dtype=np.int8); vdir = np.zeros(n, dtype=np.int8)
    ok = j_idx >= 0
    cdir[ok] = cdir1[j_idx[ok]]; vdir[ok] = vdir1[j_idx[ok]]
    bd = np.asarray(box_dir); has = bd != HOLD
    would_confirm = ((cdir == bd) | (cdir == BOTH)) & has
    would_veto = ((vdir == bd) | (vdir == BOTH)) & has
    out = np.zeros(n, dtype=np.int8)
    if ind.config.mode in ("confirm", "both"):
        out[would_confirm] = CONFIRM
    if ind.config.mode in ("veto", "both"):
        out[would_veto] = VETO
    return out


def _ind_vote(ind, ctx, bdir, src=None) -> np.ndarray:
    """Per-decision-bar vote: decision-TF (ind.vote) when src is None, else 1-minute-sourced."""
    if src is None:
        return ind.vote(ctx, bdir)
    ctx_1m, j_idx = src
    return _vote_from_1min(ind, ctx_1m, j_idx, bdir)


def composite_gate(vol_gate, df, box, indicators, k):
    """vol_gate: per-bar bool (engine idx). indicators: list of Indicator instances (enabled+disabled).
    Returns (gate, votes, active): gate = vol_gate ∧ (indicator allow, aligned to the signal bar)."""
    vg = np.asarray(vol_gate, dtype=bool)
    n = len(vg)
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    allow, votes, active = build_gate(ctx, bdir, indicators, k, base_gate=None)
    # Entry at idx uses the just-closed bar idx-1, so align the allow-mask forward by one bar.
    # idx 0 can never enter (engine warm-up) ⇒ leave True so all-off ⇒ gate == vol_gate exactly.
    aligned = np.ones(n, dtype=bool)
    aligned[1:] = allow[:-1]
    return vg & aligned, votes, active


def compute_votes(df, box, indicators, src=None) -> dict:
    """Per-decision-bar vote array for every ENABLED indicator, keyed by id(ind). Computed ONCE so
    the veto gate, the confirm resolver and the attribution all reuse it (no 3× recompute). Disabled
    indicators are skipped entirely (they don't trade and aren't worth computing — esp. the costly
    SMC ones on the 1-minute frame)."""
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    return {id(ind): _ind_vote(ind, ctx, bdir, src)
            for ind in indicators if ind.config.enabled}


def veto_mask(df, box, indicators, src=None, votes=None):
    """Per-decision-bar veto mask (Q5: veto lives in the gate). True where any ENABLED veto-capable
    (mode∈{veto,both}) indicator votes VETO, read at the just-closed signal bar and aligned to the
    entry bar (mask[idx] = veto at idx-1; idx 0 = False). No veto indicators ⇒ all False (parity).
    src routes the reading to the 1-minute frame; votes (optional) reuses a precomputed vote dict."""
    from .base import VETO
    n = len(df)
    out = np.zeros(n, dtype=bool)
    vetoers = [ind for ind in indicators
               if ind.config.enabled and ind.config.mode in ("veto", "both")]
    if not vetoers:
        return out
    if votes is None:
        votes = compute_votes(df, box, vetoers, src)
    raw = np.zeros(n, dtype=bool)
    for ind in vetoers:
        raw |= (votes[id(ind)] == VETO)
    out[1:] = raw[:-1]                            # align to the entry bar (veto read at idx-1)
    return out


def confirm_mask(df, box, indicators, k, src=None, votes=None):
    """Per-decision-bar CONFIRM gate (vectorised, for the optimiser fast path — WS-I.7).
    True where ≥ K_eff enabled confirm-capable (mode∈{confirm,both}) indicators vote CONFIRM at the
    just-closed signal bar, aligned to the entry bar (mask[idx] = confirms at idx-1; idx 0 = True).
    K_eff = min(k, #confirm-capable-enabled); no confirmers ⇒ all True (no requirement ⇒ parity).

    This is the immediate-fill confirmation as a pure gate — it does NOT model retrace/wait fill or
    the live-carry-across-HOLD-bars resolver (those stay in the exact engine / dashboard path)."""
    n = len(df)
    out = np.ones(n, dtype=bool)
    confirmers = [ind for ind in indicators
                  if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    k_eff = min(int(k), len(confirmers))
    if k_eff <= 0:
        return out                                # no confirm requirement (parity)
    if votes is None:
        votes = compute_votes(df, box, confirmers, src)
    cc = np.zeros(n, dtype=np.int64)
    for ind in confirmers:
        cc += (votes[id(ind)] == CONFIRM).astype(np.int64)
    ok = cc >= k_eff
    out[1:] = ok[:-1]                             # align to the entry bar (confirms read at idx-1)
    return out


def build_layer(df, box, indicators, k, vol_gate,
                retrace_amount=0.0, retrace_unit="atr_mult", wait_bars=0,
                src=None, votes=None, veto_as_flip=False):
    """Assemble the full indicator layer for a run (Q5 split):
      gate     = vol_gate ∧ ¬veto_mask   (eligibility)
      resolver = build_entry_resolver(confirm-capable indicators, k, GLOBAL retrace+wait)
      vmask    = veto_mask(...)           (passed to the engine for live carry-abort)
    retrace_amount/unit and wait_bars are GLOBAL (one value each, applied to ALL indicators).
    Returns (gate, resolver, vmask). All-off ⇒ gate==vol_gate, vmask all-False, resolver immediate."""
    vg = np.asarray(vol_gate, dtype=bool)
    if votes is None:                            # compute each enabled indicator's vote ONCE, reuse
        votes = compute_votes(df, box, indicators, src)
    vmask = veto_mask(df, box, indicators, src=src, votes=votes)
    # default: veto removes the bar from the gate (drop). veto_as_flip: leave the gate vol-only so
    # vetoed bars stay eligible — the engine reverses their direction instead of dropping them.
    gate = vg if veto_as_flip else (vg & ~vmask)
    resolver = build_entry_resolver(df, box, indicators, k,
                                    retrace_amount=retrace_amount, retrace_unit=retrace_unit,
                                    wait_bars=wait_bars, src=src, votes=votes)
    return gate, resolver, vmask


def build_entry_resolver(df, box, indicators, k,
                         retrace_amount=0.0, retrace_unit="atr_mult", wait_bars=0, src=None, votes=None):
    """Build the engine `entry_resolver` closure: live-B1 confirm count + GLOBAL retrace/wait fill.

    GLOBAL controls (one value each, applied to ALL indicators — WS-I notes #3/#4):
      • retrace_amount/retrace_unit → ONE shared pullback level (signal_close ∓ r; r in points, or
        atr_mult × ATR[signal_bar]);
      • wait_bars → a count of **1-minute** bars to wait inside the armed window before filling.

    For each entry the engine attempts (decision bar idx; signal from the just-closed bar idx-1):
      • confirming indicators = enabled, confirm-capable (mode∈{confirm,both}) indicators whose LIVE
        vote at bar idx-1 is CONFIRM (B1 — read at the just-closed bar);
      • effective K = min(k, #confirm-capable-enabled) (Q2 waive); k_eff==0 ⇒ immediate fill at close;
      • if #confirm ≥ k_eff the trade fills via the single global level + 1-min wait
        (timing.resolve_entry_1min over the window's 1-min bars), else None (unfilled → re-evaluate).
    Veto is NOT handled here — it lives in the composite gate (Q5). Returns (fill_ts, fill_price)|None.
    """
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    confirmers = [ind for ind in indicators
                  if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    n_confirm = len(confirmers)
    if votes is None:
        votes = {id(ind): _ind_vote(ind, ctx, bdir, src) for ind in confirmers}
    atr = classic.atr(ctx.high, ctx.low, ctx.close, 14)
    g_amount = float(retrace_amount)
    g_atr = (retrace_unit == "atr_mult")
    g_wait = int(wait_bars)

    def _offset(bar):
        if g_amount <= 0:
            return 0.0
        if g_atr:
            a = atr[bar]
            return g_amount * (a if np.isfinite(a) else 0.0)
        return g_amount

    def resolver(idx, direction, signal_close, signal_idx, ts, sub_bars):
        # votes read LIVE at the CURRENT just-closed bar (idx-1) = B1; the level anchors to signal_close.
        k_eff = min(int(k), n_confirm)
        if k_eff <= 0:
            return (ts, signal_close)            # Q2: no confirm requirement ⇒ immediate fill
        sig_bar = idx - 1
        nconf = sum(1 for ind in confirmers if votes[id(ind)][sig_bar] == CONFIRM)
        if nconf < k_eff:
            return None                           # not enough confirms this signal ⇒ no entry
        r = _offset(sig_bar)                       # ONE global retrace offset (points)
        if r <= 0 and g_wait <= 0:
            return (ts, signal_close)             # immediate fill at close (parity-style)
        d = 1 if direction == "long" else -1
        return resolve_entry_1min(d, signal_close, r, g_wait,
                                  sub_bars["Low"].to_numpy(float),
                                  sub_bars["High"].to_numpy(float),
                                  sub_bars["Date"].to_numpy())

    return resolver
