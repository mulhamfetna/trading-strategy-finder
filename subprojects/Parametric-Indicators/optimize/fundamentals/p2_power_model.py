"""WS-NEWS3 M2 (#126, parent #124) — the POWER MODEL: predict the release-minute |move| from
inputs knowable the night before.

Phase 2 (#116) proved the surprise explains the jump (rho to -0.63) — but the surprise needs
`actual`, which arrives WITH the move. This model uses only what exists before the release:

    P_hist  = expanding MEDIAN of the same (series x instrument)'s prior release-bar |open->close|%
              shifted one release (never includes the event being predicted), >=8 priors required.

That is deliberately the dumbest defensible predictor: if series identity + its own history cannot
rank releases by power, nothing pre-release can. |forecast - previous| is tested as an ADD-ON
(secondary), not baked in.

Pre-registration: #126 (filed before this first ran). Everything below is fixed there:
  primary   pooled OOS Spearman(P_hist, realized jump_pct) per instrument, Fisher-z 95% CI;
            useful iff CI-lo > 0 on each equity instrument
  V1        quintile buckets — Spearman of bucket realized means >= 0.8 (a different scorer)
  V2        CPI must rank top-2 predicted power for NQ/ES/RTY; EIA/API top-2 for CL
  V3        200 series-label shuffles (P_hist rebuilt each time) — observed Spearman must beat the
            95th percentile of the shuffled distribution, else the 'model' is vol clustering: VOID
  control   the same predictions scored against matched clean CONTROL-minute |moves| must be
            materially weaker than against release minutes

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/fundamentals/p2_power_model.py --instrument NQ
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from p1_ride_through import (FLOOR, all_calendar_minutes, load_tv_events)  # noqa: E402

MIN_PRIOR = 8          # events with fewer prior same-series releases are excluded from scoring
N_SHUFFLE = 200        # V3 permutations
SEED = 20260819


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    if not np.isfinite(r) or n < 10:
        return (np.nan, np.nan)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    return float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))


def realized_moves(df: pd.DataFrame, stamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Per timestamp: release-bar |open->close|% and the resolution-window |move|%."""
    idx = pd.Index(df["Date"])
    op, cl = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    pos = idx.get_indexer(pd.DatetimeIndex(stamps).floor("min"))
    jump, res = [], []
    for p in pos:
        if p < 1 or p + 15 >= len(op) or op[p] <= 0:
            jump.append(np.nan), res.append(np.nan)
            continue
        jump.append(abs(cl[p] - op[p]) / op[p] * 100.0)
        res.append(abs(cl[p + 15] - cl[p - 1]) / cl[p - 1] * 100.0)
    return pd.DataFrame({"jump_pct": jump, "res_pct": res})


def build_predictions(ev: pd.DataFrame, titles: pd.Series, trailing: int = 0) -> pd.Series:
    """Shifted median of jump_pct within each series — the whole model.

    trailing=0 (the PRE-REGISTERED primary): expanding median over the full prior history.
    trailing=N (declared POST-HOC variant, #126): median of the last N prior releases only.
    ⚠️ Why the variant exists: the first run showed the expanding median lags REGIME SHIFTS in a
    series' power — NQ CPI predicted 0.045% vs realized 0.42% mean (the window still remembers
    2016-2020, when CPI moved nothing). The variant is reported beside the primary, never instead
    of it, and passes through the identical V1/V3/control gates.
    """
    out = pd.Series(np.nan, index=ev.index)
    for _t, g in ev.groupby(titles):
        if trailing:
            med = g.jump_pct.rolling(trailing, min_periods=MIN_PRIOR).median().shift(1)
        else:
            med = g.jump_pct.expanding(MIN_PRIOR).median().shift(1)
        out.loc[g.index] = med
    return out


