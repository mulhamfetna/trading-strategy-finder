import sys
from pathlib import Path

# Make the subproject root importable (indicators/, engine.py, ...).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
