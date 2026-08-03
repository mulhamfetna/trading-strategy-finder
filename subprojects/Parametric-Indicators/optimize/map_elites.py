"""P4 — MAP-Elites quality-diversity archive (REPORT_optimizer_algorithm_alternatives.md §5 P4).

Every other algorithm returns ONE best point and can collapse into a single basin (the superset paradox).
MAP-Elites instead keeps an ARCHIVE of the best solution PER NICHE, so it is rewarded for diversity and
structurally cannot collapse — and it yields a PORTFOLIO of champions (safe / high-return / few-indicator)
rather than one point.

Behavior descriptors (the niche axes) for us:
    bd1 = worst-fold drawdown bucket   (how SAFE)      — bins of $2,000, capped
    bd2 = indicator-count BUCKET       (how COMPLEX)   — 9 groups, fine at 3–10, catch-all at 51+
Fitness (maximise) = median fold P/L, FEASIBLE only (full_dd ≤ 25%·full_pnl, full_pnl > 0).

Genotype (reuses P3's frozen-indicator-params philosophy — tune WHICH indicators + execution knobs, not
each indicator's internals): en[<key>] on/off (one per REGISTRY entry — 165 today, 18 when this was
written), flip, and the continuous knobs (sl_soft, sl_hard_delta, tp, gate_pct, dd_limit, cooldown, k,
+6 split). Indicator params are frozen at the warm-start champion.

⚠️ CAVEAT THAT SURVIVES THE #81 FIX: freezing the indicator params means an indicator is judged at ONE
parameter setting, and for the ~157 indicators absent from the warm-start champion that setting is the
SCHEMA DEFAULT (two_stage.py:83-86) — never tuned for this market. An indicator that would win at a
different value is eliminated before its values are explored. Tracked in #85; MAP-Elites inherits the
fix when two_stage._Ctx gets it.

The wsh4 champion is enqueued as the FIRST elite ⇒ the archive provably contains a point ≥ it.

CLI:  python3 -m optimize.map_elites <tf> [--evals N] [--split-sltp] [--no-warm-start] [--seed S]
      Indicators read the 1-MINUTE frame by default; pass --tf-indicators for the decision frame.
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

# ── the indicator axis (#88) ──────────────────────────────────────────────────────────────────────
# THE DEFECT THIS REPLACES. The second axis used to be the RAW indicator count, so the archive had one
# column per possible count and its width tracked the registry. At 18 indicators that was 19 columns —
# 9 x 19 = 171 niches against a standard 400 evaluations, i.e. ~2.3 visits per niche, so "is the
# newcomer better than the current elite?" was a question that actually got asked. At 165 indicators it
# is 166 columns = 1,494 niches and ~0.27 visits: nearly every niche is filled by the FIRST genome that
# happens to land in it and is never challenged again.
#
# That converts MAP-Elites from "keep the best per niche" into "keep the first per niche" WITHOUT
# failing, erroring, or looking any different — the archive still comes back full and is still reported
# as a portfolio of elites. Same class as the other registry-scaling defects (#81, #89 rules S2/S6): a
# constant that is really a RATIO, correct at the size it was written for and silently wrong after.
#
# The counts themselves were never the point. Deployed champions use 3–10 indicators; a 61-indicator
# genome and a 62-indicator one are not different KINDS of strategy, but they were given separate
# niches and each stole visits from the region that matters. So: bucket the axis — fine where champions
# live, coarse above — and end in an unbounded catch-all so the width is fixed at 9 no matter how big
# the library gets. 9 x 9 = 81 niches ⇒ ~4.9 visits each at 400 evals.
#
# ⚠️ THIS FIXES THE ARCHIVE'S SHAPE, NOTHING ELSE. It does not make earlier MAP-Elites results valid —
# those came from the broken shape and are UNVALIDATED (tracked in #90), which is a different and more
# awkward status than wrong. And it makes no claim that MAP-Elites beats the ordinary search.
IND_BINS = ((0, 0), (1, 2), (3, 4), (5, 7), (8, 10), (11, 15), (16, 25), (26, 50))
IND_BIN_CAP = len(IND_BINS)          # index of the unbounded "51+" bucket
IND_BIN_LABELS = tuple(f"{lo}" if lo == hi else f"{lo}-{hi}" for lo, hi in IND_BINS) + \
                 (f"{IND_BINS[-1][1] + 1}+",)
N_NICHES = (DD_BIN_CAP + 1) * (IND_BIN_CAP + 1)


def ind_bucket(n_ind: int) -> int:
    """Indicator count → bucket index. Registry-size independent BY CONSTRUCTION: the edges are absolute
    counts and the last bucket is unbounded, so growing the library cannot widen the archive."""
    for i, (lo, hi) in enumerate(IND_BINS):
        if lo <= n_ind <= hi:
            return i
    return IND_BIN_CAP


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
    """Map metrics → (dd_bucket, indicator_bucket) niche coordinate. BOTH axes are bounded, so the
    archive has a fixed 81 niches whatever the registry size — see IND_BINS above for why."""
    return (min(int(m["worst_dd"] // DD_BIN), DD_BIN_CAP), ind_bucket(int(n_ind)))


def niche_label(cell: tuple[int, int]) -> str:
    """Human-readable niche name, so a saved archive stays interpretable once the bin edges move.

    Tolerates an indicator coordinate outside IND_BIN_LABELS instead of raising. The #88 A/B substitutes
    the identity for `ind_bucket` to reproduce the old raw-count axis, which produces coordinates up to
    the registry size — and an IndexError HERE would destroy a completed run's results at the very last
    step, after every evaluation had already been paid for. Labelling is presentation; it must never be
    able to lose the measurement."""
    dd, ind = cell
    dd_s = f"≥${DD_BIN_CAP * DD_BIN:,.0f}" if dd >= DD_BIN_CAP else \
           f"${dd * DD_BIN:,.0f}-${(dd + 1) * DD_BIN:,.0f}"
    lbl = IND_BIN_LABELS[ind] if 0 <= ind < len(IND_BIN_LABELS) else str(ind)
    return f"dd {dd_s} · {lbl} ind"


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


# Genome shape targets. Deployed champions use 3–10 indicators, so a random genome should look like a
# plausible strategy rather than a committee of everything.
#
# THE BUG THIS REPLACES (#81). `en = {k: rng.random() < 0.4 ...}` is a PROBABILITY, so the genome's size
# is a function of how big the registry happens to be. At 18 indicators it meant "about 7 enabled" — a
# realistic strategy. At 165 it means "about 66", which is nothing we would ever trade. Measured by
# simulating the genome dynamics over a standard 400-evaluation run: with 18 indicators the archive
# spanned 0–15 enabled and covered the champion region; with 165 it spanned 50–83 and NEVER reached it.
# Mutation moves the count by ±1, so from ~66 it cannot walk to ~5 within any realistic budget.
#
# Sampling a COUNT and then choosing which indicators makes the genome shape independent of registry
# size — it stays correct the next time the library grows.
# ⚠️ RAND_N_IND IS A PRIOR, NOT A LIMIT — and it should be a human's choice, not a hidden constant.
# It shapes only where the search STARTS. Mutation freely adds indicators, and the archive's second axis
# is the indicator count, so higher-count niches still get colonised (measured: bootstrapping at 1–15
# still fills the archive out to ~54 enabled). But it does encode a belief — "strategies worth finding
# look like the ones we deploy, which use 3–10" — and a belief that cannot be changed from the outside
# is indistinguishable from a bug. Override with --rand-n-ind LO,HI.
RAND_N_IND = (1, 15)     # inclusive range of enabled indicators in a bootstrap genome
MUT_FRAC = 0.02          # mutation toggles ~this fraction of the genome (min 1 bit)


def _rand_geno(ctx, space, rng, n_ind_range=None):
    keys = list(library.REGISTRY)
    lo, hi = n_ind_range or RAND_N_IND
    lo = max(0, min(int(lo), len(keys)))
    hi = max(lo, min(int(hi), len(keys)))
    n_on = rng.randint(lo, hi)
    on = set(rng.sample(keys, n_on))
    en = {k: (k in on) for k in keys}
    return en, (rng.random() < 0.5), _rand_cont(space, rng)


def _mutate(geno, space, rng):
    en, flip, cont = geno
    en = dict(en)
    keys = list(library.REGISTRY)
    # A FRACTION of the genome, not a fixed 1–2 bits: at 18 indicators 1–2 bits moved ~8% of the genome,
    # at 165 the same 1–2 bits move ~1%, so the operator silently weakened ~9x when the library grew.
    n_flip = max(1, int(round(MUT_FRAC * len(keys))))
    n_flip = rng.choice([n_flip, n_flip, n_flip + 1])       # keep the old 1–1–2 shape, scaled
    for k in rng.sample(keys, min(n_flip, len(keys))):
        en[k] ^= True
    if rng.random() < 0.10:
        flip = not flip
    return en, flip, _perturb_cont(cont, space, rng)


def run(tf_name: str, n_evals: int = 400, folds: int = 5, min_trades: int = 5, seed: int = 1,
        ind_1min: bool = True, split_sltp: bool = False, warm_start: bool = False,
        save: bool = False, n_ind_range=None) -> dict:
    t0 = time.time()
    ctx = TS._Ctx(tf_name, split_sltp, ind_1min, folds, min_trades, warm_start)
    space = cont_space(ctx)
    rng = random.Random(seed)
    n_enabled = lambda en: sum(1 for k in library.REGISTRY if en[k])

    archive: dict[tuple[int, int], dict] = {}     # niche -> {fitness, metrics, geno, n_ind}

    # THE FALSIFICATION CRITERION FOR #88, counted rather than argued. These two events were previously
    # summed into a single "improvements" number, which flattered the run: accepting a genome because
    # its niche was EMPTY involves no comparison at all, while replacing a sitting elite is the only
    # thing that makes this an elites archive. Counting shelves is arithmetic; this is the evidence.
    # If `improvements` does not rise materially against the pre-fix run, the fix did not work.
    #
    # `infeasible` is a TOTAL over three different failures, split out because they call for completely
    # different responses and were previously one number (#101):
    #   invalid  — score_walkforward said not valid: a fold had fewer than min_trades. It barely traded.
    #   pnl_neg  — it traded and LOST money over the full period.
    #   dd_over  — it traded and made money, but drew down more than DD_PNL_CAP x that profit.
    # Measured on NQ 4h these account for ~70% of all evaluations, which is why archive coverage is
    # capped by the feasibility rate rather than by the niche count.
    stats = {"first_fill": 0, "improvement": 0, "rejected": 0, "infeasible": 0,
             "invalid": 0, "pnl_neg": 0, "dd_over": 0}

    def consider(geno):
        en, flip, cont = geno
        m = ctx.evaluate(ctx.build_params(en, flip, cont))
        if m is None:
            stats["invalid"] += 1; stats["infeasible"] += 1
            return False
        if not m["feasible"]:
            stats["pnl_neg" if m["full_pnl"] <= 0 else "dd_over"] += 1
            stats["infeasible"] += 1
            return False
        n_ind = n_enabled(en)
        cell = behavior(m, n_ind)
        cur = archive.get(cell)
        if cur is None:
            stats["first_fill"] += 1                      # niche was empty — nothing was compared
        elif m["median_pnl"] > cur["fitness"]:
            stats["improvement"] += 1                     # beat a sitting elite — a real choice
        else:
            stats["rejected"] += 1
            return False
        archive[cell] = {"fitness": m["median_pnl"], "metrics": m, "n_ind": n_ind,
                         "geno": (dict(en), flip, dict(cont))}
        return True

    # ── seed: warm-start champion first (guarantees a ≥-champion elite), then random bootstrap ──
    evals = 0
    if ctx.has_champion:
        consider((dict(ctx.champ_en), ctx.champ_flip, dict(ctx.champ_cont))); evals += 1
    n_boot = min(max(10, n_evals // 10), n_evals - evals)
    for _ in range(n_boot):
        consider(_rand_geno(ctx, space, rng, n_ind_range)); evals += 1

    # Snapshot after the RANDOM bootstrap so the mutation phase can be read by subtraction (#101): a
    # random genome failing is a different diagnosis from a MUTATION OF A SITTING ELITE failing — the
    # first says the prior is wrong, the second says the neighbourhood of a good strategy is hostile.
    boot_stats = dict(stats)

    _lo, _hi = n_ind_range or RAND_N_IND
    print(f"[{tf_name}] MAP-ELITES  evals={n_evals}  (bootstrap {evals}; archive {len(archive)} cells)  "
          f"bootstrap genome = {_lo}-{_hi} of {len(library.REGISTRY)} indicators; "
          f"mutation {max(1, round(MUT_FRAC * len(library.REGISTRY)))} bits  "
          f"{'[champion seeded]' if ctx.has_champion else '[no champion]'}", flush=True)
    # Printed because it is the number that silently went wrong: below ~1 the archive keeps first
    # arrivals rather than elites, and nothing else in the output would say so (#88).
    _per_niche = n_evals / N_NICHES
    print(f"   niches {N_NICHES} = {DD_BIN_CAP + 1} dd x {IND_BIN_CAP + 1} ind "
          f"[{', '.join(IND_BIN_LABELS)}] · {_per_niche:.1f} evals/niche"
          f"{'  ⚠️ BELOW 1 — the archive will keep FIRST arrivals, not elites' if _per_niche < 1 else ''}",
          flush=True)

    # ── main loop: select a random elite, mutate, place if it wins its cell ──
    while evals < n_evals:
        if archive:
            parent = rng.choice(list(archive.values()))["geno"]
            child = _mutate(parent, space, rng)
        else:
            child = _rand_geno(ctx, space, rng, n_ind_range)
        consider(child)
        evals += 1
        if evals % max(1, n_evals // 10) == 0:
            # first-fills and improvements reported SEPARATELY — summing them was the old print, and it
            # made a run that never compared anything look like a run that kept improving (#88).
            print(f"   {evals}/{n_evals} evals · {len(archive)}/{N_NICHES} niches filled · "
                  f"{stats['improvement']} improvements ({stats['first_fill']} first-fills)", flush=True)

    # ── summary: portfolio highlights ──
    cells = list(archive.values())
    best_overall = max(cells, key=lambda c: c["fitness"]) if cells else None
    safest = min(cells, key=lambda c: c["metrics"]["worst_dd"]) if cells else None
    simplest = min(cells, key=lambda c: c["n_ind"]) if cells else None
    dur = time.time() - t0
    print(f"[{tf_name}] MAP-ELITES DONE ({dur:.0f}s): {len(archive)}/{N_NICHES} niches filled "
          f"({100 * len(archive) / N_NICHES:.0f}% coverage)", flush=True)
    # The #88 verdict line. `improvement` is the only count that means a comparison took place; if it
    # stays near zero the archive is a collection of first arrivals however full it looks.
    _placed = stats["first_fill"] + stats["improvement"]
    print(f"   selection   : {stats['improvement']} improvements · {stats['first_fill']} first-fills · "
          f"{stats['rejected']} rejected · {stats['infeasible']} infeasible  "
          f"({100 * stats['improvement'] / max(1, _placed):.0f}% of placements were a real choice)",
          flush=True)
    # ACHIEVED visits per niche, which is the number the design argument actually depends on — and it is
    # NOT n_evals/N_NICHES. Measured on NQ 4h (2026-08-03): ~65% of evaluations come back INFEASIBLE, so
    # only ~135 of 400 ever reach a niche. The planned 4.9 was really ~1.7. The binding constraint on
    # archive coverage turned out to be the feasibility rate, not the niche count — worth knowing before
    # anyone "fixes" coverage by adding more niches.
    _reached = _placed + stats["rejected"]
    print(f"   reach       : {_reached}/{n_evals} evals reached a niche ({100 * stats['infeasible'] / max(1, n_evals):.0f}% "
          f"infeasible) ⇒ {_reached / N_NICHES:.2f} ACHIEVED visits per niche, {len(archive)}/{N_NICHES} filled",
          flush=True)
    print(f"   discarded   : {stats['invalid']} barely traded (<{min_trades}/fold) · "
          f"{stats['pnl_neg']} lost money · {stats['dd_over']} drew down > {100 * TS.DD_PNL_CAP:.0f}% of profit  "
          f"(#101)", flush=True)
    _mut = {k: stats[k] - boot_stats[k] for k in stats}
    # `infeasible` is a TOTAL over invalid+pnl_neg+dd_over, so summing every key double-counts it. The
    # phase total is placements + rejections + discards.
    _tot = lambda d: d["first_fill"] + d["improvement"] + d["rejected"] + d["infeasible"]
    _bn, _mn = boot_stats["infeasible"], _mut["infeasible"]
    _bt, _mt = _tot(boot_stats), _tot(_mut)
    print(f"   by phase    : random bootstrap {_bn}/{_bt} discarded ({100 * _bn / max(1, _bt):.0f}%) · "
          f"mutation of an elite {_mn}/{_mt} discarded ({100 * _mn / max(1, _mt):.0f}%)", flush=True)
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
              # Written to disk so the archive can be judged later WITHOUT rerunning it: a full-looking
              # archive with `improvements: 0` is the broken regime, and only these fields show it.
              "n_niches": N_NICHES, "evals_per_niche": round(n_evals / N_NICHES, 2),
              # planned vs ACHIEVED — the second is the one the design argument rests on
              "reached_niche": _reached, "achieved_visits_per_niche": round(_reached / N_NICHES, 2),
              "ind_bins": list(IND_BIN_LABELS), "selection": dict(stats),
              "selection_bootstrap": dict(boot_stats), "selection_mutation": dict(_mut),
              "best_overall": _portfolio_entry(best_overall), "safest": _portfolio_entry(safest),
              "simplest": _portfolio_entry(simplest),
              "archive": {niche_label(c): _portfolio_entry(v) for c, v in archive.items()}}
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
    OPT.add_indicator_frame_args(ap)
    ap.add_argument("--split-sltp", action="store_true")
    OPT.add_warm_start_args(ap)
    ap.add_argument("--save", action="store_true", help="write archive to optimize/results/mapelites_<tf>.json")
    ap.add_argument("--rand-n-ind", default=None, metavar="LO,HI",
                    help=f"bootstrap genome size range (default {RAND_N_IND[0]},{RAND_N_IND[1]}). This is a "
                         f"PRIOR on where the search starts, not a limit — mutation still reaches higher "
                         f"counts. Pass e.g. 1,165 to bootstrap across the whole registry.")
    a = ap.parse_args()
    _rng_ind = None
    if a.rand_n_ind:
        try:
            lo, hi = (int(x) for x in str(a.rand_n_ind).split(","))
        except Exception:
            raise SystemExit(f"--rand-n-ind expects LO,HI (got {a.rand_n_ind!r})")
        _rng_ind = (lo, hi)
    run(a.timeframe, n_evals=a.evals, folds=a.folds, min_trades=a.min_trades, seed=a.seed,
        ind_1min=a.ind_1min, split_sltp=a.split_sltp, warm_start=a.warm_start, save=a.save,
        n_ind_range=_rng_ind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
