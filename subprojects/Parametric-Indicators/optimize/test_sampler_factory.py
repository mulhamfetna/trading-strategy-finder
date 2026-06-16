"""P2 regression lock — selectable optimizer sampler (make_sampler factory).

Run directly:  python3 -m optimize.test_sampler_factory
(Plain-assert script, same style as optimize/test_parity.py — no pytest required.)

Guards the contract that the sampler is swappable WITHOUT changing the objective/constraint pipeline:
  • every multi-objective brain (nsga3/nsga2/tpe/motpe/gp) builds and maps to the right Optuna class
  • aliases resolve (nsgaiii→NSGA-III, gpbo→GP, cma→CMA-ES)
  • cmaes is REFUSED on the 3-objective study (it is single-objective + continuous-only, Stage-B of P3)
  • an unknown sampler name raises a clear ValueError listing the choices
  • the default is nsga3 ⇒ byte-identical to every prior run
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")  # silence Optuna ExperimentalWarning noise during the asserts

from optimize import optimizer as O

_CF = lambda t: t.user_attrs.get("constraint", [1.0])   # any constraints_func works; sampler-agnostic


def test_multi_objective_brains_build():
    expect = {"nsga3": "NSGAIIISampler", "nsga2": "NSGAIISampler",
              "tpe": "TPESampler", "motpe": "TPESampler", "gp": "GPSampler"}
    for nm, cls in expect.items():
        got = type(O.make_sampler(nm, 1, _CF, n_objectives=3)).__name__
        assert got == cls, f"{nm}: expected {cls}, got {got}"


def test_aliases_resolve():
    assert type(O.make_sampler("nsgaiii", 1, _CF, n_objectives=3)).__name__ == "NSGAIIISampler"
    assert type(O.make_sampler("gpbo", 1, _CF, n_objectives=3)).__name__ == "GPSampler"
    assert type(O.make_sampler("cma", 1, _CF, n_objectives=1)).__name__ == "CmaEsSampler"


def test_cmaes_refused_on_multi_objective():
    try:
        O.make_sampler("cmaes", 1, _CF, n_objectives=3)
    except ValueError as e:
        assert "single-objective" in str(e).lower() or "SINGLE-objective" in str(e)
        return
    raise AssertionError("cmaes must be refused on a >1-objective study")


def test_cmaes_allowed_single_objective():
    assert type(O.make_sampler("cmaes", 1, _CF, n_objectives=1)).__name__ == "CmaEsSampler"


def test_unknown_sampler_raises():
    try:
        O.make_sampler("banana", 1, _CF, n_objectives=3)
    except ValueError as e:
        assert "unknown sampler" in str(e) and "banana" in str(e)
        return
    raise AssertionError("unknown sampler must raise ValueError")


def test_default_is_nsga3():
    # the run() / make_sampler default must stay NSGA-III so prior runs reproduce byte-for-byte
    assert type(O.make_sampler(None, 1, _CF, n_objectives=3)).__name__ == "NSGAIIISampler"
    assert O.SAMPLER_CHOICES[0] == "nsga3"


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"P2 SAMPLER-FACTORY OK — {len(tests)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
