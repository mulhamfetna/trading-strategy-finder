"""ONE description of an optimizer run, and ONE function that turns it into an argv.

WHY THIS EXISTS (#91). The optimizer invocation used to be constructed in six independent places —
`dashboard/control.py` (what the UI *displays*), `dashboard/runner.py` (what actually *executes*), and
three server shell scripts. `control.py` documented the situation in its own docstring: *"mirrors
remote_wsi.sh's IND_ARGS construction exactly"* — a comment asking humans to keep three implementations
byte-identical, forever.

They did not stay identical. Measured across four configurations, what the UI showed and what the runner
executed **diverged on all four**: the UI displayed `--trials 47100` while the run used `--auto-trials`,
under a `--study-prefix` the UI never mentioned, so an operator could not tell from the screen which
study their run would write to. Their numeric agreement at any moment was a coincidence that had to be
re-established after every change — which is a structure that regenerates bugs rather than a bug.

WHAT THIS DOES NOT CHANGE. The optimizer still runs as a SEPARATE PROCESS, deliberately: a
47,100-trial study runs for hours, and in-process it would block the dashboard, could not be stopped
independently, and would couple the two crashes. Process isolation is a correct design decision — the
defect was the *string* as the interface, not the boundary.

`optimizer.run()` is untouched. This module only removes the freedom for two callers to disagree about
what they are asking it to do.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import optimizer as OPT  # noqa: E402


@dataclass(frozen=True)
class RunSpec:
    """Everything needed to launch one optimizer study. Mirrors `optimizer.run()`'s parameters.

    `trials=None` means "let the optimizer size itself" (`--auto-trials`), which is the normal mode; an
    integer pins an explicit count. `effective_trials()` reports what that resolves to, so the UI can
    show a number without the *command* having to carry one.
    """
    tf: str
    instrument: str = "NQ"
    folds: int = 5
    min_trades: int = 5
    study_prefix: str | None = None
    trials: int | None = None                    # None ⇒ --auto-trials
    trials_per_dim: int = OPT.TRIALS_PER_DIM
    ind_1min: bool = True
    split_sltp: bool = False
    sampler: str | None = None
    only_indicators: tuple[str, ...] = ()
    exclude_indicators: tuple[str, ...] = ()
    reference: str | None = None
    max_enabled: int | None = None
    warm_start: bool = True
    dd_pnl_cap: float | None = None
    train_window: str | None = None
    force_eod: bool = False
    freeze_indicators: bool = False
    contributors: tuple[str, ...] = field(default_factory=tuple)
    # Preflight escapes (#94). Represented HERE, not only on the CLI, because the control centre
    # launches through build_argv — an override the UI cannot express is an override the operator
    # cannot use, and they would reach for --no-preflight (or stop using the UI) instead.
    # #95: the contributor committee scope. Empty ⇒ nothing withheld (the new default); naming keys
    # reimposes the historical exclusion. Here rather than only on the CLI so the control centre can
    # express it — a scope the UI cannot set is a scope the operator cannot choose.
    contrib_exclude: tuple[str, ...] = field(default_factory=tuple)
    # The fusion opt-in (#96). Contributors are a research feature, not a native indicator; naming
    # tokens is not enough on its own, here or on the CLI.
    enable_fusion_contributors: bool = False
    # #96: scope the COMMITTEE. --only-indicators never did this — it scoped the strategy
    # layer and left the committee searching the whole registry, which is the ~9-day cost.
    contrib_only: tuple[str, ...] = field(default_factory=tuple)
    allow_dirty: bool = False
    allow_behind: bool = False

    # ── derived, so the UI never computes a budget the launch does not use ──────────────────────────
    def effective_trials(self) -> int:
        """The trial count this spec actually results in — explicit, or the ∝-dimension recommendation
        computed WITH the indicator scope (the scope-blind version was an 8x over-budget, #2)."""
        if self.trials is not None:
            return int(self.trials)
        return OPT.recommended_trials(self.split_sltp, self.trials_per_dim,
                                      only_inds=tuple(self.only_indicators),
                                      exclude_inds=tuple(self.exclude_indicators),
                                      # #95: the contributor committee is a SECOND full-registry
                                      # search — it roughly doubles the space. Omitting it here sized
                                      # every contributor run for about half of what it searched.
                                      contrib_tokens=tuple(self.contributors),
                                      contrib_exclude=tuple(self.contrib_exclude),
                                      contrib_only=tuple(self.contrib_only))

    def dims(self) -> dict:
        return OPT.search_dims(self.split_sltp, only_inds=tuple(self.only_indicators),
                               exclude_inds=tuple(self.exclude_indicators))

    def indicators_searched(self) -> int:
        return len(OPT.searchable_indicators(tuple(self.only_indicators),
                                             tuple(self.exclude_indicators)))

    def study_name(self) -> str | None:
        """Mirrors optimizer.py: f'{prefix}_{tf}{suffix}' (suffix empty for NQ)."""
        if not self.study_prefix:
            return None
        return f"{self.study_prefix}_{self.tf}" + ("" if self.instrument == "NQ" else f"_{self.instrument}")


def build_argv(spec: RunSpec, python: str = "python3", unbuffered: bool = False,
               script: str = "optimize/optimizer.py") -> list[str]:
    """The ONE place an optimizer invocation is constructed.

    Field order is deliberately stable so the rendered command is diffable across runs and matches what
    the server scripts have historically emitted.
    """
    argv = [python]
    if unbuffered:
        argv.append("-u")
    argv += [script, str(spec.tf), "--folds", str(spec.folds), "--min-trades", str(spec.min_trades)]
    if spec.study_prefix:
        argv += ["--study-prefix", str(spec.study_prefix)]
    argv += (["--trials", str(int(spec.trials))] if spec.trials is not None else ["--auto-trials"])
    if spec.ind_1min:
        argv.append("--ind-1min")
    if spec.split_sltp:
        argv.append("--split-sltp")
    if spec.sampler:
        argv += ["--sampler", str(spec.sampler)]
    if spec.exclude_indicators:
        argv += ["--exclude-indicators", ",".join(map(str, spec.exclude_indicators))]
    if spec.only_indicators:
        argv += ["--only-indicators", ",".join(map(str, spec.only_indicators))]
    if spec.reference:
        argv += ["--reference", str(spec.reference)]
    if spec.max_enabled:
        argv += ["--max-enabled", str(int(spec.max_enabled))]
    if not spec.warm_start:
        argv.append("--no-warm-start")
    if spec.dd_pnl_cap not in (None, ""):
        argv += ["--dd-pnl-cap", str(spec.dd_pnl_cap)]
    if spec.train_window:
        argv += ["--train-window", str(spec.train_window)]
    if spec.force_eod:
        argv.append("--force-eod")
    if spec.freeze_indicators:
        argv.append("--freeze-indicators")
    if spec.contributors:
        argv += ["--contributors", ",".join(map(str, spec.contributors))]
        if spec.enable_fusion_contributors:
            argv.append("--enable-fusion-contributors")
    if spec.instrument and spec.instrument != "NQ":
        argv += ["--instrument", str(spec.instrument)]
    if spec.contrib_exclude:
        argv += ["--contrib-exclude", ",".join(map(str, spec.contrib_exclude))]
    if spec.contrib_only:
        argv += ["--contrib-only", ",".join(map(str, spec.contrib_only))]
    if spec.allow_dirty:
        argv.append("--allow-dirty")
    if spec.allow_behind:
        argv.append("--allow-behind")
    return argv


def from_cfg(cfg: dict, tf: str | None = None, study_prefix: str | None = None) -> RunSpec:
    """Build a RunSpec from a control-centre config dict.

    Accepts BOTH the raw Run cfg (`trials_mode`/`trials`) and an already-expanded queue cell
    (`auto_trials` + `trials`), which is the same duality `runner._explicit_trials` handled.
    """
    tfs = cfg.get("timeframes") or ([cfg["timeframe"]] if cfg.get("timeframe") else ["4h"])
    tf = str(tf if tf is not None else tfs[0])

    # explicit trial count, or None for auto
    if "auto_trials" in cfg:                                  # expanded queue cell
        trials = None if cfg["auto_trials"] else (int(cfg.get("trials") or 0) or None)
    elif cfg.get("trials_mode") == "one":
        trials = int(cfg.get("trials") or 0) or None
    else:
        trials = None

    return RunSpec(
        tf=tf,
        instrument=str(cfg.get("instrument", "NQ")),
        folds=int(cfg.get("folds", 5)),
        min_trades=int(cfg.get("min_trades", 5)),
        study_prefix=study_prefix,
        trials=trials,
        trials_per_dim=int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM)),
        ind_1min=bool(cfg.get("ind_1min", True)),
        split_sltp=bool(cfg.get("split_sltp", False)),
        sampler=(str(cfg["sampler"]) if cfg.get("sampler") else None),
        only_indicators=tuple(cfg.get("only_indicators") or ()),
        exclude_indicators=tuple(cfg.get("exclude_indicators") or ()),
        reference=(str(cfg["reference"]) if cfg.get("reference") else None),
        max_enabled=(int(cfg["max_enabled"]) if cfg.get("max_enabled") else None),
        warm_start=not bool(cfg.get("cold_start")),
        dd_pnl_cap=(cfg["dd_cap"] if cfg.get("dd_cap") not in (None, "") else None),
        train_window=(str(cfg["train_window"]) if cfg.get("train_window") else None),
        force_eod=bool(cfg.get("force_eod", False)),
        freeze_indicators=bool(cfg.get("freeze_indicators", False)),
        contributors=tuple(cfg.get("contributors") or ()),
        contrib_exclude=tuple(cfg.get("contrib_exclude") or ()),
        enable_fusion_contributors=bool(cfg.get("enable_fusion_contributors")),
        contrib_only=tuple(cfg.get("contrib_only") or ()),
        allow_dirty=bool(cfg.get("allow_dirty")),
        allow_behind=bool(cfg.get("allow_behind")),
    )


def with_prefix(spec: RunSpec, prefix: str) -> RunSpec:
    """The runner assigns the study prefix; the preview must show the SAME spec, prefix included."""
    return replace(spec, study_prefix=prefix)
