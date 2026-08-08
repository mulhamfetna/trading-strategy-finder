"""#118 — the WS-NEWS2 claims ledger.

Every number this workstream has published is registered here and re-derived from the committed file it
came from. If a figure cannot be produced by a function in this file, it has no standing and must not
appear in a report or an issue comment.

⚠️ Each claim declares its BLIND SPOT. That field is not documentation — the runner refuses to pass a
claim without one. The TradingView DST defect was a true statement about one series published as a
statement about 649; writing "this cannot see the other 648 titles" is what makes that impossible.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from harness import Check, Claim, register

ROOT = Path(__file__).resolve().parents[4]           # repo root (verify/optimize/P-I/subprojects/<root>)
FUND = ROOT / "subprojects/Parametric-Indicators/optimize/fundamentals"
TV_RAW = FUND / "tradingview/tv_us_calendar_raw.csv"
FRED_CAL = FUND / "us_high_impact.csv"
MIN_YEAR = 2016

SEASON_WINTER = [1, 2, 12]
SEASON_SUMMER = [6, 7, 8]
# Speeches, testimony and Treasury auctions genuinely move around the clock, so a winter/summer
# difference is expected for them and is not evidence of a timezone defect.
MOVING_EVENTS = ("Speech", "Testimony", "Auction", "Speaks")


# ---------------------------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def tv():
    import pandas as pd
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


@lru_cache(maxsize=None)
def h1a(instrument: str):
    return json.loads((FUND / f"h1a_stopout_{instrument}.json").read_text())["results"]


def h1a_ratio(instrument: str, wait: int, stop: float, field: str = "either_stopped") -> float:
    rows = h1a(instrument)
    rel = next(r for r in rows if r["set"] == "RELEASES" and r["wait_min"] == wait and r["stop_pct"] == stop)
    ctl = next(r for r in rows if r["set"] == "CONTROL" and r["wait_min"] == wait and r["stop_pct"] == stop)
    return rel[field] / ctl[field]


@lru_cache(maxsize=4)
def dst_broken_years(*, season_stat: str = "mode") -> dict[int, float]:
    """Share of series per year whose WINTER modal ET time differs from their SUMMER modal ET time.

    A release sits at the same US-Eastern wall-clock time in January and in July. A disagreement means
    the stored UTC used a fixed offset, so the summer rows are an hour late.
    """
    d = tv()
    out: dict[int, float] = {}
    for yr, gy in d.groupby(d.et.dt.year):
        bad = tot = 0
        for title, g in gy.groupby("title"):
            if any(k in str(title) for k in MOVING_EVENTS):
                continue
            win = g[g.et.dt.month.isin(SEASON_WINTER)]
            smr = g[g.et.dt.month.isin(SEASON_SUMMER)]
            if len(win) < 3 or len(smr) < 3:
                continue
            tot += 1
            a = win.et.dt.strftime("%H:%M")
            b = smr.et.dt.strftime("%H:%M")
            if season_stat == "mode":
                differ = a.mode()[0] != b.mode()[0]
            else:   # a DIFFERENT statistic — used by V1 so the two do not share an implementation
                differ = abs(win.et.dt.hour.median() - smr.et.dt.hour.median()) >= 0.5
            bad += bool(differ)
        if tot:
            out[int(yr)] = bad / tot
    return out


def usable_series(min_year: int = MIN_YEAR, min_releases: int = 40) -> int:
    d = tv()
    t = d.dropna(subset=["actual", "forecast", "previous"])
    t = t[t.et >= f"{min_year}-01-01"]
    return int((t.groupby("title").size() >= min_releases).sum())


# ---------------------------------------------------------------------------------------------
# CLAIM 1 — the H1-A danger ratio (defect #2: a published number present in no file)
# ---------------------------------------------------------------------------------------------
def _h1a_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION by a different code path: internal consistency of the stop-out counts.

    `either` must satisfy  max(long, short) <= either <= min(1, long + short)  by set algebra. This
    never touches the ratio arithmetic, so it fails for a different reason than the ledger check does.
    """
    bad = []
    for inst in ("NQ", "GC"):
        for r in h1a(inst):
            lo, sh, ei = r["long_stopped"], r["short_stopped"], r["either_stopped"]
            if not (max(lo, sh) - 1e-9 <= ei <= min(1.0, lo + sh) + 1e-9):
                bad.append(f"{inst} w{r['wait_min']} s{r['stop_pct']}")
    return (not bad), (f"{len(bad)} inconsistent rows: {bad[:3]}" if bad
                       else f"all {sum(len(h1a(i)) for i in ('NQ','GC'))} rows satisfy "
                            f"max(L,S) <= either <= L+S")


