# #198 — vol-gate recalibration cadence: pre-registration

**Filed 2026-08-30 BEFORE any run.** Part of #194 phase 2 (the cheap arm of #186, promoted to run first).
Cost estimate posted on the issue (~20–40 min server replay compute + one default-off engine hook).

## 0. Question
The deployed champions' volatility gates are **frozen 2025 quantiles**: the threshold is
`percentile(gate_pct)` of `vf[:n2025]` (`volatility.gate_threshold`, seeded once, never updated). In the
2026 regime several slots went structurally dark (NQ 5m: 640/641 signals killed, 1 entry/60d; NQ 2m/1h,
RTY 15m, ES 2m at 0.5–2% entry rates — #176/#179). **Does re-estimating ONLY the gate threshold on a
trailing window, at a fixed cadence, recover part of the fleet's forward decay — without touching any other
champion parameter?**

## 1. The hook (engine change, default-off, golden-locked)
`optimize/l2/l1_runner.run_l1` gains two OPTIONAL params (absent ⇒ exact current behaviour, proven
byte-identical by test and by the golden gate):
- `gate_recal_months: int` — every M calendar months (segment boundaries = month starts), the threshold is
  re-estimated **causally** at the boundary bar;
- the trailing seed at each boundary = the **last `len(vf_seed)` decision bars strictly before the
  boundary** (same window LENGTH as the frozen seed, so the only thing that changes is *when*, never
  *how much* data). Bars before the first boundary use the original frozen threshold.
No other parameter, path, or engine is modified. `gate_pct` itself (the percentile) is never re-fit.

## 2. Arms (frozen)
On the extended root, all 54 `best` slots, full replay 2025-01 → 2026-08-07, 1 contract:
- **A0 frozen** — the control: today's behaviour (must equal the round-2 books byte-for-byte; this is also
  the hook's off-state proof).
- **A1 quarterly** — `gate_recal_months = 3`.
- **A2 monthly** — `gate_recal_months = 1`.
- **C random-percentile control** — monthly cadence, but at each boundary the threshold is drawn at a
  RANDOM percentile (seeded rng(198), uniform 5–95) of the same trailing window, per slot. If "any refresh
  helps as much as the real refresh", the benefit is churn, not calibration.

## 3. Judgement (frozen)
- Primary read: the **fresh window** (entries after each instrument's pre-extension engine end, as in
  #179) at **$25/rt**; secondary: $10/rt and raw; fleet-level first, per-slot with power labels
  (POSITIVE-change / NEGATIVE-change / UNDERPOWERED, MDE at 80%/5% two-sided).
- The recalibration VERDICT is positive iff fleet fresh net@$25 of an arm exceeds A0's by more than the
  same arm-vs-A0 difference of control C (the churn floor), with a session-block bootstrap CI (1,000
  resamples) excluding zero on the A-vs-A0 difference.
- Dark-slot secondary metric (reported, not the verdict): entry-rate recovery on the five known dark slots
  (NQ 5m/2m/1h, RTY 15m, ES 2m).
- If the verdict is positive, the winning cadence enters the LIVE-PROTOCOL (#199) exactly as tested; if
  null/negative, the protocol ships with frozen gates and #186 (full re-fit study) decides whether to run.

## 4. Outputs
`optimize/gatecal/` (runner + summary), evidence `optimize/gatecal/data/` (summaries + fleet tables;
books on the server), claim `claims_gatecal.py` (V1 off-state byte parity + golden; V2 the arms' numbers
re-derive; V3 falsifier: the random-percentile control does NOT reproduce the real arm's effect, and the
off-state equals the round-2 books), report `docs/WS-GATECAL-REPORT.md`.

## 5. Blind spots (declared)
1. The fresh window is 1–2.5 months per instrument — fleet-level power only; per-slot claims will mostly be
   UNDERPOWERED and are labelled, not hidden.
2. Recalibrating the *threshold* at a frozen percentile cannot fix a slot whose PERCENTILE choice itself is
   stale — that is #186's territory (re-fitting `gate_pct` is optimization, not recalibration).
3. The 2025 part of the replay overlaps the champions' training data; only the fresh cut is OOS.
4. Monthly boundaries are calendar conventions; no boundary tuning is permitted (M ∈ {1,3} only, fixed here).
