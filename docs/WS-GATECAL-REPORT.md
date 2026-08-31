# #198 — vol-gate recalibration cadence: the report

**Date:** 2026-08-30 · **Pre-registration:** `docs/WS-GATECAL-PREREGISTRATION.md` (filed before any run) ·
**Claim:** `GATECAL-CADENCE-NULL` (ledger 77/77) · **Evidence:** `optimize/gatecal/data/` (verdict JSON,
A0-parity proof, arm summaries; 216 per-trade books on the server `wsg-i/gatecal/`).

## 0. One paragraph

The deployed champions' volatility gates are frozen 2025 quantiles, and several slots went dark when the
2026 regime arrived — the natural fix is to re-estimate the threshold on a trailing window at a fixed
cadence. We built that as a default-off engine hook (off-state proven **identical on all 54 real books**),
replayed the whole fleet under quarterly and monthly cadences plus a random-percentile churn control, and
judged it by the frozen rule. **Verdict: NULL for both cadences.** Recalibration does what it promises
mechanically — the dark slots reopen (NQ 2m fresh entries 20 → 46/86, NQ 1h 10 → 16) and the fleet takes
~1,300 more fresh trades — but at $25/round-trip the fleet ends **no better than frozen** (quarterly
−$4,070, monthly −$710; CI95s straddle zero), and the churn control embarrassed both by **trading less**
(+$36,792 vs frozen, itself not significant). On a friction-negative window, admitting more trades is not a
cure; the toll is. **The LIVE-PROTOCOL (#199) ships with frozen gates.**

## 1. The numbers (fresh window, per arm)

| arm | fresh trades | raw | net @$10 | net @$25 | vs A0 @$25 (CI95) | dark-slot entries (NQ 5m/2m/1h · RTY 15m · ES 2m) |
|---|---|---|---|---|---|---|
| A0 frozen | 3,733 | +$29,807 | −$7,523 | **−$63,518** | — | 4 / 20 / 10 · 1 · 19 |
| A1 quarterly | 5,074 | +$59,262 | — | −$67,588 | −$4,070 [−36.8k, +32.0k] | 5 / 86 / 16 · 2 · 19 |
| A2 monthly | 5,023 | +$61,347 | — | −$64,228 | −$710 [−32.4k, +32.6k] | 5 / 46 / 16 · 2 · 18 |
| C random-pct (churn control) | 1,356 | +$7,174 | — | −$26,726 | +$36,792 [−15.1k, +85.8k] | 1 / 50 / 0 · 1 · 5 |

The verdict rule (§3 of the prereg): an arm is POSITIVE only if it beats the churn floor AND its bootstrap
CI95 excludes zero. A1/A2 do neither. C's large point difference comes from *tighter* random gates cutting
trade count — the same "fewer trades, less toll" arithmetic as the fleet's whole friction story — and its
CI includes zero too.

## 2. What went well / wrong

**Well:** the hook's off-state (A0) reproduced the round-2 books **54/54 to half a cent** — the study's
control doubles as the merge-safety proof; the judgement refused the biggest point estimate on the table
(C) because its CI includes zero — the rule can say no; the whole study (hook + tests + 4 × 54 replays +
verdict) ran in under a day, ~25 minutes of server compute.

**Wrong / limits:** one fresh window (1–2.5 months per instrument), fleet-level power only; the percentile
itself was never re-fit (that is optimization — #186's question, deliberately excluded); recalibration was
all-slots-or-nothing by design.

## 3. The exploratory observation (logged, NOT a verdict)

On the **9 allowlist slots** (#195) only — computed after the fleet verdict, therefore post-hoc and
selection-on-selection — recalibration *helped*: fresh net@$25 frozen +$37,315 → quarterly **+$54,434** /
monthly **+$52,341**, while the churn control managed only +$16,676. Reading: the fleet NULL is the sum of
"good slots get better" and "reopened bad slots pay the toll". **Hypothesis for a future pre-registration
(fold into #186 or a #199 amendment): recalibrate the gate only within the allowlist.** It enters no
protocol until it survives its own pre-registered test on data that did not produce it.

## 4. Consequences
- #199 LIVE-PROTOCOL: gates FROZEN, stated with this claim as the cause.
- #186 walk-forward study: still open; its prior is lowered at fleet level and sharpened toward the
  allowlist-conditional question above.
- The hook stays in the engine (default-off, byte-proven) — the follow-up study needs no new machinery.

## 5. Reproduce
```
python3 -m pytest optimize/test_gate_recal.py                     # the hook's 5 unit tests
# server, extended root:
python3 optimize/gatecal/gatecal_run.py --out <dir> --arm A0 --jobs 8   # then A1, A2, C
python3 optimize/gatecal/gatecal_verdict.py --books <dir> --out <dir>/gatecal_verdict.json
python3 optimize/verify/run.py                                    # GATECAL-CADENCE-NULL, 77/77
```
