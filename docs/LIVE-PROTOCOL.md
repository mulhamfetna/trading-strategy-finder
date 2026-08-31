# LIVE-PROTOCOL — the frozen rules of the live run (#199)

**STATUS: DRAFT — awaiting the owner's signature.** Nothing below is in force until the owner signs §9; at
signature this file is hash-pinned in the ledger and every later change is a dated amendment in §10. Part
of #194 phase 3. The purpose (from `docs/RUNG4-ROADMAP.md`): make the live account a scientific
instrument — a trade book executed under pre-registered rules, reconciled fill-by-fill against the engine,
judged by the same stressed-cost verdict rules as every backtest, verifiable regardless of sign.

## 1. Universe and execution (the three things the first live account changed are forbidden here)
1. **Slots:** exactly the members of `optimize/live/live_allowlist.json` (#195; sha256[:16] recorded at
   signature). Today: ES 4h/2h/1h/15m · NQ 4h/2h · GC 4h · HG 4h · NG 4h. The list changes only by
   re-running its frozen rule after a pre-registered input changes (#197 adoption, a new forward round) —
   a dated amendment, never a hand edit.
2. **Size:** **one contract, always.** No `capital_fraction`, no tiers, no martingale, no exceptions
   (RISK-02: 21.8% of trades lose more than their stop; ruin is single-trade; every sizing ramp tested on
   this system was killed).
3. **Parameters:** the deployed `best` champion set as of signature (including #197's per-slot
   adopt/retain outcomes), served from the committed champion files — the live executor must echo them in
   its journal (`entryContext`) so parity can prove what actually ran (#182's lesson).
4. **Exits:** the engine's exit machinery per champion — TP-hard / SL-soft / SL-hard / TIME_CAP / EOD with
   each slot's `cap_mode` — implemented natively or by brackets **proven equivalent in parity** (#200
   acceptance). One position per instrument root at any time (the ES_1h/ES_2h bracket-netting failure
   class). No manual intervention on open positions except the kill rules in §3.
5. **Gates:** **FROZEN** as deployed — the pre-registered #198 verdict (`GATECAL-CADENCE-NULL`): cadence
   recalibration does not beat the toll at fleet level. The exploratory allowlist-conditional observation
   enters only via its own future pre-registration and an amendment here.

## 2. Data dependencies (stated as hard)
- **Box feed:** owner-scraped, monthly cadence minimum. If the newest box row is older than 35 calendar
  days, **no new entries** fleet-wide (open positions manage to exit normally). Every box drop passes the
  gate-E merge (`fwd_merge_boxes.py --probe` first — the convention check that caught the ES double-shift).
- **Candles/tape:** the server data root per `docs/DATA-AND-KNOWLEDGE-MAP.md`; any local data tree is a
  protocol violation.

## 3. Kill rules (mechanical, no discretion)
1. **Per-trade:** broker-side hard stop always resting; if a fill reports a loss worse than 3× the slot's
   modelled SL-hard distance, the slot halts pending reconciliation.
2. **Fleet drawdown halt:** if realized fleet drawdown from the live peak exceeds **$25,000** (≈ the
   fresh-window fleet loss at $25/rt — the number the backtest says a bad quarter costs), all entries halt;
   re-arm only by a dated amendment after a written cause analysis (sticky halt, WS-DEPLOY semantics).
3. **Dependency halts:** box staleness (§2); journal write failure; parity job failure ⇒ entries halt until
   the pipeline is whole.

## 4. Reconciliation (the referee's feed)
Monthly minimum (weekly during the first two months): scrape the executor journal →
`optimize/live_parity/live_vs_engine.py` decomposition (shared/missed/extra entries; exit term; size term)
→ side-by-side table. Tolerances: shared entries ≥ 95%; qty = 1 on 100% of orders; |exit term| within the
pre-registered slippage allowance (set at signature from #200's measured brackets); extra-entry term ≈ 0.
A month outside tolerance is **flagged in the ledger as a failed month** — it stays in the record and the
cause analysis becomes an amendment; it is never explained away or excluded.

## 5. Judgement (same rules as every backtest)
- Costs: the actual commissions+fees per fill are recorded; the headline is **net of actuals**, with the
  $10/$25 stressed views alongside for comparability with the research record.
- **No verdict before power:** the first verdict window opens at **6 months**; per the WS-FWD r2 MDE math
  the 4h-rung slots need roughly a year for a $300–500/trade effect, and the protocol says so up front.
  Interim months get descriptive monthly claims (`LIVE-MONTH-<YYYY-MM>`), never performance verdicts.
- The final claim of a window states POSITIVE / NEGATIVE / UNDERPOWERED under the standard rules (dumb
  control: the same window's allowlist book replayed by the engine — live must not be *worse than its own
  engine twin* beyond the slippage allowance; noise check: bootstrap CI; power: MDE vs actual costs).
- A negative or underpowered verdict is a publishable outcome of this protocol, not a failure of it.

## 6. The never-list (violations void the run's claims from that point)
No position sizing · no manual overrides of entries/exits · no non-protocol strategies in the account ·
no parameter edits outside amendments · no window/slot cherry-picking in any report · no pausing "to wait
out" a drawdown short of a §3 halt · no reading of dashboard counts that #196 did not certify.

## 7. Roles
- **Executor** (owner/team leader): runs the bot per §1, keeps the journal, executes fixes from #200.
- **Referee** (this repo's machinery): parity runs, monthly claims, the ledger; CI keeps every number
  re-derivable.
- Fallback mode: if no broker gateway is available at signature, the identical protocol runs
  **broker-paper**, declared as such in every claim; the clock starts only if this fallback is named here
  at signature.

## 8. Prerequisites before signature (the #194 board)
- [x] #195 allowlist frozen (`LIVE-ALLOWLIST-FROZEN`)
- [x] #198 gate policy decided (`GATECAL-CADENCE-NULL` → frozen)
- [x] #196 UI single-engine (`UI-TRADES-SINGLE-ENGINE`)
- [ ] #197 ES adopt/retain outcomes folded in (campaign running)
- [ ] #200 executor compliance: clean parity decomposition on a 2-week window
- [ ] slippage allowance measured (#200) and written into §4
- [ ] owner decisions: gateway vs broker-paper; box-export cadence commitment (§2)

## 9. Signature
Owner: ____________  Date: ____________  Allowlist sha256[:16]: ____________  Protocol file sha256[:16]: ____________

## 10. Amendments (dated, append-only)
*(none)*
