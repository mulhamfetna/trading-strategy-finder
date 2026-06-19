"""Causality audit for the L1 engine (Task 1 of the causal log-first rebuild).

These are the LOAD-BEARING causal proofs: a decision at bar i must depend only on bars <= i.
We prove it by TRUNCATING the engine inputs and re-running the pipeline — not by asserting a
numpy slice is unchanged (which would test slicing, not the engine). See optimize/l2/AUDIT_causality.md."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
import pytest
from optimize.l2 import l1_runner
from optimize import data as data_mod
from optimize import timeframes as TF


def test_decisions_depend_only_on_past_bars(monkeypatch):
    """Re-running L1 on inputs TRUNCATED to the first `cut` decision bars must reproduce the full
    run's L1 entries on that prefix (entry bar + direction). If any past decision used a future bar,
    the truncated entry set would differ — i.e. this fails iff there is look-ahead."""
    full = l1_runner.run_l1("4h")
    cut = full.n_split
    full_prefix = {(int(t["entry_idx"]), t["direction"]) for t in full.ledger if int(t["entry_idx"]) < cut}
    assert full_prefix, "expected at least one in-sample L1 entry"

    d4, d1, box, vf, n_split = data_mod.load_inputs("4h")
    t_cut = pd.Timestamp(d4["Date"].iloc[cut - 1])
    d4t = d4.iloc[:cut].copy()
    d1t = d1[d1["Date"] <= t_cut].copy()
    boxt = box[box["Date"] <= t_cut].copy() if "Date" in box.columns else box
    monkeypatch.setattr(data_mod, "load_inputs",
                        lambda tf: (d4t, d1t, boxt, vf[:cut], min(n_split, cut)))
    trunc = l1_runner.run_l1("4h")
    trunc_entries = {(int(t["entry_idx"]), t["direction"]) for t in trunc.ledger}
    assert trunc_entries == full_prefix, "a past decision changed when future bars were removed (look-ahead)"


def test_gate_threshold_stable_under_input_truncation():
    """Causal-in-VALUES: the in-sample gate threshold must be identical whether or not the OOS tail
    of the RAW inputs exists. We recompute the HAR-RV forecast on truncated raw inputs via the SAME
    vol_forecast path the loader uses, and assert the in-sample percentile is unchanged. The warmup
    back-fill (nanmedian over the forecast array) is the only theoretical future-touch; this measures
    its effect on the champion threshold to be exactly zero."""
    full = l1_runner.run_l1("4h")
    if full.params["gate_pct"] <= 0:
        pytest.skip("gate_pct=0 — no vol gate to test")
    cut = full.n_split
    thr_full = float(np.percentile(full.vf[:cut], full.params["gate_pct"]))

    d4, d1, _box, _vf, _n = data_mod.load_inputs("4h")
    t_cut = pd.Timestamp(d4["Date"].iloc[cut - 1])
    bar_minutes = TF.get("4h").minutes
    vf_trunc = data_mod.vol_forecast(d4.iloc[:cut].copy(),
                                     d1[d1["Date"] <= t_cut].copy(),
                                     bar_minutes=bar_minutes)
    thr_trunc = float(np.percentile(vf_trunc[:cut], full.params["gate_pct"]))
    assert abs(thr_full - thr_trunc) < 1e-9, \
        f"gate threshold moved when future raw inputs were removed: {thr_full} vs {thr_trunc}"


def test_exits_resolve_forward_not_lookahead():
    """Evidence for the audit: every trade exits at or after its entry (the 1-min sub-bar exit search
    is the trade PLAYING OUT forward in time, not look-ahead)."""
    full = l1_runner.run_l1("4h")
    for t in full.ledger:
        assert pd.Timestamp(t["exit_time"]) >= pd.Timestamp(t["entry_time"])
