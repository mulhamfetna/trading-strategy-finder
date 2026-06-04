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
from .timing import resolve_retrace_entry


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


def build_layer(df, box, indicators, k, vol_gate):
    """Assemble the full indicator layer for a run (Q5 split):
      gate     = vol_gate ∧ ¬veto_mask   (eligibility)
      resolver = build_entry_resolver(confirm-capable indicators, k)   (K-count + fill price)
      vmask    = veto_mask(...)           (passed to the engine for live carry-abort)
    Returns (gate, resolver, vmask). All-off ⇒ gate==vol_gate, vmask all-False, resolver immediate."""
    from .base import VETO  # local to avoid noise
    vg = np.asarray(vol_gate, dtype=bool)
    vmask = veto_mask(df, box, indicators)
    gate = vg & ~vmask
    resolver = build_entry_resolver(df, box, indicators, k)
    return gate, resolver, vmask


def build_entry_resolver(df, box, indicators, k):
    """Build the engine `entry_resolver` closure implementing the live-B1 confirm + retrace fill.

    For each entry the engine attempts (decision bar idx, signal from the just-closed bar idx-1):
      • confirming indicators = enabled, confirm-capable (mode∈{confirm,both}) indicators whose LIVE
        wait-debounced vote at bar idx-1 is CONFIRM (B1 — read at the just-closed bar);
      • each contributes a retrace level (signal_close ∓ r; r in points or atr_mult);
      • effective K = min(k, #confirm-capable-enabled) (Q2 waive); k_eff==0 ⇒ immediate fill at close;
      • the trade fills at the K-th confirm's level via resolve_retrace_entry over the window's 1-min
        bars, or None (unfilled → engine skips, re-evaluates next bar).
    Veto is NOT handled here — it lives in the composite gate (Q5). Returns (fill_ts, fill_price)|None.

    NOTE (scope): within-window per signal bar (the dominant case). Carrying an armed setup across
    HOLD decision bars (full B1 §C) is a documented follow-up; the per-bar re-evaluation already
    gives live readings on every signalling bar.
    """
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    confirmers = [ind for ind in indicators
                  if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    n_confirm = len(confirmers)
    votes = {id(ind): ind.vote(ctx, bdir) for ind in confirmers}
    atr = classic.atr(ctx.high, ctx.low, ctx.close, 14)

    def _offset(ind, bar):
        r = float(ind.config.retrace_amount)
        if ind.config.retrace_unit == "atr_mult":
            a = atr[bar]
            r = r * (a if np.isfinite(a) else 0.0)
        return r

    def resolver(idx, direction, signal_close, signal_idx, ts, sub_bars):
        # votes read LIVE at the CURRENT just-closed bar (idx-1) = B1; levels anchor to signal_close.
        k_eff = min(int(k), n_confirm)
        if k_eff <= 0:
            return (ts, signal_close)            # Q2: no confirm requirement ⇒ immediate fill
        sig_bar = idx - 1
        long = direction == "long"
        n_imm = 0                                 # retrace=0 confirms (live at bar 0, fill at close)
        pull = []                                 # retrace>0 confirm levels (need a pullback touch)
        for ind in confirmers:
            if votes[id(ind)][sig_bar] == CONFIRM:
                r = _offset(ind, sig_bar)
                if r <= 0:
                    n_imm += 1
                else:
                    pull.append(signal_close - r if long else signal_close + r)
        if n_imm + len(pull) < k_eff:
            return None                           # not enough confirms this signal ⇒ no entry
        if k_eff <= n_imm:
            return (ts, signal_close)             # K-th confirm is immediate ⇒ fill now at close
        need = k_eff - n_imm                       # remaining confirms must come from pullbacks
        d = 1 if long else -1
        return resolve_retrace_entry(d, signal_close, pull,
                                     sub_bars["Low"].to_numpy(float),
                                     sub_bars["High"].to_numpy(float),
                                     sub_bars["Date"].to_numpy(), need)

    return resolver
