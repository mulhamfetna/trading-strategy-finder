# optimize/l2/test_tf_defaults.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import payload
from optimize.l2 import l1_runner

_W = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full.json"


def test_4h_default_unchanged():
    # 4h stays the lean champion — byte-identical to the pre-change behavior
    assert payload.l1_default_params("4h") == payload.validate_layer_params(l1_runner._lean_params("4h"))


def test_per_tf_default_matches_wsh4_champion():
    champs = json.loads(_W.read_text())
    for tf in ("2h", "15m", "2m"):
        p = payload.l1_default_params(tf)
        assert p["sl_soft"] == float(champs[tf]["box"]["sl_soft"])      # box → params
        assert p["tp"] == float(champs[tf]["box"]["tp"])
        assert p["ind_1min"] is True                                   # L1 champions run on the 1-min frame
        assert isinstance(p["indicators"], list)


def test_tf_set_is_the_six_decision_tfs():
    assert payload._TF_SET == ("4h", "2h", "1h", "15m", "5m", "2m")


def test_non_4h_causal_run_does_not_hit_the_4h_only_lean_path():
    # Regression: build_view_payload / logbook.run_causal used the no-params "frozen lean" L1 run whenever
    # l1==l1_default_params(tf). The lean champion is 4h-only, so a non-4h default L1 (the wsh4 champion)
    # crashed with SystemExit("missing wsh_lean_4h_champion.json"). The fix gates that fast path on tf=="4h".
    l1 = payload.l1_default_params("2h")
    out = payload.build_view_payload(l1, payload.l2_default_params(), "2h", "l2")
    assert out["meta"]["view"] == "l2"
    assert len(out["log"]) == out["meta"]["n"] > 0
