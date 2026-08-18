"""#119 — is TradingView's `actual` the FIRST PRINT, or a later revision?

⛔ THIS GATES PHASE 2 (#116) ENTIRELY.

Phase 2's features are `actual - forecast` and `actual - previous`. If TradingView back-fills REVISED
values, both contain information that did not exist at the release second, and the study would produce
a clean, well-controlled, look-ahead-contaminated result. Nothing about the output would look wrong.

The magnitude is not hypothetical: 2025 nonfarm payrolls were revised DOWN by 801k-1,032k jobs between
the first print and today.

METHOD. Each release gives three numbers, not two:

    first print   ALFRED vintage as of the release date -> what a trader saw that morning
    current       FRED today                            -> after every revision to date
    TV actual     TradingView                           -> the number under test

⚠️ TradingView reports the monthly CHANGE (`236` = +236k); FRED's PAYEMS reports the LEVEL. The headline
   change is `vintage_d[m] - vintage_d[m-1]` — the first print of month m minus the value of m-1 THEN IN
   FORCE, which is how the BLS reports it. Differencing the VINTAGE gives that. Differencing today's
   series does not, and neither does differencing a series of initial releases.

⭐ THE DISCRIMINATING SUBSET. For many months the first print and the current value are nearly equal;
   those releases cannot tell the two hypotheses apart at all. Including them dilutes the answer toward
   "matches both", which is not an answer. The verdict is computed ONLY where |first - current| is large
   enough to be unambiguous, and that subset's size is reported BEFORE the verdict.

⚠️⚠️ V3 IS THE CHECK THAT MATTERS: compare TV `actual` against the first print of the WRONG month. If
   that also matches, the matcher matches everything and "it matches the first print" means nothing.
   This is the exact shape of the RETRACTED Nasdaq claim "off by one, verified 3x" — three dates
   tested, their neighbours never.

Pre-registration, decision rule, blind spot: issue #119. Protocol: #118.

    python3 optimize/fundamentals/alfred_revision_check.py --series nfp
    python3 optimize/fundamentals/alfred_revision_check.py --series cpi
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import alfred  # noqa: E402

TV_RAW = HERE / "tradingview" / "tv_us_calendar_raw.csv"
CACHE = HERE / "alfred_cache"
CACHE.mkdir(exist_ok=True)

_OBS = "https://api.stlouisfed.org/fred/series/observations"


@dataclass(frozen=True)
class SeriesSpec:
    key: str
    tv_title: str
    fred_id: str
    unit: str
    # |first - current| at or above this counts as DISCRIMINATING. Pre-registered in #119.
    discriminating: float
    # |tv_actual - candidate| at or below this counts as a MATCH. Set from the reporting granularity of
    # the published figure, not chosen to make anything pass.
    match_tol: float
    kind: str                      # "diff" (level -> monthly change) or "pct" (level -> MoM %)


SPECS = {
    # NFP: TradingView prints thousands of jobs (236 = +236k). PAYEMS is thousands of persons.
    # Published to the nearest 1k, so a 0.5k tolerance is half the reporting granularity.
    "nfp": SeriesSpec("nfp", "Non Farm Payrolls", "PAYEMS", "k jobs",
                      discriminating=10.0, match_tol=0.5, kind="diff"),
    # CPI MoM: TradingView prints one decimal of a percent. CPIAUCSL is the SA index.
    # ⚠️ 0.05 is half of the 0.1pp reporting granularity — so a "match" cannot be an artefact of rounding.
    # ⚠️⚠️ CPI turned out to have almost NO DISCRIMINATING POWER for this question: it is revised by less
    # than the 0.1pp it is reported to, so first print and current value agree on 121 of 125 releases and
    # the two hypotheses predict the same number. It returns CANNOT TELL by the pre-registered n>=20 rule.
    # That is an ABSENCE OF POWER, not a disagreement with NFP — kept here as the record of why a second
    # series was needed.
    "cpi": SeriesSpec("cpi", "Inflation Rate MoM", "CPIAUCSL", "% MoM",
                      discriminating=0.15, match_tol=0.05, kind="pct"),
    # ⭐ Durable Goods Orders: the real V2. A percent-change series like CPI (so it tests the same code
    # path as CPI, not NFP's level-differencing) but one that IS revised materially — factory shipments
    # are restated every month as late survey responses arrive.
    "durables": SeriesSpec("durables", "Durable Goods Orders MoM", "DGORDER", "% MoM",
                           discriminating=0.15, match_tol=0.05, kind="pct"),
    # Retail Sales: a second percent-change series with routine revisions, and one of the seven events
    # round 1 actually studied.
    "retail": SeriesSpec("retail", "Retail Sales MoM", "RSAFS", "% MoM",
                         discriminating=0.15, match_tol=0.05, kind="pct"),
}


# ------------------------------------------------------------------------------------------------
# FRED / ALFRED access
# ------------------------------------------------------------------------------------------------
def _cached(name: str, fn):
    p = CACHE / f"{name}.json"
    if p.exists():
        d = json.loads(p.read_text())
        return pd.Series({pd.Timestamp(k): v for k, v in d.items()}).sort_index()
    s = fn()
    p.write_text(json.dumps({str(k.date()): float(v) for k, v in s.items()}))
    return s


def current_series(fred_id: str) -> pd.Series:
    """Today's values — after every revision."""
    def _fetch():
        url = f"{_OBS}?series_id={fred_id}&api_key={alfred._key()}&file_type=json"
        with urllib.request.urlopen(url, timeout=60) as r:
            obs = json.loads(r.read().decode())["observations"]
        return pd.Series({pd.Timestamp(o["date"]): float(o["value"])
                          for o in obs if o["value"] not in (".", "")}).sort_index()
    return _cached(f"{fred_id}_current", _fetch)


