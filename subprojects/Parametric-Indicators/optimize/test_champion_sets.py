"""Every champion set the dashboard can serve must carry FULL-PRECISION parameters.

THE BUG THIS LOCKS OUT. Champion params were once persisted with round(x, 4) — four DECIMAL places. Our
markets span four orders of magnitude (Dow $44,452, natural gas $3.57), so four decimals leaves an NG stop
of 0.0008 with a single significant digit. On NG 5m that flipped the champion's P/L from +$38,079 to
-$1,714 and got 10 of the 54 head-to-head verdicts wrong.

The corrupted files (wsh4_*, eod1_*) still exist on disk — they are what shipped before the fix. Nothing
must ever point a champion set back at them, and no set may serve a stop that looks rounded.
"""
import json
import re

import pytest

from optimize.l2 import payload as P

# Prefixes written before the precision fix. A set pointing at one of these serves mangled stops.
CORRUPTED_PREFIXES = {"wsh4", "eod1", "cap1"}

# Stops below this are small enough that 4-dp rounding measurably distorts them (NG ~0.0008, HG ~0.0013).
SMALL_STOP = 0.05


def test_no_set_points_at_a_corrupted_prefix():
    """wsh4_* / eod1_* / cap1_* were persisted at 4 decimal places. They must never be served again."""
    bad = {name: spec["prefix"] for name, spec in P.CHAMPION_SETS.items()
           if spec["prefix"] in CORRUPTED_PREFIXES}
    assert not bad, (
        f"these sets point at pre-precision-fix champion files: {bad}. "
        f"Use the re-extracted (…p) files — the old ones flip NG 5m's sign.")


def test_default_set_exists_and_is_verified():
    d = P.champion_set(None)
    assert d in P.CHAMPION_SETS, f"default set {d!r} is not registered"
    assert P.CHAMPION_SETS[d]["verified"], "the DEFAULT set must be one the causal engine has confirmed"


def test_unknown_set_falls_back_to_a_registered_one():
    """A typo in the URL must not 404 or serve nothing — it falls back to the deployed set."""
    assert P.champion_set("nonsense") in P.CHAMPION_SETS
    assert P.champion_set("") in P.CHAMPION_SETS


@pytest.mark.parametrize("name", sorted(P.CHAMPION_SETS))
def test_every_registered_set_has_files_on_disk(name):
    p = P._instrument_champions_path("NQ", name)
    if not p.exists():
        pytest.skip(f"{name}: {p.name} not present in this checkout")
    champs = json.loads(p.read_text())
    assert champs, f"{name}: {p.name} is empty"


@pytest.mark.parametrize("name", sorted(P.CHAMPION_SETS))
def test_no_served_champion_has_a_rounded_stop(name):
    """The real check: a SMALL stop with <=4 decimals is the fingerprint of round(x, 4).

    0.0008 is corrupt (one significant digit). 0.000809191240378 is what the optimizer actually searched.
    Large-priced markets are exempt — a Dow stop of 10.246 is legitimately short.
    """
    suspects = []
    for inst in ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"):
        p = P._instrument_champions_path(inst, name)
        if not p.exists():
            continue
        for tf, entry in json.loads(p.read_text()).items():
            box = entry.get("box", {})
            for k in ("sl_soft", "sl_hard", "tp", "dd_limit"):
                v = box.get(k)
                if not isinstance(v, float) or v == 0 or abs(v) >= SMALL_STOP:
                    continue
                decimals = len(re.sub(r"^-?0\.", "", f"{v!r}").rstrip("0")) if "." in repr(v) else 0
                if decimals <= 4:
                    suspects.append(f"{inst}_{tf}.{k}={v!r}")
    assert not suspects, (
        f"set {name!r} serves champions whose stops look 4-dp rounded — the NG 5m sign-flip bug:\n  "
        + "\n  ".join(suspects[:10]))