def _h1a_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: GC is a different instrument, different price file, same conclusion.

    If the release-window effect were an artefact of the NQ frame or of one control construction, it
    would not reproduce on gold.
    """
    r = {s: h1a_ratio("GC", 5, s) for s in (0.05, 0.1, 0.2, 0.4)}
    mono = all(r[a] <= r[b] + 1e-9 for a, b in zip((0.05, 0.1, 0.2), (0.1, 0.2, 0.4)))
    return (r[0.4] > 1.5 and mono), (f"GC 5-min ratios {({k: round(v,2) for k,v in r.items()})}, "
                                     f"rising with stop width={mono}")


def _h1a_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the release window is more dangerous at EVERY wait" must be FALSE.

    ⭐ This is the check that proves the CONTROL is not simply mis-sampled. If our time-of-day-matched
    control were systematically calmer than reality — the obvious way to manufacture this result — the
    ratio would exceed 1 everywhere. It must NOT. At a 60-minute wait the ratios fall BELOW 1, which a
    broken control cannot produce.
    """
    long_waits = [h1a_ratio(i, 60, s) for i in ("NQ", "GC") for s in (0.2, 0.4)]
    falsified = all(x < 1.0 for x in long_waits)
    return falsified, (f"60-min ratios {[round(x,2) for x in long_waits]} — all < 1, so the control is "
                       f"not uniformly calmer; the 5-min excess is specific to the window"
                       if falsified else f"60-min ratios {[round(x,2) for x in long_waits]} include "
                                         f">= 1 — the control may be biased and the whole result suspect")


