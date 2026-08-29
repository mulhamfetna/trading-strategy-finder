"""WS-FWD Phase 2 (#176) — the fresh-window cut + per-slot diagnostics.

Consumes the Phase-1 books (fwd_book_<TOK>_<TF>.csv) and produces, per slot:
  - full-book metrics (net, max DD on exit-ordered equity, win rate, exit-reason mix, monthly),
  - the FRESH cut: trades ENTERING after the pre-extension engine end (frozen in the
    pre-registration; the tape the deployed champion had never seen),
  - the RESOLUTION class: trades that were OPEN at the old data end and now resolve on real tape,
  - drift vs the extraction-time record in the champion file (full_pnl/full_dd as extracted).

Descriptive only — verdict language stays in the report under the pre-registered rules
(fresh cells with n<10 are reported, not judged).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# Pre-extension engine ends (phase-0 audit, frozen in docs/WS-FWD-PREREGISTRATION.md)
PRE_END = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00",
           "GC": "2026-07-02 19:59:00", "SI": "2026-07-02 19:59:00",
           "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
           "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00",
           "YM": "2026-07-05 19:59:00"}
TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def _metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0, "pnl": 0.0}
    d = df.sort_values("exit_time")
    eq = d["pnl"].cumsum()
    dd = (eq.cummax() - eq).max()
    wins = int((d["pnl"] > 0).sum())
    return {"n": len(d), "pnl": round(float(d["pnl"].sum()), 2),
            "max_dd": round(float(dd), 2), "wins": wins,
            "win_rate": round(wins / len(d), 4),
            "avg_win": round(float(d.loc[d["pnl"] > 0, "pnl"].mean()), 2) if wins else None,
            "avg_loss": round(float(d.loc[d["pnl"] <= 0, "pnl"].mean()), 2) if wins < len(d) else None,
            "worst": round(float(d["pnl"].min()), 2), "best": round(float(d["pnl"].max()), 2),
            "exit_reasons": d["exit_reason"].value_counts().to_dict()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True, help="dir holding fwd_book_*.csv")
    ap.add_argument("--champions", default="optimize/results", help="dir with best_champions_full*.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    books = Path(args.books)
    champ_dir = Path(args.champions)

    out: dict = {}
    for tok, pre in PRE_END.items():
        suf = "" if tok == "NQ" else f"_{tok}"
        cfile = champ_dir / f"best_champions_full{suf}.json"
        champs = json.loads(cfile.read_text()) if cfile.exists() else {}
        pre_ts = pd.Timestamp(pre)
        for tf in TFS:
            key = f"{tok}_{tf}"
            b = books / f"fwd_book_{tok}_{tf}.csv"
            if not b.exists():
                out[key] = {"status": "no_book"}
                continue
            df = pd.read_csv(b)
            # the causal log serializes times as epoch seconds of the ET-naive wall time
            for c in ("entry_time", "exit_time"):
                df[c] = pd.to_datetime(pd.to_numeric(df[c]), unit="s")
            full = _metrics(df)
            fresh = _metrics(df[df["entry_time"] > pre_ts])
            resolution = _metrics(df[(df["entry_time"] <= pre_ts) & (df["exit_time"] > pre_ts)])
            rec = champs.get(tf, {})
            monthly = (df.assign(m=df["exit_time"].dt.strftime("%Y-%m"))
                         .groupby("m")["pnl"].sum().round(2).to_dict())
            out[key] = {"status": "ok", "full": full, "fresh": fresh, "resolution": resolution,
                        "extraction_record": {"full_pnl": rec.get("full_pnl"),
                                              "full_dd": rec.get("full_dd"), "win": rec.get("win")},
                        "monthly": monthly,
                        "fresh_window_start": pre}
    Path(args.out).write_text(json.dumps(out, indent=1))
    ok = [k for k, v in out.items() if v.get("status") == "ok"]
    fresh_n = sum(out[k]["fresh"]["n"] for k in ok)
    fresh_pnl = round(sum(out[k]["fresh"]["pnl"] for k in ok), 2)
    res_n = sum(out[k]["resolution"]["n"] for k in ok)
    print(f"slots ok={len(ok)}  fresh trades={fresh_n} (${fresh_pnl:,})  resolution trades={res_n}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
