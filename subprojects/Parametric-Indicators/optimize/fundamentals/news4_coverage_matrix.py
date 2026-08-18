#!/usr/bin/env python3
"""WS-NEWS4 / N1 (#135): the news-programme coverage matrix.

Builds the authoritative series x question status record from the ACTUAL evidence
files on disk -- never from memory or narrative docs:

  jump/direction  phase2_pairs.csv + phase2_s*_result.json   (WS-NEWS2, 82 series x 8 instruments)
  power           p2_power_rank_{INST}[_t24].csv             (WS-NEWS3 M2, 5 series x 5 instruments)
  premium/ride    p1_events_{INST}.csv                       (WS-NEWS3 M1, 5 series x 4 idx/metal + EIA/API on CL)
  deployment      ../../../../src/deploy/data/release_schedule.csv  ({CPI,NFP,FOMC} x {NQ,RTY})
  universe        tradingview/tv_us_calendar_raw.csv         (39,221 events, 649 series)

Outputs (committed evidence):
  news4_coverage_matrix.csv            machine-readable; N2 consumes the NEVER list from here
  ../../../../docs/NEWS-COVERAGE-MATRIX.md   the human table

Statuses: TESTED / PARTIAL / NEVER / DEPLOYED (deployment column), each TESTED cell
naming its evidence file. Usable-history convention: events >= 2016-01-01 only
(pre-2016 calendar timestamps are DST-broken -- WS-NEWS2 #114).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # legacy18 root
DOCS = REPO / "docs"
USABLE_FROM = "2016-01-01"
MIN_EVENTS = 40  # inclusion floor for the universe rows (below this, no study is powered)

P1_INSTRUMENTS = ["NQ", "RTY", "ES", "GC", "CL"]
P2_INSTRUMENTS = ["NQ", "RTY", "ES", "GC", "CL"]


def load_universe() -> pd.DataFrame:
    df = pd.read_csv(HERE / "tradingview" / "tv_us_calendar_raw.csv")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["minute"] = df["date"].dt.floor("min")
    usable = df[df["date"] >= USABLE_FROM]

    g = usable.groupby("title")
    uni = pd.DataFrame(
        {
            "n_usable": g.size(),
            "tv_importance_max": g["importance"].max(),
            "first_usable": g["date"].min().dt.date.astype(str),
            "last_usable": g["date"].max().dt.date.astype(str),
            "top_utc_time": g["date"].agg(
                lambda s: s.dt.strftime("%H:%M").value_counts().idxmax()
            ),
            "category": g["category"].agg(
                lambda s: s.dropna().value_counts().idxmax() if s.notna().any() else ""
            ),
        }
    )

    # co-release detection: share of a series' usable events whose exact minute also
    # carries a DIFFERENT series' event (the dedupe-by-minute caveat), + top partner.
    minute_titles = usable.groupby("minute")["title"].agg(set)
    shared_frac, top_partner = {}, {}
    for title, rows in usable.groupby("title"):
        partners: dict[str, int] = {}
        n_shared = 0
        for m in rows["minute"]:
            others = minute_titles.loc[m] - {title}
            if others:
                n_shared += 1
                for o in others:
                    partners[o] = partners.get(o, 0) + 1
        shared_frac[title] = n_shared / len(rows)
        top_partner[title] = max(partners, key=partners.get) if partners else ""
    uni["shared_minute_frac"] = pd.Series(shared_frac)
    uni["top_shared_partner"] = pd.Series(top_partner)
    return uni


def phase2_coverage() -> pd.DataFrame:
    pairs = pd.read_csv(HERE / "phase2_pairs.csv")
    return pairs.groupby("release").agg(
        direction_instruments=("instrument", lambda s: "/".join(sorted(set(s)))),
        direction_pairs=("instrument", "size"),
    )


def p2_coverage() -> pd.DataFrame:
    frames = []
    for inst in P2_INSTRUMENTS:
        f = HERE / f"p2_power_rank_{inst}.csv"
        if f.exists():
            frames.append(pd.read_csv(f)[["title", "instrument"]])
    allr = pd.concat(frames)
    return allr.groupby("title").agg(
        power_instruments=("instrument", lambda s: "/".join(sorted(set(s))))
    )


def p1_coverage() -> pd.DataFrame:
    """Premium coverage + the M1-grid indicator: gross mean $/event of the LONG ride
    at (lead 5 min, stop 0.10%, no TP) -- the grid cell closest to the deployed spec.
    This is a coverage INDICATOR only; verdict-grade numbers live in the M1 report."""
    frames = []
    for inst in P1_INSTRUMENTS:
        f = HERE / f"p1_events_{inst}.csv"
        if not f.exists():
            continue
        e = pd.read_csv(f)
        e = e[
            (e["set"] == "RELEASES")
            & (e["direction"] == "long")
            & (e["lead_min"] == 5)
            & (e["stop_pct"] == 0.1)
        ]
        frames.append(e[["instrument", "title", "pnl_usd"]])
    allp = pd.concat(frames)
    per = allp.groupby(["title", "instrument"])["pnl_usd"].agg(["mean", "count"])
    out = per.reset_index().groupby("title").apply(
        lambda d: pd.Series(
            {
                "premium_instruments": "/".join(sorted(d["instrument"])),
                "premium_m1_long_usd": "; ".join(
                    f"{r.instrument} {r['mean']:+.0f}$ (n={int(r['count'])})"
                    for _, r in d.iterrows()
                ),
            }
        ),
        include_groups=False,
    )
    return out


def deployed_titles() -> set[str]:
    sched = pd.read_csv(REPO / "src" / "deploy" / "data" / "release_schedule.csv")
    return set(sched["title"].unique())


def build() -> pd.DataFrame:
    uni = load_universe()
    d = phase2_coverage()
    p2 = p2_coverage()
    p1 = p1_coverage()
    deployed = deployed_titles()

    touched = set(d.index) | set(p2.index) | set(p1.index) | deployed
    rows = uni[(uni["n_usable"] >= MIN_EVENTS) | (uni.index.isin(touched))].copy()
    # studies also touched series absent from the >=2016 slice? keep them anyway
    for t in touched - set(rows.index):
        rows.loc[t] = {c: 0 if rows[c].dtype.kind in "if" else "" for c in rows.columns}

    m = rows.join(d).join(p2).join(p1)

    def status_direction(r):
        if isinstance(r.get("direction_instruments"), str) and r["direction_instruments"]:
            return "TESTED"
        return "NEVER"

    def status_power(r):
        if isinstance(r.get("power_instruments"), str) and r["power_instruments"]:
            return "TESTED"
        return "NEVER"

    def status_premium(r):
        pi = r.get("premium_instruments")
        if not (isinstance(pi, str) and pi):
            return "NEVER"
        # EIA/API were provenance-UNVERIFIED and CL-only -> PARTIAL by design
        if r.name in ("EIA Crude Oil Stocks Change", "API Crude Oil Stock Change"):
            return "PARTIAL (CL only, provenance unverified)"
        if "NQ" in pi and "RTY" in pi:
            return "TESTED"
        return f"PARTIAL ({pi})"

    m["direction_status"] = m.apply(status_direction, axis=1)
    m["jump_status"] = m["direction_status"]  # WS-NEWS2 s0/s1 ran on the same pair list
    m["power_status"] = m.apply(status_power, axis=1)
    m["premium_status"] = m.apply(status_premium, axis=1)
    m["deployment_status"] = [
        "DEPLOYED (NQ+RTY)" if t in deployed else "" for t in m.index
    ]

    m = m.sort_values("n_usable", ascending=False)
    m.index.name = "series"
    return m


def n2_candidates(m: pd.DataFrame) -> pd.DataFrame:
    """The NEVER list N2 scans: enough usable events, premium never tested."""
    c = m[(m["premium_status"] == "NEVER") & (m["n_usable"] >= MIN_EVENTS)].copy()
    # speeches/testimony have fuzzy actual-start times -- flag, do not exclude
    c["timestamp_quality"] = [
        "FUZZY (speech/testimony/minutes start-time)"
        if any(k in t for k in ("Speech", "Testimony", "Press Conference", "Beige"))
        else "SCHEDULED-PRINT"
        for t in c.index
    ]
    return c


def n2_moments() -> pd.DataFrame:
    """The honest scan unit for N2: the distinct release MINUTE, not the series title.

    Co-released titles (the NFP block is ~8 titles in one minute; the EIA 14:30 crude
    block ~7) collapse to one tradeable moment. Minutes already containing one of the
    premium-tested series (CPI/NFP/FOMC/Retail/Durables + EIA-crude/API) are excluded --
    those moments are covered evidence, whatever else co-released there. The rest are
    grouped by their series-set signature into scan groups."""
    df = pd.read_csv(HERE / "tradingview" / "tv_us_calendar_raw.csv")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df[df["date"] >= USABLE_FROM]
    df["minute"] = df["date"].dt.floor("min")

    tested = {
        "Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision",
        "Retail Sales MoM", "Durable Goods Orders MoM",
        "EIA Crude Oil Stocks Change", "API Crude Oil Stock Change",
    }
    per_min = df.groupby("minute")["title"].agg(lambda s: frozenset(s))
    untested = per_min[[not (ts & tested) for ts in per_min]]

    def leader(ts: frozenset) -> str:
        # the member with the most total usable events = the block's anchor series
        counts = df[df["title"].isin(ts)]["title"].value_counts()
        return counts.idxmax()

    rows = []
    for sig, grp in untested.groupby(untested.apply(lambda ts: tuple(sorted(ts)))):
        ts = frozenset(sig)
        rows.append(
            {
                "anchor_series": leader(ts),
                "n_moments": len(grp),
                "member_titles": " | ".join(sorted(ts)),
                "n_members": len(ts),
                "top_utc_time": grp.index.strftime("%H:%M").value_counts().idxmax()
                if len(grp) else "",
            }
        )
    mo = pd.DataFrame(rows)
    # many signatures are variations of the same block (a member misses one month);
    # aggregate by anchor for the headline table
    agg = mo.groupby("anchor_series").agg(
        n_moments=("n_moments", "sum"),
        n_signatures=("n_moments", "size"),
        top_utc_time=("top_utc_time", lambda s: s.value_counts().idxmax()),
        max_block=("n_members", "max"),
    ).sort_values("n_moments", ascending=False)
    return agg


def render_md(m: pd.DataFrame, cand: pd.DataFrame, moments: pd.DataFrame) -> str:
    ev = {
        "direction": "`phase2_pairs.csv` + `phase2_s2/s3/s4_result.json` (WS-NEWS2 #121-#123)",
        "jump": "`phase2_s0_result.json` / `phase2_s1_result.json` (WS-NEWS2)",
        "power": "`p2_power_rank_{INST}[_t24].csv` (WS-NEWS3 M2, #125)",
        "premium": "`p1_events_{INST}.csv` / `p1_ride_{INST}.csv` (WS-NEWS3 M1, #124)",
        "deployment": "`src/deploy/data/release_schedule.csv` (WS-DEPLOY #127-#132, v5.3.0)",
    }
    L = []
    L.append("# NEWS coverage matrix — what was tested, partially tested, never tested\n")
    L.append("**WS-NEWS4 / N1 (#135).** Generated by "
             "`subprojects/Parametric-Indicators/optimize/fundamentals/news4_coverage_matrix.py` "
             "from the evidence files directly — regenerate, never hand-edit. "
             f"Usable window ≥ {USABLE_FROM} (pre-2016 calendar timestamps are DST-broken). "
             f"Universe floor: ≥ {MIN_EVENTS} usable events, plus every series any study touched.\n")
    L.append("## Evidence keys\n")
    for k, v in ev.items():
        L.append(f"- **{k}** — {v}")
    L.append("\n## The matrix\n")
    L.append("Premium $ figures are the M1 grid indicator (LONG, lead 5 min, stop 0.10%, no TP, "
             "gross $/event) — coverage evidence, **not** deployment-grade verdicts.\n")
    hdr = ("| series | n≥2016 | imp | UTC | shared-min | direction | power | premium | "
           "M1 long $/ev | deployed |")
    L.append(hdr)
    L.append("|" + "---|" * 10)
    for t, r in m.iterrows():
        shared = f"{r['shared_minute_frac']:.0%}"
        if r["top_shared_partner"]:
            shared += f" ({r['top_shared_partner'][:24]})"
        L.append(
            f"| {t} | {int(r['n_usable'])} | {int(r['tv_importance_max'])} | "
            f"{r['top_utc_time']} | {shared} | {r['direction_status']} | "
            f"{r['power_status']} | {r['premium_status']} | "
            f"{r.get('premium_m1_long_usd') if isinstance(r.get('premium_m1_long_usd'), str) else ''} | "
            f"{r['deployment_status']} |"
        )
    L.append("\n## N2 scan candidates (premium NEVER tested, powered universe)\n")
    L.append("Per-series view (`news4_n2_candidates.csv`) — but the honest scan unit is the "
             "**release moment** below: co-released titles collapse to one minute.\n")
    L.append("| series | n≥2016 | UTC | timestamp quality | shared-minute |")
    L.append("|" + "---|" * 5)
    for t, r in cand.iterrows():
        L.append(
            f"| {t} | {int(r['n_usable'])} | {r['top_utc_time']} | {r['timestamp_quality']} | "
            f"{r['shared_minute_frac']:.0%} |"
        )
    L.append("\n## N2 scan units — untested release MOMENTS grouped by anchor series\n")
    L.append("Distinct usable minutes (≥2016) NOT containing any premium-tested series "
             "(CPI/NFP/FOMC/Retail/Durables/EIA-crude/API), grouped by the block's anchor "
             "(its highest-frequency member). `news4_n2_moments.csv` is the machine copy.\n")
    L.append("| anchor series | untested moments | signature variants | UTC | max block size |")
    L.append("|" + "---|" * 5)
    for t, r in moments[moments["n_moments"] >= MIN_EVENTS].iterrows():
        L.append(
            f"| {t} | {int(r['n_moments'])} | {int(r['n_signatures'])} | "
            f"{r['top_utc_time']} | {int(r['max_block'])} |"
        )
    L.append("\n## Known traps encoded here\n")
    L.append("- **Initial Jobless Claims is TradingView importance 0** — any importance≥1 filter "
             "silently drops the single highest-frequency macro release (556 usable events).")
    L.append("- **Co-released minutes**: the deployed dedupe-by-minute means e.g. Unemployment Rate "
             "(with NFP) and Core CPI (with CPI) are implicitly inside deployed events — the "
             "shared-minute column quantifies this per series.")
    L.append("- Direction/jump coverage is 8 instruments (NQ/ES/RTY/GC/SI/CL/NG/HG) — **YM absent** "
             "(0-byte 1m frame, WS-NEWS2).")
    L.append("- Premium coverage is 5 series × NQ/RTY/ES/GC (+ EIA/API on CL, provenance "
             "unverified) — the funnel's provenance restriction does NOT apply to the "
             "timestamps-only ride, which is exactly N2's opening.")
    return "\n".join(L) + "\n"


def main() -> None:
    m = build()
    cand = n2_candidates(m)
    moments = n2_moments()
    m.to_csv(HERE / "news4_coverage_matrix.csv")
    cand.to_csv(HERE / "news4_n2_candidates.csv")
    moments.to_csv(HERE / "news4_n2_moments.csv")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "NEWS-COVERAGE-MATRIX.md").write_text(render_md(m, cand, moments))
    print(f"series in matrix: {len(m)}")
    print(m["premium_status"].value_counts().to_string())
    print(f"N2 candidate series: {len(cand)}")
    big = moments[moments["n_moments"] >= MIN_EVENTS]
    print(f"N2 moment groups >= {MIN_EVENTS}: {len(big)} "
          f"(total untested moments in them: {int(big['n_moments'].sum())})")
    print(big.head(40).to_string())


if __name__ == "__main__":
    main()
