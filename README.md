# Trading Strategy Finder

[![CI](https://github.com/mulhamfetna/trading-strategy-finder/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mulhamfetna/trading-strategy-finder/actions/workflows/ci.yml) [![DOI](https://zenodo.org/badge/1237945931.svg)](https://zenodo.org/badge/latestdoi/1237945931) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

A reproducible **quantitative-analysis** research codebase for discovering and validating futures
trading strategies: box-level signal engines, multi-objective optimization, extreme-value risk
modelling, and a discipline of pre-registered, power-analysed, cross-instrument-replicated backtests.

> Developed primarily by **AI agents working in parallel.** If you are an agent (or a human) about to
> contribute, **read [`AGENTS.md`](AGENTS.md) first** — it is the operating contract that keeps parallel
> work from colliding.

## What's here

| Path | What it is |
|---|---|
| `subprojects/Parametric-Indicators/` | **The current engine** — box-strategy backtester, the fast (numpy) + exact engines (parity-locked), the optimizer, the L2 layer, the dashboard, and the golden regression gate (`perf/`). |
| `subprojects/Parametric-Indicators/docs/superpowers/` | The research reports — every verdict, discovery, and honest retraction (news "priced in", gap-aware fills, the Asia-cell fluke, …). |
| `subprojects/Parametric-Indicators/DAILY_REPORTS.md` | The running standup. |
| `docs/` | Workflow proposals and long-form references. **`docs/POSITIONING.md`** — where this work sits in the field, rung by rung, each cell linked to its evidence; `docs/POSITIONING-AUDIT-2026-08-29.md` — the measured audit behind it. |

| `src/deploy/` | **The live deployment layer** — the news-release executor (`release_executor.py`, v5.3.0–v5.4.2), the deployed power-forecast model (`power_forecast.py`, v5.4.3), the regime monitor and its schedule. The only code that touches an account. Covered by the 157-test root suite. |
| `subprojects/Parametric-Indicators/shareable/`, `server-audit/` | **Snapshots, not live code** — hand-off bundles and the harvested server archive (#94). Each carries its own README saying so. |

The frozen **v1.x** era (`src/main/`) is preserved under the `v1.0.0` / `v1.0-working` tags.

## Two tiers of reproducibility (read this before judging the numbers)

1. **Every published number re-derives from committed evidence — anyone, offline.**
   `cd subprojects/Parametric-Indicators && python3 optimize/verify/run.py` replays the claims ledger
   (71 claims, each with three verifications that must fail for different reasons and a declared blind
   spot) against JSON/CSV files in this repo. No market data needed. `--selftest` proves the gate can fail
   (5 historical defects rejected). The ledger also refuses any claim whose evidence is not in git.
2. **Recomputing the evidence from raw prices — server-only.** The 1-second/1-minute futures tape is
   licensed and lives only on the compute server (`docs/DATA-AND-KNOWLEDGE-MAP.md`). Tier 1 is what an
   outside reviewer can do today; tier 2 is what the owner can do.

## Run it

The engine is a Python project under `subprojects/Parametric-Indicators/` (`requirements.txt`, `pytest`).
Price data is **not** in the repo (server-only, gitignored) — see `AGENTS.md §8`. The dashboard, optimizer,
and golden gate run from there.

Tests run from two places, both green on a fresh clone with no data: the repo root (`pytest` → 157 tests,
`src/` + workflow) and the engine directory (`cd subprojects/Parametric-Indicators && pytest` → ~1,070
collected; data-dependent modules skip themselves; the snapshot directories are excluded by its own
`pytest.ini`/`conftest.py`).

## How we work (multi-agent)

`Issue → feat/<issue>-<slug> branch (one worktree) → PR → dev (integration) → main (verified only) →
tag + Release + Zenodo DOI`. Checkpoints are **Releases with DOIs**, never lingering branches. Full rules
in [`AGENTS.md`](AGENTS.md).

## License

**AGPL-3.0-or-later** — see [`LICENSE`](LICENSE). Strong copyleft: derivatives, including works run as a
network service, must remain open-source under the same terms.

## How to cite

GitHub renders a **"Cite this repository"** button from [`CITATION.cff`](CITATION.cff); a DOI is minted
per release via Zenodo (badge above).

```
Fetna, M. (2026). Trading Strategy Finder: a reproducible quantitative-analysis framework for futures
trading-strategy discovery and validation (Version 5.6.0) [Software]. Zenodo.
https://doi.org/10.5281/zenodo.22161256
```

Cite the **version you actually used** (the DOI above is v5.6.0). To cite the project in general — always
resolving to the newest release — use the concept DOI **`10.5281/zenodo.21473312`**. Every version DOI is
listed in [`CITATION.cff`](CITATION.cff).
