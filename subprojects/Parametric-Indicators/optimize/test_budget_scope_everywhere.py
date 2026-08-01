"""EVERY place that sizes a search must size the search it is actually launching.

THE DEFECT THIS LOCKS OUT, and why this file is phrased as a sweep rather than a case (#89).

`--auto-trials` budgets a run as `total_dimensions x TRIALS_PER_DIM`. When a run is restricted with
`--only-indicators`, the dimension count must shrink with it. That was fixed once, in
`optimizer.main()` — and then found again, and again, and again:

    1. optimizer.main()              --auto-trials over-budgeted 8x            (#2, fixed)
    2. control.plan()/preview        the UI showed 47,100 for a 5,900 search   (fixed)
    3. runner.target_trials()        the WATCHDOG chased 47,000 vs 5,800       (#89 sweep, fixed)
    4. remote_wsi.sh cmd_run()       the server launcher, same computation     (#89 sweep, fixed)

Four sites, one defect, found one at a time over two days. **Fixing a bug at one call site is not
fixing the bug.** So this test does not check a call site; it enumerates every consumer that resolves a
budget and asserts they all agree with the spec — which is the only way a fifth site gets caught on the
day it appears rather than months later.

The 8x matters concretely: ~20 hours per study instead of ~45 minutes, and a watchdog that respawns the
optimizer chasing a target the search was never sized for.
"""
import pytest

from indicators import library
from optimize import optimizer as OPT
from optimize import run_spec as RS
from optimize.dashboard import control, runner

ORIGINAL_18 = list(library.REGISTRY)[:18]

SCOPES = [
    ("full registry", {}),
    ("only the original 18", {"only_indicators": ORIGINAL_18}),
    ("only three", {"only_indicators": ORIGINAL_18[:3]}),
    ("exclude five", {"exclude_indicators": ORIGINAL_18[:5]}),
    # #95 — THE FIFTH INSTANCE, and the one this file was blind to. Every scope above runs WITHOUT
    # cross-instrument contributors, so the missing contributor term could not fail any of them. The
    # committee is a second full-registry search that roughly DOUBLES the space; `search_dims` had no
    # term for it at all, so `--contributors ES --plan` reported the same 470 dimensions with and
    # without the block, and --auto-trials sized every contributor run for about half its own space.
    #
    # Found by trying to size the two arms of the #95 comparison: both printed IDENTICAL dimensions,
    # which cannot be true, because the arms differ by exactly eight committee keys.
    ("with an ES contributor", {"contributors": ("ES",)}),
    ("contributor, committee scoped", {"contributors": ("ES",),
                                       "contrib_exclude": tuple(ORIGINAL_18[:8])}),
]


def _cfg(scope: dict, **extra) -> dict:
    return {"timeframes": ["4h"], **scope, **extra}


@pytest.mark.parametrize("label,scope", SCOPES, ids=[s[0] for s in SCOPES])
def test_every_budget_consumer_agrees(label, scope):
    """THE SWEEP. The spec, the UI plan, and the watchdog target must all resolve to the same number."""
    cfg = _cfg(scope)
    spec = runner.spec_for(cfg, "4h").effective_trials()
    plan = control.plan(cfg)["recommended_trials"]
    watchdog = runner.target_trials(cfg, "4h")
    assert spec == plan == watchdog, (
        f"{label}: budget consumers disagree — spec={spec:,} plan={plan:,} watchdog={watchdog:,}. "
        f"Every one of these has been an 8x over-budget at some point; they must resolve identically.")


@pytest.mark.parametrize("label,scope", SCOPES, ids=[s[0] for s in SCOPES])
def test_budget_tracks_the_indicator_scope(label, scope):
    """A narrower search must cost less. The whole class of bug is a budget that ignores the scope."""
    spec = RS.from_cfg(_cfg(scope), "4h")
    expected = OPT.recommended_trials(False, only_inds=tuple(scope.get("only_indicators", ())),
                                      exclude_inds=tuple(scope.get("exclude_indicators", ())),
                                      contrib_tokens=tuple(scope.get("contributors", ())),
                                      contrib_exclude=tuple(scope.get("contrib_exclude", ())))
    assert spec.effective_trials() == expected
    n_searched = spec.indicators_searched()
    if n_searched < len(library.REGISTRY):
        full = OPT.recommended_trials(False)
        assert spec.effective_trials() < full, (
            f"{label}: searching {n_searched}/{len(library.REGISTRY)} indicators but charged the "
            f"full-registry budget")


