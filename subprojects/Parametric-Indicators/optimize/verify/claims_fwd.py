"""WS-FWD claims (#176) — forward-OOS run of the deployed champions on the extended tape.

Protocol: #118. Pre-registration: docs/WS-FWD-PREREGISTRATION.md (gates + fresh-window
definitions frozen before any run). Evidence: optimize/fwd/data/ (committed).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from harness import Check, Claim, register

FWD = Path(__file__).resolve().parents[1] / "fwd" / "data"

# The pre-extension engine ends (phase-0 audit) — the fresh-window boundaries, and the box
# ends beyond which NO entry may exist (fabrication tripwire).
PRE_END = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00",
           "GC": "2026-07-02 19:59:00", "SI": "2026-07-02 19:59:00",
           "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
           "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00",
           "YM": "2026-07-05 19:59:00"}
BOX_END = {"NQ": "2026-06-10", "ES": "2026-05-22", "GC": "2026-06-27", "SI": "2026-06-29",
           "HG": "2026-06-27", "CL": "2026-06-27", "NG": "2026-06-27", "RTY": "2026-06-27",
           "YM": "2026-06-27"}


def _ext() -> dict:
    return json.load(open(FWD / "fwd_extension_report.json"))


def _summary() -> list[dict]:
    return json.load(open(FWD / "fwd_run_summary.json"))


def _book(tok: str, tf: str) -> pd.DataFrame:
    df = pd.read_csv(FWD / f"fwd_book_{tok}_{tf}.csv")
    for c in ("entry_time", "exit_time"):
        df[c] = pd.to_datetime(pd.to_numeric(df[c]), unit="s")
    return df


def _gates_v1() -> tuple[bool, str]:
    """V1 — GATE RECORD: all 9 instruments passed gate A (coverage 1.0, zero OHLCV mismatches)
    and all 54 gate-B resample proofs, and every instrument was appended."""
    r = _ext()
    toks = [t for t in r if t != "pre_checksums"]
    if len(toks) != 9:
        return False, f"expected 9 tokens, got {len(toks)}"
    for t in toks:
        g = r[t]
        if not (g["gate_a"]["pass"] and g["gate_a"]["coverage"] == 1.0 and g["appended"]):
            return False, f"{t}: gate A/appended failed"
        if sorted(g["extended_tfs"]) != sorted(["2m", "5m", "15m", "1h", "2h", "4h"]):
            return False, f"{t}: gate B did not pass all 6 TFs"
        if any(v != 0 for v in g["gate_a"]["mismatches"].values()):
            return False, f"{t}: gate A mismatches nonzero"
    return True, "9/9 gate A exact (incl. volume), 54/54 gate B exact, 9/9 appended"


def _gates_v2() -> tuple[bool, str]:
    """V2 — PROD SAFETY: the production candle files' checksums were identical before/after
    (the extension lives in a parallel root; prod was never written)."""
    r = _ext()
    bad = [t for t in r if t != "pre_checksums" and not r[t]["prod_sha_stable"]]
    return (not bad), (f"prod files touched: {bad}" if bad else "9/9 prod sha stable")


def _gates_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (fabrication tripwire): if box levels had been fabricated/extrapolated,
    entries would exist beyond each instrument's box end. Confirm the broken-world statement
    is FALSE: NO book contains an entry after its instrument's last box date (+1 day slack
    for the session-close mapping)."""
    for row in _summary():
        if row.get("status") != "ok":
            return False, f"slot not ok: {row}"
        tok, tf = row["instrument"], row["tf"]
        df = _book(tok, tf)
        lim = pd.Timestamp(BOX_END[tok]) + pd.Timedelta(days=1)
        n_bad = int((df["entry_time"] > lim).sum())
        if n_bad:
            return False, f"{tok} {tf}: {n_bad} entries beyond box end {BOX_END[tok]}"
    return True, "0 entries beyond any box end across all 54 books — nothing fabricated"


def _books_total() -> float:
    tot = 0.0
    for row in _summary():
        df = _book(row["instrument"], row["tf"])
        tot += float(df["pnl"].sum())
    return round(tot, 2)


