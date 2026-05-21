from __future__ import annotations

from pathlib import Path
from typing import Mapping


def render_template(template_path: Path, values: Mapping[str, object]) -> str:
    """Render a simple placeholder template using {{NAME}} tokens."""
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    rendered = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

    unresolved = [token for token in ("{{", "}}") if token in rendered]
    if unresolved:
        raise KeyError(f"Unresolved template placeholder in {template_path}")

    return rendered

