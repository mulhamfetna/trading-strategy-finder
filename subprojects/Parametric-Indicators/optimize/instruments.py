"""Parametric-Indicators instrument facade — the single place instrument identity + economics live for the
engine. Reuses the cross-subproject no-mix registry (subprojects/all-stocks-signals/instruments.py, the same
one optimize/l2/contributors/registry.py loads) and adds the point-value economics that registry lacks.

NQ resolves to the engine's EXISTING data paths (optimize/data._RAW / _BOX_CSV) so NQ stays byte-identical;
ES resolves through the registry (ALL_STOCKS/...). Default token is "NQ" everywhere."""
from __future__ import annotations

import functools
import importlib.util
import os
import sys
from pathlib import Path

import config                                   # noqa: E402 (top-level module on sys.path)
from optimize import timeframes as TF           # noqa: E402

# Mirror optimize/data.py's constants WITHOUT importing it (data.py imports this module → avoid a cycle).
_BASE = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_RAW = _BASE / TF.RAW_DIR
_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"
_INST_PATH = _BASE / "subprojects" / "all-stocks-signals" / "instruments.py"

TOKENS: tuple[str, ...] = ("NQ", "ES", "GC", "SI", "HG", "RTY", "YM")   # + COMEX metals (GC/SI/HG) + CME RTY/YM; ETFs deferred
POINT_VALUE: dict[str, float] = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "HG": 25000.0, "RTY": 50.0, "YM": 5.0}


def _load_registry():
    """Load the no-mix registry by file path (mirrors contributors/registry._load_instruments)."""
    spec = importlib.util.spec_from_file_location("ass_instruments", _INST_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ass_instruments"] = mod         # required for Python 3.14 dataclass module lookup
    spec.loader.exec_module(mod)
    return mod.REGISTRY


_REGISTRY = _load_registry()


def is_valid(token: str) -> bool:
    return token in TOKENS


def point_value(token: str) -> float:
    return POINT_VALUE.get(token, POINT_VALUE["NQ"])


def resolve_paths(token: str, tf: str) -> tuple[str, str, str]:
    """(decision_csv, minute_csv, box_csv) for token+tf. NQ → the engine's existing paths (byte-identical);
    ES → the ALL_STOCKS registry."""
    if token == "NQ":
        return (str(_RAW / f"NQ_{tf}.csv"), str(_RAW / "NQ_1m.csv"), str(_BOX_CSV))
    inst = _REGISTRY[token]
    return (inst.candle_csv(tf), inst.candle_csv("1m"), inst.box_csv)


@functools.lru_cache(maxsize=None)
def _ref_price(token: str) -> float:
    import pandas as pd
    dec_csv, _, _ = resolve_paths(token, "4h")
    df = pd.read_csv(dec_csv)
    col = "close" if "close" in df.columns else df.columns[4]
    return float(df[col].median())


def scale_factor(token: str) -> float:
    """inst_ref / NQ_ref (median 4h close). 1.0 for NQ. Used to price-scale the non-NQ permissive default."""
    if token == "NQ":
        return 1.0
    return _ref_price(token) / _ref_price("NQ")
