"""Kalman / signal-fusion STUDY package (research only, off the production optimize/ path).

Imports the parity-locked engine as a library to (a) compute the M0 ceiling and (b) evaluate
admit/direction policies for M1/M2/M3. Never modifies optimize/. See
docs/superpowers/specs/2026-07-01-kalman-signal-fusion-study-design.md.
"""
from __future__ import annotations
import sys
from pathlib import Path

# subproject root (…/Parametric-Indicators) on sys.path so `optimize`/`config` import.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
