"""Project-wide custom exceptions.

Implements the no-fallback rule (see docs/CODING_RULES.md):
every internal code path that would silently fall back to a default
value must raise ConfigurationError instead, carrying a structured
system_status payload that the SSE / HTTP layers can ship to the
client.

Two layers of failure surface:

1. **API boundary** — handled by Pydantic's ValidationError. Missing
   fields in incoming requests raise ValidationError automatically;
   the FastAPI exception handler wraps each one with a system-status
   payload (current request body + env summary) and returns 422.

2. **Internal code** — anywhere code would have read a default
   (`getattr(x, 'name', default)`, `dict.get(k, default)`, `value or
   fallback`), raise ConfigurationError with an explicit code, message,
   and the system state at the moment of failure.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


class ConfigurationError(Exception):
    """A required value is missing and the no-fallback rule forbids defaults.

    Always supply:
      - code: a short kebab-case identifier (e.g. "missing-param",
        "missing-data-file"). Stable; safe to grep for.
      - message: one human-readable sentence.
      - system_status: a dict capturing whatever context helps debugging
        — current params, file paths checked, request body, etc.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        system_status: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.system_status: Dict[str, Any] = dict(system_status or {})
        super().__init__(self._format())

    def _format(self) -> str:
        body = json.dumps(self.system_status, default=str, indent=2, sort_keys=True)
        return f"[{self.code}] {self.message}\nSystem status:\n{body}"

    def to_payload(self) -> Dict[str, Any]:
        """Serialisable shape for SSE `event: error` frames and HTTP 422 bodies."""
        return {
            'code': self.code,
            'message': self.message,
            'system_status': self.system_status,
        }


class MissingParameterError(ConfigurationError):
    """Raised when a strategy parameter is absent from a dataclass / dict /
    request that should have provided it. Distinct subclass so callers can
    differentiate 'user forgot to set X' from other configuration faults."""

    def __init__(
        self,
        param: str,
        *,
        where: str,
        system_status: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            f"Required parameter '{param}' is missing at {where}; the no-fallback "
            "rule forbids substituting a default.",
            code='missing-parameter',
            system_status={'param': param, 'where': where, **(system_status or {})},
        )


class MissingDataFileError(ConfigurationError):
    """Raised when a CSV the engine needs cannot be located. Distinct from
    MissingParameterError because the value WAS provided — the file just
    isn't there."""

    def __init__(
        self,
        path: str,
        *,
        role: str,
        system_status: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            f"Data file for '{role}' not found at {path!r}.",
            code='missing-data-file',
            system_status={'role': role, 'path': path, **(system_status or {})},
        )
