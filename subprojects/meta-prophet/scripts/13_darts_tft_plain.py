"""Phase D.5 — Darts TFTModel (Temporal Fusion Transformer), no past_covariates.

TFT requires future_covariates; we synthesize a constant 'bar-index' future-known feature
so the model has something to attend over. Without any covariates TFT can still fit but
requires `add_relative_index=True`.
"""
from _darts_runner import run_darts_model, PL_TRAINER_KWARGS  # type: ignore
from darts.models import TFTModel

run_darts_model(
    name="darts-tft-plain",
    model_class=TFTModel,
    model_kwargs=dict(
        input_chunk_length=12, output_chunk_length=1, n_epochs=15, random_state=42,
        force_reset=True, hidden_size=16, lstm_layers=1, num_attention_heads=2,
        dropout=0.1, batch_size=32, add_relative_index=True,
        pl_trainer_kwargs=PL_TRAINER_KWARGS,
    ),
    use_regressors=False,
    output_filename="13_darts_tft_plain.csv",
    retrain_every=40,  # TFT is slower; cadence relaxed
)
