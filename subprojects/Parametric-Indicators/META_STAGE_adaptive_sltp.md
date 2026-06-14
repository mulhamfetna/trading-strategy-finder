# META — Current Stage: Adaptive / Derived SL/TP

**As of 2026-06-14.** A single-page map of *where we are right now* on the SL/TP-sizing workstream — what
exists, what was decided, what's next. Points to the detailed artifacts; does not duplicate them.

---

## 1. One-paragraph state
We added an **ATR-multiplier SL/TP mode** to the backtester, discovered it appeared to "beat" the fixed
champion, and ran a deep investigation + two expert councils that established: the apparent gain was a
**measurement artifact** (in-sample window + 3× expansion band + a 14-minute ATR + a look-ahead reference),
not real edge. We **fixed the three defects** (R1 causal ref, R2 source-correct period, R3 shrink-only band),
re-verified the fixed champion is **byte-identical to golden**, and confirmed via a third council that the
**deployed champion needs no re-optimization** while **adopting any volatility-based sizing is a new search
dimension**. The user then reframed the real goal: replace stale *absolute* SL/TP with a **self-recalibrating
derived relationship** (`SL = k·D_t`). That is now an **approved action plan** (`ACTION_PLAN_derived_sltp.md`),
and we are **starting Stage 0 (feasibility)**.

## 2. What exists now (this stage's artifacts)
| Artifact | What it is |
|---|---|
| `strategy.py`, `frontend/index.html` | ATR-multiplier mode (`sltp_mode='atr'`) + R1/R2/R3 fixes + Reset/defaults fix + resizable settings panel + full-number inputs |
| `REVIEW_atr_sizing_contradiction.md` | Root-cause investigation of the "ATR beats fixed" contradiction; the 6-axis reconciliation; R1–R3 (now applied) |
| `COUNCIL_RULING_atr_sizing.md` | 6–0 ruling: the STUDY is the valid measurement; the dashboard "+21%" is a confounded in-sample artifact |
| `COUNCIL_RULING_reoptimization.md` | 6–0 ruling: fixed champion needs NO re-opt; ATR sizing IS a new search space (joint `wsh5` if adopting) |
| `ACTION_PLAN_derived_sltp.md` | Approved plan for the derived/self-recalibrating SL/TP (Approach A spine + B fitted policy), staged |
| `optimize/sub/STUDY_sub_optimizer_*.md` | The earlier dynamic-SL/TP study (shrink-only, OOS) that the councils ruled on |

## 3. Decisions locked (so we don't relitigate)
- **Fixed champion stays the deployed default** — provably byte-identical; no re-optimization triggered by
  any change this cycle (all gated behind `sltp_mode != 'fixed'`).
- **ATR-multiplier mode is kept for now**, to be removed only after the derived "Auto" mode is validated as
  the better replacement.
- **The real goal is robustness-first:** SL/TP as a ratio to a live driver so there is no absolute number to
  decay; OOS performance gain over fixed is a bonus, never a requirement to ship.
- **Validation discipline (non-negotiable):** causal features only, multi-fold walk-forward, judge on
  **return/DD not raw PnL**, fresh study prefix `wsh5`, pre-registered adopt rule (must OOS-dominate fixed).

## 4. The plan & where we are on it (`ACTION_PLAN_derived_sltp.md`)
- **Stage 0 — Feasibility (offline, cheap) ← STARTING NOW.** Does `best-SL/TP ÷ driver` stay stable across
  the 25 months (per driver)? GO/NO-GO before any GPU.
- Stage 1 — engine `sltp_mode='relative'` + Manual/Auto UI (two sub-boxes, disable inactive).
- Stage 2 — joint `wsh5` NSGA-III walk-forward (4h pilot → all TF); pre-registered adopt rule.
- Stage 3 — swap constant `k` → fitted `SizingPolicy` (Approach B).
- Stage 4 — remove the ATR-multiplier mode (cleanup) once Auto is adopted.

## 5. Safety posture
- Golden byte-match (fixed mode, all 6 TFs) is the hard gate re-run after every engine change — **green**.
- Everything new is default-OFF; nothing deployed changes until something OOS-dominates the champion.
- Secrets at the repo root (`keypass.txt`, `login.txt`, `*.ovpn`) are **never** staged.

## 6. Detail lives in
`ACTION_PLAN_derived_sltp.md` · `REVIEW_atr_sizing_contradiction.md` · `COUNCIL_RULING_atr_sizing.md` ·
`COUNCIL_RULING_reoptimization.md` · `SYSTEM_UPDATES_MEGADOC.md` (§4D) · `optimize/sub/STUDY_sub_optimizer_*.md`.
