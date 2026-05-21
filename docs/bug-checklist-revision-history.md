# Bug Checklist (All Previous Revisions)

Generated: 2026-05-21  
Scope: Consolidated known bugs and quality risks extracted from prior exported reviews and bug reports.

---

## How To Use

1. Run this checklist at the start of every revision/QA cycle (**Stage A: Known Bugs Pass**).
2. Mark each item as: `PASS`, `FAIL`, or `N/A`.
3. If a failed item is new or regressed, append it to the **Master Bug Register** section.

---

## A) Master Regression Checklist

| ID | Bug Pattern | Category | Severity | First Seen | Last Seen | Current Expectation |
|---|---|---|---|---|---|---|
| BUG-001 | NQ contract multiplier missing (`$2/point`) causing under-sized P/L | Financial logic | Critical | report-revision4 | report-revision4 | Must remain fixed in all future outputs |
| BUG-002 | Exit timestamp before entry timestamp | Data integrity | Critical | CRITICAL_TIMESTAMP_BUG | CRITICAL_TIMESTAMP_BUG | Must never occur |
| BUG-003 | Corrupted timestamp format (`YYYY-MM-DD 00:00:00 HH:MM:SS`) | Formatting/data | High | re_review/v3 | fixed in final review | Must remain clean |
| BUG-004 | Return string format `+-X%` | UI logic | High | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Must show valid signed format only |
| BUG-005 | Negative return shown in green | UX/UI | Medium | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Negative must be red |
| BUG-006 | Net/gross metric labeling mismatch | Financial semantics | High | re_review/v3 | revision5 (semantic concern) | Labels must be unambiguous (`gross_wins`, `net_profit`, etc.) |
| BUG-007 | Stale insights text from old dataset | Data freshness | Critical | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Insights must match current run only |
| BUG-008 | Contradictory insights (e.g., "all winning trades" with zero winners) | Logic/content | High | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Narratives must reflect actual counts |
| BUG-009 | EV/Trade inconsistency with fee handling | Financial logic | Medium | COMPREHENSIVE_BUG_REPORT | re_review | EV formula and display must match |
| BUG-010 | Running capital mismatch in metrics logs | Financial/data | High | re_review | re_review | Capital path must reconcile per trade |
| BUG-011 | Profit factor / Sharpe displayed as raw zero when undefined | Statistical clarity | Medium | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Show `N/A` with reason when insufficient data |
| BUG-012 | R/R displayed while no valid winners or inconsistent with data | Financial logic | High | COMPREHENSIVE_BUG_REPORT | re_review | R/R must be data-driven and conditionally shown |
| BUG-013 | SL/TP stated vs realized exits inconsistent without explanation | Risk model | High | re_review | revision5 (still relevant) | Show slippage/gap note and realized stats |
| BUG-014 | Strategy labeling mismatch ("scalping" with multi-day holding times) | Strategy framing | Medium | revision5 | revision5 | Label and holding profile must be consistent |
| BUG-015 | Silent exception swallowing (`except: pass`) in signal filtering path | Technical reliability | High | revision5 | revision5 | No silent failures in critical path |

---

## B) Panel/Section Quick Checks

### Header / KPI
- [ ] Return sign and color are correct for gain/loss.
- [ ] Final capital, return %, and net P/L reconcile to initial capital.
- [ ] No stale period labels or static values after data refresh.

### Metrics Panel
- [ ] `net_profit`, `gross_*`, `fees`, and `final_capital` naming is unambiguous.
- [ ] EV/Trade formula includes fee treatment consistently.
- [ ] Undefined metrics (Sharpe/PF) are shown as `N/A` when sample is insufficient.

### Trades Panel
- [ ] Every entry meets documented rules at entry timestamp.
- [ ] Every exit reason matches actual trigger path.
- [ ] Direction badge, P/L sign, and class coloring are consistent.

### Analysis Panel
- [ ] Winner/loser narratives match counts and actual outcomes.
- [ ] Terminology is consistent with other tabs.

### Playbook Panel
- [ ] Rules reflect actual engine behavior (including slippage/gap behavior).
- [ ] Strategy label matches holding-time reality.
- [ ] R/R statement matches realized data context.

### Logs Panel
- [ ] For every trade: `ENTRY -> EXIT -> METRICS`.
- [ ] Exit timestamp is always later than entry timestamp.
- [ ] Running capital sequence reconciles exactly.

### Insights Panel
- [ ] No stale text from previous run.
- [ ] Findings/recommendations match current metrics and counts.
- [ ] Narrative claims are statistically valid for sample size.

### Chart Panel
- [ ] Time axis formatting is clean and monotonic.
- [ ] Marker indices map to valid trade rows.
- [ ] Indicator lengths align with candle arrays.

---

## C) Master Bug Register (Append Each Iteration)

Add newly discovered bugs here with unique IDs.

| New ID | Revision | Segment | Lens That Found It | Severity | Evidence | Added By |
|---|---|---|---|---|---|---|
| (append) |  |  |  |  |  |  |

---

## Source Reports Consolidated

- `docs/legacy/COMPREHENSIVE_BUG_REPORT.md`
- `docs/legacy/CRITICAL_TIMESTAMP_BUG.md`
- `docs/legacy/report-revision4.md`
- `docs/legacy/report-revision5.md`
- `docs/ultimate_trading_dashboard_review_v3.md`
- `docs/legacy/ultimate_trading_dashboard_re_review.md`
- `docs/legacy/ultimate_trading_dashboard_final_review.md`

