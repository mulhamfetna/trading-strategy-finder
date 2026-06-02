"""Workstream C2 — high-frequency deep learning on the 1-min VOLATILITY target.

C1 proved direction is unpredictable even with 487k bars. But 1-min RANGE is strongly
autocorrelated (ACF ~0.75). Here we point the same GPU deep models (NBEATS/LSTM/Transformer)
at next-bar range, and ask: do they beat the strong volatility baselines (persistence + EWMA)?

Target: log range, where range_t = (high_t - low_t) / close_t  (positive, persistent). We model
log(range) for numerical stability (the scaling lesson from notes/38), then reconstruct.

Baselines: naive persistence (next range = last range) and EWMA(span). A model is useful only
if it beats the BEST baseline (volatility is easy to beat-naive on; the bar is EWMA/HAR).

Usage (GPU server, MP_ACCELERATOR=gpu + HSA override exported):
    python 42_hf_vol_dl.py --csv data/NQ_1m.csv --model nbeats --epochs 10 \
        --input-chunk 60 --test-bars 20000 --out runs/c2_nbeats
"""
from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_ACCEL = os.environ.get("MP_ACCELERATOR", "cpu").lower()
if _ACCEL == "cpu":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from darts import TimeSeries  # noqa: E402

PL_KW = {"enable_progress_bar": False, "enable_model_summary": False, "logger": False,
         "accelerator": _ACCEL}
if _ACCEL == "gpu":
    PL_KW["devices"] = 1


def build_model(name, input_chunk, epochs, batch):
    common = dict(input_chunk_length=input_chunk, output_chunk_length=1, n_epochs=epochs,
                  random_state=42, force_reset=True, batch_size=batch, pl_trainer_kwargs=PL_KW)
    if name == "nbeats":
        from darts.models import NBEATSModel
        return NBEATSModel(num_stacks=2, num_blocks=2, num_layers=2, layer_widths=128, **common)
    if name == "lstm":
        from darts.models import RNNModel
        return RNNModel(model="LSTM", training_length=input_chunk * 2, hidden_dim=32,
                        n_rnn_layers=1, **common)
    if name == "transformer":
        from darts.models import TransformerModel
        return TransformerModel(d_model=32, nhead=4, num_encoder_layers=2,
                                num_decoder_layers=2, dim_feedforward=128, **common)
    raise SystemExit(f"unknown model {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--model", default="nbeats", choices=["nbeats", "lstm", "transformer"])
    ap.add_argument("--input-chunk", type=int, default=60)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--test-bars", type=int, default=20000)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--ewma-span", type=int, default=60)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    df = pd.read_csv(a.csv, usecols=["high", "low", "close"])
    hi, lo, cl = (df[c].astype(float).to_numpy() for c in ("high", "low", "close"))
    rng = (hi - lo) / cl                          # bar range / close  (>=0, persistent)
    eps = 1e-6
    logrng = np.log(rng + eps)
    n = len(logrng)
    print(f"[c2] device={_ACCEL} model={a.model} bars={n:,} test={a.test_bars} "
          f"target=log_range input_chunk={a.input_chunk} epochs={a.epochs}", flush=True)

    y = TimeSeries.from_values(logrng.reshape(-1, 1), columns=["log_range"])
    split = n - a.test_bars
    model = build_model(a.model, a.input_chunk, a.epochs, a.batch)
    print(f"[c2] fitting on {split:,} bars ...", flush=True)
    model.fit(y[:split])
    print(f"[c2] fit done {time.time()-t0:.1f}s; forecasting ...", flush=True)

    fc = model.historical_forecasts(series=y, start=split, forecast_horizon=1,
                                    stride=a.stride, retrain=False, last_points_only=True,
                                    verbose=False)
    yhat_log = fc.values().reshape(-1)
    idx = np.arange(split, split + len(yhat_log) * a.stride, a.stride)[: len(yhat_log)]
    ytrue = rng[idx]                              # actual range at forecast bars
    yhat = np.exp(yhat_log) - eps                 # model prediction (back to range)

    # baselines on the same bars
    naive = rng[idx - 1]                          # persistence: last bar's range
    ewma = pd.Series(rng).ewm(span=a.ewma_span, adjust=False).mean().to_numpy()[idx - 1]

    def rmse(p): return float(np.sqrt(np.mean((ytrue - p) ** 2)))
    def qlike(p):  # volatility loss: penalises under-prediction; uses variance=range^2 proxy
        v_true = np.maximum(ytrue, eps) ** 2; v_pred = np.maximum(p, eps) ** 2
        return float(np.mean(v_true / v_pred - np.log(v_true / v_pred) - 1))
    r_model, r_naive, r_ewma = rmse(yhat), rmse(naive), rmse(ewma)
    best_base = min(r_naive, r_ewma)
    lift_naive = (r_naive - r_model) / r_naive * 100
    lift_best = (best_base - r_model) / best_base * 100

    pd.DataFrame({"idx": idx, "y_true_range": ytrue, "y_hat_range": yhat,
                  "naive": naive, "ewma": ewma}).to_csv(Path(a.out) / "preds.csv", index=False)
    result = dict(model=a.model, device=_ACCEL, target="log_range", n_test=int(len(idx)),
                  rmse_model=r_model, rmse_naive=r_naive, rmse_ewma=r_ewma,
                  qlike_model=qlike(yhat), qlike_naive=qlike(naive), qlike_ewma=qlike(ewma),
                  lift_vs_naive_pct=lift_naive, lift_vs_best_baseline_pct=lift_best,
                  best_baseline=("ewma" if r_ewma < r_naive else "naive"),
                  wall_s=round(time.time() - t0, 1), epochs=a.epochs, input_chunk=a.input_chunk)
    with open(Path(a.out) / "result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"[c2] DONE rmse: model={r_model:.6f} naive={r_naive:.6f} ewma={r_ewma:.6f} | "
          f"lift_vs_naive={lift_naive:+.2f}% lift_vs_best={lift_best:+.2f}% ({result['wall_s']}s)",
          flush=True)
    print(f"[c2] {'BEATS' if lift_best>0 else 'loses to'} best baseline "
          f"({result['best_baseline']}) — volatility {'IS' if lift_best>0 else 'not (vs that baseline)'} learnable here",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
