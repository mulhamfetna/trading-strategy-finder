"""End-to-end L2 round-1 smoke: run L1, build the dropped-signal dataset, run L2 with a PERMISSIVE
stand-in profile (no indicators, no vol gate ⇒ L2 takes every dropped signal where L1 is flat), and
print standalone + combined-guardrail metrics. Read-only.

Using a permissive profile (rather than L1's own lean params) is deliberate: lean-params-as-L2 yields
0 trades — L2 with L1's own gate rejects exactly the bars L1 dropped (the counterfactual "accept the
pause" result). The permissive profile exercises the full pipeline (trades + L1-entry force-close).
The real, profitable L2 profile is what the later optimizer phase (prefix l2v1) will search for.

Run:  python3 -m optimize.l2.run_smoke
"""
from __future__ import annotations

import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, dataset, engine, metrics    # noqa: E402


def _permissive_l2_profile(l1) -> dict:
    """Take every flat dropped signal in the box direction: no indicators, no vol gate, no breaker."""
    p = l1.params
    return dict(sl_soft=p["sl_soft"], sl_hard=p["sl_hard"], tp=p["tp"],
                gate_pct=0.0, dd_limit=0.0, cooldown=0, flip=False, k=1,
                ind_1min=False, indicators=[])


def main() -> int:
    import warnings
    warnings.filterwarnings("ignore")
    l1 = l1_runner.run_l1("4h")
    ds = dataset.build_dataset(l1)
    res = engine.run_l2(l1, _permissive_l2_profile(l1))
    s = metrics.score(res)
    g = metrics.combined(l1, res)
    print(f"L1 trades={len(l1.ledger)} pnl=${sum(t['pnl'] for t in l1.ledger):,.0f}")
    print(f"dropped total={len(ds)} veto={ds.n_veto} vol_gate={ds.n_vol_gate} "
          f"flat_candidates={len(ds.flat_candidates())}")
    print(f"L2 (permissive) standalone: n={s['n']} pnl=${s['pnl']:,.0f} maxDD=${s['max_dd']:,.0f} "
          f"win={s['win']}% L1-entry-exits={s['n_l1_entry_exits']}")
    print(f"combined: pnl=${g['pnl']:,.0f} maxDD=${g['max_dd']:,.0f} "
          f"(L1-only DD ${g['l1_only_dd']:,.0f}) dd_not_worse={g['dd_not_worse']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
