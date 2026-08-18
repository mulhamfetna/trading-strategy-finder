"""PORTABLE backtester — the news-release-long champion, fully self-contained.

Reproduces the champion from `champion.json` against a raw 1-second CSV and the bundled schedule —
no project imports, only numpy + pandas. The same fill semantics the study pre-registered (#117)
and the executor verified (parity: NQ 327/327 exact; 2024+ subset 81/81, $36,209.52 to the cent).

    python3 portable_backtester.py --bars-1s /path/NQ_1s.csv --instrument NQ
    python3 portable_backtester.py --bars-1s ... --instrument NQ --verify   # against champion.json

The 1-second CSV format: datetime,open,high,low,close,volume (ISO-8601, sorted, ET-naive).
⚠️ 1-second files carry bars only for TRADED seconds — never treat a bar offset as a duration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CHAMP = json.loads((HERE / "champion.json").read_text())
SPEC = CHAMP["spec"]
LEAD_S, EXIT_S, TOL_S = 300, 900, 60
STOP_PCT = SPEC["stop_loss"]["pct_of_entry"]
TP_PCT = SPEC["take_profit"]["pct_of_entry"]
_SEEK = 1 << 20


def _seek_to(path: Path, target: str) -> int:
    """Byte offset of the first complete line with timestamp >= target (ISO sorts lexically)."""
    size = path.stat().st_size
    with path.open("rb") as f:
        f.readline()
        lo, hi = f.tell(), size
        while lo < hi:
            mid = (lo + hi) // 2
            f.seek(mid); f.readline()
            pos = f.tell(); line = f.readline()
            if not line:
                hi = mid; continue
            if line.split(b",", 1)[0].decode() < target:
                lo = pos + len(line)
            else:
                hi = mid
        f.seek(max(0, lo - _SEEK))                    # rewind: landing EARLY is free, LATE drops bars
        if lo > _SEEK:
            f.readline()
        return f.tell()


def load_windows(path: Path, stamps) -> pd.DataFrame:
    w = sorted((t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
               for t in stamps)
    s_str = np.array([a.strftime("%Y-%m-%d %H:%M:%S") for a, _ in w])
    e_str = np.array([b.strftime("%Y-%m-%d %H:%M:%S") for _, b in w])
    lo, hi = min(s_str), max(e_str)
    keep = []
    fh = path.open("r")
    fh.seek(_seek_to(path, lo))
    if fh.tell() == 0:
        fh.readline()
    for ch in pd.read_csv(fh, chunksize=4_000_000, dtype={"datetime": str}, header=None,
                          names=["datetime", "open", "high", "low", "close", "volume"]):
        t = ch["datetime"].to_numpy()
        if t[-1] < lo:
            continue
        if t[0] > hi:
            break
        a = np.searchsorted(t, s_str, side="left")
        b = np.searchsorted(t, e_str, side="right")
        m = np.zeros(len(t), bool)
        for x, y in zip(a, b):
            if y > x:
                m[x:y] = True
        if m.any():
            keep.append(ch[m])
    fh.close()
    d = pd.concat(keep, ignore_index=True)
    d["Date"] = pd.to_datetime(d["datetime"])
    return (d.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
            [["Date", "Open", "High", "Low", "Close"]]
            .drop_duplicates("Date").sort_values("Date").reset_index(drop=True))


def bracket(idx, op, hi, lo, cl, t_rel, pv, qty):
    """The confirmed trade on one release. Fill semantics exactly as pre-registered (#117)."""
    t0 = np.datetime64(t_rel)
    i_ent = int(np.searchsorted(idx, t0 - np.timedelta64(LEAD_S, "s"), "right")) - 1
    i_rel = int(np.searchsorted(idx, t0, "left"))
    i_end = int(np.searchsorted(idx, t0 + np.timedelta64(EXIT_S, "s"), "right")) - 1
    if i_ent < 0 or i_end <= i_ent or i_rel <= i_ent or i_end >= len(idx):
        return None
    if abs((pd.Timestamp(idx[i_ent]) - (t_rel - pd.Timedelta(seconds=LEAD_S))).total_seconds()) > TOL_S:
        return None
    entry = float(cl[i_ent])
    if not np.isfinite(entry) or entry <= 0:
        return None
    sl = entry * (1 - STOP_PCT / 100)
    tp = entry * (1 + TP_PCT / 100)
    out_p, outcome = None, "timed"
    for b in range(i_ent + 1, i_end + 1):
        if lo[b] <= sl:                                # tie in one bar => STOP (pessimistic)
            out_p = min(op[b], sl)                     # GAP-01: worse of line / open
            outcome = "stopped_pre" if b < i_rel else "stopped_post"
            break
        if hi[b] >= tp:
            out_p = max(op[b], tp)                     # resting limit: better of line / open
            outcome = "tp"
            break
    if out_p is None:
        out_p = float(cl[i_end])
    pts = out_p - entry
    return {"et": str(t_rel), "outcome": outcome, "pnl_points": pts, "pnl_usd": pts * pv * qty}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--instrument", required=True, choices=list(SPEC["instruments"]))
    ap.add_argument("--schedule", default=str(HERE / "schedule_2024plus.csv"))
    ap.add_argument("--qty", type=int, default=1)
    ap.add_argument("--verify", action="store_true",
                    help="compare against champion.json's 2024-2026 expected numbers")
    a = ap.parse_args()

    pv = SPEC["instruments"][a.instrument]["point_value"]
    cost = SPEC["costs_per_leg_usd"]["stressed"][a.instrument] * a.qty
    ev = pd.read_csv(a.schedule, parse_dates=["et"])
    ev = ev[ev.status == "confirmed"].sort_values("et")
    # v1.2.0: an instrument may ride a SUBSET of the schedule (ES = CPI only, #139) —
    # declared in champion.json spec.instruments[<inst>].series; absent = the full schedule.
    series = SPEC["instruments"][a.instrument].get("series")
    if series:
        ev = ev[ev.title.isin(series)]
    print(f"news-release-long v{CHAMP['meta']['version']} · {a.instrument} · qty={a.qty} · "
          f"{len(ev)} releases ({ev.et.min():%Y-%m-%d} .. {ev.et.max():%Y-%m-%d})")
    print(f"spec: long @ close(rel−300s) · SL {STOP_PCT}% (worse-of) · TP {TP_PCT}% (better-of) · "
          f"tie⇒STOP · exit +900s · stressed cost ${cost:.2f}/event")

    bars = load_windows(Path(a.bars_1s), list(ev.et))
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    fills = [f for f in (bracket(idx, op, hi, lo, cl, t, pv, a.qty) for t in ev.et) if f]
    d = pd.DataFrame(fills)
    g = d.pnl_usd
    print(f"\nevents {len(d)} · gross ${g.sum():+,.2f} (mean ${g.mean():+.2f}/event) · "
          f"net(stressed) mean ${g.mean() - cost:+.2f} · win {(g > 0).mean():.1%} · "
          f"median ${g.median():+.1f}")
    print("outcomes:", d.outcome.value_counts(normalize=True).round(3).to_dict())

    if a.verify:
        exp = CHAMP["performance_2024_2026"][a.instrument]
        checks = [("n_events", len(d), exp["n_events"], 0),
                  ("gross_mean", round(g.mean() / a.qty, 2), exp["gross_mean_per_event"], 0.01),
                  ("total_gross", round(g.sum() / a.qty, 2), round(exp["total_gross"], 2), 0.01)]
        ok = True
        for name, got, want, tol in checks:
            hit = abs(got - want) <= tol
            ok &= hit
            print(f"  VERIFY {name}: got {got} want {want} -> {'OK' if hit else 'MISMATCH'}")
        print("VERIFY:", "PASS — the bundle reproduces the champion" if ok else "FAIL")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