def initial_release_series(fred_id: str) -> pd.Series:
    """FRED `output_type=4` — INITIAL RELEASE ONLY, in one call.

    ⭐ V1 uses this as a genuinely different MECHANISM for the same quantity: the level as first
    published. If ALFRED's `realtime_start=<release date>` convention were off by one — returning the
    state BEFORE the 08:30 release rather than after — the point-in-time level and this level would
    disagree, and the whole primary measurement would be built on the previous month's vintage.
    """
    def _fetch():
        # ⚠️ output_type=4 REQUIRES an explicit realtime span. Without one FRED defaults the period to
        # today..today and answers 400 "No vintage dates exist for the specified real-time period" —
        # which reads like the series is missing rather than like the query is malformed.
        url = (f"{_OBS}?series_id={fred_id}&api_key={alfred._key()}&file_type=json"
               f"&output_type=4&realtime_start=1776-07-04&realtime_end=9999-12-31")
        with urllib.request.urlopen(url, timeout=60) as r:
            obs = json.loads(r.read().decode())["observations"]
        return pd.Series({pd.Timestamp(o["date"]): float(o["value"])
                          for o in obs if o["value"] not in (".", "")}).sort_index()
    return _cached(f"{fred_id}_initial", _fetch)


def vintage_cached(fred_id: str, as_of: str) -> pd.Series | None:
    """Point-in-time vintage, cached per (series, date). Returns None if ALFRED has no vintage.

    ⚠️ AR-C3: `SeriesNotInAlfred` is a FACT ABOUT THE DATA — permanent and expected for early vintages —
    and must never be conflated with a network failure. It is returned as None and COUNTED; a network
    failure propagates and stops the run.
    """
    p = CACHE / f"{fred_id}_{as_of}.json"
    if p.exists():
        d = json.loads(p.read_text())
        if d is None:
            return None
        return pd.Series({pd.Timestamp(k): v for k, v in d.items()}).sort_index()
    try:
        s = alfred.vintage(fred_id, as_of)
    except alfred.SeriesNotInAlfred:
        p.write_text("null")
        return None
    p.write_text(json.dumps({str(k.date()): float(v) for k, v in s.items()}))
    return s


# ------------------------------------------------------------------------------------------------
# the measurement
# ------------------------------------------------------------------------------------------------
def _transform(level: pd.Series, month: pd.Timestamp, kind: str) -> float | None:
    """Turn a LEVEL series into the number TradingView actually prints, for reference month `month`."""
    idx = level.index
    if month not in idx:
        return None
    prev = idx[idx < month]
    if len(prev) == 0:
        return None
    a, b = float(level[month]), float(level[prev[-1]])
    if kind == "diff":
        return a - b
    return (a / b - 1.0) * 100.0 if b else None


def tv_events(spec: SeriesSpec, min_year: int) -> pd.DataFrame:
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d[(d.title == spec.tv_title) & d.actual.notna()].copy()
    # ⚠️ Key on the REFERENCE month, not the release date: `referenceDate` is the month the statistic
    # describes. Keying on the release date would silently pair a release with the wrong month whenever
    # a publication slipped across a month boundary.
    d["ref_month"] = (pd.to_datetime(d["referenceDate"], format="mixed", utc=True)
                      .dt.tz_localize(None).dt.to_period("M").dt.to_timestamp())
    d = d[d.et.dt.year >= min_year]
    return d[["et", "ref_month", "actual", "forecast", "previous"]].drop_duplicates("ref_month")


