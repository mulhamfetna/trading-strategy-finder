"""WS-NEWS2 Phase 1, H1-B / H1-C (#115) — does `forecast - previous` carry DIRECTION?

    H1-B  does the market DRIFT toward the anticipated change BEFORE the print?   [T-X, T)
    H1-C  does the anticipated change predict the direction AFTER the print?      [T, T+h)

FEATURE: A = forecast - previous, the "anticipated change" — the only number available before the
release that could carry direction.

⚠️ STRONG PRIOR AGAINST BOTH, recorded before the run so a null is no surprise and a hit is no fluke:
   round-1 experiment #15 found NO information leak (07:45-08:28 runs 0.81-0.89x a control), `forecast`
   is PUBLIC so an efficient market has already priced A, and round 1 measured the reward side of
   scheduled news as ZERO on a proxy surprise.

⭐⭐⭐ BECAUSE WE EXPECT A NULL, THE CRITICAL CHECK IS THE PLANTED-EFFECT PROBE (HB-C2).
   A null from a broken pipeline is indistinguishable from a null from an absent edge, and this
   workstream produced a manufactured null THIS WEEK (the pre-2016 DST defect, #114). So the pipeline is
   handed a synthetic feature that IS the outcome plus noise, and it must FIND it. If the probe fails,
   NO negative result may be reported at all.

⚠️⚠️ NORMALISATION IS EXPANDING, NEVER FULL-SAMPLE. A is in thousands of jobs for payrolls and percent
   for CPI, so it must be normalised before pooling — but a full-sample z-score uses the mean and sd of
   events that had not happened yet. That is look-ahead, and it is invisible in the output. Expanding
   window, >=24 prior observations in that series; the first 24 events per series are DISCARDED and the
   loss is reported.

UNIVERSE — deliberately restricted to VERIFIED data. Only the four series whose `actual`, `previous`
and `forecast` went through #119/#120. Running on the other 99 would test a hypothesis on data of
unchecked provenance, which is the habit this sequence exists to break. Coverage traded for verified
inputs, on purpose.

PRE-REGISTERED GRID (#115, the whole search): H1-B X in {5,15,30,60}, H1-C h in {5,15,60}, two
instruments, Pearson AND Spearman => 28 tests => Bonferroni alpha = 0.05/28 = 0.00179.

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/fundamentals/h1bc_anticipated_direction.py \
        --instrument NQ
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

TV_RAW = HERE / "tradingview" / "tv_us_calendar_raw.csv"

# ---- pre-registered constants (#115). Changing any of these invalidates the pre-registration. ------
# ⚠️ The floor is PER INSTRUMENT, not global (#121). The calendar floor is 2016 everywhere (the
# TradingView DST defect, #114), but the PRICE frames become fully covered at different years — the
# pre-2016 source is sparse and the sparsity differs by instrument. One global cut would either discard
# good years or admit thin ones, and a thin year does not announce itself in the output.
MIN_YEAR = 2016
INSTRUMENT_FLOOR = {
    "NQ": 2016, "GC": 2016, "ES": 2016, "CL": 2016, "HG": 2016, "SI": 2016,
    "NG": 2017,     # full bar coverage only from 2017
    "RTY": 2019,    # contract lists from 2017-07; full coverage from 2019
}
# ⛔ YM has NO 1-minute frame — every aggregated file is 0 bytes (#121). Excluded, not silently missing.
EXCLUDED = {"YM": "1-minute frame is empty (#121)"}
SERIES = {                           # the VERIFIED four (#119, #120)
    "nfp":      "Non Farm Payrolls",
    "cpi":      "Inflation Rate MoM",
    "retail":   "Retail Sales MoM",
    "durables": "Durable Goods Orders MoM",
}
# ⚠️⚠️ P1X-C6: THE ENERGY RELEASES ARE NOT PROVENANCE-VERIFIED. #119 and #120 cleared four series;
# EIA and API are not among them, so we do NOT know that their `actual` is a first print or that their
# `previous` is point-in-time. A result on these is a WEAKER CLAIM and every report must say so.
#
# They are included anyway because they are the ONLY way to test the owner's actual premise — "a
# release may move oil a lot but not Nasdaq" — and because they are weekly, so they carry ~4x the
# sample of any monthly series. The honest handling is to run them, label them in the OUTPUT ITSELF,
# and never pool them with the verified four.
ENERGY_SERIES = {
    "eia_crude":    "EIA Crude Oil Stocks Change",
    "eia_gasoline": "EIA Gasoline Stocks Change",
    "eia_natgas":   "EIA Natural Gas Stocks Change",
    "eia_distill":  "EIA Distillate Stocks Change",
}
SERIES_SETS = {"verified": SERIES, "energy": ENERGY_SERIES}
PRE_WINDOWS = [5, 15, 30, 60]        # H1-B, minutes before the print
POST_HORIZONS = [5, 15, 60]          # H1-C, minutes after the print
MIN_HISTORY = 24                     # expanding-window normalisation warm-up
# ⚠️⚠️ THE CORRECTION CHANGED WITH THE INSTRUMENT COUNT. #115 corrected over 28 tests (2 instruments).
# Eight instruments makes it 112. This RAISES the bar — more coverage demands larger effects — and a
# cell that was borderline at two instruments will not survive at eight. Fixed before running (#122).
N_INSTRUMENTS = 8
N_PRIMARY_TESTS = N_INSTRUMENTS * (len(PRE_WINDOWS) + len(POST_HORIZONS)) * 2
BONFERRONI = 0.05 / N_PRIMARY_TESTS
N_PERM = 1000                        # C1 permutation draws
# ⚠️ V3 probe effect sizes. The FIRST version planted a single r=0.15 — BELOW the minimum detectable
# correlation at this sample size (~0.19 at n=411, alpha=0.00179), so the probe could never have passed
# and would have voided every run for a reason that has nothing to do with the pipeline being broken.
# A probe calibrated below the study's own resolution tests nothing. Now it is a CURVE, and the pass
# criterion is "detects at or above the MDE" — i.e. the pipeline achieves the power it claims.
PLANTED_R_GRID = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
SEED = 20260808                      # fixed: a reproducible "random" control, not Math.random noise


# ------------------------------------------------------------------------------------------------
# events
# ------------------------------------------------------------------------------------------------
def load_events(floor: int = MIN_YEAR, series: dict | None = None) -> pd.DataFrame:
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    series = SERIES if series is None else series
    d = d[d.title.isin(series.values()) & d.forecast.notna() & d.previous.notna()]
    d = d[d.et.dt.year >= floor].copy()
    d["series"] = d.title.map({v: k for k, v in series.items()})
    d["A"] = d.forecast.astype(float) - d.previous.astype(float)
    d = d.sort_values("et").drop_duplicates(["series", "et"]).reset_index(drop=True)

    # ⚠️ EXPANDING normalisation, per series. shift(1) is what makes it strictly past-only: without it
    # the current observation contributes to its own mean and sd, which is a subtle look-ahead that
    # would still "work" and never raise anything.
    out = []
    for s, g in d.groupby("series"):
        g = g.sort_values("et").copy()
        mu = g.A.expanding().mean().shift(1)
        sd = g.A.expanding().std().shift(1)
        g["A_z"] = (g.A - mu) / sd
        g["n_hist"] = np.arange(len(g))
        g.loc[g.n_hist < MIN_HISTORY, "A_z"] = np.nan
        out.append(g)
    return pd.concat(out).sort_values("et").reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# returns
# ------------------------------------------------------------------------------------------------
def _at(idx: pd.DatetimeIndex, ts: pd.Timestamp) -> int | None:
    """Position of the last bar at or before `ts`. None if outside the frame."""
    i = idx.searchsorted(ts, side="right") - 1
    return int(i) if 0 <= i < len(idx) else None


def returns_for(px: pd.DataFrame, stamps: pd.Series, offsets_min: list[int], *, post: bool,
                price_col: str = "Close") -> pd.DataFrame:
    """Signed returns around each stamp.

    H1-B (post=False): [T-X, T) — from X minutes before the print to the last bar BEFORE it.
      ⚠️ The end bar is T-1 minute, NOT T. Including the release bar would fold the news itself into a
      "pre-release" drift and manufacture the very effect H1-B is looking for.
    H1-C (post=True):  [T, T+h) — from the release bar to h minutes later.
    """
    idx = pd.DatetimeIndex(px["Date"])
    vals = px[price_col].to_numpy(dtype=float)
    rows = []
    for ts in stamps:
        r: dict = {}
        i_t = _at(idx, ts)
        for m in offsets_min:
            if i_t is None:
                r[f"r{m}"] = np.nan
                continue
            if post:
                a, b = _at(idx, ts), _at(idx, ts + pd.Timedelta(minutes=m))
            else:
                a, b = _at(idx, ts - pd.Timedelta(minutes=m)), _at(idx, ts - pd.Timedelta(minutes=1))
            if a is None or b is None or b <= a or vals[a] <= 0:
                r[f"r{m}"] = np.nan
            else:
                # ⚠️ Guard against a stale-bar join: if the anchor bar is far from the requested time
                # the frame has a hole there and the "return" would span a gap of unknown length.
                gap_ok = abs((idx[a] - (ts if post else ts - pd.Timedelta(minutes=m))).total_seconds()) <= 300
                r[f"r{m}"] = (vals[b] / vals[a] - 1.0) * 100.0 if gap_ok else np.nan
        rows.append(r)
    return pd.DataFrame(rows, index=stamps.index)


# ------------------------------------------------------------------------------------------------
# statistics
# ------------------------------------------------------------------------------------------------
def corr_pair(x: np.ndarray, y: np.ndarray) -> dict:
    from scipy import stats
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 30 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
        return {"n": int(m.sum()), "pearson_r": np.nan, "pearson_p": np.nan,
                "spearman_r": np.nan, "spearman_p": np.nan}
    pr, pp = stats.pearsonr(x[m], y[m])
    sr, sp = stats.spearmanr(x[m], y[m])
    return {"n": int(m.sum()), "pearson_r": float(pr), "pearson_p": float(pp),
            "spearman_r": float(sr), "spearman_p": float(sp)}


def mde_correlation(n: int, alpha: float = BONFERRONI, power: float = 0.80) -> float:
    """Minimum detectable correlation (HB-C5). Fisher z, two-sided.

    ⚠️ MANDATORY WITH EVERY NEGATIVE. A null at low power says nothing, and this workstream has already
    retracted a conclusion for exactly that reason.
    """
    from scipy import stats
    if n < 10:
        return float("nan")
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    z = (z_a + z_b) / np.sqrt(n - 3)
    return float(np.tanh(z))


def permutation_p(x: np.ndarray, y: np.ndarray, groups: np.ndarray, rng) -> float:
    """C1 — shuffle the feature WITHIN each series and re-measure |Spearman|.

    ⚠️ Within-series, not global: a global shuffle would also destroy the series composition, so a
    'significant' result could come from series differing in mean return rather than from the pairing.
    """
    from scipy import stats
    m = np.isfinite(x) & np.isfinite(y)
    x, y, g = x[m], y[m], groups[m]
    if len(x) < 30:
        return float("nan")
    obs = abs(stats.spearmanr(x, y).statistic)
    hits = 0
    for _ in range(N_PERM):
        xs = x.copy()
        for gv in np.unique(g):
            sel = np.where(g == gv)[0]
            xs[sel] = rng.permutation(xs[sel])
        if abs(stats.spearmanr(xs, y).statistic) >= obs:
            hits += 1
    return (hits + 1) / (N_PERM + 1)


# ------------------------------------------------------------------------------------------------
def run(instrument: str, verbose: bool = True, series_set: str = "verified") -> dict:
    from optimize.fundamentals.extended_data import load_1m_extended

    floor = INSTRUMENT_FLOOR.get(instrument, MIN_YEAR)
    ev = load_events(floor, SERIES_SETS[series_set])
    px = load_1m_extended(instrument)
    px = px.sort_values("Date").reset_index(drop=True)
    rng = np.random.default_rng(SEED)

    out: dict = {"instrument": instrument, "min_year": floor,
                 "series_set": series_set,
                 "provenance_verified": series_set == "verified",
                 "series": sorted(SERIES_SETS[series_set]), "n_events_raw": int(len(ev)),
                 "n_dropped_warmup": int(ev.A_z.isna().sum()),
                 "bonferroni_alpha": BONFERRONI, "n_primary_tests": N_PRIMARY_TESTS,
                 "price_span": [str(px.Date.min()), str(px.Date.max())]}

    ev = ev.dropna(subset=["A_z"]).reset_index(drop=True)
    out["n_events_used"] = int(len(ev))

    pre = returns_for(px, ev.et, PRE_WINDOWS, post=False)
    post = returns_for(px, ev.et, POST_HORIZONS, post=True)

    # ---- C2 matched non-event control: the SAME clock time, on days with no release in our set -----
    # ⚠️ Built by shifting each event back exactly 7 days: same weekday, same clock minute, same
    # session — so anything it finds is ordinary price behaviour, not news.
    ctrl_stamps = ev.et - pd.Timedelta(days=7)
    real_days = set(ev.et.dt.normalize())
    keep = ~ctrl_stamps.dt.normalize().isin(real_days)
    ctrl_pre = returns_for(px, ctrl_stamps.where(keep), PRE_WINDOWS, post=False)
    ctrl_post = returns_for(px, ctrl_stamps.where(keep), POST_HORIZONS, post=True)
    out["n_control"] = int(keep.sum())

    az = ev.A_z.to_numpy(dtype=float)
    grp = ev.series.to_numpy()

    cells = []
    for label, frame, offs, ctrl in (("H1-B", pre, PRE_WINDOWS, ctrl_pre),
                                     ("H1-C", post, POST_HORIZONS, ctrl_post)):
        for m in offs:
            y = frame[f"r{m}"].to_numpy(dtype=float)
            c = corr_pair(az, y)
            c.update(hypothesis=label, offset_min=m,
                     mde_r=mde_correlation(c["n"]),
                     passes_bonferroni=bool(min(c["pearson_p"], c["spearman_p"]) < BONFERRONI)
                     if np.isfinite(c["pearson_p"]) else False)
            # C1 permutation only where it could matter — 1,000 Spearmans per cell is not free
            c["perm_p"] = (permutation_p(az, y, grp, rng)
                           if c["n"] >= 30 and min(c["pearson_p"], c["spearman_p"]) < 0.05
                           else None)
            cc = corr_pair(az, ctrl[f"r{m}"].to_numpy(dtype=float))
            c["control_spearman_r"] = cc["spearman_r"]
            c["control_spearman_p"] = cc["spearman_p"]

            # ⭐⭐ DIRECTIONAL ACCURACY — the quantity the STRATEGY actually needs, and it is not the
            # correlation. A rule would trade the SIGN of A_z, so what matters is how often that sign
            # matches the sign of the move. Reported with a Wilson interval, and compared against the
            # ~71% that #111 established is required to cover costs.
            #
            # ⚠️ Reporting only the correlation would have left the decision-relevant number implicit
            # and forced a later reader to convert r -> accuracy through a bivariate-normal assumption
            # that FAT TAILS VIOLATE. This is measured, not converted.
            mm = np.isfinite(az) & np.isfinite(y) & (az != 0) & (y != 0)
            if mm.sum() >= 30:
                hit = float((np.sign(az[mm]) == np.sign(y[mm])).mean())
                nn = int(mm.sum())
                z = 1.959963985
                den = 1 + z * z / nn
                centre = (hit + z * z / (2 * nn)) / den
                half = z * np.sqrt(hit * (1 - hit) / nn + z * z / (4 * nn * nn)) / den
                c["hit_rate"] = hit
                c["hit_n"] = nn
                c["hit_ci95"] = [float(centre - half), float(centre + half)]
                c["hit_beats_break_even"] = bool(centre - half > 0.71)
            cells.append(c)
    out["cells"] = cells

    # ---- V1 re-derivation: a DIFFERENT price construction (Open) and a second correlation path -------
    pre_o = returns_for(px, ev.et, PRE_WINDOWS, post=False, price_col="Open")
    v1 = []
    from scipy import stats as _st
    for m in PRE_WINDOWS:
        a = corr_pair(az, pre[f"r{m}"].to_numpy(dtype=float))
        b = corr_pair(az, pre_o[f"r{m}"].to_numpy(dtype=float))
        # rank-transform then Pearson MUST equal Spearman exactly — a second implementation path
        mm = np.isfinite(az) & np.isfinite(pre[f"r{m}"].to_numpy(dtype=float))
        rr = (_st.pearsonr(_st.rankdata(az[mm]), _st.rankdata(pre[f"r{m}"].to_numpy(dtype=float)[mm]))[0]
              if mm.sum() > 30 else np.nan)
        v1.append({"offset_min": m, "close_spearman": a["spearman_r"], "open_spearman": b["spearman_r"],
                   "rank_pearson": float(rr), "spearman": a["spearman_r"],
                   "identical": bool(np.isfinite(rr) and abs(rr - a["spearman_r"]) < 1e-9)})
    out["v1"] = v1

    # ---- V2 split-half by era ---------------------------------------------------------------------
    era = ev.et.dt.year < 2021
    v2 = []
    # ⚠️ Iterate over (hypothesis, offset) PAIRS. 5 and 15 appear in BOTH grids, so keying on the bare
    # offset silently resolved every post-release horizon to the PRE-release frame — the split-half
    # check was validating H1-B twice and never touching H1-C, while printing rows labelled as if it had.
    for hyp, frame, m in ([("H1-B", pre, m) for m in PRE_WINDOWS] +
                          [("H1-C", post, m) for m in POST_HORIZONS]):
        y = frame[f"r{m}"].to_numpy(dtype=float)
        a = corr_pair(az[era.to_numpy()], y[era.to_numpy()])
        b = corr_pair(az[~era.to_numpy()], y[~era.to_numpy()])
        v2.append({"hypothesis": hyp, "offset_min": m,
                   "early_spearman": a["spearman_r"], "late_spearman": b["spearman_r"],
                   "early_n": a["n"], "late_n": b["n"],
                   "same_sign": bool(np.isfinite(a["spearman_r"]) and np.isfinite(b["spearman_r"])
                                     and np.sign(a["spearman_r"]) == np.sign(b["spearman_r"]))})
    out["v2_split_half"] = v2

    # ---- V3 PLANTED-EFFECT PROBE (HB-C2) -----------------------------------------------------------
    # ⭐⭐⭐ Build a synthetic feature that IS the outcome plus noise, calibrated to r ~= PLANTED_R, and
    # require the pipeline to FIND it. If this fails, the pipeline cannot detect an effect and NO
    # negative result may be reported.
    probe: dict = {"curve": [], "detected": False}
    y60 = post["r60"].to_numpy(dtype=float)
    mm = np.isfinite(y60)
    if mm.sum() >= 50:
        ys = (y60[mm] - np.nanmean(y60[mm])) / np.nanstd(y60[mm])
        mde = mde_correlation(int(mm.sum()))
        probe["n"] = int(mm.sum())
        probe["mde_r"] = mde
        for target in PLANTED_R_GRID:
            k = target / np.sqrt(max(1e-9, 1 - target ** 2))
            planted = k * ys + rng.standard_normal(mm.sum())
            c = corr_pair(planted, y60[mm])
            probe["curve"].append({
                "target_r": target, "measured_spearman": c["spearman_r"], "p": c["spearman_p"],
                "detected": bool(np.isfinite(c["spearman_p"]) and c["spearman_p"] < BONFERRONI)})
        # ⭐ PASS = every planted effect AT OR ABOVE the study's own MDE is found. Anything below the
        # MDE is expected to be missed; missing it is the study's resolution, not a pipeline fault.
        above = [c for c in probe["curve"] if c["target_r"] >= mde]
        probe["detected"] = bool(above) and all(c["detected"] for c in above)
        probe["smallest_detected"] = next((c["target_r"] for c in probe["curve"] if c["detected"]), None)
    out["v3_planted_probe"] = probe

    # ---- verdict -----------------------------------------------------------------------------------
    if not probe.get("detected"):
        out["verdict"] = "VOID"
        out["reason"] = ("HB-C2 FAILED: the pipeline missed a planted effect AT OR ABOVE its own MDE, "
                         "so it cannot find an effect that is present. No negative result may be "
                         "reported — a null here would be indistinguishable from a broken measurement.")
    else:
        hits = [c for c in cells if c["passes_bonferroni"]]
        clean = [c for c in hits if (c.get("perm_p") or 1.0) < 0.05
                 and not (np.isfinite(c["control_spearman_p"]) and c["control_spearman_p"] < 0.05)]
        if not hits:
            out["verdict"] = "NEGATIVE"
            out["reason"] = (f"0 of {len(cells)} cells clear Bonferroni alpha={BONFERRONI:.5f}, and the "
                             f"planted probe WAS detected — so the pipeline can find an effect and "
                             f"there is none of this size to find")
        elif clean:
            out["verdict"] = "POSITIVE"
            out["reason"] = f"{len(clean)} cell(s) clear Bonferroni AND both controls"
        else:
            out["verdict"] = "POSITIVE BUT CONTROLS FAIL"
            out["reason"] = f"{len(hits)} cell(s) clear Bonferroni but fail C1/C2 — HB-C3 voids them"

    if verbose:
        _report(out)
    return out


def _report(o: dict) -> None:
    print("=" * 104)
    print(f"H1-B / H1-C — does `forecast - previous` carry DIRECTION?   {o['instrument']}   #115")
    print("=" * 104)
    tag = ("VERIFIED provenance" if o.get("provenance_verified") else
           "UNVERIFIED provenance — #119/#120 did NOT clear these; a WEAKER claim")
    print(f"  series set '{o.get('series_set')}' [{tag}]: {', '.join(o['series'])}   era {o['min_year']}+")
    print(f"  price frame: {o['price_span'][0]} -> {o['price_span'][1]}")
    print(f"  events: {o['n_events_raw']} raw, {o['n_dropped_warmup']} dropped by the expanding-window "
          f"warm-up, {o['n_events_used']} used")
    print(f"  matched non-event controls: {o['n_control']}")
    print(f"  ⚠️ pre-registered: {o['n_primary_tests']} tests, Bonferroni alpha = {o['bonferroni_alpha']:.5f}")
    print()
    print(f"  {'hyp':<6}{'off':>5}{'n':>6}{'Pearson r':>11}{'p':>9}{'Spearman r':>12}{'p':>9}"
          f"{'MDE r':>8}{'ctrl r':>9}{'perm p':>9}{'hit%':>7}{'  95% CI':>16}  pass")
    for c in o["cells"]:
        pp = "-" if c.get("perm_p") is None else f"{c['perm_p']:.3f}"
        print(f"  {c['hypothesis']:<6}{c['offset_min']:>5}{c['n']:>6}{c['pearson_r']:>11.3f}"
              f"{c['pearson_p']:>9.3f}{c['spearman_r']:>12.3f}{c['spearman_p']:>9.3f}"
              f"{c['mde_r']:>8.3f}{c['control_spearman_r']:>9.3f}{pp:>9}"
              f"{100*c.get('hit_rate', float('nan')):>7.1f}"
              f"{('[%.3f,%.3f]' % tuple(c['hit_ci95'])) if 'hit_ci95' in c else '':>16}  "
              f"{'YES' if c['passes_bonferroni'] else '.'}")
    print()
    print("  V1 re-derivation (Close vs Open construction; rank-Pearson must EQUAL Spearman):")
    for v in o["v1"]:
        print(f"    {v['offset_min']:>3}m  close {v['close_spearman']:+.3f}   open {v['open_spearman']:+.3f}"
              f"   rank-Pearson == Spearman: {v['identical']}")
    print("  V2 split-half by era (2016-2020 vs 2021-2026):")
    for v in o["v2_split_half"]:
        print(f"    {v['hypothesis']:<6}{v['offset_min']:>3}m  early {v['early_spearman']:+.3f} (n={v['early_n']})"
              f"   late {v['late_spearman']:+.3f} (n={v['late_n']})   same sign: {v['same_sign']}")
    p = o.get("v3_planted_probe", {})
    print(f"  V3 ⭐⭐⭐ PLANTED-EFFECT PROBE — can this pipeline find an effect that IS there?")
    print(f"      n={p.get('n')}   study MDE r={p.get('mde_r', float('nan')):.3f} at alpha={BONFERRONI:.5f}")
    for c in p.get("curve", []):
        mark = "detected" if c["detected"] else "missed"
        note = "" if c["target_r"] >= p.get("mde_r", 9) else "   (below MDE — expected to be missed)"
        print(f"        planted r={c['target_r']:.2f} -> measured {c['measured_spearman']:+.3f} "
              f"p={c['p']:.6f}  {mark}{note}")
    print(f"      smallest detected: r={p.get('smallest_detected')}   PASS={p.get('detected')}")
    print("      ⚠️ If this is False, a null here means NOTHING — the pipeline could not find an effect")
    print("        that is definitely present, and the result is VOID rather than negative.")
    print()
    hits = [c for c in o["cells"] if "hit_rate" in c]
    if hits:
        best = max(hits, key=lambda c: c["hit_rate"])
        print(f"  ⭐⭐ DIRECTIONAL ACCURACY — what a rule would actually need (#111: ~71% to cover costs)")
        print(f"      best cell: {best['hypothesis']} {best['offset_min']}m -> {100*best['hit_rate']:.1f}% "
              f"(95% CI {100*best['hit_ci95'][0]:.1f}-{100*best['hit_ci95'][1]:.1f}%), n={best['hit_n']}")
        print(f"      cells whose CI LOWER BOUND clears 71%: "
              f"{sum(c['hit_beats_break_even'] for c in hits)} of {len(hits)}")
        print(f"      ⚠️ 50% is a coin flip. An accuracy near 50 with a CI that contains 50 is NOT a")
        print(f"        weak edge — it is no edge, and it still pays the full round trip.")
    print(f"  VERDICT: {o['verdict']} — {o['reason']}")
    print("=" * 104)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--series-set", choices=sorted(SERIES_SETS), default="verified")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = run(a.instrument, series_set=a.series_set)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