register(Claim(
    id="FWD-EXTENSION-AND-54-BOOKS",
    issue="#176",
    statement="Phase 0.5+1 (#176): the tape was extended to 2026-08-07 for all 9 instruments "
              "under exact splice/resample gates (zero mismatches incl. volume; prod untouched), "
              "and all 54 deployed `best` champions ran through the dashboard's own causal path "
              "on the extended root — 54/54 ok, full books committed. Aggregate full-window book "
              "P/L $2,180,903 (2025 $1,364,369 + 2026-to-date $816,536; the 2026 part is the "
              "SELECTION window of the best set, not OOS).",
    source="optimize/fwd/data/fwd_run_summary.json + fwd_book_*.csv",
    value_fn=_books_total,
    expect=2180902.65,
    tol=0.5,
    blind_spot="The books use the engine's standard cost model (no commission/slippage stress); "
               "and a vendor roll INSIDE the appended window handled differently by the two "
               "sources is invisible to the 21-day overlap gate.",
    checks=[Check("V1", "gates-exact", _gates_v1),
            Check("V2", "prod-untouched", _gates_v2),
            Check("V3", "no-entries-beyond-box-end", _gates_v3)],
))


def _fresh_total() -> float:
    tot = 0.0
    for row in _summary():
        df = _book(row["instrument"], row["tf"])
        pre = pd.Timestamp(PRE_END[row["instrument"]])
        tot += float(df.loc[df["entry_time"] > pre, "pnl"].sum())
    return round(tot, 2)


def _fresh_v1() -> tuple[bool, str]:
    """V1 — COUNT RECORD: the fresh window (entries after each pre-extension end) holds
    exactly 25 trades, all NQ/ES (the only instruments whose box outlived their candle end)."""
    n = 0
    off = []
    for row in _summary():
        df = _book(row["instrument"], row["tf"])
        pre = pd.Timestamp(PRE_END[row["instrument"]])
        k = int((df["entry_time"] > pre).sum())
        n += k
        if k and row["instrument"] not in ("NQ", "ES"):
            off.append(f"{row['instrument']} {row['tf']}: {k}")
    if off:
        return False, f"fresh entries outside NQ/ES: {off}"
    return n == 25, f"fresh trades = {n} (expect 25), all NQ/ES"


def _fresh_v2() -> tuple[bool, str]:
    """V2 — ANCHOR CLOSURE: the NQ 4h full book equals the known deployed anchor
    ($151,655.19 / 277) plus exactly its 2 fresh-sliver trades (−$599.00) → $151,056.19 / 279.
    The delta is fully attributed; nothing else moved."""
    df = _book("NQ", "4h")
    pre = pd.Timestamp(PRE_END["NQ"])
    fresh = df[df["entry_time"] > pre]
    old = float(df["pnl"].sum()) - float(fresh["pnl"].sum())
    ok = (abs(old - 151655.19) < 0.01 and len(df) - len(fresh) == 277 and len(fresh) == 2)
    return ok, f"book−fresh = ${old:,.2f}/{len(df)-len(fresh)} vs anchor $151,655.19/277; fresh n={len(fresh)}"


def _fresh_v3() -> tuple[bool, str]:
    """V3 — POWER HONESTY (falsifier of over-claiming): if the fresh window were a usable
    verdict on the champions, it would have a non-trivial sample. Confirm it does NOT:
    every slot's fresh n is < 10, so per the pre-registration NO slot receives a fresh-window
    verdict (report-only). This check FAILS if any slot quietly crossed the verdict bar."""
    for row in _summary():
        df = _book(row["instrument"], row["tf"])
        pre = pd.Timestamp(PRE_END[row["instrument"]])
        k = int((df["entry_time"] > pre).sum())
        if k >= 10:
            return False, f"{row['instrument']} {row['tf']}: fresh n={k} >= 10 — verdict bar crossed"
    return True, "all slots fresh n < 10 — no fresh-window verdicts permitted (as registered)"


