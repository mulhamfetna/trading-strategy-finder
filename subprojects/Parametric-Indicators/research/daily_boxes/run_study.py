"""Run the daily-box characterization. SERVER ONLY (loads champion + 1-min data).

Usage:
  python3 -m research.daily_boxes.run_study --tf 4h --horizons 1,3,6 --seed 20260723 \
      --draws 1000 --block 20 --loc-frac 0.02
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parents[2]
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from engine import _LEVEL_PAIRS                                          # noqa: E402
from optimize import counterfactual_pause as cp                          # noqa: E402
from optimize.signals import decision_signals                            # noqa: E402
from research.daily_boxes.extended_frame import load_extended            # noqa: E402
from research.daily_boxes.informativeness import (                       # noqa: E402
    block_bootstrap_ci, block_bootstrap_diff_ci, control_date, control_location,
    directional_forward_returns, min_detectable_effect,
)
from research.daily_boxes.levels import DAILY_LEVELS                     # noqa: E402
from research.daily_boxes.measure import gate_survival, supply_stats     # noqa: E402
from research.daily_boxes.study_signals import study_signals             # noqa: E402

_EXPECTED_BARS = {"4h": 2119}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True)
    ap.add_argument("--horizons", required=True, help="comma-separated bar counts, e.g. 1,3,6")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--draws", type=int, required=True, help="control draws / bootstrap resamples")
    ap.add_argument("--block", type=int, required=True, help="bootstrap block length in bars")
    ap.add_argument("--loc-frac", type=float, required=True, help="control-1 offset as a fraction of price")
    ap.add_argument("--out", default="results/daily_boxes")
    a = ap.parse_args()
    horizons = [int(h) for h in a.horizons.split(",")]

    # ---- MANDATORY parameter echo: no silent defaults, ever.
    print("=" * 72)
    print("DAILY-BOX CHARACTERIZATION -- parameters actually used")
    print(f"  timeframe        : {a.tf}")
    print(f"  horizons (bars)  : {horizons}")
    print(f"  seed             : {a.seed}")
    print(f"  control draws    : {a.draws}")
    print(f"  bootstrap block  : {a.block}")
    print(f"  loc control frac : {a.loc_frac}")
    print(f"  base level pairs : {[p[2] for p in _LEVEL_PAIRS]}")
    print(f"  daily level pairs: {[p[2] for p in DAILY_LEVELS]}")
    print("=" * 72)

    rng = np.random.default_rng(a.seed)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # ================= M1 + M2 : champion window =================
    C = cp.load_champion(a.tf)
    df_dec, box, gate = C["d"], C["box"], cp._engine_gate(C)
    n_bars = len(df_dec)
    print(f"\n[M1/M2] champion frame: {n_bars} bars "
          f"{df_dec['Date'].min()} -> {df_dec['Date'].max()}")
    if a.tf in _EXPECTED_BARS and n_bars != _EXPECTED_BARS[a.tf]:
        raise SystemExit(f"ABORT: expected {_EXPECTED_BARS[a.tf]} bars for {a.tf}, got {n_bars}. "
                         "The champion frame moved; the baseline comparison would be invalid.")

    # fidelity gate -- our rule must equal production's on the production level set
    ours = study_signals(df_dec, box, _LEVEL_PAIRS)
    prod = decision_signals(df_dec, box)
    n_mismatch = int((ours != prod).sum())
    if n_mismatch:
        raise SystemExit(f"ABORT: parity gate failed -- {n_mismatch} bars differ from decision_signals.")
    print(f"[parity] study_signals == decision_signals on all {n_bars} bars  OK")

    s = supply_stats(df_dec, box, _LEVEL_PAIRS, DAILY_LEVELS)
    baseline_entries = int(len(cp.champion_taken_trades(C)))
    g = gate_survival(s["new_mask"], gate, baseline_entries)

    print(f"\n[M1] base={s['base_signals']}  daily={s['daily_signals']}  "
          f"combined={s['combined_signals']}  NEW={s['new_signals']}")
    print(f"[M1] days: total={s['days_total']} with-base={s['days_with_base_signal']} "
          f"scarce={s['days_scarce']} rescued-by-daily={s['days_rescued_by_daily']}")
    print(f"[M2] baseline entries={baseline_entries}  new gate-surviving={g['gate_surviving']}  "
          f"uplift={g['uplift']:.1%}  band={g['verdict_band']}")
    print("[M2] NOTE: upper bound -- ignores position-carry, cooldown and breaker.")

    pd.DataFrame([{**{k: v for k, v in s.items() if k != "new_mask"},
                   **g, "tf": a.tf, "bars": n_bars,
                   "baseline_entries": baseline_entries}]).to_csv(
        outdir / f"{a.tf}_supply.csv", index=False)

    # ================= M3 : champion window, plus the 2024 extension WHERE IT EXISTS =================
    # The 2024 add-on candles exist for 4h and 1m only -- there is no NQ_1h_2024.csv. Rather than fabricate
    # one by resampling (which would not be byte-comparable to how the production frames were built), the
    # extended arm is simply SKIPPED and the skip is printed, so a missing window can never be mistaken for
    # a measured null.
    windows = {"champion_2025_2026": (df_dec, box)}
    try:
        windows["extended_2024_2026"] = load_extended(a.tf)
    except FileNotFoundError as e:
        print(f"\n[M3] extended 2024-26 window UNAVAILABLE for {a.tf} (missing {e}); "
              f"reporting the champion window only.")

    rows = []
    diffs = []
    for window, (dd, bx) in windows.items():
        real = study_signals(dd, bx, DAILY_LEVELS)
        c1 = study_signals(dd, control_location(bx, DAILY_LEVELS, rng, a.loc_frac), DAILY_LEVELS)
        c2 = study_signals(dd, control_date(bx, DAILY_LEVELS, rng), DAILY_LEVELS)
        for h in horizons:
            arms = {}
            for label, sg in (("real", real), ("control_location", c1), ("control_date", c2)):
                r = directional_forward_returns(dd, sg, h)
                r = r[~np.isnan(r)]
                arms[label] = r
                lo, hi = block_bootstrap_ci(r, a.block, a.draws, 0.10, np.random.default_rng(a.seed))
                rows.append({
                    "window": window, "horizon": h, "arm": label, "n": len(r),
                    "mean_points": float(r.mean()) if len(r) else float("nan"),
                    "mean_dollars": float(r.mean()) * 20.0 if len(r) else float("nan"),
                    "ci90_lo": lo, "ci90_hi": hi,
                    "min_detectable_effect_points": min_detectable_effect(r),
                })
                print(f"[M3] {window:20s} h={h} {label:17s} n={len(r):6d} "
                      f"mean={rows[-1]['mean_points']:+8.2f}pt "
                      f"CI90=[{lo:+.2f},{hi:+.2f}] MDE={rows[-1]['min_detectable_effect_points']:.2f}")

            # THE decisive comparison: is real BETTER than each dumb control? Overlapping one-sample CIs are
            # not a test of the difference, so bootstrap the difference itself.
            for ctrl in ("control_location", "control_date"):
                pt, dlo, dhi = block_bootstrap_diff_ci(arms["real"], arms[ctrl], a.block, a.draws, 0.10,
                                                       np.random.default_rng(a.seed + 1))
                beats = dlo > 0.0
                diffs.append({"window": window, "horizon": h, "vs": ctrl,
                              "diff_points": pt, "diff_dollars": pt * 20.0,
                              "ci90_lo": dlo, "ci90_hi": dhi, "real_beats_control": beats})
                print(f"[M3-DIFF] {window:20s} h={h} real - {ctrl:16s} "
                      f"= {pt:+8.2f}pt CI90=[{dlo:+.2f},{dhi:+.2f}] "
                      f"{'REAL WINS' if beats else 'no advantage'}")

    pd.DataFrame(rows).to_csv(outdir / f"{a.tf}_informativeness.csv", index=False)
    pd.DataFrame(diffs).to_csv(outdir / f"{a.tf}_real_vs_control.csv", index=False)

    n_wins = sum(1 for d in diffs if d["real_beats_control"])
    print(f"\n[VERDICT INPUT] supply band = {g['verdict_band']} (uplift {g['uplift']:.1%})")
    print(f"[VERDICT INPUT] real beats a dumb control in {n_wins}/{len(diffs)} comparisons")
    print(f"\nwrote {outdir}/{a.tf}_supply.csv, {a.tf}_informativeness.csv, {a.tf}_real_vs_control.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
