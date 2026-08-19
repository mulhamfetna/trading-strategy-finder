# SCALING FINDINGS — the news layer at 1 / 5 / 10 / 20 contracts
**Studies D3 (#131, volume & participation) + D4 (#132, worked-entry validation) · window 2024→2026 · net = STRESSED costs · evidence in `evidence/`**

The one-line discovery that shaped everything: **the wall is the quiet ENTRY second, not the violent
exit** — release−300s trades a median of 7 contracts on NQ (5 on RTY) while the exit-fill seconds are
deep (231 median NQ; the release explosion is 33× the entry second). The full 300-second pre-release
window, however, carries median 1,531 contracts (NQ) — so a **worked (VWAP) entry** removes the wall,
and D4 proved the economics survives it (NQ keeps 96% of the edge; RTY actually improves +24%).

---

## qty = 1 — the baseline, deployable as verified
| | NQ | RTY |
|---|---|---|
| net / event | +$424.53 | +$95.19 (worked: **+$123.50**) |
| total 2024→2026 | +$34,387 | +$7,711 (worked: +$10,003) |
| worst event / −2R budget | −$1,018 / −$859 | −$333 / −$225 |
| entry-second participation (median) | 14.3% | 20.0% |

**Summary:** the exact configuration the whole verification chain proved (replay parity to the cent,
dashboard byte-identical to production). Single-second entry acceptable; on RTY the worked entry is
already the better model (its thin premarket whipsaws 25% of single entries before the print).
**Status: ready the moment #127's merge gate opens. Combined pace ≈ $16–17k/yr.**

## qty = 5 — feasible, work the entry
| | NQ | RTY |
|---|---|---|
| net / event (single / worked) | +$2,122.66 / +$2,034.18 | +$475.96 / **+$617.49** |
| total 2024→2026 (worked) | +$164,769 | +$50,016 |
| worst event / −2R budget | −$5,088 / −$4,294 | −$1,663 / −$1,124 |
| entry-second participation (median) | **71.4%** — marginal | 100% |
| worked-window participation | 0.3% | 0.6% |

**Summary:** the single-second entry is already strained (you'd be most of the entry second's
volume); the worked entry makes it trivial (≪1% of the window) at a 4% edge cost on NQ and a GAIN on
RTY. **Status: feasible now via the worked entry. Combined pace ≈ $83k/yr (worked).**

## qty = 10 — worked entry only
| | NQ | RTY |
|---|---|---|
| net / event (worked) | +$4,068.37 | +$1,234.97 |
| total 2024→2026 (worked) | +$329,538 | +$100,033 |
| worst event / −2R budget | −$10,175 / −$8,589 | −$3,325 / −$2,248 |
| entry-second participation (median) | 142.9% — **impossible single-second** | 200% |
| worked-window participation | 0.65% | 1.2% |

**Summary:** the single-second model physically stops existing (you would BE 1.4–2× the entire
second). The worked entry is comfortably fed and D4-validated. **Status: model-validated; needs the
owner's broker-margin check + a live worked-order path. Combined pace ≈ $165k/yr.**

## qty = 20 — the study's ceiling
| | NQ | RTY |
|---|---|---|
| net / event (worked) | +$8,136.73 | +$2,469.95 |
| total 2024→2026 (worked) | **+$659,075** | **+$200,066** |
| worst event / −2R budget | −$20,350 / −$17,178 | −$6,650 / −$4,497 |
| worked-window participation (median / thin-tail p95) | 1.31% / 2.55% | 2.49% / 5.45% |

**Summary:** combined **+$859,141 over 2024→2026 ≈ $330k/yr pace — approaching a third of the whole
deployed book** — at 1.3–2.5% window participation. RTY's exit seconds start getting heavy at this
size (21.5% median participation), so 20 is this study's honest ceiling, not a floor for further
extrapolation. **Status: model-validated ceiling; margin is a six-figure broker commitment (owner to
verify); book-depth beyond bar data remains the declared blind spot.**

---

## The verification spine under all of the above
D3 — V1 linearity to the cent (81 events × 3 qtys × 2 instruments, zero mismatches) · V3 volume
falsifier passed (the release explosion is present: 33×/18.6×). D4 — V1 dual-path VWAP zero
mismatches + the generalized bracket collapses byte-identically to the parity-proven code · V3
shifted-window falsifier flips NQ +$429 → −$534 (anchoring real). Stressed costs deployed
end-to-end, including the regime monitor (net-stressed input, stand-down proven by test).


---

# UPDATE 2026-08-19 — ES & YM scaling (RQ-1 #141 / RQ-9 #150, shipped v5.4.2)

The same D3/D4 battery, CPI-only, floor 2024, judged by a rule pre-registered before the runs
(participation median ≤2.5% / p95 ≤5% in worked-entry mode; retention ≥80%; all hard gates):

| leg | approved tier (worked) | participation at tier | retention | window net at tier (2024→26) |
|---|---|---|---|---|
| ES | **qty ≤ 20** | 0.59% / 0.98% (window median 3,389 contracts) | 85.9% | +$263,880 |
| YM | **qty ≤ 5** — q10 REJECTED (2.67%/6.11%) | 1.33% / 3.05% (window median 375) | 84.3% | +$43,481 |

Hard gates: V1 linearity to the cent (both) · V3 volume physics 48.8×/51.0× · D4 dual-path
VWAP 0 mismatches · shifted-window falsifiers flip $943/$616. Single-shot entries stay qty=1
on both legs (entry-second wall; YM qty=1 governed by RQ-7's direct fill test, Δ$0.58).
Layer at max approved tiers ≈ **$1.167M window / ~$450k/yr pace** (worked-entry model figures).
Evidence: `evidence/scaling_esym/` · ledger claim `ESYM-SCALING-TIERS`.
