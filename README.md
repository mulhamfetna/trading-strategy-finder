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
| `docs/` | Workflow proposals and long-form references. Era-expired documents are kept under era-labelled names (e.g. `START-HERE-2026-08-legacy18-onboarding.md`) and `docs/archive/` — historical record, not current instructions. **`docs/POSITIONING.md`** — where this work sits in the field, rung by rung, each cell linked to its evidence; `docs/POSITIONING-AUDIT-2026-08-29.md` — the measured audit behind it. |

| `src/deploy/` | **The live deployment layer** — the news-release executor (`release_executor.py`, v5.3.0–v5.4.2), the deployed power-forecast model (`power_forecast.py`, v5.4.3), the regime monitor and its schedule. The only code that touches an account. Covered by the 157-test root suite. |
| `subprojects/Parametric-Indicators/shareable/`, `server-audit/` | **Snapshots, not live code** — hand-off bundles and the harvested server archive (#94). Each carries its own README saying so. |

The frozen **v1.x** era (`src/main/`) is preserved under the `v1.0.0` / `v1.0-working` tags.

## Two tiers of reproducibility (read this before judging the numbers)

1. **Every published number re-derives from committed evidence — anyone, offline.**
   `cd subprojects/Parametric-Indicators && python3 optimize/verify/run.py` replays the claims ledger
   (79 claims, each with three verifications that must fail for different reasons and a declared blind
   spot) against JSON/CSV files in this repo. No market data needed. `--selftest` proves the gate can fail
   (5 historical defects rejected). The ledger also refuses any claim whose evidence is not in git.
2. **Recomputing the evidence from raw prices — server-only.** The 1-second/1-minute futures tape is
   licensed and lives only on the compute server (`docs/DATA-AND-KNOWLEDGE-MAP.md`). Tier 1 is what an
   outside reviewer can do today; tier 2 is what the owner can do.

## Findings you can quote (each line is a machine-verified ledger claim)

Every number below re-derives offline from committed evidence via the claims ledger; the bracketed ID is
the claim to replay. Negative results are published with the same rigor as positive ones — each carries a
power analysis, and each positive carries a dumb control and a noise check.

**Does opening-range breakout (ORB) survive realistic trading costs?** No. A pre-registered 225-cell grid
(9 futures instruments × 2 session anchors × 4 window lengths × 3 exit rules, 16 years of 1-minute data,
2010–2026) produced **zero** cells meeting the positive bar at $25/round-trip; 28 cells are negative *with
power* (MDE ≤ $25/trade), and the literature's favourite 5-minute window is the worst of the four.
The best-looking cell fails a random-anchor control — it is volatility expansion, not an "open" effect.
[`ORB-GRID-NO-POSITIVE-CELL`]

**Do optimized backtest champions hold up on genuinely fresh data?** Mostly no — and we publish that. On
the first strictly out-of-sample forward window, 3,733 trades earned +$29,807 raw but **−$63,518 at
$25/round-trip**; the fleet's per-trade mean decayed to 17.6% of what the selection window predicted
(decay t = −2.53). Only the 4-hour timeframe stayed positive after stressed costs.
[`FWD2-FRESH-WINDOW`]

**Is anything left after that honesty?** Yes, narrowly. A pre-registered scheduled-news entry (long NQ at
release −300 s on CPI/NFP/FOMC, fixed stop/target) survives Bonferroni correction and stressed costs at
+$133/event net, t = 4.13 — with its era-concentration declared in the claim itself.
[`P3-LONG-RELEASE-TRADE-CONFIRMED`]

**How is the live universe chosen?** By a frozen rule, not by hand: five pre-registered criteria applied
to the forward books admit exactly 9 of 54 instrument/timeframe slots, beating a random-set control.
[`LIVE-ALLOWLIST-FROZEN`]

## The track record (out-of-sample by construction)

Since **2026-08-31** the deployed parameter set and the 9-slot universe are hash-frozen under a signed,
amendment-only protocol ([`docs/LIVE-PROTOCOL.md`](docs/LIVE-PROTOCOL.md), claim
[`LIVE-PROTOCOL-SIGNED`]). Each new data drop is audited against the previous one (a repaint check), then
replayed with the frozen set — so every recorded window is out-of-sample *by construction*: the
parameters were pinned and published before the data existed. One contract always, stressed-cost views
alongside raw, no verdict before the pre-registered power threshold, and a negative outcome is a
publishable result of the protocol, not a failure of it. Where this places the project among academic and
industry practice, rung by rung with linked evidence: [`docs/POSITIONING.md`](docs/POSITIONING.md).

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
trading-strategy discovery and validation (Version 5.7.0) [Software]. Zenodo.
https://doi.org/10.5281/zenodo.22212233
```

Cite the **version you actually used** (the DOI above is v5.7.0). To cite the project in general — always
resolving to the newest release — use the concept DOI **`10.5281/zenodo.21473312`**. Every version DOI is
listed in [`CITATION.cff`](CITATION.cff).
