# SIZING · 00 — THE COMPLETE WORKSTREAM REPORT (fat-tail-aware position sizing)

**The sizing workstream, start to finish. The question left open by #7: given a tiny, uncertain edge and a
fat-tailed instrument, how much should we risk per trade? The answer, triangulated three independent ways
and stress-tested against the gap tail: a small, capped fraction — ~quarter-to-half Kelly (0.6–1.2% of
capital per trade), edge-champions only, hard cap. One method (vol-targeting contracts) looks promising but
needs a true out-of-sample test. Nothing adopted; production byte-identical; $0.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Detail: [`SIZE-01`](SIZE-01-RESEARCH-fractional-kelly.md)
(research) · [`SIZE-02`](SIZE-02-Z1-kelly-on-our-ledger.md) (Z1) · [`SIZE-03`](SIZE-03-Z2-ruin-and-gap-haircut.md)
(Z2) · [`SIZE-04`](SIZE-04-Z3-vol-targeting.md) (Z3) · [`SIZE-05`](SIZE-05-Z4-pnldd-objective.md) (Z4).

---

## PART 0 — THE GREAT PICTURE

> **🍼 In one paragraph** — "How big should each bet be?" has a precise answer (the Kelly criterion), and we
> computed it on our own trades: full Kelly is ~2.5% of capital risked per trade. But full Kelly is a
> reckless target — it delivers a ~55% typical drawdown, and it assumes our edge estimate is exactly right
> when it's a thin, fluke-window number that could be near zero. Every safety consideration — parameter
> uncertainty, drawdown probability, the fat tail, and our own PnL:DD objective — pushes the honest size
> down to a *fraction* of Kelly. The recommendation is small and boring on purpose: **risk about 0.5–1% of
> capital per trade, only on the strategies that actually have an edge, with a hard cap for the black-swan
> gap.** One idea for squeezing more out of it — scaling position size to volatility — looks promising but
> hasn't cleared an out-of-sample test yet, so it stays a candidate, not a change.

| Step | Question | Answer |
|---|---|---|
| **Research** | The sizing math? | Kelly `f*=(Bp−q)/B`; full Kelly is the ceiling; fractionalize hard for edge-error + fat tails; cap against one gap. |
| **Z1** | Our Kelly number? | **f\* = 2.5%** pooled, but 95% CI **[0.3%, 4.4%]**; 5m/2m ≈ 0 (no edge). |
| **Z2** | Tail/gap haircut? | Ruin is modest at small f; **drawdown binds** — half-Kelly for a tolerable ride. |
| **Z3** | Fixed vs vol-target? | Vol-targeting **promising** (Sharpe 3.2→3.9, both halves) but in-sample → **needs OOS**. |
| **Z4** | For our PnL:DD objective? | The ratio favors half–full Kelly, but the **absolute drawdown** there (30–62%) is intolerable → ~half-Kelly or below. |

---

## PART 1 — THE DISCOVERIES

1. **Full Kelly is small and hugely uncertain (Z1).** 2.5% pooled, CI [0.3%, 4.4%] — the edge is thin
   (realized win rate 39.8%) and the fastest champions (5m/2m) have *no* Kelly edge at all. Kelly is
   ~10–20× more sensitive to the edge estimate than to variance, and ours is a 2025–2026 estimate.
2. **The fat tail doesn't ruin you at sensible size — the volatility of full Kelly does (Z2).** A 4–6× gap
   on a bounded stop is survivable; P(ruin) stays <1% up to ~2.5%. But full Kelly gives a 50%+ drawdown two
   times in three.
3. **The PnL:DD *ratio* is a poor sizing guide (Z4).** It's flat from half- to full-Kelly because it trades
   bigger drawdowns for bigger growth at a constant ratio. The real constraint is the *absolute* drawdown
   you can live through.
4. **Vol-targeting the *contract count* is a mechanically valid lever (Z3)** — unlike D4's rejected
   vol-scaled *stop* (which broke the gambler's-ruin race). It shows a stable in-sample Sharpe edge, but the
   mechanism is unclear (corr(pnl,σ)≈0) and it's in-sample.
5. **Every angle converges on the same small fraction.** Parameter safety (Z1), ruin/drawdown probability
   (Z2), and the absolute-drawdown-under-PnL:DD view (Z4) all point to **~quarter-to-half Kelly.**

---

## PART 2 — WHAT WENT WELL / WHAT WENT WRONG

**Well:** research-first gave the exact formula and the dominant caveat (edge-error sensitivity), which Z1
then made concrete; the Z2 Monte Carlo separated *ruin* (not binding) from *drawdown* (binding); the
discipline caught Z3's raw result as leverage-inflated and forced the fair (leverage-matched, cost-charged,
split-half) comparison.

**Wrong / caught:** (1) I mis-predicted Z4 — expected the PnL:DD ratio to favor the smallest fraction; it's
flat, and I flagged the correction and the real (absolute-DD) constraint. (2) Z3's first pass compared
un-leverage-matched series (vol-targeting deployed more average size via Jensen) — corrected to a matched
comparison before drawing any conclusion. Both are the process working: predict, test, correct.

---

## PART 3 — THE RECOMMENDATION (and its guardrails)

**Risk ~quarter-to-half Kelly — about 0.6–1.2% of capital per trade** — on the **edge-champions
(4h/2h/1h/15m), not 5m/2m**, with a **hard contract cap** for the un-modeled catastrophic gap. Start at
quarter-Kelly (parameter safety); move toward half-Kelly only if the edge is confirmed out-of-sample and a
~30% drawdown is acceptable.

**Guardrails (do not skip):**
- The edge (p≈40%) is a **2025–2026 estimate**; if it's lower forward, every fraction shrinks.
- The gap model is a **D2/D3 assumption, not live fills** — a real fraction needs real slippage data.
- **Nothing is adopted.** This is a bounded recommendation, not a shipped change. Production byte-identical.

## PART 4 — WHAT REMAINS

- **Vol-targeting (Z3)** — a true **OOS test** (ideally on GC), realistic costs, and a demonstrated
  mechanism, before it's more than a candidate.
- **The wider project's open threads:** **task #16** (assess the user's external data sources), and the
  **long-GC-history data decision** — which would unfreeze the GC news/distribution work *and* give Z3 its
  OOS home. Both are the natural next moves now that the strategic questions (news, stop, session,
  distribution, sizing) are all answered.
