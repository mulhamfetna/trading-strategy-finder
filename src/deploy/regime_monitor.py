"""WS-DEPLOY D2 (#129) — the regime monitor: the operating condition before any live deployment.

WHY THIS EXISTS (from the evidence, not caution theatre): the premium funding the confirmed trade
is era-concentrated — NQ winning-cell per event: 2016–19 +$59 · 2020–21 +$24 · 2022+ +$292 — and
the sample cannot distinguish a permanent premium from an inflation-era regime. So the alarm is
built BEFORE going live.

THE RULE (pinned in the owner decision packet):
    state = STAND_DOWN  if  rolling mean of the LAST 24 CPI-event trade P&Ls  <  $0
    STAND_DOWN is STICKY: the monitor never un-halts itself. Clearing requires an explicit
    `--clear` (an owner action) — halting is automatic, restarting is a decision.
    Operating procedure also includes the ANNUAL claims-ledger re-run (optimize/verify/run.py on
    the research branch): if it is not green, published numbers have drifted from their files.

Input: a per-event P&L file (the executor's replay output or its live causal log) with columns
    et, title, and net_stressed_usd (preferred) or pnl_usd — only CPI rows enter the window.
⚠️ D3 (#127, owner-approved): the monitor consumes NET-STRESSED P&L, not gross — the alarm must
    fire on the number the trade actually keeps. Falls back to gross ONLY with a loud warning.

    python3 -m src.deploy.regime_monitor --events deploy_out/replay_NQ_q1.csv
    python3 -m src.deploy.regime_monitor --events ... --history      # full historical state walk
    python3 -m src.deploy.regime_monitor --clear --state-file ...    # OWNER action only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

WINDOW = 24                       # 24 CPI events = two years of CPI, the power-model horizon
CPI_TITLE = "Inflation Rate MoM"
DEFAULT_STATE = Path("deploy_out/regime_state.json")


def rolling_state(events: pd.DataFrame) -> pd.DataFrame:
    """Per CPI event: the trailing-24 mean INCLUDING that event, and the resulting state."""
    cpi = (events[events.title == CPI_TITLE]
           .assign(et=lambda d: pd.to_datetime(d.et))
           .sort_values("et").reset_index(drop=True))
    if len(cpi) == 0:
        raise ValueError("no CPI events in the input — the monitor has nothing to watch")
    if "net_stressed_usd" in cpi.columns:
        pnl = cpi.net_stressed_usd
    else:
        import sys
        print("WARNING: net_stressed_usd column absent — monitor falling back to GROSS pnl_usd "
              "(less conservative than the deployed stressed-cost policy)", file=sys.stderr)
        pnl = cpi.pnl_usd
    cpi["pnl_used"] = pnl
    cpi["roll24"] = pnl.rolling(WINDOW, min_periods=WINDOW).mean()
    cpi["state"] = "WARMUP"
    cpi.loc[cpi.roll24.notna() & (cpi.roll24 >= 0), "state"] = "GO"
    cpi.loc[cpi.roll24.notna() & (cpi.roll24 < 0), "state"] = "STAND_DOWN"
    return cpi[["et", "pnl_used", "roll24", "state"]]


def current_state(events: pd.DataFrame, state_file: Path) -> dict:
    """The operational answer: GO or STAND_DOWN right now — with stickiness applied."""
    walk = rolling_state(events)
    latest = walk.iloc[-1]
    sticky = {"halted": False, "halted_at": None}
    if state_file.exists():
        sticky = json.loads(state_file.read_text())
    if latest.state == "STAND_DOWN" and not sticky["halted"]:
        sticky = {"halted": True, "halted_at": str(latest.et)}
    out = {"state": "STAND_DOWN" if sticky["halted"] else str(latest.state),
           "roll24": float(latest.roll24) if pd.notna(latest.roll24) else None,
           "as_of": str(latest.et), "sticky": sticky,
           "rule": f"rolling mean of last {WINDOW} CPI-event P&Ls < $0 => STAND_DOWN (sticky; "
                   f"clearing is an OWNER action)"}
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(sticky, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", help="per-event P&L csv (replay output or live log)")
    ap.add_argument("--state-file", default=str(DEFAULT_STATE))
    ap.add_argument("--history", action="store_true", help="print the full historical state walk")
    ap.add_argument("--clear", action="store_true",
                    help="OWNER ACTION: clear a sticky STAND_DOWN")
    a = ap.parse_args()

    sf = Path(a.state_file)
    if a.clear:
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps({"halted": False, "halted_at": None}, indent=1))
        print("sticky STAND_DOWN cleared — recorded as an owner action")
        return 0
    if not a.events:
        ap.error("--events is required unless --clear")
    ev = pd.read_csv(a.events)
    if a.history:
        walk = rolling_state(ev)
        flips = walk[walk.state.ne(walk.state.shift())]
        print(f"CPI events {len(walk)} · window {WINDOW}")
        for _, r in flips.iterrows():
            r24 = f"{r.roll24:+.2f}" if pd.notna(r.roll24) else "n/a"
            print(f"  {str(r.et)[:10]}  -> {r.state:<10} (roll24 {r24})")
        share = (walk.state == "STAND_DOWN").mean()
        print(f"  time in STAND_DOWN: {share:.1%} of evaluable CPI events")
        return 0
    print(json.dumps(current_state(ev, sf), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
