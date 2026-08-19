"""FU-14 (#166) — the M2 power model, productionized: night-before event-size forecasts.

Implements `docs/FU13-FU14-PREREGISTRATION.md` (stages B/P/S/F/A, PASS lines fixed pre-run).
The model is M2's verbatim methodology (#126): P_hist = median of the same (series×instrument)
prior release-bar |open→close|%, shifted one release, ≥8 priors — expanding (the pre-registered
primary) and trailing-24 (the declared regime-aware variant), computed by importing M2's OWN
functions (`build_predictions`, `realized_moves`, `load_tv_events`) — nothing re-implemented.

    verify    parity vs the committed evidence (p2_power_events_{INST}_t24.csv) + the primary
              Spearman vs the committed result JSON.               [stages P + S]
    scramble  the falsifier: shuffled series labels must collapse the correlation. [stage F]
    forecast  the ops artifact: per upcoming scheduled event, the night-before predicted
              power (% and $/contract), JSONL — the paper-intents pattern.        [stage A]

    python3 -m src.deploy.power_forecast verify   --instrument NQ
    python3 -m src.deploy.power_forecast forecast --instrument NQ --now "2026-08-19" [--horizon-days 30]

This layer emits INFORMATION only — no trading consumer. Consumers are separate gated studies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FUND = REPO / "subprojects" / "Parametric-Indicators" / "optimize" / "fundamentals"
sys.path.insert(0, str(REPO / "subprojects" / "Parametric-Indicators"))
sys.path.insert(0, str(FUND))

PV = {"NQ": 20.0, "ES": 50.0, "RTY": 50.0, "GC": 100.0, "CL": 1000.0, "YM": 5.0}


def _m2():
    """Import M2's own machinery lazily (needs the fundamentals sys.path)."""
    import p2_power_model as p2
    from p1_ride_through import FLOOR, load_tv_events
    return p2, FLOOR, load_tv_events


def _assemble(inst: str) -> pd.DataFrame:
    """The exact M2 event table: calendar events of the 5 series + realized moves from 1m data."""
    p2, _FLOOR, load_tv_events = _m2()
    from optimize.fundamentals.extended_data import load_1m_extended
    raw = load_tv_events(inst)
    df = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    ev = pd.concat([raw.reset_index(drop=True),
                    p2.realized_moves(df, pd.DatetimeIndex(raw.et))], axis=1)
    return ev.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)


def verify(inst: str) -> int:
    p2, _, _ = _m2()
    ev = _assemble(inst)
    ev["pred"] = p2.build_predictions(ev, ev.title, trailing=24)
    mine = ev.dropna(subset=["pred"])[["title", "et", "pred", "jump_pct"]].copy()
    mine["et"] = pd.to_datetime(mine.et)
    ref = pd.read_csv(FUND / f"p2_power_events_{inst}_t24.csv", parse_dates=["et"])
    j = ref.merge(mine, on=["title", "et"], suffixes=("_ref", ""), how="outer", indicator=True)
    n_miss = int((j._merge != "both").sum())
    dp = (j.pred - j.pred_ref).abs().max()
    dj = (j.jump_pct - j.jump_pct_ref).abs().max()
    res = json.load(open(FUND / f"p2_power_result_{inst}_t24.json"))
    from scipy import stats
    r, _p = stats.spearmanr(mine.pred, mine.jump_pct)
    dr = abs(r - res["primary"]["spearman"])
    ok = n_miss == 0 and dp < 1e-9 and dj < 1e-9 and dr < 1e-4
    print(f"FU-14 verify {inst}: rows {len(mine)} vs ref {len(ref)} · unmatched {n_miss} · "
          f"max|Δpred| {dp:.2e} · max|Δjump| {dj:.2e} · Spearman {r:+.4f} vs committed "
          f"{res['primary']['spearman']:+.4f} (Δ {dr:.2e}) -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def scramble(inst: str, seed: int = 20260819) -> int:
    p2, _, _ = _m2()
    from scipy import stats
    ev = _assemble(inst)
    rng = np.random.default_rng(seed)
    real = p2.build_predictions(ev, ev.title, trailing=24)
    m = pd.DataFrame({"pred": real, "jump": ev.jump_pct}).dropna()
    r_real, _ = stats.spearmanr(m.pred, m.jump)
    rs = []
    for _ in range(20):
        sh = pd.Series(rng.permutation(ev.title.to_numpy()), index=ev.index)
        p = p2.build_predictions(ev, sh, trailing=24)
        mm = pd.DataFrame({"pred": p, "jump": ev.jump_pct}).dropna()
        rs.append(stats.spearmanr(mm.pred, mm.jump)[0])
    ok = float(np.median(rs)) < r_real - 0.2
    print(f"FU-14 scramble {inst}: real {r_real:+.3f} vs scrambled median {np.median(rs):+.3f} "
          f"(p95 {np.percentile(rs, 95):+.3f}) -> {'COLLAPSES (PASS)' if ok else 'FAIL'}")
    return 0 if ok else 1


def forecast(inst: str, now: pd.Timestamp, horizon_days: int, out_dir: Path) -> int:
    """The ops artifact: for each upcoming scheduled event of the modeled series, the
    night-before predicted power (expanding primary + trailing-24 variant), % and $/contract."""
    p2, _, load_tv_events = _m2()
    ev = _assemble(inst)
    hist = ev[ev.et < now]
    import tv_calendar
    cal = tv_calendar.load()
    titles = sorted(ev.title.unique())
    fwd = cal[(cal.title.isin(titles)) & (cal.event_et > now)
              & (cal.event_et <= now + pd.Timedelta(days=horizon_days))]
    ref_price = None
    try:
        from optimize.fundamentals.extended_data import load_1m_extended
        df = load_1m_extended(inst)
        ref_price = float(df[df.Date < now].Close.iloc[-1])
    except Exception:
        pass
    rows = []
    for _, r in fwd.sort_values("event_et").iterrows():
        prior = hist[hist.title == r.title].jump_pct
        if len(prior) < 8:
            continue
        exp_med = float(prior.median())
        t24_med = float(prior.tail(24).median())
        row = {"series": r.title, "event_et": str(r.event_et), "instrument": inst,
               "n_priors": int(len(prior)),
               "pred_power_pct_expanding": round(exp_med, 4),
               "pred_power_pct_t24": round(t24_med, 4)}
        if ref_price:
            row["pred_move_usd_per_contract_t24"] = round(t24_med / 100 * ref_price * PV[inst], 2)
        rows.append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"power_forecast_{inst}.jsonl"
    with dest.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"FU-14 forecast {inst}: {len(rows)} upcoming events within {horizon_days}d of {now} "
          f"-> {dest}")
    for r in rows[:6]:
        print("  ", r)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    for m in ("verify", "scramble"):
        sp = sub.add_parser(m)
        sp.add_argument("--instrument", required=True, choices=list(PV))
    fp = sub.add_parser("forecast")
    fp.add_argument("--instrument", required=True, choices=list(PV))
    fp.add_argument("--now", required=True)
    fp.add_argument("--horizon-days", type=int, default=30)
    fp.add_argument("--out-dir", default="deploy_out_power")
    a = ap.parse_args()
    if a.mode == "verify":
        return verify(a.instrument)
    if a.mode == "scramble":
        return scramble(a.instrument)
    return forecast(a.instrument, pd.Timestamp(a.now), a.horizon_days, Path(a.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
