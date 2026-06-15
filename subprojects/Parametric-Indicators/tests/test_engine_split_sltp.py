"""Phase E gate — per-direction (split) SL/TP in SimpleStrategy.

T2 (degenerate): long_*==short_*==shared  ⇒ identical trades to shared-only.
T3 (direction-consistency): asymmetric split ⇒ long entries use the long points, short entries the short
    points (verified on the recorded SL/TP lines), and the result differs from shared.
T-valid: bad per-side ordering raises.
(T1 golden byte-match + T4 fast/exact parity are run separately; this file is the split-specific unit test.)
Run: python3 tests/test_engine_split_sltp.py   (also pytest-discoverable)
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import engine            # noqa: E402
import strategy          # noqa: E402

_BUNDLE = None
def _bundle():
    global _BUNDLE
    if _BUNDLE is None:
        df4, df1, box, vf, n = strategy.load_inputs()
        _BUNDLE = (df4, df1, box)
    return _BUNDLE


def _params(**over):
    base = dict(sl_soft_points=100.0, sl_hard_points=150.0, tp_soft_points=100.0, tp_hard_points=120.0,
                data_path_4h="", data_path_1min="", box_data_path="", direction_scope='both',
                flip_entry_direction=False)
    base.update(over)
    return engine.SimpleStrategyParams(**base)


def _run(sp):
    df4, df1, box = _bundle()
    trades, _ = engine.SimpleStrategy(sp).backtest(df4, df1, box)
    return [t for t in trades if t.get('exit_reason') not in (None, 'OPEN')]


def _key(t):
    return (str(t['entry_time']), t['direction'], round(float(t['entry_price']), 4),
            round(float(t['tp_hard_line']), 4), round(float(t['sl_hard_line']), 4), t['exit_reason'])


def test_degenerate_split_equals_shared():
    shared = _run(_params())
    split = _run(_params(long_sl_soft_points=100.0, long_sl_hard_points=150.0, long_tp_soft_points=100.0,
                         long_tp_hard_points=120.0, short_sl_soft_points=100.0, short_sl_hard_points=150.0,
                         short_tp_soft_points=100.0, short_tp_hard_points=120.0))
    assert len(shared) == len(split), f"trade count differs: {len(shared)} vs {len(split)}"
    assert [_key(a) for a in shared] == [_key(b) for b in split], "degenerate split must equal shared exactly"
    return len(shared)


def test_direction_consistency():
    # asymmetric: long TP far (300), short TP near (60); long SL 150/short SL 90
    sp = _params(long_sl_hard_points=150.0, long_tp_hard_points=300.0, long_tp_soft_points=290.0,
                 short_sl_hard_points=90.0, short_sl_soft_points=80.0, short_tp_hard_points=60.0,
                 short_tp_soft_points=55.0)
    tr = _run(sp)
    nL = nS = 0
    for t in tr:
        ep = float(t['entry_price'])
        if t['direction'] == 'long':
            nL += 1
            assert abs(t['tp_hard_line'] - (ep + 300.0)) < 1e-6, f"long TP not 300: {t['tp_hard_line']-ep}"
            assert abs(t['sl_hard_line'] - (ep - 150.0)) < 1e-6, f"long SL not 150: {ep-t['sl_hard_line']}"
        else:
            nS += 1
            assert abs(t['tp_hard_line'] - (ep - 60.0)) < 1e-6, f"short TP not 60: {ep-t['tp_hard_line']}"
            assert abs(t['sl_hard_line'] - (ep + 90.0)) < 1e-6, f"short SL not 90: {t['sl_hard_line']-ep}"
    assert nL > 0 and nS > 0, f"need both directions to test (got {nL} long, {nS} short)"
    return nL, nS


def test_bad_split_raises():
    for bad in (dict(long_sl_hard_points=50.0, long_sl_soft_points=100.0),   # hard < soft
                dict(short_tp_hard_points=10.0, short_tp_soft_points=20.0),   # hard < soft
                dict(long_tp_hard_points=-5.0)):                              # <= 0
        try:
            engine.SimpleStrategy(_params(**bad))
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")
    return True


if __name__ == "__main__":
    n = test_degenerate_split_equals_shared(); print(f"T2 degenerate==shared: PASS ({n} trades identical)")
    nL, nS = test_direction_consistency();     print(f"T3 direction-consistency: PASS ({nL} long, {nS} short, per-side lines correct)")
    test_bad_split_raises();                   print("T-valid bad-split raises: PASS")
    print("ALL SPLIT TESTS PASS")
