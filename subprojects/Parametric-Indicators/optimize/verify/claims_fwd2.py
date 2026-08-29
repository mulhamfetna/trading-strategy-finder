"""WS-FWD round 2 claims (#179) — the deployed champions on the REAL forward window.

Round 1 (#176, claims_fwd.py) ran on candles to 2026-08-07 but boxes ending 05-22..06-26, so
its "fresh window" was a 25-trade sliver. The owner's box export (raw 2026-05-18..08-07, all 9)
was merged on the server under gate E (optimize/fwd/fwd_merge_boxes.py), the ES box was found
double-shifted and corrected, and the whole pipeline re-ran into optimize/fwd/data_r2/.
Pre-registration: docs/WS-FWD-PREREGISTRATION.md "Round 2" (filed before the run).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

R1 = Path(__file__).resolve().parents[1] / "fwd" / "data"
R2 = Path(__file__).resolve().parents[1] / "fwd" / "data_r2"

PRE_END = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00",
           "GC": "2026-07-02 19:59:00", "SI": "2026-07-02 19:59:00",
           "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
           "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00",
           "YM": "2026-07-05 19:59:00"}
# round-1 box ends (entries beyond these were IMPOSSIBLE in round 1)
BOX_END_R1 = {"NQ": "2026-06-10", "ES": "2026-05-22", "GC": "2026-06-27", "SI": "2026-06-29",
              "HG": "2026-06-27", "CL": "2026-06-27", "NG": "2026-06-27", "RTY": "2026-06-27",
              "YM": "2026-06-27"}
TAPE_END = pd.Timestamp("2026-08-07 17:00:00")


def _summary() -> list[dict]:
    return json.load(open(R2 / "fwd_run_summary.json"))


def _book(root: Path, tok: str, tf: str) -> pd.DataFrame:
    df = pd.read_csv(root / f"fwd_book_{tok}_{tf}.csv")
    for c in ("entry_time", "exit_time"):
        df[c] = pd.to_datetime(pd.to_numeric(df[c]), unit="s")
    return df


def _slots() -> list[tuple[str, str]]:
    return [(r["instrument"], r["tf"]) for r in _summary()]


# ----------------------------------------------------------------------------- claim 1
def _merge_v1() -> tuple[bool, str]:
    """V1 — GATE E RECORD: every merged file passed gate E (no engine-column value conflict on
    the overlap, no columns missing in the drop); the only overlap disagreements are NaN-vs-
    value on the sparse trend columns (scrape repaint), recorded per file."""
    rep = json.load(open(R2.parent / "data" / "fwd_box_merge_report.json"))
    merged = {k: v for k, v in rep.items() if "gate_e" in v}
    bad = [k for k, v in merged.items() if not v["gate_e"] or v["engine_fail"]]
    warn = {k: v["engine_warn"] for k, v in merged.items() if v["engine_warn"]}
    ok = len(merged) == 16 and not bad and all(v.get("merged_rows") for v in merged.values())
    return ok, f"{len(merged)} files gate E, failures={bad}, nan-vs-value warnings={list(warn)}"


def _merge_v2() -> tuple[bool, str]:
    """V2 — APPEND-ONLY WHERE IT MUST BE: for the 42 non-NQ/non-ES slots the round-2 book is
    identical (entry times and P/L) to the round-1 book for every entry more than 7 days before
    the round-1 box end — the refresh added rows, it did not rewrite history."""
    bad = []
    for tok, tf in _slots():
        if tok in ("NQ", "ES"):
            continue
        cut = pd.Timestamp(BOX_END_R1[tok]) - pd.Timedelta(days=7)
        a = _book(R1, tok, tf); b = _book(R2, tok, tf)
        a = a[a["entry_time"] < cut].reset_index(drop=True)
        b = b[b["entry_time"] < cut].reset_index(drop=True)
        same = len(a) == len(b) and (a["entry_time"].values == b["entry_time"].values).all() \
            and float(np.abs(a["pnl"].values - b["pnl"].values).max()) < 0.01
        if not same:
            bad.append(f"{tok}_{tf}")
    return (not bad), (f"42 slots identical before the old box end" if not bad else f"diverged: {bad}")


def _merge_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the new boxes really drove the books): every one of the 54 slots has at
    least one entry AFTER its round-1 box end (impossible in round 1), no entry after the tape
    end, and the ES books differ from round 1 from the FIRST month (a no-op 'correction' would
    leave them identical)."""
    no_new = []; beyond = []
    for tok, tf in _slots():
        b = _book(R2, tok, tf)
        lim = pd.Timestamp(BOX_END_R1[tok]) + pd.Timedelta(days=1)
        if int((b["entry_time"] > lim).sum()) == 0:
            no_new.append(f"{tok}_{tf}")
        if int((b["entry_time"] > TAPE_END).sum()):
            beyond.append(f"{tok}_{tf}")
    es_same = []
    for tf in ("4h", "2h", "1h", "15m", "5m", "2m"):
        a = _book(R1, "ES", tf); b = _book(R2, "ES", tf)
        jan = pd.Timestamp("2025-02-01")
        sa = set(a.loc[a["entry_time"] < jan, "entry_time"]); sb = set(b.loc[b["entry_time"] < jan, "entry_time"])
        if sa == sb:
            es_same.append(tf)
    ok = not no_new and not beyond and not es_same
    return ok, f"slots without post-old-box entries={no_new}; entries beyond tape={beyond}; ES slots unchanged in Jan-2025={es_same}"


