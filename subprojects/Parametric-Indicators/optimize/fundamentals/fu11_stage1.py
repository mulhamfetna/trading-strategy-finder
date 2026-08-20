"""FU-11 Stage 1 (#162) — the fused size engine: FORECAST-QUALITY stage.

Implements `docs/FU11-STAGE1-PREREGISTRATION.md` exactly (PASS lines fixed before this ran).
Question: does adding the calendar terms the live vol engine is blind to (event dummy +
M2 night-before power) beat the engine's HAR family AS A FORECAST of its own target rv_pts?

Models (all causal, fits on TRAIN < 2024-01-01 only):
  A deployed-HAR (fixed 0.5/0.3/0.2)  ·  B HAR-LS (fitted)  ·  C fused (B + dummy + power)
  D dummy-only (decomposition)        ·  C* shuffled-power placebo (falsifier, 20 seeds)

Decision statistic: paired per-bar QLIKE differential (B − C) on TEST EVENT BARS,
bootstrap 90% CI. Everything else per the pre-registration.

    WSH_DATA_BASE=... python3 optimize/fundamentals/fu11_stage1.py --instrument NQ --minutes 60
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # Parametric-Indicators root (volatility.py)
sys.path.insert(0, str(HERE))

import p2_power_model as p2                 # noqa: E402
from p1_ride_through import load_tv_events  # noqa: E402
from extended_data import load_1m_extended  # noqa: E402
from volatility import compute_rv_pts       # noqa: E402

TRAIN_END = pd.Timestamp("2024-01-01")      # matches FU-13's convention
ERA_SPLIT = pd.Timestamp("2025-01-01")
N_BOOT, N_SHUFFLE, SEED = 2000, 20, 20260820
EPS = 1e-9


def qlike(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Per-observation QLIKE (meta-prophet definition); mean over bars is the score."""
    vt = np.maximum(y, EPS) ** 2
    vp = np.maximum(p, EPS) ** 2
    return vt / vp - np.log(vt / vp) - 1