def run(spec: SeriesSpec, min_year: int, verbose: bool = True) -> dict:
    ev = tv_events(spec, min_year)
    cur = current_series(spec.fred_id)
    init = initial_release_series(spec.fred_id)

    rows, no_vintage, no_month = [], 0, 0
    # ⚠️ Every uncached event is one ALFRED round trip. Print progress: a long silent run is
    # indistinguishable from a hung one, and a blind wait is exactly what the project rules forbid.
    n_total = len(ev)
    for i, (_, e) in enumerate(ev.iterrows(), 1):
        if verbose and (i % 10 == 0 or i == 1):
            print(f"PROG {i}/{n_total} events ({100*i/n_total:.0f}%)", flush=True)
        as_of = e.et.date().isoformat()
        vin = vintage_cached(spec.fred_id, as_of)
        if vin is None:
            no_vintage += 1
            continue
        m = e.ref_month
        first = _transform(vin, m, spec.kind)
        curv = _transform(cur, m, spec.kind)
        # V3 shifted-month control: the first print of the PREVIOUS reference month
        prev_idx = vin.index[vin.index < m]
        shifted = _transform(vin, prev_idx[-1], spec.kind) if len(prev_idx) else None
        # V1: the level as FIRST PUBLISHED, via a different mechanism (output_type=4)
        init_lvl = float(init[m]) if m in init.index else None
        vin_lvl = float(vin[m]) if m in vin.index else None
        if first is None or curv is None:
            no_month += 1
            continue
        rows.append(dict(ref_month=m, release=e.et, tv=float(e.actual), first=first, current=curv,
                         shifted=shifted, init_lvl=init_lvl, vin_lvl=vin_lvl))

    df = pd.DataFrame(rows)
    if df.empty:
        return {"spec": spec.key, "n": 0, "verdict": "CANNOT TELL", "reason": "no usable events"}

    df["d_first"] = (df.tv - df["first"]).abs()
    df["d_current"] = (df.tv - df.current).abs()
    df["d_shifted"] = (df.tv - df.shifted).abs()
    df["revision"] = (df["first"] - df.current).abs()
    disc = df[df.revision >= spec.discriminating]

    def rate(sub, col):
        return float((sub[col] <= spec.match_tol).mean()) if len(sub) else float("nan")

    out = {
        "spec": spec.key, "fred_id": spec.fred_id, "tv_title": spec.tv_title, "unit": spec.unit,
        "min_year": min_year,
        "n_tv_events": int(len(ev)),
        "n_usable": int(len(df)),
        "n_no_alfred_vintage": int(no_vintage),          # AR-C3: expected + permanent, counted apart
        "n_month_missing": int(no_month),
        "discriminating_threshold": spec.discriminating,
        "match_tol": spec.match_tol,
        "n_discriminating": int(len(disc)),
        "match_first_all": rate(df, "d_first"),
        "match_current_all": rate(df, "d_current"),
        "match_first_disc": rate(disc, "d_first"),
        "match_current_disc": rate(disc, "d_current"),
        "match_shifted_disc": rate(disc, "d_shifted"),   # V3
        "median_revision_disc": float(disc.revision.median()) if len(disc) else float("nan"),
    }

    # V1 — the two mechanisms must agree on the first-published LEVEL
    lv = df.dropna(subset=["init_lvl", "vin_lvl"])
    out["v1_n"] = int(len(lv))
    out["v1_level_agreement"] = float(((lv.init_lvl - lv.vin_lvl).abs() <= 1e-6).mean()) if len(lv) else float("nan")

    # ---- pre-registered decision rule (#119). Fail-safe direction fixed BEFORE the data was seen. ----
    mf, mc, ms = out["match_first_disc"], out["match_current_disc"], out["match_shifted_disc"]
    if out["n_discriminating"] < 20:
        verdict, why = "CANNOT TELL", f"only {out['n_discriminating']} discriminating releases (<20)"
    elif not (ms < 0.20):
        verdict, why = "VOID", (f"AR-C2 FAILED: the shifted-month control matches {ms:.0%} of the time — "
                                f"the matcher matches nearly anything, so no verdict is admissible")
    elif mf >= 0.80 and mf > mc + 0.30:
        verdict, why = "FIRST PRINT", f"matches the first print {mf:.0%} vs the revised value {mc:.0%}"
    elif mc >= 0.80 and mc > mf + 0.30:
        verdict, why = "REVISED", f"matches the revised value {mc:.0%} vs the first print {mf:.0%}"
    else:
        verdict, why = "CANNOT TELL", (f"neither dominates (first {mf:.0%}, current {mc:.0%}) — "
                                       f"treated as REVISED per AR-C5")
    out["verdict"], out["reason"] = verdict, why

    # ⭐ EVIDENCE TABLE. The per-event triple is the actual evidence and it is small, reviewable and
    # diffable. The ALFRED cache is NOT committed: each vintage file holds the series' whole history
    # (PAYEMS back to 1939), so 4 series would be ~12 MB of mostly-redundant JSON. ALFRED vintages are
    # immutable, so the cache buys speed, not integrity — anyone with a free FRED key reproduces it.
    ev_path = HERE / f"alfred_revision_{spec.key}.csv"
    df.assign(series=spec.key, fred_id=spec.fred_id, unit=spec.unit,
              discriminating=df.revision >= spec.discriminating).to_csv(ev_path, index=False)
    out["evidence"] = str(ev_path.relative_to(HERE.parents[2]))

    if verbose:
        _report(out, df, disc, spec)
        print(f"  evidence table -> {ev_path.name}  ({len(df)} rows)")
    return out


