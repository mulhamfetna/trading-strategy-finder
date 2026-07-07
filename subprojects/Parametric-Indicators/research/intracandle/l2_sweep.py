"""E3a champion-first study: run the L2 champion with intra-candle entry timing ON across a sweep of wait
windows N, and report the COMBINED (L1+L2) book vs today's baseline ($175,372 / 289 / $14,342 DD). Gates the
l2ic1 optimizer run. L1 stays the frozen champion; only L2's vetoed-stream entry timing changes."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.l2 import l1_runner, engine, metrics  # noqa: E402
from optimize.l2.payload import validate_layer_params, l2_default_params  # noqa: E402

_L1 = None


def _l1(tf):
    global _L1
    if _L1 is None:
        _L1 = l1_runner.run_l1(tf)
    return _L1


def sweep(tf="4h", Ns=(30, 60, 120, 240)):
    l1 = _l1(tf)
    base = dict(l2_default_params())                          # the promoted L2 champion (l2v2)
    rows = []
    for N in Ns:
        p = validate_layer_params({**base, "l2_intracandle": True, "l2_intracandle_max_wait": N})
        r = engine.run_l2(l1, p)
        c = metrics.combined(l1, r)                           # {pnl, max_dd, l1_only_dd, dd_not_worse}
        rows.append({"N": N,
                     "l2_n": len(r.ledger),
                     "l2_pnl": round(float(sum(t["pnl"] for t in r.ledger)), 0),
                     "combined_pnl": round(float(c["pnl"]), 0),
                     "combined_n": len(l1.ledger) + len(r.ledger),
                     "combined_dd": round(float(c["max_dd"]), 0),
                     "dd_not_worse": bool(c["dd_not_worse"])})
    return rows


if __name__ == "__main__":
    import json
    print("baseline combined (l2_intracandle OFF, l2v2 champion): $175,372 / 289 / $14,342 DD")
    for r in sweep():
        print(json.dumps(r))
