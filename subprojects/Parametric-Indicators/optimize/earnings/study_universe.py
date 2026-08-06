"""WS-EARN — THE STUDY UNIVERSE. Which companies the analysis actually runs on, and why.

This file exists so the company selection is a RECORDED DECISION rather than something buried in a
report or re-derived from memory later. The full 201-event table stays untouched; this produces a
filtered view alongside it.

THE DECISION (owner, 2026-08-04): drop ranks 11, 13, 15, 16, 17, 18, 19 from the top-20 and continue
with the remaining 12.

  dropped   11 WMT    Walmart            13 ASML  ASML Holding
            15 CSCO   Cisco              16 AMAT  Applied Materials
            17 COST   Costco             18 LRCX  Lam Research
            19 PLTR   Palantir

⚠️⚠️ A CONSEQUENCE THE DECISION CARRIES, RECORDED SO IT IS NOT DISCOVERED LATER AS A SURPRISE.

WMT and ASML were the ONLY two companies reporting before the US open, and ASML's off-schedule
2024-10-15 release was the ONLY mid-session event in all 201. Dropping them makes the study universe
**100% after-the-close**, every event inside the 16:01-16:30 band.

That is a real simplification — one session, one liquidity regime, no pre-market thinness to model —
but it also means:

  * the study can no longer say anything about pre-market announcements;
  * the "BMO events look weak (1.36x, n=18)" question from verification round 2 is now
    OUT OF SCOPE rather than answered. It is not a finding; it is a question we chose not to ask.

⚠️ INTC IS RETAINED (rank 14) and is the company with the measured ~7-minute gap between its press
release and its SEC filing. Its timestamps are correct as ACCEPTANCE times but are NOT the announcement
moment. It needs the C5 correction before Stage 4, or it will contribute a near-quiet minute (1.32x)
where the real event sits at 3.22x.

    python3 optimize/earnings/study_universe.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FULL = DATA / "earnings_timestamps_FINAL.csv"
OUT_CSV = DATA / "earnings_timestamps_STUDY12.csv"
OUT_JSON = DATA / "study_universe.json"

# Ranks are the COMPANY ranks in earnings_timestamps_FINAL.csv (combined weight, share classes merged).
# Rank 7 (SPCX) never had events and is absent from the table entirely.
DROPPED = {
    11: ("WMT", "Walmart", "owner's selection; also the last pre-open reporter besides ASML"),
    13: ("ASML", "ASML Holding", "owner's selection; removes the only pre-open and only mid-session events"),
    15: ("CSCO", "Cisco Systems", "owner's selection"),
    16: ("AMAT", "Applied Materials", "owner's selection"),
    17: ("COST", "Costco Wholesale", "owner's selection"),
    18: ("LRCX", "Lam Research", "owner's selection"),
    19: ("PLTR", "Palantir Technologies", "owner's selection"),
}


def main() -> int:
    import pandas as pd

    df = pd.read_csv(FULL, parse_dates=["event_et"])
    keep = df[~df.company_rank.isin(DROPPED)].copy()
    gone = df[df.company_rank.isin(DROPPED)]

    print("=" * 88)
    print("WS-EARN study universe — recorded selection")
    print("=" * 88)
    print(f"full table   : {len(df):>4} events, {df.ticker.nunique()} companies")
    print(f"dropped      : {len(gone):>4} events, {gone.ticker.nunique()} companies")
    print(f"STUDY SET    : {len(keep):>4} events, {keep.ticker.nunique()} companies\n")

    print("dropped, with reason:")
    for rank, (tick, name, why) in sorted(DROPPED.items()):
        n = int((df.company_rank == rank).sum())
        print(f"  {rank:>3}  {tick:<7} {n:>3} events   {name:<24} — {why}")

    print("\nretained study universe:")
    print(f"  {'#':>3}  {'tick':<7}{'wt%':>7}{'n':>4}   {'median time (ET)':<18} company")
    for _, r in (keep.drop_duplicates("ticker")
                 .sort_values("company_rank").iterrows()):
        sub = keep[keep.ticker == r.ticker]
        med = sorted(sub.event_et.dt.strftime("%H:%M:%S"))[len(sub) // 2]
        note = "  <-- ~7 min filing lag, needs C5 correction" if r.ticker == "INTC" else ""
        print(f"  {r.company_rank:>3}  {r.ticker:<7}{r.combined_weight_pct:>6.2f}%{len(sub):>4}   "
              f"{med:<18} {r.company[:34]}{note}")

    # Session mix — the consequence that must not be discovered later by surprise.
    print(f"\nsession mix : {keep.session.value_counts().to_dict()}")
    if set(keep.session.unique()) == {"AMC"}:
        print("  ⚠️  the study universe is now 100% AFTER-THE-CLOSE.")
        print("      Pre-market announcements are OUT OF SCOPE, not answered.")

    # Independence: same-evening reporters are one event for the index, not several.
    cov = keep[keep.nq_coverage == "bar_present"].sort_values("event_et")
    grp = (cov.event_et.diff().dt.total_seconds().fillna(9e9) > 3600).cumsum()
    sizes = cov.groupby(grp).size()
    print(f"\nevents with NQ price coverage      : {len(cov)}")
    print(f"EFFECTIVELY INDEPENDENT 60-min windows : {len(sizes)}")
    print(f"  windows holding >1 company       : {int((sizes > 1).sum())}")
    print(f"  largest simultaneous cluster     : {int(sizes.max())} companies")

    keep.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps({
        "decision_date": "2026-08-04",
        "decided_by": "owner",
        "source_table": FULL.name,
        "dropped_ranks": {str(k): {"ticker": v[0], "company": v[1], "reason": v[2]}
                          for k, v in DROPPED.items()},
        "kept_tickers": sorted(keep.ticker.unique().tolist()),
        "n_events": int(len(keep)),
        "n_events_with_price": int(len(cov)),
        "independent_windows": int(len(sizes)),
        "session_mix": {k: int(v) for k, v in keep.session.value_counts().items()},
        "consequences": [
            "study universe is 100% after-the-close; pre-market announcements are out of scope",
            "the BMO weak-signal question (1.36x, n=18) is now unasked, not answered",
            "INTC retained and still needs the ~7-minute C5 correction before Stage 4",
        ],
    }, indent=1))
    print(f"\nwrote {len(keep)} events -> {OUT_CSV}")
    print(f"wrote selection record -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
