"""Workstream C1 — high-frequency deep learning on 1-min data, PRICE-RETURN target.

Goal: directly test the hypothesis "the transformer only failed for lack of data — give it
~487k one-minute bars and it will predict price." We train a Darts deep model to forecast the
next 1-min log-return and compare its price reconstruction to the naive guess (next price =
last price). Per the measured 1-min return ACF (~-0.006, i.e. white noise) the expectation is
that it still does NOT beat naive — this run is the rigorous proof, on real GPU + real data.

Unlike the 4h tournament (585 eval bars, retrain-every-20), 1-min has ~487k bars, so we use a
single chronological train/test split + 1-step `historical_forecasts(retrain=False)` over the
test tail. That scales; per-bar retraining would mean tens of thousands of fits.

Usage (on the GPU server, with MP_ACCELERATOR=gpu + HSA override exported):
    python 40_hf_1min_dl.py --csv data/NQ_1m.csv --model nbeats --epochs 10 \
        --input-chunk 60 --test-bars 20000 --stride 1 --out runs/c1_nbeats
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


def build_model(name: str, input_chunk: int, epochs: int, batch: int):
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
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    df = pd.read_csv(a.csv, usecols=["datetime", "close"])
    close = df["close"].astype(float).to_numpy()
    logret = np.diff(np.log(close))                      # target: next-bar log return
    n = len(logret)
    print(f"[c1] device={_ACCEL} model={a.model} bars={n:,} test_bars={a.test_bars} "
          f"input_chunk={a.input_chunk} epochs={a.epochs}", flush=True)

    y = TimeSeries.from_values(logret.reshape(-1, 1), columns=["logret"])
    split = n - a.test_bars
    train, _ = y[:split], y[split:]
    print(f"[c1] train={split:,}  test={a.test_bars:,}", flush=True)

    model = build_model(a.model, a.input_chunk, a.epochs, a.batch)
    print(f"[c1] fitting ...", flush=True)
    model.fit(train)
    print(f"[c1] fit done in {time.time()-t0:.1f}s; forecasting test tail ...", flush=True)

    # 1-step-ahead forecasts across the test region, no retrain (scalable).
    start = split
    fc = model.historical_forecasts(
        series=y, start=start, forecast_horizon=1, stride=a.stride,
        retrain=False, last_points_only=True, verbose=False,
    )
    yhat_ret = fc.values().reshape(-1)
    idx = np.arange(start, start + len(yhat_ret) * a.stride, a.stride)[: len(yhat_ret)]
    ytrue_ret = logret[idx]

    # Reconstruct price; naive = predict next price == last price (ret_hat = 0).
    prev_close = close[idx]                 # close[t-1] (logret[i] is return INTO bar i+1)
    yhat_price = prev_close * np.exp(yhat_ret)
    ytrue_price = close[idx + 1]
    naive_price = prev_close                # naive: next price = last price

    def rmse(a_, b_): return float(np.sqrt(np.mean((a_ - b_) ** 2)))
    rmse_model = rmse(ytrue_price, yhat_price)
    rmse_naive = rmse(ytrue_price, naive_price)
    hit = float(np.mean(np.sign(yhat_ret) == np.sign(ytrue_ret)) * 100)
    lift = float((rmse_naive - rmse_model) / rmse_naive * 100)

    pd.DataFrame({"idx": idx, "y_true_price": ytrue_price, "y_hat_price": yhat_price,
                  "naive_price": naive_price, "y_true_return": ytrue_ret,
                  "y_hat_return": yhat_ret}).to_csv(Path(a.out) / "preds.csv", index=False)
    result = dict(model=a.model, device=_ACCEL, n_test=int(len(idx)),
                  rmse_model=rmse_model, rmse_naive=rmse_naive, lift_vs_naive_pct=lift,
                  hit_rate_pct=hit, wall_s=round(time.time() - t0, 1),
                  input_chunk=a.input_chunk, epochs=a.epochs, stride=a.stride)
    with open(Path(a.out) / "result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"[c1] DONE  rmse_model={rmse_model:.4f} rmse_naive={rmse_naive:.4f} "
          f"lift={lift:+.3f}% hit={hit:.2f}%  ({result['wall_s']}s)", flush=True)
    print(f"[c1] {'BEATS naive' if lift>0 else 'loses to naive'} (expected: loses)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
