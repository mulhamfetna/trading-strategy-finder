"""Phase 0 — the REGRESSION GATE: re-run the engine and assert byte-equality vs the frozen golden
baselines (task #210). Run after EVERY optimization step; any mismatch fails loudly (non-zero exit).

Compares, per champion timeframe:
  * every summary metric (P/L, DD, n_taken, win, pf, ...) — exact;
  * the taken-trade ledger — SHA-256 must match;
  * every enabled indicator's per-decision-bar vote array — SHA-256 must match.

Run:  python3 perf/check_golden.py [tf ...]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from _common import TFS, load_bundle, compute_votes_named   # noqa: E402

_HERE = Path(__file__).resolve().parent
_GOLD = _HERE / "golden"
sys.path.insert(0, str(_HERE.parent))
import strategy  # noqa: E402
from capture_golden import _sha, _trades_frame  # noqa: E402


def check(tf: str) -> list[str]:
    gold_path = _GOLD / f"{tf}.json"
    if not gold_path.exists():
        return [f"[{tf}] NO GOLDEN BASELINE (run capture_golden.py first)"]
    gold = json.loads(gold_path.read_text())
    fails = []

    df_dec, df1, box, vf, n2025, preset = load_bundle(tf)
    payload = strategy.build_payload(df_dec, df1, box, vf, n2025, preset)
    s = payload["meta"]["summary"]

    for k, gv in gold["summary"].items():
        nv = s.get(k)
        if nv != gv:
            fails.append(f"[{tf}] summary.{k}: golden={gv} now={nv}")

    th = _sha(_trades_frame(payload["trades"]).to_csv(index=False).encode())
    if th != gold["trades_sha256"]:
        fails.append(f"[{tf}] trades hash differs (golden {gold['trades_sha256'][:8]} now {th[:8]})")

    votes = compute_votes_named(tf, df_dec, df1, box, preset)
    now_hashes = {k: _sha(np.ascontiguousarray(v).tobytes()) for k, v in votes.items()}
    for k, gh in gold["vote_sha256"].items():
        nh = now_hashes.get(k)
        if nh != gh:
            fails.append(f"[{tf}] vote[{k}] hash differs (golden {gh[:8]} now {nh and nh[:8]})")
    extra = set(now_hashes) - set(gold["vote_sha256"])
    if extra:
        fails.append(f"[{tf}] unexpected new indicators: {sorted(extra)}")

    if not fails:
        print(f"  [{tf}] ✅ MATCH  (P/L ${s['pnl']:,.0f}, n={s['n_taken']}, {len(votes)} indicators)",
              flush=True)
    return fails


def main() -> int:
    tfs = sys.argv[1:] or TFS
    print(f"checking against golden baselines: {tfs}", flush=True)
    all_fails = []
    for tf in tfs:
        all_fails += check(tf)
    if all_fails:
        print("\n❌ GOLDEN REGRESSION — results changed:", flush=True)
        for f in all_fails:
            print("   " + f, flush=True)
        return 1
    print("\n✅ ALL GOLDEN BASELINES MATCH — results unchanged.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
