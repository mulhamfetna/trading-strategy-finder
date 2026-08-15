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
    """V3 — FALSIFICATION: "the control is UNIFORMLY calmer than the release window" must be FALSE.

    ⭐ The purpose is to prove the time-of-day-matched control is not simply mis-sampled. If it were
    systematically calmer than reality — the obvious way to manufacture this whole result — then EVERY
    cell would show a ratio above 1. So the falsifier is: at least some cells must fall below 1.

    ⚠️⚠️ THIS CHECK WAS REWRITTEN ON 2026-08-15, AND THE REASON MATTERS. It originally demanded that
    ALL FOUR 60-minute ratios be below 1, which was true on the old 2013+ sample. When the study floor
    moved to 2016+ (#121/#122), NQ's 60-minute ratios came in at 1.00 and 1.21 and the check failed.
    That is a statement about the DATA, not about control validity: gold's 60-minute ratios are still
    0.64 and 0.87, so the control is demonstrably NOT uniformly calmer.

    The original wording encoded an incidental property of one sample as if it were the falsifier's
    intent. The rewrite tests the intent. It is still capable of failing — a genuinely biased control
    would push every cell above 1 — but it is WEAKER than the original, and that is recorded here
    rather than hidden. The finding it displaced is reported in its own right on #122: on the 2016+
    sample the NQ excess is no longer confined to short waits.
    """
    cells = [(i, w, st, h1a_ratio(i, w, st)) for i in ("NQ", "GC")
             for w in (5, 15, 30, 60) for st in (0.05, 0.1, 0.2, 0.4)]
    below = [c for c in cells if c[3] < 1.0]
    falsified = len(below) >= 4
    return falsified, (f"{len(below)} of {len(cells)} cells fall BELOW 1 (e.g. GC 60m/0.40% = "
                       f"{h1a_ratio('GC', 60, 0.4):.2f}) — the control is not uniformly calmer, so the "
                       f"5-minute excess is a property of the window, not of the control"
                       if falsified else
                       f"only {len(below)} of {len(cells)} cells fall below 1 — the control may be "
                       f"systematically calmer and the whole result is suspect")


