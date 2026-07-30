"""A MAP-Elites genome must look like a strategy we would trade, at ANY registry size.

THE BUG THIS LOCKS OUT (#81). The bootstrap genome was built with a fixed PROBABILITY:

    en = {k: (rng.random() < 0.4) for k in library.REGISTRY}

which makes the genome's size a function of how big the registry happens to be. At **18** indicators
that meant "about 7 enabled" — a realistic strategy. At **165** it means "about 66", which is nothing we
would ever deploy: our champions use **3–10**.

Mutation had the same shape of defect — a fixed "toggle 1–2 bits" moved ~8% of an 18-indicator genome
and ~1% of a 165-indicator one, silently weakening ~9x when the library grew.

Measured before the fix, simulating the genome dynamics over a standard 400-evaluation run: with 18
indicators the archive spanned 0–15 enabled and covered the champion region; with 165 it spanned
**50–83 and never reached it**. Starting at ~66 and moving ±1 per mutation, you cannot walk to ~5 within
any realistic budget — so MAP-Elites could not find strategies shaped like the ones we actually run.

The fix samples a COUNT and then chooses which indicators, and mutates a FRACTION of the genome. Both
are registry-size independent, so they stay correct the next time the library grows.
"""
import random

import pytest

from indicators import library
from optimize import map_elites as ME

SPACE = {"x": (0.0, 1.0, False)}          # continuous knobs are irrelevant to genome shape


def _n_on(en):
    return sum(1 for k in library.REGISTRY if en[k])


@pytest.mark.parametrize("seed", range(8))
def test_bootstrap_genome_is_a_plausible_strategy(seed):
    """A random genome must have a champion-like number of indicators, not ~40% of the library."""
    en, _flip, _cont = ME._rand_geno(None, SPACE, random.Random(seed))
    n = _n_on(en)
    lo, hi = ME.RAND_N_IND
    assert lo <= n <= hi, f"bootstrap genome enabled {n} indicators, expected {lo}..{hi}"
    assert n < 0.4 * len(library.REGISTRY), (
        f"{n} enabled is the old probability-based shape — the whole point is that genome size must not "
        f"scale with the registry ({len(library.REGISTRY)} indicators)")


def test_genome_size_does_not_track_registry_size():
    """The regression, stated directly: doubling the registry must NOT double the genome."""
    rng = random.Random(0)
    sizes = [_n_on(ME._rand_geno(None, SPACE, rng)[0]) for _ in range(50)]
    assert max(sizes) <= ME.RAND_N_IND[1]
    # the old code would average ~0.4 * 165 = 66
    assert sum(sizes) / len(sizes) < 20, f"mean enabled {sum(sizes)/len(sizes):.1f} — far too many"


def test_mutation_moves_a_fraction_not_a_fixed_bit_count():
    rng = random.Random(1)
    en, flip, cont = ME._rand_geno(None, SPACE, rng)
    expected = max(1, round(ME.MUT_FRAC * len(library.REGISTRY)))
    changed = []
    for _ in range(30):
        m_en, _, _ = ME._mutate((en, flip, cont), SPACE, rng)
        changed.append(sum(1 for k in library.REGISTRY if m_en[k] != en[k]))
    assert min(changed) >= 1, "a mutation must change at least one indicator"
    assert max(changed) <= expected + 1, f"mutation changed up to {max(changed)} bits, expected ~{expected}"
    assert expected > 2, (
        "with 165 indicators a mutation should move more than the legacy 1-2 bits, or the operator is "
        "~9x weaker than when it was tuned at 18")


def _reachable(seed, n_evals=400):
    """Simulate the archive's indicator-count coverage using the REAL genome operators."""
    rng = random.Random(seed)
    archive = {}

    def consider(g):
        n = _n_on(g[0])
        if n not in archive:
            archive[n] = g
            return True
        return False

    n_boot = min(max(10, n_evals // 10), n_evals)
    for _ in range(n_boot):
        consider(ME._rand_geno(None, SPACE, rng))
    ev = n_boot
    while ev < n_evals:
        consider(ME._mutate(rng.choice(list(archive.values())), SPACE, rng))
        ev += 1
    return min(archive), max(archive)


@pytest.mark.parametrize("seed", range(4))
def test_archive_reaches_the_region_our_champions_live_in(seed):
    """THE TEST THAT MATTERS. Deployed champions use 3-10 indicators. Before the fix the archive spanned
    50-83 and never came close — the search could not represent a strategy we would trade."""
    lo, _hi = _reachable(seed)
    assert lo <= 10, (
        f"archive's simplest strategy has {lo} indicators; our champions use 3-10, so the search cannot "
        f"reach them (this is exactly the #81 defect)")


def test_old_probability_shape_would_fail_this():
    """Guards the REASON for the fix, so nobody 'simplifies' back to a fixed probability."""
    rng = random.Random(0)
    old = {k: (rng.random() < 0.4) for k in library.REGISTRY}
    n_old = _n_on(old)
    assert n_old > 40, "expected the legacy 0.4 probability to enable dozens of indicators at 165"
    lo, hi = ME.RAND_N_IND
    assert not (lo <= n_old <= hi), "the legacy shape must NOT satisfy the new genome-size contract"
