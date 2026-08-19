# The Research Queue — every identified-but-untested item, formally registered

**Instituted 2026-08-18 by owner instruction: "approve those tests and queue them in proper
documentation instead of random dropping incidents."** Rule from here on: any study-worthy
observation that a workstream cannot pursue in-scope gets an RQ entry + its own GitHub issue
AT THE MOMENT IT IS FOUND — never a loose remark in a report or chat. An RQ item is *queued*,
not started: work begins only when the owner pulls it (the WS-FUSION → WS-EARN pipeline keeps
its owner-ordered priority over everything here).

Update discipline: add entries at the bottom with the next RQ number; never renumber; when an
item starts, link its workstream issues here and mark ACTIVE; when it finishes, mark CLOSED
with the verdict. This file is the index — the design detail lives in each item's issue.

| ID | item | origin | issue | status |
|---|---|---|---|---|
| RQ-1 | **ES CPI scaling study** (D3/D4-style: per-second participation, worked entry, qty 5/10/20 for the ES CPI ride) | WS-ESCPI blind spot — qty=1 arithmetic only; ES has the deepest book of the four indexes | #141 | **CLOSED-DEPLOYED** — ES approved at qty≤20 worked (0.59%/0.98%, retention 85.9%); shipped v5.4.2 |
| RQ-2 | **Retail short-side study** — the anti-premium is gross-negative on 7 instruments; is its SHORT side tradeable at cost? | N3 + WS-GRID; hypothesis generated from the full history ⇒ needs forward-era or fresh-design confirmation, own pre-registration | #142 | QUEUED |
| RQ-3 | **ES CPI forward paper-confirmation track** — paper intents beside the live layer; future CPI prints vote (~6–12 months to power) | the #139 ship-decision option 2; design pre-drafted so it can start the day the owner picks it | #143 | CLOSED-SUPERSEDED — the owner shipped on descriptive grade; the layer is paper-only until a gateway, so the forward record accumulates automatically in live operation |
| RQ-4 | **YM direction study** — the missing 9th row of WS-NEWS2's direction grid (YM was excluded for its 0-byte 1m frame, now FIXED) | WS-ESCPI's YM re-assembly; direction was dead 8/8 — this closes the literal direction grid | #144 | QUEUED |
| RQ-5 | **Metals CPI cost-frontier** — HG gross +$80/ev and SI gross +$48/ev at CPI are positive but drowned by $52.50/$102.50 cost lines; micro contracts or measured (not formula) costs could change the verdict | WS-GRID finding 1 | #145 | QUEUED |
| RQ-6 | **Coverage-matrix regeneration** — merge the 661 grid verdicts into `NEWS-COVERAGE-MATRIX.md` so the premium column shows per-instrument status instead of the superseded "NEVER" | WS-GRID documentation debt | #146 | QUEUED |
| RQ-7 | **YM CPI promotion path** — the grid's only positive (+$107.64 net, p=0.0016, jump 9.8×; thin tape median 101 pre-release seconds ⇒ execution study required, not just statistics) | WS-GRID + the ESCPI descriptive; same data as #139's evidence — rides on the same owner decision | #147 | **CLOSED-ACQUIRED** — the pre-registered execution study passed all four ACQ layers (staleness p95 7.2s; next-open Δ$0.58; depth 364; exit 638s/4081); YM CPI deployed in v5.4.1; qty>1 still gated on its own D3/D4 study |
| RQ-9 | **YM CPI scaling** — D3/D4 battery for the fourth leg | v5.4.1's qty>1 prohibition | #150 | **CLOSED-DEPLOYED-CAPPED** — q5 passes (1.33%/3.05%), q10 breaches (2.67%/6.11%) ⇒ YM qty≤5 worked; shipped v5.4.2 |
| RQ-8 | **WS-FUSION** — indicators × news (opens with deep brainstorming + a follow-up system); then the **WS-EARN return** (earnings alone → ×indicators → ×news×indicators) | owner roadmap 2026-08-18 | **#152** | **ACTIVE** — opened 2026-08-19 with the deep brainstorm + the use-case follow-up ledger (owner instruction: "proceed to newsxindicators") |

## Standing intake rule (for every future workstream)

When an experiment surfaces something out-of-scope: (1) same day, add the RQ row and open the
issue with origin + question + design sketch + prerequisites; (2) reference the RQ ID in the
workstream report instead of prose like "noted for later"; (3) the ledger may cite RQ IDs in
blind-spot fields. An observation without an RQ number does not exist.
