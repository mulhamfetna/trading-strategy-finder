#!/usr/bin/env python3
"""WS-NEWS4 / N2 (#136) — the wide-series premium scan.

Runs the FROZEN confirmed ride (LONG rel-300s, S 0.10% worse-of, TP 0.40% better-of,
tie=>STOP, timed exit +900s, stressed costs lead) on every release moment the funnel never
premium-tested. Everything here implements `docs/NEWS4-N2-PREREGISTRATION.md` (commit
a988f17, filed BEFORE any run) — tiers, gates, alphas and the $150 MDE line are frozen there.

Fill model: imported from the parity-proven executor (src/deploy/release_executor.py),
NOT re-implemented. Calendar: tv_calendar.load() (the ET-wall-clock convention every prior
study used). Usable era >= 2016 (source property, see tv_calendar.py).

    python3 news4_premium_scan.py --instrument NQ --bars-1s /path/NQ_1s.csv [--tier 1|2|all]

Outputs (committed evidence):
    news4_scan_blocks_{INST}.csv    per-block statistics + gate results + verdicts
    news4_scan_events_{INST}.csv    per-event fills (block-tagged)
    news4_scan_result_{INST}.json   run manifest: spec echo, counts, verdicts
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))          # src.deploy.*
sys.path.insert(0, str(HERE))          # tv_calendar

from src.deploy.release_executor import (   # noqa: E402  the parity-proven machinery
    COST_PER_LEG, EXIT_S, LEAD_S, PV, Leg, load_1s_windows, run_bracket,
)
import tv_calendar                          # noqa: E402

# ---- pre-registered constants (NEWS4-N2-PREREGISTRATION.md — do not edit after results) --------
MIN_YEAR = 2016
MIN_MOMENTS = 40
ALPHA_T1 = 0.05 / 20                  # 10 blocks x 2 instruments, Bonferroni
FDR_Q_T2 = 0.10
MDE_LINE_USD = 150.0                  # powered-null boundary, 80% power
JUMP_RATIO = 1.2                      # V2 timestamp gate: event minute vs quiet control
NOISE_PCTL = 99.0                     # placebo percentile the observed mean must clear
N_PLACEBO = 1000
N_CTRL_DAYS = 400                     # quiet control days sampled per clock time
CTRL_QUIET_MIN = 30                   # "quiet" = no calendar event within +/- this many minutes
SEED = 117                            # deterministic control sampling (nod to the spec issue)
SPEECH_FUZZ_S = 120                   # T2 speech sensitivity shift

TESTED_TITLES = {                     # premium evidence exists => their minutes are covered
    "Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision",
    "Retail Sales MoM", "Durable Goods Orders MoM",
    "EIA Crude Oil Stocks Change", "API Crude Oil Stock Change",
}
DEPLOYED_TITLES = {"Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"}

# title renames: same series, renamed by the source (pre-registered merge map)
RENAME_MERGE = {
    "ISM Non-Manufacturing PMI": "ISM Services PMI",
    "ISM Non-Manufacturing Prices": "ISM Services Prices",
    "ISM Non-Manufacturing Employment": "ISM Services Employment",
    "ISM Non-Manufacturing New Orders": "ISM Services New Orders",
    "ISM Non-Manufacturing Business Activity": "ISM Services Business Activity",
    "Personal Income (MoM)": "Personal Income MoM",
    "Jobless Claims 4-Week Average": "Jobless Claims 4-week Average",
    "Baker Hughes Total Rigs Count": "Baker Hughes Total Rig Count",
    "Markit Manufacturing PMI Flash": "S&P Global Manufacturing PMI Flash",
    "Markit Manufacturing PMI Final": "S&P Global Manufacturing PMI Final",
    "Markit Services PMI Flash": "S&P Global Services PMI Flash",
    "Markit Services PMI Final": "S&P Global Services PMI Final",
    "Markit Composite PMI Flash": "S&P Global Composite PMI Flash",
    "Markit Composite PMI Final": "S&P Global Composite PMI Final",
    "Building Permits Prel": "Building Permits",
    "Building Permits Final": "Building Permits",
}

T1_ANCHORS = [
    "Initial Jobless Claims", "PPI MoM", "Core PCE Price Index MoM",
    "GDP Growth Rate QoQ Adv", "ISM Manufacturing PMI", "ISM Services PMI",
    "JOLTs Job Openings", "Michigan Consumer Sentiment Prel",
    "ADP Employment Change", "FOMC Minutes",
]

WINDOW_S = LEAD_S + EXIT_S            # 1200 s: two ride windows intersect iff |dt| < this


def norm_sf(x: np.ndarray | float) -> np.ndarray | float:
    """Standard normal survival function (avoids a scipy dependency on the server)."""
    from math import erfc, sqrt
    if np.isscalar(x):
        return 0.5 * erfc(x / sqrt(2.0))
    return 0.5 * np.array([erfc(float(v) / sqrt(2.0)) for v in x])


def t_test_mean(x: np.ndarray) -> tuple[float, float]:
    """Two-sided one-sample t vs 0 (normal approx for the p — n >= 40 everywhere by design)."""
    n = len(x)
    if n < 3 or x.std(ddof=1) == 0:
        return 0.0, 1.0
    t = x.mean() / (x.std(ddof=1) / np.sqrt(n))
    return float(t), float(2 * norm_sf(abs(t)))


def mde_usd(x: np.ndarray, alpha: float) -> float:
    """Minimum detectable |mean| at 80% power for this n and sd."""
    from math import sqrt
    z_a = abs(_z(1 - alpha / 2))
    z_b = abs(_z(0.80))
    return float((z_a + z_b) * x.std(ddof=1) / sqrt(len(x)))


def _z(p: float) -> float:
    """Inverse normal CDF (Acklam's rational approximation — 1e-9 accurate, dependency-free)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = np.sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = np.sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ---- block assembly -----------------------------------------------------------------------------
def build_blocks(cal: pd.DataFrame, data_end: pd.Timestamp):
    """Returns (blocks, ctrl_clocks): blocks = list of dicts {anchor, tier, moments, clock,
    is_speech}; moments are ET minute Timestamps after both pre-registered exclusions."""
    cal = cal.copy()
    cal["title"] = cal["title"].replace(RENAME_MERGE)
    cal = cal[(cal.event_et.dt.year >= MIN_YEAR) & (cal.event_et <= data_end)]
    cal["minute"] = cal.event_et.dt.floor("min")

    covered = set(cal[cal.title.isin(TESTED_TITLES)]["minute"])
    deployed_ts = np.sort(cal[cal.title.isin(DEPLOYED_TITLES)]["minute"].unique())

    def clean(minutes: pd.Series) -> list[pd.Timestamp]:
        out = []
        for m in sorted(set(minutes)):
            if m in covered:
                continue
            i = np.searchsorted(deployed_ts, np.datetime64(m))
            near = []
            if i > 0:
                near.append(deployed_ts[i - 1])
            if i < len(deployed_ts):
                near.append(deployed_ts[i])
            if any(abs((np.datetime64(m) - t) / np.timedelta64(1, "s")) < WINDOW_S for t in near):
                continue                                   # window-overlap exclusion
            out.append(pd.Timestamp(m))
        return out

    blocks = []
    used_minutes: set[pd.Timestamp] = set()
    for anchor in T1_ANCHORS:
        mom = clean(cal[cal.title == anchor]["minute"])
        blocks.append({"anchor": anchor, "tier": 1, "moments": mom, "is_speech": False})
        used_minutes.update(mom)

    # Tier 2: every remaining untested minute, grouped by its highest-frequency member title
    remaining = cal[~cal["minute"].isin(covered) & ~cal["minute"].isin(used_minutes)]
    freq = remaining["title"].value_counts()
    per_min = remaining.groupby("minute")["title"].agg(
        lambda s: max(set(s), key=lambda t: freq[t]))
    t2 = per_min.reset_index().rename(columns={"title": "anchor"})
    for anchor, grp in t2.groupby("anchor"):
        mom = clean(grp["minute"])
        if len(mom) >= MIN_MOMENTS:
            is_speech = any(k in anchor for k in
                            ("Speech", "Testimony", "Press Conference", "Beige"))
            blocks.append({"anchor": anchor, "tier": 2, "moments": mom, "is_speech": is_speech})

    for b in blocks:
        clocks = pd.Series([m.strftime("%H:%M") for m in b["moments"]])
        b["clock"] = clocks.value_counts().idxmax() if len(clocks) else ""
        b["n_raw"] = len(b["moments"])
    return blocks


def control_days(cal: pd.DataFrame, clock: str, data_end: pd.Timestamp) -> list[pd.Timestamp]:
    """Quiet control moments for one ET clock time: business days with NO calendar event
    within +/-CTRL_QUIET_MIN minutes of that time, sampled deterministically."""
    hh, mm = map(int, clock.split(":"))
    days = pd.bdate_range(f"{MIN_YEAR}-01-01", data_end.normalize())
    ev_by_day: dict = {}
    for d, g in cal[cal.event_et.dt.year >= MIN_YEAR].groupby(cal.event_et.dt.date):
        ev_by_day[d] = g.event_et.values
    quiet = []
    for day in days:
        t = day + pd.Timedelta(hours=hh, minutes=mm)
        evs = ev_by_day.get(day.date())
        if evs is None or not (
            (np.abs((evs - np.datetime64(t)) / np.timedelta64(1, "m")) <= CTRL_QUIET_MIN).any()
        ):
            quiet.append(t)
    rng = np.random.default_rng(SEED)
    if len(quiet) > N_CTRL_DAYS:
        quiet = [quiet[i] for i in sorted(rng.choice(len(quiet), N_CTRL_DAYS, replace=False))]
    return quiet


# ---- the ride + the minute jump -----------------------------------------------------------------
def ride_all(idx, op, hi, lo, cl, moments, pv: float, tag: str) -> pd.DataFrame:
    rows = []
    for t in moments:
        f = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), pv, tag)
        if f is not None:
            rows.append({"et": t, "pnl_usd": f.pnl_usd, "outcome": f.outcome,
                         "entry": f.entry, "exit_price": f.exit_price,
                         "exit_s": f.exit_s_from_release})
    return pd.DataFrame(rows)


