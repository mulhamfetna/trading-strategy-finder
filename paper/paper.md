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
date: 1 September 2026
bibliography: paper.bib
---

# Summary

Trading Strategy Finder is a Python framework for researching trading strategies on futures
markets — and, centrally, for making the *claims* that come out of that research trustworthy. It
provides backtesting engines, a multi-objective strategy optimizer, and walk-forward evaluation,
like other backtesting tools. Its distinctive contribution is a governance layer: a
**machine-verified claims ledger** in which every number the project publishes exists as an
executable claim — the number is re-derived live from the committed evidence files that produced
it, checked by three independent verifications that must fail for different reasons (one of them a
falsification test), and accompanied by a mandatory declared blind spot. All 79 current claims
replay offline in minutes with no market data, continuous integration blocks any change that breaks
one, and a self-test replays five real historical defects and requires the harness to reject each
one for the right reason. Around the ledger, the framework operationalizes pre-registration with
append-only amendments, mandatory power analysis for negative results, dumb controls and noise
checks for positive ones, stressed transaction-cost reporting, and a live track record whose
parameters are hash-frozen under a signed protocol before evaluation data exists — making it
out-of-sample by construction.

# Statement of need

Trading-strategy research has a structural false-positive problem: the researcher controls the
number of trials, the cost assumptions, and the stopping rule, and effects are small relative to
per-trade noise. The methodology literature has quantified the damage — data-snooping reversals
[@white2000reality], the probability of backtest overfitting [@bailey2014pseudo], and
multiple-testing haircuts across published anomalies [@harvey2016cross] — but the remedies remain
conventions enforced by the same person they constrain. Researchers who want to hold themselves to
a pre-registration standard in this domain currently have no tooling that *binds* their published
numbers to the artifacts that produced them, forces negatives to state their statistical power, or
mechanically prevents the quiet edit of an evidence file. Trading Strategy Finder exists to close
that gap. Its target audience is quantitative-finance researchers, reproducibility researchers, and
practitioners who need an auditable standard of evidence for strategy claims. Market data are
deliberately external to the repository: the pipeline runs against any user-supplied one-minute
data feed, so the framework is data-vendor-neutral, and no data at all are needed to verify any
published claim.

# State of the field

Mature open-source backtesting frameworks — Backtrader [@backtrader], Zipline
[@zipline], and vectorbt [@vectorbt], among others — provide event-driven or vectorized
simulation, portfolio accounting, and performance metrics, and QuantConnect's LEAN provides the
same as a hosted platform. All of them answer "what would this strategy have earned?"; none of them
constrain *how the researcher reports the answer*. Nothing in these tools prevents silent re-runs
until something works, headline results at zero cost assumptions, or negatives discarded without a
power analysis. On the governance side, general pre-registration infrastructure (e.g., the Open
Science Framework [@nosek2018preregistration]) records intent but does not integrate with a
computational pipeline: it cannot re-derive a published number from evidence or fail a build when a
claim breaks. Trading Strategy Finder occupies the intersection: simulation *plus* enforced
verification governance. We know of no other public trading-research codebase in which every
published number is a CI-enforced, falsifier-carrying, machine-replayable claim.

# Software design

Three design decisions carry the framework. **First, verification is a data structure, not a
document.** A claim is an object binding a statement, its evidence-file paths, an executable
`value_fn` re-deriving the headline number within an explicit tolerance, three verifications
required to fail for different reasons, and a non-empty blind-spot declaration; structural rules
reject claims whose evidence is not version-controlled. This makes "the paper says X" a testable
proposition forever, at the cost of authorship overhead per claim — a trade-off we accept because
exploratory work may run unregistered but is unpublishable until registered. **Second, the engines
are redundant on purpose.** A fast vectorized engine and an exact reference engine are
parity-locked (they must agree trade-for-trade in CI) so that speed optimizations can never
silently change results — the parity suite runs data-free on synthetic sessions. **Third, the
framework distrusts its own gates.** A self-test replays five real historical defects from the
project's past — including a claim verified against notes rather than its producing artifact, and a
unit-drift defect — and requires each to be rejected *for the matching reason*, treating
rejection-by-crash as failure; this exists because the gate once passed for the wrong reason.
Optimization (NSGA-III via Optuna [@optuna]) writes to PostgreSQL studies with never-reused
prefixes, so failed campaigns remain on the record.

# Research impact statement

The framework is the instrument of an active 18-month research programme whose outputs are public
and re-derivable: two companion research papers submitted in 2026 — a pre-registered 225-cell,
16-year null result on opening-range breakout, and a methodology paper on the claims ledger itself
— draw every number from this repository's evidence files via the ledger, and both are reproducible
by third parties without any market data (`python3 optimize/verify/run.py`, 79/79 claims). The
software is versioned and archived with DOIs on Zenodo (concept DOI 10.5281/zenodo.21473312, eight
released versions to date), is deployed in production research use at BeInMedia, and operates a
signed, hash-frozen live evaluation protocol whose windows accumulate as new ledger claims —
a public, out-of-sample-by-construction track record that external researchers can audit
continuously. The verification pattern (claims with falsifiers and blind spots, defect-replay
self-tests, evidence-tracking rules) is domain-portable and documented for reuse beyond finance.

# AI usage disclosure

Generative AI was used substantially in this project, under human direction, and the framework's
governance was designed with that in mind. AI coding agents (Anthropic Claude-family models,
operated through the Claude Code environment) wrote large portions of the codebase, documentation,
and analysis pipeline, and assisted in drafting this paper. The human authors set the research
questions, made all core design decisions (the claim schema, engine parity, pre-registration and
verdict rules, the live protocol), reviewed the agents' outputs, and signed every pre-registration
and protocol decision. Independently of that review, correctness is enforced mechanically rather
than assumed: all AI-produced changes pass the same CI gates as any contribution — byte-compilation,
import smoke tests, engine-parity checks, and the full claims-ledger replay — and no result is
publishable except as a ledger claim with its falsifier. The defect-replay self-test described
above guards the verification layer itself.

# Acknowledgements

This software was developed at BeInMedia (Nmo AI) — Kuwait, Dubai, and Doha
(https://www.beinmedia.com/) — which provided the research infrastructure, computing resources,
and data licensing that made the project possible.

# References
