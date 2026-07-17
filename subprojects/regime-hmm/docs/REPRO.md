# Stage 2 — baseline: causal HMM regime on the fusion book (workstream #110)

**2026-07-15, server** (`~/Mulham/regime-hmm`, isolated venv: hmmlearn 0.3.3 + jumpmodels 0.1.1).
Script `regime_baseline.py`. Daily NQ features 2010–2026 (4977 days; features = daily log-return,
log intraday-realized-vol, 20d volume z-score). HMM fit on **train = pre-2024** (4187 days); regime at
each day = **filtered** (causal forward-algorithm) argmax; fusion trades (2024–26, 539) labeled by their
entry-day live regime. Regimes ranked 0=calmest → 3=most turbulent by realized-vol emission mean.

BIC chose **4 states** (logL/BIC: n2 −14881/29937, n3 −13540/27372, n4 −13030/26485). ⚠️ prior-art warns
4+ states can flicker — a persistence/stability check is pending (robustness stage).

## Result — the strategy is VOL-SEEKING

| regime (0=calm→3=turbulent) | trades | P/L | maxDD | Return/DD | win | days |
|---|--:|--:|--:|--:|--:|--:|
| all | 539 | $151,872 | $27,508 | 5.52 | 52% | — |
| 0 (calmest) | 15 | **−$1,354** | $7,897 | **−0.17** | 53% | 800 |
| 1 | 110 | $18,621 | $9,917 | 1.88 | 49% | 1162 |
| 2 | 332 | $101,464 | $27,019 | 3.76 | 53% | 1947 |
| 3 (most turbulent) | 82 | $33,141 | $7,982 | **4.15 (best)** | 52% | 1068 |
| **sit-out regime 3** | 457 | $118,731 | $26,498 | **4.48 (< 5.52 → HURTS)** | — | — |
| realized-vol tercile: sit-out top | 334 | $97,846 | $27,324 | **3.58 (HURTS)** | — | — |

## Discovery (the important one)
- **Our edge lives in high volatility.** The most turbulent regime has the *best* Return/DD (4.15); the
  *calmest* regime is the only losing one (−0.17). **Sitting out high-vol trades — HMM-regime or vol-tercile
  — HURTS.** This is a clean mechanistic explanation of the [TimesFM NO-GO](../../timesfm-fusion/docs/ROBUSTNESS.md):
  a high-vol veto backfires because a box-breakout strategy is vol-seeking (exactly the prior-art backfire
  condition — "momentum works better in high vol", and why it hurt ES too).
- **The signal is real but INVERTED vs the naive intuition:** the money-losing regime is calm/chop (breakouts
  fail in quiet ranges). The candidate policy is therefore **downsize / sit out the CALM regime**, not the
  turbulent one — the opposite of a vol veto.

## Honest caveats (do NOT over-read this baseline)
- **Post-hoc regime picking is the overfitting trap.** "Sit out regime 0" was *observed* here, not validated.
  It must clear the **random-regime control** (does the real regime beat shuffled labels?) and hold **per-year /
  OOS** before it means anything — the same discipline that killed TimesFM.
- 4-state model chosen by BIC alone; **stability/persistence check pending**.
- One fusion book (2024–26); the Jump Model (prior-art says it beats HMM) not yet run.

## Next (proceeding)
1. **Jump Model** baseline (jumpmodels) — same pipeline; prior-art expects it to beat the HMM (more persistent).
2. **Inverted policy test** — downsize/sit-out the CALM regime, WITH the random-regime control + per-year OOS.
3. Then full robustness → verdict (regime → policy: size/sit-out).
