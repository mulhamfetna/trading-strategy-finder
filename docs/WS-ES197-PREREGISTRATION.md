# #197 — ES re-selection on the corrected box: pre-registration

**Filed 2026-08-30 BEFORE any trial runs.** Part of #194 phase 2. Cause: the six deployed ES champions were
*selected on a double-shifted box* (one business day of lookahead at week/month boundaries, found and
corrected in #179; full-book impact of the correction: ES 4h $74,237→$40,432, ES 2m +$12,042→−$435).

## 0. Question
On the corrected ES box, per timeframe (4h 2h 1h 15m 5m 2m): does a freshly optimized champion beat the
incumbent `best` ES champion — judged by the standard fold protocol at stressed cost — or is the incumbent
retained with cause?

## 1. Data & environment (frozen)
Server, extended root (`WSH_DATA_BASE=~/Mulham/wsg-i/FWD_EXTENDED`): candles → 2026-08-07, corrected ES box
→ 2026-08-06 (the box spans 2025-01 → 2026-08-06, which is therefore the whole optimizable frame). Own
`TMPDIR`; L1/vote caches wiped before the campaign; Postgres `wsh-pg` with the NEW study prefix **`es197`**
(never reuse a prefix — #94/#88 lessons).

## 2. Candidates per slot (frozen)
- **INCUMBENT** — the deployed `best` ES params, unchanged, re-scored on the corrected box (no fitting).
- **FRESH** — one standard campaign per timeframe:
  `optimizer.py <tf> --instrument ES --study-prefix es197 --auto-trials --trials-per-dim 100 --folds 5`
  with every default as shipped (force-EOD standard, sampler nsga3, cold start — #102 — fresh seeds, 1-min
  indicator frame). No flag tuning, no re-runs on disappointment, no second prefix. If a study crashes it
  is resumed, never restarted with different settings.
- Champion extraction exactly as the historical sets: row 0 of the feasible-Pareto CSV via
  `build_champions_from_pareto.py` (`WSI_INSTRUMENT=ES`).

## 3. Decision rule (frozen — and its honest limitation)
There is **no held-out window**: the corrected box spans only 2025-01→2026-08-06 and the fold protocol uses
all of it (this is the same epistemic position the incumbents were selected in; the LIVE run is the OOS).
Therefore, per slot:
- **ADOPT the fresh champion** iff BOTH: (a) its median-fold net at **$25/rt** exceeds the incumbent's
  re-scored median-fold net@$25 by more than the incumbent's between-fold standard error, AND (b) it passes
  the #195 allowlist criteria 3–5 recomputed on its full corrected-box book (gross ≥ 2× friction, full-book
  net@$25 > 0, not gate-dark).
- **RETAIN the incumbent** otherwise — "retain with cause" is the expected outcome for the middle rungs
  (2h/1h/15m barely moved under the correction).
- The #195 allowlist is then re-derived by its own frozen rule (a dated amendment to the JSON); ES slots may
  enter or leave it. No hand edits.

## 4. Controls & falsifiers (frozen)
- **Same-seed trap (#88):** the fresh campaign runs with fresh seeds; no result may be called replicated on
  seed agreement.
- **Random-trial control:** for every ADOPT, 20 random completed trials from the same study (seeded
  rng(197)) are scored by the same rule; the adopted champion must beat the p95 of that pool's median-fold
  net@$25 (an optimizer that only shuffles noise adopts nothing).
- **Ledger falsifier:** the BEST-SET-SELECTION-RECORD claim's V3 already proves the stored ES figures
  cannot be regenerated on the corrected box; after #197 the champion files change ⇒ that claim's evidence
  is updated in the same PR with the change recorded (never silently).

## 5. Budget (posted on the issue before launch)
~100 trials/dim × 6 slots (wsh4 norm ≈ 5,483 trials/52 dims per slot) ≈ 30–35k trials; 6 studies run in
parallel on the 32-core server; expected 6–24 h wall. Books/summaries → `optimize/es197/data/` (committed),
studies stay in `wsh-pg`.

## 6. Outputs
`optimize/es197/` (launch script + decision script), evidence `optimize/es197/data/`, claim
`claims_es197.py` (V1 decision rule re-derives per slot; V2 incumbents re-scored on the corrected box match
the round-2 books; V3 the random-trial control), report `docs/WS-ES197-REPORT.md`, updated
`best_champions_full_ES.json` (or an explicit retain-all note), allowlist amendment by rule.

## 7. Blind spots (declared)
1. No OOS inside the data — adoption is a *training-protocol* decision; the live run judges it.
2. The corrected box's 2025 rows are the same rows the incumbents trained on (only ES's alignment
   changed); improvements may partly be re-fitting to the same noise at the correct alignment.
3. 20 months of ES box data is short for 5 folds on slow TFs; min-trades pruning may thin 4h/2h candidates.
4. WS-ESCPI's ES legs are NOT re-examined here (separate follow-up if adoption changes ES 4h/2h).
