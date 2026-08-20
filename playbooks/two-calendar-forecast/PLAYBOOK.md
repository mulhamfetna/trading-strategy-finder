# The Two-Calendar Forecast Layer — playbook v1.0.0 (E-D1, deployed-on-branch 2026-08-20)

**What it is**: the calendar-augmented volatility context the live HAR gate is blind to,
composed by ROUTING (never a fitted joint model — E-X2/E-X2v2 proved fitted composition
interferes on NQ): the FU-11-certified model on macro event bars, the E-X1-certified model
on earnings bars, plain HAR-LS elsewhere. INFORMATION ONLY — no trading consumer.

**Modes** (`python3 -m src.deploy.two_calendar_forecast ...`):
- `verify --instrument NQ|ES` — parity vs the committed FU-11/E-X1 evidence (Δ must be 0)
  plus the union count-weighted identity.
- `scramble --instrument NQ` — per-calendar power-scramble falsifiers (must collapse).
- `forecast --instrument NQ --now <date> [--horizon-days 30] [--earnings-dates file.csv]`
  — JSONL of upcoming known events with the night-before predicted power and the routed
  bar-level vol lift (rv points the blind HAR would miss). Macro is fully forward-capable
  (TV calendar); earnings need a user-supplied dates file (EDGAR is historical — declared).

**Certified numbers behind it**: macro event-bar QLIKE 8.11→0.48 (NQ; FU-11, 4/4 lines);
earnings 1.30→0.79 (E-X1, 4/4); both placebo-collapsed; interference of fitted composition
CI-confirmed (E-X2v2) — hence routing. Deployment battery: parity Δ=0.0 both instruments ·
falsifiers collapse · artifact regime-sane (NFP +71.9 rv pts, CPI +69.9, Durables +12.3) ·
golden 6/6 ALL MATCH (no engine path touched). Ledger claim `ED1-TWO-CALENDAR-DEPLOYED`.
