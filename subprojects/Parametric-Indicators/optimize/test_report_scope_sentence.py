"""A generated report must describe the search it actually ran — never assert a scope from a literal.

THE DEFECT THIS LOCKS OUT (#89 sweep, 2026-07-31). `report_wsi._write_md` opened every generated report
with the sentence:

    Search = box params + all 15 indicators on/off + their params + K.

"15" was a literal, correct on the day it was typed. The registry then grew to 18, and then to 165, and
the sentence never moved. Worse, it is wrong in the OTHER direction too: campaigns that deliberately
restrict the search with `--only-indicators` still got a report claiming "all". The wshgap4 report
rescued from the server on 2026-07-31 says "all 15 indicators" for a run that searched the original
**18** under an explicit scope — a report describing a search that never happened, in a file whose whole
job is to be the durable record of what happened.

This is the reporting face of the same defect the trial budget had (#2): a number about the search,
computed from something other than the search.
"""
import os

import pytest

from indicators import library
from optimize import report_wsi as R

ORIGINAL_18 = list(library.REGISTRY)[:18]


@pytest.fixture(autouse=True)
def _clean_scope_env(monkeypatch):
    """The scope travels by environment (WSH_ONLY/WSH_EXCLUDE — the channel remote_wsi.sh exports), so
    every case must start from a known-empty one or it inherits the developer's shell."""
    monkeypatch.delenv("WSH_ONLY", raising=False)
    monkeypatch.delenv("WSH_EXCLUDE", raising=False)


def test_unscoped_run_reports_the_registry_size_not_a_literal():
    s = R._scope_sentence()
    assert str(len(library.REGISTRY)) in s
    assert "15 indicators" not in s, "the hardcoded 15 is back"


def test_only_indicators_is_reported_as_a_restriction_not_as_all():
    os.environ["WSH_ONLY"] = ",".join(ORIGINAL_18)
    s = R._scope_sentence()
    assert s.startswith("18 of "), s
    assert "all" not in s, "a restricted search must never be described as 'all'"
    assert "--only-indicators" in s, "the report must say HOW the search was restricted"


def test_exclude_indicators_shrinks_the_reported_count():
    os.environ["WSH_EXCLUDE"] = ",".join(ORIGINAL_18[:5])
    s = R._scope_sentence()
    assert s.startswith(f"{len(library.REGISTRY) - 5} of ")
    assert "--exclude-indicators" in s


def test_only_and_exclude_compose_in_the_sentence():
    os.environ["WSH_ONLY"] = ",".join(ORIGINAL_18)
    os.environ["WSH_EXCLUDE"] = ",".join(ORIGINAL_18[:3])
    s = R._scope_sentence()
    assert s.startswith("15 of "), s
    assert "--only-indicators" in s and "--exclude-indicators" in s


def test_the_sentence_agrees_with_the_optimizer_that_will_run():
    """The report and the optimizer must resolve the scope through the SAME function. If the report
    counted the scope its own way, the two could disagree — which is how "all 15" survived in the first
    place."""
    from optimize import optimizer as OPT
    os.environ["WSH_ONLY"] = ",".join(ORIGINAL_18)
    n = len(OPT.searchable_indicators(tuple(ORIGINAL_18), ()))
    assert R._scope_sentence().startswith(f"{n} of ")


def test_a_typo_in_the_scope_cannot_inflate_the_reported_count():
    """Same rule the budget follows: an indicator that does not exist is not a searched dimension, so it
    must not appear in the count the report publishes."""
    os.environ["WSH_ONLY"] = ",".join(ORIGINAL_18 + ["not_a_real_indicator"])
    assert R._scope_sentence().startswith("18 of ")
