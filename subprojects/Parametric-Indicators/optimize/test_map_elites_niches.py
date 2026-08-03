"""The MAP-Elites archive must stay small enough to actually SELECT (#88).

WHY THESE ASSERTIONS EXIST. MAP-Elites keeps the best solution per niche. That only means anything if
each niche is visited more than once — the second visit is where "is the newcomer better than the
sitting elite?" gets asked. The old second axis was the RAW indicator count, so the archive's width
tracked the registry: 19 columns at 18 indicators (171 niches, ~2.3 evals each) became 166 columns at
165 (1,494 niches, ~0.27 each). Below one visit per niche the method degrades into "keep the FIRST
arrival", and it does so silently — the archive still comes back full and is still reported as a
portfolio of elites.

This is the same class as #81 and the four sites in #89: a constant that is really a RATIO, correct at
the size it was written for and quietly wrong afterwards. So the tests below pin the RATIO and the
registry-independence, not just the current numbers.

WHAT IS DELIBERATELY NOT TESTED HERE: whether the archive's contents are any good, and whether
MAP-Elites beats the ordinary search. This fixes the shape. Re-validating results produced under the
broken shape is #90.
"""
import inspect

from indicators import library
from optimize import map_elites as ME

STANDARD_EVALS = 400          # the default run size, and the budget every ratio below is judged against


# ── the axis itself ──────────────────────────────────────────────────────────────────────────────

def test_the_indicator_axis_is_bucketed_not_the_raw_count():
    """The defect in one assertion: two adjacent large counts must share a niche. A 61-indicator and a
    62-indicator strategy are not different KINDS of thing, and giving each its own niche is what stole
    the visits from the region that matters."""
    assert ME.ind_bucket(61) == ME.ind_bucket(62) == ME.ind_bucket(140)


def test_the_champion_region_keeps_fine_resolution():
    """Deployed champions use 3-10 indicators. Coarsening is only acceptable if it does NOT coarsen
    there — otherwise the fix trades one blindness for another."""
    assert len({ME.ind_bucket(n) for n in (3, 5, 8)}) == 3, "3-4 / 5-7 / 8-10 must stay distinct"
    assert ME.ind_bucket(0) != ME.ind_bucket(1), "'no indicators' is its own kind of strategy"


def test_every_count_lands_in_exactly_one_bucket_and_they_are_ordered():
    seen = [ME.ind_bucket(n) for n in range(0, 600)]
    assert min(seen) == 0 and max(seen) == ME.IND_BIN_CAP
    assert seen == sorted(seen), "buckets must be monotone in the count, or the axis is not an axis"
    assert len(set(seen)) == ME.IND_BIN_CAP + 1, "every bucket must be reachable"


def test_the_last_bucket_is_unbounded():
    """The catch-all is what makes the width fixed. Without it the axis grows with the library again."""
    assert ME.ind_bucket(51) == ME.ind_bucket(10_000) == ME.IND_BIN_CAP


# ── the ratio that actually broke ────────────────────────────────────────────────────────────────

def test_a_standard_run_visits_each_niche_several_times():
    """THE POINT. Below 1.0 the archive keeps first arrivals; the old shape sat at 0.27."""
    per_niche = STANDARD_EVALS / ME.N_NICHES
    assert per_niche >= 4.0, f"only {per_niche:.2f} evals per niche — selection barely happens"


def test_the_niche_count_is_the_product_of_both_capped_axes():
    assert ME.N_NICHES == (ME.DD_BIN_CAP + 1) * (ME.IND_BIN_CAP + 1) == 81


def test_the_archive_does_not_grow_when_the_library_grows():
    """Registry-independence BY CONSTRUCTION (playbook rules S2/S6). The old axis failed exactly here,
    and nothing announced it — which is why this is pinned rather than trusted."""
    assert len(library.REGISTRY) > 100, "sanity: this repo has the grown library"
    biggest = max(ME.ind_bucket(n) for n in (len(library.REGISTRY), 500, 5_000))
    assert biggest == ME.IND_BIN_CAP
    assert ME.N_NICHES == 81, "niche count must not depend on the registry at all"


def test_behavior_returns_a_bounded_coordinate_on_both_axes():
    for dd in (0.0, 1_999.0, 15_999.0, 250_000.0):
        for n in (0, 7, 165, 900):
            r, c = ME.behavior({"worst_dd": dd}, n)
            assert 0 <= r <= ME.DD_BIN_CAP and 0 <= c <= ME.IND_BIN_CAP


# ── the falsification instrumentation ────────────────────────────────────────────────────────────

def test_first_fills_and_improvements_are_counted_separately():
    """The pre-registered evidence for #88. The old code summed them into one 'improvements' number, so
    a run that never compared anything looked like a run that kept improving. Accepting into an EMPTY
    niche involves no comparison; only replacing a sitting elite does."""
    src = inspect.getsource(ME.run)
    assert '"first_fill": 0' in src and '"improvement": 0' in src
    assert 'stats["first_fill"] += 1' in src, "first-fills must be counted, not folded into improvements"
    assert 'stats["improvement"] += 1' in src
    # and both must survive to disk, or the run cannot be judged after the fact
    assert '"selection": dict(stats)' in src


def test_the_run_reports_evals_per_niche():
    """The number that silently went wrong must appear in the output. A ratio nobody prints is a ratio
    nobody notices going bad — that is precisely how this survived the 18 -> 165 growth."""
    src = inspect.getsource(ME.run)
    assert "evals/niche" in src
    assert "BELOW 1" in src, "a run in the degraded regime must say so out loud"


def test_saved_archives_are_labelled_by_niche_not_by_index():
    """Bin edges may move. Bare '(2, 3)' keys become meaningless the moment they do, so old result files
    would silently be misread as describing niches they never described."""
    assert ME.niche_label((0, 0)).startswith("dd $0")
    assert "51+" in ME.niche_label((ME.DD_BIN_CAP, ME.IND_BIN_CAP))
    assert "≥" in ME.niche_label((ME.DD_BIN_CAP, 0)), "the capped DD bucket must read as a bound"
    assert inspect.getsource(ME.run).count("niche_label(c)") == 1
