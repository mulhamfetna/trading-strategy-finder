"""FastAPI backend for the live dashboard (replaces Dash from old iter 8).

Phase A of the FastAPI + Vue migration. See
docs/superpowers/specs/2026-05-22-fastapi-vue-migration-design.md.
"""

from src.api.app import app

__all__ = ['app']
