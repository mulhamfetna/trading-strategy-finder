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
# wsh4 regime: champions whose indicators were tuned on the 1-MINUTE frame (--ind-1min sweep). The dev
# dashboard already evaluates indicators on the 1-minute frame (strategy.py), so these reproduce
# faithfully. Added ALONGSIDE the originals above — never replacing them.
_CHAMP_1MIN_JSON = _HERE / "optimize" / "results" / "wsh4_champions_full.json"
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


def _champions_1min() -> dict:
    """wsh4 per-TF champions (indicators tuned on the 1-minute frame). Empty if the file is absent."""
    if not _CHAMP_1MIN_JSON.exists():
        return {}
    try:
        return json.loads(_CHAMP_1MIN_JSON.read_text())
    except Exception:
        return {}


_CHAMP_WSH5_SPLIT_JSON = _HERE / "optimize" / "results" / "wsh5_4h_split_champion.json"
# wsh5 regime: a SINGLE 4h champion from the SPLIT long/short SL/TP sweep (Q3/E2; --split-sltp). The
# full-data optimizer ran 4h-ONLY (2026-06-15 directive). This is imported as an ALTERNATIVE profile —
# the deployed shared champion ([[project_wsg_winner]] / wsh4 4h) is NOT replaced: per the adoption gate
# the split champion did NOT OOS-dominate (lower return, much lower drawdown, higher win-rate). See
# study_range_regime/REPORT_wsh5_4h_split_champion.md. NOTE: this run predates the ifvg/breaker/cisd votes
# being wired, so its search space did NOT include them (a subsequent run will).
def _champions_wsh5_split() -> dict:
    if not _CHAMP_WSH5_SPLIT_JSON.exists():
        return {}
    try:
        return json.loads(_CHAMP_WSH5_SPLIT_JSON.read_text())
    except Exception:
        return {}


# β-ablation LEAN champion: the wsh4 1-min 4h champion with 5 of its 8 indicators dropped (keep
# cci/order_block/structure_trend). Full-period P/L $149,989 (+5.5% vs the 8-ind champion) at HALF the data
# footprint (346->138 candles). Source/run: study_range_regime/UPDATE_S0_beta_no_entry_and_ablation.md +
# REPORT_indicator_ablation_wsi1m_4h.md. CAVEAT: ablation is FULL-PERIOD only; re-check folds/OOS before deploy.
_CHAMP_LEAN_JSON = _HERE / "optimize" / "results" / "wsh_lean_4h_champion.json"

def _champions_lean() -> dict:
    if not _CHAMP_LEAN_JSON.exists():
        return {}
    try:
        return json.loads(_CHAMP_LEAN_JSON.read_text())
    except Exception:
        return {}


_CHAMP_WSH6_LOWDD_JSON = _HERE / "optimize" / "results" / "wsh6_lowdd_4h_champion.json"

def _champions_wsh6_lowdd() -> dict:
    """wsh6 (cap_1min searched) — the lowest-drawdown CAPPED Pareto pick. A conservative alternative:
    a hard max-hold cap trades return for much smaller DD (never beats the uncapped champion on P/L)."""
    if not _CHAMP_WSH6_LOWDD_JSON.exists():
        return {}
    try:
        return json.loads(_CHAMP_WSH6_LOWDD_JSON.read_text())
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
    p = dict(
        timeframe=timeframe, window="full",
        sl_soft=box["sl_soft"], sl_hard=box["sl_hard"], tp=box["tp"],
        gate_pct=box["gate_pct"], dd_limit=box["dd_limit"], cooldown=box["cooldown"],
        flip=box["flip"], k=box["k"],
        dd_cap=config.DD_CAP, pv=config.NQ_POINT_VALUE,
        retrace_amount=0, retrace_unit="atr_mult", wait_bars=0,
        gen={"swing_l": gen_swing, "golf_n": 3},
        indicators=specs,
    )
    # Optional SPLIT long/short SL/TP (Q3/E2): when a champion box carries any per-side value, pass all six
    # through so the dashboard imports it in 'split' mode. Absent ⇒ shared SL/TP (the common case) ⇒ omitted
    # ⇒ the form stays in 'shared' mode. A blank/None per side still falls back to the shared boxes server-side.
    _SPLIT = ("long_sl_soft", "long_sl_hard", "long_tp", "short_sl_soft", "short_sl_hard", "short_tp")
    if any(box.get(k) is not None for k in _SPLIT):
        for k in _SPLIT:
            p[k] = box.get(k)
    # Optional exit cap (cap_1min bars cap / cap_mode). Absent ⇒ omitted ⇒ no cap (existing presets
    # unchanged). A bars cap sets cap_mode='bars' so the dashboard applies it; 'eod' carries the margin.
    if box.get("cap_mode"):
        p["cap_mode"] = box["cap_mode"]
        if box["cap_mode"] == "eod":
            p["eod_margin_min"] = int(box.get("eod_margin_min", 15) or 15)
    if box.get("cap_1min"):
        p["cap_1min"] = int(box["cap_1min"])
        p.setdefault("cap_mode", "bars")
    return p


