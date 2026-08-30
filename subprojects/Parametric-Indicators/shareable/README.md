---
name: shareable-bundles
description: Hand-off bundles — SNAPSHOTS of the engine at the moment each study closed. Not the live code.
type: archive
---

# `shareable/` — snapshots, not the live engine

Every directory here is a self-contained bundle handed to someone outside the repo (a backtester with its
champions, a playbook, a study record). Each carries **its own copy** of `engine.py` / `strategy.py` /
`payload.py` frozen at the date of the bundle, so it keeps reproducing the numbers it shipped with even after
the live engine moves on. That is deliberate — and it means:

- **The live files are the ones at `subprojects/Parametric-Indicators/{engine.py,strategy.py,optimize/…}`.**
  A bundle's copy will drift from them and is not meant to be kept in sync.
- Bundles are excluded from the engine's test collection (`pytest.ini` / `conftest.py`) and from the claims
  ledger; their evidence is the study's committed data, not these copies.
- Roughly a third of the tracked Python in the repo is these copies plus `server-audit/` (positioning audit
  2026-08-29 §3.3). When in doubt, read the live path, not the bundle.

Bundles: `orb_study_bundle` (WS-ORB #183), `winning_strategy_backtester`, `wsh6cold_4h_backtester`,
`playbooks_backtester`, `lean_3indicator_backtester`, `two_layer_causal_backtester`, `mtf_layer_fusion_backtester`,
`l2_optimizer`, `server_agent_kit`, plus the zips beside them.
