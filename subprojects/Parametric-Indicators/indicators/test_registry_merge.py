import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators import library


def test_every_registry_key_has_schema_and_vice_versa():
    assert set(library.REGISTRY) == set(library.SCHEMA), (
        set(library.REGISTRY) ^ set(library.SCHEMA))


def test_school_modules_merge_in():
    # built-ins still present after refactor
    for k in ("ema_trend", "rsi", "adx"):
        assert k in library.REGISTRY and k in library.SCHEMA
