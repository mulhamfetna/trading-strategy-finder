"""Cross-instrument L2 contributor registry — the standard for adding QQQ/SQQQ (Spec §3).

A `Contributor` is a declarative bundle (token + candle/box/delivery sources + alignment kind) built
from `subprojects/all-stocks-signals/instruments.py` (the no-mix contract — the single place instrument
identity lives). Generic over instruments: nothing here special-cases ES beyond the one registry entry.
Part A registers ES (align='identity', exact grid). ETFs (align='as_of') are a later registry entry +
adapter — ZERO gate-logic change (Spec §3.3)."""
from __future__ import annotations

import importlib.util
import sys
import os
from dataclasses import dataclass
from pathlib import Path

# The parent trading repo root (override for the server migration via WSH_DATA_BASE; mirrors
# optimize/data._BASE). The instruments registry + delivery bundles live under it.
_TRADING = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_INST_PATH = _TRADING / "subprojects" / "all-stocks-signals" / "instruments.py"


def _load_instruments():
    """Load the no-mix instrument registry by file path (avoids polluting sys.path with the generic
    top-level module name 'instruments')."""
    spec = importlib.util.spec_from_file_location("ass_instruments", _INST_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ass_instruments"] = mod  # required for Python 3.14 dataclasses module lookup
    spec.loader.exec_module(mod)
    return mod


_instruments = _load_instruments()


@dataclass(frozen=True)
class Contributor:
    """One external contributor's data identity + how it aligns onto NQ's decision grid."""
    token: str          # instrument identifier (e.g. "ES")
    candle_dir: str     # dir holding <prefix>_<TF>.csv
    candle_prefix: str  # filename prefix (e.g. "ES")
    box_csv: str        # the unified per-instrument box file (_full_data.csv)
    delivery_dir: str   # <TOKEN>_SIGNALS_DELIVERY/2_holds_dropped (the delivered Stage-1 touch signal)
    align: str          # "identity" (exact grid, ES) | "as_of" (ETF) — Part A uses identity only
    tick_threshold: float = 0.75   # BoxLookup traversal tick band (repo-canonical 0.75)

    def candle_csv(self, tf: str) -> str:
        return os.path.join(self.candle_dir, f"{self.candle_prefix}_{tf}.csv")

    def delivery_csv(self, tf: str, preset: str = "full") -> str:
        return os.path.join(self.delivery_dir, f"{self.token}_{tf}_{preset}.csv")


def _from_instrument(token: str, align: str) -> Contributor:
    inst = _instruments.REGISTRY[token]
    delivery_dir = str(_TRADING / inst.delivery_name() / "2_holds_dropped")
    return Contributor(token=inst.token, candle_dir=inst.candle_dir,
                       candle_prefix=inst.candle_prefix, box_csv=inst.box_csv,
                       delivery_dir=delivery_dir, align=align)


# Part A: ES only. NQ is the host (contributor #0, identity decision grid) and needs no load here.
CONTRIBUTORS: dict[str, Contributor] = {
    "ES": _from_instrument("ES", align="identity"),
}


def get_contributor(token: str) -> Contributor:
    if token not in CONTRIBUTORS:
        raise KeyError(f"unknown contributor {token!r}; known: {sorted(CONTRIBUTORS)}")
    return CONTRIBUTORS[token]
