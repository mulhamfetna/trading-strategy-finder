"""The optimizer must warm-start from the DEPLOYED champion set, not a hardcoded one.

THE BUG THIS LOCKS OUT (issue #2). `warm_start_seeds()` read `wsh4_champions_full*.json` by name. The
deployed set moved to `best_*` on 2026-07-14 and this was never updated, so every warm-started
re-optimization for the next fortnight seeded from a RETIRED set.

Why that is worse than it sounds: Optuna's warm start guarantees the returned front scores >= its seed.
The guarantee never broke — it kept holding against the wrong incumbent. So the run looked healthy and
its report read "+$52,443 vs deployed", while against the champions actually deployed the same trio was
$12,832 WORSE out-of-sample. A silent wrong baseline is invisible precisely because every internal
consistency check still passes.

These tests follow the resolver rather than any filename, so they survive the next set change too.
"""
import json

from optimize import optimizer
from optimize.l2 import payload as P

# Prefixes persisted before the precision fix; a seed taken from one of these is doubly wrong.
CORRUPTED_PREFIXES = {"wsh4", "eod1", "cap1"}


def test_seed_file_is_the_deployed_set_not_a_hardcoded_name():
    for inst in ("NQ", "GC", "ES"):
        got = optimizer._deployed_champion_file(inst)
        assert got is not None, f"{inst}: resolver returned nothing"
        assert got == P._instrument_champions_path(inst), (
            f"{inst}: warm start would seed from {got.name}, but the deployed set resolves to "
            f"{P._instrument_champions_path(inst).name}")


def test_seed_file_never_comes_from_a_retired_prefix():
    """The specific regression: seeding from wsh4_* while `best_*` is deployed."""
    for inst in ("NQ", "GC"):
        name = optimizer._deployed_champion_file(inst).name
        prefix = name.split("_champions_full")[0]
        assert prefix not in CORRUPTED_PREFIXES, (
            f"{inst}: warm start seeds from {name} — a pre-precision-fix / retired set. "
            f"Deployed is {P.DEFAULT_CHAMPION_SET!r}.")


def test_resolver_tracks_a_changed_default(monkeypatch):
    """Change the deployed set and the seed must follow it — no stale hardcoded filename."""
    before = optimizer._deployed_champion_file("NQ")
    monkeypatch.setattr(P, "DEFAULT_CHAMPION_SET", "incumbent")
    after = optimizer._deployed_champion_file("NQ")
    assert after != before, "seed file did not follow the deployed set when it changed"
    assert after.name.startswith(P.CHAMPION_SETS["incumbent"]["prefix"])


def test_deployed_seed_actually_exists_and_carries_a_box():
    """A resolver that points at a missing file degrades to the unfloored legacy path — catch that here
    rather than discovering it in an 8-hour run's results."""
    for inst in ("NQ", "GC"):
        f = optimizer._deployed_champion_file(inst)
        assert f.exists(), f"{inst}: deployed champion file {f.name} is missing"
        champs = json.loads(f.read_text())
        assert champs, f"{inst}: {f.name} is empty"
        for tf, entry in champs.items():
            assert entry.get("box"), f"{inst} {tf}: champion has no box to seed from"