def strategies() -> list[dict]:
    """List of importable strategies: the plain box winner first, then each per-TF WS-I champion.
    Each item = {id, label, preset} where preset matches the dashboard param schema 1:1."""
    champs = _champions()
    _champs_1min = _champions_1min()          # wsh4 (1-minute-frame trained) champions, added below
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
        # Degraded champions (e.g. flip=true TFs whose old-quirk tuning went negative under the
        # corrected reverse-entry-only engine) are kept selectable but unmistakably flagged.
        if c.get("degraded"):
            label = f"⚠ WS-I {tf} — DEGRADED (reverse-entry-only flip) — typ ${c['median_pnl']:,.0f}"
        else:
            label = f"WS-I {tf} champion — typ ${c['median_pnl']:,.0f}"
        out.append({"id": f"wsi_{tf}", "label": label,
                    "preset": _preset(tf, c["box"], c.get("indicators", {}))})
    # NEW: wsh4 champions — indicators tuned on the 1-MINUTE frame. Added alongside (not replacing) the
    # entries above; labelled "⏱1-min" so it's unmistakable which regime they came from. The dev
    # dashboard evaluates indicators on the 1-minute frame, so these reproduce their tuned behaviour.
    for tf in _TF_ORDER:
        c = _champs_1min.get(tf)
        if not c:
            continue
        p = _preset(tf, c["box"], c.get("indicators", {}))
        p["trained_on"] = "1-minute frame (wsh4)"      # provenance marker (frontend ignores unknown keys)
        out.append({"id": f"wsi1m_{tf}",
                    "label": f"⏱ WS-I {tf} · 1-min-trained — typ ${c['median_pnl']:,.0f}",
                    "preset": p})
    # NEW: wsh5 4h SPLIT long/short SL/TP champion (Q3/E2 sweep, 4h-only full-data run). Imported as an
    # ALTERNATIVE (lower-return / much-lower-drawdown / higher-win-rate) — NOT a champion swap (adoption gate:
    # it did not OOS-dominate the shared champion). Importing it puts the dashboard in 'split' mode.
    for tf, c in _champions_wsh5_split().items():
        p = _preset(tf, c["box"], c.get("indicators", {}))
        p["trained_on"] = "1-minute frame · split long/short SL/TP (wsh5, 4h-only)"
        out.append({"id": f"wsh5split_{tf}",
                    "label": f"⚖ WS split {tf} · long/short SL/TP — typ ${c['median_pnl']:,.0f} (DD ${c['worst_dd']:,.0f})",
                    "preset": p})
    # NEW: β-ablation LEAN champion — the wsh4 1-min 4h champion stripped to its 3 high-value indicators
    # (cci/order_block/structure_trend; drop bollinger/keltner/mfi/obv/sma_trend). Full-period $149,989
    # (+5.5% vs the 8-ind champion) at HALF the data footprint (346->138). Imported as an ALTERNATIVE for the
    # fewer-indicators / lighter-live-data goal — NOT a champion swap (ablation is full-period; verify folds/OOS).
    for tf, c in _champions_lean().items():
        p = _preset(tf, c["box"], c.get("indicators", {}))
        p["trained_on"] = ("β ablation of the wsh4 1-min champion — lean 3-indicator subset "
                           "(full-period +5.5%; footprint 346->138 candles; verify on folds before deploy)")
        out.append({"id": f"wshlean_{tf}",
                    "label": (f"🍃 WS lean {tf} · 3-ind cci/OB/structure — ${c['full_pnl']:,.0f} "
                              f"(+5.5% vs champ · footprint {c.get('data_footprint_candles','?')})"),
                    "preset": p})
    # NEW: wsh6 low-DD CAPPED variant — the cap_1min search (11.4k trials) found NO config that beats the
    # uncapped champion on P/L; the cap is a pure drawdown trade. This is the best-P/L feasible CAPPED point:
    # a conservative profile (~−36% P/L for ~−58% DD). Side-by-side alternative, NOT a champion swap.
    for tf, c in _champions_wsh6_lowdd().items():
        b = dict(c["box"]); b.setdefault("cap_mode", "bars")
        p = _preset(tf, b, c.get("indicators", {}))
        p["trained_on"] = ("wsh6 cap_1min search — lowest-DD capped Pareto pick (cap trades return for DD; "
                           "never beats the uncapped champion on P/L)")
        out.append({"id": f"wsh6lowdd_{tf}",
                    "label": (f"🛡 WS low-DD {tf} · cap {int(c['box']['cap_1min'])} — ${c['full_pnl']:,.0f} "
                              f"(DD ${c['full_dd']:,.0f}, ~half vs champ)"),
                    "preset": p})
    # user-saved profiles (server-side store) — first-class entries, id prefixed 'user_'
    for name, preset in load_user_profiles().items():
        out.append({"id": f"user_{name}", "label": f"👤 {name}", "preset": preset})
    return out
