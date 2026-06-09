"""WS-I winning-strategy presets for the dashboard (one-click import).

Each per-timeframe champion (from optimize/results/wsi_champions_full.json) is mapped to the EXACT
dashboard parameter schema — box/risk knobs + every indicator's on/off + its tuned internal params +
K — so selecting it fills the whole form. The dashboard-only GLOBAL entry-timing knobs
(retrace/wait) stay at their off defaults: the WS-I search never tuned them, so leaving them off
reproduces the reported behaviour exactly.

Nothing here is hardcoded in the frontend — the presets are served via /api/config.
"""
from __future__ import annotations

import json
from pathlib import Path

import config
from indicators import library

_HERE = Path(__file__).resolve().parent
_CHAMP_JSON = _HERE / "optimize" / "results" / "wsi_champions_full.json"
# User-saved profiles persist here (server-side, shared across browsers) — same JSON shape as the
# built-in presets, so they're first-class entries in the Strategy dropdown.
_PROFILES_JSON = _HERE / "profiles" / "user_profiles.json"
_TF_ORDER = ["4h", "2h", "1h", "15m", "5m", "2m", "1m"]   # coarsest → finest (matches the report)


def load_user_profiles() -> dict:
    """{name: preset} of user-saved profiles, from the on-disk store (empty if none)."""
    if not _PROFILES_JSON.exists():
        return {}
    try:
        d = json.loads(_PROFILES_JSON.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_user_profile(name: str, preset: dict) -> dict:
    """Persist one profile (name → preset) to the shared on-disk store. Returns all profiles."""
    name = (name or "").strip()
    if not name:
        raise ValueError("profile name is required")
    profs = load_user_profiles()
    profs[name] = preset
    _PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES_JSON.write_text(json.dumps(profs, indent=1))
    return profs


def delete_user_profile(name: str) -> dict:
    profs = load_user_profiles()
    profs.pop((name or "").strip(), None)
    _PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES_JSON.write_text(json.dumps(profs, indent=1))
    return profs


def _champions() -> dict:
    if not _CHAMP_JSON.exists():
        return {}
    try:
        return json.loads(_CHAMP_JSON.read_text())
    except Exception:
        return {}


def _all_specs(inds_on: dict | None = None):
    """Return (full 15-indicator spec list, gen_swing_l). Every registered indicator is emitted with
    enabled True/False so importing a preset RESETS indicators not in it (a previously-on indicator
    is turned off). mode = the schema default (the search used a fixed mode per indicator)."""
    inds_on = inds_on or {}
    specs, gen_swing = [], 2
    for key in library.REGISTRY:
        meta = library.SCHEMA[key]
        on = key in inds_on
        params = dict(inds_on[key]) if on else {}
        # the structure-generation report uses ONE global swing_l; align it to the structure-style
        # indicator's own swing_l when that indicator is on (purely cosmetic — voting uses params).
        if on and key in ("order_block", "structure_trend") and "swing_l" in params:
            gen_swing = params["swing_l"]
        specs.append({"key": key, "enabled": on, "mode": meta["mode"], "params": params})
    return specs, gen_swing


def _preset(timeframe: str, box: dict, inds_on: dict) -> dict:
    specs, gen_swing = _all_specs(inds_on)
    return dict(
        timeframe=timeframe, window="full",
        sl_soft=box["sl_soft"], sl_hard=box["sl_hard"], tp=box["tp"],
        gate_pct=box["gate_pct"], dd_limit=box["dd_limit"], cooldown=box["cooldown"],
        flip=box["flip"], k=box["k"],
        dd_cap=config.DD_CAP, pv=config.NQ_POINT_VALUE,
        retrace_amount=0, retrace_unit="atr_mult", wait_bars=0,
        gen={"swing_l": gen_swing, "golf_n": 3},
        indicators=specs,
    )


def strategies() -> list[dict]:
    """List of importable strategies: the plain box winner first, then each per-TF WS-I champion.
    Each item = {id, label, preset} where preset matches the dashboard param schema 1:1."""
    champs = _champions()
    # the original box winner (all indicators off → pure box strategy), 4h
    winner_box = dict(sl_soft=config.WINNER["sl_soft"], sl_hard=config.WINNER["sl_hard"],
                      tp=config.WINNER["tp"], gate_pct=config.WINNER["gate_pct"],
                      dd_limit=config.WINNER["dd_limit"], cooldown=config.WINNER["cooldown"],
                      flip=config.WINNER["flip"], k=1)
    out = [{"id": "winner", "label": "★ Winner — plain box (4h)",
            "preset": _preset("4h", winner_box, {})}]
    for tf in _TF_ORDER:
        c = champs.get(tf)
        if not c:
            continue
        out.append({"id": f"wsi_{tf}",
                    "label": f"WS-I {tf} champion — typ ${c['median_pnl']:,.0f}",
                    "preset": _preset(tf, c["box"], c.get("indicators", {}))})
    # user-saved profiles (server-side store) — first-class entries, id prefixed 'user_'
    for name, preset in load_user_profiles().items():
        out.append({"id": f"user_{name}", "label": f"👤 {name}", "preset": preset})
    return out
