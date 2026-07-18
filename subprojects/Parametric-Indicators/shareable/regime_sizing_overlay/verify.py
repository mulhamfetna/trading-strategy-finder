#!/usr/bin/env python3
"""Reproduce the regime size-ramp candidate's documented numbers TO THE DOLLAR, from the bundled fixture.

Mirrors the champion bundle's guarantee: run it and every headline figure in the config/report must match
exactly. Any mismatch is a FAIL (loud), not a warning.

    python3 verify.py                         # uses configs/NQ_regime_sizing.json + bundled reference book
    python3 verify.py --config <cfg.json> --book <entries.csv> --regime <regime.csv>
"""
from __future__ import annotations
import argparse, csv, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _day(t):
    t = str(t).strip()
    if t.isdigit():
        return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime("%Y-%m-%d")
    return t[:10]


def _dd(pnls):
    eq = peak = worst = 0.0
    for p in pnls:
        eq += p; peak = max(peak, eq); worst = max(worst, peak - eq)
    return worst


def _stats(pnls):
    tot = sum(pnls); d = _dd(pnls)
    return tot, d, (tot / d if d else float("nan"))


def run(cfg_path: Path, book_path: Path, regime_path: Path):
    cfg = json.loads(cfg_path.read_text())
    pre, exp = cfg["preset"], cfg["expected"]

    reg, n = {}, 0
    with regime_path.open() as fh:
        for r in csv.DictReader(fh):
            reg[str(r["date"])[:10]] = int(r["regime"]); n = int(r["n_regimes"])

    times, pnls = [], []
    with book_path.open() as fh:
        for r in csv.DictReader(fh):
            times.append(r.get("datetime") or r.get("time")); pnls.append(float(r["pnl"]))

    lo, hi = float(pre["ramp_lo"]), float(pre["ramp_hi"])
    ramp = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    scaled = [ramp[reg[_day(t)]] * p if _day(t) in reg else p for t, p in zip(times, pnls)]

    f_pnl, f_dd, f_r = _stats(pnls)
    s_pnl, s_dd, s_r = _stats(scaled)
    k = (f_dd / s_dd) if s_dd else 1.0                       # equal-risk normalization
    eq = [p * k for p in scaled]
    e_pnl, e_dd, e_r = _stats(eq)

    checks = [
        ("trades",             len(pnls),        exp["trades"],            0),
        ("flat P/L",           f_pnl,            exp["flat_pnl"],          1.0),
        ("flat maxDD",         f_dd,             exp["flat_dd"],           1.0),
        ("flat Return/DD",     round(f_r, 2),    exp["flat_ret_dd"],       0.01),
        ("overlay P/L",        e_pnl,            exp["overlay_pnl"],       1.0),
        ("overlay maxDD",      e_dd,             exp["overlay_dd"],        1.0),
        ("overlay Return/DD",  round(e_r, 2),    exp["overlay_ret_dd"],    0.01),
        ("Δ at equal risk",    e_pnl - f_pnl,    exp["delta_equal_risk"],  1.0),
        ("equal-risk scale",   round(k, 4),      exp["equal_risk_scale"],  0.001),
    ]
    print(f"=== {cfg['id']} — reproduce to the dollar ===")
    print(f"    {cfg['status']}\n")
    ok = True
    for name, got, want, tol in checks:
        good = abs(float(got) - float(want)) <= tol
        ok &= good
        g = f"{got:,.2f}" if isinstance(got, float) else f"{got:,}"
        w = f"{want:,.2f}" if isinstance(want, float) else f"{want:,}"
        print(f"  {'PASS' if good else 'FAIL'}  {name:20} got {g:>14}   expected {w:>14}")
    print(f"\n  RESULT: {'✅ ALL MATCH — reproduces to the dollar' if ok else '❌ MISMATCH'}")
    print(f"\n  ⚠ {cfg['validation']['verdict']}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "configs" / "NQ_regime_sizing.json"))
    ap.add_argument("--book", default=str(HERE / "reference" / "nq_2426_fusion_entries.csv"))
    ap.add_argument("--regime", default=str(HERE / "regime" / "nq_daily_regime.csv"))
    a = ap.parse_args()
    raise SystemExit(run(Path(a.config), Path(a.book), Path(a.regime)))


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