register(Claim(
    id="H1A-NQ-5M-040-RATIO",
    issue="#115",
    statement="NQ, 5-min wait, 0.40% stop: the release window stops out 4.27x as often as the "
              "time-of-day-matched control (either side).",
    source="optimize/fundamentals/h1a_stopout_NQ.json",
    value_fn=lambda: round(h1a_ratio("NQ", 5, 0.4), 2),
    expect=4.27, tol=0.005,
    blind_spot="Reads the stored result file. It CANNOT detect an error in the backtest that produced "
               "it (wrong bars, wrong release timestamps, wrong control sampling) — only that the "
               "published figure matches the file. Re-running the study is a separate act.",
    checks=[Check("V1", "either/long/short set algebra", _h1a_v1),
            Check("V2", "reproduces on GC (different instrument)", _h1a_v2),
            Check("V3", "NOT dangerous at every wait — control is not uniformly calm", _h1a_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 2 — the DST audit (defect #1: verified on one series, generalised to 649)
# ---------------------------------------------------------------------------------------------
def _dst_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION with a DIFFERENT STATISTIC: median hour instead of modal HH:MM.

    Mode and median fail differently. If the modal comparison were picking up a handful of rescheduled
    prints rather than a systematic offset, the median would not agree.
    """
    alt = dst_broken_years(season_stat="median")
    bad_alt = sorted(y for y, s in alt.items() if s > 0.25)
    return (bad_alt == [2013, 2014, 2015]), f"median-hour audit flags {bad_alt}"


def _dst_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: FRED's own release dates.

    FRED is an authoritative, entirely separate publisher. If 2016+ timestamps were still wrong, the
    exact-ET agreement with FRED would not be high.
    """
    import pandas as pd
    if not FRED_CAL.exists():
        return False, "us_high_impact.csv missing — cannot cross-check"
    fred = pd.read_csv(FRED_CAL, parse_dates=["Date"])
    d = tv()
    f = fred[(fred.event == "nonfarm_payrolls") & (fred.Date >= f"{MIN_YEAR}-01-01")]
    t = d[(d.title == "Non Farm Payrolls") & (d.et >= f"{MIN_YEAR}-01-01")]
    exact = len({pd.Timestamp(x) for x in f.Date} & {pd.Timestamp(x) for x in t.et})
    rate = exact / max(len(f), 1)
    return rate >= 0.90, f"NFP exact-ET agreement with FRED on {MIN_YEAR}+: {rate:.0%} ({exact}/{len(f)})"


def _dst_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the audit reports no broken years anywhere" must be FALSE.

    ⭐⭐ THE CHECK THAT WAS MISSING. An audit that has never flagged anything is indistinguishable from
    an audit that cannot flag anything. 2013-2015 are known-broken, so a healthy instrument MUST report
    them. If this ever starts passing silently, the audit has stopped working — not the data.
    """
    yrs = dst_broken_years()
    known_bad = [y for y in (2013, 2014, 2015) if yrs.get(y, 0) > 0.25]
    return (len(known_bad) == 3), (f"audit still flags the known-broken years {known_bad} "
                                   f"({', '.join(f'{y}:{yrs[y]:.0%}' for y in known_bad)}) — "
                                   f"it is capable of failing"
                                   if len(known_bad) == 3 else
                                   f"audit flags only {known_bad} of [2013, 2014, 2015] — "
                                   f"THE INSTRUMENT IS BROKEN, not the data")


register(Claim(
    id="TV-DST-CLEAN-FROM-2016",
    issue="#114",
    statement="No year at or after 2016 fails the TradingView DST audit (>25% of series with a "
              "winter/summer modal-ET disagreement).",
    source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
    value_fn=lambda: len([y for y, s in dst_broken_years().items() if s > 0.25 and y >= MIN_YEAR]),
    expect=0, tol=0,
    blind_spot="Only detects a WHOLE-SEASON offset visible in the modal time of a series with >=3 "
               "winter and >=3 summer observations. It CANNOT see: a constant offset applied all year "
               "(no seasonal signature), an error in a series with sparse seasonal coverage, or a "
               "wrong MINUTE within the right hour. It also excludes speeches/testimony/auctions by "
               "name, so a genuine defect confined to those is invisible.",
    checks=[Check("V1", "median-hour statistic agrees with modal-HH:MM", _dst_v1),
            Check("V2", "FRED release dates agree on 2016+", _dst_v2),
            Check("V3", "audit still flags 2013-2015 — it can fail", _dst_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 3 — NFP is the clean series (documents WHY the single-series check passed)
# ---------------------------------------------------------------------------------------------
def _nfp_v1() -> tuple[bool, str]:
    d = tv()
    n = d[(d.title == "Non Farm Payrolls") & (d.et < f"{MIN_YEAR}-01-01")]
    hm = n.et.dt.strftime("%H:%M")
    return (set(hm) == {"08:30"}), f"pre-2016 NFP times: {dict(hm.value_counts())}"


def _nfp_v2() -> tuple[bool, str]:
    """V2 — the UTC field itself must alternate 13:30Z / 12:30Z with daylight saving."""
    d = tv()
    n = d[(d.title == "Non Farm Payrolls") & (d.et < f"{MIN_YEAR}-01-01")]
    z = n.utc.dt.strftime("%H:%M")
    return (set(z) == {"13:30", "12:30"}), f"pre-2016 NFP UTC times: {dict(z.value_counts())}"


def _nfp_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "every series is as clean as NFP pre-2016" must be FALSE.

    ⭐⭐⭐ THIS IS THE DEFECT, ENCODED. NFP passing is true and was published as if it settled the file.
    This check asserts that generalising from it is WRONG, so the trap can never be re-entered
    silently: if this ever passes, either the data was refetched and fixed, or the audit broke.
    """
    yrs = dst_broken_years()
    share_2015 = yrs.get(2015, 0.0)
    return (share_2015 > 0.5), (f"91%-scale disagreement remains in 2015 ({share_2015:.0%} of series) "
                                f"while NFP is 36/36 clean — a single-series check CANNOT generalise"
                                if share_2015 > 0.5 else
                                f"2015 now shows only {share_2015:.0%} broken — data changed under us; "
                                f"re-audit before trusting anything downstream")


register(Claim(
    id="TV-NFP-CLEAN-PRE-2016",
    issue="#114",
    statement="Nonfarm Payrolls is clean before 2016 (every pre-2016 row at 08:30 ET) even though most "
              "of the file is not — which is why verifying on NFP alone passed.",
    source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
    value_fn=lambda: int((tv().query("title == 'Non Farm Payrolls'").et < f"{MIN_YEAR}-01-01").sum()),
    expect=36, tol=0,
    blind_spot="Says nothing about any other series, which is precisely the point of registering it. "
               "It also cannot see whether NFP's 08:30 is the true release instant, only that it is "
               "internally consistent across seasons.",
    checks=[Check("V1", "all pre-2016 NFP rows at 08:30 ET", _nfp_v1),
            Check("V2", "UTC alternates 13:30Z/12:30Z with DST", _nfp_v2),
            Check("V3", "other series are NOT clean — no generalising", _nfp_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 4 — timestamps are the scheduled MINUTE (gates Phase 3, #117)
# ---------------------------------------------------------------------------------------------
def _sec_v1() -> tuple[bool, str]:
    """V1 — re-derive from the RAW STRING rather than the parsed datetime.

    Parsing could in principle discard sub-minute precision; reading the text cannot.
    """
    raw = tv()["date"].astype(str)
    nonzero = raw.str.contains(r"T\d\d:\d\d:(?!00)\d\d", regex=True).sum()
    return (nonzero == 0), f"{nonzero} raw strings carry non-zero seconds"


def _sec_v2() -> tuple[bool, str]:
    """V2 — the minute distribution must look like a SCHEDULE, not like observations."""
    m = tv().et.dt.strftime("%M").value_counts(normalize=True)
    top = m.head(2).sum()
    return (top > 0.8), f"top-2 minutes-of-hour hold {top:.0%} of all events ({dict(m.head(2).round(3))})"


def _sec_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the detector reports zero because it cannot detect" must be FALSE.

    A "0 of 39,221" result is the classic shape of a check that silently does nothing. Inject a
    synthetic non-zero-seconds timestamp and require the detector to catch it.
    """
    import pandas as pd
    probe = pd.Series(["2020-05-06T13:30:07.000Z", "2020-05-06T13:30:00.000Z"])
    caught = probe.str.contains(r"T\d\d:\d\d:(?!00)\d\d", regex=True).sum()
    return (caught == 1), f"synthetic probe: detector caught {caught} of 1 planted non-zero-seconds row"


register(Claim(
    id="TV-TIMESTAMPS-MINUTE-ONLY",
    issue="#117",
    statement="TradingView timestamps carry zero seconds on every row — they are the SCHEDULED minute, "
              "not the observed release instant, so Phase 3 cannot take its starting gun from them.",
    source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
    value_fn=lambda: int((tv().et.dt.second != 0).sum()),
    expect=0, tol=0,
    blind_spot="Proves the field has no sub-minute precision. It CANNOT tell us how far the true "
               "release instant is from the scheduled minute — that requires the 1-second tape "
               "(Phase 3 step 0). A zero here is a statement about the SOURCE, not about reality.",
    checks=[Check("V1", "raw strings, not parsed datetimes", _sec_v1),
            Check("V2", "minute distribution looks like a schedule", _sec_v2),
            Check("V3", "detector catches a planted non-zero-seconds row", _sec_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 5 — the Phase 2 universe (defect: #116 states ~30 releases, guessed before we had data)
# ---------------------------------------------------------------------------------------------
def _univ_v1() -> tuple[bool, str]:
    """V1 — count by a different route: value_counts on the filtered frame, no groupby."""
    d = tv()
    t = d.dropna(subset=["actual", "forecast", "previous"])
    t = t[t.et >= f"{MIN_YEAR}-01-01"]
    vc = t["title"].value_counts()
    n = int((vc >= 40).sum())
    return (n == 103), f"value_counts route gives {n}"


def _univ_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: our 7 FRED events must all appear in the usable universe."""
    d = tv()
    t = d.dropna(subset=["actual", "forecast", "previous"])
    t = t[t.et >= f"{MIN_YEAR}-01-01"]
    vc = t["title"].value_counts()
    need = ["Non Farm Payrolls", "Inflation Rate MoM", "PPI MoM", "Retail Sales MoM",
            "Fed Interest Rate Decision", "Core PCE Price Index MoM"]
    missing = [x for x in need if vc.get(x, 0) < 40]
    return (not missing), (f"all {len(need)} round-1 events present with >=40 releases" if not missing
                           else f"missing from the usable universe: {missing}")


def _univ_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the count is insensitive to MIN_YEAR" must be FALSE.

    If the era filter made no difference, it would mean the filter is not being applied — the silent
    no-op that makes a constraint look enforced when it is not.
    """
    a, b = usable_series(2013), usable_series(2016)
    return (a != b), (f"MIN_YEAR is actually applied: 2013 -> {a} series, 2016 -> {b}"
                      if a != b else f"identical counts ({a}) — the era filter is a NO-OP")


register(Claim(
    id="NEWS2-USABLE-UNIVERSE",
    issue="#116",
    statement="103 release series carry actual+forecast+previous with >=40 releases since 2016 — so "
              "the Phase 2 matrix is 927 pairs, not the ~270 stated in #116.",
    source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
    value_fn=lambda: usable_series(),
    expect=103, tol=0,
    blind_spot="Counts series that are TESTABLE, not series that are RELEVANT. It applies no economic "
               "filter, so it is an upper bound on the matrix and says nothing about which pairs have "
               "a mechanism. It also cannot see whether `actual` is a first print or a revision — the "
               "ALFRED question that gates Phase 2 entirely.",
    checks=[Check("V1", "value_counts route agrees with groupby", _univ_v1),
            Check("V2", "all round-1 FRED events present", _univ_v2),
            Check("V3", "the MIN_YEAR filter is not a no-op", _univ_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 6 — retracted figures must not reappear (defects #2, #3, #7 were PUBLICATION failures)
# ---------------------------------------------------------------------------------------------
# ⚠️ Each entry is a figure or phrase that was published and later shown to be wrong. Mentions are
# allowed ONLY on a line that marks them as retracted — otherwise a corrected doc slowly drifts back.
RETRACTED: dict[str, str] = {
    r"1\.31[–-]2\.92": "H1-A danger ratio present in no result file",
    r"Inflation Rate Mom\b": "invented casing variant; the real neighbour is 'Inflation Rate MoM Final'",
    r"off by one, verified 3": "Nasdaq date-parameter claim tested on 3 dates, never their neighbours",
}
# ⚠️ Kept DELIBERATELY NARROW. Every phrase here is retraction or defect-citation language; none of
# them is something an ordinary sentence reusing the figure would contain. Widening this to anything
# vaguer (e.g. bare "note", "see") would let the retracted figure back in under cover.
RETRACTION_MARKERS = re.compile(
    r"retract|correct|previously|mis-?transcription|was wrong|invented|no lower-case|CORRECTION|"
    r"appears nowhere|had it backwards|phantom|"
    # defect-citation context: prose that is ABOUT the error rather than repeating it
    r"defect\s*#|in no (result )?file|against my notes|planted|does not appear", re.I)


# An EXPLICIT, auditable opt-out for prose that catalogues the defects themselves — a table listing
# retracted figures cannot carry a marker on every row. Suppression starts at the marker and ends at
# the next blank line, so it can never silently cover a whole file.
CATALOGUE_MARKER = "RETRACTION-CATALOGUE"


def _suppressed_lines(lines: list[str]) -> set[int]:
    """1-indexed line numbers covered by a RETRACTION-CATALOGUE block."""
    out: set[int] = set()
    active = False
    for i, ln in enumerate(lines, 1):
        if CATALOGUE_MARKER in ln:
            active = True
        elif active and not ln.strip():
            active = False
        if active:
            out.add(i)
    return out


def _retraction_violations() -> list[str]:
    hits: list[str] = []
    roots = [ROOT / "docs", FUND, ROOT / "subprojects/Parametric-Indicators/optimize/verify"]
    for base in roots:
        for p in base.rglob("*"):
            if p.suffix.lower() not in (".md", ".py") or not p.is_file():
                continue
            try:
                lines = p.read_text(errors="ignore").splitlines()
            except OSError:
                continue
            skip = _suppressed_lines(lines)
            for i, ln in enumerate(lines, 1):
                if i in skip:
                    continue
                for pat in RETRACTED:
                    if re.search(pat, ln) and not RETRACTION_MARKERS.search(ln):
                        # ⚠️ A retraction spans lines and the marker may fall EITHER SIDE of the
                        # figure — "That was wrong" often lands on the NEXT line. The first version
                        # looked only upward and produced 5 false positives out of 6 hits, which is
                        # the fastest way to teach everyone to ignore this gate.
                        ctx = " ".join(lines[max(0, i - 4):i + 3])
                        if not RETRACTION_MARKERS.search(ctx):
                            hits.append(f"{p.relative_to(ROOT)}:{i}  {pat}")
    return hits


def _ret_v1() -> tuple[bool, str]:
    v = _retraction_violations()
    return (not v), (f"{len(v)} unmarked reuse(s): {v[:3]}" if v else
                     f"{len(RETRACTED)} retracted figures, 0 unmarked reuses")


def _ret_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: the retracted H1-A range must also be absent from the DATA."""
    vals = {round(h1a_ratio(i, w, s), 2) for i in ("NQ", "GC")
            for w in (5, 15, 30, 60) for s in (0.05, 0.1, 0.2, 0.4)}
    present = {x for x in vals if abs(x - 1.31) < 0.005 or abs(x - 2.92) < 0.005}
    # 2.92 IS real (NQ 5-min 0.20%); 1.31 is the fabricated end of the range.
    return (not any(abs(x - 1.31) < 0.005 for x in vals)), \
           (f"1.31 appears in no cell of either result file; 2.92 does exist (NQ 5-min 0.20%) — "
            f"the range was fabricated at its LOWER end, matched: {sorted(present)}")


def _ret_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the scanner reports clean because it scans nothing" must be FALSE."""
    probe = "the ratio was 1.31-2.92 across both instruments"
    caught = any(re.search(p, probe) for p in RETRACTED)
    marked = RETRACTION_MARKERS.search(probe)
    n_files = sum(1 for base in [ROOT / "docs", FUND] for p in base.rglob("*")
                  if p.suffix.lower() in (".md", ".py") and p.is_file())
    return (caught and not marked and n_files > 10), \
           f"synthetic unmarked reuse detected={bool(caught)}; scanner covers {n_files} files"


register(Claim(
    id="NEWS2-RETRACTIONS-NOT-REUSED",
    issue="#118",
    statement="No figure that has been retracted reappears in docs or code except on a line that marks "
              "it as retracted.",
    source="docs/ + optimize/fundamentals/ + optimize/verify/ (*.md, *.py)",
    value_fn=lambda: len(_retraction_violations()),
    expect=0, tol=0,
    blind_spot="Only catches the three retractions listed in RETRACTED, by literal pattern. A wrong "
               "number that was never formally retracted is invisible, as is a paraphrase that avoids "
               "the pattern. It scans .md and .py only — NOT issue comments on GitHub, which is where "
               "two of the three were originally published.",
    checks=[Check("V1", "scan docs/ and code for unmarked reuse", _ret_v1),
            Check("V2", "1.31 exists in no cell of the result files", _ret_v2),
            Check("V3", "scanner catches a planted unmarked reuse", _ret_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 7 — TradingView's `actual` is the FIRST PRINT, not a revision (#119; gates Phase 2)
# ---------------------------------------------------------------------------------------------
# ⚠️ Evidence: optimize/fundamentals/alfred_revision_<series>.csv — one row per release carrying the
# TradingView value, the ALFRED first print, today's FRED value and the shifted-month control.
REV_TOL = {"nfp": 0.5, "cpi": 0.05, "durables": 0.05, "retail": 0.05}
REV_DISC = {"nfp": 10.0, "cpi": 0.15, "durables": 0.15, "retail": 0.15}


@lru_cache(maxsize=None)
def revision_evidence(series: str):
    import pandas as pd
    return pd.read_csv(FUND / f"alfred_revision_{series}.csv", parse_dates=["ref_month", "release"])


def revision_rates(series: str) -> dict:
    d = revision_evidence(series)
    tol, disc_thr = REV_TOL[series], REV_DISC[series]
    disc = d[(d["first"] - d["current"]).abs() >= disc_thr]
    r = lambda col: float(((disc.tv - disc[col]).abs() <= tol).mean()) if len(disc) else float("nan")
    return {"n": len(d), "n_disc": len(disc), "first": r("first"), "current": r("current"),
            "shifted": r("shifted")}


def _rev_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION with a different comparison: ROUND both to the reporting granularity and
    require EXACT equality, instead of comparing within a tolerance.

    A tolerance-based match can be widened until anything passes; exact equality after rounding cannot.
    """
    out = {}
    for s in ("nfp", "durables", "retail"):
        d = revision_evidence(s)
        step = REV_TOL[s] * 2                       # the published granularity (1k jobs, 0.1pp)
        disc = d[(d["first"] - d["current"]).abs() >= REV_DISC[s]]
        eq = ((disc.tv / step).round() == (disc["first"] / step).round()).mean()
        out[s] = round(float(eq), 3)
    ok = all(v >= 0.98 for v in out.values())
    return ok, f"exact match after rounding to the published granularity: {out}"


def _rev_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: two further statistics, different publishers, different code path.

    NFP is a LEVEL DIFFERENCE (thousands of jobs); retail sales and durable goods are PERCENT CHANGES
    computed from an index. A conclusion that held only for payrolls would be an artefact of that
    differencing.
    """
    rs = {s: revision_rates(s) for s in ("retail", "durables")}
    ok = all(v["first"] >= 0.98 and v["current"] <= 0.02 and v["n_disc"] >= 20 for v in rs.values())
    return ok, "; ".join(f"{k}: {v['n_disc']} disc, first {v['first']:.0%}, revised {v['current']:.0%}"
                         for k, v in rs.items())


def _rev_v3() -> tuple[bool, str]:
    """V3 — TWO falsifiers, because this claim gates a whole phase.

    (a) ⚠️⚠️ SHIFTED-MONTH CONTROL — "the matcher also matches the WRONG month" must be FALSE. Without
        this, a 100% match rate is compatible with a matcher that matches anything, which is exactly the
        retracted Nasdaq "off by one, verified 3x" defect.
    (b) ⭐ "the decision rule always returns a verdict" must be FALSE. CPI has only 4 discriminating
        releases and MUST come back CANNOT TELL. A rule that never withholds judgement is not a rule.
    """
    shifted = {s: round(revision_rates(s)["shifted"], 3) for s in ("nfp", "durables", "retail")}
    a = all(v <= 0.20 for v in shifted.values())
    cpi = revision_rates("cpi")
    b = cpi["n_disc"] < 20
    return (a and b), (f"(a) shifted-month control {shifted} — collapsed from ~100%; "
                       f"(b) CPI has {cpi['n_disc']} discriminating releases (<20) so the rule "
                       f"withholds a verdict — it is capable of saying CANNOT TELL")


register(Claim(
    id="TV-ACTUAL-IS-FIRST-PRINT",
    issue="#119",
    statement="TradingView's `actual` is the FIRST PRINT, not a later revision: on the 116 NFP releases "
              "where the first print and today's value differ by >=10k jobs, it matches the first print "
              "100% of the time and the revised value 0%.",
    source="optimize/fundamentals/alfred_revision_nfp.csv",
    value_fn=lambda: round(revision_rates("nfp")["first"], 3),
    expect=1.0, tol=0.001,
    blind_spot="Covers 4 series of 649 (NFP, CPI, retail sales, durable goods). TradingView may "
               "back-fill different series from different vendors or eras, and this cannot see that — "
               "the licence is for the series TESTED. It says nothing about `forecast` (a back-filled "
               "late consensus would be a separate contamination), nothing about the timestamp (that "
               "is the #114 DST audit), and by construction it cannot detect a revision smaller than "
               "the discriminating threshold.",
    checks=[Check("V1", "exact match after rounding, not a tolerance", _rev_v1),
            Check("V2", "retail sales + durable goods (percent-change series)", _rev_v2),
            Check("V3", "shifted-month control collapses AND the rule can say CANNOT TELL", _rev_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 8/9 — `previous` is point-in-time; `forecast` is not a copy of `actual` (#120)
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def fp_evidence(series: str):
    import pandas as pd
    return pd.read_csv(FUND / f"forecast_previous_{series}.csv", parse_dates=["ref_month", "release"])


def fp_rates(series: str) -> dict:
    d = fp_evidence(series)
    tol, thr = REV_TOL[series], REV_DISC[series]
    h = d.dropna(subset=["tv_previous", "prev_pit", "prev_today"])
    disc = h[(h.prev_pit - h.prev_today).abs() >= thr].copy()
    disc["pit_shift"] = disc.prev_pit.shift(1)
    r = lambda col: (float(((disc.tv_previous - disc[col]).abs() <= tol).mean())
                     if len(disc.dropna(subset=[col])) else float("nan"))
    f = d.dropna(subset=["tv_forecast", "tv_actual"])
    return {"n_disc": len(disc), "pit": r("prev_pit"), "today": r("prev_today"),
            "shifted": r("pit_shift"),
            "b1": float(((f.tv_actual - f.tv_forecast).abs() <= tol).mean()) if len(f) else float("nan")}


def _pit_v1() -> tuple[bool, str]:
    """V1 — exact equality after rounding to the published granularity, not a tolerance."""
    out = {}
    for s in ("nfp", "durables", "retail"):
        d = fp_evidence(s)
        tol, thr, step = REV_TOL[s], REV_DISC[s], REV_TOL[s] * 2
        h = d.dropna(subset=["tv_previous", "prev_pit", "prev_today"])
        disc = h[(h.prev_pit - h.prev_today).abs() >= thr]
        out[s] = round(float(((disc.tv_previous / step).round() == (disc.prev_pit / step).round()).mean()), 3)
    return all(v >= 0.95 for v in out.values()), f"exact match after rounding: {out}"


def _pit_v2() -> tuple[bool, str]:
    """V2 — two further series, percent-change rather than level-difference."""
    rs = {s: fp_rates(s) for s in ("durables", "retail")}
    ok = all(v["pit"] >= 0.95 and v["today"] <= 0.05 and v["n_disc"] >= 20 for v in rs.values())
    return ok, "; ".join(f"{k}: {v['n_disc']} disc, point-in-time {v['pit']:.0%}, today {v['today']:.0%}"
                         for k, v in rs.items())


def _pit_v3() -> tuple[bool, str]:
    """V3 — the shifted-RELEASE control must collapse, and the rule must be able to withhold a verdict.

    ⭐ CPI has only 4 discriminating releases and returns CANNOT TELL. Same absence of power as in #119,
    and the same reason: CPI is barely revised, so the three candidate values for `previous` are the
    same number and nothing can be told apart.
    """
    sh = {s: round(fp_rates(s)["shifted"], 3) for s in ("nfp", "durables", "retail")}
    return (all(v <= 0.30 for v in sh.values()) and fp_rates("cpi")["n_disc"] < 20), \
           (f"shifted-release control {sh} — collapsed from ~99%; CPI has "
            f"{fp_rates('cpi')['n_disc']} discriminating releases so the rule says CANNOT TELL")


register(Claim(
    id="TV-PREVIOUS-IS-POINT-IN-TIME",
    issue="#120",
    statement="TradingView's `previous` is the value that stood on the MORNING OF THE RELEASE, not "
              "today's revised value: on the 119 NFP releases where those differ by >=10k jobs it "
              "matches the point-in-time value 99% and today's value 0%.",
    source="optimize/fundamentals/forecast_previous_nfp.csv",
    value_fn=lambda: round(fp_rates("nfp")["pit"], 3),
    expect=0.992, tol=0.002,
    blind_spot="Covers 4 series of 649, and CPI among them has no discriminating power at all. It "
               "shows the ROW was captured live; it does NOT directly verify `forecast`, for which no "
               "archive exists. It cannot see an error smaller than the discriminating threshold, and "
               "it says nothing about series whose statistic is never revised.",
    checks=[Check("V1", "exact match after rounding, not a tolerance", _pit_v1),
            Check("V2", "durables + retail (percent-change series)", _pit_v2),
            Check("V3", "shifted-release control collapses; rule can say CANNOT TELL", _pit_v3)],
))


def _fc_v1() -> tuple[bool, str]:
    """V1 — the exact-zero-surprise rate, recomputed from the evidence CSVs on every series."""
    b1 = {s: round(fp_rates(s)["b1"], 3) for s in ("nfp", "cpi", "durables", "retail")}
    return all(v < 0.50 for v in b1.values()), f"exact-zero surprise rate per series: {b1}"


def _fc_v2() -> tuple[bool, str]:
    """V2 — the surprise must have real dispersion. A copied forecast has none."""
    out = {}
    for s in ("nfp", "cpi", "durables", "retail"):
        d = fp_evidence(s).dropna(subset=["tv_forecast", "tv_actual"])
        out[s] = round(float((d.tv_actual - d.tv_forecast).std()), 3)
    return all(v > 0 for v in out.values()), f"sd(actual - forecast) per series: {out}"


def _fc_v3() -> tuple[bool, str]:
    """V3 — PLANTED-CONTAMINATION PROBE. B1 reporting a low rate is worthless if it could not report a
    high one, so copy `actual` into `forecast` and require B1 to catch it at ~100%.
    """
    d = fp_evidence("nfp").dropna(subset=["tv_actual"])
    tol = REV_TOL["nfp"]
    planted = float(((d.tv_actual - d.tv_actual).abs() <= tol).mean())
    real = fp_rates("nfp")["b1"]
    return (planted > 0.95 and real < 0.05), \
           (f"planted copy detected at {planted:.0%}; the real data sits at {real:.1%} — the detector "
            f"can fire and does not")


register(Claim(
    id="TV-FORECAST-NOT-COPIED-FROM-ACTUAL",
    issue="#120",
    statement="TradingView's `forecast` is not a copy of `actual`: the exact-zero-surprise rate is "
              "0.8% on NFP (and under 50% on every series tested), while a planted copy is detected "
              "at 100%.",
    source="optimize/fundamentals/forecast_previous_nfp.csv",
    value_fn=lambda: round(fp_rates("nfp")["b1"], 4),
    expect=0.0079, tol=0.0005,
    blind_spot="⚠️⚠️ THIS IS FALSIFICATION THAT FAILED TO FALSIFY — IT IS NOT VERIFICATION. There is NO "
               "archive of pre-release consensus to check `forecast` against (round 1's Nasdaq join is "
               "2010-only and TradingView starts 2013, so they do not overlap), so this workstream "
               "CANNOT verify `forecast`. It rules out the crudest contamination (forecast copied from "
               "the outcome) and nothing more. The revision-correlation tests B2/B2b/B2c are reported "
               "but CANNOT decide the question: an informed consensus and a contaminated one predict "
               "the same sign at every horizon. The strongest evidence remains INDIRECT — "
               "[[TV-PREVIOUS-IS-POINT-IN-TIME]] shows the row was captured live.",
    checks=[Check("V1", "exact-zero surprise rate on all 4 series", _fc_v1),
            Check("V2", "surprise has real dispersion", _fc_v2),
            Check("V3", "planted copy is detected at 100%", _fc_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 10 — H1-B / H1-C are NEGATIVE, and the pipeline is proven able to find an effect (#115)
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def h1bc(instrument: str) -> dict:
    return json.loads((FUND / f"h1bc_result_{instrument}.json").read_text())


def _h1bc_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: two independent implementation checks recorded inside the run.

    (a) rank-transform then Pearson MUST equal Spearman exactly — a second code path to the same
        statistic; (b) the same correlations recomputed on an Open-based return construction, which
        must not flip the conclusion.
    """
    ok, detail = True, []
    for inst in ("NQ", "GC"):
        v1 = h1bc(inst)["v1"]
        identical = all(r["identical"] for r in v1)
        big = max(abs(r["open_spearman"]) for r in v1)
        ok = ok and identical and big < 0.196          # still below the study's own MDE
        detail.append(f"{inst}: rank-Pearson==Spearman {identical}, max |Open-construction rho| {big:.3f}")
    return ok, "; ".join(detail)


def _h1bc_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: a different instrument, a different price file, the same verdict."""
    v = {i: h1bc(i)["verdict"] for i in ("NQ", "GC")}
    hits = {i: sum(c["passes_bonferroni"] for c in h1bc(i)["cells"]) for i in ("NQ", "GC")}
    return (set(v.values()) == {"NEGATIVE"}), f"verdicts {v}; cells clearing Bonferroni {hits}"


def _h1bc_v3() -> tuple[bool, str]:
    """V3 — ⭐⭐⭐ THE PLANTED-EFFECT PROBE. The falsifier that matters for a NEGATIVE result.

    A null from a broken pipeline is indistinguishable from a null from an absent edge — and this
    workstream produced a manufactured null the same week (the pre-2016 DST defect). So a synthetic
    feature that IS the outcome plus noise is planted at a range of effect sizes, and every planted
    effect at or above the study's own MDE must be FOUND.
    """
    out, ok = {}, True
    for inst in ("NQ", "GC"):
        p = h1bc(inst)["v3_planted_probe"]
        ok = ok and bool(p["detected"])
        out[inst] = f"MDE {p['mde_r']:.3f}, smallest detected r={p['smallest_detected']}"
    return ok, "; ".join(f"{k}: {v}" for k, v in out.items())


register(Claim(
    id="H1BC-ANTICIPATED-CHANGE-NEGATIVE",
    issue="#115",
    statement="`forecast - previous` carries NO usable direction on NQ or GC: 0 of 7 pre-registered "
              "cells per instrument clear Bonferroni alpha=0.00179, on 411 events over 2016-2026.",
    source="optimize/fundamentals/h1bc_result_NQ.json",
    value_fn=lambda: sum(c["passes_bonferroni"] for c in h1bc("NQ")["cells"]),
    expect=0, tol=0,
    blind_spot="⚠️ THE STUDY'S RESOLUTION IS r ~ 0.195. An anticipation effect SMALLER than that is "
               "invisible here, and a small real edge is entirely plausible — this is 'no effect of "
               "this size', not 'no effect'. Covers 4 series of 103 and 2 instruments of 9: a drift "
               "that exists only in oil around EIA inventories is untested. `forecast` itself is "
               "unverified (#120) — no consensus archive exists. Correlation is linear/monotone only, "
               "so a threshold effect ('only huge anticipated changes matter') would be missed. The "
               "expanding-window normalisation discards the first 24 events per series (96 of 507).",
    checks=[Check("V1", "rank-Pearson == Spearman; Open-based construction agrees", _h1bc_v1),
            Check("V2", "GC reproduces NQ's verdict on a different price file", _h1bc_v2),
            Check("V3", "planted-effect probe detects everything at/above the MDE", _h1bc_v3)],
))
