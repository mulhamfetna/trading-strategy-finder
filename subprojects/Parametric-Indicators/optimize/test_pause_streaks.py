import numpy as np

from optimize.pause_streaks import longest_run, pause_metrics, pause_totals, per_bar_cause


def test_longest_run():
    assert longest_run(np.array([0, 1, 1, 0, 1, 1, 1, 0], dtype=bool)) == 3
    assert longest_run(np.array([0, 0, 0], dtype=bool)) == 0
    assert longest_run(np.array([1, 1], dtype=bool)) == 2


def test_pause_metrics_decomposition():
    sig = np.array([0, 1, 0, 0, 1, 1, 0], dtype=int)    # candidates at idx 1,4,5
    volg = np.array([1, 0, 1, 1, 1, 1, 1], dtype=bool)  # idx1 vol-gated
    veto = np.array([0, 0, 0, 0, 1, 0, 0], dtype=bool)  # idx4 vetoed
    conf = np.array([1, 1, 1, 1, 1, 0, 1], dtype=bool)  # idx5 confirm<K (conf False)
    m = pause_metrics(sig, volg, veto, conf, bar_seconds=4 * 3600,
                      trade_spans=[(0, 6)])             # one trade idx0->6 (6 bars)
    assert m["box_silence"]["bars"] == 2                # idx2,3 run (idx6 trailing single)
    assert m["gate_noentry"]["bars"] == 1               # idx1
    assert m["indicator_noentry"]["bars"] == 2          # idx4 (veto) + idx5 (confirm) consecutive
    assert m["position_hold"]["bars"] == 6
    assert "days" in m["box_silence"]


def test_pause_totals_counts_and_invariant():
    sig = np.array([0, 1, 0, 0, 1, 1, 0], dtype=int)    # candidates at idx 1,4,5
    volg = np.array([1, 0, 1, 1, 1, 1, 1], dtype=bool)  # idx1 vol-gated
    veto = np.array([0, 0, 0, 0, 1, 0, 0], dtype=bool)  # idx4 vetoed
    conf = np.array([1, 1, 1, 1, 1, 0, 1], dtype=bool)  # idx5 confirm<K
    t = pause_totals(sig, volg, veto, conf, bar_seconds=4 * 3600, trade_spans=[(0, 6)])
    assert t["box_silence_total"]["bars"] == 4          # idx 0,2,3,6
    assert t["gate_noentry_total"]["bars"] == 1         # idx1
    assert t["indicator_noentry_total"]["bars"] == 2    # idx4 (veto) + idx5 (confirm<K)
    assert t["position_hold_total"]["bars"] == 6        # total bars in position (one 6-bar trade)
    assert t["noentry_total"]["bars"] == 7              # 4 + 1 + 2 (invariant)
    assert t["noentry_total"]["bars"] == (t["box_silence_total"]["bars"]
                                          + t["gate_noentry_total"]["bars"]
                                          + t["indicator_noentry_total"]["bars"])
    assert "days" in t["noentry_total"] and "hours" in t["position_hold_total"]


def test_per_bar_cause_partition():
    # every bar attributed to exactly one cause
    sig = np.array([0, 1, 1, 1, 0], dtype=int)
    volg = np.array([1, 0, 1, 1, 1], dtype=bool)
    veto = np.array([0, 0, 1, 0, 0], dtype=bool)
    conf = np.array([1, 1, 1, 1, 1], dtype=bool)
    bs, gb, ib, we = per_bar_cause(sig, volg, veto, conf)
    cover = bs.astype(int) + gb.astype(int) + ib.astype(int) + we.astype(int)
    assert (cover == 1).all()


def test_edges_no_signal_and_all_signal():
    n = 5
    none = np.zeros(n, dtype=int)
    alls = np.ones(n, dtype=int)
    g = np.ones(n, dtype=bool)
    no_veto = np.zeros(n, dtype=bool)
    yes_conf = np.ones(n, dtype=bool)
    m_none = pause_metrics(none, g, no_veto, yes_conf, bar_seconds=14400)
    assert m_none["box_silence"]["bars"] == n
    assert m_none["position_hold"]["bars"] == 0          # no trades
    m_all = pause_metrics(alls, g, no_veto, yes_conf, bar_seconds=14400)
    assert m_all["box_silence"]["bars"] == 0             # always a signal