def draw_paired_controls(events: pd.DatetimeIndex, lo_d, hi_d, seed: int) -> list:
    """One clean control timestamp PER event (aligned; None where no clean draw found)."""
    rng = np.random.default_rng(seed)
    cal = all_calendar_minutes()
    by_day: dict = {}
    for ts in cal:
        by_day.setdefault(ts.normalize(), []).append(ts)
    by_day = {k: pd.DatetimeIndex(sorted(v)) for k, v in by_day.items()}

    def clean(c) -> bool:
        near = by_day.get(c.normalize())
        if near is None:
            return True
        i = near.searchsorted(c)
        return not any(0 <= j < len(near) and abs((near[j] - c).total_seconds()) < 3600
                       for j in (i - 1, i))

    out = []
    for t in events:
        pick = None
        for _ in range(60):
            shift = int(rng.integers(3, 500)) * (1 if rng.random() < 0.5 else -1)
            c = pd.Timestamp(t) - pd.Timedelta(days=shift)
            if lo_d <= c <= hi_d and c.weekday() < 5 and clean(c):
                pick = c
                break
        out.append(pick)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ", choices=list(FLOOR))
    ap.add_argument("--trailing", type=int, default=0,
                    help="0 = pre-registered expanding median; N = declared trailing-N variant")
    a = ap.parse_args()
    inst = a.instrument

    from scipy import stats
    from optimize.fundamentals.extended_data import load_1m_extended

    raw = load_tv_events(inst)
    # |forecast - previous| for the secondary feature test (re-read: load_tv_events drops the values)
    tvr = pd.read_csv(HERE / "tradingview" / "tv_us_calendar_raw.csv", low_memory=False)
    tvr["utc"] = pd.to_datetime(tvr["date"], format="mixed", utc=True)
    tvr["et"] = tvr["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    fp = tvr.dropna(subset=["forecast", "previous"]).copy()
    fp["abs_fp"] = (fp.forecast.astype(float) - fp.previous.astype(float)).abs()
    raw = raw.merge(fp[["title", "et", "abs_fp"]], on=["title", "et"], how="left")

    df = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    ev = pd.concat([raw.reset_index(drop=True),
                    realized_moves(df, pd.DatetimeIndex(raw.et))], axis=1)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)

    ev["pred"] = build_predictions(ev, ev.title, a.trailing)
    scored = ev.dropna(subset=["pred"]).copy()
    n_excl = len(ev) - len(scored)

    print("=" * 100)
    mode = f"trailing-{a.trailing} VARIANT (post-hoc, declared)" if a.trailing else "expanding (PRE-REGISTERED primary)"
    print(f"WS-NEWS3 M2 (#126) — the power model, {inst} — {mode}")
    print("=" * 100)
    print(f"  events {len(ev)} · scored {len(scored)} (excluded {n_excl} with <{MIN_PRIOR} priors) · "
          f"series {sorted(ev.title.unique())}")

    # ---- primary --------------------------------------------------------------------------------
    r, p = stats.spearmanr(scored.pred, scored.jump_pct)
    lo, hi = fisher_ci(r, len(scored))
    r2, _ = stats.spearmanr(scored.pred, scored.res_pct)
    print(f"\n  PRIMARY pooled OOS Spearman(P_hist, jump_pct) = {r:+.3f} [{lo:+.3f},{hi:+.3f}] "
          f"(p={p:.2e}, n={len(scored)})   [resolution-window variant {r2:+.3f}]")
    primary_pass = bool(lo > 0)

    # ---- V1 — quintile scorer -------------------------------------------------------------------
    q = pd.qcut(scored.pred, 5, labels=False, duplicates="drop")
    bucket_means = scored.groupby(q).jump_pct.mean()
    rv1, _ = stats.spearmanr(bucket_means.index.to_numpy(), bucket_means.to_numpy())
    v1_pass = bool(rv1 >= 0.8)
    print(f"  V1 quintile bucket means {[round(v,3) for v in bucket_means]} -> Spearman {rv1:+.2f} "
          f"{'PASS' if v1_pass else 'FAIL'}")

    # ---- V2 — known anchors ---------------------------------------------------------------------
    rank = (scored.groupby("title").pred.median().sort_values(ascending=False))
    top2 = list(rank.index[:2])
    if inst == "CL":
        v2_pass = sum(("EIA" in t or "API" in t) for t in top2) == 2
    elif inst in ("NQ", "ES", "RTY"):
        v2_pass = any("Inflation Rate MoM" == t for t in top2)
    else:
        v2_pass = True   # GC: no pre-registered anchor
    print(f"  V2 predicted-power ranking: {list(rank.round(4).items())}")
    print(f"     top-2 {top2} -> {'PASS' if v2_pass else 'FAIL'}")

    # ---- V3 — series-label shuffle --------------------------------------------------------------
    rng = np.random.default_rng(SEED)
    shuffled = []
    labels = ev.title.to_numpy().copy()
    for _ in range(N_SHUFFLE):
        rng.shuffle(labels)
        pred_s = build_predictions(ev, pd.Series(labels, index=ev.index), a.trailing)
        m = pred_s.notna() & ev.jump_pct.notna()
        rs, _ = stats.spearmanr(pred_s[m], ev.jump_pct[m])
        shuffled.append(rs)
    p95 = float(np.nanpercentile(shuffled, 95))
    v3_pass = bool(r > p95)
    print(f"  V3 shuffled-label Spearman: median {np.nanmedian(shuffled):+.3f}, p95 {p95:+.3f} "
          f"vs observed {r:+.3f} -> {'PASS' if v3_pass else 'FAIL — vol clustering, VOID'}")

    # ---- dumb control — same predictions vs no-news minutes -------------------------------------
    ctrl = draw_paired_controls(pd.DatetimeIndex(scored.et), df.Date.min(), df.Date.max(), SEED)
    keep = [i for i, c in enumerate(ctrl) if c is not None]
    cm = realized_moves(df, pd.DatetimeIndex([ctrl[i] for i in keep]))
    cs = scored.iloc[keep].reset_index(drop=True)
    m = cm.jump_pct.notna()
    rc, _ = stats.spearmanr(cs.pred[m.to_numpy()], cm.jump_pct[m])
    ctl_pass = bool(not np.isfinite(rc) or rc < r - 0.15)
    print(f"  CONTROL Spearman(P_hist, no-news-minute |move|) = {rc:+.3f} (n={int(m.sum())}) "
          f"-> {'materially weaker: PASS' if ctl_pass else 'NOT weaker: FAIL'}")

    # ---- secondary — does |forecast-previous| add anything? -------------------------------------
    s2 = scored.dropna(subset=["abs_fp"]).copy()
    s2["fp_z"] = np.nan
    for _t, g in s2.groupby("title"):
        mu = g.abs_fp.expanding(MIN_PRIOR).mean().shift(1)
        sd = g.abs_fp.expanding(MIN_PRIOR).std().shift(1)
        s2.loc[g.index, "fp_z"] = (g.abs_fp - mu) / sd
    s2 = s2.dropna(subset=["fp_z"])
    resid_rank = s2.jump_pct.rank() - s2.pred.rank()
    rf, pf = stats.spearmanr(s2.fp_z, resid_rank)
    print(f"  SECONDARY |forecast-previous| on residual: Spearman {rf:+.3f} (p={pf:.3f}, n={len(s2)})")

    # ---- deliverable: the selection table -------------------------------------------------------
    tab = (scored.groupby("title")
           .agg(n=("jump_pct", "size"), pred_med=("pred", "median"),
                realized_med=("jump_pct", "median"), realized_mean=("jump_pct", "mean"))
           .sort_values("pred_med", ascending=False).reset_index())
    tab["instrument"] = inst
    tab["unverified"] = tab.title.map(dict(zip(scored.title, scored.unverified)))
    sfx = f"_t{a.trailing}" if a.trailing else ""
    tab.to_csv(HERE / f"p2_power_rank_{inst}{sfx}.csv", index=False)
    scored[["title", "et", "unverified", "jump_pct", "res_pct", "pred", "abs_fp"]].to_csv(
        HERE / f"p2_power_events_{inst}{sfx}.csv", index=False)

    out = {"instrument": inst, "n_events": int(len(ev)), "n_scored": int(len(scored)),
           "n_excluded_lt_min_prior": int(n_excl), "min_prior": MIN_PRIOR,
           "primary": {"spearman": float(r), "ci": [lo, hi], "p": float(p), "pass": primary_pass,
                       "resolution_variant": float(r2)},
           "v1_quintiles": {"bucket_means": [float(v) for v in bucket_means],
                            "spearman": float(rv1), "pass": v1_pass},
           "v2_rank_top2": top2, "v2_pass": bool(v2_pass),
           "v3_shuffle": {"median": float(np.nanmedian(shuffled)), "p95": p95, "pass": v3_pass},
           "control": {"spearman": float(rc) if np.isfinite(rc) else None, "pass": ctl_pass},
           "secondary_fp": {"spearman": float(rf), "p": float(pf), "n": int(len(s2))}}
    (HERE / f"p2_power_result_{inst}{sfx}.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote p2_power_rank_{inst}{sfx}.csv (+events, +result json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