def _books_total() -> float:
    return round(sum(float(_book(R2, t, f)["pnl"].sum()) for t, f in _slots()), 2)


register(Claim(
    id="FWD2-BOX-MERGE-AND-54-BOOKS",
    issue="#179",
    statement="Round 2 (#179): the owner's box export (raw 2026-05-18..08-07, all 9) was merged "
              "on the server under gate E — 16 files, zero engine-column conflicts on 31-day "
              "overlaps (NaN-vs-value only on sparse trend columns, recorded); engine boxes now "
              "end 2026-08-06 for all 9. The ES 'raw' box was found already shifted and had been "
              "shifted AGAIN by onboarding (Friday rows carried next week's levels) — corrected to "
              "a single shift. All 54 `best` champions re-ran on the extended root with the L1 "
              "cache wiped: 54/54 ok, aggregate full-book P/L $2,169,105 (round 1: $2,180,903; "
              "ES full books -$30,893 on the corrected box, ES_2m +$12,042 -> -$435). Round-1 NQ "
              "books had never seen the with20d box (data-blind L1 cache served the 05-22 "
              "result) — round 2 has NQ entries from 2026-05-25 on.",
    source="optimize/fwd/data/fwd_box_merge_report.json + optimize/fwd/data_r2/fwd_book_*.csv",
    value_fn=_books_total,
    expect=2169105.47,
    tol=0.5,
    blind_spot="The 2026 part of every full book is still the SELECTION window of `best`; only "
               "the fresh window is OOS. The W/M trend columns repaint between scrapes (one NQ "
               "date) — existing rows were kept, so the live path sees the earlier scrape.",
    checks=[Check("V1", "gate-e-record", _merge_v1),
            Check("V2", "append-only-42-slots", _merge_v2),
            Check("V3", "new-boxes-drove-the-books", _merge_v3)],
))


# ----------------------------------------------------------------------------- claim 2
def _fresh_books() -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    out = []
    for tok, tf in _slots():
        b = _book(R2, tok, tf)
        fr = b[b["entry_time"] > pd.Timestamp(PRE_END[tok])]
        ins = b[b["entry_time"] <= pd.Timestamp(PRE_END[tok])]
        out.append((f"{tok}_{tf}", fr, ins))
    return out


def _fresh_total() -> float:
    return round(sum(float(fr["pnl"].sum()) for _, fr, _ in _fresh_books()), 2)


def _fresh_v1() -> tuple[bool, str]:
    """V1 — THE WINDOW IS REAL AND POWERED AT FLEET LEVEL: 3,733 fresh entries across 54 slots,
    47 slots with n >= 10 (verdict-eligible), every instrument represented, entries span
    late May .. 2026-08-06."""
    fb = _fresh_books()
    n = sum(len(fr) for _, fr, _ in fb)
    n10 = sum(1 for _, fr, _ in fb if len(fr) >= 10)
    toks = {k.split("_")[0] for k, fr, _ in fb if len(fr)}
    last = max(fr["entry_time"].max() for _, fr, _ in fb if len(fr))
    ok = n == 3733 and n10 == 47 and len(toks) == 9 and last.date() == pd.Timestamp("2026-08-06").date()
    return ok, f"n={n}, slots n>=10: {n10}/54, instruments {len(toks)}/9, last entry {last}"


