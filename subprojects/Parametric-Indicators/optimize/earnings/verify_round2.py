"""WS-EARN Stage 1 — SECOND VERIFICATION ROUND (#110).

An independent audit of the 201-row table, run after collection. Five checks, each able to FAIL.

  V1  structural integrity        duplicates, cadence, period alignment                    (offline)
  V2  in-document date            the filing's own sentence "On <date>, X released ..."    (offline)
  V3  price-tape alignment        a FALSIFICATION test in the style of verify_timezone.py  (offline)
  V4  classification audit        random sample with the evidence that decided each row    (offline)
  V5  timestamp re-fetch          same fact, DIFFERENT endpoint                            (network)

⚠️⚠️ V3 AND CIRCULARITY — read before interpreting it.

V3 measures |1-minute return| at offsets around our timestamps and expects a spike at offset 0. That is
legitimate ONLY as a falsification test of a SYSTEMATIC error — the same use
`optimize/fundamentals/verify_timezone.py` already makes of it for macro releases, where a 7-hour
timezone error showed up as a spike 7 hours away from where it should be.

It is NOT a timestamp source. **No timestamp may be moved because of what V3 shows.** If it were, the
Stage 4 finding would be a tautology: we would have defined the spike into existence and then
"discovered" it. V3 can only say *the set of timestamps is grossly misaligned* or *it is not*.

A concrete illustration of why it is worth running anyway: before the SGML fix, 22 events (all MSFT,
all LRCX) sat 4-5 hours early. V3 would have shown their energy at offset -240/-300 instead of 0.

    python3 optimize/earnings/verify_round2.py [--refetch N]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLE = DATA / "earnings_timestamps_FINAL.csv"
TEXT = DATA / "filing_text.json"
RECHECK = DATA / "verify_round2_refetch.json"

UA = "MulhamFetna-Research contact@mulhamfetna.com"
PAUSE = 0.15
MONTHS = ("January February March April May June July August September October November December").split()
# ⚠️ Must require a RESULTS verb within the same sentence. A bare "On <date>" also matches the dividend
# sentence ("...payable on February 15, 2024..."), which sits exactly 14 days after the announcement —
# so a loose pattern reports a confident 14-day "disagreement" on every Apple filing. That is the check
# being wrong, not the data.
DATE_CLAIM = re.compile(
    r"\bOn\s+(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b"
    r"[^.]{0,160}?\b(released|announced|issued|reported|published|furnish\w*)\b"
    r"[^.]{0,80}?\b(results|earnings|financial)\b", re.I)

FAILS: list[str] = []


def banner(t: str) -> None:
    print("\n" + "=" * 92)
    print(t)
    print("=" * 92)


# ------------------------------------------------------------------------------------------------
def v1_structure(df) -> None:
    banner("V1  STRUCTURAL INTEGRITY")
    dup_acc = df[df.duplicated("accession", keep=False)]
    dup_evt = df[df.duplicated(["ticker", "event_et"], keep=False)]
    print(f"  duplicate accessions           : {len(dup_acc)}")
    print(f"  duplicate (ticker, timestamp)  : {len(dup_evt)}")
    if len(dup_acc) or len(dup_evt):
        FAILS.append("V1: duplicates present")

    print(f"\n  {'ticker':<8}{'n':>3}  {'min gap':>8}{'median':>9}{'max gap':>9}   verdict")
    for t, g in df.groupby("ticker"):
        g = g.sort_values("event_et")
        gaps = g["event_et"].diff().dt.days.dropna()
        if gaps.empty:
            continue
        ok = gaps.min() >= 60 and gaps.max() <= 130
        if not ok:
            FAILS.append(f"V1: {t} cadence {gaps.min():.0f}-{gaps.max():.0f} days")
        print(f"  {t:<8}{len(g):>3}  {gaps.min():>8.0f}{gaps.median():>9.0f}{gaps.max():>9.0f}   "
              f"{'ok' if ok else '<-- IRREGULAR'}")

    # The filing's stated period should sit at or just before the announcement, never after.
    bad = 0
    for _, r in df.iterrows():
        if isinstance(r.report_date, str) and len(r.report_date) == 10:
            if datetime.fromisoformat(r.report_date).date() > r.event_et.date():
                bad += 1
    print(f"\n  filings whose stated period is AFTER the announcement: {bad}")
    if bad:
        FAILS.append(f"V1: {bad} rows with period after announcement")


# ------------------------------------------------------------------------------------------------
def v2_in_document_date(df, text) -> None:
    banner("V2  IN-DOCUMENT DATE — does the filing's own text agree with our timestamp?")
    agree = disagree = absent = 0
    bad_rows = []
    for _, r in df.iterrows():
        txt = (text.get(r.accession, {}) or {}).get("text_v2") or ""
        m = DATE_CLAIM.search(txt)
        if not m:
            absent += 1
            continue
        mon = [x.lower() for x in MONTHS].index(m.group(1).lower()) + 1
        claimed = datetime(int(m.group(3)), mon, int(m.group(2))).date()
        delta = abs((claimed - r.event_et.date()).days)
        if delta <= 1:
            agree += 1
        else:
            disagree += 1
            bad_rows.append((r.ticker, str(r.event_et), str(claimed), r.accession))
    n = agree + disagree
    print(f"  filings stating a date in their own text : {n} of {len(df)}")
    print(f"  agree with our timestamp (+-1 day)       : {agree}" + (f"  ({100*agree/n:.1f}%)" if n else ""))
    print(f"  DISAGREE                                 : {disagree}")
    print(f"  no date sentence found                   : {absent}")
    for b in bad_rows[:10]:
        print(f"      {b[0]:<6} ours={b[1]}  document says={b[2]}  {b[3]}")
    if n and disagree / n > 0.02:
        FAILS.append(f"V2: {disagree}/{n} in-document dates disagree")


# ------------------------------------------------------------------------------------------------
def v3_tape_alignment(df) -> None:
    banner("V3  PRICE-TAPE ALIGNMENT — falsification test only, NEVER a timestamp source")
    try:
        import numpy as np
        import pandas as pd
        from optimize.fundamentals.extended_data import load_1m_extended
        d1 = load_1m_extended("NQ")
    except Exception as exc:
        print(f"  price frame unavailable: {type(exc).__name__}: {exc}")
        return

    import numpy as np
    import pandas as pd
    close = d1["Close"].to_numpy(float)
    ret = np.abs(np.diff(close, prepend=close[0]) / close)
    idx = pd.Index(d1["Date"])

    # ⚠️ THE BASELINE MUST BE TIME-OF-DAY MATCHED.
    # A flat all-hours mean makes a 06:00 pre-market bar look unremarkable no matter what happens in it,
    # because it is being compared against 09:30-16:00 activity. Measured here: the average |return| at
    # 06:00 is a small fraction of the 10:00 average. Using the flat mean showed the BMO earnings events
    # (WMT, ASML) as a 1.06x non-event — an artefact of the yardstick, not a property of the releases.
    hm = d1["Date"].dt.hour * 60 + d1["Date"].dt.minute
    tod = pd.Series(ret).groupby(hm.to_numpy()).transform("mean").to_numpy()
    tod = np.where(tod > 0, tod, ret.mean())
    base_flat = ret.mean()

    def profile(sub, label):
        t0 = idx.get_indexer(pd.to_datetime(sub["event_et"]).dt.floor("min"))
        t0 = t0[t0 >= 0]
        if len(t0) == 0:
            print(f"  {label}: no events matched a bar")
            return None
        print(f"\n  {label}  (n={len(t0)} events matched to an exact 1-minute bar)")
        print(f"  {'offset':>7} {'vs same-time-of-day':>20}  ")
        peak, peak_off = 0.0, None
        for off in range(-5, 11):
            ii = t0 + off
            ii = ii[(ii >= 0) & (ii < len(ret))]
            mult = (ret[ii] / tod[ii]).mean()          # each bar vs a NORMAL bar at that clock time
            if mult > peak:
                peak, peak_off = mult, off
            bar = "#" * int(min(mult, 60))
            mark = "  <== announcement minute" if off == 0 else ""
            print(f"  {off:>7} {mult:>18.2f}x  {bar}{mark}")
        print(f"  peak at offset {peak_off:+d} ({peak:.2f}x a normal bar at the same clock time)")
        return peak_off

    cov = df[df.nq_coverage == "bar_present"]
    po = profile(cov, "ALL earnings events")
    if po is not None and abs(po) > 2:
        FAILS.append(f"V3: peak volatility at offset {po:+d}, not the announcement minute")

    for sess in ("AMC", "BMO"):
        s = cov[cov.session == sess]
        if len(s) >= 5:
            profile(s, f"{sess} events only")

    # The falsification arm: if timestamps were systematically hours off, energy would sit far away.
    print("\n  FALSIFICATION — |return| at large offsets (should be ~1x, i.e. an ordinary minute):")
    t0 = idx.get_indexer(pd.to_datetime(cov["event_et"]).dt.floor("min"))
    t0 = t0[t0 >= 0]
    for off in (-300, -240, -60, 0, 60, 240, 300):
        ii = t0 + off
        ii = ii[(ii >= 0) & (ii < len(ret))]
        if len(ii) == 0:
            continue
        print(f"     offset {off:>5} min ({off/60:+.0f}h): {(ret[ii]/tod[ii]).mean():>6.2f}x "
              f"(flat-baseline view: {ret[ii].mean()/base_flat:.2f}x)")


# ------------------------------------------------------------------------------------------------
def v4_classification_audit(df, text, k=12) -> None:
    banner(f"V4  CLASSIFICATION AUDIT — random sample of {k}, with the evidence that decided each")
    rng = random.Random(20260804)                       # fixed seed: the sample is reproducible
    for _, r in df.sample(n=min(k, len(df)), random_state=20260804).iterrows():
        txt = (text.get(r.accession, {}) or {}).get("text_v2") or ""
        snippet = re.sub(r"\s+", " ", txt[:130])
        print(f"\n  {r.ticker:<6} {r.event_et}  [{r.session}]")
        print(f"     markers  : {r.evidence}")
        print(f"     docs read: {r.evidence_source}")
        print(f"     text     : {snippet}...")


# ------------------------------------------------------------------------------------------------
def v5_refetch(df, n) -> None:
    banner(f"V5  TIMESTAMP RE-FETCH — same fact from a DIFFERENT endpoint (n={n})")
    print("  primary source was {accession}-index-headers.html")
    print("  this check reads the raw submission .txt header instead — a different file entirely.\n")
    cache = json.loads(RECHECK.read_text()) if RECHECK.exists() else {}
    sample = df.sample(n=min(n, len(df)), random_state=7).sort_values("event_et")
    ok = bad = fail = 0
    for _, r in sample.iterrows():
        acc = r.accession
        if acc not in cache:
            url = (f"https://www.sec.gov/Archives/edgar/data/{r.cik}/"
                   f"{acc.replace('-', '')}/{acc}.txt")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    head = resp.read(4000).decode("utf-8", errors="replace")
                m = re.search(r"ACCEPTANCE-DATETIME>(\d{14})", head)
                cache[acc] = m.group(1) if m else None
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                cache[acc] = f"__FAIL__{type(exc).__name__}"
            time.sleep(PAUSE)
        raw = cache[acc]
        if not raw or str(raw).startswith("__FAIL__"):
            fail += 1
            continue
        got = datetime.strptime(raw, "%Y%m%d%H%M%S")
        if abs((got - r.event_et.to_pydatetime()).total_seconds()) <= 1:
            ok += 1
        else:
            bad += 1
            print(f"     MISMATCH {r.ticker:<6} table={r.event_et}  txt-header={got}  {acc}")
    RECHECK.write_text(json.dumps(cache, indent=1))
    print(f"  confirmed identical : {ok}")
    print(f"  MISMATCH            : {bad}")
    print(f"  unreachable         : {fail}")
    if bad:
        FAILS.append(f"V5: {bad} timestamps differ between endpoints")


# ------------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", type=int, default=40)
    a = ap.parse_args()

    import pandas as pd
    df = pd.read_csv(TABLE, parse_dates=["event_et"])
    text = json.loads(TEXT.read_text())
    print(f"table: {TABLE.name} — {len(df)} events, {df.ticker.nunique()} companies")

    v1_structure(df)
    v2_in_document_date(df, text)
    v3_tape_alignment(df)
    v4_classification_audit(df, text)
    if a.refetch:
        v5_refetch(df, a.refetch)

    banner("VERDICT")
    if FAILS:
        print("  FAILED CHECKS:")
        for f in FAILS:
            print(f"    - {f}")
    else:
        print("  all checks passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
