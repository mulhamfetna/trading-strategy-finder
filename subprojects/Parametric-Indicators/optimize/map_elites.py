"""P4 — MAP-Elites quality-diversity archive (REPORT_optimizer_algorithm_alternatives.md §5 P4).

Every other algorithm returns ONE best point and can collapse into a single basin (the superset paradox).
MAP-Elites instead keeps an ARCHIVE of the best solution PER NICHE, so it is rewarded for diversity and
structurally cannot collapse — and it yields a PORTFOLIO of champions (safe / high-return / few-indicator)
rather than one point.

Behavior descriptors (the niche axes) for us:
    bd1 = worst-fold drawdown bucket   (how SAFE)      — bins of $2,000, capped
    bd2 = number of indicators enabled (how COMPLEX)   — raw count 0..N
Fitness (maximise) = median fold P/L, FEASIBLE only (full_dd ≤ 25%·full_pnl, full_pnl > 0).

Genotype (reuses P3's frozen-indicator-params philosophy — tune WHICH indicators + execution knobs, not
each indicator's internals): en[<key>] on/off (18), flip, and the continuous knobs (sl_soft, sl_hard_delta,
tp, gate_pct, dd_limit, cooldown, k, +6 split). Indicator params are frozen at the warm-start champion.

The wsh4 champion is enqueued as the FIRST elite ⇒ the archive provably contains a point ≥ it.

CLI:  python3 -m optimize.map_elites <tf> [--evals N] [--ind-1min] [--split-sltp] [--no-warm-start] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import two_stage as TS              # reuse _Ctx (data load + build_params + evaluate + champion)
from optimize import optimizer as OPT
from indicators import library

DD_BIN = 2000.0          # worst-fold DD bucket width ($)
DD_BIN_CAP = 8           # cap the DD axis at 8 buckets (≥$16k all share the top cell)


def cont_space(ctx) -> dict:
    """name -> (lo, hi, is_int) for every continuous knob, from the per-TF bounds. +split when enabled."""
    b = ctx.b
    s = {"sl_soft": (float(b["sl_soft"][0]), float(b["sl_soft"][1]), False),
         "sl_hard_delta": (0.0, float(b["sl_hard"][1]), False),
         "tp": (float(b["tp"][0]), float(b["tp"][1]), False),
         "gate_pct": (0.0, 100.0, False),
         "dd_limit": (0.0, TS.DD_LIMIT_MAX, False),
         "cooldown": (0, ctx.cap, True),
         "k": (1, 5, True)}
    if ctx.split_sltp:
        s.update(long_sl_soft=s["sl_soft"], long_sl_hard_delta=s["sl_hard_delta"], long_tp=s["tp"],
                 short_sl_soft=s["sl_soft"], short_sl_hard_delta=s["sl_hard_delta"], short_tp=s["tp"])
    return s


def behavior(m: dict, n_ind: int) -> tuple[int, int]:
    """Map metrics → (dd_bucket, n_indicators) niche coordinate."""
    return (min(int(m["worst_dd"] // DD_BIN), DD_BIN_CAP), int(n_ind))


def _rand_cont(space: dict, rng: random.Random) -> dict:
    out = {}
    for nm, (lo, hi, is_int) in space.items():
        v = rng.uniform(lo, hi)
        out[nm] = int(round(v)) if is_int else v
    return out


def _perturb_cont(cont: dict, space: dict, rng: random.Random) -> dict:
    """Gaussian nudge each knob by ~10% of its range, clamped to bounds."""
    out = {}
    for nm, (lo, hi, is_int) in space.items():
        sigma = 0.10 * (hi - lo)
        v = min(hi, max(lo, cont[nm] + rng.gauss(0.0, sigma)))
        out[nm] = int(round(v)) if is_int else v
    return out


def _rand_geno(ctx, space, rng):
    en = {k: (rng.random() < 0.4) for k in library.REGISTRY}
    return en, (rng.random() < 0.5), _rand_cont(space, rng)


def _mutate(geno, space, rng):
    en, flip, cont = geno
    en = dict(en)
    for _ in range(rng.choice([1, 1, 2])):          # toggle 1–2 indicator bits
        en[rng.choice(list(library.REGISTRY))] ^= True
    if rng.random() < 0.10:
        flip = not flip
    return en, flip, _perturb_cont(cont, space, rng)


def run(tf_name: str, n_evals: int = 400, folds: int = 5, min_trades: int = 5, seed: int = 1,
        ind_1min: bool = False, split_sltp: bool = False, warm_start: bool = True,
        save: bool = False) -> dict:
    t0 = time.time()
    ctx = TS._Ctx(tf_name, split_sltp, ind_1min, folds, min_trades, warm_start)
    space = cont_space(ctx)
    rng = random.Random(seed)
    n_enabled = lambda en: sum(1 for k in library.REGISTRY if en[k])

    archive: dict[tuple[int, int], dict] = {}     # niche -> {fitness, metrics, geno, n_ind}

    def consider(geno):
        en, flip, cont = geno
        m = ctx.evaluate(ctx.build_params(en, flip, cont))
        if m is None or not m["feasible"]:
            return False
        n_ind = n_enabled(en)
        cell = behavior(m, n_ind)
        cur = archive.get(cell)
        if cur is None or m["median_pnl"] > cur["fitness"]:
            archive[cell] = {"fitness": m["median_pnl"], "metrics": m, "n_ind": n_ind,
                             "geno": (dict(en), flip, dict(cont))}
            return True
        return False

    # ── seed: warm-start champion first (guarantees a ≥-champion elite), then random bootstrap ──
    evals = 0
    if ctx.has_champion:
        consider((dict(ctx.champ_en), ctx.champ_flip, dict(ctx.champ_cont))); evals += 1
    n_boot = min(max(10, n_evals // 10), n_evals - evals)
    for _ in range(n_boot):
        consider(_rand_geno(ctx, space, rng)); evals += 1

    print(f"[{tf_name}] MAP-ELITES  evals={n_evals}  (bootstrap {evals}; archive {len(archive)} cells)  "
          f"{'[champion seeded]' if ctx.has_champion else '[no champion]'}", flush=True)

    # ── main loop: select a random elite, mutate, place if it wins its cell ──
    improvements = 0
    while evals < n_evals:
        if archive:
            parent = rng.choice(list(archive.values()))["geno"]
            child = _mutate(parent, space, rng)
        else:
            child = _rand_geno(ctx, space, rng)
        if consider(child):
            improvements += 1
        evals += 1
        if evals % max(1, n_evals // 10) == 0:
            print(f"   {evals}/{n_evals} evals · {len(archive)} cells filled · {improvements} improvements",
                  flush=True)

    # ── summary: portfolio highlights ──
    cells = list(archive.values())
    best_overall = max(cells, key=lambda c: c["fitness"]) if cells else None
    safest = min(cells, key=lambda c: c["metrics"]["worst_dd"]) if cells else None
    simplest = min(cells, key=lambda c: c["n_ind"]) if cells else None
    dur = time.time() - t0
    print(f"[{tf_name}] MAP-ELITES DONE ({dur:.0f}s): {len(archive)} niches filled", flush=True)
    if best_overall:
        b = best_overall["metrics"]
        print(f"   best return : med ${b['median_pnl']:,.0f}  worstDD ${b['worst_dd']:,.0f}  "
              f"full ${b['full_pnl']:,.0f}  +{best_overall['n_ind']}ind", flush=True)
        s = safest["metrics"]
        print(f"   safest      : med ${s['median_pnl']:,.0f}  worstDD ${s['worst_dd']:,.0f}  "
              f"+{safest['n_ind']}ind", flush=True)
        print(f"   simplest    : med ${simplest['metrics']['median_pnl']:,.0f}  "
              f"+{simplest['n_ind']}ind", flush=True)

    result = {"timeframe": tf_name, "evals": n_evals, "coverage": len(archive), "dur_s": dur,
              "best_overall": _portfolio_entry(best_overall), "safest": _portfolio_entry(safest),
              "simplest": _portfolio_entry(simplest),
              "archive": {f"{c}": _portfolio_entry(v) for c, v in archive.items()}}
    if save:
        out = OPT._RESULTS_DIR / f"mapelites_{tf_name}.json"
        out.write_text(json.dumps(result, indent=2)); print(f"   wrote {out}", flush=True)
    return result


def _portfolio_entry(cell: dict | None) -> dict | None:
    if cell is None:
        return None
    m = cell["metrics"]
    return {"median_pnl": m["median_pnl"], "worst_dd": m["worst_dd"], "median_win": m["median_win"],
            "full_pnl": m["full_pnl"], "full_dd": m["full_dd"], "n_ind": cell["n_ind"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="P4 MAP-Elites quality-diversity archive")
    ap.add_argument("timeframe")
    ap.add_argument("--evals", type=int, default=400)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ind-1min", action="store_true")
    ap.add_argument("--split-sltp", action="store_true")
    ap.add_argument("--no-warm-start", action="store_true")
    ap.add_argument("--save", action="store_true", help="write archive to optimize/results/mapelites_<tf>.json")
    a = ap.parse_args()
    run(a.timeframe, n_evals=a.evals, folds=a.folds, min_trades=a.min_trades, seed=a.seed,
        ind_1min=a.ind_1min, split_sltp=a.split_sltp, warm_start=not a.no_warm_start, save=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
