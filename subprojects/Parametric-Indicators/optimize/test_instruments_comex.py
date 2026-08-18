import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import instruments as inst

# The price data is server-only and gitignored, so a checkout may legitimately hold some instruments and
# not others (this machine has GC and SI but not HG/CL/NG). Asserting a file exists is then a statement
# about the MACHINE, not about the code — and a suite that fails for environmental reasons teaches people
# to ignore failures. The naming/shifted-box CONTRACT is still asserted for every token either way; only
# the on-disk existence check is skipped when the data is absent.


def _require(path: str, tok: str, what: str) -> None:
    if not os.path.exists(path):
        pytest.skip(f"{tok}: {what} not present in this checkout ({path}) — price data is server-only")


def test_tokens_include_comex():
    assert inst.TOKENS == ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")   # COMEX metals + NYMEX energy + CME


def test_point_values():
    assert inst.point_value("GC") == 100.0
    assert inst.point_value("SI") == 5000.0
    assert inst.point_value("HG") == 25000.0   # Copper, COMEX full (25,000 lbs · $/lb)
    assert inst.point_value("CL") == 1000.0    # Crude Oil, NYMEX full (1,000 bbl · $/bbl)
    assert inst.point_value("NG") == 10000.0   # Natural Gas, NYMEX full (10,000 MMBtu · $/MMBtu)


@pytest.mark.parametrize("tok", ["GC", "SI", "HG", "CL", "NG"])
def test_resolve_paths_use_shifted_box(tok):
    """GC/SI/HG/CL/NG (and ES) backtester must read the -1-workday-SHIFTED box, not the raw one.

    Parametrized so one absent instrument skips alone instead of hiding the other four — previously a
    single missing HG file aborted the whole loop before GC/SI/CL/NG were checked at all.
    """
    dec, minute, box = inst.resolve_paths(tok, "4h")
    # naming contract — always asserted, no data required
    assert dec.endswith(f"{tok}_4h.csv")
    assert minute.endswith(f"{tok}_1m.csv")
    assert box.endswith(f"{tok}_full_data_shifted.csv"), f"{tok} backtester must read the SHIFTED box"
    # existence — only meaningful where the data actually lives
    _require(dec, tok, "decision-frame CSV")
    _require(minute, tok, "1-minute CSV")
    _require(box, tok, "shifted box CSV")


def test_es_repointed_to_shifted_box():
    _, _, box = inst.resolve_paths("ES", "4h")
    assert box.endswith("ES_full_data_shifted.csv"), "ES must now read the shifted box (raw retired 2026-07-06)"
    _require(box, "ES", "shifted box CSV")
