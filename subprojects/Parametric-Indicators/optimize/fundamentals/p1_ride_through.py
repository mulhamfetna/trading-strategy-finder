"""WS-NEWS3 P1 (#125, parent #124) — the ride was never priced.

H1-A (#115) measured whether a position opened BEFORE a release survives TO the release — and stopped
measuring at the release second. Phase 1's actual trade — enter early, hold THROUGH the print, ride
the move — has no measured expectancy. This script prices it, end to end, plus the one Phase-1 clause
genuinely never tested: does the pre-release PRICE PATTERN (drift) predict the release-move direction?

WHAT IS ALREADY FINAL AND NOT RE-LITIGATED
  · direction from consensus data: NEGATIVE (H1-B/C, both anchors; S4: 1/612, 57.4% vs 71%)
  · pre-release survival: H1-A's grid — cheap stops rarely reach the release alive (NQ 57%, CL 94%
    stopped at 0.05%/5min); NQ/ES pre-release is ~2x MORE dangerous than control at usable stops.
  ⇒ the honest EXPECTATION here is coin-flip gross minus costs. A confidence interval is a
    measurement and an expectation is not — and the same run prices the surviving leg of a Phase-3
    straddle, which is why every cell reports gross AND net under three cost scenarios.

DESIGN (pre-registered in #125 before the first run)
  events   TradingView calendar (verified provenance #119/#120), per-instrument floors; the 4
           verified series everywhere; EIA+API added for CL (⚠️ UNVERIFIED provenance, marked);
           "Fed Interest Rate Decision" tracked separately for the drift test (Lucca–Moench prior).
  ride     enter at the OPEN of the bar at release−T (H1-A's convention, so its survival grid
           composes with these cells), stop at entry ± entry·S%, walk bars through the print, exit
           at the stop (gap-aware: fill at the WORSE of stop line / bar open — GAP-01) or at the
           close of the bar at release+15min. BOTH directions, always.
  grid     T ∈ {5, 15, 30} min × S ∈ {0.10, 0.20, 0.40}% — H1-A's units. 2 directions.
  drift    sign(close(rel−1m) − close(rel−60m)) vs sign(close(rel+15m) − close(rel−1m)),
           Wilson 95% CI, judged against 0.5 (information) and 0.71 (the #111 break-even).
  control  identical measurements at the same clock minute on days with NO tracked release
           (H1-A's draw, fresh seed). ⚠️ For the ride this is the whole verdict: if releases pay
           like controls, holding through news has no news-specific expectancy. For drift the
           control separates "news direction" from plain momentum-continuation.

VERIFICATION (V1/V2/V3, #118 — three checks that fail for DIFFERENT reasons)
  V1  --v1 replays H1-A's OWN calendar (us_high_impact.csv) through THIS pipeline's independent
      crossing test (boolean scan of the window vs H1-A's max-adverse-then-threshold) and requires
      the committed h1a_stopout_{INST}.json fractions to reproduce EXACTLY on all 16 cells.
      Blind spot it covers: a broken window/entry/stop convention in this script.
  V2  the release-bar |open→close| on events must exceed the control's by >1.2x (the known
      release-minute effect, reproduced from an independent pipeline). Blind spot: right code,
      wrong events (a calendar/timezone defect would kill the known effect).
  V3  FALSIFIER — the same jump statistic ON CONTROL timestamps must NOT exceed its own
      surroundings (ratio < 1.2): a pipeline that finds a "release jump" where no release exists
      is measuring its own artefact. This check CAN fail, and would, if the bar matching leaked.

COSTS (round trip, 1 contract) — commission $2.50 + spread of {1, 2, 4} ticks:
  optimistic / realistic / stressed. ⚠️ For NQ this is $7.50/12.50/22.50 — deliberately MORE
  conservative than WS-EARN's $4.50/9.50/14.50 ladder; conservative is the honest side for a study
  whose expected verdict is "costs dominate". Gross is always reported alongside.

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/fundamentals/p1_ride_through.py --instrument NQ
    ... --v1            # verification against H1-A's committed grid
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

TV_RAW = HERE / "tradingview" / "tv_us_calendar_raw.csv"
H1A_CAL = HERE / "us_high_impact.csv"

VERIFIED = ["Non Farm Payrolls", "Inflation Rate MoM", "Retail Sales MoM",
            "Durable Goods Orders MoM"]
ENERGY = ["EIA Crude Oil Stocks Change", "API Crude Oil Stock Change"]   # ⚠️ UNVERIFIED provenance
FOMC = "Fed Interest Rate Decision"                                       # drift test, separately
FLOOR = {"NQ": 2016, "GC": 2016, "ES": 2016, "CL": 2016}

LEADS_MIN = [5, 15, 30]
STOPS_PCT = [0.10, 0.20, 0.40]        # H1-A's units — its survival grid composes with these cells
EXIT_MIN = 15                          # exit at close(release + 15m) if never stopped
PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "CL": 1000.0}
TICK_USD = {"NQ": 5.0, "ES": 12.50, "GC": 10.0, "CL": 10.0}
COST_SCEN = {"optimistic": 1, "realistic": 2, "stressed": 4}              # spread in ticks
COMMISSION = 2.50


def costs_usd(inst: str) -> dict:
    return {k: COMMISSION + t * TICK_USD[inst] for k, t in COST_SCEN.items()}


def load_tv_events(instrument: str) -> pd.DataFrame:
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    series = list(VERIFIED) + [FOMC]      # FOMC rides in the pool; the drift test splits it out
    if instrument == "CL":
        series += ENERGY
    d = d[d.title.isin(series) & d.actual.notna() & d.forecast.notna()]
    d = d[d.et.dt.year >= FLOOR[instrument]].sort_values("et").reset_index(drop=True)
    # ⚠️ two verified series occasionally share the same 8:30 minute (e.g. CPI + Retail Sales).
    # A position is ONE position — keeping both rows would double-weight that minute's ride.
    d = d.drop_duplicates(subset="et", keep="first").reset_index(drop=True)
    d["unverified"] = d.title.isin(ENERGY)
    return d[["title", "et", "unverified"]]


def draw_controls(events: pd.DatetimeIndex, lo_d, hi_d, seed: int) -> list[pd.Timestamp]:
    """H1-A's control draw: same clock minute, a weekday 3–500 days away with NO tracked release."""
    rng = np.random.default_rng(seed)
    real_days = set(events.normalize())
    out = []
    for t in events:
        for _ in range(40):
            shift = int(rng.integers(3, 500)) * (1 if rng.random() < 0.5 else -1)
            c = pd.Timestamp(t) - pd.Timedelta(days=shift)
            if c.normalize() in real_days or c < lo_d or c > hi_d or c.weekday() >= 5:
                continue
            out.append(c)
            break
    return out


