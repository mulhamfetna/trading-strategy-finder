
---
title: 'Trading Strategy Finder: a machine-verified, pre-registered research framework for futures trading strategies'
tags:
  - Python
  - quantitative finance
  - backtesting
  - reproducibility
  - pre-registration
  - futures markets
authors:
  - name: Mulham Fetna
    orcid: 0009-0006-4432-798X
    corresponding: true
    affiliation: 1
  - name: Abd Ulfatah Esper
    affiliation: 1
affiliations:
  - name: BeInMedia (Nmo AI), Kuwait City, Kuwait
    index: 1
date: 2026-09-01
bibliography: paper.bib
---

# Summary

Trading Strategy Finder is a Python research framework for discovering and — more importantly —
*honestly validating* futures trading strategies. It combines a parity-locked pair of backtest
engines (a fast vectorized engine and an exact reference engine that must agree trade-for-trade),
a multi-objective optimizer (NSGA-III via Optuna) over a 165-indicator signal registry,
walk-forward fold evaluation, stressed transaction-cost reporting, and a governance layer that is
the project's distinctive contribution: a **machine-verified claims ledger**. Every number the
project publishes is a claim with three independent verifications that must fail for different
reasons, a declared blind spot, and committed evidence files; `optimize/verify/run.py` re-derives
all 79 current claims offline, with no market data, and continuous integration blocks any change
that breaks one. Studies are pre-registered before they run; negative results carry mandatory power
analyses; positive results require dumb controls and noise checks; and the live track record is
out-of-sample by construction, because the deployed parameter set and trading universe are
hash-frozen under a signed, amendment-only protocol before new data exists.

# Statement of need

Backtest research has a well-documented false-positive problem: selection among many implicit
trials, small per-trade effects, and cost assumptions that decide the sign of a result
[@bailey2014pseudo; @harvey2016cross; @white2000reality]. General scientific tooling for
pre-registration does not integrate with trading research pipelines, and popular open-source
backtesters (e.g., Backtrader, Zipline, vectorbt) provide simulation but no *verification
governance*: nothing in them prevents the researcher from silently re-running until something
works. Trading Strategy Finder addresses that gap. The framework's studies of opening-range
breakout (a pre-registered 225-cell, 16-year null), scheduled macroeconomic news, and forward
out-of-sample decay are all replayable by third parties from committed evidence, and the full
pipeline re-runs against any user-supplied one-minute data feed — market data are deliberately
external to the repository, so the software is data-vendor-neutral. The intended audience is
quantitative-finance researchers, reproducibility researchers, and practitioners who need an
auditable standard of evidence for strategy claims.

# Functionality

- **Engines:** causal box-strategy backtester with conservative fill conventions (gap-through fills
  at the bar open, stop-first within a bar), an accelerated engine parity-locked to it, and golden
  regression gates.
- **Optimization:** multi-objective search (Optuna/NSGA-III) with walk-forward folds, feasibility
  constraints, and budget conventions; PostgreSQL-backed studies.
- **Verification:** the claims ledger (79 claims, three verifications + blind spot each, evidence
  required to be git-tracked), a self-test that replays five historical defects, and data-free CI
  (byte-compile, import smoke, engine parity, full ledger) required on protected branches.
- **Protocolized live record:** a signed protocol with a rule-derived instrument allowlist, frozen
  parameters, repaint audits between data drops, and append-only amendments.
- **Reporting:** dashboards and full-book reports with raw/\$10/\$25 stressed-cost views.

The engine test suite runs green on a fresh clone with no market data (data-dependent tests skip
themselves), which is also how the JOSS reviewer can exercise the software.

# Author contributions

M.F.: conceptualization, methodology, software, validation, formal analysis, investigation, data
curation, visualization, project administration, writing. A.U.E.: conceptualization, data curation,
supervision.

# Acknowledgments

This software was developed at **BeInMedia (Nmo AI)** (Kuwait • Dubai • Doha,
https://www.beinmedia.com/), which provided the research infrastructure, computing resources, and
data licensing. Substantial portions of the codebase were developed with the assistance of AI
coding agents operating under the authors' direction; all results are gated by the pre-registered
claims ledger and CI described above.

# References

