# PROGRESS RECORD — the whole project, verbatim state

**Established 2026-08-19 by owner instruction ("it is very important to establish strong
progress record"). This is the project-wide WHERE-WE-ARE document — updated at every
workstream transition, never allowed to go stale. The GitHub mirror is the pinned progress
issue; labels + milestones organize the board; releases carry the shipped artifacts.**

---

## 0 · The one-paragraph state

Two production income systems plus one information layer, all verified end-to-end
(claims ledger **64/64 on both machines**). **System 1 — the box strategy**: 55 champions
across 9 markets (~$840k/yr 2026-OOS at deployed caps), engine golden-locked (6/6).
**System 2 — the news layer** (v5.4.2): four legs, one CPI bet — $67,767 net stressed
2024→2026 at qty=1/leg; scaled tiers approved by rule (NQ/RTY/ES ≤20 worked, YM ≤5),
≈$1.167M/window model-grade. **The power-forecast layer** (v5.4.3, FU-14): night-before
event-size forecasts, information-only. **WS-FUSION is CLOSED (2026-08-20)**: 14
pre-registered studies in 2 days — the fused forecast WON its quality stage (the live vol
gate's one blindness proven repairable), every P&L consumer closed under its own rule, and
the deployed structure (state-blind entry, flat sizing, frozen geometry) is now VALIDATED
BY MEASUREMENT; per-layer profit attribution lives in `SYSTEM-LAYERS-ANALYSIS.md` §5.
Everything paper-only until a live gateway; the regime monitor guards all news legs.
**The WS-EARN return RAN (era 10, 7 studies, one day)** — earnings power forecastable, the
blindness law spans both calendars, the E-S1 substrate frozen, state-blind extended to
size, and **E-D1 released in v5.5.0** (the two-calendar layer: the gate's nightly blindness
schedule; routing, never fitting). **Era 12 (WS-FWD, 2026-08-21): the tape is extended to
2026-08-07 for all 9 instruments under exact gates and all 54 champions re-booked on it —
but the fresh window is a 25-trade sliver because the scraped BOX feed ends in June; the
owner's box export is the single unlock. Sharp findings: NQ 5m dark since April (frozen
gate), 8 slots negative at $10/rt friction (NG ladder).**

## 1 · Shipped releases (the immutable trail)

| release | date | what shipped |
|---|---|---|
| v5.2.0 | 2026-07 | box-strategy milestone (main==dev, golden 6/6; `best_*` deployed set) |
| v5.3.0 | 2026-08-18 | the news layer: NQ/RTY executor + regime monitor + qty≤20 worked entry; bundle v1.1.0 |
| [v5.4.0](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.0) | 2026-08-18 | ES CPI shipped (#139, descriptive-grade acceptance); bundle v1.2.0 |
| [v5.4.1](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.1) | 2026-08-19 | YM CPI acquired via the pre-registered execution gate (#147); bundle v1.3.0 |
| [v5.4.2](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.2) | 2026-08-19 | scaled tiers ES ≤20 / YM ≤5 (#141/#150); bundles v1.4.0 + v1.4.1 (docs-current) |
| [v5.4.3](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.3) | 2026-08-19 | the power-forecast layer deployed (FU-14, information-only, bundle v1.0.0) + the Exp2 sizing ramp honestly killed (FU-13 NOT-DEPLOYED) |
| [v5.5.0](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.5.0) | 2026-08-20 | the two-calendar forecast layer (E-D1, routing pattern, information-only; bundle v1.0.0) + WS-FUSION closure + era 10 (the WS-EARN return, 7 studies) |
| [v5.5.1](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.5.1) | 2026-08-20 | ⭐⭐ THE ROADMAP COMPLETES: XNI closure (law #1) + X-3 collision-priced artifact (bundle v1.1.0) + X-4 dashboard event-window tags + X-5b monitor context field — all information-only, parity-proven, never-gates |

## 2 · The workstream history (what is CLOSED, with its verdict)

Full experiment-level detail: `NEWS-MASTER-EXPERIMENT-RECORD.md` (eras 0–8) and the
per-workstream full records. The one-line-each version:

| workstream | issues | verdict |
|---|---|---|
| WS-NEWS2 (calendar + direction) | #114–#123 | direction DEAD on 643 pairs; the ≥2016 timestamp rule; TradingView chosen |
| WS-NEWS3 (the premium) | #117, #124–#126 | the confirmed ride: NQ +$133.06/RTY net, Bonferroni+holdout |
| WS-DEPLOY | #127–#132 | executor (parity to the cent), regime monitor, qty≤20 worked → v5.3.0 |
| WS-NEWS4 (dropped series) | #134–#138 | ZERO new premiums (11,822 moments); Retail anti-premium CONFIRMED; EIA/API powered NO |
| WS-ESCPI | #139 | ES CPI shipped v5.4.0; the YM-holdout saga (corrupt file → rebuilt from raw → VOID-DATA) |
| WS-GRID | #140 | the literal full grid: 661 cells, ONE positive (YM CPI); CPI = equity-index phenomenon NQ>ES>YM>RTY |
| RQ-7 (YM execution) | #147 | ALL 4 ACQ layers pass → YM acquired v5.4.1; traded-seconds density ≠ fill quality |
| RQ-1/RQ-9 (scaling) | #141/#150 | ES ≤20 approved; YM capped at 5 BY THE RULE → v5.4.2 |
| RQ-6 (matrix regen) | #146 | grid verdicts merged into the generated coverage matrix |
| RQ-3 (forward-confirm) | #143 | superseded — paper-only live operation IS the forward record |
| RQ-2 (Retail short) | #142 | CLOSED via FU-8: Retail loses BOTH WAYS — the anti-premium is chop, not drift |
| **WS-EARN return (era 10)** | #109/#169 | **CLOSED 2026-08-20**: earnings power forecastable (ρ .4583/.3323); the vol-gate blindness spans both calendars; the 924-row substrate frozen; fitted-joint interference confirmed at power (the powered-tolerance law); state-blind extended to SIZE; **E-D1 the two-calendar layer RELEASED v5.5.0** |
| **XNI phase 3 (era 11)** | #172–#173 | **CLOSED 2026-08-20**: law #1 (the calendars resolve independently — compound power is pure addition); X-3/X-4/X-5b information artifacts **RELEASED v5.5.1**; X-5 informative-decomposed; X-2/X-6 parked-with-cause. ⭐⭐ **THE ROADMAP COMPLETE** |
| **WS-FUSION (time × state)** | #152–#168 | **CLOSED 2026-08-20**: FU-14 deployed + FU-11 Stage 1 WON (the fused forecast beats the live gate); every P&L consumer closed with a law (veto=seasonality; sizing NQ-local ×3 asymmetry proof; geometry=width bias; state gates null; classifier bar held by 0.003; Retail loses both ways); FU-9 dataset built (no-repaint proof); closing bilingual report + WS-EARN hand-off shipped |
| **WS-FWD (era 12 — champions forward run)** | #176 | **CLOSED 2026-08-21**: candles extended to 2026-08-07 all 9 under exact gates (16y set ≡ vendor, 0 mismatches incl. volume; parallel root, prod untouched); 54/54 books rebuilt (NQ 4h anchor closes to the cent); **fresh window = 25 trades only — the scraped BOX FEED ends 06-09/05-21/06-26; owner box export = the unlock**; ⭐ NQ 5m dark since 04-25 (frozen gate quantile vs the 2026 regime); ⭐ 8 slots negative at $10/rt (NG ladder = friction illusion); full report + Playwright-verified dashboard sweep + claims FWD-×3 |

## 3 · ACTIVE + QUEUED (the live board)

**The board is QUIET AND GREEN (2026-08-21, post-WS-FWD)**: no active workstream, no
unverdicted study, no stale doc. Everything open is deliberate:

- **Owner-side items (the only movers of new profit)**: the LIVE GATEWAY (all income is
  paper until it — $67,767/window earned and uncollected) · broker margin at the approved
  tiers · the C4 timestamp spot-check (#110) · a forward earnings calendar (lights up the
  earnings side of the nightly artifact) · **a fresh BOX export through 2026-08 for all 9
  instruments (#176 — turns the extended tape into a real ~2-month OOS test of all 54
  champions; also: a standing box-refresh cadence — the with20d drop sat unswapped since
  June)** · the prod data-root swap decision · the vol-gate recalibration campaign
  (NQ 5m dark since April; a re-optimization decision).
- **Queued next (owner's word)**: the ORB (opening-range-breakout) study on all
  instruments — new issue + deep-research-first + own pre-registration.
- **Deliberate holds**: FU-15 dual-sided bracket (#168, parked by owner — first in line on
  the word) · FU-4 (gated-off) · FU-11 consumers ① re-gate / ④ stops (low-priority) ·
  X-2/X-6 (parked-with-cause under law #1).
- **Fresh-registration hypotheses (future data only, never re-tested on consumed history)**:
  the ES-led T1 super-additivity texture · FU-6's 0.577 tree · FU-3's NQ sizing texture.
- **Research queue**: RQ-4 (#144), RQ-5 (#145) — queued. The optimizer research arm
  (#79–#108) keeps its own queue, unchanged by these eras.

## 4 · The verification state (what "trusted" means right now)

Claims ledger **53/53** (local AND server; `optimize/verify/run.py`) · engine golden gate
**6/6 baselines MATCH** · executor replay parity to the cent on all four legs · portable
bundle `--verify` PASS NQ/RTY/ES/YM · dashboard branch ≡ production (screenshot evidence) ·
isolation battery 18/18. Every published number is ledger-bound or re-derivable from a
committed file; `expect` values are never adjusted.

## 5 · Data & infra assets (and their sharp edges)

- 1-second archive, 9 instruments, 2010→2026 (server `~/Mulham/data_2010_1s/`); **YM rebuilt
  from raw 2026-08-18** (was corrupt; its 0-byte 1m frame is fixed — YM fully studyable).
- TradingView calendar (39,221 events, 649 series; usable ≥2016 — pre-2016 DST-broken).
- Server: AMD box (123 GB), worktrees `~/Mulham/code`=dev · `~/Mulham/earn1`=legacy18;
  dashboard :8200 production, :8250 branch; venv `data_2010_1s/venv` (scipy via `python3 -m
  pip`; its pip binary is broken).
- Known traps live in the memory index and the full records (gitignore blanket rules,
  untracked-now-tracked pulls, pkill-by-port, tie-break instability, cost-drag reading, …).

## 6 · Standing guards (unchanged, non-negotiable)

Paper-only until a live gateway · regime monitor GO required on every news leg · YM qty>5 and
any new instrument/tier requires its own pre-registered study · margin at size owner-side ·
pre-registration before runs · V1/V2/V3 + ledger before publishing · all work inside the
trading root.

## 7 · How this record is maintained (the GitHub feature map)

| feature | use |
|---|---|
| **This file** + the pinned **📌 PROGRESS issue** | the always-current state (update both at every transition) |
| **Milestones** | one per workstream — closed carry their verdict, open carry the plan |
| **Labels** | `workstream:*`, `family:*`, `status:*` on every issue — the board is filterable |
| **Issues** | one per phase/use-case; every step a comment as it happens; bodies never edited |
| **Releases** | every ship, with the bundle attached — the immutable artifact trail |
| **The claims ledger** | the machine-checked truth of every number |
