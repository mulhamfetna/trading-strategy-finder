"""#118 VP-C2 — replay real historical defects and require the harness to REJECT them.

⚠️⚠️ A GATE THAT HAS NEVER FAILED IS UNTESTED. Every defect in #118 passed a check that was incapable
of failing, so a verification harness whose own failure path is unexercised reproduces the exact
problem it was built to solve — one level up.

Each replay below reconstructs a claim EXACTLY AS IT WAS ORIGINALLY PUBLISHED and asserts this harness
would have rejected it. If a replay ever starts passing, the harness has gone soft.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from claims_news2 import RETRACTED, RETRACTION_MARKERS, dst_broken_years, h1a, h1a_ratio  # noqa: E402
from harness import Check, Claim, run_claim  # noqa: E402

import re  # noqa: E402


def _expect_rejected(name: str, claim: Claim, *, because: str, reason: str) -> bool:
    """Reject the replay AND require the rejection to be for `reason`.

    ⚠️⚠️ THIS GUARD WAS ADDED AFTER THE SELF-TEST PASSED FOR THE WRONG REASON. On its first run, two
    replays were "correctly REJECTED" — by a FileNotFoundError from a bad ROOT path, not by the defect
    they were replaying. A green self-test that is green for an unrelated reason is the same disease as
    a check that cannot fail, one level up. So the rejection line must now MATCH.
    """
    r = run_claim(claim)
    blob = " ".join(r.lines)
    crashed = "producer raised" in blob and "raised" not in reason
    matched = re.search(reason, blob) is not None
    good = (not r.ok) and matched and not crashed
    print(f"  [{'ok  ' if good else 'FAIL'}] {name}")
    print(f"         replaying: {because}")
    for ln in r.lines:
        print(f"         {ln}")
    if good:
        print(f"         -> correctly REJECTED, and for the right reason (/{reason}/)")
    elif r.ok:
        print("         -> ⚠️ ACCEPTED. The harness would have let this through. Fix the harness.")
    elif crashed:
        print("         -> ⚠️ rejected by a CRASH, not by the defect. That is not a passing gate.")
    else:
        print(f"         -> ⚠️ rejected, but not for the expected reason (/{reason}/).")
    return good


# ------------------------------------------------------------------------------------------------
# DEFECT #2 — a published figure that exists in no result file ("1.31-2.92x", published three times)
# ------------------------------------------------------------------------------------------------
def replay_fabricated_number() -> bool:
    c = Claim(
        id="REPLAY-FABRICATED",
        statement="NQ 5-min danger ratio is 1.31x (as originally published).",
        source="optimize/fundamentals/h1a_stopout_NQ.json",
        value_fn=lambda: round(h1a_ratio("NQ", 5, 0.4), 2),
        expect=1.31, tol=0.005,
        blind_spot="declared, so the structural gate cannot be what rejects this",
        checks=[Check("V3", "trivially true", lambda: (True, "n/a"))],
    )
    return _expect_rejected(
        "defect #2 — number present in no file", c,
        because="a figure checked against my notes instead of against the JSON that produced it",
        # ⚠️ Pinned loosely on purpose: the REAL value moved 4.27 -> 4.37 when the owner regenerated
        # the price frame, and hard-coding it made this self-test fail for a reason that had nothing to
        # do with the defect being replayed. What must be asserted is that the ledger rejects the
        # FABRICATED 1.31 — not what the true value happens to be this month.
        reason=r"LEDGER  FAIL  re-derived [0-9.]+, published 1\.31")


# ------------------------------------------------------------------------------------------------
# DEFECT #1 — DST verified on ONE series (NFP) and generalised to all 649
# ------------------------------------------------------------------------------------------------
def replay_single_series_generalisation() -> bool:
    """As originally published: "daylight saving is correctly encoded at source", evidenced by NFP."""
    c = Claim(
        id="REPLAY-DST-ALL-CLEAN",
        statement="Daylight saving is correctly encoded across the whole file (evidence: NFP 164/164).",
        source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
        value_fn=lambda: len([y for y, s in dst_broken_years().items() if s > 0.25]),
        expect=0, tol=0,
        blind_spot="declared, so the structural gate is not what rejects this — the DATA is",
        checks=[Check("V1", "NFP is 100% at 08:30 ET (the original evidence, and it is TRUE)",
                      lambda: (True, "164/164 — a true statement about one series of 649")),
                Check("V3", "no series disagrees between winter and summer",
                      lambda: (max(dst_broken_years().values()) < 0.25,
                               f"worst year: {max(dst_broken_years().values()):.0%} of series disagree"))],
    )
    return _expect_rejected(
        "defect #1 — single-series generalisation", c,
        because="V1 passes on the original evidence (NFP really is clean) and the claim is STILL "
                "rejected, because the ledger value and the V3 falsifier look at the population",
        reason=r"re-derived 3, published 0")


def replay_missing_falsifier() -> bool:
    """The structural half of defect #1: a claim with no V3 and no stated blind spot."""
    c = Claim(
        id="REPLAY-NO-V3",
        statement="Verified — NFP timestamps are correct.",
        source="optimize/fundamentals/tradingview/tv_us_calendar_raw.csv",
        value_fn=lambda: 164,
        expect=164, tol=0,
        blind_spot="",                       # <- not declared: VP-C4
        checks=[Check("V1", "recount", lambda: (True, "164"))],   # <- no V3
    )
    return _expect_rejected(
        "defect #1 (structural) — no falsifier, no denominator", c,
        because="'verified' with no stated population and nothing that could have come out false",
        reason=r"no blind_spot declared")


