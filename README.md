# Trading Strategy Finder

[![DOI](https://zenodo.org/badge/1237945931.svg)](https://zenodo.org/badge/latestdoi/1237945931) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

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
| `docs/` | Workflow proposals and long-form references. |

The frozen **v1.x** era (`src/main/`) is preserved under the `v1.0.0` / `v1.0-working` tags.

## Run it

The engine is a Python project under `subprojects/Parametric-Indicators/` (`requirements.txt`, `pytest`).
Price data is **not** in the repo (server-only, gitignored) — see `AGENTS.md §8`. The dashboard, optimizer,
and golden gate run from there.

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
trading-strategy discovery and validation (Version 5.1.0) [Software].
https://github.com/mulhamfetna/trading-strategy-finder
```
