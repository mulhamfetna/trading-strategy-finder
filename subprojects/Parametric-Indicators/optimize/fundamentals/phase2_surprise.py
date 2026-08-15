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
    for t, g in d.groupby("title"):
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
    idx = pd.DatetimeIndex(px["Date"])
    close = px["Close"].to_numpy(dtype=float)

    def at(ts):
        i = idx.searchsorted(ts, side="right") - 1
        return int(i) if 0 <= i < len(idx) else None

    rows = []
    for ts in stamps:
        r = {}
        a = at(ts)
        for h in horizons:
            b = at(ts + pd.Timedelta(minutes=h))
            if a is None or b is None or b <= a or close[a] <= 0 or \
                    abs((idx[a] - ts).total_seconds()) > 300:
                r[f"r{h}"] = np.nan
            else:
                r[f"r{h}"] = (close[b] / close[a] - 1.0) * 100.0
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
        for h in POST_HORIZONS:
            y = rets[f"r{h}"].to_numpy(dtype=float)
            c = corr(x, y)
            c["horizon_min"] = h
            c.update({("hit_" + k): v for k, v in sign_hit(x, y).items()})
            cells.append(c)
        out["arms"][arm] = cells

    # ---- the pre-registered S0 gate ---------------------------------------------------------------
    # ⚠️ SIGN AND SIGNIFICANCE ONLY. Round 1's -0.193 was measured on a different sample with a
    # different feature; asserting a magnitude match would be pinning a number to data that did not
    # produce it. What must reproduce is the DIRECTION of gold's response and that it is detectable.
    proxy = out["arms"]["proxy"]
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
            print(f"    {'h':>4}{'n':>6}{'Pearson':>10}{'p':>9}{'Spearman':>10}{'p':>9}"
                  f"{'same-sign':>11}{'inverse rule':>14}")
            for c in out["arms"][arm]:
                ss = c.get("hit_same_sign")
                inv = c.get("hit_inverse_rule_accuracy")
                print(f"    {c['horizon_min']:>4}{c['n']:>6}{c['pearson_r']:>10.3f}{c['pearson_p']:>9.4f}"
                      f"{c['spearman_r']:>10.3f}{c['spearman_p']:>9.4f}"
                      f"{(100*ss if ss else float('nan')):>10.1f}%{(100*inv if inv else float('nan')):>13.1f}%")
        print(f"\n  S0 GATE: {'PASS' if out['s0_pass'] else 'FAIL'} — {out['s0_reason']}")
        if not out["s0_pass"]:
            print("  ⛔ STOP. Nothing downstream of a pipeline that cannot see a known effect means")
            print("     anything, and this workstream has already produced one manufactured null.")
        print("=" * 100)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["s0"], default="s0")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = stage_s0()
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0 if res.get("s0_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
