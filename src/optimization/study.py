"""Study lifecycle for the NSGA-II optimiser.

`run_study()` is the worker entry point. It:
  1. Creates (or resumes) an Optuna study with SQLite storage.
  2. Iterates trials up to `population_size × generations`.
  3. Calls `objective.evaluate()` per trial.
  4. Emits SSE-ready events via `on_event(event_type, payload)`.
  5. Polls `should_stop()` between trials for graceful cancellation.

The caller (FastAPI endpoint) wires `on_event` to a queue.Queue and runs
this function inside a daemon thread.
"""
from __future__ import annotations

import datetime
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import optuna
import pandas as pd

from src.exceptions import ConfigurationError
from src.optimization.objective import evaluate as evaluate_trial
from src.optimization.persistence import create_study, load_study
from src.optimization.walk_forward import split_folds
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategyParams


SearchSpaceRange = Tuple[float, float]
EventEmitter = Callable[[str, Dict[str, Any]], None]
StopFlag = Callable[[], bool]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _suggest(trial: optuna.Trial, search_space: Dict[str, SearchSpaceRange]) -> Dict[str, float]:
    """Suggest one trial's params. Encodes the sl_hard >= sl_soft + 50 constraint
    via reparameterisation (sl_hard = sl_soft + delta)."""
    sl_soft_lo, sl_soft_hi = search_space['sl_soft_points']
    delta_lo, delta_hi     = search_space['sl_hard_delta']
    tp_lo, tp_hi           = search_space['tp_target_points']

    sl_soft = trial.suggest_float('sl_soft_points', sl_soft_lo, sl_soft_hi)
    delta   = trial.suggest_float('sl_hard_delta',  delta_lo,  delta_hi)
    sl_hard = sl_soft + delta
    tp      = trial.suggest_float('tp_target_points', tp_lo, tp_hi)

    return {
        'sl_soft_points': sl_soft,
        'sl_hard_points': sl_hard,
        'tp_target_points': tp,
    }


def _pareto_payload(study: optuna.Study) -> List[Dict[str, Any]]:
    """Return the current Pareto front as a serialisable list."""
    try:
        best = study.best_trials
    except (ValueError, RuntimeError):
        return []
    return [
        {
            'trial_number': t.number,
            'params': dict(t.params),
            'values': [float(v) for v in t.values],
        }
        for t in best
    ]


def run_study(
    study_name: str,
    baseline_params: BoxStrategyParams,
    box_lookup: BoxLookup,
    df: pd.DataFrame,
    search_space: Dict[str, SearchSpaceRange],
    population_size: int,
    generations: int,
    fold_count: int,
    min_trades_per_fold: int,
    db_path: str,
    on_event: EventEmitter,
    should_stop: StopFlag,
    resume: bool = False,
    max_duration_s: int = 1800,
) -> Dict[str, Any]:
    """Run an NSGA-II study end-to-end.

    Returns a `complete` payload (same shape as the SSE `event: complete`).

    The caller passes a daemon-thread context: `on_event` is called from this
    function's thread; `should_stop` is read between trials.
    """
    if resume:
        study = load_study(study_name=study_name, db_path=db_path)
    else:
        study = create_study(study_name=study_name, db_path=db_path)
        study.set_user_attr('trials_total', population_size * generations)
        study.set_user_attr('started_at', _now_iso())

    folds = split_folds(df, fold_count=fold_count)
    trials_total = int(study.user_attrs['trials_total'])
    trials_done_at_start = sum(
        1 for t in study.trials
        if t.state in (
            optuna.trial.TrialState.COMPLETE,
            optuna.trial.TrialState.PRUNED,
            optuna.trial.TrialState.FAIL,
        )
    )

    on_event('study_started', {
        'study_id': study_name,
        'trials_total': trials_total,
        'started_at': study.user_attrs['started_at'],
        'resumed': resume,
    })

    start_wall = time.perf_counter()
    pruned_count = 0
    fatal_error: Optional[Dict[str, Any]] = None
    trials_remaining = trials_total - trials_done_at_start
    trials_in_this_run = 0

    for _ in range(trials_remaining):
        if should_stop():
            break
        if (time.perf_counter() - start_wall) > max_duration_s:
            on_event('warning', {
                'code': 'max-duration-exceeded',
                'message': f'study halted after {max_duration_s}s wall-clock limit',
                'system_status': {'elapsed_s': time.perf_counter() - start_wall},
            })
            break

        trial = study.ask()
        suggested = _suggest(trial, search_space)
        try:
            values = evaluate_trial(
                suggested_params=suggested,
                baseline_params=baseline_params,
                folds=folds,
                min_trades_per_fold=min_trades_per_fold,
                box_lookup=box_lookup,
            )
            study.tell(trial, list(values))
            on_event('trial', {
                'trial_number': trial.number,
                'params': dict(trial.params),
                'values': [float(v) for v in values],
                'state': 'complete',
                'pruned_reason': None,
            })
        except optuna.TrialPruned as exc:
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
            pruned_count += 1
            on_event('trial', {
                'trial_number': trial.number,
                'params': dict(trial.params),
                'values': [],
                'state': 'pruned',
                'pruned_reason': str(exc),
            })
        except ConfigurationError as exc:
            fatal_error = exc.to_payload()
            on_event('error', fatal_error)
            break
        trials_in_this_run += 1

        on_event('progress', {
            'trials_done': trials_done_at_start + trials_in_this_run,
            'trials_total': trials_total,
            'percent': 100.0 * (trials_done_at_start + trials_in_this_run) / trials_total,
            'current_generation': (trials_done_at_start + trials_in_this_run) // population_size,
            'pareto_size': len(_pareto_payload(study)),
            'elapsed_ms': int((time.perf_counter() - start_wall) * 1000),
        })

        # Generation boundary event.
        if (trials_done_at_start + trials_in_this_run) % population_size == 0:
            on_event('generation', {
                'generation': (trials_done_at_start + trials_in_this_run) // population_size,
                'pareto_front': _pareto_payload(study),
            })

    pareto = _pareto_payload(study)
    pf_sorted = sorted(pareto, key=lambda p: -p['values'][0])  # PF desc
    dd_sorted = sorted(pareto, key=lambda p: p['values'][1])   # MaxDD asc (more negative first)

    complete_payload = {
        'study_id': study_name,
        'pareto_front': pareto,
        'top_5_by_pf': pf_sorted[:5],
        'top_5_by_min_dd': dd_sorted[:5],
        'total_trials': trials_done_at_start + trials_in_this_run,
        'pruned_count': pruned_count,
        'elapsed_ms': int((time.perf_counter() - start_wall) * 1000),
    }
    if fatal_error is None:
        on_event('complete', complete_payload)
    return complete_payload
