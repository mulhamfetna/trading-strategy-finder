"""E-D1 — the two-calendar forecast layer (ROUTING pattern). docs/ED1-PREREGISTRATION.md.

The calendar-augmented volatility context the live HAR gate is blind to, composed by
ROUTING (the E-X2v2 insight): the FU-11-certified model on macro event bars, the
E-X1-certified model on earnings bars, plain HAR-LS elsewhere. Information layer only —
no trading consumer, no engine import.

    python3 -m src.deploy.two_calendar_forecast verify   --instrument NQ
    python3 -m src.deploy.two_calendar_forecast scramble --instrument NQ
    python3 -m src.deploy.two_calendar_forecast forecast --instrument NQ --now "2026-02-01" \
        [--horizon-days 30] [--earnings-dates file.csv]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
PI = REPO / "subprojects" / "Parametric-Indicators"
FUND = PI / "optimize" / "fundamentals"
EARN = PI / "optimize" / "earnings"
for p_ in (str(PI), str(FUND)):
    sys.path.insert(0, p_)

TRAIN_END = pd.Timestamp("2024-01-01")
MINUTES, SEED, N_SHUF = 60, 20260820, 20


def _machinery():
    from extended_data import load_1m_extended
    from volatility import compute_rv_pts
    from optimize.fundamentals.fu11_stage1 import (qlike, build_frame, har_regressors,
                                                   ols_predict)
    from optimize.earnings.ex2_joint_forecast import macro_terms, earn_terms
    return (load_1m_extended, compute_rv_pts, qlike, build_frame, har_regressors,
            ols_predict, macro_terms, earn_terms)


def _fit(inst: str):
    """Deterministic rebuild of the two certified models + routing masks."""
    (load_1m, rv_pts, qlike, build_frame, har_reg, ols, macro_terms, earn_terms) \
        = _machinery()
    df1 = load_1m(inst).sort_values("Date").reset_index(drop=True)
    frame = build_frame(df1, MINUTES)
    rv = pd.Series(rv_pts(frame, df1, bar_minutes=MINUTES)).ffill().bfill().to_numpy()
    dates = frame["Date"]
    starts = frame["Date"].to_numpy()
    m_dum, m_pw = macro_terms(inst, df1, starts)
    e_dum, e_pw = earn_terms(inst, starts)
    Xh = har_reg(rv)
    valid = np.isfinite(Xh).all(1) & np.isfinite(rv)
    train = valid & (dates < TRAIN_END).to_numpy()
    test = valid & (dates >= TRAIN_END).to_numpy()
    pB, bB = ols(Xh, rv, train)
    pCm, bCm = ols(np.c_[Xh, m_dum, m_pw], rv, train)
    pCe, bCe = ols(np.c_[Xh, e_dum, e_pw], rv, train)
    routed = np.where(m_dum > 0, pCm, np.where(e_dum > 0, pCe, pB))
    return dict(rv=rv, dates=dates, test=test, m_dum=m_dum, e_dum=e_dum,
                pB=pB, pCm=pCm, pCe=pCe, routed=routed, qlike=qlike,
                betas={"B": bB.tolist(), "Cm": bCm.tolist(), "Ce": bCe.tolist()},
                Xh=Xh, train=train, m_pw=m_pw, e_pw=e_pw, ols=ols, starts=starts)


def verify(inst: str) -> int:
    f = _fit(inst)
    q = f["qlike"]
    mbar = f["test"] & (f["m_dum"] > 0)
    ebar = f["test"] & (f["e_dum"] > 0)
    ubar = f["test"] & ((f["m_dum"] > 0) | (f["e_dum"] > 0))
    qm = float(np.mean(q(f["rv"][mbar], f["routed"][mbar])))
    qe = float(np.mean(q(f["rv"][ebar], f["routed"][ebar])))
    qu = float(np.mean(q(f["rv"][ubar], f["routed"][ubar])))
    ref_m = json.load(open(FUND / f"fu11_stage1_{inst}_60m.json"))["scores"]["C_fused"]["event"]["qlike"]
    ref_e = json.load(open(EARN / "data" / f"ex1_result_{inst}.json"))["scores"]["C"]["event"]
    ident_u = (qm * mbar.sum() + qe * ebar.sum()) / ubar.sum()
    dm, de, du = abs(qm - ref_m), abs(qe - ref_e), abs(qu - ident_u)
    ok = dm < 1e-9 and de < 1e-9 and du < 1e-9
    print(f"E-D1 verify {inst}: macro {qm:.6f} vs committed {ref_m:.6f} (Δ{dm:.1e}) · "
          f"earn {qe:.6f} vs {ref_e:.6f} (Δ{de:.1e}) · union identity Δ{du:.1e} -> "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 1


def scramble(inst: str) -> int:
    f = _fit(inst)
    q = f["qlike"]
    rng = np.random.default_rng(SEED)
    out_ok = True
    for cal, dum, pw in (("macro", f["m_dum"], f["m_pw"]),
                         ("earn", f["e_dum"], f["e_pw"])):
        bar = f["test"] & (dum > 0)
        other_dum = f["e_dum"] if cal == "macro" else f["m_dum"]
        base_cols = np.c_[f["Xh"], dum]
        pD, _ = f["ols"](base_cols, f["rv"], f["train"])
        qD = float(np.mean(q(f["rv"][bar], pD[bar])))
        pC = f["pCm"] if cal == "macro" else f["pCe"]
        qC = float(np.mean(q(f["rv"][bar], pC[bar])))
        idx = np.where(dum > 0)[0]
        scr = []
        for s in range(N_SHUF):
            r2 = np.random.default_rng(SEED + 1 + s)
            pw2 = pw.copy()
            pw2[idx] = r2.permutation(pw2[idx])
            pS, _ = f["ols"](np.c_[f["Xh"], dum, pw2], f["rv"], f["train"])
            scr.append(float(np.mean(q(f["rv"][bar], pS[bar]))))
        q_scr = float(np.median(scr))
        gain = qD - qC
        kept = qD - q_scr
        ok = gain <= 0 or kept <= 0.5 * gain
        out_ok &= ok
        print(f"E-D1 scramble {inst}/{cal}: C {qC:.4f} D {qD:.4f} scrambled {q_scr:.4f} "
              f"(keeps {kept:+.4f} of gain {gain:+.4f}) -> "
              f"{'COLLAPSES (PASS)' if ok else 'FAIL'}", flush=True)
        _ = other_dum
    return 0 if out_ok else 1


def forecast(inst: str, now: pd.Timestamp, horizon: int, earn_file: str | None,
             out_dir: Path) -> int:
    f = _fit(inst)
    b_m = f["betas"]["Cm"]
    b_e = f["betas"]["Ce"]
    rows = []
    # macro side: the DEPLOYED power layer's own assembly (nothing re-implemented)
    from src.deploy import power_forecast as pf
    ev_hist = pf._assemble(inst)
    ev_hist = ev_hist[ev_hist.et < now]
    import tv_calendar
    titles = sorted(ev_hist.title.unique())
    cal = tv_calendar.load()
    fwd = cal[(cal.title.isin(titles)) & (cal.event_et > now)
              & (cal.event_et <= now + pd.Timedelta(days=horizon))]
    for _, r in fwd.sort_values("event_et").iterrows():
        prior = ev_hist[ev_hist.title == r.title].jump_pct
        if len(prior) < 8:
            continue
        p_hist = float(prior.median())
        rows.append({"calendar": "macro", "event": r.title, "event_et": str(r.event_et),
                     "pred_power_pct": round(p_hist, 4),
                     "bar_lift_rv_pts": round(b_m[-2] + b_m[-1] * p_hist, 2)})
    if earn_file:
        hist = pd.read_csv(EARN / "data" / f"ep1_events_{inst}.csv",
                           parse_dates=["event_et"])
        ed = pd.read_csv(earn_file, parse_dates=["event_et"])
        for _, r in ed[(ed.event_et > now)
                       & (ed.event_et <= now + pd.Timedelta(days=horizon))].iterrows():
            tick = getattr(r, "ticker", "?")
            prior = hist[(hist.ticker == tick) & (hist.event_et < now)].jump_pct
            if len(prior) < 8:
                continue
            p_hist = float(prior.median())
            rows.append({"calendar": "earnings", "event": tick,
                         "event_et": str(r.event_et),
                         "pred_power_pct": round(p_hist, 4),
                         "bar_lift_rv_pts": round(b_e[-2] + b_e[-1] * p_hist, 2)})
    # X-3 (docs/X3-PREREGISTRATION.md): collision flag + additive compound lift.
    # Law #1 (X-1): the calendars resolve independently => composition is ADDITIVE;
    # max per counterpart calendar avoids double-counting clustered prints.
    for r in rows:
        t_r = pd.Timestamp(r["event_et"])
        best = None
        flag = None
        for o in rows:
            if o is r or o["calendar"] == r["calendar"]:
                continue
            dh = (t_r - pd.Timestamp(o["event_et"])).total_seconds() / 3600.0
            if abs(dh) <= 24.0:
                flag = "T1" if (0.0 < dh <= 18.0 and flag != "T1") else (flag or "T2")
                if o.get("bar_lift_rv_pts") is not None:
                    lift_o = o["bar_lift_rv_pts"]
                    best = lift_o if best is None else max(best, lift_o)
        r["collision"] = flag
        if flag is not None and best is not None and r.get("bar_lift_rv_pts") is not None:
            r["compound_lift_rv_pts"] = round(r["bar_lift_rv_pts"] + best, 2)

    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"two_calendar_forecast_{inst}.jsonl"
    with dest.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"E-D1 forecast {inst}: {len(rows)} upcoming known events within {horizon}d of "
          f"{now} -> {dest}", flush=True)
    for r in rows[:5]:
        print("  ", r, flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    for m in ("verify", "scramble"):
        sp = sub.add_parser(m)
        sp.add_argument("--instrument", required=True, choices=["NQ", "ES"])
    fp = sub.add_parser("forecast")
    fp.add_argument("--instrument", required=True, choices=["NQ", "ES"])
    fp.add_argument("--now", required=True)
    fp.add_argument("--horizon-days", type=int, default=30)
    fp.add_argument("--earnings-dates", default=None)
    fp.add_argument("--out-dir", default="deploy_out_two_calendar")
    a = ap.parse_args()
    if a.mode == "verify":
        return verify(a.instrument)
    if a.mode == "scramble":
        return scramble(a.instrument)
    return forecast(a.instrument, pd.Timestamp(a.now), a.horizon_days,
                    a.earnings_dates, Path(a.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