def build_frame(df1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Research decision frame: floor-to-`minutes` bars from the 1m closes (declared blind
    spot in the pre-reg: NOT the engine's session frames — same frame for every model)."""
    t = df1["Date"].dt.floor(f"{minutes}min")
    g = df1.groupby(t, sort=True)
    return pd.DataFrame({"Date": g["Date"].first().index,
                         "Close": g["Close"].last().to_numpy()}).reset_index(drop=True)


def har_regressors(rv: np.ndarray) -> np.ndarray:
    s = pd.Series(rv)
    return np.column_stack([
        s.shift(1).to_numpy(),
        s.shift(1).rolling(6).mean().to_numpy(),
        s.shift(1).rolling(30).mean().to_numpy(),
    ])


def deployed_har(rv: np.ndarray) -> np.ndarray:
    """The live engine's fixed-weight forecast on the same regressors."""
    X = har_regressors(rv)
    return 0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 2]


def ols_predict(X: np.ndarray, y: np.ndarray, fit_mask: np.ndarray) -> np.ndarray:
    Z = np.c_[np.ones(len(X)), X]
    beta, *_ = np.linalg.lstsq(Z[fit_mask], y[fit_mask], rcond=None)
    return np.maximum(Z @ beta, EPS), beta


def event_features(ev: pd.DataFrame, starts: np.ndarray, minutes: int,
                   power: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Map scored events onto decision bars: dummy + night-before power (% units)."""
    n = len(starts)
    dummy = np.zeros(n)
    pw = np.zeros(n)
    et = ev["et"].to_numpy()
    idx = np.searchsorted(starts, et, side="right") - 1
    dur = np.timedelta64(int(minutes), "m")
    for k, (i, p_) in enumerate(zip(idx, power.to_numpy(float))):
        if i >= 0 and et[k] < starts[i] + dur and np.isfinite(p_):
            dummy[i] = 1.0
            pw[i] = max(pw[i], p_)
    return dummy, pw


def run(inst: str, minutes: int, out_dir: Path) -> dict:
    print(f"[FU-11 S1] instrument={inst} minutes={minutes} TRAIN_END={TRAIN_END.date()} "
          f"ERA_SPLIT={ERA_SPLIT.date()} N_BOOT={N_BOOT} N_SHUFFLE={N_SHUFFLE} SEED={SEED}",
          flush=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    frame = build_frame(df1, minutes)
    rv = compute_rv_pts(frame, df1, bar_minutes=minutes)
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    dates = frame["Date"]
    starts = frame["Date"].to_numpy()
    print(f"[FU-11 S1] 1m rows={len(df1):,} bars={len(frame):,} "
          f"span {dates.iloc[0]} .. {dates.iloc[-1]}", flush=True)

    # --- M2 events with night-before power (expanding = the pre-registered primary) ---
    raw = load_tv_events(inst)
    ev = pd.concat([raw.reset_index(drop=True),
                    p2.realized_moves(df1, pd.DatetimeIndex(raw.et))], axis=1)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)
    ev["et"] = pd.to_datetime(ev["et"])
    ev["pred_exp"] = p2.build_predictions(ev, ev.title, trailing=0)
    scored = ev.dropna(subset=["pred_exp"]).reset_index(drop=True)
    print(f"[FU-11 S1] events total={len(ev)} scored(≥8 priors)={len(scored)} "
          f"series={sorted(scored.title.unique())}", flush=True)

    dummy, pw = event_features(scored, starts, minutes, scored["pred_exp"])

    # --- models ---
    y = rv
    Xh = har_regressors(rv)
    valid = np.isfinite(Xh).all(1) & np.isfinite(y)
    train = valid & (dates < TRAIN_END).to_numpy()
    test = valid & (dates >= TRAIN_END).to_numpy()
    evt_test = test & (dummy > 0)
    quiet_test = test & (dummy == 0)
    print(f"[FU-11 S1] train bars={train.sum():,} test bars={test.sum():,} "
          f"test EVENT bars={evt_test.sum()} (events in test window)", flush=True)

    pA = np.maximum(deployed_har(rv), EPS)
    pB, bB = ols_predict(Xh, y, train)
    pC, bC = ols_predict(np.c_[Xh, dummy, pw], y, train)
    pD, bD = ols_predict(np.c_[Xh, dummy], y, train)
    print(f"[FU-11 S1] betas B={np.round(bB, 4).tolist()}", flush=True)
    print(f"[FU-11 S1] betas C={np.round(bC, 4).tolist()} (…, dummy, power)", flush=True)
    print(f"[FU-11 S1] betas D={np.round(bD, 4).tolist()} (…, dummy)", flush=True)

    def scores(pred):
        out = {}
        for name, m in (("overall", test), ("event", evt_test), ("quiet", quiet_test)):
            out[name] = {"qlike": float(np.mean(qlike(y[m], pred[m]))),
                         "rmse": float(np.sqrt(np.mean((y[m] - pred[m]) ** 2)))}
        return out

    sc = {k: scores(p_) for k, p_ in (("A_deployed", pA), ("B_har_ls", pB),
                                      ("C_fused", pC), ("D_dummy", pD))}

    # --- decision statistic: paired QLIKE differential (B − C) on test event bars ---
    dloss = qlike(y[evt_test], pB[evt_test]) - qlike(y[evt_test], pC[evt_test])
    rng = np.random.default_rng(SEED)
    n = len(dloss)
    boots = np.array([np.mean(dloss[rng.integers(0, n, n)]) for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    dAC = float(np.mean(qlike(y[evt_test], pA[evt_test]) - qlike(y[evt_test], pC[evt_test])))

    # era halves (sign stability)
    eras = {}
    for name, m in (("2024", evt_test & (dates < ERA_SPLIT).to_numpy()),
                    ("2025plus", evt_test & (dates >= ERA_SPLIT).to_numpy())):
        eras[name] = {"n": int(m.sum()),
                      "mean_diff_B_minus_C": float(np.mean(qlike(y[m], pB[m])
                                                           - qlike(y[m], pC[m])))
                      if m.sum() else None}

    # --- falsifier: shuffled-power placebo (refit C with permuted per-event power) ---
    placebo = []
    for s in range(N_SHUFFLE):
        r2 = np.random.default_rng(SEED + 1 + s)
        pw_sh = event_features(scored, starts, minutes,
                               pd.Series(r2.permutation(scored["pred_exp"].to_numpy()),
                                         index=scored.index))[1]
        pS, _ = ols_predict(np.c_[Xh, dummy, pw_sh], y, train)
        placebo.append(float(np.mean(qlike(y[evt_test], pS[evt_test]))))
    q_pl = float(np.median(placebo))

    # --- PASS evaluation (pre-registered lines; NQ carries lines 1/3/4) ---
    gain_C_over_D = sc["D_dummy"]["event"]["qlike"] - sc["C_fused"]["event"]["qlike"]
    placebo_gain_over_D = sc["D_dummy"]["event"]["qlike"] - q_pl
    line1 = bool(np.mean(dloss) > 0 and ci[0] > 0 and dAC > 0)
    line3 = bool(sc["C_fused"]["overall"]["qlike"]
                 <= 1.001 * sc["B_har_ls"]["overall"]["qlike"])
    line4 = bool(gain_C_over_D <= 0
                 or placebo_gain_over_D <= 0.5 * gain_C_over_D)

    # power analysis material (mandatory if negative)
    sd = float(np.std(dloss, ddof=1)) if n > 1 else float("nan")
    mde = float(1.645 * sd / np.sqrt(n)) if n > 1 else float("nan")

    res = {
        "instrument": inst, "minutes": minutes, "n_train": int(train.sum()),
        "n_test": int(test.sum()), "n_test_event_bars": int(n),
        "scores": sc,
        "decision": {"mean_qlike_diff_B_minus_C_event": float(np.mean(dloss)),
                     "boot90_ci": ci, "mean_diff_A_minus_C_event": dAC,
                     "era_halves": eras},
        "decomposition": {"event_qlike_C": sc["C_fused"]["event"]["qlike"],
                          "event_qlike_D_dummy_only": sc["D_dummy"]["event"]["qlike"],
                          "gain_C_over_D": gain_C_over_D},
        "falsifier": {"placebo_event_qlike_median": q_pl,
                      "placebo_gain_over_D": placebo_gain_over_D,
                      "collapses": line4},
        "pass_lines": {"1_nq_primary_ci_gt0": line1, "3_no_harm_overall": line3,
                       "4_falsifier_collapses": line4},
        "power_analysis": {"sd_diff": sd, "mde_90pct_power_one_sided": mde},
        "betas": {"B": bB.tolist(), "C": bC.tolist(), "D": bD.tolist()},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"fu11_stage1_{inst}_{minutes}m.json"
    dest.write_text(json.dumps(res, indent=2))
    print(f"[FU-11 S1] {inst} {minutes}m: event QLIKE A={sc['A_deployed']['event']['qlike']:.4f} "
          f"B={sc['B_har_ls']['event']['qlike']:.4f} C={sc['C_fused']['event']['qlike']:.4f} "
          f"D={sc['D_dummy']['event']['qlike']:.4f} placebo={q_pl:.4f}", flush=True)
    print(f"[FU-11 S1] decision diff(B−C)={np.mean(dloss):+.4f} CI90={ci} "
          f"lines: 1={line1} 3={line3} 4={line4} -> {dest}", flush=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    run(a.instrument, a.minutes, Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
