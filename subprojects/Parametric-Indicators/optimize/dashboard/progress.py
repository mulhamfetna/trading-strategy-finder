"""Live progress + ETA for the control center. Pure `compute_eta` (unit-tested) + a thin study reader.

ETA = remaining trials ÷ the trailing trial-rate (Δdone/Δt over the sample buffer). None when the rate
is non-positive (can't estimate). No optimizer-engine import — reads only trial counts."""
from __future__ import annotations


def compute_eta(samples: list[tuple[float, int]], target: int) -> dict:
    """samples: list of (epoch_seconds, trials_done), oldest→newest. Returns
    {done, target, rate_per_min, eta_seconds|None, elapsed_seconds}."""
    if not samples:
        return {"done": 0, "target": target, "rate_per_min": 0.0, "eta_seconds": None,
                "elapsed_seconds": 0.0}
    t0, d0 = samples[0]
    t1, d1 = samples[-1]
    dt = t1 - t0
    rate_per_sec = (d1 - d0) / dt if dt > 0 else 0.0
    remaining = max(0, target - d1)
    if remaining == 0:
        eta = 0.0
    elif rate_per_sec > 0:
        eta = remaining / rate_per_sec
    else:
        eta = None
    return {"done": d1, "target": target, "rate_per_min": rate_per_sec * 60.0,
            "eta_seconds": eta, "elapsed_seconds": dt}


# Per-study rolling sample buffer, keyed by study name (process-local; the control plane is single-process).
_BUFFERS: dict[str, list[tuple[float, int]]] = {}
_MAX_SAMPLES = 20


def record(study: str, now: float, done: int, keep: int = _MAX_SAMPLES) -> list[tuple[float, int]]:
    """Append a (now, done) sample for `study` and return the trailing buffer (capped)."""
    buf = _BUFFERS.setdefault(study, [])
    if not buf or buf[-1][1] != done or (now - buf[-1][0]) >= 1.0:
        buf.append((now, done))
        del buf[:-keep]
    return buf


def live(study: str, done: int, target: int, now: float) -> dict:
    """Record a fresh sample and return the ETA dict for `study`."""
    return compute_eta(record(study, now, done), target)
