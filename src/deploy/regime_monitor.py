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


def compound_context(cpi_ets: pd.Series) -> pd.DataFrame:
    """X-5b (docs/X5B-PREREGISTRATION.md): the compound-power CONTEXT per CPI event —
    pred_exp + the MAX top-12 earnings pred within ±24h (X-5's exact definition; X-3's
    law-#1 additive composition). INFORMATION ONLY — nothing here may ever gate."""
    import numpy as np
    repo = Path(__file__).resolve().parents[2]
    pi = repo / "subprojects" / "Parametric-Indicators" / "optimize"
    d = pd.read_csv(pi / "fundamentals" / "fu9_event_state_NQ.csv", parse_dates=["et"],
                    usecols=["et", "title", "pred_exp"])
    d = d[d.title == CPI_TITLE]
    earn = pd.read_csv(pi / "earnings" / "data" / "ep1_events_NQ.csv",
                       parse_dates=["event_et"])
    e_et = earn.event_et.to_numpy()
    e_p = earn.pred.to_numpy(float)
    rows = []
    hist = []
    for t in pd.to_datetime(cpi_ets):
        base = d.loc[d.et == t, "pred_exp"]
        base = float(base.iloc[0]) if len(base) and np.isfinite(base.iloc[0]) else None
        comp = None
        if base is not None:
            dh = np.abs((t.to_datetime64() - e_et) / np.timedelta64(1, "h"))
            near = e_p[(dh <= 24.0) & np.isfinite(e_p)]
            comp = round(base + (float(near.max()) if len(near) else 0.0), 4)
        note = None
        if comp is not None:
            prior = [x for x in hist if x is not None]
            if len(prior) >= 8:
                note = "high" if comp > float(np.median(prior)) else "low"
            hist.append(comp)
        rows.append({"compound_power_pct": comp, "power_regime_note": note})
    return pd.DataFrame(rows, index=range(len(rows)))


def current_state(events: pd.DataFrame, state_file: Path, context: bool = False) -> dict:
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
    if context:
        ctx = compound_context(walk.et).iloc[-1]
        out["context"] = {"compound_power_pct": ctx.compound_power_pct,
                          "power_regime_note": ctx.power_regime_note,
                          "authority": "information only — never gates (X-5b)"}
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
    ap.add_argument("--context", action="store_true",
                    help="X-5b: add the compound-power CONTEXT field (information only)")
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
        if a.context:
            walk = pd.concat([walk, compound_context(walk.et)], axis=1)
        flips = walk[walk.state.ne(walk.state.shift())]
        print(f"CPI events {len(walk)} · window {WINDOW}")
        for _, r in flips.iterrows():
            r24 = f"{r.roll24:+.2f}" if pd.notna(r.roll24) else "n/a"
            cx = ""
            if a.context and "compound_power_pct" in walk.columns and \
                    pd.notna(r.get("compound_power_pct")):
                cx = f" · compound {r.compound_power_pct:.3f}% ({r.power_regime_note})"
            print(f"  {str(r.et)[:10]}  -> {r.state:<10} (roll24 {r24}){cx}")
        share = (walk.state == "STAND_DOWN").mean()
        print(f"  time in STAND_DOWN: {share:.1%} of evaluable CPI events")
        return 0
    print(json.dumps(current_state(ev, sf, context=a.context), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
