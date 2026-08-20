# XNI Phase 3 — the Full Record (earnings × news × indicators)

**Opened 2026-08-20 (tracking #172; brainstorm + X-ledger `XNI-BRAINSTORM.md`; claims
`claims_xni.py`).**

## X-0 · The opening state

Three eras hand this phase: two certified size forecasts (macro ρ≈0.5 deployed; earnings
ρ≈0.46), the released two-calendar blindness schedule (E-D1, v5.5.0), the state-blind law
at full strength (X-R1: stances = telemetry only), and the born constraint — collisions are
rare, census before outcomes, mechanically gated.

## X-1 · The collision census + compound-power measurement: CLOSED-INDEPENDENT ✅ (2026-08-20)

**The census (the gate cleared — no underpowered closure was needed):** of ~560 macro
events ≥2016, **63/64** (NQ/ES) had a top-12 earnings print in the prior 18 hours (T1) and
**118** had one within ±24h (T2); 190 earnings events sit within 24h of a macro release.
Collisions are not rare after all at the top-12 scale — the born constraint was satisfied
by measurement, not assumption.

**The outcomes (NQ primary; matched same-series controls; within-series shuffles):**

| type | n | NQ Δlog(jump) | CI90 | shuffle p95 | verdict |
|---|---|---|---|---|---|
| T1 earnings-night→macro-morning | 63 | +0.1723 | [−0.0631, +0.3985] | +0.2630 | **CLOSED-INDEPENDENT** |
| T2 same-24h | 118 | +0.0494 | [−0.1443, +0.2409] | +0.2049 | **CLOSED-INDEPENDENT** |

**Recorded, NOT promoted**: ES's T1 clears every registered line alone — **+0.3580, CI
[+0.1225, +0.5845], above its shuffle p95 (+0.2543)** — but the registered primary is NQ
and no pooled rule existed; none was invented post hoc (ledger V2 verifies the
non-promotion). It stands as a single-witness, fresh-registration-eligible hypothesis
("T1 super-additivity, ES-led") on future data.

**The consequence — the phase's first law**: the two calendars resolve INDEPENDENTLY at
the measurable level. Compound power therefore composes ADDITIVELY from the two certified
forecasts — X-3's collision flag needs no interaction statistics, and FU-15's parked gate
input gains nothing beyond the two forecasts it already has. Ledger:
`X1-CALENDARS-INDEPENDENT`, **60/60 both machines**.

## X-3 · The compound-power artifact: SHIPPED-ON-BRANCH ✅ (2026-08-20)

**A composition, not a study (law #1: the calendars resolve independently ⇒ ADDITIVE
composition, no interaction statistics). The E-D1 artifact now carries, per event: the
`collision` flag (T1/T2, X-1's frozen windows) and `compound_lift_rv_pts` (own lift + the
max counterpart lift within ±24h).**

Three lines, all green: **P** — verify Δ0.0e+00 both instruments AFTER the change ·
**C** — census consistency: the 2025 artifact's T1 rate 22.6% vs X-1's own machinery on
the same window 22.4% (ratio 1.009, inside the registered ±10%) · **A/V3** — every one of
the 44 compound rows re-derives additively from a ±24h counterpart, checked ROW BY ROW in
the ledger claim itself (e.g. FOMC 2025-01-29: own 58.0 + earnings 15.5 = 73.5 rv pts).

**The incident worth the record**: the claim's own V3 caught a real composition bug on the
first pass — a `max(best or 0.0, …)` seed silently FLOORED negative counterpart lifts to
zero. The earnings model's dummy beta is negative, so a tiny-power print carries a negative
lift — the certified model's honest statement, which the composition must respect. Fixed,
re-run, all green. A machine check catching its own author within the hour is the protocol
working exactly as designed.

Bundle re-zips at the next release (noted). Ledger: `X3-COMPOUND-ARTIFACT-SHIPPED`,
**61/61 both machines**.

## X-5 · Monitor × compound power: INFORMATIVE — regime-dominant, honestly decomposed ✅ (2026-08-20)

**The protective analysis (order rationale recorded: before X-4, on committed data only; no
trigger changes regardless of verdict — the D2 monitor is a deployed protection layer).**

