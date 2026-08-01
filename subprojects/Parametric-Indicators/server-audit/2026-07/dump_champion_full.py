"""On the server: reproduce the dashboard L1 'Run' payload for a champion (inst, tf) and dump it as JSON.
Mirrors server.py /api/backtest_causal (L1 view) exactly."""
import json, sys
from optimize.l2 import payload as l2p

inst, tf = sys.argv[1], sys.argv[2]
discover = "--keys" in sys.argv

# champion params the dashboard pre-fills for this instrument+tf (reads wsh4_champions_full_<INST>.json)
l1def = l2p.instrument_l1_default(inst, tf)
body = dict(l1def); body["timeframe"] = tf; body["instrument"] = inst
l1lay = l2p._layer_from_strategy(body)
out = l2p.build_view_payload(l1lay, {}, tf, "l1", instrument=inst, l1_engine=body)

if discover:
    def shape(v):
        if isinstance(v, dict): return {k: shape(x) for k, x in list(v.items())[:60]} if len(v) <= 60 else f"dict[{len(v)}]"
        if isinstance(v, list): return f"list[{len(v)}]" + (f" e.g. {shape(v[0])}" if v else "")
        return type(v).__name__
    print("TOP KEYS:", list(out.keys()))
    print(json.dumps({k: shape(out[k]) for k in out if k != "log"}, indent=1, default=str)[:4000])
else:
    # drop the huge per-candle log + chart arrays; keep every scalar/box metric
    slim = {k: v for k, v in out.items() if k not in ("log",)}
    json.dump(slim, open(f"/tmp/champ_full_{inst}_{tf}.json", "w"), default=str)
    print(f"wrote /tmp/champ_full_{inst}_{tf}.json  keys={list(slim.keys())}")
