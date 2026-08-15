"""#116 Phase 2 — surprise -> POWER and DIRECTION, per release x per instrument.

    surprise            = actual - forecast      (what the market did NOT price)
    level change        = actual - previous      (the direction the data itself moved)
    anticipated change  = forecast - previous    (already answered NEGATIVE in Phase 1, #122)

STAGES (#116 execution plan). Each is a checkpoint that can STOP the phase, not a step to work through.

    S0  PIPELINE VALIDITY   reproduce a KNOWN effect before asking anything new
    S1  features            + BOTH `level change` variants (#120 Test C)
    S2  planted probe       per pair; a pair whose probe fails is VOID, not negative
    S3  the 643 pairs       Bonferroni alpha = 0.000078, matrix fixed in phase2_pairs.csv
    S4  controls            on every survivor
    S5  accuracy            vs the 71% break-even (#111) — the DECISION number
    S6  synthesis

⭐⭐ WHY S0 EXISTS AND RUNS FIRST. Round 1 established that GOLD RESPONDS INVERSELY to macro surprises:
Spearman -0.193, sign-hit 39.5% against a 49.0% +/- 1.7% baseline, negative in 15 of 16 years. If this
pipeline cannot see that, nothing it says downstream means anything — and Phase 1 has already shown
this workstream can produce a MANUFACTURED null (the pre-2016 DST defect, #114) that looks exactly
like a real one.

⚠️ S0 HAS TWO ARMS, and the distinction matters:
    proxy    round 1's definition: expected = mean of the previous LOOKBACK changes in the same vintage.
             This is what -0.193 was measured on, so it is the only fair reproduction target.
    real     actual - forecast, the published consensus. NEW. If it shows the effect MORE strongly, the
             real consensus is the better instrument; if less, round 1's proxy was capturing something
             the consensus does not.

⚠️ The samples differ: round 1 ran 1,208 releases over 2010-2026; we run 2016+ with a real consensus.
So S0 does NOT assert a magnitude match. It asserts SIGN and SIGNIFICANCE — a negative, significant
monotone response on gold. Asserting the magnitude would be pinning a number to a different sample.

    python3 optimize/fundamentals/phase2_surprise.py --stage s0
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
PAIRS = HERE / "phase2_pairs.csv"

# The four series whose actual/previous/forecast were cleared by #119 and #120.
VERIFIED = ["Non Farm Payrolls", "Inflation Rate MoM", "Retail Sales MoM", "Durable Goods Orders MoM"]

INSTRUMENT_FLOOR = {"NQ": 2016, "GC": 2016, "ES": 2016, "CL": 2016, "HG": 2016, "SI": 2016,
                    "NG": 2017, "RTY": 2019}
MIN_HISTORY = 24            # expanding-window warm-up, as in Phase 1
POST_HORIZONS = [5, 15, 60]
SEED = 20260815


def load_calendar(titles: list[str], floor: int) -> pd.DataFrame:
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d[d.title.isin(titles) & d.actual.notna() & d.forecast.notna() & d.previous.notna()]
    d = d[d.et.dt.year >= floor].copy()
    d = d.sort_values("et").drop_duplicates(["title", "et"]).reset_index(drop=True)

    out = []
    for _title, g in d.groupby("title"):
        g = g.sort_values("et").copy()
        g["surprise_real"] = g.actual.astype(float) - g.forecast.astype(float)
        # ⚠️ ROUND 1'S PROXY, reconstructed exactly: the expectation is the mean of the previous
        # LOOKBACK *changes* within the same series — no consensus involved. This is the definition
        # -0.193 was measured on, so it is the only fair reproduction target.
        chg = g.actual.astype(float).diff()
        g["surprise_proxy"] = g.actual.astype(float) - (g.actual.astype(float).shift(1)
                                                        + chg.rolling(12).mean().shift(1))
        # ⚠️ Expanding normalisation with shift(1): strictly past-only. Without the shift the current
        # observation contributes to its own mean and spread — a look-ahead that still "works".
        for col in ("surprise_real", "surprise_proxy"):
            mu = g[col].expanding().mean().shift(1)
            sd = g[col].expanding().std().shift(1)
            g[col + "_z"] = (g[col] - mu) / sd
        g["n_hist"] = np.arange(len(g))
        g.loc[g.n_hist < MIN_HISTORY, ["surprise_real_z", "surprise_proxy_z"]] = np.nan
        out.append(g)
    return pd.concat(out).sort_values("et").reset_index(drop=True)


def post_returns(px: pd.DataFrame, stamps: pd.Series, horizons: list[int]) -> pd.DataFrame:
    """Post-release returns, anchored BOTH ways — because the anchor decides the answer.

    ⚠️⚠️ THE ANCHOR IS NOT A DETAIL. S0 FAILED ON ITS FIRST RUN BECAUSE OF IT, and the failure looked
    exactly like "the pipeline is broken".

        anchor = the release bar's CLOSE  ->  measures the POST-JUMP RESIDUE
        anchor = the release bar's OPEN   ->  includes the RELEASE-MINUTE JUMP

    Round 1 established that for gold, **$132 of a $137 reaction happens INSIDE the release minute**
    (jump t = +7.13; post-print residue +$5.37, t = 0.52 — i.e. noise). So anchoring on the close
    throws away 96% of the effect and measures the noise. Measured here on the same data:

        GC, proxy surprise:   jump Spearman -0.273 (p<0.0001)   |   close-anchored +0.016 (p=0.76)
        GC, real surprise:    jump Spearman -0.415 (p<0.0001)   |   close-anchored +0.014 (p=0.78)

    ⭐ WHICH ONE IS RIGHT DEPENDS ON THE TRADE, and that is why both are returned:
        · PRE-POSITIONED (in before the print, as H1-C's question assumes): you hold through the jump,
          so the OPEN anchor is correct.
        · REACTIVE (enter after seeing the number): you can only get the close, so the CLOSE anchor is
          correct — and it is also the honest measure of what is left to capture after latency.
    """
    idx = pd.DatetimeIndex(px["Date"])
    close = px["Close"].to_numpy(dtype=float)
    open_ = px["Open"].to_numpy(dtype=float)

    def at(ts):
        i = idx.searchsorted(ts, side="right") - 1
        return int(i) if 0 <= i < len(idx) else None

    rows = []
    for ts in stamps:
        r: dict = {}
        a = at(ts)
        ok_anchor = a is not None and abs((idx[a] - ts).total_seconds()) <= 300 and open_[a] > 0
        r["jump"] = (close[a] / open_[a] - 1.0) * 100.0 if ok_anchor else np.nan
        for h in horizons:
            b = at(ts + pd.Timedelta(minutes=h)) if a is not None else None
            if not ok_anchor or b is None or b <= a:
                r[f"open_r{h}"] = np.nan
                r[f"close_r{h}"] = np.nan
            else:
                r[f"open_r{h}"] = (close[b] / open_[a] - 1.0) * 100.0
                r[f"close_r{h}"] = (close[b] / close[a] - 1.0) * 100.0
        rows.append(r)
    return pd.DataFrame(rows, index=stamps.index)


def corr(x, y) -> dict:
    from scipy import stats
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 30 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
        return {"n": int(m.sum()), "pearson_r": np.nan, "pearson_p": np.nan,
                "spearman_r": np.nan, "spearman_p": np.nan}
    pr, pp = stats.pearsonr(x[m], y[m])
    sr, sp = stats.spearmanr(x[m], y[m])
    return {"n": int(m.sum()), "pearson_r": float(pr), "pearson_p": float(pp),
            "spearman_r": float(sr), "spearman_p": float(sp)}


def sign_hit(x, y) -> dict:
    """Directional accuracy of the INVERSE rule, with a Wilson interval.

    ⭐ Round 1 reported gold's sign-hit as 39.5% against a 49.0% +/- 1.7% baseline — i.e. the surprise
    predicts the move with the OPPOSITE sign. Accuracy of the inverse rule is 100% - 39.5% = 60.5%,
    which is the number a trader would care about, so both are reported.
    """
    m = np.isfinite(x) & np.isfinite(y) & (x != 0) & (y != 0)
    n = int(m.sum())
    if n < 30:
        return {"n": n}
    same = float((np.sign(x[m]) == np.sign(y[m])).mean())
    z = 1.959963985
    den = 1 + z * z / n
    c = (same + z * z / (2 * n)) / den
    h = z * np.sqrt(same * (1 - same) / n + z * z / (4 * n * n)) / den
    return {"n": n, "same_sign": same, "inverse_rule_accuracy": 1 - same,
            "same_sign_ci95": [float(c - h), float(c + h)]}


# ------------------------------------------------------------------------------------------------
# S0 — pipeline validity
# ------------------------------------------------------------------------------------------------
def stage_s0(verbose: bool = True) -> dict:
    from optimize.fundamentals.extended_data import load_1m_extended

    cal = load_calendar(VERIFIED, INSTRUMENT_FLOOR["GC"])
    px = load_1m_extended("GC").sort_values("Date").reset_index(drop=True)
    rets = post_returns(px, cal.et, POST_HORIZONS)

    out: dict = {"stage": "S0", "instrument": "GC", "series": VERIFIED,
                 "n_events": int(len(cal)), "price_span": [str(px.Date.min()), str(px.Date.max())],
                 "round1_reference": {"spearman": -0.193, "sign_hit": 0.395,
                                      "baseline": [0.473, 0.507], "note": "measured on the PROXY "
                                      "surprise over 1,208 releases 2010-2026 — a different sample"},
                 "arms": {}}

    for arm, col in (("proxy", "surprise_proxy_z"), ("real", "surprise_real_z")):
        x = cal[col].to_numpy(dtype=float)
        cells = []
        for measure in ["jump"] + [f"{anc}_r{h}" for anc in ("open", "close") for h in POST_HORIZONS]:
            y = rets[measure].to_numpy(dtype=float)
            c = corr(x, y)
            c["measure"] = measure
            c["includes_jump"] = measure == "jump" or measure.startswith("open_")
            c.update({("hit_" + k): v for k, v in sign_hit(x, y).items()})
            cells.append(c)
        out["arms"][arm] = cells

    # ---- the pre-registered S0 gate ---------------------------------------------------------------
    # ⚠️ SIGN AND SIGNIFICANCE ONLY. Round 1's -0.193 was measured on a different sample with a
    # different feature; asserting a magnitude match would be pinning a number to data that did not
    # produce it. What must reproduce is the DIRECTION of gold's response and that it is detectable.
    # ⚠️ The gate is judged on the JUMP-INCLUSIVE measures only. Round 1's -0.193 was a statement
    # about the release reaction, and the close-anchored residue is the part round 1 itself reported
    # as noise (t = 0.52). Judging the gate on the residue would be requiring the pipeline to
    # reproduce an effect in the one place the reference says it does not exist.
    proxy = [c for c in out["arms"]["proxy"] if c["includes_jump"]]
    neg = [c for c in proxy if np.isfinite(c["spearman_r"]) and c["spearman_r"] < 0]
    sig = [c for c in neg if c["spearman_p"] < 0.05]
    out["s0_pass"] = bool(len(neg) >= 2 and len(sig) >= 1)
    out["s0_reason"] = (f"{len(neg)} of {len(proxy)} horizons negative, {len(sig)} significant at 0.05 "
                        f"— gold's inverse response to macro surprise reproduces in SIGN"
                        if out["s0_pass"] else
                        f"only {len(neg)} of {len(proxy)} horizons negative and {len(sig)} significant "
                        f"— the KNOWN effect does not reproduce, so the pipeline cannot be trusted")

    if verbose:
        print("=" * 100)
        print("PHASE 2 · S0 — PIPELINE VALIDITY: does the KNOWN gold effect reproduce?   #116")
        print("=" * 100)
        print(f"  instrument GC · {out['n_events']} events · series {', '.join(VERIFIED)}")
        print(f"  price frame {out['price_span'][0]} -> {out['price_span'][1]}")
        print(f"  ⭐ round-1 reference: Spearman -0.193, sign-hit 39.5% vs a 49.0%+/-1.7% baseline")
        print(f"     ⚠️ measured on the PROXY surprise over 1,208 releases 2010-2026 — a DIFFERENT")
        print(f"        sample, so S0 asserts SIGN and SIGNIFICANCE, never a magnitude match.")
        for arm in ("proxy", "real"):
            print(f"\n  ARM '{arm}'{'  (round 1 definition — the reproduction target)' if arm == 'proxy' else '  (published consensus — NEW)'}")
            print(f"    {'measure':>10}{'jump?':>7}{'n':>6}{'Pearson':>10}{'p':>9}{'Spearman':>10}{'p':>9}"
                  f"{'inverse rule':>14}")
            for c in out["arms"][arm]:
                inv = c.get("hit_inverse_rule_accuracy")
                print(f"    {c['measure']:>10}{('YES' if c['includes_jump'] else '.'):>7}{c['n']:>6}"
                      f"{c['pearson_r']:>10.3f}{c['pearson_p']:>9.4f}"
                      f"{c['spearman_r']:>10.3f}{c['spearman_p']:>9.4f}"
                      f"{(100*inv if inv else float('nan')):>13.1f}%")
        print(f"\n  S0 GATE: {'PASS' if out['s0_pass'] else 'FAIL'} — {out['s0_reason']}")
        if not out["s0_pass"]:
            print("  ⛔ STOP. Nothing downstream of a pipeline that cannot see a known effect means")
            print("     anything, and this workstream has already produced one manufactured null.")
        print("=" * 100)
    return out


# ------------------------------------------------------------------------------------------------
# S1 — feature construction
# ------------------------------------------------------------------------------------------------
def build_features(titles: list[str], floor: int) -> pd.DataFrame:
    """The Phase 2 feature set.

    ⚠️⚠️ TWO `level change` VARIANTS ARE MANDATORY (#120 Test C). TradingView's `previous` equals the
    PRIOR RELEASE'S `actual` only 3% of the time for payrolls but 95% of the time for CPI, because the
    BLS revises payrolls with every release and barely revises CPI. So `actual - previous` is the
    REVISED-BASIS change for one series and FIRST-PRINT-TO-FIRST-PRINT for another.

    Pooling them without distinction puts two different quantities in one column, in a way correlated
    with WHICH SERIES it is — systematic, not noise. Both are computed; the as-published one is primary
    because it is the number a trader actually saw.
    """
    d = load_calendar(titles, floor)
    a_ = d.actual.astype(float)
    f_ = d.forecast.astype(float)
    p_ = d.previous.astype(float)

    d["surprise"] = a_ - f_                                   # what the market did NOT price
    d["level_change_published"] = a_ - p_                     # PRIMARY: as the calendar showed it
    d["level_change_firstprint"] = a_ - d.groupby("title").actual.shift(1).astype(float)
    d["anticipated_change"] = f_ - p_                         # answered NEGATIVE in Phase 1 (#122)
    # ⭐ Did the surprise REINFORCE the expected direction, or reverse it? Sign-only, so it is immune
    # to the unit differences that force normalisation everywhere else.
    d["confirmation"] = (np.sign(d.surprise) == np.sign(d.anticipated_change)).astype(float)
    d.loc[(d.surprise == 0) | (d.anticipated_change == 0), "confirmation"] = np.nan

    # ⚠️ EXPANDING normalisation with shift(1), per series. A full-sample z-score uses the mean and
    # spread of events that had not happened yet — look-ahead that produces no error and no warning.
    out = []
    for _t, g in d.groupby("title"):
        g = g.sort_values("et").copy()
        for col in ("surprise", "level_change_published", "level_change_firstprint",
                    "anticipated_change"):
            mu = g[col].expanding().mean().shift(1)
            sd = g[col].expanding().std().shift(1)
            g[col + "_z"] = (g[col] - mu) / sd
            g.loc[np.arange(len(g)) < MIN_HISTORY, col + "_z"] = np.nan
        out.append(g)
    return pd.concat(out).sort_values("et").reset_index(drop=True)


FEATURES = ["surprise_z", "level_change_published_z", "level_change_firstprint_z",
            "anticipated_change_z", "confirmation"]


def stage_s1(verbose: bool = True) -> dict:
    d = build_features(VERIFIED, 2016)
    out: dict = {"stage": "S1", "n_events": int(len(d)), "series": VERIFIED, "features": FEATURES,
                 "coverage": {c: int(d[c].notna().sum()) for c in FEATURES}}

    # ---- ⭐⭐⭐ V3 — THE LOOK-AHEAD FALSIFIER: PREFIX INVARIANCE -----------------------------------
    # A strictly past-only feature CANNOT change when later events are appended. So recompute the
    # features on a TRUNCATED calendar (the first 60% of events) and require the overlapping rows to be
    # BIT-IDENTICAL to the full run.
    #
    # ⚠️ This is the check that a full-sample z-score fails and nothing else would catch: the values
    # would still look sane, the correlations would still compute, and the leak would be invisible.
    floor = 2016
    cut = d.et.quantile(0.60)
    d_trunc_src = load_calendar(VERIFIED, floor)
    d_trunc_src = d_trunc_src[d_trunc_src.et <= cut]
    # rebuild features from the truncated source using the same code path
    a_, f_, p_ = (d_trunc_src.actual.astype(float), d_trunc_src.forecast.astype(float),
                  d_trunc_src.previous.astype(float))
    d_trunc_src["surprise"] = a_ - f_
    d_trunc_src["level_change_published"] = a_ - p_
    d_trunc_src["level_change_firstprint"] = a_ - d_trunc_src.groupby("title").actual.shift(1).astype(float)
    d_trunc_src["anticipated_change"] = f_ - p_
    parts = []
    for _t, g in d_trunc_src.groupby("title"):
        g = g.sort_values("et").copy()
        for col in ("surprise", "level_change_published", "level_change_firstprint",
                    "anticipated_change"):
            mu = g[col].expanding().mean().shift(1)
            sd = g[col].expanding().std().shift(1)
            g[col + "_z"] = (g[col] - mu) / sd
            g.loc[np.arange(len(g)) < MIN_HISTORY, col + "_z"] = np.nan
        parts.append(g)
    dt = pd.concat(parts).sort_values("et").reset_index(drop=True)

    key = ["title", "et"]
    j = d[key + [c for c in FEATURES if c.endswith("_z")]].merge(
        dt[key + [c for c in FEATURES if c.endswith("_z")]], on=key, suffixes=("_full", "_trunc"))
    mism = {}
    for c in [c for c in FEATURES if c.endswith("_z")]:
        x, y = j[c + "_full"], j[c + "_trunc"]
        both = x.notna() & y.notna()
        mism[c] = int((np.abs(x[both] - y[both]) > 1e-12).sum())
    out["prefix_invariance"] = {"n_compared": int(len(j)), "mismatches": mism,
                                "pass": all(v == 0 for v in mism.values())}

    # ---- V1 — the same feature by a different code path -------------------------------------------
    # `surprise` recomputed straight from the raw columns, bypassing build_features entirely.
    raw = pd.read_csv(TV_RAW, low_memory=False)
    raw["utc"] = pd.to_datetime(raw["date"], format="mixed", utc=True)
    raw["et"] = raw["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    raw = raw[raw.title.isin(VERIFIED) & raw.actual.notna() & raw.forecast.notna()
              & raw.previous.notna()]
    raw = raw[raw.et.dt.year >= 2016]
    raw["surprise_alt"] = raw.actual.astype(float) - raw.forecast.astype(float)
    j2 = d[["title", "et", "surprise"]].merge(raw[["title", "et", "surprise_alt"]], on=["title", "et"])
    out["v1_surprise_identical"] = int((np.abs(j2.surprise - j2.surprise_alt) > 1e-12).sum()) == 0
    out["v1_n"] = int(len(j2))

    # ---- V2 — the two level-change variants must DIFFER, and differ per series --------------------
    # ⭐ If they were identical everywhere, #120's Test C finding would be wrong and one variant would
    # be redundant. If they differed everywhere, `previous` would never be the prior print. The
    # PER-SERIES SPLIT is the substance.
    agree = {}
    for t, g in d.groupby("title"):
        m = g.level_change_published.notna() & g.level_change_firstprint.notna()
        agree[t] = round(float((np.abs(g.level_change_published[m]
                                       - g.level_change_firstprint[m]) < 1e-9).mean()), 3)
    out["v2_variants_agree_by_series"] = agree
    out["v2_pass"] = bool(max(agree.values()) - min(agree.values()) > 0.5)

    # ---- ⭐⭐ PROVE THE FALSIFIER CAN FAIL -------------------------------------------------------
    # "Prefix invariance holds" is worthless if the check could not detect a violation. Plant the exact
    # defect it exists for — a FULL-SAMPLE z-score, which uses events that had not happened yet — and
    # require the check to catch it. A gate that has never failed is untested.
    def _z(g, leak):
        if leak:
            return (g.surprise - g.surprise.mean()) / g.surprise.std()
        mu = g.surprise.expanding().mean().shift(1)
        sd = g.surprise.expanding().std().shift(1)
        return (g.surprise - mu) / sd

    def _leak_feats(src):
        src = src.copy()
        src["surprise"] = src.actual.astype(float) - src.forecast.astype(float)
        parts = []
        for _t, g in src.groupby("title"):
            g = g.sort_values("et").copy()
            g["surprise_z"] = _z(g, True)
            g.loc[np.arange(len(g)) < MIN_HISTORY, "surprise_z"] = np.nan
            parts.append(g)
        return pd.concat(parts).sort_values("et").reset_index(drop=True)

    src_full = load_calendar(VERIFIED, floor)
    A, B = _leak_feats(src_full), _leak_feats(src_full[src_full.et <= cut])
    jj = A[["title", "et", "surprise_z"]].merge(B[["title", "et", "surprise_z"]],
                                                on=["title", "et"], suffixes=("_f", "_t"))
    both = jj.surprise_z_f.notna() & jj.surprise_z_t.notna()
    caught = int((np.abs(jj.surprise_z_f[both] - jj.surprise_z_t[both]) > 1e-12).sum())
    out["v3_planted_leak"] = {"rows": int(both.sum()), "caught": caught,
                              "pass": bool(both.sum() > 0 and caught == int(both.sum()))}

    out["s1_pass"] = bool(out["prefix_invariance"]["pass"] and out["v1_surprise_identical"]
                          and out["v2_pass"] and out["v3_planted_leak"]["pass"])

    if verbose:
        print("=" * 100)
        print("PHASE 2 · S1 — FEATURE CONSTRUCTION   #116")
        print("=" * 100)
        print(f"  {out['n_events']} events · {len(VERIFIED)} verified series · 2016+")
        print(f"  feature coverage (non-null): {out['coverage']}")
        print()
        print("  ⭐⭐⭐ V3 LOOK-AHEAD FALSIFIER — PREFIX INVARIANCE")
        print("     A strictly past-only feature CANNOT change when later events are appended.")
        print(f"     Recomputed on the first 60% of events; {out['prefix_invariance']['n_compared']} "
              f"overlapping rows compared.")
        print(f"     mismatches: {out['prefix_invariance']['mismatches']}")
        print(f"     -> {'PASS — no leakage' if out['prefix_invariance']['pass'] else 'FAIL — THE FEATURES SEE THE FUTURE'}")
        pl = out["v3_planted_leak"]
        print(f"     ⭐⭐ and the check CAN fail: a planted full-sample z-score is caught on "
              f"{pl['caught']}/{pl['rows']} rows -> {'PASS' if pl['pass'] else 'FAIL — THE GATE IS BLIND'}")
        print()
        print(f"  V1 `surprise` recomputed from raw columns, {out['v1_n']} rows: "
              f"{'identical' if out['v1_surprise_identical'] else 'MISMATCH'}")
        print(f"  V2 the two level-change variants, share IDENTICAL per series:")
        for t, v in out["v2_variants_agree_by_series"].items():
            print(f"       {t:<28}{100*v:>6.1f}%")
        print(f"     -> {'PASS' if out['v2_pass'] else 'FAIL'} — they must diverge per series, or "
              f"#120 Test C is wrong and one variant is redundant")
        print()
        print(f"  S1: {'PASS' if out['s1_pass'] else 'FAIL'}")
        print("=" * 100)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["s0", "s1"], default="s0")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = stage_s0() if a.stage == "s0" else stage_s1()
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0 if res.get(f"{a.stage}_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
