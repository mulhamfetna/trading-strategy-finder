"""WS-FWD Phase 1 (#176) — run every deployed champion (`best` set) on the extended tape.

For each instrument x decision-TF slot: load the champion EXACTLY as the dashboard serves it
(optimize.l2.payload._champion_layer_params — 1-min indicator frame forced), run the causal
L1 view through the SAME code path the dashboard's /api/causal_backtest uses
(build_view_payload(l1, {}, tf, "l1")), and write the full per-trade book + a summary.

A slot with no champion in the set is recorded as "no_champion" and NOT silently run on the
scaled-permissive fallback (the owner asked for the champions' performance, not the default's).

Isolation: run with TMPDIR pointed INSIDE the extended root so the params-keyed L1 disk cache
(/tmp/wsh_l1_cache) is never shared with the production dashboard — the cache key does not see
the data root, so sharing it would serve old-tape books for new-tape requests (or vice versa).

Usage (server):
  env WSH_DATA_BASE=.../FWD_EXTENDED WSG_DATA_ROOT=.../FWD_EXTENDED/data TMPDIR=.../FWD_EXTENDED/tmp \
      python3 optimize/fwd/fwd_run_champions.py --out .../fwd_books [--jobs 8]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

TFS = ("4h", "2h", "1h", "15m", "5m", "2m")
TOKENS = ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")
SET = "best"
# Optional: a directory of <prefix>_champions_full[_TOK].json files to run INSTEAD of a registered set
# (WS-LIVE-PARITY #182 runs the wsh4 set the live trader actually carries). Set via --champ-dir.
CHAMP_DIR = os.environ.get("WSH_FWD_CHAMP_DIR", "")
CHAMP_PREFIX = os.environ.get("WSH_FWD_CHAMP_PREFIX", "wsh4")


def run_slot(job: tuple[str, str, str]) -> dict:
    tok, tf, outdir = job
    from optimize.l2 import payload as P
    out = {"instrument": tok, "tf": tf, "set": SET if not CHAMP_DIR else f"{CHAMP_PREFIX}@{CHAMP_DIR}"}
    try:
        if CHAMP_DIR:
            suf = "" if tok == "NQ" else f"_{tok}"
            cf = Path(CHAMP_DIR) / f"{CHAMP_PREFIX}_champions_full{suf}.json"
        else:
            cf = P._instrument_champions_path(tok, SET)
        if not cf.exists():
            out["status"] = "no_champion_file"
            return out
        champs = json.loads(cf.read_text())
        if tf not in champs:
            out["status"] = "no_champion"
            return out
        l1p = P._champion_layer_params(tf, champs[tf])
        # the l1 view validates the L2 dict too; the L1 book is independent of it (L2 only manages
        # L1's dropped signals) — use the deterministic scaled-permissive default, never {}.
        l2p = P._scaled_permissive(tok)
        view = P.build_view_payload(l1p, l2p, tf, "l1", instrument=tok)
        trades = view["trades"]
        pnl = sum(t["pnl"] for t in trades)
        eq = peak = dd = 0.0
        wins = 0
        for t in sorted(trades, key=lambda r: r["exit_time"]):
            eq += t["pnl"]
            peak = max(peak, eq)
            dd = max(dd, peak - eq)
            wins += t["pnl"] > 0
        monthly: dict[str, float] = {}
        for t in trades:
            m = str(t["exit_time"])[:7]
            monthly[m] = round(monthly.get(m, 0.0) + t["pnl"], 2)
        out.update(status="ok", n_trades=len(trades), pnl=round(pnl, 2), max_dd=round(dd, 2),
                   wins=wins, win_rate=round(wins / len(trades), 4) if trades else None,
                   first_entry=str(trades[0]["entry_time"]) if trades else None,
                   last_entry=str(trades[-1]["entry_time"]) if trades else None,
                   last_exit=max((str(t["exit_time"]) for t in trades), default=None),
                   monthly=dict(sorted(monthly.items())),
                   params_hash=hash(json.dumps(l1p, sort_keys=True, default=str)) & 0xFFFFFFFF)
        book = Path(outdir) / f"fwd_book_{tok}_{tf}.csv"
        cols = ["layer", "entry_time", "exit_time", "direction", "entry_price", "exit_price",
                "exit_reason", "pnl"]
        with open(book, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for t in sorted(trades, key=lambda r: r["entry_time"]):
                w.writerow(t)
        out["book"] = str(book)
    except Exception as e:  # noqa: BLE001 — a slot failure must not kill the sweep
        out["status"] = f"ERROR: {type(e).__name__}: {e}"
        out["trace"] = traceback.format_exc()[-2000:]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--tokens", default=",".join(TOKENS))
    ap.add_argument("--tfs", default=",".join(TFS))
    ap.add_argument("--champ-dir", default="", help="run the champion files in this dir (prefix --champ-prefix) instead of the registered set")
    ap.add_argument("--champ-prefix", default="wsh4")
    args = ap.parse_args()
    if args.champ_dir:                      # env so spawned workers see the same override
        os.environ["WSH_FWD_CHAMP_DIR"] = str(Path(args.champ_dir).resolve())
        os.environ["WSH_FWD_CHAMP_PREFIX"] = args.champ_prefix
        global CHAMP_DIR, CHAMP_PREFIX
        CHAMP_DIR, CHAMP_PREFIX = os.environ["WSH_FWD_CHAMP_DIR"], args.champ_prefix
    outdir = Path(args.out).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(tok, tf, str(outdir)) for tok in args.tokens.split(",") for tf in args.tfs.split(",")]

    print(f"# WS-FWD phase 1 — {len(jobs)} slots, set={SET if not CHAMP_DIR else CHAMP_PREFIX + '@' + CHAMP_DIR}, jobs={args.jobs}, "
          f"WSH_DATA_BASE={os.environ.get('WSH_DATA_BASE')!r} TMPDIR={os.environ.get('TMPDIR')!r}", flush=True)
    results = []
    if args.jobs > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(args.jobs) as pool:
            for r in pool.imap_unordered(run_slot, jobs):
                results.append(r)
                print(f"[{r['instrument']} {r['tf']}] {r.get('status')} pnl={r.get('pnl')} "
                      f"n={r.get('n_trades')} dd={r.get('max_dd')} last_exit={r.get('last_exit')}", flush=True)
    else:
        for j in jobs:
            r = run_slot(j)
            results.append(r)
            print(f"[{r['instrument']} {r['tf']}] {r.get('status')} pnl={r.get('pnl')} "
                  f"n={r.get('n_trades')} dd={r.get('max_dd')} last_exit={r.get('last_exit')}", flush=True)

    (outdir / "fwd_run_summary.json").write_text(json.dumps(results, indent=1))
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\nDONE ok={ok}/{len(jobs)} -> {outdir/'fwd_run_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
