"""Tests that current documentation doesn't reference removed/renamed paths.

Excludes archives and historical reports - those are meant to describe
old state. The test enforces that current top-level docs only describe
the current invocation paths and output layout.
"""

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


REPO_ROOT = Path(__file__).resolve().parents[1]


# Files we exclude from the freshness check.
ARCHIVED_OR_HISTORICAL = {
    'docs/legacy',
    'docs/V1-FROZEN.md',
    'docs/2026-05-21-todo-status-report.md',  # describes WHAT changed; cites old paths
    'docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md',  # same
    'docs/superpowers/plans',
    'docs/superpowers/specs',  # contains historical specs (phase1, dashboard-candlestick)
    'docs/revisions/REVISION_LOG.md',
    'docs/revisions/LESSONS_LEARNED.md',
    'docs/bug-checklist-revision-history.md',
    'docs/fixes-needed-report-2026-05-21.md',
    'docs/reviewer-playbook-segmented.md',
    'docs/ultimate_trading_dashboard_review_v3.md',
    'docs/COMPLETE-DOCUMENTATION.md',  # long-form, not router-quality; tracked separately
    'docs/PLAYBOOK.md',
    'docs/API.md',
}


CURRENT_DOC_PATHS = [
    'AGENTS.md',
    'README.md',
    'docs/MASTER_DOCUMENTATION.md',
]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding='utf-8')


def test_master_documentation_router_references_tutorials_not_interview_preparation():
    """docs/MASTER_DOCUMENTATION.md must reference docs/Tutorials/ (the
    current location), not the removed docs/interview_preparation/."""
    content = _read('docs/MASTER_DOCUMENTATION.md')
    assert 'docs/Tutorials/' in content
    assert 'docs/interview_preparation/' not in content


def test_master_documentation_router_references_output_not_docs_for_artifacts():
    """Generated artifacts now live under output/, not docs/."""
    content = _read('docs/MASTER_DOCUMENTATION.md')
    # output/dashboards/ should appear
    assert 'output/dashboards/' in content
    # The stale paths must not appear
    assert 'docs/ultimate_trading_dashboard.html' not in content
    assert 'docs/dashboard_data.json' not in content
    assert 'docs/live_trading_dashboard.html' not in content


def test_master_documentation_router_lists_iter_artifacts():
    """The router must point to the iter sequencing design, the iter
    runner (src/main/run_strategy.py), and the renderer/template files
    added during iters 1-5."""
    content = _read('docs/MASTER_DOCUMENTATION.md')
    assert 'src/main/run_strategy.py' in content
    assert 'templates/ultimate_dashboard.html.tpl' in content
    assert 'src/dashboard/template_renderer.py' in content
    assert 'src/backtest/engine.py' in content


def test_readme_uses_module_invocation_pattern():
    """README must show `python3 -m src.main.X` invocations after the
    entry scripts moved into src/main/ (commit cf904c9)."""
    content = _read('README.md')
    # Not the old bare paths
    assert 'python3 ultimate_dashboard.py' not in content
    assert 'python3 main.py' not in content
    # The current pattern
    assert 'python3 -m src.main.' in content


def test_project_documentation_main_entrypoints_reflect_src_main_path():
    """Project_Documentation/<entry>.py.doc.md files describe the current
    location (src/main/), not the removed root-level path."""
    for entry in ('main.py', 'ultimate_dashboard.py', 'fast_optimizer.py', 'live_dashboard.py'):
        doc = _read(f'Project_Documentation/{entry}.doc.md')
        # The doc must mention src/main/<entry>.
        assert f'src/main/{entry}' in doc, (
            f"Project_Documentation/{entry}.doc.md does not reference "
            f"the current src/main/{entry} path"
        )
        # Should NOT advertise the old bare CLI invocation as primary.
        assert f'python3 {entry}' not in doc, (
            f"Project_Documentation/{entry}.doc.md still suggests the "
            f"old `python3 {entry}` invocation; should be "
            f"`python3 -m src.main.{entry[:-3]}`"
        )


def test_current_docs_no_stale_interview_preparation_references():
    """Top-level current docs must not link to docs/interview_preparation/
    (that directory was renamed to docs/Tutorials/ on 2026-05-22)."""
    for rel in CURRENT_DOC_PATHS:
        content = _read(rel)
        assert 'docs/interview_preparation/' not in content, (
            f"{rel} still references the removed docs/interview_preparation/ "
            f"directory; use docs/Tutorials/"
        )
