# RQ-1 (#141) + RQ-9 (#150) pre-registration — ES & YM CPI scaling, and the scaled-deploy rule

**Filed BEFORE any run (commit date = filing date). Owner instruction (2026-08-19): run the
ES CPI and YM CPI scaling tests; "if worked out we will deploy both scaled."**

## Design — the exact D3/D4 battery, restricted to each leg's deployed series (CPI)

Machinery: `src/deploy/scaling_study.py` (D3) and `src/deploy/worked_entry_study.py` (D4),
extended only by a `--series` filter (mirroring the executor; default = full schedule so
NQ/RTY behavior stays byte-identical). Window: **floor 2024** (the D3 convention — the
operative window). Qty grid: **{1, 5, 10, 20}**. Costs/PVs from the deployed tables
(ES $50/pt · $52.50/event; YM $5/pt · $22.50/event), costs scaling linearly with qty.

## Hard verification gates (any failure ⇒ the tier — or the study — is VOID, not approved)

- **V1 linearity**: per-event dollars at every qty = qty × (qty=1) TO THE CENT; per-contract
  points qty-invariant. (Arithmetic integrity of the engine.)
- **V3 volume physics**: the exit-fill second's volume materially above the entry second's
  (median ratio > 3) — the release volume explosion is physics; absent ⇒ volume alignment
  broken ⇒ VOID.
- **D4-V1**: worked-entry VWAP dual-path (numpy dot vs pandas) zero mismatches.
- **D4-V3**: shifting the build window by +360 s must change the result by > |$100| —
  anchoring is real, else VOID.

## The scaled-deploy rule (a-priori; the same regime the deployed NQ/RTY tiers passed)

Per instrument, per tier Q ∈ {5, 10, 20}, in **worked-entry mode** (VWAP over
[rel−300 s, rel−5 s), bracket active from rel−5 s — the validated D4 model):

1. **Participation**: Q / window-volume — median ≤ **2.5 %** AND p95 ≤ **5 %**
   (the deployed NQ/RTY qty=20 regime was 1.3–2.5 %).
2. **Edge retention**: worked-entry per-event net ≥ **80 %** of the single-entry net at the
   same Q (NQ kept 96 %, RTY improved), and positive.
3. All hard gates green.

**DEPLOY each leg at the highest tier passing all three** (worked-entry mode; single-shot
entries stay approved only for Q with entry-second participation median ≤ 25 %, the D3 line).
A leg whose best tier is 1 simply stays as-is — that is a finding, not a failure.
Expectations recorded (cannot drift): ES (deepest book) likely clears 20; YM's window median
364 contracts puts qty=20 at ≈ 5.5 % median — **borderline by design; the rule decides, not
preference.**

## Blind spots (declared)

1. 1-second volume bounds participation, not book depth or queue position (D3's standing caveat).
2. Worked-entry fills at window VWAP assume fair fills at ≤ 2.5 % participation — the same
   model property the deployed NQ/RTY tiers carry; it is a model, reported, never netted away.
3. CPI-only samples are n≈29 per leg in the window — the ECONOMICS at scale inherit the
   already-verified per-event edge; this study verifies FEASIBILITY (participation + retention),
   not the premium again.
4. Margin at four scaled legs remains owner-side, as always.
