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


def veto_mask(df, box, indicators):
    """Per-decision-bar veto mask (Q5: veto lives in the gate). True where any ENABLED veto-capable
    (mode∈{veto,both}) indicator votes VETO, read at the just-closed signal bar and aligned to the
    entry bar (mask[idx] = veto at idx-1; idx 0 = False). No veto indicators ⇒ all False (parity)."""
    from .base import VETO
    n = len(df)
    out = np.zeros(n, dtype=bool)
    vetoers = [ind for ind in indicators
               if ind.config.enabled and ind.config.mode in ("veto", "both")]
    if not vetoers:
        return out
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    raw = np.zeros(n, dtype=bool)
    for ind in vetoers:
        raw |= (ind.vote(ctx, bdir) == VETO)
    out[1:] = raw[:-1]                            # align to the entry bar (veto read at idx-1)
    return out


def confirm_mask(df, box, indicators, k):
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
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    cc = np.zeros(n, dtype=np.int64)
    for ind in confirmers:
        cc += (ind.vote(ctx, bdir) == CONFIRM).astype(np.int64)
    ok = cc >= k_eff
    out[1:] = ok[:-1]                             # align to the entry bar (confirms read at idx-1)
    return out


def build_layer(df, box, indicators, k, vol_gate,
                retrace_amount=0.0, retrace_unit="atr_mult", wait_bars=0):
    """Assemble the full indicator layer for a run (Q5 split):
      gate     = vol_gate ∧ ¬veto_mask   (eligibility)
      resolver = build_entry_resolver(confirm-capable indicators, k, GLOBAL retrace+wait)
      vmask    = veto_mask(...)           (passed to the engine for live carry-abort)
    retrace_amount/unit and wait_bars are GLOBAL (one value each, applied to ALL indicators).
    Returns (gate, resolver, vmask). All-off ⇒ gate==vol_gate, vmask all-False, resolver immediate."""
    vg = np.asarray(vol_gate, dtype=bool)
    vmask = veto_mask(df, box, indicators)
    gate = vg & ~vmask
    resolver = build_entry_resolver(df, box, indicators, k,
                                    retrace_amount=retrace_amount, retrace_unit=retrace_unit,
                                    wait_bars=wait_bars)
    return gate, resolver, vmask


def build_entry_resolver(df, box, indicators, k,
                         retrace_amount=0.0, retrace_unit="atr_mult", wait_bars=0):
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
    votes = {id(ind): ind.vote(ctx, bdir) for ind in confirmers}
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
