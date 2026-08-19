# FU-11 — The Fused Size Engine: the SAVED design draft (owner: "save your suggestions, I will need them in a minute")

**Status: SAVED-PENDING (2026-08-19). Not pre-registered, not run. Queued behind the
owner-ordered FU-13/FU-14 verification arc. This file is the suggestion of record so it can
never be dropped; the pre-registration will be derived from it when the owner calls it.**

## The corrected study (from FU-12's system analysis)

Upgrade the system's ONE deployed volatility engine — `volatility.py`'s HAR-RV `vol_forecast`,
the live entry gate of every champion — with the calendar information it is blind to.

- **Inputs**: HAR-RV terms (tape memory) × M2 event-power terms (calendar, night-before,
  ρ≈0.5; t24 variant) · optional audition: the TimesFM/Chronos-2 forecast bands as INPUTS
  (their NO-GOs were about the veto use-case, not band accuracy; corr(TimesFM, Chronos)=0.71 —
  they carry one signal between them).
- **Stage 1 — forecast quality (the deciding stage)**: fused vs HAR-RV-alone on QLIKE/RMSE,
  the meta-prophet F2 methodology, multi-era, multi-instrument, causal splits. If the fusion
  does not beat the deployed engine as a FORECAST, the study ends there.
- **Stage 2+ — consumers, each its own gated pre-registration**:
  ① champions' entry re-gate with fused vf (golden-locked default-off; the Chronos program
  rule — vol-gating doesn't help this vol-seeking book — predicts neutral, so this is the
  least-priority consumer);
  ② the Exp2 sizing ramp with the fused forecast as its regime input (Exp2's own promotion
  path asked for exactly this);
  ③ FU-7 power-scaled bracket geometry on the news legs;
  ④ box stop distances (vol-scaled stops, era-0 probe redone properly).
- **Integrity**: mechanism-first; pre-registered mappings; era splits; cross-instrument
  holdout; dumb controls (shuffled-power placebo); stressed costs on any P&L claim.
