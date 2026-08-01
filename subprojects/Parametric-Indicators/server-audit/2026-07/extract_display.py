"""Read the already-computed full payload JSONs on the server and emit ONE small combined display JSON."""
import json

PAIRS = [("GC", "4h"), ("SI", "2m"), ("ES", "4h")]
comb = {}
for inst, tf in PAIRS:
    try:
        out = json.load(open(f"/tmp/champ_full_{inst}_{tf}.json"))
    except Exception as e:
        comb[inst] = {"error": str(e)}; continue
    meta = out.get("meta", {})
    summ = meta.get("summary", {})
    params = meta.get("params", {})
    ev = out.get("events", [])
    xb = {}
    if isinstance(ev, list):
        for e in ev:
            if not isinstance(e, dict): continue
            r = str(e.get("reason") or e.get("exit") or e.get("type") or e.get("kind") or "?")
            d = xb.setdefault(r, {"n": 0, "pnl": 0.0})
            d["n"] += 1
            try: d["pnl"] += float(e.get("pnl", 0) or 0)
            except Exception: pass
    inds = [i.get("key") for i in params.get("indicators", []) if isinstance(i, dict) and i.get("enabled")]
    comb[inst] = {
        "tf": tf,
        "summary": summ,
        "exit_breakdown": xb,
        "params": {k: params.get(k) for k in
                   ("sl_soft", "sl_hard", "tp", "gate_pct", "gate_thr", "dd_limit",
                    "cooldown", "k", "flip", "window")},
        "indicators": inds,
        "counts": {k: (len(out[k]) if isinstance(out.get(k), list) else None)
                   for k in ("candles", "trades", "equity", "events")},
    }
json.dump(comb, open("/tmp/champ_display.json", "w"), default=str)
import os
print("wrote /tmp/champ_display.json", os.path.getsize("/tmp/champ_display.json"), "bytes")
