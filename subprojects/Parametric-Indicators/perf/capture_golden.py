"""Phase 0 — freeze the CURRENT engine's outputs as immutable golden baselines (task #210).

For each champion timeframe it records, into perf/golden/:
  <tf>.json        — summary metrics + content hashes (trades + per-indicator votes) + key params
  <tf>_votes.npz   — the full per-decision-bar vote array of every enabled indicator
  <tf>_trades.csv  — the full taken-trade ledger

These are the "before photographs". Every later optimization must reproduce them byte-for-byte
(checked by perf/check_golden.py). Run ONCE before any engine change.

Run:  python3 perf/capture_golden.py [tf ...]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from _common import TFS, load_bundle, compute_votes_named   # noqa: E402  (perf/ on path via run dir)

_HERE = Path(__file__).resolve().parent
_GOLD = _HERE / "golden"
_GOLD.mkdir(exist_ok=True)
sys.path.insert(0, str(_HERE.parent))
import strategy  # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _trades_frame(trades):
    import pandas as pd
    cols = ["entry_time", "exit_time", "direction", "entry_price", "exit_price",
            "exit_reason", "sl_soft_line", "sl_hard_line", "tp_hard_line", "pnl", "equity", "dd"]
    return pd.DataFrame([{c: t.get(c) for c in cols} for t in trades], columns=cols)


def capture(tf: str) -> dict:
    df_dec, df1, box, vf, n2025, preset = load_bundle(tf)
    payload = strategy.build_payload(df_dec, df1, box, vf, n2025, preset)
    s = payload["meta"]["summary"]
    trades = payload["trades"]

    tdf = _trades_frame(trades)
    tdf.to_csv(_GOLD / f"{tf}_trades.csv", index=False)
    trades_hash = _sha(tdf.to_csv(index=False).encode())

    votes = compute_votes_named(tf, df_dec, df1, box, preset)
    np.savez_compressed(_GOLD / f"{tf}_votes.npz", **votes)
    vote_hashes = {k: _sha(np.ascontiguousarray(v).tobytes()) for k, v in sorted(votes.items())}

    rec = {
        "tf": tf,
        "summary": {k: s[k] for k in ("pnl", "max_dd", "n_taken", "n_candidates", "win", "pf",
                                      "avg_win", "avg_loss", "n_locks", "noentry_streak_n",
                                      "noentry_streak_days")},
        "n_trades": len(trades),
        "trades_sha256": trades_hash,
        "vote_sha256": vote_hashes,
        "indicators_enabled": sorted(votes.keys()),
    }
    (_GOLD / f"{tf}.json").write_text(json.dumps(rec, indent=1))
    print(f"  [{tf}] P/L ${s['pnl']:,.0f}  DD ${s['max_dd']:,.0f}  n={s['n_taken']}  "
          f"trades#{trades_hash[:8]}  +{len(votes)}ind", flush=True)
    return rec


def main() -> int:
    tfs = sys.argv[1:] or TFS
    print(f"capturing golden baselines for: {tfs}", flush=True)
    for tf in tfs:
        capture(tf)
    print(f"golden baselines written -> {_GOLD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
