"""Pure-function template renderer.

Used by `src/main/ultimate_dashboard.py` to keep static HTML out of Python
source. Placeholders use ``{{NAME}}`` syntax with names matching
``[A-Z_][A-Z0-9_]*``.

This module is intentionally FP (a single pure function): no state, no
class, no I/O beyond the one ``read_text`` call. The refactor policy in
`docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md`
recommends FP for pure transforms.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


def render_template(template_path: Path, values: Mapping[str, object]) -> str:
    """Load ``template_path`` and substitute ``{{NAME}}`` placeholders.

    Args:
        template_path: Path to a UTF-8 text template file.
        values: Mapping from placeholder name to replacement value.
            Values are converted to ``str`` lazily.

    Returns:
        Rendered template content.

    Raises:
        FileNotFoundError: ``template_path`` does not exist.
        KeyError: Template references a placeholder name that is not in
            ``values``.
    """
    template_path = Path(template_path)
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")

    referenced = set(_PLACEHOLDER_RE.findall(template))
    missing = referenced - set(values)
    if missing:
        raise KeyError(
            f"Template placeholders without values: {sorted(missing)}"
        )

    # Single-pass substitution via re.sub so a replacement value containing
    # another placeholder is NOT re-substituted. (A naive
    # ``str.replace`` loop would re-substitute.)
    def _sub(match: re.Match) -> str:
        return str(values[match.group(1)])

    return _PLACEHOLDER_RE.sub(_sub, template)
