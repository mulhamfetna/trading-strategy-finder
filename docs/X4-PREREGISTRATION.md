# X-4 (#172 ledger) — blindness-hours observability on the dashboard: pre-registration

**Filed 2026-08-20 BEFORE any change. X-4 is OBSERVABILITY, not gating (FU-2 proved vetoes
don't pay): the operator sees which trades happened inside known event windows. Books,
numbers and every existing field stay byte-identical; the annotation is additive and
gracefully absent if the calendars cannot load.**

## The change (frozen)

`server.py` (the dashboard backend): each trade in the `/api/backtest` payload gains
`event_window` ∈ {"macro", "earnings", "both", ""} — macro = the entry time inside a
Tier-1 window [rel−5m, rel+15m] (FU-1's frozen definition, TV calendar ≥2016); earnings =
within ±15m of a committed top-12 acceptance stamp. `meta` gains `event_window_counts` +
the authority note ("observability only — never gates"). Calendar load is lazy and
fault-tolerant: on any failure the tags are "" and meta records `context_unavailable`
(the dashboard never breaks on the annotation's account). The causal-log CSV column is a
declared v2, not smuggled in.

## PASS lines (fixed now)

1. **P — response parity**: the pre-change reference response (captured BEFORE the code
   moved: the WS-G winner preset, full window, 65 trades) must equal the post-change
   response after stripping ONLY the new fields — JSON-equal, every number untouched.
2. **C — tag correctness**: the 65 reference trades' tags re-derived independently from
   the committed calendars (in the ledger claim) must match the served tags.
3. **V — the browser gate (the UI-verification rule)**: the branch dashboard :8250 loads
   and runs the preset in a real browser; the headline numbers match production :8200 for
   the identical request; screenshot kept. If the browser bridge is unavailable, the
   numeric parity stands and the visual step is recorded OPEN — never silently skipped.
4. Restart-rule compliance: the branch server restarted after the pull (the stale-server
   trap), production :8200 untouched.

## Blind spots (declared)

1. Production :8200 stays on the released code until the next release ships this — the
   annotation lives on :8250/branch (declared; the owner's pipeline ships it).
2. Earnings window ±15m around the ACCEPTANCE stamp inherits the acceptance-lag smear.
3. The frontend renders what it knows; the new field appears in the payload/CSV consumers
   first — a visible UI column is part of v2 if the owner wants it on-screen.
