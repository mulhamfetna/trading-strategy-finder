# Fixes Needed Report for Development Team

Generated: 2026-05-21  
Source: latest deep dashboard/system re-review

---

## Priority Fixes

| ID | Severity | Segment | Problem | Required Fix | Validation Method |
|---|---|---|---|---|---|
| FIX-2026-05-21-01 | High | Metrics panel | Gross metric naming is ambiguous and can be interpreted incorrectly by reviewers/traders | Rename metrics for semantic clarity (`gross_wins`, `gross_losses`, `net_profit_after_fees` as applicable) and align UI labels with formulas | Reconcile displayed values against trade-level aggregates and formula definitions |
| FIX-2026-05-21-02 | High | Playbook / Header | Strategy labeled as "scalping" while measured holding times are multi-day | Either update strategy label to match behavior or enforce time-based exit constraints to fit scalping definition | Recompute holding-time distribution and confirm consistency with declared strategy type |
| FIX-2026-05-21-03 | High | Technical pipeline | Silent exception swallowing in critical filtering path hides defects (`except: pass`) | Replace silent catch with explicit error handling/logging and deterministic fallback policy | Negative-path tests prove errors are surfaced and traceable |
| FIX-2026-05-21-04 | Medium | QA / Research validation | Robustness evidence is incomplete for final submission confidence | Add walk-forward/out-of-sample validation, benchmark comparison, and sensitivity analysis to release evidence pack | Revision report includes reproducible robustness section with pass/fail criteria |

---

## Ownership Suggestion

- Quant/Strategy Engineering: FIX-01, FIX-02  
- Core Engineering: FIX-03  
- QA + Quant Research: FIX-04

---

## Release Gate Policy

Final submission remains conditional until all **High** severity items above are closed and validated.

