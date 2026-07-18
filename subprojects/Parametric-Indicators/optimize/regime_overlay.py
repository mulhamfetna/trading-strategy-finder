"""EXPERIMENTAL regime size-ramp overlay for the dashboard — ADDITIVE and OFF BY DEFAULT.

⚠️  CANDIDATE, NOT a confirmed edge. The regime *ordering* is validated (beats 96% of random regime→size
maps; helps 4/5 purged folds) but the DOLLAR magnitude is unconfirmed on the n=1 (2024-26) book — bootstrap
90% CI [-$21k, +$61k] includes zero. See subprojects/regime-edge/docs/SECOND_TEST.md.

This module NEVER mutates the payload's existing numbers. `overlay_from_log()` returns a separate dict that
the dashboard renders as its own clearly-labelled experimental card. Any failure returns None (the endpoint
must be unaffected).

Rule: per entry, size multiplier = linear ramp over the day's causal HMM regime vol-rank (calmest lo →
most turbulent hi), then normalized so max-drawdown matches the flat book (equal-risk).
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

_REGIME_CSV = Path(__file__).resolve().parents[2] / "regime-edge" / "data" / "nq_daily_regime.csv"
_CACHE = None


def _day(t):
    """Log rows carry `time` as a Unix EPOCH int (not a date string) — map it to the naive YYYY-MM-DD the
    regime artifact is keyed on. Accepts a date-ish string too."""
    if t is None:
        return ""
    try:
        if isinstance(t, (int, float)) or (isinstance(t, str) and t.strip().isdigit()):
            return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""
    return str(t)[:10]


def _regime_map():
    """(date -> regime rank, n_regimes); ({}, 0) when the artifact is missing."""
    global _CACHE
    if _CACHE is None:
        m, n = {}, 0
        try:
            with open(_REGIME_CSV) as fh:
                for r in csv.DictReader(fh):
                    m[str(r["date"])[:10]] = int(r["regime"])
                    n = int(r["n_regimes"])
        except Exception:
            m, n = {}, 0
        _CACHE = (m, n)
    return _CACHE


def _dd(pnls):
    eq = peak = 0.0
    worst = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        worst = max(worst, peak - eq)
    return worst


def _stats(pnls):
    tot = sum(pnls)
    d = _dd(pnls)
    return {"pnl": tot, "dd": d, "ret_dd": (tot / d) if d else None,
            "win": (100.0 * sum(1 for p in pnls if p > 0) / len(pnls)) if pnls else 0.0}


def overlay_from_log(log, lo: float = 0.5, hi: float = 1.5, instrument: str = "NQ"):
    """Return the experimental overlay readout for a causal log, or None if unavailable.

    Never raises. Only defined for NQ (the regime artifact is NQ-derived)."""
    try:
        if str(instrument).upper() != "NQ":
            return None
        rmap, n = _regime_map()
        if not rmap or n < 2:
            return None
        ramp = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
        flat, scaled, matched = [], [], 0
        for row in log or []:
            if (row.get("decision") if isinstance(row, dict) else getattr(row, "decision", None)) != "entry":
                continue
            pnl = row.get("pnl") if isinstance(row, dict) else getattr(row, "pnl", None)
            t = row.get("time") if isinstance(row, dict) else getattr(row, "time", None)
            if pnl is None:
                continue
            pnl = float(pnl)
            r = rmap.get(_day(t))
            flat.append(pnl)
            if r is None:
                scaled.append(pnl)
            else:
                matched += 1
                scaled.append(ramp[min(max(r, 0), n - 1)] * pnl)
        if len(flat) < 20 or matched == 0:
            return None
        b, g = _stats(flat), _stats(scaled)
        # normalize to EQUAL RISK: hold max-drawdown at the flat book's
        k = (b["dd"] / g["dd"]) if g["dd"] else 1.0
        eq = [p * k for p in scaled]
        e = _stats(eq)
        return {
            "enabled": True, "experimental": True, "ramp": [lo, hi], "n_regimes": n,
            "trades": len(flat), "matched_days": matched,
            "flat": {"pnl": round(b["pnl"], 2), "dd": round(b["dd"], 2),
                     "ret_dd": round(b["ret_dd"], 3) if b["ret_dd"] else None},
            "overlay": {"pnl": round(e["pnl"], 2), "dd": round(e["dd"], 2),
                        "ret_dd": round(e["ret_dd"], 3) if e["ret_dd"] else None,
                        "scale": round(k, 4)},
            "delta_equal_risk": round(e["pnl"] - b["pnl"], 2),
            "note": ("EXPERIMENTAL CANDIDATE — magnitude UNCONFIRMED (n=1 book; bootstrap 90% CI "
                     "[-$21k,+$61k] includes zero). Equal-risk: max-DD held at the flat book's. "
                     "Does not change any deployed number."),
        }
    except Exception:
        return None
