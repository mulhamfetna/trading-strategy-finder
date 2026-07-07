import math
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.metrics import payoff_ratio, max_drawdown, summarize


def test_payoff_ratio_basic():
    # wins avg = (200+100)/2 = 150 ; losses avg = 100 ; payoff = 1.5
    assert payoff_ratio([200.0, 100.0, -100.0]) == 1.5

def test_payoff_ratio_no_losses_is_inf():
    assert payoff_ratio([10.0, 20.0]) == math.inf

def test_payoff_ratio_no_wins_is_zero():
    assert payoff_ratio([-10.0, -20.0]) == 0.0

def test_max_drawdown_simple():
    # equity path: +100, +50 (peak 100→150), -200 (trough -50) → DD from 150 to -50 = 200
    assert max_drawdown([100.0, 50.0, -200.0]) == 200.0

def test_summarize_fields():
    m = summarize([200.0, -100.0, 300.0], n_eligible=12)
    assert m.n_entries == 3
    assert m.n_eligible == 12
    assert m.entry_rate == 0.25
    assert m.total_pnl == 400.0
    assert m.win_rate == 2 / 3
    assert m.payoff == 2.5          # avg win 250 / avg loss 100
    assert m.expectancy == 400.0 / 3
