# PROGRESS RECORD — the whole project, verbatim state

**Established 2026-08-19 by owner instruction ("it is very important to establish strong
progress record"). This is the project-wide WHERE-WE-ARE document — updated at every
workstream transition, never allowed to go stale. The GitHub mirror is the pinned progress
issue; labels + milestones organize the board; releases carry the shipped artifacts.**

---

## 0 · The one-paragraph state

Two production systems, both verified end-to-end. **System 1 — the box strategy**: 55
champions across 9 markets (~$840k/yr 2026-OOS at the deployed caps), engine golden-locked
(6/6 baselines). **System 2 — the news layer** (v5.4.2): four legs, one CPI bet — NQ + RTY
(CPI/NFP/FOMC) + ES (CPI) + YM (CPI) — $67,767 net stressed 2024→2026 at qty=1/leg,
scaled tiers approved by pre-registered rule (NQ/RTY/ES ≤20 worked, YM ≤5),
≈ $1.167M/window at max tiers (model-grade). The news research programme is **complete**:
~1,300 series×instrument cells measured, the premium grid literally closed, claims ledger
**40/40 on both machines**. **WS-FUSION is EXECUTING** (brainstorm + FU ledger, #152): the approved
order is unpaused (owner 2026-08-19) — FU-1 (the event-window audit) ACTIVE, FU-9 next;
FU-11 (#162, the owner's direction×size candidate) runs its archaeology stage. Everything is
paper-only until a live gateway; the regime monitor guards all news legs.

## 1 · Shipped releases (the immutable trail)

| release | date | what shipped |
|---|---|---|
| v5.2.0 | 2026-07 | box-strategy milestone (main==dev, golden 6/6; `best_*` deployed set) |
| v5.3.0 | 2026-08-18 | the news layer: NQ/RTY executor + regime monitor + qty≤20 worked entry; bundle v1.1.0 |
| [v5.4.0](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.0) | 2026-08-18 | ES CPI shipped (#139, descriptive-grade acceptance); bundle v1.2.0 |
| [v5.4.1](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.1) | 2026-08-19 | YM CPI acquired via the pre-registered execution gate (#147); bundle v1.3.0 |
| [v5.4.2](https://github.com/mulhamfetna/trading-strategy-finder/releases/tag/v5.4.2) | 2026-08-19 | scaled tiers ES ≤20 / YM ≤5 (#141/#150); bundles v1.4.0 + v1.4.1 (docs-current) |

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
| RQ-2 (Retail short) | #142 | absorbed into FU-8 (#160) |

## 3 · ACTIVE + QUEUED (the live board)

- **WS-FUSION (#152, EXECUTING)** — plan approved and UNPAUSED (2026-08-19): FU-1 ACTIVE
  (#153), FU-9 next (#161); order FU-1→FU-9→FU-2/3→FU-7→FU-5/6. Use-cases #153–#161.
- **FU-11 (#162, the owner's flagged candidate)** — Direction × Size fusion: the early-era
  "direction predictable, size not" claim × the confirmed M2 power model ("size predictable,
  direction not"). Three gated stages (archaeology → re-audit under modern discipline →
  fusion design). **Stage 1 (archaeology) ACTIVE; stages 2/3 gated on its outcome.**
- **Research queue** (`RESEARCH-QUEUE.md`): RQ-4 YM direction row (#144), RQ-5 metals cost
  frontier (#145) — queued. Standing rule: an observation without an RQ/FU number does not exist.
- **Then**: WS-EARN return (earnings alone → ×indicators → ×news×indicators, reusing the
  news machinery + FU-9's schema).

## 4 · The verification state (what "trusted" means right now)

Claims ledger **40/40** (local AND server; `optimize/verify/run.py`) · engine golden gate
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
