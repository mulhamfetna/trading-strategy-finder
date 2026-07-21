---
name: Workstream / research question
about: A new research question, feature, or plan (one workstream = one branch = one worktree)
labels: ["status:in-progress"]
---

## The question / goal
<what we are trying to answer or build, in one paragraph>

## Pre-registered criterion (research only)
<the decision rule, written BEFORE the run — e.g. "REAL iff cross-instrument replication holds">

## Plan
- [ ] Deep-research / prior-art pass
- [ ] Implement on the feature branch
- [ ] Power analysis (if a negative result is possible) / dumb-control + noise (if positive)
- [ ] Golden gate green on server; CI green
- [ ] Report in `docs/superpowers/`

## Coordination
- Branch: `feat/<this-issue>-<slug>`  ·  Worktree: `.worktrees/<slug>`  ·  Server: `~/Mulham/<slug>`
- Labels: add one `workstream:*` and one `type:*`
