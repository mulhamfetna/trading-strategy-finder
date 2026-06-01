"""Phase D.2 — Darts RNNModel (LSTM) with past_covariates (14 bar-open regressors)."""
from _darts_runner import run_darts_model, PL_TRAINER_KWARGS  # type: ignore
from darts.models import RNNModel

run_darts_model(
    name="darts-rnn-regressors (LSTM)",
    model_class=RNNModel,
    model_kwargs=dict(
        model="LSTM", input_chunk_length=12, output_chunk_length=1, training_length=24,
        hidden_dim=16, n_rnn_layers=1, n_epochs=20, random_state=42, force_reset=True,
        pl_trainer_kwargs=PL_TRAINER_KWARGS,
    ),
    use_regressors=True,
    output_filename="10_darts_rnn_regressors.csv",
    retrain_every=20,
)