register(Claim(
    id="FWD-FRESH-WINDOW-SLIVER",
    issue="#176",
    statement="Phase 2 (#176): the genuinely-unseen fresh window contains only 25 entries "
              "(+$1,823.47 total, all NQ/ES May sliver + the with20d NQ box days), because the "
              "box feed — owner-scraped — ends before or at each instrument's old candle end. "
              "NO fresh-window verdict on any champion is possible yet (all n<10); the blocker "
              "is the owner's box export through 2026-08, not engineering.",
    source="optimize/fwd/data/fwd_book_*.csv (fresh cut re-derived)",
    value_fn=_fresh_total,
    expect=1823.47,
    tol=0.5,
    blind_spot="The fresh window says nothing about July/August behavior — zero entries exist "
               "there; exits, too, all resolve by early July. The extension's value for those "
               "months is latent until fresh boxes land.",
    checks=[Check("V1", "fresh-count-and-locus", _fresh_v1),
            Check("V2", "nq4h-anchor-closure", _fresh_v2),
            Check("V3", "no-verdict-bar-crossed", _fresh_v3)],
))


def _gate_result() -> dict:
    return json.load(open(FWD / "fwd_dashboard_gate.json"))


def _dash_v1() -> tuple[bool, str]:
    """V1 — FULL SWEEP: the Playwright gate ran all 54 slots and every one matched the core
    book exactly (on-screen rounded P/L and trade count)."""
    g = _gate_result()
    ok = [k for k, v in g.items() if v.get("status") == "ok"]
    bad = {k: v for k, v in g.items() if v.get("status") != "ok"}
    return (len(ok) == 54 and not bad), f"match {len(ok)}/54; bad={list(bad)[:5]}"


def _dash_v2() -> tuple[bool, str]:
    """V2 — EVIDENCE EXISTS: every matched slot has its committed screenshot on disk."""
    g = _gate_result()
    missing = [k for k, v in g.items()
               if v.get("status") == "ok" and not (FWD / "shots" / v["shot"]).exists()]
    return (not missing), (f"missing shots: {missing[:5]}" if missing else "54/54 screenshots present")


def _dash_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the gate can see a lie): the recorded want_pnl strings were derived
    from the books at gate time; confirm that perturbing any book total by $1 would break its
    slot's match — i.e. seen==want is an exact string equality, not a tolerance. We re-derive
    want from the committed summary and demand equality with the gate's stored want."""
    summ = {f"{r['instrument']}_{r['tf']}": r for r in _summary()}
    g = _gate_result()
    for k, v in g.items():
        if v.get("status") != "ok":
            continue
        p = summ[k]["pnl"]
        r = round(p)
        want = ("+" if r >= 0 else "-") + "$" + f"{abs(r):,}"
        if want != v["want_pnl"] or v["seen_pnl"] != v["want_pnl"]:
            return False, f"{k}: want drift ({want} vs {v['want_pnl']} vs seen {v['seen_pnl']})"
    return True, "want==seen exact strings for all matched slots; $1 perturbation would break"


def _dash_count() -> float:
    g = _gate_result()
    return float(sum(1 for v in g.values() if v.get("status") == "ok"))


register(Claim(
    id="FWD-DASHBOARD-VISUAL-GATE",
    issue="#176",
    statement="Phase 3 (#176): the branch dashboard (:8250 on the extended root), driven the "
              "house way — SSH tunnel + Playwright, never interactive — reproduced every core "
              "book on screen: 54/54 slots' visible total P/L and trade count equal the Phase-1 "
              "books exactly; 54 screenshots committed as evidence.",
    source="optimize/fwd/data/fwd_dashboard_gate.json + shots/",
    value_fn=_dash_count,
    expect=54.0,
    tol=0.0,
    blind_spot="The gate reads the L1 view headline; it does not re-verify every chart pixel, "
               "and production :8200 (old root) intentionally still serves the pre-extension "
               "books until the owner blesses a swap.",
    checks=[Check("V1", "54-of-54-match", _dash_v1),
            Check("V2", "screenshots-exist", _dash_v2),
            Check("V3", "exact-string-equality", _dash_v3)],
))
