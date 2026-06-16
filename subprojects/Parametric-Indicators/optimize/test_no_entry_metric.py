"""S0 unit lock — no_entry_metrics (warmup-vs-decision attribution). Run: python3 -m pytest optimize/test_no_entry_metric.py -q"""
from optimize.no_entry import no_entry_metrics


def test_basic_gap_and_decision_split():
    # entries at bars 0,10,50,55 over 100 bars; warmup boundary at 12 decision bars; 4h => 6 bars/day
    m = no_entry_metrics([0, 10, 50, 55], n_bars=100, warmup_decision_bars=12, bar_hours=4.0)
    # gaps (start,len): (0,0),(0,10),(10,40),(50,5) -> overall max = 40
    assert m["max_no_entry_bars"] == 40
    assert m["max_no_entry_days"] == round(40 * 4 / 24, 3)
    # decision gaps have start >= 12 -> only (50,5); the 40-bar gap starts at 10 (<12) -> excluded
    assert m["max_no_entry_bars_decision"] == 5
    # overall-longest gap starts at bar 10 < warmup 12 -> tagged warmup
    assert m["longest_gap_source"] == "warmup"
    assert m["first_entry_bar"] == 0


def test_decision_sourced_when_after_warmup():
    # warmup tiny (2); entries 3,5,60 -> gap 5->60 = 55 starts at 5 >= 2 -> decision
    m = no_entry_metrics([3, 5, 60], n_bars=100, warmup_decision_bars=2, bar_hours=4.0)
    assert m["max_no_entry_bars_decision"] == 55 and m["longest_gap_source"] == "decision"


def test_no_trades():
    m = no_entry_metrics([], n_bars=100, warmup_decision_bars=5, bar_hours=4.0)
    assert m["max_no_entry_bars"] == 0 and m["max_no_entry_bars_decision"] == 0
    assert m["first_entry_bar"] is None and m["longest_gap_source"] == "none"


def test_trailing_excluded_from_decision():
    m = no_entry_metrics([20, 30], n_bars=100, warmup_decision_bars=0, bar_hours=4.0)
    assert m["trailing_no_entry_bars"] == 69          # 99 - 30
    assert m["max_no_entry_bars_decision"] == 20       # gaps: (0,20),(20,10) -> max decision 20; trailing excluded


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t(); print(f"  ok  {t.__name__}")
    print(f"S0 NO-ENTRY OK — {len(tests)} checks passed")


if __name__ == "__main__":
    _main()
