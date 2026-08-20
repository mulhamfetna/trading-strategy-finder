# X-5b (#172 ledger) — the monitor's compound-power context field: pre-registration

**Filed 2026-08-20 BEFORE any change. X-5b is the exact registered consequence of X-5's
INFORMATIVE verdict and nothing more: a CONTEXT FIELD in the monitor's REPORT output.
The trigger — the rolling-24 rule, its stickiness, its clearing procedure — is NOT
touched; the parity line proves it byte-for-byte.**

## The change (frozen)

`src/deploy/regime_monitor.py` gains an OPTIONAL `--context` flag: when supplied with the
two frozen evidence files (FU-9 NQ + E-P1 NQ), the report output (history mode and current
mode) carries per CPI event / per current state:
- `compound_power_pct`: the event's `pred_exp` + the MAX top-12 earnings `pred` within
  ±24h (X-5's exact definition, itself X-3's law-#1 composition);
- `power_regime_note`: "high"/"low" vs the causal median of prior compound values
  (labeling only).
Without `--context`, the module's behavior and output are BYTE-IDENTICAL to today.

## PASS lines (fixed now)

1. **P — trigger parity**: the full `--history` state walk over the committed replay
   evidence, run WITHOUT `--context`, must be byte-identical before vs after the change;
   and WITH `--context`, the `state` column must be identical too (the field is additive).
2. **C — definition parity**: the emitted `compound_power_pct` values must equal X-5's
   committed series on overlapping events (re-derived in the claim from the frozen files).
3. **D — ledger green both machines** (the golden gate is untouched by construction — no
   engine path; the ED1 static-proof pattern applies).

ALL green ⇒ shipped-on-branch (module + this doc); any failure ⇒ revert.

## Blind spots (declared)

1. Context uses the frozen research evidence files — the LIVE monitor's context would
   need the nightly artifact as its source (a wiring note for the ops runbook, not code).
2. The regime label's causal median is labeling convenience, not a threshold with any
   authority (declared to prevent future drift toward a second trigger).
3. NQ-only context (the monitored instrument's own series).
