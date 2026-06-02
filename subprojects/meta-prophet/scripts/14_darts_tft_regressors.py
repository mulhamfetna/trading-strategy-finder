"""Phase D.6 — Darts TFTModel with past_covariates (14 bar-open regressors)."""
from _darts_runner import run_darts_model, PL_TRAINER_KWARGS  # type: ignore
from darts.models import TFTModel

run_darts_model(
    name="darts-tft-regressors",
    model_class=TFTModel,
    model_kwargs=dict(
        input_chunk_length=12, output_chunk_length=1, n_epochs=15, random_state=42,
        force_reset=True, hidden_size=16, lstm_layers=1, num_attention_heads=2,
        dropout=0.1, batch_size=32, add_relative_index=True,
        pl_trainer_kwargs=PL_TRAINER_KWARGS,
    ),
    use_regressors=True,
    covariate_kind="future",   # TFTModel supports future_covariates (bar-open-known)
    output_filename="14_darts_tft_regressors.csv",
    retrain_every=40,
)
