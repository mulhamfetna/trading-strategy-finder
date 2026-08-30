"""Engine-root conftest (positioning audit 2026-08-29 §3.2).

`server-audit/` holds frozen historical copies of this tree (#94) and `shareable/` holds bundle snapshots with
their own engine.py/strategy.py. Neither is a test suite. `norecursedirs`/`--ignore` in pytest.ini were not
enough on their own (pytest 9 still collected the archive when started from this directory — measured), so
the exclusion is enforced here too, at the collection hook, with paths relative to this file.
"""
collect_ignore_glob = ["server-audit/*", "server-audit/**", "shareable/*", "shareable/**", "*.rsync-retired-*"]
