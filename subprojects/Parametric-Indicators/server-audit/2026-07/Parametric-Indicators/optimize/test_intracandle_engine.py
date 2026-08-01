import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from research.intracandle.champion_run import run_champion_exact  # noqa: E402


def test_off_is_champion_parity():
    base, s = run_champion_exact("4h", intracandle_veto_entry=False)
    assert len(base) == 214            # champion trade count (NQ 4h)
    assert s["pnl"] == 142203.0


def test_on_adds_entries():
    base, _ = run_champion_exact("4h", intracandle_veto_entry=False)
    more, _ = run_champion_exact("4h", intracandle_veto_entry=True, intracandle_max_wait=240)
    # Rescued vetoed signals ADD net entries. Not purely additive: a mid-candle entry occupies the position
    # and can reshape the later timeline (one-position-at-a-time), so we assert net growth + genuinely-new keys.
    assert len(more) > len(base)
    new = {t["entry_time"] for t in more} - {t["entry_time"] for t in base}
    assert len(new) > 0                # at least one genuinely-new intra-candle (rescued) entry
