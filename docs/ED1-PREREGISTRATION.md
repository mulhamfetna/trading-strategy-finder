# E-D1 — the two-calendar forecast layer (routing pattern): pre-registration

**Filed 2026-08-20 BEFORE any build, by owner order ("proceed to ed1"). The FU-14
deployment pattern applied to the E-X2v2 engineering insight: composition by ROUTING —
each certified single-calendar model applied to its own calendar's bars — is
interference-free by construction and inherits each model's certification. E-D1 ships an
INFORMATION layer only: parity + falsifiers + a nightly artifact; ZERO trading consumers;
no engine file is touched; golden stays byte-identical by construction.**

## What the layer is

`src/deploy/two_calendar_forecast.py` — the calendar-augmented volatility context the live
HAR gate is blind to, routed: on MACRO event bars the FU-11-certified model (HAR-LS + macro
dummy/power), on EARNINGS bars the E-X1-certified model (HAR-LS + earnings dummy/power),
plain HAR-LS elsewhere. Coefficients are re-fit deterministically from the same frozen
inputs (train < 2024) — the parity stage pins them to the committed evidence.

## Stages and PASS lines (fixed now — the FU-14 battery)

| stage | what runs | PASS line |
|---|---|---|
| B (build) | the module; modes `verify` / `scramble` / `forecast`; imports the committed machinery (fu11_stage1, ex2 term builders) — nothing re-implemented | module exists; no engine imports touched |
| P (parity) | routed event-bar QLIKE recomputed per instrument | macro bars ≡ the committed `fu11_stage1_{inst}_60m.json` fused event QLIKE and earnings bars ≡ the committed `ex1_result_{inst}.json` fused event QLIKE, both ≤1e-9, NQ AND ES; the union number must equal the count-weighted identity of the two |
| F (falsifier) | 20 power-scrambles per calendar (NQ) through the module | each calendar's scrambled event-bar QLIKE loses ≥ half of the certified gain over dummy-only (the FU-11/E-X1 convention) |
| A (artifact) | `forecast --now <historical date>`: JSONL of upcoming known events with the routed bar-level vol lift (expected rv addition vs the blind HAR) — macro from the TV calendar; earnings ONLY from a user-supplied dates file (forward earnings dates are not in our data — DECLARED, not hidden) | artifact well-formed; per-event lifts finite; macro events present for a known historical window |
| D (system) | full claims ledger both machines + the golden gate (`perf/check_golden.py`) on the server | ledger green; golden ALL MATCH (the module touches no engine path — this proves it) |
| **DEPLOY rule** | | ALL stages green ⇒ **DEPLOYED-ON-BRANCH** as an information layer (module + claim + playbook doc); the release/merge ship remains the owner's standing pipeline and is NOT executed by this study. Any failure ⇒ NOT-DEPLOYED, verdict recorded. |

## Blind spots (declared)

1. Forward earnings dates require an owner-supplied calendar (EDGAR is historical);
   the macro side is fully forward-capable today (TV calendar).
2. Research 1h frames (the certified models' own grade); the layer describes the RESEARCH
   forecast's repair — the live champions' gate frames are engine-loader session frames
   (the FU-11 §consumer-① declaration stands).
3. Information-only: the achievement record must not describe this as income (the FU-14
   rule verbatim).
