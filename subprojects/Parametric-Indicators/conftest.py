"""Engine-root conftest (positioning audit 2026-08-29 §3.2).

`server-audit/` holds frozen historical copies of this tree (#94) and `shareable/` holds bundle snapshots with
their own engine.py/strategy.py. Neither is a test suite. `norecursedirs`/`--ignore` in pytest.ini were not
enough on their own (pytest 9 still collected the archive when started from this directory — measured), so
the exclusion is enforced here too, at the collection hook, with paths relative to this file.
"""
collect_ignore_glob = ["server-audit/*", "server-audit/**", "shareable/*", "shareable/**", "*.rsync-retired-*"]


# ---------------------------------------------------------------------------------------------------------
# Market data is SERVER-ONLY since 2026-08-22 (docs/DATA-AND-KNOWLEDGE-MAP.md). A fresh clone has no candles,
# no boxes, no 16-year tape. The root suite already skips its data-dependent tests one by one; the engine
# suite has ~100 tests across ~35 files that open a data file and would otherwise FAIL on every machine but
# the server. Turning "the data file this test needs is not here" into a SKIP is the honest reading of that
# outcome: the test did not run, it did not fail. Any other FileNotFoundError still fails. The skip message
# names the missing path so the reason is on the record (positioning audit 2026-08-29 §3.2 / round 3).
# ---------------------------------------------------------------------------------------------------------
import re as _re

import pytest as _pytest

_DATA_PATH = _re.compile(r"(Full_Canldes_Data|/data/(20\d\d_data|full_data)|ALL_STOCKS/|_Continuous_Data/|data_2010_1s|/shifted_boxes/)")


@_pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when in ("setup", "call") and rep.failed and call.excinfo is not None:
        exc = call.excinfo.value
        if isinstance(exc, FileNotFoundError) and _DATA_PATH.search(str(exc)):
            rep.outcome = "skipped"
            rep.longrepr = (str(item.fspath), getattr(item, "location", (None, 0))[1] or 0,
                            f"Skipped: market data not present (server-only): {exc}")
