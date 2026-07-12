"""Tasks 2-3 — the volatility envelope, the derived bounds, and the decision-frame mask."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize import data
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals import window as W

_CACHE = {}


def _bundle(tf="4h", inst="NQ"):
    if (tf, inst) not in _CACHE:
        df_dec, df1, _box, _vf, _n = data.load_inputs(tf, instrument=inst)
        _CACHE[(tf, inst)] = (df_dec, df1)
    return _CACHE[(tf, inst)]


# --------------------------------------------------------------------------- envelope

def test_envelope_has_one_row_per_offset():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert list(env.index) == list(range(-60, 61))
    assert (env["ratio"] > 0).all()


def test_envelope_peaks_at_offset_zero():
    """THE CALENDAR VALIDATION.

    If our release timestamps are right, the volatility spike lands ON the release minute. If a
    FRED release_id or an Eastern clock time were wrong, the spike would land somewhere else.
    This test is the calendar's proof, not a formality. Do not loosen it — fix the calendar.
    """
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    peak = int(env["ratio"].idxmax())
    assert -1 <= peak <= 1, f"volatility peaks at offset {peak}, not 0 — calendar timestamps are wrong"


def test_release_minute_is_visibly_more_volatile_than_baseline():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert env.loc[0, "ratio"] > 2.0, "the release minute should be >2x a normal minute"


def test_the_market_is_QUIET_before_a_release():
    """MEASURED FINDING — and it contradicts the original design premise.

    The brainstorm assumed volatility ramps up BEFORE a release ("before and while the news is
    released there is high volatility"). It does not. The market goes still: offsets -6..-2 sit at
    0.78x-1.16x baseline, i.e. at or BELOW an ordinary minute. Traders stand aside and wait.

    Consequence: the derived pre-window is ZERO minutes. There is no pre-release storm to hide from
    -- only a post-release one. If this test ever fails, the market's behaviour has changed and the
    'widen-and-hold' head (milestone 2) needs rethinking.
    """
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    calm = env.loc[-6:-2, "ratio"]
    assert (calm < 1.5).all(), f"expected calm before the release, got {calm.to_dict()}"


def test_the_storm_decays_within_half_an_hour():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert env.loc[25, "ratio"] < 1.6, "volatility should be back near baseline ~25 min after"


def test_far_post_offsets_are_contaminated_by_the_CASH_OPEN_not_the_release():
    """A trap, documented so nobody 'fixes' it later.

    Most of our releases land at 08:30 ET. Offset +60 is therefore 09:30 ET -- the US cash equity
    open, the single most volatile minute of the trading day. The envelope shows ~4.9x there, but
    that is a DIFFERENT event, not the release still echoing an hour later.

    This is why derive_bounds walks a CONTIGUOUS run outward from offset 0 and stops at the first
    quiet minute (it stops at +13): the calm patch at +22..+27 separates the release storm from the
    cash open, so the window cannot run away and swallow the whole morning.
    """
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert env.loc[60, "ratio"] > 2.0, "expected the 09:30 cash open to show up at offset +60"
    assert env.loc[25, "ratio"] < 1.6, "expected a calm gap separating the release from the open"


def test_derived_bounds_are_zero_pre_and_a_short_post():
    """The measured window. Pinned so a data or calendar change that moves it is caught."""
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    pre, post = W.derive_bounds(env, threshold=1.5)
    assert pre == 0, f"expected no pre-release ramp, got pre={pre}"
    assert 8 <= post <= 20, f"expected a ~10-20 min post-release storm, got post={post}"


def test_derive_bounds_brackets_zero_and_is_sane():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    pre, post = W.derive_bounds(env, threshold=1.5)
    assert pre >= 0 and post >= 1
    assert pre <= 60 and post <= 60


# --------------------------------------------------------------------------- masks

def test_mask_is_decision_length_bool_and_entry_aligned():
    df_dec, _ = _bundle()
    mask = W.release_window_mask(df_dec, rc.load_calendar(), pre_min=5, post_min=15)
    assert mask.dtype == np.bool_
    assert len(mask) == len(df_dec)
    assert mask[0] == False, "bar 0 can never be entry-blocked (identity, matches runner.py:188)"
    assert mask.any(), "with a real calendar some decision bars must be inside a window"


def test_mask_is_all_false_for_an_empty_calendar():
    df_dec, _ = _bundle()
    empty = pd.DataFrame({"Date": pd.to_datetime([]), "event": [], "agency": []})
    mask = W.release_window_mask(df_dec, empty, pre_min=5, post_min=15)
    assert not mask.any(), "identity default: no releases => no blocking"


def test_exit_targets_point_at_the_window_open():
    _, df1 = _bundle()
    tgt = W.news_exit_targets(df1, rc.load_calendar(), pre_min=5)
    assert len(tgt) == len(df1)
    inside = tgt[tgt >= 0]
    assert len(inside) > 0
    assert (inside < len(df1)).all()


def test_exit_targets_are_all_minus_one_for_an_empty_calendar():
    _, df1 = _bundle()
    empty = pd.DataFrame({"Date": pd.to_datetime([]), "event": [], "agency": []})
    tgt = W.news_exit_targets(df1, empty, pre_min=5)
    assert (tgt == -1).all(), "identity default: no releases => no forced exits"
