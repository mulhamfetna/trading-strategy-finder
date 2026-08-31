"""LIVE-PROTOCOL Amendment 1 — the frozen-replay track record (#213). Server-side, per box drop.

    python3 optimize/live/replay_window.py --out <dir>            # after the drop passed fwd_merge_boxes

Sequence (per docs/LIVE-PROTOCOL.md §7/A1): the owner's drop has ALREADY passed the gate-E merge with the
repaint audit; this script then (1) verifies the allowlist hash against the signed protocol §9, (2) replays
the 9 allowlist slots with the FROZEN champion set through the same causal path as every book, (3) cuts the
new window = entries on days strictly after the previous frontier DATE (the frontier day itself belongs
to the prior record) recorded in live_record_state.json, (4) writes
books + a summary with raw/$10/$25 views, and (5) advances the frontier. Everything it writes is committed;
each drop becomes a LIVE-WINDOW-<date> ledger claim. One contract; engine fills; paper/replay labelled.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

AL = PI / "optimize" / "live" / "live_allowlist.json"
STATE = PI / "optimize" / "live" / "live_record_state.json"
PROTO = PI.parents[1] / "docs" / "LIVE-PROTOCOL.md"
COST = 25.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default=date.today().isoformat())
    a = ap.parse_args()
    out = Path(a.out).expanduser() / a.label
    out.mkdir(parents=True, exist_ok=True)

    # 1) the universe the owner signed, byte-for-byte
    alh = hashlib.sha256(AL.read_bytes()).hexdigest()[:16]
    m = re.search(r"Allowlist sha256\[:16\]: \*\*([0-9a-f]{16})\*\*", PROTO.read_text())
    if not m or m.group(1) != alh:
        raise SystemExit(f"ALLOWLIST HASH MISMATCH: protocol §9 {m.group(1) if m else None} vs file {alh} — "
                         "the signed universe changed without an amendment; refusing to run")
    slots = json.load(open(AL))["allowed"]
    state = json.load(open(STATE))
    prev_frontier = state["frontier"]

    from optimize.l2 import payload as P
    rows = []
    for slot in slots:
        tok, tf = slot.split("_")
        champs = json.loads(P._instrument_champions_path(tok, "best").read_text())
        l1p = P._champion_layer_params(tf, champs[tf])
        view = P.build_view_payload(l1p, P._scaled_permissive(tok), tf, "l1", instrument=tok)
        tr = pd.DataFrame(view["trades"])
        if len(tr):
            tr["et"] = pd.to_datetime(pd.to_numeric(tr["entry_time"]), unit="s")
            w = tr[tr["et"].dt.normalize() > pd.Timestamp(prev_frontier[tok])]   # frontier DAY inclusive to the prior record
        else:
            w = tr
        with open(out / f"lw_book_{slot}.csv", "w", newline="") as f:
            cw = csv.DictWriter(f, fieldnames=["layer", "entry_time", "exit_time", "direction",
                                               "entry_price", "exit_price", "exit_reason", "pnl"],
                                extrasaction="ignore")
            cw.writeheader()
            for t in (w.drop(columns=["et"]).to_dict("records") if len(w) else []):
                cw.writerow(t)
        pnl = float(w["pnl"].sum()) if len(w) else 0.0
        rows.append({"slot": slot, "n": int(len(w)), "raw": round(pnl, 2),
                     "net10": round(pnl - 10.0 * len(w), 2), "net25": round(pnl - COST * len(w), 2),
                     "window_start": prev_frontier[tok],
                     "last_entry": str(w["et"].max()) if len(w) else None})
        print(f"{slot}: n={len(w)} raw={pnl:,.2f} net25={pnl - COST*len(w):,.2f}", flush=True)

    # 3) advance the frontier to each instrument's current box end (the engine's decision frame end)
    from optimize import data as D
    new_frontier = dict(prev_frontier)
    for tok in sorted({s.split("_")[0] for s in slots}):
        df_dec, _, box, _, _ = D.load_inputs("4h", instrument=tok)
        new_frontier[tok] = str(pd.to_datetime(box["Date"]).max().date())
    summary = {"label": a.label, "mode": "paper/frozen-replay (LIVE-PROTOCOL A1)",
               "allowlist_sha16": alh, "prev_frontier": prev_frontier, "new_frontier": new_frontier,
               "cost_rt": COST, "slots": rows,
               "fleet": {"n": sum(r["n"] for r in rows), "raw": round(sum(r["raw"] for r in rows), 2),
                          "net10": round(sum(r["net10"] for r in rows), 2),
                          "net25": round(sum(r["net25"] for r in rows), 2)}}
    (out / "live_window_summary.json").write_text(json.dumps(summary, indent=1))
    state["frontier"] = new_frontier
    state["windows"] = state.get("windows", []) + [{"label": a.label, "fleet": summary["fleet"]}]
    STATE.write_text(json.dumps(state, indent=1))
    print(json.dumps(summary["fleet"]), "->", out / "live_window_summary.json", flush=True)


if __name__ == "__main__":
    main()