def test_the_watchdog_cannot_chase_a_target_the_run_is_not_sized_for():
    """The specific #89-sweep regression: target_trials ignored the scope, so a scoped run was given an
    8.1x target (47,000 vs 5,800) and the watchdog would keep respawning to reach it."""
    cfg = _cfg({"only_indicators": ORIGINAL_18})
    assert runner.target_trials(cfg, "4h") == runner.spec_for(cfg, "4h").effective_trials()
    assert runner.target_trials(cfg, "4h") < OPT.recommended_trials(False)


def test_explicit_trial_count_is_honoured_by_all_consumers():
    """An operator who pins a number gets it everywhere — scoping must not silently override a choice."""
    cfg = _cfg({"only_indicators": ORIGINAL_18}, trials_mode="one", trials=250)
    assert runner.spec_for(cfg, "4h").effective_trials() == 250
    assert runner.target_trials(cfg, "4h") == 250


def test_no_module_resolves_a_budget_without_the_scope():
    """The net for a FIFTH site. Any call to `recommended_trials` outside optimizer.py/run_spec.py must
    pass the indicator scope, or it is reintroducing the defect.

    Uses the AST, not a regex. A regex over source text produced five false positives on the first
    attempt: `stage_a_recommended_trials(...)` is a different function that merely ends with the same
    name, and one 'offender' was the word appearing inside a DOCSTRING that documents this very bug.
    Parsing means the check sees calls, not text — no substring collisions, and comments and strings
    are invisible to it.
    """
    import ast
    import pathlib

    offenders = []
    for rel in ("optimize/dashboard/control.py", "optimize/dashboard/runner.py",
                "optimize/two_stage.py", "optimize/map_elites.py"):
        p = pathlib.Path(rel)
        if not p.exists():
            continue
        for node in ast.walk(ast.parse(p.read_text())):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name != "recommended_trials":            # exact — not stage_a_recommended_trials
                continue
            kw = {k.arg for k in node.keywords}
            if not ({"only_inds", "exclude_inds"} & kw):
                offenders.append(f"{rel}:{node.lineno}: recommended_trials(...) with no indicator scope")
    assert not offenders, (
        "these resolve a trial budget without the indicator scope — the 8x defect, again:\n  "
        + "\n  ".join(offenders))


def test_a_contributor_run_costs_MORE_than_the_same_run_without_one():
    """The contributor committee is a second full-registry search. If adding one does not raise the
    budget, the budget is not seeing it — which is exactly the state this file was written to end."""
    plain = OPT.recommended_trials(False)
    withes = OPT.recommended_trials(False, contrib_tokens=("ES",))
    assert withes > plain, "adding an ES contributor did not change the budget at all"
    assert withes > 1.8 * plain, (
        f"the committee roughly doubles the space, but the budget only moved {plain:,} -> {withes:,}")


def test_scoping_the_COMMITTEE_shrinks_the_budget_too():
    """The #95 comparison needs this to be true: its two arms differ ONLY by eight committee keys, and
    a plan that cannot price that difference cannot size the comparison."""
    full = OPT.recommended_trials(False, contrib_tokens=("ES",))
    scoped = OPT.recommended_trials(False, contrib_tokens=("ES",),
                                    contrib_exclude=tuple(ORIGINAL_18[:8]))
    assert scoped < full, "excluding committee keys did not shrink the contributor dimensions"


def test_the_contributor_term_is_zero_when_there_are_no_contributors():
    """Byte-identical to every prior non-contributor run — the new term must not move an existing plan."""
    assert OPT.search_dims(False)["contributors"] == 0
    assert OPT.search_dims(False)["total"] == OPT.search_dims(False, contrib_tokens=())["total"]
