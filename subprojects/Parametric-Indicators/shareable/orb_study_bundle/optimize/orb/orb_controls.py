"""WS-ORB (#183) dumb control 1 (random-time range) + vol-tercile check for named cells.
    python3 optimize/orb/orb_controls.py --root <tape> --out <json> --cells NQ_globex_60_R1,NQ_cash_15_R2 [--draws 20]
Random anchor: same N and rule, anchor drawn uniformly (seeded) from the session's minutes that leave >= N+30 bars;
the real cell's confirmation-window $25 mean must beat the p95 of the draws. Vol terciles: trailing 20-session
realised vol (sd of session log close/close) -> mean $25 P/L in bottom / middle / top tercile."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve(); sys.path.insert(0, str(HERE.parents[2]))
from optimize.orb import orb_reference as R  # noqa: E402

PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "HG": 25000.0, "CL": 1000.0, "NG": 10000.0, "RTY": 50.0, "YM": 5.0}
CONF = ("2018-01-01", "2024-12-31 23:59:59")


def conf_mean(b: pd.DataFrame) -> float:
    if b.empty:
        return np.nan
    b = b[(pd.to_datetime(b["entry_time"]) >= CONF[0]) & (pd.to_datetime(b["entry_time"]) <= CONF[1])]
    return float((b["pnl"] - 25.0).mean()) if len(b) else np.nan


def with_anchor(df: pd.DataFrame, arm: str, tok: str, N: int, rule: str, anchor_min: int) -> pd.DataFrame:
    """Run a cell with the anchor moved to anchor_min (minutes after midnight) — by temporarily rewriting the table."""
    hm = f"{anchor_min // 60:02d}:{anchor_min % 60:02d}"
    if arm == "cash":
        old = R.CASH_OPEN[tok]; R.CASH_OPEN[tok] = hm
        try:
            return R.run_cell(df, "cash", tok, N, rule, PV[tok])
        finally:
            R.CASH_OPEN[tok] = old
    # globex: shift the datetime so that anchor_min becomes 18:00 (the session logic is fixed at 18:00)
    shift = (18 * 60 - anchor_min)
    d2 = df.copy(); d2["datetime"] = pd.to_datetime(d2["datetime"]) + pd.Timedelta(minutes=shift)
    b = R.run_cell(d2, "globex", tok, N, rule, PV[tok])
    if len(b):
        for c in ("entry_time", "exit_time"):
            b[c] = pd.to_datetime(b[c]) - pd.Timedelta(minutes=shift)
    return b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/dev/Mulham/data_2010_1s")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--draws", type=int, default=20)
    a = ap.parse_args()
    rng = np.random.default_rng(183)
    res = {}
    cache = {}
    for cell in a.cells.split(","):
        tok, arm, N, rule = cell.split("_"); N = int(N)
        if tok not in cache:
            df = pd.read_csv(Path(a.root) / f"{tok}_Continuous_Data" / f"{tok}_1m.csv"); df["datetime"] = pd.to_datetime(df["datetime"]); cache[tok] = df
        df = cache[tok]
        real_b = R.run_cell(df, arm, tok, N, rule, PV[tok]); real = conf_mean(real_b)
        if arm == "cash":
            lo = R._hm(R.CASH_OPEN[tok]); hi = R._hm(R.CASH_CLOSE[tok]) - N - 30
        else:
            lo, hi = 0, 24 * 60 - 1
        draws = []
        for k in range(a.draws):
            am = int(rng.integers(lo, hi + 1)) if arm == "cash" else int(rng.integers(0, 24 * 60))
            if arm == "cash" and am == lo:
                am += 1
            b = with_anchor(df, arm, tok, N, rule, am)
            draws.append({"anchor": f"{am // 60:02d}:{am % 60:02d}", "conf_mean25": conf_mean(b), "n": int(len(b))})
            print(cell, draws[-1], flush=True)
        vals = np.array([d["conf_mean25"] for d in draws if np.isfinite(d["conf_mean25"])])
        p95 = float(np.percentile(vals, 95)) if len(vals) else np.nan
        # vol terciles on the real book
        d = R.sessionize(df, arm, tok); d = d[d["in_sess"]]
        sc = d.groupby("session")["close"].last(); rv = np.log(sc).diff().rolling(20).std().shift(1)
        rb = real_b[(pd.to_datetime(real_b["entry_time"]) >= CONF[0]) & (pd.to_datetime(real_b["entry_time"]) <= CONF[1])].copy()
        rb["rv"] = rb["session"].map(rv); rb = rb.dropna(subset=["rv"])
        rb["terc"] = pd.qcut(rb["rv"], 3, labels=["low", "mid", "high"])
        terc = (rb["pnl"] - 25).groupby(rb["terc"], observed=True).agg(["mean", "count", "sum"]).round(2)
        res[cell] = {"real_conf_mean25": real, "draws": draws, "p95": p95, "beats_p95": bool(np.isfinite(real) and real > p95),
                     "rank_of_real": int((vals >= real).sum()) + 1 if np.isfinite(real) else None,
                     "vol_terciles": {k: {"mean": float(v["mean"]), "n": int(v["count"]), "sum": float(v["sum"])} for k, v in terc.iterrows()}}
        print(cell, "real", round(real, 2), "p95", round(p95, 2), "beats", res[cell]["beats_p95"], "terciles", res[cell]["vol_terciles"], flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print("->", a.out)


if __name__ == "__main__":
    main()
