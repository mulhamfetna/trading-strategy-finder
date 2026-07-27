"""The difference statistic, the shuffled-label control, and the power floor."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.news_context.stats import (               # noqa: E402
    assoc, bucket_delta, min_detectable_rho, shuffle_control,
)


def test_assoc_finds_a_planted_monotone_relationship():
    z = np.linspace(-3, 3, 200)
    r = 5 * z                       # perfectly monotone
    a = assoc(z, r)
    assert a["spearman"] == pytest.approx(1.0, abs=1e-9)
    assert a["n"] == 200


def test_assoc_reports_spearman_where_pearson_is_blinded_by_a_fat_tail():
    # monotone relationship + one enormous outlier that wrecks Pearson but not the ranks
    z = np.linspace(-3, 3, 200)
    r = 5 * z
    z[-1], r[-1] = 3.0, -100000.0
    a = assoc(z, r)
    assert a["spearman"] > 0.9, "ranks should survive a single outlier"
    assert a["pearson"] < a["spearman"], "this is exactly why spearman leads on fat tails"


def test_assoc_too_few_points_is_nan_not_a_crash():
    a = assoc(np.array([1.0]), np.array([2.0]))
    assert np.isnan(a["spearman"]) and a["n"] == 1


def test_bucket_delta_detects_a_planted_sign_flip():
    rng = np.random.default_rng(0)
    z = rng.normal(0, 1, 400)
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    r = np.empty(400)
    r[:200] = z[:200] * 10
    r[200:] = -z[200:] * 10
    d = bucket_delta(z, r, lab, "A", "B")
    assert d > 1.5, "a +1 vs -1 correlation flip must produce a delta near 2"


def test_shuffle_control_rejects_a_planted_flip():
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1, 400)
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    r = np.empty(400)
    r[:200] = z[:200] * 10
    r[200:] = -z[200:] * 10
    p, _pct = shuffle_control(z, r, lab, "A", "B", draws=200, rng=np.random.default_rng(2))
    assert p < 0.01, "a real flip must beat shuffled labels"


def test_shuffle_control_passes_pure_noise():
    rng = np.random.default_rng(3)
    z = rng.normal(0, 1, 400)
    r = rng.normal(0, 1, 400)          # no relationship at all
    lab = np.array(["A"] * 200 + ["B"] * 200, dtype=object)
    p, _pct = shuffle_control(z, r, lab, "A", "B", draws=200, rng=np.random.default_rng(4))
    assert p > 0.05, "noise must NOT be called significant"


def test_shuffle_control_is_deterministic_for_a_fixed_seed():
    rng = np.random.default_rng(5)
    z = rng.normal(0, 1, 200)
    r = rng.normal(0, 1, 200)
    lab = np.array(["A"] * 100 + ["B"] * 100, dtype=object)
    a = shuffle_control(z, r, lab, "A", "B", 100, np.random.default_rng(7))
    b = shuffle_control(z, r, lab, "A", "B", 100, np.random.default_rng(7))
    assert a == b


def test_min_detectable_rho_shrinks_with_n():
    small = min_detectable_rho(50, 50)
    large = min_detectable_rho(2000, 2000)
    assert large < small
    assert 0 < large < 1


def test_min_detectable_rho_nan_for_tiny_buckets():
    assert np.isnan(min_detectable_rho(2, 100))
