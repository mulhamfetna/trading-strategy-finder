"""WS-EARN Stage 1, step 6 (#110) — assemble the FINAL verified table + the TradingView worksheet.

Consumes the document-evidence classification and produces:

  earnings_timestamps_FINAL.csv   one row per EARNINGS announcement, timestamp to the second, in
                                  tz-naive US-Eastern wall-clock (the NQ price frame's own convention)
  TRADINGVIEW-VERIFICATION.md     the 36-event stratified worksheet for the human check (C4)

C3b — TIME-OF-DAY STABILITY, and what it is worth.
    A scheduled corporate process produces a stable release clock time. Apple has filed at 16:30:2x-4x
    ET for eleven consecutive quarters. That stability is NOT independent evidence (it is the same
    source), but it is a strong instrument: a genuine anomaly stands out against it. ASML's accidental
    early release of its Q3-2024 results lands at 11:34:59 ET against its habitual 06:0x — visible
    immediately as an outlier rather than buried.

    So the spread is reported per company, and every event more than 30 minutes from its company's
    median release time is FLAGGED for the human check. Flagged does not mean wrong; it means look.

⚠️ ANTI-CIRCULARITY: the price frame is read here for ONE purpose — flagging whether a 1-minute bar
   exists at the event minute. No timestamp is ever adjusted toward an observed volatility spike.

    python3 optimize/earnings/build_final_table.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone as _tz
from zoneinfo import ZoneInfo

ET_ZONE = ZoneInfo("America/New_York")
UTC = _tz.utc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CLASSIFIED = DATA / "earnings_events_classified.json"
AUTH = DATA / "authoritative_times.json"
OUT_CSV = DATA / "earnings_timestamps_FINAL.csv"
OUT_MD = HERE / "TRADINGVIEW-VERIFICATION.md"

RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)
FLAG_MINUTES = 30              # distance from company median that triggers a human look


def session_of(dt: datetime) -> str:
    hm = (dt.hour, dt.minute)
    if dt.weekday() >= 5:
        return "weekend"
    if hm < RTH_OPEN:
        return "BMO"
    if hm < RTH_CLOSE:
        return "intraday"
    return "AMC"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="suffix for all data files, e.g. 16y")
    ap.add_argument("--no-worksheet", action="store_true",
                    help="skip the TradingView worksheet (it is specific to the verified 2.4y set)")
    a = ap.parse_args()
    sfx = f"_{a.tag}" if a.tag else ""
    global CLASSIFIED, AUTH, OUT_CSV
    CLASSIFIED = DATA / f"earnings_events_classified{sfx}.json"
    AUTH = DATA / f"authoritative_times{sfx}.json"
    OUT_CSV = DATA / f"earnings_timestamps_FINAL{sfx}.csv"
    print(f"classified : {CLASSIFIED.name}\nauth       : {AUTH.name}\nout        : {OUT_CSV.name}\n")

    events = json.loads(CLASSIFIED.read_text())
    rows = [e for e in events.values() if e["label"] == "earnings"]
    dropped = [e for e in events.values() if e["label"] != "earnings"]

    # ⚠️ TIMESTAMPS COME FROM THE SGML HEADER, NOT THE JSON API.
    # EDGAR's submissions JSON labels `acceptanceDateTime` with a trailing Z, but for some filings the
    # value is Eastern wall-clock rather than UTC. Converting those as UTC moved Microsoft's earnings to
    # 12:04 ET — four hours early, into the middle of the session instead of after the close. The SGML
    # `ACCEPTANCE-DATETIME` is EDGAR's own record, in Eastern, and is used for EVERY event.
    auth = json.loads(AUTH.read_text()) if AUTH.exists() else {}
    n_corrected = n_unresolved = 0
    for r in rows:
        raw = (auth.get(r["accession"]) or {}).get("sgml")
        if raw:
            dt = datetime.strptime(raw, "%Y%m%d%H%M%S")
            if abs((dt - datetime.fromisoformat(r["event_et"])).total_seconds()) > 60:
                n_corrected += 1
                r["json_et_rejected"] = r["event_et"]
            r["dt"] = dt
            r["time_source"] = "EDGAR SGML ACCEPTANCE-DATETIME (Eastern)"
        else:
            r["dt"] = datetime.fromisoformat(r["event_et"])
            r["time_source"] = "UNRESOLVED — JSON acceptanceDateTime, treat as suspect"
            n_unresolved += 1
        r.setdefault("json_et_rejected", "")
        # `dt` is the authoritative value — the emitted column must BE it, not the string it replaced.
        r["event_et"] = r["dt"].isoformat(sep=" ")
        # Recompute UTC from the AUTHORITATIVE Eastern time. Carrying the JSON's original `event_utc`
        # forward would leave the two columns contradicting each other on exactly the 22 rows that were
        # corrected — a table that disagrees with itself is worse than one that is merely wrong.
        r["event_utc"] = (r["dt"].replace(tzinfo=ET_ZONE)
                          .astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S") + "Z")
    rows.sort(key=lambda r: (r["ticker"], r["dt"]))
    print(f"authoritative times  : {len(rows)-n_unresolved} resolved from SGML, "
          f"{n_corrected} CORRECTED vs the JSON field, {n_unresolved} unresolved")

    # ---- de-duplicate: the SAME announcement filed twice -----------------------------------------
    # ⚠️ INTC filed each quarter's earnings TWICE in 2010-2013: the wire service filed the press
    # release in the evening (~16:1x) and Intel self-filed a duplicate the NEXT MORNING (~09:xx).
    # 14 such pairs. This is not merely a double count — the duplicate carries a next-morning
    # timestamp, so keeping it would place a real event hours after it actually happened.
    #
    # Keep the EARLIEST of any pair inside 24h: the announcement is the FIRST public disclosure.
    # Applied to every company, not special-cased to INTC, so the same pattern elsewhere is caught.
    by_tkr: dict[str, list] = defaultdict(list)
    for r in rows:
        by_tkr[r["ticker"]].append(r)
    kept, dropped_dupes = [], []
    for t, g in by_tkr.items():
        g.sort(key=lambda r: r["dt"])
        last = None
        for r in g:
            if last is not None and (r["dt"] - last["dt"]).total_seconds() < 24 * 3600:
                r["dropped_as_duplicate_of"] = last["accession"]
                dropped_dupes.append(r)
                continue
            kept.append(r)
            last = r
    if dropped_dupes:
        cnt = defaultdict(int)
        for r in dropped_dupes:
            cnt[r["ticker"]] += 1
        print(f"duplicate filings    : {len(dropped_dupes)} removed "
              f"({dict(cnt)}) — kept the earliest of each pair")
    rows = sorted(kept, key=lambda r: (r["ticker"], r["dt"]))

    print(f"classified filings   : {len(events)}")
    print(f"  labelled earnings  : {len(rows)}")
    for lab in sorted({e['label'] for e in dropped}):
        print(f"  labelled {lab:<18}: {sum(1 for e in dropped if e['label']==lab)}  (excluded from the table)")

    # ---- C3b: per-company time-of-day stability -------------------------------------------------
    print("\n=== C3b  time-of-day stability per company ===")
    print(f"{'ticker':<8}{'n':>4}  {'median release (ET)':<21}{'spread':<12}flagged")
    med: dict[str, float] = {}
    by_t = defaultdict(list)
    for r in rows:
        by_t[r["ticker"]].append(r)

    for t in sorted(by_t):
        secs = [r["dt"].hour * 3600 + r["dt"].minute * 60 + r["dt"].second for r in by_t[t]]
        m = statistics.median(secs)
        med[t] = m
        devs = [abs(s - m) / 60.0 for s in secs]
        flagged = sum(1 for d in devs if d > FLAG_MINUTES)
        hh, rem = divmod(int(m), 3600)
        mm, ss = divmod(rem, 60)
        spread = f"±{max(devs):.0f} min" if devs else "-"
        mark = f"  <-- {flagged}" if flagged else ""
        print(f"{t:<8}{len(secs):>4}  {hh:02d}:{mm:02d}:{ss:02d}{'':<13}{spread:<12}{flagged}{mark}")

    for r in rows:
        s = r["dt"].hour * 3600 + r["dt"].minute * 60 + r["dt"].second
        r["dev_from_median_min"] = round(abs(s - med[r["ticker"]]) / 60.0, 1)
        r["time_outlier"] = "YES" if r["dev_from_median_min"] > FLAG_MINUTES else ""
        r["session"] = session_of(r["dt"])

    # ---- price coverage (the ONLY use of the price frame) ---------------------------------------
    try:
        import pandas as pd
        from optimize.fundamentals.extended_data import load_1m_extended
        df = load_1m_extended("NQ")
        lo, hi = df["Date"].min(), df["Date"].max()
        minutes = set(df["Date"].values)
        for r in rows:
            ts = pd.Timestamp(r["dt"]).floor("min")
            r["nq_coverage"] = ("outside_span" if (ts < lo or ts > hi)
                                else "bar_present" if ts.to_datetime64() in minutes
                                else "in_span_no_bar")
        print(f"\nprice frame: {lo} -> {hi}  ({len(df):,} bars)")
    except Exception as exc:
        for r in rows:
            r["nq_coverage"] = "unknown"
        print(f"\nprice coverage UNAVAILABLE: {type(exc).__name__}: {exc}")

    cov = defaultdict(int)
    for r in rows:
        cov[r["nq_coverage"]] += 1
    print("coverage:", dict(cov))

    # ---- write the table ------------------------------------------------------------------------
    cols = ["ticker", "company", "company_rank", "combined_weight_pct", "cik", "event_et", "event_utc",
            "session", "form", "items", "report_date", "filing_date", "accession",
            "evidence_source", "evidence", "dev_from_median_min", "time_outlier", "nq_coverage",
            # audit trail: where the time came from, and what it replaced on the 22 corrected rows
            "time_source", "json_et_rejected"]
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} earnings events -> {OUT_CSV}")

    # ---- TradingView worksheet: 3 events x top 12 companies -------------------------------------
    ranked = sorted(by_t, key=lambda t: by_t[t][0]["company_rank"])[:12]
    lines = [
        "# WS-EARN Stage 1 — TradingView verification worksheet (criterion C4, issue #110)",
        "",
        "**What you are checking:** that the timestamp in our table is the moment the market actually",
        "reacted, to within ±1 minute. Our timestamps come from SEC EDGAR — the second the SEC accepted",
        "the company's Form 8-K earnings filing. That is *documentary*, not derived from price.",
        "",
        "**Why your check matters:** EDGAR records when the FILING was accepted, not when the press",
        "release crossed the wire. For Apple the two coincide. For others the filing can lag the release",
        "by minutes. Your eyes on the chart are the only fully independent test of the minute we have —",
        "no free data vendor publishes announcement times at all (Nasdaq's own API returns",
        "`time-not-supplied`).",
        "",
        "**Pass mark, pre-registered before collection:** ≥ 34 of 36 within ±1 minute.",
        "",
        "## How to check one row",
        "",
        "1. Open TradingView, symbol **NQ1!** (Nasdaq-100 futures — it trades after the 16:00 close, so",
        "   it covers after-market earnings; QQQ regular-hours data does not).",
        "2. Set the interval to **1 minute**.",
        "3. Jump to the date and time in the row.",
        "4. You are looking for a **sudden volume and range expansion** at that minute or the one after.",
        "5. Write what you see in the verdict column.",
        "",
        "⚠️ **Do not adjust our timestamp to match the spike.** If they disagree, record the disagreement.",
        "Moving the timestamp to fit the price would make the later analysis circular — we would be",
        "'discovering' a spike exactly where we had defined it to be.",
        "",
        "⚠️ Rows marked **OUTLIER** sit far from that company's usual release time. Being an outlier does",
        "not make a row wrong — a company can genuinely release off-schedule — but they are the rows most",
        "worth your attention.",
        "",
        "ℹ️ Rows marked `outside_span` are after 2026-05-19, where our local price file ends. **TradingView",
        "still has that data**, so you can check them normally; they simply are not usable for analysis yet.",
        "",
        "### ⚠️ Please write the time you actually SEE, even when it matches",
        "",
        "The most valuable column is **observed spike time**, not the tick. We have since discovered that",
        "the SEC filing timestamp is *not* the announcement moment for every company — Intel's filing lags",
        "its own press release by about **7 minutes**. Your observed times are how we measure that gap for",
        "the 15 companies that publish no timestamp of their own.",
        "",
        "So: fill in the observed time on **every** row. A row that matches is data, not a non-event.",
        "",
        "| # | ticker | date | our time (ET) | session | flag | NQ bar | **observed spike time** | Δ |",
        "|---|--------|------|---------------|---------|------|--------|------------------------|---|",
    ]
    n = 0
    for t in ranked:
        ev = sorted(by_t[t], key=lambda r: r["dt"])
        picks = [ev[0], ev[len(ev) // 2], ev[-1]] if len(ev) >= 3 else ev
        for r in picks:
            n += 1
            lines.append(
                f"| {n} | **{t}** | {r['dt']:%Y-%m-%d} | **{r['dt']:%H:%M:%S}** | {r['session']} | "
                f"{'⚠️ OUTLIER' if r['time_outlier'] else ''} | {r['nq_coverage']} |  |  |")
    lines += [
        "",
        f"**Total rows to check: {n}.** Pass mark ≥ 34 within ±1 minute.",
        "",
        "---",
        "",
        "## Supplementary — the time-of-day outliers (NOT part of the pre-registered 36)",
        "",
        "These sit far from their company's usual release time, so they are the most informative rows in",
        "the whole table. They are listed **separately on purpose**: criterion C4 was pre-registered at",
        "36 rows with a pass mark of 34, and quietly enlarging the sample after the fact would change the",
        "denominator of a test that was fixed in advance. Check them because they are interesting — the",
        "result does not count toward C4 either way.",
        "",
        "| ticker | date | time (ET) | minutes from that company's median | note |",
        "|--------|------|-----------|-----------------------------------|------|",
    ]
    extra = sorted((r for r in rows if r["time_outlier"]), key=lambda r: r["dt"])
    for r in extra:
        note = ("only intraday event in the entire table" if r["session"] == "intraday"
                else "falls inside the 17:00-17:59 CME halt — no NQ bar exists"
                if r["nq_coverage"] == "in_span_no_bar" else "")
        lines.append(f"| **{r['ticker']}** | {r['dt']:%Y-%m-%d} | **{r['dt']:%H:%M:%S}** | "
                     f"{r['dev_from_median_min']:.0f} | {note} |")
    lines += [
        "",
        "---",
        "",
        "## What we already know about each company's offset (so you know what to expect)",
        "",
        "Measured from company IR websites and independently corroborated by the price tape. **This is",
        "context, not an answer key** — if what you see disagrees with this table, your observation wins",
        "and we investigate.",
        "",
        "| company | expected gap | how we know |",
        "|---------|--------------|-------------|",
        "| **AAPL** | **0 min** — filing time IS the release | tape peaks exactly at our timestamp (6.95×) |",
        "| **AMD** | ~1.5 min early | AMD's IR site (16:15:00) + tape peak at −1 |",
        "| **INTC** | **~7 min early** ⚠️ | Intel's IR site (16:01:00) + tape peak at −7 |",
        "| MSFT, NVDA | ~1 min early | tape only — **unmeasured documentarily** |",
        "| META | ~3 min early | tape only — **unmeasured documentarily** |",
        "| GOOGL, AMZN, AVGO, TSLA, MU, WMT, ASML | **unknown** | no published times; not yet measured |",
        "",
        "## If a row disagrees with our timestamp",
        "",
        "Write down the time you actually see — that *is* the result. A **consistent** per-company offset",
        "is criterion C5 and becomes a recorded correction. A **random** disagreement means the source is",
        "unreliable for that company, and it gets excluded with the exclusion recorded.",
        "",
        "🚫 **Do not adjust our timestamps to match what you see.** Record both. If we moved timestamps to",
        "fit the price, the later analysis would be circular — we would 'discover' a spike exactly where we",
        "had defined it to be.",
    ]
    # The worksheet is the human-verification instrument for the 2.4-year set. A 16-year rebuild must
    # not overwrite it — the owner's pending C4 check is against those exact 36 rows.
    if a.no_worksheet:
        print("worksheet skipped (--no-worksheet): the existing one belongs to the verified 2.4y set")
    else:
        OUT_MD.write_text("\n".join(lines) + "\n")
        print(f"wrote {n}-row worksheet -> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
