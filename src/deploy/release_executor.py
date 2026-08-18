"""WS-DEPLOY D1 (#128) — the release executor: the confirmed news trade, exactly as verified.

THE SPEC (pre-registered in #117, confirmed in M3 at Bonferroni α/54 + half-split; the numbers of
record live in `docs/WS-NEWS3-FINAL-REPORT.md` and `p3_events_*.csv`):

    LONG <qty> contracts at the close of the 1-second bar at (release − 300 s)
    stop-loss     entry × (1 − 0.10%)   fill = WORSE  of (line, breaching bar's open)   [GAP-01]
    take-profit   entry × (1 + 0.40%)   resting limit: fill = BETTER of (line, bar open)
    tie rule      one 1-second bar breaching BOTH  ⇒ counted as a STOP (pessimistic)
    timed exit    any open position closes on the bar at (release + 900 s)

RISK FACTS INHERITED FROM THE EVIDENCE (stated here so live use cannot shed them):
    · win rate 36.4%, median event LOSES — the +4R tail pays (23% of events)
    · worst measured loss = 2.1× the nominal stop (gap-through-stop in the sweep second)
    · magnitude is era-concentrated ⇒ the regime monitor (regime_monitor.py) is NOT optional

MODES
    replay  historical proof: walks real 1-second bars and reproduces the M3 evidence.
            V1 parity: at qty=1 the per-event P&L must equal `p3_events_NQ.csv`'s confirmed cell
            EXACTLY (same events, same fills).
    paper   forward mode: reads the schedule, emits time-stamped ORDER INTENTS as JSONL — no
            broker, no side effects. The multi-leg structure is native (a leg list), though the
            confirmed spec uses a single long leg.

⛔ Branch contract (#127): not mergeable without an explicit owner instruction.

    python3 -m src.deploy.release_executor replay --instrument NQ \
        --bars-1s /path/NQ_1s.csv --schedule src/deploy/data/release_schedule.csv \
        [--qty 1] [--parity-ref /path/p3_events_NQ.csv]
    python3 -m src.deploy.release_executor paper --instrument NQ --now "2026-09-10 08:00"
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .schedule import load as load_schedule, DEFAULT_SCHEDULE

# ---- the confirmed spec (frozen; changing any value voids the M3 evidence trail) ---------------
LEAD_S = 300
EXIT_S = 900
STOP_PCT = 0.10
TP_PCT = 0.40
ENTRY_TOL_S = 60                 # the entry bar must sit within 60 s of (release − LEAD_S)
PV = {"NQ": 20.0, "RTY": 50.0, "ES": 50.0, "YM": 5.0}
TICK_USD = {"NQ": 5.0, "RTY": 5.0, "ES": 12.5, "YM": 5.0}   # ES #139 · YM #147 (candidate); same cost formula
COST_PER_LEG = {k: {"optimistic": 2.50 + 1 * t, "realistic": 2.50 + 2 * t,
                    "stressed": 2.50 + 4 * t} for k, t in TICK_USD.items()}


@dataclass
class Leg:
    direction: str               # 'long' | 'short'
    qty: int = 1


@dataclass
class Fill:
    et: str
    title: str
    direction: str
    qty: int
    entry: float
    exit_price: float
    outcome: str                 # 'tp' | 'stopped_pre' | 'stopped_post' | 'timed'
    exit_s_from_release: float
    pnl_points: float            # per contract
    pnl_usd: float               # × qty × pv
    meta: dict = field(default_factory=dict)


# ---- self-contained 1-second window loader ------------------------------------------------------
# Deliberately duplicated from the research branch's extended_data loader so this branch stands
# alone (isolation condition, #127). Same trick: ISO-8601 sorts lexicographically, so we binary-
# seek the raw bytes and parse only the rows we keep. The 1 MB rewind guards the boundary case
# where the search lands one line late (landing EARLY is free — the window mask discards it).
_SEEK_SAFETY = 1 << 20


def _seek_to(path: Path, target: str) -> int:
    size = path.stat().st_size
    with path.open("rb") as f:
        f.readline()
        lo, hi = f.tell(), size
        while lo < hi:
            mid = (lo + hi) // 2
            f.seek(mid)
            f.readline()
            pos = f.tell()
            line = f.readline()
            if not line:
                hi = mid
                continue
            ts = line.split(b",", 1)[0].decode()
            if ts < target:
                lo = pos + len(line)
            else:
                hi = mid
        f.seek(max(0, lo - _SEEK_SAFETY))
        if lo > _SEEK_SAFETY:
            f.readline()
        return f.tell()


def load_1s_windows(path: Path, windows, chunksize: int = 4_000_000,
                    keep_volume: bool = False) -> pd.DataFrame:
    w = sorted((pd.Timestamp(s), pd.Timestamp(e)) for s, e in windows)
    if not w:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close"])
    s_str = np.array([s.strftime("%Y-%m-%d %H:%M:%S") for s, _ in w])
    e_str = np.array([e.strftime("%Y-%m-%d %H:%M:%S") for _, e in w])
    lo, hi = min(s_str), max(e_str)
    keep = []
    fh = path.open("r")
    fh.seek(_seek_to(path, lo))
    if fh.tell() == 0:
        fh.readline()                                  # skip the header if we start at byte 0
    reader = pd.read_csv(fh, chunksize=chunksize, dtype={"datetime": str}, header=None,
                         names=["datetime", "open", "high", "low", "close", "volume"])
    for ch in reader:
        t = ch["datetime"].to_numpy()
        if t[-1] < lo:
            continue
        if t[0] > hi:
            break
        a = np.searchsorted(t, s_str, side="left")
        b = np.searchsorted(t, e_str, side="right")
        mask = np.zeros(len(t), dtype=bool)
        for x, y in zip(a, b):
            if y > x:
                mask[x:y] = True
        if mask.any():
            keep.append(ch[mask])
    fh.close()
    cols = ["Date", "Open", "High", "Low", "Close"] + (["Volume"] if keep_volume else [])
    if not keep:
        return pd.DataFrame(columns=cols)
    d = pd.concat(keep, ignore_index=True)
    d["Date"] = pd.to_datetime(d["datetime"])
    d = d.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close",
                          "volume": "Volume"})
    return d[cols].drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)


# ---- the bracket, exactly as M3 coded it --------------------------------------------------------
def run_bracket(idx, op, hi, lo, cl, t_rel: pd.Timestamp, leg: Leg, pv: float,
                title: str, entry_price: float | None = None,
                walk_from: int | None = None) -> Fill | None:
    """One leg through one release. Semantics IDENTICAL to p3_straddle.leg_pnl — that identity is
    the V1 parity claim, enforced by replay against the committed evidence, not assumed.

    D4 (#132) generalization, both kwargs default to the ORIGINAL behavior so every existing call
    is byte-identical (the bridge test enforces this):
      entry_price  override the fill price (e.g. the worked-entry VWAP); default = close of the
                   bar at release−LEAD_S.
      walk_from    first bar index the bracket is ACTIVE from; default = the bar after the entry
                   bar. The worked entry activates at release−5s (unprotected while building —
                   an explicit model property, reported, never netted away).
    """
    t0 = np.datetime64(t_rel)
    i_ent = int(np.searchsorted(idx, t0 - np.timedelta64(LEAD_S, "s"), side="right")) - 1
    i_rel = int(np.searchsorted(idx, t0, side="left"))
    i_end = int(np.searchsorted(idx, t0 + np.timedelta64(EXIT_S, "s"), side="right")) - 1
    if i_ent < 0 or i_end <= i_ent or i_rel <= i_ent or i_end >= len(idx):
        return None
    if abs((pd.Timestamp(idx[i_ent]) - (t_rel - pd.Timedelta(seconds=LEAD_S)))
           .total_seconds()) > ENTRY_TOL_S:
        return None
    entry = float(cl[i_ent]) if entry_price is None else float(entry_price)
    if not np.isfinite(entry) or entry <= 0:
        return None
    d_stop = entry * STOP_PCT / 100.0
    d_tp = entry * TP_PCT / 100.0
    long_ = leg.direction == "long"
    stop_lvl = entry - d_stop if long_ else entry + d_stop
    tp_lvl = entry + d_tp if long_ else entry - d_tp

    out_p, outcome, b_exit = None, "timed", i_end
    b_start = (i_ent + 1) if walk_from is None else max(int(walk_from), i_ent + 1)
    for b in range(b_start, i_end + 1):
        hit_sl = lo[b] <= stop_lvl if long_ else hi[b] >= stop_lvl
        hit_tp = hi[b] >= tp_lvl if long_ else lo[b] <= tp_lvl
        if hit_sl:                                     # tie (both in one bar) ⇒ STOP, pessimistic
            out_p = min(op[b], stop_lvl) if long_ else max(op[b], stop_lvl)
            outcome = "stopped_pre" if b < i_rel else "stopped_post"
            b_exit = b
            break
        if hit_tp:
            out_p = max(op[b], tp_lvl) if long_ else min(op[b], tp_lvl)
            outcome, b_exit = "tp", b
            break
    if out_p is None:
        out_p = float(cl[i_end])
    pnl_pts = (out_p - entry) if long_ else (entry - out_p)
    return Fill(et=str(t_rel), title=title, direction=leg.direction, qty=leg.qty,
                entry=entry, exit_price=float(out_p), outcome=outcome,
                exit_s_from_release=float((idx[b_exit] - t0) / np.timedelta64(1, "s")),
                pnl_points=float(pnl_pts), pnl_usd=float(pnl_pts * pv * leg.qty))


# ---- replay -------------------------------------------------------------------------------------
def replay(instrument: str, bars_1s: Path, schedule_path: Path, qty: int,
           out_dir: Path, floor_year: int = 2016,
           series: list[str] | None = None) -> pd.DataFrame:
    sched = load_schedule(schedule_path)
    # per-instrument study floor (#121/#122): RTY's price history starts 2019 — its M3 evidence
    # was produced with floor 2019, so parity requires the same cut.
    ev = sched[(sched.status == "confirmed")
               & (sched.et.dt.year >= floor_year)].reset_index(drop=True)
    # WS-ESCPI (#139): an instrument may ride a SUBSET of the schedule (ES rides CPI only —
    # the premium is CPI-concentrated and only the CPI slice passed its battery there).
    # Default None = the full schedule, so NQ/RTY behaviour is byte-identical.
    if series is not None:
        ev = ev[ev.title.isin(series)].reset_index(drop=True)
    print(f"replay {instrument}: {len(ev)} confirmed releases "
          f"({ev.et.min()} .. {ev.et.max()}), qty={qty}, spec: lead {LEAD_S}s, "
          f"S {STOP_PCT}%, TP {TP_PCT}%, exit +{EXIT_S}s")
    windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
               for t in ev.et]
    bars = load_1s_windows(bars_1s, windows)
    print(f"  1s bars loaded: {len(bars):,}")
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    fills = []
    for _, r in ev.iterrows():
        f = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", qty),
                        PV[instrument], r.title)
        if f is not None:
            fills.append(f)
    d = pd.DataFrame([f.__dict__ for f in fills]).drop(columns=["meta"])
    d["net_stressed_usd"] = d.pnl_usd - COST_PER_LEG[instrument]["stressed"] * qty
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"replay_{instrument}_q{qty}.csv"
    d.to_csv(dest, index=False)
    g = d.pnl_usd
    cost = COST_PER_LEG[instrument]["stressed"] * qty
    print(f"  events {len(d)} · gross mean ${g.mean():+.2f}/event · "
          f"net(stressed) ${g.mean() - cost:+.2f} · wrote {dest}")
    return d


def parity_check(replayed: pd.DataFrame, ref_csv: Path) -> bool:
    """V1 — the replay (qty=1) must reproduce the committed M3 evidence.

    Scoring (refined after the RTY diagnosis, #128):
      · a reference event MISSING from the replay, or any P&L/outcome mismatch  ⇒ FAIL
      · a replay event ABSENT from the reference                                ⇒ reported, listed
    ⚠️ Why extras are reported rather than failed: the original study's same-minute dedupe used
    pandas' non-stable default sort, and its tie-break came out DIFFERENTLY per instrument-floor —
    2026-03-06 08:30 (a rare NFP + Retail Sales shared minute) is in the NQ evidence (it is NQ's
    worst event) but was tie-broken OUT of the RTY selection. The schedule replicates the NQ-floor
    selection verbatim, so RTY replay covers that minute while RTY's reference lacks it. The cause
    is an input-selection instability in the STUDY, pinned by diffing its own load_tv_events output
    — not an executor defect. Missing or mismatched evidence remains a hard FAIL.
    """
    ref = pd.read_csv(ref_csv)
    ref = ref[(ref["set"] == "RELEASES") & (ref.stop == STOP_PCT) & (ref.tp == TP_PCT)]
    ref = ref[["et", "long_usd", "long_outcome"]].copy()
    ref["et"] = pd.to_datetime(ref.et)
    mine = replayed[["et", "pnl_usd", "outcome"]].copy()
    mine["et"] = pd.to_datetime(mine.et)
    j = ref.merge(mine, on="et", how="outer", indicator=True)
    missing = j[j._merge == "left_only"]
    extra = j[j._merge == "right_only"]
    both = j[j._merge == "both"]
    bad_pnl = int((np.abs(both.long_usd - both.pnl_usd) > 1e-9).sum())
    bad_out = int((both.long_outcome != both.outcome).sum())
    ok = len(missing) == 0 and bad_pnl == 0 and bad_out == 0
    print(f"V1 PARITY vs {ref_csv.name}: matched {len(both)} events · "
          f"missing-from-replay {len(missing)} · pnl mismatches {bad_pnl} · "
          f"outcome mismatches {bad_out} · replay-extras {len(extra)} "
          f"-> {'PASS — the executor IS the verified study' if ok else 'FAIL'}")
    for _, r in extra.iterrows():
        print(f"    extra (study tie-break drop, see docstring): {r.et}")
    return ok


# ---- paper mode ---------------------------------------------------------------------------------
def paper(instrument: str, schedule_path: Path, now: pd.Timestamp, qty: int,
          out_dir: Path, horizon_days: int = 40) -> list[dict]:
    """Emit order INTENTS for upcoming scheduled releases. No broker, no side effects — every
    intent is a JSONL row a human (or a future gateway) consumes. Stop/TP are expressed as
    percentages because the entry PRICE is unknowable until the entry second."""
    sched = load_schedule(schedule_path)
    upcoming = sched[(sched.et > now) & (sched.et <= now + pd.Timedelta(days=horizon_days))]
    intents = []
    for _, r in upcoming.iterrows():
        t_entry = r.et - pd.Timedelta(seconds=LEAD_S)
        intents.append({
            "intent": "BRACKET", "instrument": instrument, "qty": qty, "direction": "long",
            "series": r.title, "release_et": str(r.et), "enter_at_et": str(t_entry),
            "entry_type": "market-on-1s-close", "stop_pct": STOP_PCT, "tp_pct": TP_PCT,
            "tie_rule": "both-in-one-bar => STOP", "timed_exit_et": str(r.et + pd.Timedelta(seconds=EXIT_S)),
            "status": r.status,
            "risk_notes": "win 36.4%; median event loses; worst measured loss 2.1x the stop; "
                          "regime monitor MUST be GO before honouring this intent"})
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"paper_intents_{instrument}.jsonl"
    with dest.open("w") as f:
        for i in intents:
            f.write(json.dumps(i) + "\n")
    print(f"paper: {len(intents)} intents within {horizon_days} days of {now} -> {dest}")
    return intents


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    rp = sub.add_parser("replay")
    rp.add_argument("--instrument", required=True, choices=list(PV))
    rp.add_argument("--bars-1s", required=True)
    rp.add_argument("--schedule", default=str(DEFAULT_SCHEDULE))
    rp.add_argument("--qty", type=int, default=1)
    rp.add_argument("--floor-year", type=int, default=2016)
    rp.add_argument("--series", default="",
                    help="comma-separated schedule titles this instrument rides "
                         "(empty = all; ES deploys with 'Inflation Rate MoM' only, #139)")
    rp.add_argument("--parity-ref", default="")
    rp.add_argument("--out-dir", default="deploy_out")
    pp = sub.add_parser("paper")
    pp.add_argument("--instrument", required=True, choices=list(PV))
    pp.add_argument("--schedule", default=str(DEFAULT_SCHEDULE))
    pp.add_argument("--now", required=True)
    pp.add_argument("--qty", type=int, default=1)
    pp.add_argument("--out-dir", default="deploy_out")
    a = ap.parse_args()

    if a.mode == "replay":
        d = replay(a.instrument, Path(a.bars_1s), Path(a.schedule), a.qty, Path(a.out_dir),
                   a.floor_year,
                   series=[s.strip() for s in a.series.split(",") if s.strip()] or None)
        if a.parity_ref:
            return 0 if parity_check(d, Path(a.parity_ref)) else 1
        return 0
    paper(a.instrument, Path(a.schedule), pd.Timestamp(a.now), a.qty, Path(a.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
