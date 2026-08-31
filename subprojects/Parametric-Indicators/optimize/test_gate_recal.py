"""#198 — unit tests for the gate-recalibration hook (docs/WS-GATECAL-PREREGISTRATION.md §1).
Pure-function level (no market data): the off-state is byte-identical, boundaries follow the calendar,
the trailing seed is causal, and the random-percentile control is reproducible."""
import numpy as np
import pandas as pd

from volatility import gate_threshold, gate_thresholds_recal


def _dates(n, start="2025-01-01", freq="4h"):
    return pd.date_range(start, periods=n, freq=freq).to_numpy()


def test_off_state_is_the_frozen_threshold_everywhere():
    rng = np.random.default_rng(0)
    vf = rng.lognormal(0, 1, 800)
    thr = gate_thresholds_recal(vf, _dates(800), n_split=400, gate_pct=90, recal_months=0)
    assert np.all(thr == gate_threshold(vf, 400, 90))


def test_prefix_before_first_boundary_stays_frozen_and_then_changes():
    rng = np.random.default_rng(1)
    vf = np.r_[rng.lognormal(0, 0.2, 400), rng.lognormal(2.0, 0.2, 800)]   # regime jump after the seed
    thr = gate_thresholds_recal(vf, _dates(1200), n_split=400, gate_pct=90, recal_months=1)
    frozen = gate_threshold(vf, 400, 90)
    assert np.all(thr[:400] == frozen)
    assert thr[-1] > frozen * 2                       # the trailing seed sees the hotter regime


def test_causal_trailing_seed_uses_only_past_bars():
    # plant an extreme value AT a boundary bar: the threshold set at that boundary must NOT see it
    n, ns = 1200, 400
    vf = np.ones(n)
    dates = _dates(n)
    months = pd.PeriodIndex(pd.DatetimeIndex(dates), freq="M")
    first = np.r_[True, (months[1:] != months[:-1])]
    b = int(np.nonzero(first & (np.arange(n) >= ns))[0][0])
    vf[b] = 1e9
    thr = gate_thresholds_recal(vf, dates, n_split=ns, gate_pct=90, recal_months=1)
    assert thr[b] <= 1.0 + 1e-9                      # percentile of past ones, spike excluded


def test_quarterly_recalibrates_at_a_third_of_the_monthly_boundaries():
    rng = np.random.default_rng(3)
    vf = rng.lognormal(0, 1, 2000)
    d = _dates(2000)
    t1 = gate_thresholds_recal(vf, d, 400, 90, recal_months=1)
    t3 = gate_thresholds_recal(vf, d, 400, 90, recal_months=3)
    c1 = int((np.diff(t1) != 0).sum()); c3 = int((np.diff(t3) != 0).sum())
    assert c1 > c3 >= 1 and c1 >= 2 * c3


def test_random_pct_control_is_seeded_and_differs_from_real():
    rng = np.random.default_rng(4)
    vf = rng.lognormal(0, 1, 1500)
    d = _dates(1500)
    a = gate_thresholds_recal(vf, d, 400, 90, 1, random_pct_seed=198)
    b = gate_thresholds_recal(vf, d, 400, 90, 1, random_pct_seed=198)
    c = gate_thresholds_recal(vf, d, 400, 90, 1)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