**Result**: the monitor's rolling-24 CPI health co-moves with the compound-power series at
Spearman **+0.9057** (CI [0.8625, 0.9317], n=93; era halves +0.54/+0.73) — INFORMATIVE by
the registered rule. **The decomposition stated first**: the within-year shuffle bar itself
reaches **0.879** — the ANNUAL REGIME carries the bulk of the correlation. This is the
CPI-power-era law (the ride pays when CPI power is high — era 2's discovery) re-measured at
the monitor level; the genuinely event-level increment is the **0.027 margin** above the
shuffle bar. The claim's V3 verifies this decomposition is stated, permanently.

**Consequence (as registered, no more)**: a compound-power CONTEXT FIELD may be added to
the monitor's REPORT output — information only, its own small parity gate, the trigger
never changes. **Armed as X-5b; not built until called.** Incident kept: a claims-path
typo (xni/data parents depth), caught by the ledger's first run.

Ledger: `X5-MONITOR-POWER-INFORMATIVE`, **62/62 both machines**.

## X-5b · The monitor's context field: SHIPPED-ON-BRANCH ✅ (2026-08-20)

**X-5's registered consequence, delivered exactly and no more: an OPTIONAL `--context`
flag on the regime monitor's report — `compound_power_pct` (X-5's definition, X-3's
additive law) + a median-label regime note carrying the authority string "information only
— never gates".**

**The trigger is untouched, proven three ways**: (1) the old and new `rolling_state` are
BYTE-EQUAL on the committed replay evidence (the parity log); (2) the trigger function's
source contains no context reference (static proof, ledger-checked); (3) the flag and
parameter default OFF — without them the module IS the old module. Definition parity:
29/29 CPI events match the frozen-file recomputation to 1e-9.

Runbook note (not code): the LIVE monitor's context source is the nightly two-calendar
artifact; the frozen research files serve the historical mode. Ledger:
`X5B-MONITOR-CONTEXT-SHIPPED`, **63/63 both machines**.

## X-4 · Blindness-hours observability: SHIPPED-ON-BRANCH ✅ (2026-08-20)

**The dashboard's `/api/backtest` trades now carry `event_window` (macro = FU-1's frozen
[rel−5,+15] Tier-1 window · earnings = ±15m of a committed acceptance stamp) with meta
counts and the authority string "observability only — never gates".**

- **P — books untouched, proven**: the post-change response is JSON-EQUAL to a reference
  captured BEFORE the code moved (the 65-trade WS-G champion run), stripping only the new
  fields. Since the reference ran the production code, the branch's numbers equal
  production's transitively.
- **C — tag correctness**: positive controls fire on real event minutes ('macro' at rel and
  rel+10m; 'earnings' at a stamp), the clean minute stays clean, and all 65 reference
  trades re-derive with 0 mismatches. The 4h book's all-blank tags are CORRECT — 4h entry
  stamps never fall inside 20-minute windows; finer TFs are where the field lights up.
- **V — the visual gate, THE HOUSE WAY (owner-corrected mid-study)**: SSH tunnel +
  Playwright — both dashboards clicked Run; the branch's visible dollar figures EQUAL
  production's ($166,554 P/L · $13,963 DD · …); the branch screenshot is committed
  evidence (`x4_dashboard_8250.png`).

**Incidents kept (all recovered, all now in memory)**: the restart used the wrong
interpreter (no-numpy system python) then missed the data-root env — the stale-server and
sync-roots traps, live; and the visual gate was first attempted with Claude-in-Chrome —
**owner correction of record: NEVER — the standard is ssh-tunnel + Playwright** (saved to
the feedback memory). Ledger: `X4-BLINDNESS-OBSERVABILITY-SHIPPED`, **64/64 both machines**.

## The closure (2026-08-20)

The phase's own test, satisfied: X-1 law #1 · X-3/X-4/X-5b shipped with parity proofs ·
X-5 informative-decomposed · X-R1 standing · X-2/X-6 parked-with-cause. Ledger **64/64
both machines**; closing bilingual report `XNI-CLOSING-REPORT-BILINGUAL.html`. **The
owner's three-step roadmap is COMPLETE** — the coherent total finding: scheduled violence
is rankable from its own history (twice productionized); nothing else predicts it
(direction ×3, state on every axis, cross-calendar interaction); the edge stays where it
was earned, and every new layer is information under authority strings. This record is
COMPLETE.