def wilson(k: int, n: int) -> tuple[float, float]:
    from scipy import stats
    if n == 0:
        return (np.nan, np.nan)
    lo, hi = stats.binomtest(k, n).proportion_ci(0.95, method="wilson")
    return (float(lo), float(hi))


def ride_cells(df: pd.DataFrame, stamps: pd.DatetimeIndex, titles, label: str,
               inst: str) -> list[dict]:
    """Every (lead, stop, direction) cell: gross/net $ expectancy of holding THROUGH the release."""
    idx = pd.Index(df["Date"])
    op, hi, lo, cl = (df[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    pos = idx.get_indexer(pd.DatetimeIndex(stamps).floor("min"))
    keep = pos >= 0
    pos, titles = pos[keep], np.asarray(titles)[keep]
    rows = []
    for T in LEADS_MIN:
        starts = pos - T
        ends = pos + EXIT_MIN
        ok = (starts >= 0) & (ends < len(idx))
        s, e, r, tt = starts[ok], ends[ok], pos[ok], titles[ok]
        entry = op[s]
        for S in STOPS_PCT:
            dist = entry * (S / 100.0)
            for direction in ("long", "short"):
                pnl_pts = np.full(len(s), np.nan)
                stopped_pre = np.zeros(len(s), bool)
                stopped_any = np.zeros(len(s), bool)
                for i in range(len(s)):
                    stop_lvl = entry[i] - dist[i] if direction == "long" else entry[i] + dist[i]
                    out_p = np.nan
                    for b in range(s[i], e[i] + 1):
                        hit = lo[b] <= stop_lvl if direction == "long" else hi[b] >= stop_lvl
                        if hit:
                            # GAP-01: a breach fills at the WORSE of the stop line / the bar's open
                            fill = min(op[b], stop_lvl) if direction == "long" else max(op[b], stop_lvl)
                            out_p = fill
                            stopped_any[i] = True
                            stopped_pre[i] = b < r[i]
                            break
                    if not stopped_any[i]:
                        out_p = cl[e[i]]
                    pnl_pts[i] = (out_p - entry[i]) if direction == "long" else (entry[i] - out_p)
                gross = pnl_pts * PV[inst]
                m, sd, n = float(np.mean(gross)), float(np.std(gross, ddof=1)), len(gross)
                se = sd / np.sqrt(n)
                mde = 2.80 * se        # (z_.975 + z_.80) · se — smallest detectable mean, 80% power
                row = {"set": label, "instrument": inst, "lead_min": T, "stop_pct": S,
                       "direction": direction, "n": n,
                       "gross_mean": m, "gross_ci_lo": m - 1.96 * se, "gross_ci_hi": m + 1.96 * se,
                       "gross_sd": sd, "mde_usd": mde,
                       "stopped_pre_release": float(stopped_pre.mean()),
                       "stopped_total": float(stopped_any.mean())}
                for scen, c in costs_usd(inst).items():
                    row[f"net_{scen}"] = m - c
                rows.append(row)
    return rows


def drift_test(df: pd.DataFrame, stamps: pd.DatetimeIndex, titles, label: str,
               inst: str) -> list[dict]:
    """Does the last hour's drift predict the direction of the release move (jump INCLUDED)?"""
    idx = pd.Index(df["Date"])
    cl = df["Close"].to_numpy(float)
    pos = idx.get_indexer(pd.DatetimeIndex(stamps).floor("min"))
    keep = pos >= 60
    pos, titles = pos[keep], np.asarray(titles)[keep]
    ok = pos + EXIT_MIN < len(cl)
    pos, titles = pos[ok], titles[ok]
    drift = cl[pos - 1] - cl[pos - 60]
    move = cl[pos + EXIT_MIN] - cl[pos - 1]
    rows = []
    groups = {"ALL": np.ones(len(pos), bool),
              "FOMC": np.asarray(titles) == FOMC,
              "NON_FOMC": np.asarray(titles) != FOMC}
    for g, mask in groups.items():
        d0, m0 = drift[mask], move[mask]
        nz = (d0 != 0) & (m0 != 0)
        n = int(nz.sum())
        k = int((np.sign(d0[nz]) == np.sign(m0[nz])).sum())
        lo_, hi_ = wilson(k, n)
        rows.append({"set": label, "instrument": inst, "group": g, "n": n,
                     "accuracy": k / n if n else np.nan, "ci_lo": lo_, "ci_hi": hi_,
                     "beats_half": bool(n and lo_ > 0.5),
                     "beats_break_even": bool(n and lo_ >= 0.71)})
    return rows


def jump_ratio(df: pd.DataFrame, stamps: pd.DatetimeIndex) -> dict:
    """Mean release-bar |open->close| vs the mean over the bars 60..6 min BEFORE (same events)."""
    idx = pd.Index(df["Date"])
    op, cl = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    pos = idx.get_indexer(pd.DatetimeIndex(stamps).floor("min"))
    pos = pos[pos >= 60]
    absoc = np.abs(cl - op)
    at = absoc[pos]
    around = np.array([absoc[p - 60:p - 5].mean() for p in pos])
    ok = np.isfinite(at) & np.isfinite(around) & (around > 0)
    ratios = at[ok] / around[ok]
    m = float(np.mean(ratios))
    se = float(np.std(ratios, ddof=1) / np.sqrt(ok.sum()))
    return {"n": int(ok.sum()), "ratio": m, "ci_lo": m - 1.96 * se, "ci_hi": m + 1.96 * se}


def v1_replay_h1a(inst: str) -> int:
    """Replay H1-A's calendar through THIS pipeline's crossing test; its JSON must reproduce exactly."""
    from optimize.fundamentals.extended_data import load_1m_extended
    ref = json.loads((HERE / f"h1a_stopout_{inst}.json").read_text())
    cal = pd.read_csv(H1A_CAL, parse_dates=["Date"])
    cal = cal[cal.Date.dt.year >= FLOOR[inst]]
    df = load_1m_extended(inst)
    idx = pd.Index(df["Date"])
    op, hi, lo = (df[c].to_numpy(float) for c in ("Open", "High", "Low"))
    pos = idx.get_indexer(pd.DatetimeIndex(cal["Date"]).floor("min"))
    pos = pos[pos >= 0]
    bad = 0
    for row in ref["results"]:
        if row["set"] != "RELEASES":
            continue
        w, pct = row["wait_min"], row["stop_pct"]
        starts = pos - w
        ok = starts >= 0
        s, e = starts[ok], pos[ok]
        entry = op[s]
        # independent path: boolean scan of the window, not max-adverse-then-threshold
        L = np.array([(lo[s[i]:e[i]] <= entry[i] - entry[i] * pct / 100.0).any() if e[i] > s[i]
                      else False for i in range(len(s))])
        Sh = np.array([(hi[s[i]:e[i]] >= entry[i] + entry[i] * pct / 100.0).any() if e[i] > s[i]
                       else False for i in range(len(s))])
        for name, mine in (("long_stopped", L.mean()), ("short_stopped", Sh.mean()),
                           ("either_stopped", (L | Sh).mean())):
            if abs(float(mine) - row[name]) > 1e-12:
                bad += 1
                print(f"  ✗ V1 MISMATCH {inst} wait={w} stop={pct}% {name}: "
                      f"mine {float(mine):.6f} vs H1-A {row[name]:.6f}")
    print(f"V1 ({inst}): {'PASS — H1-A grid reproduced exactly, independent code path' if bad == 0 else f'FAIL — {bad} mismatches'}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ", choices=list(FLOOR))
    ap.add_argument("--v1", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    if a.v1:
        return 1 if v1_replay_h1a(a.instrument) else 0

    from optimize.fundamentals.extended_data import load_1m_extended
    inst = a.instrument
    ev = load_tv_events(inst)
    df = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)

    print("=" * 100)
    print(f"WS-NEWS3 P1 (#125) — pricing the ride through the release, {inst}")
    print("=" * 100)
    # no-silent-defaults: every parameter actually used, printed
    print(f"  events {len(ev)} ({ev.et.min():%Y-%m-%d}..{ev.et.max():%Y-%m-%d}, floor {FLOOR[inst]}) "
          f"series {sorted(ev.title.unique())}")
    print(f"  grid leads {LEADS_MIN}m x stops {STOPS_PCT}% x 2 directions · exit +{EXIT_MIN}m · "
          f"pv ${PV[inst]:.0f}/pt · costs {costs_usd(inst)}")
    if inst == "CL":
        print(f"  ⚠️ EIA/API included for CL — UNVERIFIED provenance (#123), marked in output")

    ctrl = draw_controls(pd.DatetimeIndex(ev.et), df.Date.min(), df.Date.max(), seed=20260816)
    print(f"  control timestamps: {len(ctrl)}")

    rows = ride_cells(df, pd.DatetimeIndex(ev.et), ev.title.tolist(), "RELEASES", inst)
    rows += ride_cells(df, pd.DatetimeIndex(ctrl), ["CTRL"] * len(ctrl), "CONTROL", inst)
    drows = drift_test(df, pd.DatetimeIndex(ev.et), ev.title.tolist(), "RELEASES", inst)
    drows += drift_test(df, pd.DatetimeIndex(ctrl), ["CTRL"] * len(ctrl), "CONTROL", inst)

    # ---- V2 / V3 — the known jump must be there on events, and NOT there on controls -------------
    v2 = jump_ratio(df, pd.DatetimeIndex(ev.et))
    v3 = jump_ratio(df, pd.DatetimeIndex(ctrl))
    v2_pass = v2["ci_lo"] > 1.2
    v3_pass = v3["ratio"] < 1.2
    print(f"\n  V2 release-bar jump vs its own prior hour : {v2['ratio']:.2f}x "
          f"[{v2['ci_lo']:.2f},{v2['ci_hi']:.2f}] n={v2['n']}  -> {'PASS' if v2_pass else 'FAIL'}")
    print(f"  V3 same statistic on CONTROL timestamps   : {v3['ratio']:.2f}x "
          f"[{v3['ci_lo']:.2f},{v3['ci_hi']:.2f}] n={v3['n']}  -> {'PASS (no phantom jump)' if v3_pass else 'FAIL — pipeline artefact'}")

    R = pd.DataFrame(rows)
    D = pd.DataFrame(drows)
    R.to_csv(HERE / f"p1_ride_{inst}.csv", index=False)
    D.to_csv(HERE / f"p1_drift_{inst}.csv", index=False)

    print(f"\n  RIDE-THROUGH EXPECTANCY (gross $ per event, 1 contract; net = realistic costs)")
    print(f"  {'set':>9} {'lead':>5} {'stop':>6} {'dir':>6} {'n':>5} {'gross':>9} {'95% CI':>20} "
          f"{'net(real)':>10} {'MDE':>8} {'stopped<rel':>11}")
    for _, r in R.iterrows():
        print(f"  {r['set']:>9} {r.lead_min:>4}m {r.stop_pct:>5.2f}% {r.direction:>6} {r.n:>5} "
              f"{r.gross_mean:>+9.2f} [{r.gross_ci_lo:>+8.2f},{r.gross_ci_hi:>+8.2f}] "
              f"{r.net_realistic:>+10.2f} {r.mde_usd:>8.2f} {r.stopped_pre_release:>10.1%}")

    print(f"\n  DRIFT -> RELEASE DIRECTION (accuracy, Wilson 95%; break-even 71%)")
    for _, r in D.iterrows():
        print(f"  {r['set']:>9} {r.group:>9} n={r.n:>4} acc={r.accuracy:.3f} "
              f"[{r.ci_lo:.3f},{r.ci_hi:.3f}]  >0.5: {r.beats_half}  >=0.71: {r.beats_break_even}")

    out = {"instrument": inst, "n_events": int(len(ev)), "n_controls": int(len(ctrl)),
           "grid": {"leads_min": LEADS_MIN, "stops_pct": STOPS_PCT, "exit_min": EXIT_MIN},
           "costs_usd": costs_usd(inst), "pv": PV[inst],
           "v2_jump_on_events": {**v2, "pass": bool(v2_pass)},
           "v3_no_jump_on_controls": {**v3, "pass": bool(v3_pass)},
           "ride": rows, "drift": drows}
    dest = Path(a.out) if a.out else HERE / f"p1_result_{inst}.json"
    dest.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