# ------------------------------------------------------------------------------------------------
# DEFECT #6 — absolute point stops compared across instruments of different price scale
# ------------------------------------------------------------------------------------------------
def replay_units_flaw() -> bool:
    """A 40-point stop is a different RISK on NQ than on GC. Re-derived from the committed files.

    Implied price = median_stop_pts / stop_pct * 100, taken straight from the H1-A result files.
    """
    def implied_price(inst: str) -> float:
        r = next(x for x in h1a(inst) if x["set"] == "RELEASES" and x["wait_min"] == 5
                 and x["stop_pct"] == 0.4)
        return r["median_stop_pts"] / 0.4 * 100.0

    def pct_of_40pt(inst: str) -> float:
        return 40.0 / implied_price(inst) * 100.0

    def scale_invariance() -> tuple[bool, str]:
        a, b = pct_of_40pt("NQ"), pct_of_40pt("GC")
        same = abs(a - b) < 0.05
        return same, (f"a 40-point stop is {a:.2f}% of NQ and {b:.2f}% of GC "
                      f"({max(a,b)/min(a,b):.1f}x different risk) — comparing the two in POINTS "
                      f"compares different things")

    c = Claim(
        id="REPLAY-UNITS",
        statement="Gold is calmer than the Nasdaq before releases (measured with a 40-POINT stop).",
        source="optimize/fundamentals/h1a_stopout_{NQ,GC}.json",
        value_fn=lambda: round(pct_of_40pt("NQ"), 2),
        expect=round(pct_of_40pt("GC"), 2), tol=0.05,   # the flawed premise: same stop = same risk
        blind_spot="declared",
        checks=[Check("V3", "a fixed point stop is the same % of price on both instruments",
                      scale_invariance)],
    )
    return _expect_rejected(
        "defect #6 — units flaw (points vs percent)", c,
        because="an absolute point stop was silently a different percentage of price on each "
                "instrument, producing a fake 'gold is calmer' result",
        reason=r"x different risk")


# ------------------------------------------------------------------------------------------------
# DEFECT #3 / #7 — a claim published as "verified" that was never measured
# ------------------------------------------------------------------------------------------------
def replay_unmarked_retraction() -> bool:
    """The retraction scanner must catch a retracted figure reused without a retraction marker."""
    planted = "the pre-release window is 1.31-2.92 times more dangerous"
    caught = [p for p in RETRACTED if re.search(p, planted)]
    marked = bool(RETRACTION_MARKERS.search(planted))
    good = bool(caught) and not marked
    print(f"  [{'ok  ' if good else 'FAIL'}] defect #3/#7 — retracted figure reused unmarked")
    print(f"         planted text: {planted!r}")
    print(f"         patterns matched: {caught}; retraction marker present: {marked}")
    print(f"         -> {'correctly REJECTED' if good else '⚠️ NOT CAUGHT — scanner is blind'}")
    return good


REPLAYS = [
    replay_fabricated_number,
    replay_single_series_generalisation,
    replay_missing_falsifier,
    replay_units_flaw,
    replay_unmarked_retraction,
]


def main() -> int:
    print("=" * 100)
    print("HARNESS SELF-TEST (VP-C2) — replaying real defects; each MUST be rejected")
    print("=" * 100)
    results = []
    for fn in REPLAYS:
        print()
        results.append(fn())
    n_ok = sum(results)
    print("\n" + "=" * 100)
    print(f"{n_ok}/{len(results)} historical defects correctly rejected")
    if n_ok != len(results):
        print("⚠️ THE HARNESS WOULD HAVE LET A KNOWN DEFECT THROUGH.")
    print("=" * 100)
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
