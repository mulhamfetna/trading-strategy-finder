"""Phase 5 — consolidate per-model outputs into leaderboard.csv + plots.

NeuralProphet was dropped from the tournament due to NeuralProphet 0.8 +
torch 2.12 + Python 3.14 incompatibilities. See notes/07_phase4_neuralprophet_BLOCKED.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.metrics import compute_all, rmse

MODELS = [
    ("naive",                 "outputs/01_naive.csv"),
    ("prophet",               "outputs/02_prophet.csv"),
    ("arima",                 "outputs/03_arima.csv"),
    ("sarimax-plain",         "outputs/06_sarimax_plain.csv"),
    ("sarimax-regressors",    "outputs/07_sarimax_regressors.csv"),
    ("statsforecast",         "outputs/08_statsforecast_autoarima.csv"),
    ("darts-rnn-plain",       "outputs/09_darts_rnn_plain.csv"),
    ("darts-rnn-regressors",  "outputs/10_darts_rnn_regressors.csv"),
    ("darts-nbeats-plain",    "outputs/11_darts_nbeats_plain.csv"),
    ("darts-nbeats-regressors","outputs/12_darts_nbeats_regressors.csv"),
    ("darts-tft-plain",       "outputs/13_darts_tft_plain.csv"),
    ("darts-tft-regressors",  "outputs/14_darts_tft_regressors.csv"),
]


def main() -> None:
    naive_df = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive_df["y_true_price"].to_numpy(), naive_df["y_hat_price"].to_numpy())

    rows = []
    per_model: dict[str, pd.DataFrame] = {}
    for name, path in MODELS:
        p = ROOT / path
        if not p.exists():
            print(f"  [skip] {name}: {path} missing")
            continue
        df = pd.read_csv(p)
        per_model[name] = df
        m = compute_all(
            y_true_price=df["y_true_price"].to_numpy(),
            y_hat_price=df["y_hat_price"].to_numpy(),
            y_true_ret=df["y_true_return"].to_numpy(),
            y_hat_ret=df["y_hat_return"].to_numpy(),
            rmse_naive=rmse_naive,
        )
        rows.append({"model": name, **m})

    leaderboard = pd.DataFrame(rows).sort_values("rmse")
    leaderboard.to_csv(ROOT / "outputs" / "leaderboard.csv", index=False)
    print(leaderboard.to_string(index=False))

    # Leaderboard bar chart
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, col, title in zip(axes,
                              ["rmse", "mape", "lift_vs_naive"],
                              ["RMSE ($)", "MAPE (%)", "Lift vs naive (%)"]):
        ax.bar(leaderboard["model"], leaderboard[col])
        ax.set_title(title); ax.tick_params(axis="x", rotation=20); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(ROOT / "plots" / "leaderboard.png", dpi=120); plt.close(fig)

    # Per-model trajectory plots
    for name, df in per_model.items():
        df["datetime"] = pd.to_datetime(df["datetime"])
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["datetime"], df["y_true_price"], label="actual", linewidth=0.8)
        ax.plot(df["datetime"], df["y_hat_price"],  label=name, linewidth=0.8, alpha=0.8)
        ax.set_title(f"{name} — 2026 walk-forward"); ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(ROOT / "plots" / f"{name}_trajectory.png", dpi=120); plt.close(fig)

    # Error distribution overlay
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, df in per_model.items():
        err = np.abs(df["y_true_price"] - df["y_hat_price"])
        ax.hist(err, bins=50, alpha=0.5, label=name)
    ax.set_xlabel("|error|  ($)"); ax.set_ylabel("count"); ax.set_title("Per-bar abs-error distribution")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(ROOT / "plots" / "error_distribution.png", dpi=120); plt.close(fig)

    print("plots saved to plots/")


if __name__ == "__main__":
    main()