def _report(out: dict, df: pd.DataFrame, disc: pd.DataFrame, spec: SeriesSpec) -> None:
    print("=" * 100)
    print(f"ALFRED REVISION CHECK — {spec.tv_title}  ({spec.fred_id}, {spec.unit})   #119")
    print("=" * 100)
    print(f"  TradingView events with an `actual`, {out['min_year']}+ : {out['n_tv_events']}")
    print(f"  usable (ALFRED vintage + reference month present)      : {out['n_usable']}")
    print(f"  ⚠️ no ALFRED vintage (EXPECTED, permanent, not an error): {out['n_no_alfred_vintage']}")
    print(f"  reference month absent from a series                   : {out['n_month_missing']}")
    print()
    print(f"  ⭐ DISCRIMINATING SUBSET (|first - current| >= {spec.discriminating} {spec.unit}) : "
          f"{out['n_discriminating']}")
    print(f"     median revision there: {out['median_revision_disc']:.3f} {spec.unit}")
    print(f"     (reported BEFORE the verdict — on the rest, the two hypotheses predict the same thing)")
    print()
    print(f"  match tolerance: +/-{spec.match_tol} {spec.unit} (half the reporting granularity)")
    print(f"    {'':22}{'all events':>14}{'discriminating':>16}")
    print(f"    {'matches FIRST PRINT':22}{out['match_first_all']:>13.0%}{out['match_first_disc']:>16.0%}")
    print(f"    {'matches REVISED value':22}{out['match_current_all']:>13.0%}{out['match_current_disc']:>16.0%}")
    print()
    print(f"  V1  first-published LEVEL, two mechanisms (point-in-time vintage vs output_type=4):")
    print(f"      agreement {out['v1_level_agreement']:.0%} on {out['v1_n']} events")
    print(f"  V2  see the other --series run (different unit, different publisher behaviour)")
    print(f"  V3  ⚠️⚠️ SHIFTED-MONTH CONTROL: TV actual vs the WRONG month's first print — "
          f"{out['match_shifted_disc']:.0%}")
    print(f"      (must COLLAPSE. If it does not, the matcher matches anything and the result is void.)")
    print()
    if len(disc):
        show = disc.nlargest(8, "revision")[["ref_month", "tv", "first", "current", "revision"]]
        print("  largest revisions in the discriminating subset:")
        print(f"    {'month':<12}{'TV actual':>11}{'first print':>13}{'today':>11}{'revision':>11}")
        for _, r in show.iterrows():
            print(f"    {r.ref_month:%Y-%m}     {r.tv:>10.1f}{r['first']:>13.1f}{r.current:>11.1f}"
                  f"{r.revision:>11.1f}")
    print()
    print(f"  VERDICT: {out['verdict']}  —  {out['reason']}")
    print("=" * 100)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", choices=sorted(SPECS), default="nfp")
    ap.add_argument("--min-year", type=int, default=2016)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = run(SPECS[a.series], a.min_year)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0 if res.get("verdict") in ("FIRST PRINT", "REVISED", "CANNOT TELL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
