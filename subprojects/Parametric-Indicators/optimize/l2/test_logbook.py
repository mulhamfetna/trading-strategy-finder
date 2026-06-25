"""run_causal parity + structure tests. The causal log must reproduce the legacy oracle exactly
(L1 via l1_runner, L2 via engine.run_l2) — parity is the gate for the whole rebuild."""
import sys
import json
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.l2 import logbook, payload, l1_runner, engine, metrics

_CHAMP = json.load(open(str(_PI / "optimize/results/l2v2_4h_champion.json")))["params"]


def test_run_causal_emits_one_row_per_decision_bar():
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    assert res.n == len(res.log) == len(res.dec_dates)
    assert {r.layer for r in res.log} <= {"L1", "L2", None}
    assert all(r.reason for r in res.log)                       # every row attributed
    assert all(r.box_cause is not None for r in res.log if r.i > 0)  # box_cause kept on every bar incl. in-position
    assert res.warmup["l1"]["warmup_bars"] > 0                  # L1 lean champion has 1-min indicators


def test_causal_l1_matches_legacy_oracle():
    """L1 entries (bar + direction) and P/L from the causal log == the legacy l1_runner ledger exactly."""
    legacy = l1_runner.run_l1("4h")                             # frozen lean champion
    res = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    l1_entries = [(r.i, r.direction) for r in res.log if r.layer == "L1" and r.decision == "entry"]
    legacy_entries = [(int(t["entry_idx"]), t["direction"]) for t in legacy.ledger]
    assert l1_entries == legacy_entries
    l1_rows = [r for r in res.log if r.layer == "L1" and r.decision == "entry"]
    assert round(sum(r.pnl for r in l1_rows)) == 149989
    # per-layer running equity is booked in exit-time order; final equity == layer P/L; dd never negative
    last = max(l1_rows, key=lambda r: r.exit_time)
    assert round(last.equity) == 149989 and all(r.dd >= 0 for r in l1_rows)


def test_causal_l2_matches_legacy_engine():
    """L2 book from the causal log == legacy engine.run_l2 (l1_priority) STRUCTURALLY: entry set,
    count, DD, and the force-closed subset — not just rounded dollars."""
    legacy_l1 = l1_runner.run_l1("4h")
    legacy = engine.run_l2(legacy_l1, _CHAMP)                   # l1_priority
    res = logbook.run_causal(payload.l1_default_params("4h"), _CHAMP, "4h")
    l2_rows = [r for r in res.log if r.layer == "L2" and r.decision == "entry"]
    assert sorted((r.i, r.direction) for r in l2_rows) == \
           sorted((int(t["entry_idx"]), t["direction"]) for t in legacy.ledger)
    assert len(l2_rows) == 34
    assert round(metrics.score(legacy)["pnl"]) == round(sum(r.pnl for r in l2_rows)) == 25383
    eq = np.cumsum([r.pnl for r in sorted(l2_rows, key=lambda r: r.exit_time)])
    assert round(float((np.maximum.accumulate(eq) - eq).max())) == 7136               # L2 DD (l2v2)
    fc_causal = sorted((r.i, round(r.exit_price, 4), round(r.pnl, 2)) for r in l2_rows if r.exit_reason == "L1-entry")
    fc_legacy = sorted((int(t["entry_idx"]), round(float(t["exit_price"]), 4), round(float(t["pnl"]), 2))
                       for t in legacy.ledger if t["exit_reason"] == "L1-entry")
    assert fc_causal == fc_legacy and len(fc_causal) == legacy.n_l1_entry_exits


def test_l1_and_l2_entries_are_disjoint():
    """One shared account: a bar cannot be both an L1 and an L2 entry."""
    res = logbook.run_causal(payload.l1_default_params("4h"), _CHAMP, "4h")
    l1b = {r.i for r in res.log if r.layer == "L1" and r.decision == "entry"}
    l2b = {r.i for r in res.log if r.layer == "L2" and r.decision == "entry"}
    assert l1b.isdisjoint(l2b)


def test_force_close_only_strictly_inside_l2_span():
    """An L1 entry on an L2 trade's natural-exit bar must NOT force-close it; only one strictly inside does."""
    dec_dates = np.array(["2025-01-01T00:00", "2025-01-01T04:00", "2025-01-01T08:00", "2025-01-01T12:00"],
                         dtype="datetime64[ns]")
    dec_close = np.array([100.0, 110.0, 120.0, 130.0])
    cand = [{"entry_idx": 0, "entry_time": dec_dates[0], "entry_price": 100.0, "direction": "long",
             "exit_time": dec_dates[2], "exit_price": 120.0, "exit_reason": "TAKE_PROFIT_HARD", "pnl_points": 20.0}]
    assert engine.force_close_on_l1_entry(list(cand), [2], dec_dates, dec_close, 20.0)[0]["exit_reason"] == "TAKE_PROFIT_HARD"
    assert engine.force_close_on_l1_entry(list(cand), [1], dec_dates, dec_close, 20.0)[0]["exit_reason"] == "L1-entry"


def test_l1result_exposes_votes_and_skipped_would_be():
    """task #210/verbose-logs: L1Result surfaces per-bar votes + breaker-skipped would-be P/L."""
    l1 = payload.run_l1_cached("4h", use_disk=False)
    n = len(l1.df_dec)
    assert hasattr(l1, "votes_by_bar") and len(l1.votes_by_bar) == n
    nonempty = [v for v in l1.votes_by_bar if v]
    assert nonempty, "no per-bar votes recorded"
    chip = nonempty[0][0]
    assert set(chip) == {"key", "vote", "active"}
    assert chip["vote"] in ("confirm", "veto", "neutral")
    assert isinstance(l1.skipped_would_be, dict)


def test_run_causal_populates_deferred_fields():
    """verbose-logs: run_causal fills text/indicators/veto_flip/would_be_pnl."""
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    rows = res.log
    assert any(r.indicators for r in rows), "no row carries indicator votes"
    assert all(isinstance(r.text, str) and r.text for r in rows), "text not populated on every row"
    skip_rows = [r for r in rows if r.event_type == "SKIP"]
    assert (not skip_rows) or any(r.would_be_pnl is not None for r in skip_rows), "SKIP rows missing would_be_pnl"
    for r in rows:
        if r.decision == "entry" and r.box_dir and r.direction:
            assert r.veto_flip == (r.direction != r.box_dir)


def test_cap_1min_produces_time_cap_exits():
    """time-cap: cap_1min>0 on L1 yields TIME_CAP exits; default (0) yields none."""
    capped = dict(payload.l1_default_params("4h"), cap_1min=3)   # tight cap → many time-cap exits
    res = logbook.run_causal(capped, dict(payload.PERMISSIVE), "4h")
    assert "TIME_CAP" in {r.exit_reason for r in res.log if r.decision == "entry"}
    res0 = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    assert "TIME_CAP" not in {r.exit_reason for r in res0.log if r.decision == "entry"}


def test_cap_mode_eod_produces_end_of_day_exits():
    """cap_mode='eod' on L1 yields END_OF_DAY exits via the causal log."""
    p = dict(payload.l1_default_params("4h"), cap_mode="eod", eod_margin_min=15)
    res = logbook.run_causal(p, dict(payload.PERMISSIVE), "4h")
    assert "END_OF_DAY" in {r.exit_reason for r in res.log if r.decision == "entry"}
