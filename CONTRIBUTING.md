# Contributing

Contributions are welcome — issues and pull requests both. This project has an unusual operating
contract, so please read two documents before writing code:

1. **[`AGENTS.md`](AGENTS.md)** — the working rules of this repository (branch/PR flow, worktree
   discipline, verification duties). They apply to human and AI contributors alike.
2. **The verification standard:** every published number in this project is a claim in the ledger
   (`subprojects/Parametric-Indicators/optimize/verify/`). If your change alters a published
   number, the corresponding claim and its committed evidence must change in the same PR — CI
   replays the full ledger and will reject silent divergence.

## The short version

- **Open an issue first** describing what you intend to change; work happens on a
  `feat/<issue>-<slug>` branch and lands via PR into `dev` (integration), then `main`.
- **Tests must pass without market data.** The engine suite runs green on a fresh clone
  (`cd subprojects/Parametric-Indicators && pytest`); data-dependent tests skip themselves. Price
  data are never committed — the pipeline runs against a user-supplied feed.
- **CI is the gate:** byte-compile, import smoke, engine-parity (fast vs exact engines must agree
  trade-for-trade), and the claims-ledger replay are required checks on `dev` and `main`.
- **Research contributions** (new studies, strategy families, instruments) additionally follow the
  pre-registration discipline: design filed before results are computed, negatives carry power
  analyses, positives carry dumb controls and noise checks. See `docs/` for filed examples.

## License

By contributing you agree that your contributions are licensed under
[AGPL-3.0-or-later](LICENSE).