def minute_jump(idx, op, cl, moments) -> np.ndarray:
    """|open(t) -> close(t+59s)| in points for each moment with bars (the V2 gate input)."""
    out = []
    for t in moments:
        t0 = np.datetime64(t)
        i0 = int(np.searchsorted(idx, t0, side="left"))
        i1 = int(np.searchsorted(idx, t0 + np.timedelta64(60, "s"), side="right")) - 1
        if i0 >= len(idx) or i1 < i0:
            continue
        if (idx[i0] - t0) / np.timedelta64(1, "s") > 55:   # no traded second in the minute
            continue
        out.append(abs(float(cl[i1]) - float(op[i0])))
    return np.array(out)


# ---- main ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(PV))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--tier", default="all", choices=["1", "2", "all"])
    ap.add_argument("--positive-control", action="store_true",
                    help="V1 of the SCAN itself: run the deployed {CPI,NFP,FOMC} minutes "
                         "(schedule selection, no exclusions) through the identical pipeline; "
                         "the pooled block must reproduce M3's mean to the cent")
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    inst, bars_path = a.instrument, Path(a.bars_1s)
    pv, cost = PV[inst], COST_PER_LEG[inst]["stressed"]

    # data end = last bar timestamp (cheap: read the file tail)
    with bars_path.open("rb") as f:
        f.seek(-4096, 2)
        data_end = pd.Timestamp(f.read().splitlines()[-1].split(b",")[0].decode())
    print(f"scan {inst}: bars end {data_end}; spec lead {LEAD_S}s S0.10% TP0.40% exit +{EXIT_S}s; "
          f"stressed cost ${cost}/event; pre-reg a988f17")

    cal = tv_calendar.load()
    if a.positive_control:
        sched = pd.read_csv(REPO / "src" / "deploy" / "data" / "release_schedule.csv")
        sched = sched[sched.status == "confirmed"]
        sched["et"] = pd.to_datetime(sched.et)
        sched = sched[(sched.et.dt.year >= MIN_YEAR) & (sched.et <= data_end)]
        blocks = [{"anchor": f"POSCTRL {t}", "tier": 1, "is_speech": False,
                   "moments": sorted(g.et)} for t, g in sched.groupby("title")]
        blocks.append({"anchor": "POSCTRL DEPLOYED-SET", "tier": 1, "is_speech": False,
                       "moments": sorted(sched.et)})
        for b in blocks:
            clocks_ = pd.Series([m.strftime("%H:%M") for m in b["moments"]])
            b["clock"] = clocks_.value_counts().idxmax() if len(clocks_) else ""
            b["n_raw"] = len(b["moments"])
        inst_suffix = f"{inst}_posctrl"
    else:
        blocks = build_blocks(cal, data_end)
        inst_suffix = inst
    if a.tier != "all":
        blocks = [b for b in blocks if b["tier"] == int(a.tier)]
    print(f"blocks: {sum(1 for b in blocks if b['tier']==1)} T1 + "
          f"{sum(1 for b in blocks if b['tier']==2)} T2; "
          f"moments total {sum(b['n_raw'] for b in blocks):,}")

    clocks = sorted({b["clock"] for b in blocks if b["clock"]})
    ctrl = {c: control_days(cal, c, data_end) for c in clocks}
    print(f"control clocks: { {c: len(v) for c, v in ctrl.items()} }")

    # one pass over the 1s file for EVERYTHING (events + controls, speech fuzz margin included)
    windows = []
    for b in blocks:
        pad = SPEECH_FUZZ_S if b["is_speech"] else 0
        windows += [(t - pd.Timedelta(seconds=LEAD_S + 60 + pad),
                     t + pd.Timedelta(seconds=EXIT_S + 5 + pad)) for t in b["moments"]]
    for c in clocks:
        windows += [(t - pd.Timedelta(seconds=LEAD_S + 60),
                     t + pd.Timedelta(seconds=EXIT_S + 5)) for t in ctrl[c]]
    bars = load_1s_windows(bars_path, windows)
    print(f"1s bars loaded: {len(bars):,}")
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))

    # control rides + control jumps per clock (shared across blocks)
    ctrl_ride, ctrl_jump = {}, {}
    for c in clocks:
        r = ride_all(idx, op, hi, lo, cl, ctrl[c], pv, f"CTRL@{c}")
        ctrl_ride[c] = r
        ctrl_jump[c] = minute_jump(idx, op, cl, ctrl[c])
        print(f"  control {c}: rides {len(r)} · jump n {len(ctrl_jump[c])}")

    rng = np.random.default_rng(SEED)
    block_rows, event_frames = [], []
    for b in blocks:
        alpha = ALPHA_T1 if b["tier"] == 1 else 0.05
        ev = ride_all(idx, op, hi, lo, cl, b["moments"], pv, b["anchor"])
        if len(ev) == 0:
            block_rows.append({"anchor": b["anchor"], "tier": b["tier"], "clock": b["clock"],
                               "n_moments": b["n_raw"], "n_filled": 0, "verdict": "NO-DATA"})
            continue
        ev["block"] = b["anchor"]
        ev["tier"] = b["tier"]
        event_frames.append(ev)
        g = ev.pnl_usd.to_numpy()
        net = g - cost
        t_stat, p = t_test_mean(net)
        half = len(ev) // 2
        h1, h2 = g[:half].mean(), g[half:].mean()
        mde = mde_usd(net, alpha)

        cj, ej = ctrl_jump.get(b["clock"], np.array([])), minute_jump(idx, op, cl, b["moments"])
        jump_ratio = (np.median(ej) / np.median(cj)) if len(cj) and len(ej) and np.median(cj) > 0 \
            else np.nan
        jump_ok = bool(jump_ratio > JUMP_RATIO) if np.isfinite(jump_ratio) else False

        cr = ctrl_ride.get(b["clock"], pd.DataFrame())
        ctrl_net = (cr.pnl_usd.to_numpy() - cost) if len(cr) else np.array([])
        ctrl_t, ctrl_p = t_test_mean(ctrl_net) if len(ctrl_net) > 2 else (0.0, 1.0)
        ctrl_mean = float(ctrl_net.mean()) if len(ctrl_net) else np.nan
        floor_ok = bool(len(ctrl_net) and net.mean() > ctrl_mean and ctrl_p >= alpha)

        noise_p = np.nan
        if len(ctrl_net) >= 30:
            pool = ctrl_net
            sims = np.array([pool[rng.integers(0, len(pool), len(net))].mean()
                             for _ in range(N_PLACEBO)])
            noise_p = float((sims >= net.mean()).mean())
        noise_ok = bool(np.isfinite(noise_p) and noise_p < (1 - NOISE_PCTL / 100))

        fuzz_flip = False
        if b["is_speech"]:
            for shift in (-SPEECH_FUZZ_S, SPEECH_FUZZ_S):
                sh = ride_all(idx, op, hi, lo, cl,
                              [t + pd.Timedelta(seconds=shift) for t in b["moments"]],
                              pv, b["anchor"])
                if len(sh) and np.sign(sh.pnl_usd.mean() - cost) != np.sign(net.mean()):
                    fuzz_flip = True

        # verdict, exactly the pre-registered ladder
        if not jump_ok:
            verdict = "VOID-TIMESTAMP"
        elif b["is_speech"] and fuzz_flip:
            verdict = "VOID-TIMESTAMP (fuzz flip)"
        elif p < alpha and net.mean() > 0 and h1 > 0 and h2 > 0 and floor_ok and noise_ok:
            verdict = "CONFIRMED" if b["tier"] == 1 else "EXPLORATORY-POSITIVE"
        elif p >= alpha and mde <= MDE_LINE_USD:
            verdict = "POWERED-NULL"
        elif p >= alpha:
            verdict = "UNDERPOWERED"
        else:
            verdict = ("FAILED-GATES" if net.mean() > 0 else "SIGNIFICANT-NEGATIVE")
            verdict += f" (p={p:.2g})"

        block_rows.append({
            "anchor": b["anchor"], "tier": b["tier"], "clock": b["clock"],
            "n_moments": b["n_raw"], "n_filled": len(ev),
            "gross_mean": g.mean(), "net_stressed_mean": net.mean(),
            "t": t_stat, "p": p, "alpha": alpha,
            "half1_gross": h1, "half2_gross": h2, "mde_usd": mde,
            "jump_ratio": jump_ratio, "jump_ok": jump_ok,
            "ctrl_mean_net": ctrl_mean, "ctrl_p": ctrl_p, "floor_ok": floor_ok,
            "noise_p": noise_p, "noise_ok": noise_ok, "verdict": verdict,
        })
        print(f"  [{b['tier']}] {b['anchor'][:38]:<38} n={len(ev):>4} "
              f"net ${net.mean():+8.2f} p={p:.3g} jump {jump_ratio:.2f} -> {verdict}")

    bl = pd.DataFrame(block_rows)
    # BH-FDR across Tier-2 p-values (descriptive labeling, per pre-reg)
    t2 = bl[(bl.tier == 2) & bl.p.notna()].sort_values("p")
    if len(t2):
        m = len(t2)
        passed = t2[t2.p.to_numpy() <= FDR_Q_T2 * (np.arange(1, m + 1)) / m]
        bl["t2_fdr_pass"] = bl.anchor.isin(passed.anchor)

    out = Path(a.out_dir)
    bl.to_csv(out / f"news4_scan_blocks_{inst_suffix}.csv", index=False)
    pd.concat(event_frames).to_csv(out / f"news4_scan_events_{inst_suffix}.csv", index=False)
    manifest = {
        "instrument": inst, "prereg_commit": "a988f17", "seed": SEED,
        "spec": {"lead_s": LEAD_S, "exit_s": EXIT_S, "stop_pct": 0.10, "tp_pct": 0.40,
                 "cost_stressed": cost},
        "n_blocks": len(bl), "verdicts": bl.verdict.value_counts().to_dict(),
        "data_end": str(data_end),
    }
    (out / f"news4_scan_result_{inst_suffix}.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest["verdicts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
