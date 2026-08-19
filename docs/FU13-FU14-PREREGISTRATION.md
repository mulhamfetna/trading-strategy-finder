# FU-13 (#165) + FU-14 (#166) pre-registration — the two unused winners, end-to-end

**Filed BEFORE any run. Owner instruction: full pipeline (my testing → core → dashboard),
deploy ONLY if every stage passes with the expected outcomes; then verbose documentation,
playbook bundle, high-level overview + achievement summary.**

## The honest starting state (from the committed records, not the index hooks)

- **FU-13 / Exp2 sizing ramp**: Exp2b called it GREEN; the SECOND TEST **downgraded it to
  QUALIFIED** — the *signal* is real (regime→size ordering beats 96 % of random maps, helps
  4/5 purged folds and all 3 years) but the *dollar magnitude* is unconfirmed (equal-risk
  +$10.4k with 90 % CI **[−$21,075, +$60,937]** — includes zero) on the n=1 2024-26 NQ
  combined book. It already ships as an EXPERIMENTAL OFF-by-default overlay
  (`apply_regime_sizing.py`, dashboard `regime_overlay`, byte-identical when OFF). Its own
  recorded upgrade path: a longer / independent book confirms or kills the magnitude. Known:
  helps L2+combined, HURTS L1-alone → combined book only.
- **FU-14 / M2 power model**: confirmed forecast (pooled OOS Spearman **0.5907** on NQ t24,
  CI [0.533, 0.643]; V1 quintiles 1.0; V3 shuffle-beat; control weak as required; the
  recorded V2 nuance: NFP/FOMC out-rank CPI on *predicted* power — POWER ≠ PREMIUM). Consumed
  by no live layer.

## FU-13 — stages and PASS lines (fixed now)

| stage | what runs | expected outcome (PASS line) |
|---|---|---|
| R (reproduce) | regenerate the NQ 1h+4h combined book (the dashboard/L2 machinery), apply the committed overlay + committed `nq_daily_regime.csv` | OFF book ≈ the deploy card ($151,872 / $27,508 / 5.52) and ON = ($162,228 / $27,508 held / 5.90); tolerance: exact if the book regenerates identically, else every gap itemized and explained before proceeding |
| X (independent book) | the SAME a-priori ramp (0.5×→1.5×, equal-risk) on the **ES combined book** with ES's own causal daily regime (rebuilt by `precompute_regime.py` methodology) | directional agreement (uplift > 0 at equal risk) |
| M (magnitude, the decisive test) | pooled NQ+ES equal-risk uplift, bootstrap | **90 % CI > 0** AND ordering beats **≥95 % of 1,000 random regime→size maps (pooled)** AND helps **≥70 % of pooled purged folds** |
| C (core) | golden gate 6/6 (the overlay is post-book, engine untouched); overlay OFF byte-identity re-verified | ALL MATCH; OFF ≡ flat |
| D (dashboard) | `regime_overlay.overlay_from_log` output ≡ `apply_regime_sizing` on the same log; dashboard run with overlay ON, SSH+Playwright screenshots | parity exact; visual inspection matches the study numbers |
| **DEPLOY rule** | | ALL of R∧X∧M∧C∧D ⇒ status flips EXPERIMENTAL→**DEPLOYED** (combined book, ops-enabled, documented); ANY failure ⇒ **NOT-DEPLOYED**, verdict recorded, overlay stays experimental-off. The M stage is expected to be the decider — that is the point. |

## FU-14 — stages and PASS lines (fixed now)

| stage | what runs | expected outcome (PASS line) |
|---|---|---|
| B (build) | `src/deploy/power_forecast.py`: P_hist = expanding median of the same (series×instrument) prior release |move|%, shifted one release, ≥8 priors — seeded from the COMMITTED per-event evidence (`p2_power_events_{inst}_t24.csv`), emitting (a) historical parity vectors and (b) the forward-schedule night-before forecast artifact (JSONL, the paper-intents pattern) | module exists, self-contained, no engine imports touched |
| P (parity) | per-event P_hist recomputed vs the committed evidence | equal within 1e-9 on every scored event, all 5 instruments |
| S (statistic) | the primary Spearman recomputed from the parity vectors | 0.5907 ± 0.0001 on NQ t24 (and each instrument's committed value) |
| F (falsifier) | scrambled series labels through the module | correlation collapses toward the committed shuffle median (≈0.20), NOT the real 0.59 |
| A (artifact) | `--now <historical date>` forward forecast vs what actually happened next | the emitted events match the schedule; per-event predicted power finite and rank-consistent with the committed model |
| D (dashboard/ops) | the artifact generated on the server, inspected; golden gate re-run | golden 6/6; artifact well-formed |
| **DEPLOY rule** | | ALL green ⇒ DEPLOYED as an ops layer (nightly forward power forecasts; NO trading consumer — consumers remain separate gated studies, per the system analysis). Any failure ⇒ NOT-DEPLOYED. |

## Blind spots (declared)

1. FU-13's X-stage ES book is one more instrument, not a population; the pooled M gate is the
   pre-registered bar and will not be lowered if it fails.
2. FU-13 R depends on regenerating the 2024-26 combined book byte-comparably; parameter drift
   since 2026-07 is possible and will be itemized, not papered over.
3. FU-14 seeds history from the committed evidence files (not a fresh 1s recompute) — the
   parity stage makes that circularity explicit; a fresh-recompute mode is listed as a
   follow-up, not smuggled in.
4. Deploying FU-14 changes no P&L — it is an information layer; the achievement summary must
   not describe it as income.
