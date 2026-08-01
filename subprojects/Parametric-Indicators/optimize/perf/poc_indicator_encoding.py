"""#97 PoC — can "off" live inside a parameter value, or must it be its own flag?

THE QUESTION. The indicator layer is 460 of the strategy's 466 search dimensions: 165 on/off flags plus
295 parameters. The proposal is to delete the 165 flags and encode "off" inside a parameter value
(`n = 0` means this indicator is off), compressing flag+params into one axis per indicator.

WHAT THIS MEASURES, AND WHY IT IS A SAMPLING QUESTION. Whether the encoding is viable does not depend on
profitability at all — it depends on whether the search can ever REACH the off state. So this runs the
production sampler over the three candidate parameterizations and records, per trial, how many
indicators came out enabled. No backtest, no P&L: minutes instead of days.

    ARM A  flags          en_<key> categorical [False, True], params always drawn   (today)
    ARM B  value-encoded  no flag; off iff the indicator's first numeric param sits on its off value
    ARM C  conditional    en_<key> categorical, params drawn ONLY when the flag is on

THE ADVERSARIAL BIT — this is deliberately rigged IN FAVOUR of the encoding under test. The objective
is `minimise the number of enabled indicators`. Nothing else. So the search is under maximum possible
pressure to find "off", with no competing goal to distract it. If arm B still cannot turn indicators
off when turning them off is the ONLY thing being rewarded, it cannot do it in a real search either —
where "off" competes with fitting the price series.

A dumb control runs alongside: uniform random sampling of the same spaces. If the optimizer does no
better than random at the thing it is being paid to do, the comparison is measuring the space, not the
sampler.

PREDICTION, recorded before running (#97):
  * arm A centres near 82 enabled (half of 165) and the optimizer drives it toward 0
  * arm C behaves like A — the flag is unchanged, only the dead parameter draws are removed
  * arm B sits at or very near 165 (every indicator permanently ON), because for a CONTINUOUS
    parameter the off value is a single point on a real interval: probability exactly zero, and
    NSGA-III has no snap-to-off operator to reach it

Run:  WSH_DATA_BASE=... python3 -m optimize.perf.poc_indicator_encoding --trials 400
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import optuna

import provenance
from indicators import library
from optimize import optimizer as OPT

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _numeric_params(key):
    return [p for p in library.SCHEMA[key].get("params", [])
            if p.get("min") is not None and p.get("max") is not None]


def _off_sentinel(p):
    """The value that would mean 'off' under arm B: the bottom of the parameter's own range.

    Chosen as the MOST reachable candidate on purpose. A sentinel outside the range (`0` for a
    parameter bounded at 5) would be unreachable by construction and the test would prove nothing but
    its own setup. Using the range minimum gives the encoding the best case it can possibly have.
    """
    return p["min"]


def _is_float(p):
    return isinstance(p.get("min"), float) or isinstance(p.get("max"), float) \
        or isinstance(p.get("default"), float) or isinstance(p.get("step"), float)


def arm_flags(trial) -> int:
    n = 0
    for key in library.REGISTRY:
        on = trial.suggest_categorical(f"en_{key}", [False, True])
        for p in library.SCHEMA[key].get("params", []):
            OPT._suggest_param(trial, f"{key}_{p['name']}", p)      # always drawn — today's behaviour
        n += int(bool(on))
    return n


def arm_value_encoded(trial) -> int:
    n = 0
    for key in library.REGISTRY:
        ps = _numeric_params(key)
        if not ps:
            # No numeric parameter to carry the encoding, so this indicator has nowhere to put "off".
            # Counted as permanently on, which is what the proposal implies for these 23 keys.
            n += 1
            continue
        first = ps[0]
        v = OPT._suggest_param(trial, f"{key}_{first['name']}", first)
        for p in ps[1:]:
            OPT._suggest_param(trial, f"{key}_{p['name']}", p)
        n += int(v != _off_sentinel(first))
    return n


def arm_conditional(trial) -> int:
    n = 0
    for key in library.REGISTRY:
        on = trial.suggest_categorical(f"en_{key}", [False, True])
        if on:                                                       # params drawn ONLY when enabled
            for p in library.SCHEMA[key].get("params", []):
                OPT._suggest_param(trial, f"{key}_{p['name']}", p)
        n += int(bool(on))
    return n


ARMS = {"A_flags": arm_flags, "B_value_encoded": arm_value_encoded, "C_conditional": arm_conditional}


def _run_optimizer(fn, n_trials, seed):
    counts = []

    def objective(trial):
        n = fn(trial)
        counts.append(n)
        return float(n)          # minimise enabled count — maximum pressure toward "off"

    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.NSGAIIISampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return counts


def _run_random(fn, n_trials, seed):
    """The dumb control: the same spaces, sampled uniformly at random."""
    counts = []
    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.RandomSampler(seed=seed))
    study.optimize(lambda t: float(counts.append(fn(t)) or counts[-1]),
                   n_trials=n_trials, show_progress_bar=False)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    n_keys = len(library.REGISTRY)
    n_float_first = sum(1 for k in library.REGISTRY
                        if _numeric_params(k) and _is_float(_numeric_params(k)[0]))
    n_no_params = sum(1 for k in library.REGISTRY if not _numeric_params(k))
    print(provenance.one_line(), flush=True)
    print(f"[poc97] {n_keys} indicators · {n_float_first} carry a FLOAT first parameter (off value has "
          f"probability zero there) · {n_no_params} have no numeric parameter at all (nowhere to put "
          f"'off')", flush=True)
    print(f"[poc97] objective = MINIMISE enabled count. Deliberately rigged in favour of the encoding "
          f"under test: turning indicators off is the only thing rewarded.\n", flush=True)

    out = {"trials": args.trials, "seed": args.seed, "n_indicators": n_keys,
           "n_float_first_param": n_float_first, "n_without_numeric_params": n_no_params,
           "provenance": provenance.snapshot(argv=sys.argv), "arms": {}}

    for name, fn in ARMS.items():
        opt = _run_optimizer(fn, args.trials, args.seed)
        rnd = _run_random(fn, args.trials, args.seed)
        first, last = opt[:50], opt[-50:]
        row = {
            "optimizer": {"min": min(opt), "max": max(opt),
                          "mean_first50": sum(first) / len(first),
                          "mean_last50": sum(last) / len(last),
                          "reached_zero": min(opt) == 0},
            "random_control": {"min": min(rnd), "mean": sum(rnd) / len(rnd)},
        }
        out["arms"][name] = row
        o = row["optimizer"]
        print(f"[poc97] {name:16s} enabled count: min={o['min']:3d} max={o['max']:3d}  "
              f"first50={o['mean_first50']:6.1f} -> last50={o['mean_last50']:6.1f}   "
              f"(random control min={row['random_control']['min']:3d}, "
              f"mean={row['random_control']['mean']:.1f})", flush=True)

    a, b, c = (out["arms"][k]["optimizer"] for k in ("A_flags", "B_value_encoded", "C_conditional"))
    print("\n[poc97] VERDICT")
    print(f"  arm A drove enabled {a['mean_first50']:.0f} -> {a['mean_last50']:.0f}")
    print(f"  arm C drove enabled {c['mean_first50']:.0f} -> {c['mean_last50']:.0f}")
    print(f"  arm B drove enabled {b['mean_first50']:.0f} -> {b['mean_last50']:.0f}"
          f"   (of {n_keys}; floor reachable only via {n_keys - n_float_first - n_no_params} keys)")
    verdict = ("REFUTED — value encoding cannot switch indicators off even when that is the ONLY "
               "objective" if b["mean_last50"] > 0.8 * n_keys else
               "NOT REFUTED — value encoding reached the off state; needs a P&L comparison next")
    print(f"  => {verdict}")
    out["verdict"] = verdict

    p = Path(args.out) if args.out else (Path(__file__).resolve().parent / "results" / "poc97_encoding.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    print(f"\n[poc97] wrote {p}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