def _fresh_v2() -> tuple[bool, str]:
    """V2 — STRESSED COSTS LEAD: at $10/round-trip the fleet fresh window is -$7,522.91 and at
    $25/rt -$63,517.91 (n=3,733); the raw fleet mean $7.98/trade is NOT distinguishable from
    zero (t=0.88), and at $25/rt leans negative (t=-1.87)."""
    a = np.concatenate([fr["pnl"].values for _, fr, _ in _fresh_books()])
    n = len(a); tot = a.sum()
    c10 = round(tot - 10 * n, 2); c25 = round(tot - 25 * n, 2)
    se = a.std(ddof=1) / np.sqrt(n)
    t0 = a.mean() / se; t25 = (a.mean() - 25) / se
    ok = abs(c10 - (-7522.91)) < 1 and abs(c25 - (-63517.91)) < 1 and abs(t0) < 2 and t25 < 0
    return ok, f"@$10 {c10:+,.2f}; @$25 {c25:+,.2f}; mean/trade {a.mean():.2f} t0={t0:.2f} t25={t25:.2f}"


def _fresh_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the window is out-of-sample, not a re-reading of the selection window):
    if fresh trades were drawn from the in-sample distribution, the fleet would show about
    sum(n_fresh x in-sample mean) = $169,814. Observed $29,807 = 17.6%; fleet decay t=-2.53.
    Demand: observed < 50% of the in-sample expectation AND decay t < -2."""
    fb = _fresh_books()
    exp = sum(len(fr) * ins["pnl"].mean() for _, fr, ins in fb)
    a = np.concatenate([fr["pnl"].values for _, fr, _ in fb])
    b = np.concatenate([ins["pnl"].values for _, _, ins in fb])
    t = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    obs = a.sum()
    ok = obs < 0.5 * exp and t < -2
    return ok, f"observed {obs:,.0f} vs in-sample-rate expectation {exp:,.0f} ({obs / exp:.1%}); decay t={t:.2f}"


register(Claim(
    id="FWD2-FRESH-WINDOW",
    issue="#179",
    statement="Round 2 (#179) fresh window (entries after each instrument's pre-extension engine "
              "end, through 2026-08-06): 3,733 trades, raw +$29,807 — but -$7,523 at $10/rt and "
              "-$63,518 at $25/rt. Fleet mean $7.98/trade is not distinguishable from zero; it IS "
              "distinguishable from the in-sample $31.29/trade (decay t=-2.53; the window returns "
              "17.6% of what the selection-window rate predicts). Per slot: 44 consistent with "
              "in-sample (under-powered: MDE $100-$1,700/trade), 3 below at t<-2 (CL_2h, NQ_2m, "
              "SI_1h), 7 with n<10 (no verdict). Value lives in 4h (+$14,631 raw, +$10,106 at "
              "$25/rt, 181 trades); 1h is the losing rung (-$17,769 raw); ES is the only "
              "instrument positive at $25/rt (+$17,119 on the corrected box).",
    source="optimize/fwd/data_r2/fwd_book_*.csv (fresh cut re-derived) + fresh_stats.txt",
    value_fn=_fresh_total,
    expect=29807.09,
    tol=0.5,
    blind_spot="2.5 months is one regime; per-slot verdicts are mostly under-powered and the "
               "fleet t-stat mixes 4h and 2m trades of very different size. NQ 5m (n=4) and "
               "YM 2h/4h, RTY 15m/1h/2h, ES 5m have no verdict.",
    checks=[Check("V1", "window-real-and-powered", _fresh_v1),
            Check("V2", "stressed-costs-lead", _fresh_v2),
            Check("V3", "oos-not-in-sample", _fresh_v3)],
))


# ----------------------------------------------------------------------------- claim 3
def _gate_result() -> dict:
    return json.load(open(R2 / "fwd_dashboard_gate.json"))


def _money_val(x: str) -> int:
    return int(x.replace("$", "").replace(",", "").replace("+", ""))


def _deltas() -> list[dict]:
    summ = {f"{r['instrument']}_{r['tf']}": r for r in _summary()}
    out = []
    for k, v in _gate_result().items():
        n = summ[k]["n_trades"]
        dp = abs(_money_val(v["seen_pnl"]) - _money_val(v["want_pnl"]))
        out.append({"slot": k, "n": n, "dpnl": dp, "bound": 0.005 * n + 1,
                    "dn": v["seen_n"] - v["want_n"], "shot": v["shot"]})
    return out


def _dash_v1() -> tuple[bool, str]:
    """V1 — MONEY ON SCREEN == THE BOOKS: 54/54 within the cent-rounding bound; NQ counts exact
    6/6 with P/L within $1."""
    d = _deltas()
    over = [x["slot"] for x in d if x["dpnl"] > x["bound"]]
    nq = [x for x in d if x["slot"].startswith("NQ_")]
    nq_ok = len(nq) == 6 and all(x["dn"] == 0 and x["dpnl"] <= 1 for x in nq)
    ok = len(d) == 54 and not over and nq_ok
    return ok, (f"54 slots, over-bound={over}, NQ exact {nq_ok}, dollar-exact "
                f"{sum(1 for x in d if x['dpnl'] == 0)}/54, within $1 {sum(1 for x in d if x['dpnl'] <= 1)}/54")


def _dash_v2() -> tuple[bool, str]:
    """V2 — EVIDENCE EXISTS: 54 committed screenshots."""
    missing = [x["slot"] for x in _deltas() if not (R2 / "shots" / x["shot"]).exists()]
    return (not missing), ("54/54 screenshots present" if not missing else f"missing: {missing[:5]}")


def _dash_v3() -> tuple[bool, str]:
    """V3 — FALSIFIER + THE RECORDED FAILURE: >= 20 slots dollar-exact and worst delta below
    maxbound/1.5 (a different book could not cluster like this); AND the pre-registered count
    leg (strategy-engine status-line count within 3% of the causal book) FAILS on exactly one
    slot, ES_15m (-25 of 205 = 12%) — pinned here so it cannot be quietly absorbed."""
    d = _deltas()
    exact = sum(1 for x in d if x["dpnl"] == 0)
    worst = max(x["dpnl"] for x in d)
    maxbound = max(x["bound"] for x in d)
    cnt_bad = sorted(x["slot"] for x in d if abs(x["dn"]) / max(x["n"], 1) > 0.03)
    ok = exact >= 20 and worst < maxbound / 1.5 and cnt_bad == ["ES_15m"]
    return ok, (f"dollar-exact {exact}/54; max Δ ${worst} vs max bound ${maxbound:.0f}; "
                f"count-leg failures (>3%): {cnt_bad}")


def _dash_count() -> float:
    return float(sum(1 for x in _deltas() if x["dpnl"] <= x["bound"]))


register(Claim(
    id="FWD2-DASHBOARD-VISUAL-GATE",
    issue="#179",
    statement="Round 2 (#179) dashboard gate (:8250 restarted on the extended root, scripted "
              "Playwright on the server, 54 screenshots): MONEY leg PASS 54/54 within the "
              "cent-rounding bound (26 dollar-exact, 36 within $1, max Δ $25 vs $45 bound), NQ "
              "counts exact 6/6. COUNT leg FAIL on 1/54: ES_15m status-line (strategy engine) "
              "shows 180 trades vs the causal book's 205 (-12%, bound 3%); 25 non-NQ slots "
              "differ by -25..+94. The strategy-vs-causal count divergence (#176 observation) is "
              "now a gate failure on ES and needs its own issue before any live routing reads "
              "UI counts. Gate regex fixed for the dashboard's '$-437' negative rendering.",
    source="optimize/fwd/data_r2/fwd_dashboard_gate.json + shots/",
    value_fn=_dash_count,
    expect=54.0,
    tol=0.0,
    blind_spot="Headline cards + status line only; chart pixels unverified. Prod :8200 still "
               "serves the old root. The count divergence is recorded, not explained.",
    checks=[Check("V1", "money-within-bound-nq-exact", _dash_v1),
            Check("V2", "screenshots-exist", _dash_v2),
            Check("V3", "falsifier-and-pinned-count-failure", _dash_v3)],
))
