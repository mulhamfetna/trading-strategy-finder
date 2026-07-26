"""Run-queue: expand an instruments×timeframes matrix into per-study configs and launch them.
`expand` is the pure, tested core; the launcher is a thin wrapper over control.start."""
from __future__ import annotations

_SHARED_DROP = {"instruments", "timeframes", "trials_mode", "per_trials", "trials"}


def expand(cfg: dict) -> list[dict]:
    """Expand {instruments, timeframes, trials_mode, trials|per_trials, ...shared} into one config per
    (instrument, timeframe). trials_mode ∈ {auto, one, per}."""
    insts = cfg.get("instruments") or [cfg.get("instrument", "NQ")]
    tfs = cfg.get("timeframes") or [cfg.get("timeframe", "4h")]
    mode = cfg.get("trials_mode", "auto")
    per = cfg.get("per_trials", {}) or {}
    shared = {k: v for k, v in cfg.items() if k not in _SHARED_DROP}
    out = []
    for inst in insts:
        for tf in tfs:
            c = dict(shared)
            c["instrument"] = inst
            c["timeframe"] = tf
            c["timeframes"] = [tf]                         # single-tf launch per study
            if mode == "auto":
                c["auto_trials"] = True
            elif mode == "one":
                c["auto_trials"] = False
                c["trials"] = int(cfg.get("trials", 0))
            elif mode == "per":
                c["auto_trials"] = False
                c["trials"] = int(per.get(f"{inst}:{tf}", per.get(tf, 0)))
            out.append(c)
    return out


# In-process queue state (single-process control plane).
_QUEUE: list[dict] = []


def launch(cfg: dict, start_fn) -> list[dict]:
    """Expand + launch each study via start_fn (control.start); record status. Returns the queue."""
    global _QUEUE
    _QUEUE = [{"instrument": c["instrument"], "timeframe": c["timeframe"], "state": "pending", "cfg": c}
              for c in expand(cfg)]
    for item in _QUEUE:
        r = start_fn(item["cfg"])
        item["state"] = "launched" if r.get("ok") else "failed"
        item["detail"] = r.get("detail", "")
    return _QUEUE


def state() -> list[dict]:
    return [{k: v for k, v in it.items() if k != "cfg"} for it in _QUEUE]
