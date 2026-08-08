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

    # ---- 3. ⭐ TIMEZONE, from the volume signature — no external data needed ----------------------
    c = Check("timezone (RTH volume signature)",
              "Pins the frame to Eastern wall-clock to the MINUTE via the 09:30 open. It CANNOT see a "
              "whole-day shift, and for an instrument whose volume peaks elsewhere (energy at the EIA "
              "release, metals in London hours) the signature is weaker — check the reported top-3.")
    vol_by_min = df.groupby(df.Date.dt.strftime("%H:%M")).Volume.sum().sort_values(ascending=False)
    top = list(vol_by_min.head(3).index)
    rank = top.index(RTH_OPEN) + 1 if RTH_OPEN in top else None
    c.set(rank is not None,
          f"busiest minutes by volume: {top}; {RTH_OPEN} ET rank={rank or '>3'}  "
          f"(a frame stored on UTC would peak at 14:30)")
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
    c.set(len(thin) <= 1, f"bars per year median {med:,.0f}; thin years {thin or 'none'}")
    checks.append(c)

    # ---- 6. price continuity (contract rolls / splices) -------------------------------------------
    c = Check("price continuity",
              "Flags single-bar jumps that suggest an unadjusted contract roll. A CONSISTENTLY "
              "back-adjusted series passes here even if the adjustment method differs from the "
              "existing frame's — check 4 is what catches that, and only on the overlap.")
    r = df.Close.pct_change().abs() * 100
    jumps = int((r > MAX_BAR_JUMP_PCT).sum())
    worst = float(np.nanmax(r)) if len(r) else float("nan")
    c.set(jumps == 0, f"{jumps} single-bar moves > {MAX_BAR_JUMP_PCT}%; largest {worst:.2f}%")
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
                return d[["Date", "Close"]]
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
