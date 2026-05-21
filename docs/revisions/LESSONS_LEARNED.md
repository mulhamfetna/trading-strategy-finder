# Lessons Learned

## 1. Lock behavior with regression tests before refactoring

- Every bugfix that mattered (RSI filters, dashboard labels, PnL scaling) stayed fixed because tests were added first.
- Rule: no production behavior change without a failing test that reproduces it.

## 2. Keep rendering boundaries explicit

- Separating HTML template from Python logic reduced accidental UI regressions.
- Rule: presentation should live in templates/components, not long inline string builders.

## 3. Preserve market structure in charts

- Candlesticks revealed information that line charts hide.
- Rule: for trading dashboards, default to OHLC-aware visuals when candle-level interpretation matters.

## 4. Organize entrypoints under one predictable location

- Moving scripts to `src/main/` made imports and execution paths easier to maintain.
- Rule: executable entry scripts should stay in one canonical module path.

## 5. Keep output generation deterministic

- Regeneration steps are most useful when output paths and calculations are deterministic.
- Rule: prefer stable seeds/configuration and explicit output directories.

## 6. Isolate implementation using worktrees

- Worktree isolation prevented unrelated workspace drift from affecting phase work.
- Rule: use dedicated worktrees for each phase and keep commits scoped.

## 7. Avoid hidden side effects in optimization tooling

- Source-mutating utilities are risky for long-term maintainability.
- Rule: optimization should emit configs/artifacts, not rewrite source modules by default.
