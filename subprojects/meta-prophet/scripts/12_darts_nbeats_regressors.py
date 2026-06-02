"""Phase D.4 — Darts NBEATSModel with past_covariates."""
from _darts_runner import run_darts_model, PL_TRAINER_KWARGS  # type: ignore
from darts.models import NBEATSModel

run_darts_model(
    name="darts-nbeats-regressors",
    model_class=NBEATSModel,
    model_kwargs=dict(
        input_chunk_length=12, output_chunk_length=1, n_epochs=20, random_state=42,
        force_reset=True, num_stacks=2, num_blocks=2, num_layers=2, layer_widths=64,
        pl_trainer_kwargs=PL_TRAINER_KWARGS,
    ),
    use_regressors=True,
    covariate_kind="past",   # NBEATSModel only supports past_covariates
    output_filename="12_darts_nbeats_regressors.csv",
    retrain_every=20,
)
