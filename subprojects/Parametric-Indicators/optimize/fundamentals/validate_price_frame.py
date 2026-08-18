"""#121 — acceptance gate for a NEW long-history price frame, BEFORE it is wired into anything.

⚠️⚠️ WHY THIS EXISTS AND WHY IT RUNS FIRST

This project's expensive failures were never bad analysis. They were **plausible data accepted without a
check that could have failed**, and every one of them survived for weeks:

    · TradingView's pre-2016 rows were an HOUR LATE in summer (a fixed UTC offset). I verified the
      timestamps ON ONE SERIES, it passed, and I generalised. An event window built on those rows sits
      an hour from the release and returns a MANUFACTURED NULL. (#114)
    · EDGAR stamped 'Z' on Eastern times for SOME filers and not others — 22 earnings events 4-5h
      wrong, caught by a stability check rather than by inspection. (#110)
    · An absolute 40-point stop was 0.13% of NQ and 1.3% of GC, producing a fake "gold is calmer"
      result. Same number, different instrument, different meaning. (#115)

A new instrument frame can carry EVERY one of those defects, and none of them raises an exception.
So the gate runs before the frame is used, and it is written to FAIL.

⭐⭐ THE STRONGEST CHECK IS THE OVERLAP. We already hold 18 months for each of these instruments
(2025-01-01 -> 2026-07), and it is the frame the ENGINE trades. A new long frame MUST agree with it
where they overlap. That is an independent-source check with a ready-made answer key — if the new file
disagrees on shared timestamps, one of the two is wrong and nothing may proceed until we know which.

⭐ AND THE TIMEZONE CHECK NEEDS NO EXTERNAL DATA. US index futures have a volume signature the clock
cannot fake: the regular session opens at 09:30 US-Eastern and volume explodes. If the busiest minute
of the day is not 09:30, the frame is not on Eastern wall-clock — which is the convention every other
file here uses, and mixing conventions is exactly the #114 defect.

V3 falsification: the gate is handed a DELIBERATELY CORRUPTED copy of the frame (shifted one hour, the
#114 defect replayed) and must reject it. A gate that has never failed is untested.

    python3 optimize/fundamentals/validate_price_frame.py --file <new_CL_1m.csv> --instrument CL
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

REQUIRED_COLS = ["Date", "Open", "High", "Low", "Close", "Volume"]

# The engine's own frames, which the new file must agree with on the overlap.
EXISTING_HINTS = [
    "~/Mulham/wsg-i/bundle_data_all/{inst}_1m.csv",
    "~/Mulham/wsg-i/bundle_data_clng/{inst}_1m.csv",
    "{root}/bundle_data_all/{inst}_1m.csv",
]

RTH_OPEN = "09:30"          # US-Eastern; the volume signature that pins the timezone
MAX_BAR_JUMP_PCT = 10.0     # a single 1-minute bar moving more than this is a roll/splice artefact


class Check:
    def __init__(self, name: str, blind_spot: str):
        self.name, self.blind_spot = name, blind_spot
        self.ok: bool | None = None
        self.detail = ""

    def set(self, ok: bool, detail: str):
        self.ok, self.detail = bool(ok), detail
        return self


# ⚠️ TWO COLUMN CONVENTIONS EXIST IN THIS REPO, and the gate must validate the frame AS THE LOADER
# SEES IT, not as it sits on disk:
#     engine frames        Date, Open, High, Low, Close, Volume
#     16-year frames       datetime, open, high, low, close, volume
# `extended_data._read` already renames the second into the first. A gate that only accepted one of
# them would reject a perfectly good file — and worse, would tempt someone to "fix" the FILE to satisfy
# the GATE, silently diverging it from what the loader expects.
_ALIASES = {"datetime": "Date", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume"}


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={k: v for k, v in _ALIASES.items() if k in df.columns})
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns {missing}; found {list(df.columns)}. "
                         f"Accepted conventions: {REQUIRED_COLS} or {list(_ALIASES)}")
    df["Date"] = pd.to_datetime(df["Date"])
    if getattr(df["Date"].dt, "tz", None) is not None:
        # ⚠️ A tz-AWARE column is not a convenience, it is a different convention. Every other frame
        # here is tz-naive US-Eastern wall-clock, and silently mixing the two is the #114 defect.
        raise ValueError("Date column is timezone-AWARE; every frame here is tz-naive US-Eastern "
                         "wall-clock. Convert with .dt.tz_convert('America/New_York').dt.tz_localize(None)")
    return df.sort_values("Date").reset_index(drop=True)


def run_checks(df: pd.DataFrame, instrument: str, existing: pd.DataFrame | None) -> list[Check]:
    checks: list[Check] = []

    # ---- 1. schema and ordering ------------------------------------------------------------------
    c = Check("schema + ordering", "Says nothing about whether the VALUES are right — only shape.")
    dup = int(df.Date.duplicated().sum())
    mono = bool(df.Date.is_monotonic_increasing)
    c.set(dup == 0 and mono, f"{len(df):,} rows, duplicates={dup}, monotonic={mono}, "
                             f"span {df.Date.min()} -> {df.Date.max()}")
    checks.append(c)

    # ---- 2. OHLC internal consistency -------------------------------------------------------------
    c = Check("OHLC sanity", "Catches impossible bars. A frame can be perfectly consistent and still "
                             "be the wrong instrument, the wrong contract, or the wrong timezone.")
    bad = int((~((df.Low <= df[["Open", "Close"]].min(axis=1)) &
                 (df.High >= df[["Open", "Close"]].max(axis=1)) &
                 (df.High >= df.Low))).sum())
    c.set(bad == 0, f"{bad} bars violate Low <= min(O,C) <= max(O,C) <= High")
    checks.append(c)

    # ---- 3. ⭐ TIMEZONE, from the INTRADAY VOLUME PROFILE -----------------------------------------
    # ⚠️⚠️ THE FIRST VERSION OF THIS CHECK WAS WRONG AND I CAUGHT IT ON KNOWN-GOOD DATA. It required the
    # busiest minute of the day to be the 09:30 equity open. NQ passes. GOLD FAILS: GC's volume peaks at
    # 13:29 (the COMEX floor close) and 08:30 (the macro release slot). The GC 16-year frame is provably
    # correct — it matches the engine's own frame on 530,917 overlapping bars at 100.0000% — so this was
    # a FALSE POSITIVE on good data, and a gate that cries wolf is one everyone learns to skip.
    #
    # ⭐ The fix generalises instead of hardcoding session knowledge per instrument: compare the new
    # frame's MINUTE-OF-DAY VOLUME PROFILE against the EXISTING frame's. The existing 18-month file is
    # known-good and on the right convention, so it is the answer key for the CLOCK as well as for the
    # prices. A one-hour shift rotates the profile and destroys the correlation, whatever the instrument.
    c = Check("timezone (intraday volume profile vs the existing frame)",
              "Pins the CLOCK using the existing frame as the answer key, so it works for any "
              "instrument. It CANNOT see an error that is IDENTICAL in both files, nor a whole-DAY "
              "shift (the profile is invariant to that). Falls back to a session-anchor heuristic when "
              "no existing frame is available, and that fallback is materially weaker.")
    # ⚠️⚠️ SECOND DEFECT IN THIS CHECK, found on the owner's real data. The first version compared the
    # FULL new frame's profile against the existing frame's — but they cover DIFFERENT PERIODS (16 years
    # vs 18 months), so it was comparing two different populations and calling the difference a timezone
    # error. It failed CL and NG, whose clocks are provably correct: restricted to the overlap window
    # their profiles are IDENTICAL to the existing frame's, to the unit.
    #
    # What it was actually detecting is a PRE-2016 VOLUME-ATTRIBUTION artefact (see check 5a) — a real
    # finding, but not a timezone one. Comparing like with like separates them.
    if existing is not None and "Volume" in existing.columns:
        e = existing.dropna(subset=["Volume"])
        lo, hi = e.Date.min(), e.Date.max()
        n_ov = df[(df.Date >= lo) & (df.Date <= hi)]
        prof_new = n_ov.groupby(n_ov.Date.dt.hour * 60 + n_ov.Date.dt.minute).Volume.sum()
        prof_old = e.groupby(e.Date.dt.hour * 60 + e.Date.dt.minute).Volume.sum()
        idx = prof_new.index.union(prof_old.index)
        a_ = prof_new.reindex(idx).fillna(0.0).to_numpy(dtype=float)
        b_ = prof_old.reindex(idx).fillna(0.0).to_numpy(dtype=float)
        from scipy import stats as _st
        rho = float(_st.spearmanr(a_, b_).statistic)
        peak_new = int(prof_new.idxmax()); peak_old = int(prof_old.idxmax())
        c.set(rho > 0.80 and peak_new == peak_old,
              f"profile agreement rho={rho:.3f}; busiest minute new={peak_new//60:02d}:{peak_new%60:02d} "
              f"old={peak_old//60:02d}:{peak_old%60:02d}")
    else:
        prof_new = df.groupby(df.Date.dt.hour * 60 + df.Date.dt.minute).Volume.sum()
        top = [f"{m//60:02d}:{m%60:02d}" for m in prof_new.sort_values(ascending=False).head(3).index]
        anchors = {RTH_OPEN, "15:59", "16:00", "08:30", "13:29", "13:30", "09:31"}
        c.set(bool(set(top) & anchors),
              f"NO existing frame — weak fallback. busiest minutes {top}; "
              f"recognised US-session anchors {sorted(anchors)}")
    checks.append(c)

    # ---- 4. ⭐⭐ OVERLAP AGREEMENT with the frame the engine already trades -----------------------
    c = Check("overlap agreement with the existing frame",
              "The single strongest check, but it only covers the OVERLAPPING window. The NEW history "
              "before 2025 has no answer key here and is covered only by checks 3, 5 and 6.")
    if existing is None:
        c.set(False, "NO EXISTING FRAME FOUND TO COMPARE — this check could not run, which is NOT a pass")
    else:
        j = df.merge(existing, on="Date", suffixes=("_new", "_old"))
        if len(j) < 1000:
            c.set(False, f"only {len(j)} overlapping bars — too few to verify")
        else:
            rel = (j.Close_new - j.Close_old).abs() / j.Close_old.replace(0, np.nan)
            agree = float((rel < 1e-6).mean())
            c.set(agree > 0.999,
                  f"{len(j):,} overlapping bars, {agree:.4%} identical Close; "
                  f"max relative difference {np.nanmax(rel):.2e}")
    checks.append(c)

    # ---- 5. coverage by year ----------------------------------------------------------------------
    c = Check("coverage by year",
              "Detects an era that is thin or absent. It CANNOT detect an era that is present but "
              "WRONG — which is precisely how the #114 DST defect survived.")
    per_year = df.groupby(df.Date.dt.year).size()
    med = float(per_year.median())
    thin = {int(y): int(n) for y, n in per_year.items() if n < 0.5 * med}
    # ⚠️ Thin EARLY years are a real property of this source, not corruption — and rejecting the file
    # for them would throw away 10 good years to avoid 3 sparse ones. Reported as a LIMIT: the first
    # year at which coverage is full becomes the recommended study floor. A thin year in the MIDDLE of
    # the span is a different animal and still fails.
    interior = {y: n for y, n in thin.items() if y not in (min(per_year.index), max(per_year.index))
                and y > min(y2 for y2 in per_year.index if per_year[y2] >= 0.5 * med)}
    full_from = min((int(y) for y in per_year.index if per_year[y] >= 0.9 * med), default=None)
    c.set(not interior,
          f"bars per year median {med:,.0f}; thin years {thin or 'none'}; "
          f"⭐ full coverage from {full_from} -> USE {full_from}+ AS THE STUDY FLOOR; "
          f"interior gaps {interior or 'none'}")
    checks.append(c)

    # ---- 5a. ⚠️ pre-2016 VOLUME-ATTRIBUTION artefact ---------------------------------------------
    # Found on the owner's data: in the sparse early years a large share of each year's volume sits in
    # the last minutes of the session (18:59 / 19:59) — the aggregator appears to have parked the
    # volume of untracked minutes into the closing bars. Prices are unaffected (check 4 is 100%), but
    # any VOLUME-based analysis on those years is meaningless, and it silently distorted check 3.
    c = Check("volume attribution by year",
              "Detects volume parked into end-of-session bars. It says NOTHING about prices, which "
              "check 4 covers, and it only looks at the two closing minutes.")
    tail_min = df.Date.dt.strftime("%H:%M").isin(["18:59", "19:59"])
    share = (df[tail_min].groupby(df.loc[tail_min, "Date"].dt.year).Volume.sum()
             / df.groupby(df.Date.dt.year).Volume.sum() * 100).dropna()
    bad_years = {int(y): round(float(v), 1) for y, v in share.items() if v > 5.0}
    c.set(True, f"years with >5% of annual volume in the closing two minutes: {bad_years or 'none'}"
                f"  ⚠️ volume-based analysis is invalid in those years; prices are unaffected")
    checks.append(c)

    # ---- 6. price continuity (contract rolls / splices) -------------------------------------------
    # ⚠️ The first version failed any frame with a big single-bar move, which rejected CL, NG and HG —
    # and their jumps are NOT corruption. Measured on the owner's data, they are two different things:
    #   · at the 18:00 SESSION OPEN on roll days = an UNADJUSTED CONTRACT ROLL. Structural, and it
    #     cannot fall inside an event window for an 08:30 / 10:00 / 10:30 / 14:00 release.
    #   · INTRADAY = real market history (CL's 2020 OPEC/COVID collapse, HG's 2025 tariff crash).
    # Only an intraday jump is a hazard for an event study, so they are counted separately and the
    # roll gaps are reported rather than treated as a failure.
    c = Check("price continuity",
              "Separates session-boundary roll gaps from intraday jumps. It CANNOT tell a genuine "
              "market crash from a data error — both are intraday jumps — so intraday hits are "
              "REPORTED for a human to adjudicate, not auto-failed. A consistently back-adjusted "
              "series passes even if its adjustment differs from the existing frame's; only check 4 "
              "catches that, and only on the overlap.")
    r = df.Close.pct_change().abs() * 100
    big = df.loc[r > MAX_BAR_JUMP_PCT].assign(pct=r[r > MAX_BAR_JUMP_PCT])
    at_open = big.Date.dt.hour.isin([17, 18]) if len(big) else pd.Series(dtype=bool)
    n_roll = int(at_open.sum()) if len(big) else 0
    n_intra = int((~at_open).sum()) if len(big) else 0
    worst = float(np.nanmax(r)) if len(r) else float("nan")
    yrs = sorted(set(big.loc[~at_open, "Date"].dt.year)) if n_intra else []
    c.set(True, f"{n_roll} session-open gaps (unadjusted contract rolls — structurally outside any "
                f"intraday event window) + {n_intra} intraday jumps > {MAX_BAR_JUMP_PCT}% "
                f"{('in ' + str(yrs)) if yrs else ''}; largest overall {worst:.2f}%")
    checks.append(c)

    return checks


def falsification_probe(df: pd.DataFrame, instrument: str, existing: pd.DataFrame | None) -> tuple[bool, str]:
    """V3 — replay the #114 defect against this gate and require it to be REJECTED.

    ⚠️⚠️ A GATE THAT HAS NEVER FAILED IS UNTESTED. The corruption planted is the exact one that cost us
    a week: a one-hour shift, which is what a fixed winter UTC offset produces in summer. If the gate
    accepts it, the gate is decoration and the frame must not be wired in on its say-so.
    """
    bad = df.copy()
    bad["Date"] = bad["Date"] + pd.Timedelta(hours=1)
    res = run_checks(bad, instrument, existing)
    caught = [c.name for c in res if not c.ok]
    return bool(caught), f"one-hour-shifted copy rejected by: {caught or 'NOTHING — GATE IS BLIND'}"


def find_existing(instrument: str) -> pd.DataFrame | None:
    import os
    root = os.environ.get("WSH_DATA_BASE", "")
    for h in EXISTING_HINTS:
        p = Path(h.format(inst=instrument, root=root)).expanduser()
        if p.exists():
            try:
                d = pd.read_csv(p)
                d = d.rename(columns={k: v for k, v in _ALIASES.items() if k in d.columns})
                d["Date"] = pd.to_datetime(d["Date"])
                # Volume is carried too: the existing frame is the answer key for the CLOCK as well
                # as for the prices (check 3).
                keep = ["Date", "Close"] + (["Volume"] if "Volume" in d.columns else [])
                return d[keep]
            except Exception:                                   # noqa: BLE001
                continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--instrument", required=True)
    a = ap.parse_args()

    df = _load(Path(a.file).expanduser())
    existing = find_existing(a.instrument)

    print("=" * 100)
    print(f"PRICE FRAME ACCEPTANCE GATE — {a.instrument}   #121")
    print("=" * 100)
    print(f"  file    : {a.file}")
    print(f"  existing: {'found (overlap check ACTIVE)' if existing is not None else 'NOT FOUND'}")
    print()

    checks = run_checks(df, a.instrument, existing)
    for c in checks:
        print(f"  [{'PASS' if c.ok else 'FAIL'}] {c.name}")
        print(f"         {c.detail}")
        print(f"         ⚠️ blind spot: {c.blind_spot}")
    ok = all(c.ok for c in checks)

    caught, detail = falsification_probe(df, a.instrument, existing)
    print(f"\n  [{'PASS' if caught else 'FAIL'}] V3 falsification — the #114 one-hour shift, replayed")
    print(f"         {detail}")
    print(f"         ⚠️ If this FAILS the gate is blind and its PASSes mean nothing.")

    verdict = "ACCEPT" if (ok and caught) else "REJECT"
    print("\n" + "=" * 100)
    print(f"  VERDICT: {verdict}")
    if verdict == "REJECT":
        print("  ⛔ Do NOT wire this frame in. Every study built on it would inherit the defect, and")
        print("     the failure mode is a MANUFACTURED NULL that looks exactly like a real result.")
    print("=" * 100)
    return 0 if verdict == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
