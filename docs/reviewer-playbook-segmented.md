# Reviewer Playbook (Segmented, Strict, Iterative)

Generated: 2026-05-21  
Purpose: Enforce strict review on every generated dashboard output using known-bug regression + deep multi-lens stress testing.

---

## 1) Team Operating Model (Two Stages)

## Stage A — Known Mistakes Pass (Regression Team)

Use `docs/bug-checklist-revision-history.md` before any deep analysis.

1. Execute all known bug checks.
2. Mark each as `PASS/FAIL/N/A`.
3. Any `FAIL` is a blocker until triaged.

## Stage B — Deep Stress Review (Expert Council Team)

Review **every segment** of the generated output from six mandatory lenses, then standard professional QA checks.

---

## 2) Mandatory Segmentation Rule

Split each generated dashboard into atomic segments:

1. Header/KPI frame
2. Metrics panel
3. Trades panel
4. Analysis panel
5. Playbook panel
6. Logs panel
7. Insights panel
8. Chart frame
9. Parameter table
10. Any extra paragraph/block generated dynamically

No segment is skipped. No merged pass across multiple segments.

---

## 3) Six Mandatory Lenses Per Segment

Each segment must be reviewed from all six lenses:

1. **Expert Trader Lens**  
   Signal realism, execution realism, risk asymmetry, strategy plausibility.

2. **Expert Financial Consultant Lens**  
   Metric correctness, accounting consistency, fee/slippage/tax assumptions, reporting clarity.

3. **Technical Expert Lens**  
   Data pipeline integrity, exception handling, deterministic behavior, maintainability.

4. **Logic Expert Lens**  
   Contradictions, stale values, impossible states, rules/outcome consistency.

5. **UX/UI Expert Lens**  
   semantic color use, readability, hierarchy, terminology consistency, cognitive load.

6. **QA/Compliance Lens**  
   reproducibility, traceability, auditability, disclosure quality, policy alignment.

---

## 4) Standard Professional Review Add-ons (Always On)

For each segment, also run:

- Data integrity checks
- Statistical validity checks
- Edge-case and sparse-data behavior checks
- Negative-path/error-path behavior checks
- Regression checks against previous revision outputs
- Documentation parity checks (playbook vs implementation vs output)

---

## 5) Segment Review Template (Use Per Segment)

| Field | Required Content |
|---|---|
| Segment ID | e.g., `SEG-03 Trades Panel` |
| Input Artifact | file + line/range or selector |
| Trader Verdict | Pass/Fail + evidence |
| Financial Verdict | Pass/Fail + evidence |
| Technical Verdict | Pass/Fail + evidence |
| Logic Verdict | Pass/Fail + evidence |
| UX/UI Verdict | Pass/Fail + evidence |
| QA/Compliance Verdict | Pass/Fail + evidence |
| Add-on Checks | Results for standard checks |
| Final Segment Gate | `APPROVE` / `REJECT` |
| New Bugs Found | IDs appended to checklist register |

---

## 6) Strict Pass/Fail Gates

A segment passes only if:

1. All six mandatory lenses pass.
2. No critical/high defects remain unresolved.
3. Output is internally consistent and traceable to source metrics.
4. Segment does not conflict with any known-bug regression item.

If any gate fails => segment rejected => project output rejected for final submission.

---

## 7) Automatic Iteration Update Workflow

After every revision:

1. Run Stage A + Stage B.
2. Add each new defect to `Master Bug Register` in the checklist file.
3. Assign `New ID`, severity, segment, discovery lens, and evidence.
4. Promote repeated or severe defects into the top regression checklist.
5. Keep historical trace (first seen, last seen, fixed in revision X).

This is the mechanism that keeps the playbook and checklist self-evolving with project iterations.

---

## 8) Expert Council Protocol (Bug Discovery + Appending)

Council members: Trader, Financial, Technical, Logic, UX/UI, QA/Compliance.

For each review cycle:

1. Each expert submits lens-specific findings per segment.
2. Council lead de-duplicates findings.
3. Final bug list is severity-ranked.
4. Confirmed bugs are appended to checklist register immediately.
5. Regression checklist is updated before next cycle starts.

---

## 9) Release Decision Policy

Release allowed only when:

- Stage A has zero unresolved critical/high known bugs.
- Stage B segment gates are all `APPROVE`.
- No unresolved contradictions between dashboard output, playbook, and metrics source.

Otherwise: **No final submission**.

---

## 10) Mandatory Deliverable: Fixes Needed Report (Dev Team)

At the end of every revision cycle, produce a **Fixes Needed Report** for development.

Required fields per item:

- ID
- Segment
- Severity
- Problem statement
- Evidence (file/line or metric mismatch)
- Required fix
- Owner (team/function)
- Target revision
- Validation method

This report is not optional and is a release gate artifact.

---

## 11) Knowledge Base Append Rule (Experience Growth)

After the Fixes Needed Report is produced:

1. Append a new entry to the project knowledge base (`docs/bug-checklist-revision-history.md`).
2. Add every newly discovered fix item to the `Master Bug Register`.
3. Mark repeated defects as regression-critical candidates.
4. Keep history of first seen / last seen / fixed revision.

This ensures accumulated review experience is retained and reused automatically.

---

## 12) Minimal Execution Loop (Per Revision)

1. Load latest generated dashboard artifact(s).
2. Segment the output.
3. Run Stage A checklist.
4. Run Stage B six-lens stress test for every segment.
5. Publish Fixes Needed Report for dev team.
6. Append report outcomes to knowledge base.
7. Publish consolidated verdict.
