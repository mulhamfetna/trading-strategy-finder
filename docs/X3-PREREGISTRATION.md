# X-3 (#172 ledger) — the compound-power artifact: pre-registration

**Filed 2026-08-20 BEFORE any change. X-3 is a COMPOSITION, not a study: X-1's phase law
(the calendars resolve independently ⇒ compound power composes ADDITIVELY) means the
collision flag and compound lift are pure functions of two already-certified layers — no
new statistics exist to test, and none are invented. The FU-14-pattern lines below are
therefore parity and consistency lines, not hypothesis lines.**

## The change (frozen)

`src/deploy/two_calendar_forecast.py` `forecast` mode gains, per emitted event row:
- `collision`: "T1" if the OTHER calendar has a known event in the 18h before this one
  (X-1's frozen window), "T2" if within ±24h, else null — computed against the same event
  sources the mode already uses (TV calendar for macro; the committed table or the
  owner-supplied dates file for earnings — the E-D1 declaration inherits).
- `compound_lift_rv_pts`: this event's lift + the MAX counterpart lift inside the ±24h
  window (the additive law; max per counterpart calendar avoids double-counting clustered
  prints).
`verify` and `scramble` modes are UNTOUCHED.

## PASS lines (fixed now)

1. **P — parity preserved**: `verify` re-run on the server after the change must still be
   Δ0.0e+00 on both instruments (the certification paths untouched).
2. **C — census consistency**: a historical `forecast --now 2025-01-01 --horizon-days 365`
   run's T1 collision count for macro events must be within ±10% of X-1's census rate for
   the same window (the flag implements the same frozen definition).
3. **A — artifact well-formed**: collision and compound fields finite where present; rows
   without a counterpart carry null collision and no compound field.

**ALL green ⇒ the artifact ships on-branch (module + playbook text updated; the released
bundle re-zips at the NEXT release — noted, not re-shipped now). Any failure ⇒ the change
reverts.**

## Blind spots (declared)

1. Forward earnings dates still require the owner-supplied calendar (inherited verbatim).
2. The compound lift is additive BY LAW #1 (measured independence) — if a future fresh
   registration ever confirms the ES-led T1 texture, the composition would be revisited
   under its own pre-registration.
3. "Counterpart known events" means events the mode can see at emit time — historical runs
   see the committed table; live runs see what the owner supplies.
