## What & why
Closes #

## Verification (tick what applies — do not merge to `main` with unchecked required items)
- [ ] CI green (byte-compile + data-free tests)
- [ ] **Golden gate green on the server** (`perf/check_golden.py`) — required for `dev -> main`
- [ ] Params actually used are PRINTED in the run (no silent defaults)
- [ ] Power analysis (negative result) / dumb-control + noise check (positive result), if applicable
- [ ] Report added/updated in `docs/superpowers/` and the daily standup
- [ ] No secrets, data files, venvs, or dashboard outputs committed

## Golden hash impact
- [ ] Golden unchanged (byte-identical), OR
- [ ] Golden intentionally moved — reason + new baseline captured:
