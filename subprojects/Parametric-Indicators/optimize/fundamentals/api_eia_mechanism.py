"""#123 — is the post-API crude drift a REAL MECHANISM or an ARTEFACT?

THE SITUATION. Phase 2 (#116 S4) searched 612 pairs and found exactly one capturable effect:

    CL / API Crude Oil Stock Change   post-jump drift, rho = -0.247, p = 5.2e-05, n = 262

⛔ And its provenance CANNOT be verified (#123): the American Petroleum Institute is a PRIVATE trade
association distributing to subscribers, FRED/ALFRED carry no such series, so the method that cleared
`actual` (#119) and `previous` (#120) has no reference and cannot be run. A back-filled value here
would be INVISIBLE — the claim is unfalsifiable, not merely unchecked.

⭐ SO THE EFFECT IS ATTACKED FROM THE OTHER SIDE: does it BEHAVE the way a real mechanism would?

The setup is unusually clean because S4 searched BOTH crude releases:

    API Crude Oil Stock Change   private, Tue 16:30 ET   <- the ONLY survivor in 612 pairs
    EIA Crude Oil Stocks Change  government, Wed 10:30   <- NULL

The effect is in the private PREVIEW and absent from the official release. Two explanations:

    H1 REAL MECHANISM  the preview genuinely moves expectations; the official number arrives already
                       priced. Predicts the drift is ANTICIPATORY and REVERSES when the preview misleads.
    H2 ARTEFACT        a quirk of unverifiable data. Predicts neither.

⚠️ Everything here uses only VERIFIED price data (#121) and both releases' published values. It does
not require the provenance question to be answerable.

    A  premise      does the API number forecast the EIA number? If not, H1 is impossible.
    B  anticipation is the EIA-day jump MUTED when Tuesday's drift already moved the right way?
    C  ⭐⭐ THE DISCRIMINATOR — on weeks where API and EIA DIVERGE, does the drift REVERSE?
       An artefact has no reason to reverse specifically when the preview was misleading.
       A repricing mechanism must.

Pre-registration: issue #123. Protocol: #118.

    python3 optimize/fundamentals/api_eia_mechanism.py
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
API_TITLE = "API Crude Oil Stock Change"
EIA_TITLE = "EIA Crude Oil Stocks Change"
FLOOR = 2016
MATCH_DAYS = 3          # the EIA release following each API release


def load_pair_calendar() -> pd.DataFrame:
    """One row per API release, matched to the NEXT EIA release within MATCH_DAYS."""
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d[d.et.dt.year >= FLOOR]

    api = (d[(d.title == API_TITLE) & d.actual.notna() & d.forecast.notna()]
           .sort_values("et")[["et", "actual", "forecast", "previous"]]
           .rename(columns={"et": "api_et", "actual": "api_actual",
                            "forecast": "api_forecast", "previous": "api_previous"}))
    eia = (d[(d.title == EIA_TITLE) & d.actual.notna() & d.forecast.notna()]
           .sort_values("et")[["et", "actual", "forecast"]]
           .rename(columns={"et": "eia_et", "actual": "eia_actual", "forecast": "eia_forecast"}))

    # ⚠️ merge_asof FORWARD: each API release is matched to the NEXT EIA release, never a prior one.
    # A backward match would pair Tuesday's preview with LAST week's official number — which would
    # manufacture the very relationship test A is checking for.
    m = pd.merge_asof(api, eia, left_on="api_et", right_on="eia_et", direction="forward",
                      tolerance=pd.Timedelta(days=MATCH_DAYS))
    m = m.dropna(subset=["eia_et"]).reset_index(drop=True)
    for c in ("api_actual", "api_forecast", "api_previous", "eia_actual", "eia_forecast"):
        m[c] = m[c].astype(float)
    m["api_surprise"] = m.api_actual - m.api_forecast
    m["eia_surprise"] = m.eia_actual - m.eia_forecast
    m["divergence"] = (m.api_actual - m.eia_actual).abs()
    return m


def bar_at(idx: pd.DatetimeIndex, ts) -> int | None:
    i = idx.searchsorted(ts, side="right") - 1
    return int(i) if 0 <= i < len(idx) else None


def add_price(m: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """Post-API drift (the CAPTURABLE window) and the EIA-day jump."""
    idx = pd.DatetimeIndex(px["Date"])
    o = px["Open"].to_numpy(float)
    c = px["Close"].to_numpy(float)
    drift, jump = [], []
    for _, r in m.iterrows():
        a = bar_at(idx, r.api_et)
        b = bar_at(idx, r.api_et + pd.Timedelta(minutes=15))
        ok = a is not None and abs((idx[a] - r.api_et).total_seconds()) <= 300
        # ⚠️ the DRIFT is anchored on the release bar's CLOSE — the earliest price a reactive trader
        # can obtain, and the same measure S4 used. Anchoring on the open would fold in the jump.
        drift.append((c[b] / c[a] - 1) * 100 if (ok and b and b > a and c[a] > 0) else np.nan)
        e = bar_at(idx, r.eia_et)
        ok_e = e is not None and abs((idx[e] - r.eia_et).total_seconds()) <= 300
        jump.append((c[e] / o[e] - 1) * 100 if (ok_e and o[e] > 0) else np.nan)
    m = m.copy()
    m["api_drift"] = drift
    m["eia_jump"] = jump
    return m


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


def mde(n: int, alpha: float = 0.05, power: float = 0.80) -> float:
    from scipy import stats
    if n < 10:
        return float("nan")
    z = (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) / np.sqrt(n - 3)
    return float(np.tanh(z))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    from optimize.fundamentals.extended_data import load_1m_extended
    m = load_pair_calendar()
    px = load_1m_extended("CL").sort_values("Date").reset_index(drop=True)
    m = add_price(m, px)
    m.to_csv(HERE / "api_eia_mechanism.csv", index=False)

    out: dict = {"n_matched": int(len(m)), "floor": FLOOR}

    print("=" * 100)
    print("#123 — IS THE POST-API CRUDE DRIFT A REAL MECHANISM OR AN ARTEFACT?")
    print("=" * 100)
    print(f"  {len(m)} API releases matched to the NEXT EIA release (<= {MATCH_DAYS} days), {FLOOR}+")
    print(f"  usable drift {int(m.api_drift.notna().sum())} · usable EIA jump "
          f"{int(m.eia_jump.notna().sum())}")

    # ---- A — premise -----------------------------------------------------------------------------
    A = corr(m.api_actual.to_numpy(float), m.eia_actual.to_numpy(float))
    out["A"] = A
    out["A_pass"] = bool(np.isfinite(A["spearman_r"]) and A["spearman_r"] > 0.3
                         and A["spearman_p"] < 0.001)
    print(f"\n  A · PREMISE — does the API number forecast the EIA number?")
    print(f"     n={A['n']}  Pearson {A['pearson_r']:+.3f} (p={A['pearson_p']:.2e})  "
          f"Spearman {A['spearman_r']:+.3f} (p={A['spearman_p']:.2e})")
    print(f"     -> {'PASS — the mechanism is possible' if out['A_pass'] else 'FAIL — H1 IS IMPOSSIBLE'}")

    # ---- B — anticipation -------------------------------------------------------------------------
    B = corr(m.api_drift.to_numpy(float), m.eia_jump.to_numpy(float))
    out["B"] = B
    print(f"\n  B · ANTICIPATION — is the EIA-day jump related to Tuesday's drift?")
    print(f"     n={B['n']}  Pearson {B['pearson_r']:+.3f} (p={B['pearson_p']:.3f})  "
          f"Spearman {B['spearman_r']:+.3f} (p={B['spearman_p']:.3f})   MDE r={mde(B['n']):.3f}")

    # ---- C — ⭐⭐ THE DISCRIMINATOR ----------------------------------------------------------------
    # Split on the MEDIAN divergence, fixed in the pre-registration rather than chosen after looking.
    med = float(m.divergence.median())
    lo = m[m.divergence <= med]
    hi = m[m.divergence > med]
    Cl = corr(lo.api_surprise.to_numpy(float), lo.api_drift.to_numpy(float))
    Ch = corr(hi.api_surprise.to_numpy(float), hi.api_drift.to_numpy(float))
    out["C_median_divergence"] = med
    out["C_agreement"] = Cl
    out["C_divergence"] = Ch
    # H1: the drift should be WEAKER or REVERSED on divergence weeks.
    out["C_reversal"] = bool(np.isfinite(Cl["spearman_r"]) and np.isfinite(Ch["spearman_r"])
                             and Ch["spearman_r"] > Cl["spearman_r"] + 0.15)
    print(f"\n  C · ⭐⭐ DISCRIMINATOR — does the drift REVERSE when the preview misled?")
    print(f"     split on the median |API - EIA| = {med:.3f}")
    print(f"     AGREEMENT weeks  n={Cl['n']:>4}  surprise->drift Spearman {Cl['spearman_r']:+.3f} "
          f"(p={Cl['spearman_p']:.3f})   MDE r={mde(Cl['n']):.3f}")
    print(f"     DIVERGENCE weeks n={Ch['n']:>4}  surprise->drift Spearman {Ch['spearman_r']:+.3f} "
          f"(p={Ch['spearman_p']:.3f})   MDE r={mde(Ch['n']):.3f}")
    print(f"     -> reversal/attenuation on divergence weeks: {out['C_reversal']}")

    # ---- verdict ----------------------------------------------------------------------------------
    if not out["A_pass"]:
        v, why = "H1 DEAD", ("the API number does not forecast the EIA number, so the repricing "
                             "mechanism is impossible; the drift remains unexplained AND unverifiable")
    elif out["C_reversal"]:
        v, why = "REAL MECHANISM", ("the drift attenuates or reverses exactly on the weeks where the "
                                    "preview misled — an artefact has no reason to do that")
    else:
        v, why = "INCONCLUSIVE", ("the premise holds but the drift does NOT behave differently when "
                                 "the preview misled — consistent with H1, but not evidence FOR it")
    out["verdict"], out["reason"] = v, why
    print(f"\n  VERDICT: {v} — {why}")
    print(f"\n  ⚠️ Regardless of the verdict this changes nothing about tradeability: the drift is")
    print(f"     57.4% accurate against a 71% break-even, and it does NOT make the API series")
    print(f"     verifiable — it would show the effect BEHAVES like a mechanism, not that its")
    print(f"     inputs are clean.")
    print("=" * 100)

    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