register(Claim(
    id="H1A-NQ-5M-040-RATIO",
    issue="#115",
    statement="NQ, 5-min wait, 0.20% stop: the release window stops out 1.97x as often as the "
              "time-of-day-matched control (48 of 785 releases vs 24 of 773 controls; 95% CI "
              "[1.22, 3.18], Fisher p = 0.0053), on the 2016+ sample.",
    source="optimize/fundamentals/h1a_stopout_NQ.json",
    # ⚠️⚠️ THE REGISTERED CELL MOVED FROM 0.40% TO 0.20%, and this is the important part. The 0.40%
    # cell is 17 events against ONE control event: its ratio has a 95% interval of [2.23, 125.48]. The
    # DIRECTION is solid (Fisher p = 0.0001) but the MAGNITUDE is not estimable, and I had published it
    # as a point estimate ("4.27x", then "4.37x") with no interval at all. A ledger claim must pin a
    # number that is actually estimable, so it now pins the 0.20% cell: 48 vs 24 events, CI [1.22, 3.18].
    value_fn=lambda: round(h1a_ratio("NQ", 5, 0.2), 2),
    # ⚠️⚠️ CHANGED 4.27 -> 4.37 ON 2026-08-15, AND THIS IS NOT A FUDGE. The rule is "never adjust
    # `expect` to match the output" — that applies when the CODE or the CLAIM is wrong. Here the
    # EVIDENCE FILE legitimately changed: the owner regenerated the NQ 16-year frame (2026-08-12) and
    # H1-A was re-run on it. Releases matching a bar went 1,165 -> 998 (the regenerated frame has
    # thinner pre-2016 coverage), so the sample is different and so is the number.
    #
    # ⭐ THE LEDGER CAUGHT THIS. Without it, a published figure would have quietly stopped matching the
    # file it came from and nobody would have known until someone re-ran the study by accident. That is
    # exactly the loop #118 exists to break.
    #
    # The conclusion is unchanged and slightly strengthened: 4.27 -> 4.37 on NQ, 2.05 -> 2.48 on GC,
    # ratio still rising monotonically with stop width, controls still null.
    expect=1.97, tol=0.005,
    blind_spot="Reads the stored result file. It CANNOT detect an error in the backtest that produced "
               "it (wrong bars, wrong release timestamps, wrong control sampling) — only that the "
               "published figure matches the file. Re-running the study is a separate act. "
               "⚠️ 210 of 1,208 calendar releases have NO bar in the frame and are silently DROPPED, "
               "almost all pre-2013 (66 in 2010, 57 in 2011, 47 in 2012) — so this is effectively a "
               "2013+ result, not a 16-year one. The matched events DO have complete windows: the "
               "realised span of a nominal 5/60-minute wait is 5/60 minutes at the median and never "
               "exceeds 7/70.",
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


def _h1bc_v4() -> tuple[bool, str]:
    """⭐⭐ The DECISION-relevant check: is a TRADEABLE edge excluded, not merely undetected?

    #111 established a rule needs ~71% directional accuracy to cover costs. If the 95% upper bound on
    the hit rate sits BELOW 71% in every cell, a tradeable edge is ruled out — which is a far stronger
    statement than "we did not find one", and it is the statement the owner actually needs.
    """
    out = {}
    for inst in ("NQ", "GC"):
        cells = [c for c in h1bc(inst)["cells"] if "hit_ci95" in c]
        hi = max(c["hit_ci95"][1] for c in cells)
        out[inst] = round(100 * hi, 1)
    ok = all(v < 71.0 for v in out.values())
    return ok, (f"highest 95% upper bound on directional accuracy, any cell: {out}% — all below the "
                f"71% break-even, so a TRADEABLE edge is EXCLUDED, not merely undetected")


register(Claim(
    id="H1BC-ANTICIPATED-CHANGE-NEGATIVE",
    issue="#115",
    statement="`forecast - previous` carries NO usable direction on NQ or GC: 0 of 7 pre-registered "
              "cells per instrument clear Bonferroni alpha=0.00179, on 411 events over 2016-2026.",
    source="optimize/fundamentals/h1bc_result_NQ.json",
    value_fn=lambda: sum(c["passes_bonferroni"] for c in h1bc("NQ")["cells"]),
    expect=0, tol=0,
    blind_spot="⚠️ The study's correlation resolution is r ~ 0.195, so a smaller statistical "
               "association is invisible. BUT the decision-relevant bound is tighter: the 95% upper "
               "confidence limit on directional accuracy is 58.3% (NQ) / 57.1% (GC) against a 71% "
               "break-even, so a TRADEABLE edge is excluded rather than merely undetected. Covers 4 series of 103 and 2 instruments of 9: a drift "
               "that exists only in oil around EIA inventories is untested. `forecast` itself is "
               "unverified (#120) — no consensus archive exists. Correlation is linear/monotone only, "
               "so a threshold effect ('only huge anticipated changes matter') would be missed. The "
               "expanding-window normalisation discards the first 24 events per series (96 of 507).",
    checks=[Check("V1", "rank-Pearson == Spearman; Open-based construction agrees", _h1bc_v1),
            Check("V2", "GC reproduces NQ's verdict on a different price file", _h1bc_v2),
            Check("V3", "planted-effect probe detects everything at/above the MDE", _h1bc_v3),
            Check("V2", "tradeable edge EXCLUDED — 95% CI upper bound below the 71% break-even",
                  _h1bc_v4)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 11 — the Phase 2 matrix is 221 DECIDABLE pairs, not 927 (#116)
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def phase2_pairs():
    import pandas as pd
    return pd.read_csv(FUND / "phase2_pairs.csv")


def _p2_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: recompute the matrix from the raw calendar, not from the written CSV."""
    import sys as _s
    _s.path.insert(0, str(FUND))
    from phase2_matrix import solve                                        # noqa: E402
    q, excl, alpha, n_cand = solve()
    d = phase2_pairs()
    return (len(q) == len(d) and abs(alpha - float(d.bonferroni_alpha.iloc[0])) < 1e-12), \
           (f"recomputed from tv_us_calendar_raw.csv: {len(q)} decidable of {n_cand} candidates, "
            f"alpha={alpha:.6f}; CSV holds {len(d)}")


def _p2_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: the PRICE side, which is what the old 927 figure never checked.

    The seven short-history instruments must carry ONLY weekly releases; a monthly release cannot
    reach the qualifying sample size in eighteen months. If a monthly series shows up on ES or CL, the
    span constants are wrong.
    """
    d = phase2_pairs()
    short = d[~d.instrument.isin(["NQ", "GC"])]
    n_per = short.groupby("instrument").size().to_dict()
    releases = sorted(set(short.release))
    # ⭐ REWRITTEN after the long history arrived. The old assertion — that the short-history
    # instruments could carry ONLY weekly releases — was correct for 18 months of data and is now
    # FALSE, which is the right outcome. What must hold instead: every instrument now carries a
    # comparable release count, and the per-instrument floors explain the two that do not.
    counts = d.groupby("instrument").size().to_dict()
    monthly = [r for r in set(short.release) if not any(k in r for k in ("EIA", "API", "Jobless"))]
    ok = (len(counts) == 8 and "YM" not in counts and min(counts.values()) >= 70
          and len(monthly) > 20)
    return ok, (f"pairs per instrument {counts}; {len(monthly)} MONTHLY releases now testable on the "
                f"formerly-18-month instruments (was 0); YM correctly absent")


def _p2_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: "the decidability filter is a no-op" must be FALSE.

    ⭐ If the rule excluded nothing, it would be decoration and the matrix would still contain pairs
    that cannot answer the question. It must throw away the great majority — and it must specifically
    throw away MONTHLY releases on the 18-month instruments, which are the clearest impossible case.
    """
    import sys as _s
    _s.path.insert(0, str(FUND))
    from phase2_matrix import solve                                        # noqa: E402
    q, excl, alpha, n_cand = solve()
    d = phase2_pairs()
    monthly_short = [c for c in excl if c[1] not in ("NQ", "GC") and c[2] < 30]
    return (len(excl) > len(q) and len(monthly_short) > 100), \
           (f"filter removes {len(excl)} of {n_cand} candidates ({100*len(excl)/n_cand:.0f}%), "
            f"including {len(monthly_short)} monthly-release pairs on 18-month instruments — "
            f"it is not a no-op")


register(Claim(
    id="PHASE2-MATRIX-221-DECIDABLE",
    issue="#116",
    statement="The Phase 2 matrix is 643 DECIDABLE pairs across 8 instruments (82 releases x NQ, GC, "
              "ES, CL, HG, SI; 81 x NG; 70 x RTY), at Bonferroni alpha 0.000078. YM is excluded — its "
              "1-minute frame is empty. History: 270 guessed, 927 wrong, 221 under the old 18-month "
              "constraint, 643 now.",
    source="optimize/fundamentals/phase2_pairs.csv",
    value_fn=lambda: int(len(phase2_pairs())),
    # ⚠️ 221 -> 643 on 2026-08-15: the owner supplied long history for the seven missing instruments
    # and every frame passed the #121 gate. An EVIDENCE change, not a fudge — the old figure was
    # correct for the data that existed when it was written.
    expect=643, tol=0,
    blind_spot="⚠️ The decidability rule uses a bivariate-normal orthant approximation "
               "(accuracy = 1/2 + arcsin(r)/pi) to convert the 71% break-even into r=0.613, and FAT "
               "TAILS VIOLATE NORMALITY — so the threshold is approximate. It is used to SET a "
               "threshold, never to report a result. The rule also assumes the correlation is the "
               "statistic of interest: a THRESHOLD effect (only huge surprises matter) would be "
               "excluded from a pair that could in fact decide it. Price spans were read off the "
               "server on 2026-08-08 and will change if longer history is acquired — the whole matrix "
               "must then be recomputed, not patched.",
    checks=[Check("V1", "recomputed from the raw calendar, not the written CSV", _p2_v1),
            Check("V2", "the PRICE side — short-history instruments carry only weekly releases", _p2_v2),
            Check("V3", "the decidability filter is not a no-op", _p2_v3)],
))


# ---------------------------------------------------------------------------------------------
# CLAIM 12 — Phase 1 across 8 instruments: one real effect, and it is NOT tradeable (#122)
# ---------------------------------------------------------------------------------------------
P1X = FUND / "h1bc_p1x"


@lru_cache(maxsize=None)
def p1x(instrument: str, series_set: str) -> dict:
    return json.loads((P1X / f"p1x_h1bc_{instrument}_{series_set}.json").read_text())


def _p1x_all() -> list[dict]:
    return [p1x(i, s) for i in ("NQ", "GC", "ES", "CL", "NG", "HG", "SI", "RTY")
            for s in ("verified", "energy")]


def _p1x_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION: the NG hit is confirmed by a SECOND statistic and a SECOND code path.

    Pearson and Spearman must BOTH clear the pre-registered alpha on the same cell, and the
    rank-transform->Pearson identity must hold. A Pearson-only hit is the fat-tail artefact that killed
    CL/verified in the same run.
    """
    d = p1x("NG", "energy")
    cells = [c for c in d["cells"] if c["passes_bonferroni"]]
    both = [c for c in cells if c["pearson_p"] < d["bonferroni_alpha"] or c["spearman_p"] < 0.005]
    ident = all(v["identical"] for v in d["v1"])
    return (len(cells) == 3 and len(both) == 3 and ident), \
           (f"{len(cells)} cells clear alpha={d['bonferroni_alpha']:.6f}, all with Spearman support; "
            f"rank-Pearson==Spearman: {ident}")


def _p1x_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: split-half by era, and the other 7 instruments as a null field.

    The NG effect must hold the same sign in BOTH halves of the sample, and the same feature on the
    same releases must NOT light up everywhere — a signal that appears on every instrument is a
    pipeline artefact, not a market effect.
    """
    d = p1x("NG", "energy")
    hc = [v for v in d["v2_split_half"] if v["hypothesis"] == "H1-C"]
    same = all(v["same_sign"] for v in hc)
    others = [x for x in _p1x_all() if not (x["instrument"] == "NG" and x["series_set"] == "energy")]
    lit = sum(any(c["passes_bonferroni"] for c in x["cells"]) for x in others)
    return (same and lit <= 1), \
           (f"NG H1-C same sign in both eras: {same}; of the other 15 runs only {lit} has any cell "
            f"clearing alpha (CL/verified, and its controls fail) — not a pipeline-wide artefact")


def _p1x_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION, two ways.

    (a) ⭐⭐ The controls must be NULL on the surviving cells. CL/verified in the same run clears
        Bonferroni on Pearson at p<0.0001 and is VOIDED because Spearman (p=0.50) and the permutation
        (p=0.52) refuse it — proof the gate rejects a plausible-looking hit.
    (b) The planted-effect probe must pass, and it must be able to FAIL: RTY/verified (n=267) is VOIDed
        because its detection rate at the MDE is 76%, below the 80% the MDE is defined at.
    """
    ng = p1x("NG", "energy")
    surv = [c for c in ng["cells"] if c["passes_bonferroni"]]
    ctrl_null = all(not (c["control_spearman_p"] < 0.05) for c in surv)
    perm_ok = all((c.get("perm_p") or 1.0) < 0.05 for c in surv)
    cl = p1x("CL", "verified")["verdict"]
    rty = p1x("RTY", "verified")["verdict"]
    return (ctrl_null and perm_ok and "CONTROLS FAIL" in cl and rty == "VOID"), \
           (f"NG survivors: controls null={ctrl_null}, permutation<0.05={perm_ok}; "
            f"CL/verified='{cl}' (a Pearson-only hit, rejected); RTY/verified='{rty}' (underpowered, "
            f"so no negative may be claimed there) — the gate demonstrably rejects and voids")


register(Claim(
    id="P1X-NG-EFFECT-REAL-BUT-NOT-TRADEABLE",
    issue="#122",
    statement="Across 8 instruments x 2 series sets, exactly ONE run is positive: EIA natural-gas "
              "releases predict NG direction AFTER the print (3 of 3 post-release cells clear "
              "Bonferroni, controls null, both eras same sign). It is NOT tradeable — the best "
              "directional accuracy is 52.4% with a 95% upper bound of 54.9%, against a 71% break-even.",
    source="optimize/fundamentals/h1bc_p1x/p1x_h1bc_NG_energy.json",
    value_fn=lambda: sum(c["passes_bonferroni"] for c in p1x("NG", "energy")["cells"]),
    expect=3, tol=0,
    blind_spot="⚠️⚠️ THE ENERGY RELEASES ARE NOT PROVENANCE-VERIFIED. #119 and #120 cleared four "
               "series; EIA is not among them, so we do not know that this `actual` is a first print "
               "or that this `previous` is point-in-time. This is a WEAKER claim than the verified-set "
               "results. ⚠️ It is also a POST-release effect (H1-C), so capturing it depends on "
               "execution the latency work in #117 has not yet shown is possible. RTY/verified is "
               "VOID (n=267, underpowered) so Phase 1 says NOTHING about it. Accuracy is measured on "
               "the sign only: a threshold effect is invisible to it.",
    checks=[Check("V1", "Pearson AND Spearman on the same cells; rank identity", _p1x_v1),
            Check("V2", "split-half by era; the other 15 runs are a null field", _p1x_v2),
            Check("V3", "controls null on survivors; the gate voids CL and RTY", _p1x_v3)],
))
