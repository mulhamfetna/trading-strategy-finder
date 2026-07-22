# Fundamental Analysis — Closeout & Next Directions (2026-07-22)

**Purpose.** The `fundamental-analysis` workstream is complete. This report states plainly *where we
stopped*, *what the dead ends are*, *whether we actually improved profitability*, and *what is worth
building next* — so we can leave this topic and move to the highest-value follow-on with a clear head.
It consolidates `MASTER-STATUS-2026-07-14.md` plus the work finished since (gap-aware fills, re-optimization,
honest sizing, gold forward-validation).

> **📌 UPDATE (2026-07-22 PM) — regime-sizing candidate re-evaluated on the current champions.** The
> recommended next step (#1, regime sizing) was tested on the post-v5.1.0 adopted champions. Headline: the
> *old* ramp now **hurts** (−$60k), but a **refit generalizes out-of-sample** (+$18k on held-out 2026).
> Full previous-vs-current write-up in **§5.1**; the recommendation in **§6** is updated accordingly.

---

## 1. Where we stopped — everything is answered

Every question the branch opened is closed, and the three "actionable-now" follow-ups it had listed
(re-optimize, re-cut risk, forward-validate gold) were finished this session.

| Sub-question | Verdict |
|---|---|
| Does scheduled macro news predict **direction**? | **No** — priced in, proven at 882 releases / ~99% power. **Replicates on gold** (n=866). |
| Trade *on* the news (close / enter / **scale-in after a loss**)? | **No** — close-on-news ≈ negligible (champions open across a release ~1% of the time); enter-on-news = no edge; **scale-in = ruin math, rejected** (recovery rate *falls* with loss size — the belief was backwards). |
| A smarter / **dynamic stop-loss**? | **No** — a fair martingale even at **1-second** resolution (94% of stop-outs are genuine ~2-second liquidity sweeps, but chasing them doesn't pay). |
| A **session-window** entry edge? | **No** — 3 of 5 sessions flip sign across halves; the one survivor (Asia 22:00) tested out-of-sample cross-instrument → **fluke** (0/3 indices replicate). |
| **Vol-scaled stop** / **vol-targeting** sizing? | **Rejected** — the stop-out rate is regime-flat (55/56/57%); a σ-stop would swing; halves flip. |
| Gold's **inverse macro reaction**? | **Real but un-tradeable** — forward-validated (766 OOS trades, t=+4.26, gold-specific) but the entire edge is the release-instant jump; a causal entry earns ~\$0, dead at cost (`GC-02`). |

**Nothing is mid-run.** The tree is committed, consistent, and released as part of v5.1.0.

---

## 2. Did we improve profitability? — Yes, but be clear *how*

This distinction matters and should not be blurred:

- **The fundamental *signals* (news, sessions, gold-macro) improved profitability by \$0.** There is no
  tradeable *directional* edge in any of them. That is the settled, honest result.
- **The engine-correctness + re-optimization work that came out of this branch improved the book by
  +\$35,475 out-of-sample (+13.6%)** (`GAP-03`). That gain is *not* a new edge — it is better exploitation
  of the *existing* box edge, recovered because the old champions had been tuned on a distorted
  (gap-free) engine. Full-window +\$52,443; 2026 out-of-sample +\$35,475 (+13.6%).
- Separately, the honest-fills fix revealed drawdown had been **~10% understated** — a *risk*-accuracy
  improvement (know your true risk), and the risk budget was re-cut to a true **~0.25–0.5% of capital per
  trade** (`RISK-01`).

So the "fundamental analysis is a directional edge" thesis **failed**, but the branch still paid for
itself, +13.6% out-of-sample, through the correctness/re-optimization cleanup it forced.

---

## 3. The dead ends (so we don't re-litigate them)

1. **News as direction** — priced in.
2. **News as a decision** — close ≈ nothing; enter = no edge; **scale-in-after-loss = averaging into ruin.**
3. **Dynamic stop-loss** — martingale at 1-min *and* 1-second.
4. **Session entry edge** — flips across halves; Asia cell = fluke.
5. **Vol-scaled stop & vol-targeting** — rejected on their own temporal splits.
6. **Gold macro trade** — real, durable, un-tradeable (gone before you can enter).
7. **Silver** — frozen (long history never landed on the server).
8. **The through-line:** every small edge is killed by the **fat per-trade loss tail (worst case ≈ \$3,029/
   trade)**. An \$80/trade effect needs ~3,200 trades just to confirm against that tail.

---

## 4. The strategic lesson — direction is dead, so **sizing** is the lever

The single unifying finding across the whole project: **we cannot predict direction (news is priced in,
sessions flip), but the box edge is real and *volatility-seeking* — it lives in the most turbulent
regimes.** That reframes where the leverage is:

> Stop hunting for a signal that picks *sides*. Put the effort into **how much to bet, and when** —
> modulate *risk/size* with the regime, not the *entry direction*.

Two independent results point the same way: classic inverse-vol targeting *hurt* this strategy, while
sizing *with* volatility helped — because the edge is vol-seeking.

---

## 5. Potential improvements we can still implement (ranked)

| # | Improvement | Why it's promising | Status |
|---|---|---|---|
| **1** | **Regime-based sizing** — size by the day's volatility regime | Validated *direction* on the old champions (PnL:DD 5.52→5.90). **Re-evaluated 2026-07-22 — see §5.1:** the old ramp *hurts* the new champions, but a **refit generalizes OOS** (+$18k on 2026). | **re-evaluated → refitted candidate** |
| 2 | **Exogenous-signal fusion → a policy head** — VIX / breadth / rates / options → *size / sit-out / SL-TP*, **not** entry direction | The correct home for "fundamental" data now that direction is dead: use it to modulate *risk*, not to pick sides. | parked, **blocked on VIX data** |
| 3 | **Intra-candle vetoed entry** — increase entries toward near-zero-day-hold | Phase-1 was OOS-validated: ~2× the entries at ≥ champion P/L. Serves the stated "increase entries" direction. | parked mid Phase-2 wiring |
| 4 | **Apply the tail model to per-trade risk** | #7 characterized the tail (EVT ξ<0 bounded by the stop, but 3.9% gap *through* it) — a tool that could feed regime-aware sizing (#1/#2). | characterized, not applied |

---

## 5.1 Regime-sizing candidate — PREVIOUS result vs CURRENT re-evaluation (2026-07-22)

Because #1 was the top recommendation, it was tested on the current champions **before** proposing any
deployment. This section carries both the previous team's result and our re-evaluation, so the picture is
self-contained.

### Previous (the parked `research-regime-edge` result, on the OLD champions)
- Overlay: for each trade, multiply P&L by a linear ramp by the day's causal HMM volatility regime — calmest
  **0.5×** → most turbulent **1.5×** — then normalize the book to hold max-drawdown at the flat book's
  ("equal risk"). It is a *sizing* overlay, not an entry change.
- Result on the 2024–26 NQ 1h+4h fusion book: PnL:DD **5.52 → 5.90**, **+$10,356 at equal risk**; beat 96%
  of random regime→size shuffles; the textbook *inverse*-vol control *hurt* (4.06) → the strategy was
  **vol-seeking** (earns best in the most turbulent regime).
- Honest verdict already recorded by that team: **EXPERIMENTAL CANDIDATE, not confirmed** — the dollar uplift's
  90% bootstrap CI was **[−$21k, +$62k] (includes zero)**; shipped **OFF by default**.

### Current re-evaluation (post-v5.1.0: honest gap-aware engine + the ADOPTED NQ 1h champion)
*Code validated first: our overlay reproduces the previous result on the reference book to the dollar
(5.52 → 5.90, +$10,356), so the new numbers are trustworthy.*

| NQ 1h+4h fusion | Flat PnL:DD | + old ramp (0.5→1.5) | Inverse ramp (dumb control) |
|---|---|---|---|
| **Old champions** (reference) | 5.52 | **5.90 (+$10,356)** ✅ | — |
| **Adopted champions + honest engine** | **12.43** | **8.62 (−$59,763)** ❌ | **15.83** ✅ |

**The signal flipped.** On the adopted book the old ramp **hurts by −$59,763**; the *inverse* ramp *helps*
(12.43 → 15.83); the old ordering now beats only **23%** of random maps (was 96%). Cause: the adopted NQ 1h
champion (tighter stops, +45% P&L) earns **most in the calmest regime and least in the most turbulent** — the
opposite profile. **The "vol-seeking" property was a property of the *old* champion, not a durable truth.**
Deploying the old overlay would have cost ~$60k — caught by re-evaluating on the actual current book.

### Can we refit it (the natural question) — is that overfitting?
Two parts: the **regime model** (the HMM day-labeler) is champion-independent and needs no change; only the
**ramp** does. Refitting the ramp is legitimate *if* the direction is derived a-priori from a **causal,
held-out** measurement — not tuned to maximize P&L on one book. We ran exactly that honest test — derive the
ramp on TRAIN (2024–25), apply it **unchanged** to held-out 2026:

| | Flat PnL:DD | Refit | Equal-risk Δ |
|---|---|---|---|
| Train 2024–25 | 7.23 | 9.64 | +$37,898 ✅ |
| **Held-out 2026** | 7.83 | **9.59** | **+$18,340 ✅** |

**The refit helps on data it never saw → it is *not* overfitting.** The refitted direction is the *inverse*
of the old one (downsize turbulent / upsize calm), matching the new champion's profile.

### Two riders that keep it a *candidate*, not an edge
1. **Champion-specific + fragile.** The direction *flipped* between two champions; a refitted overlay must be
   **re-derived and re-validated on every champion change** — not set-and-forget.
2. **Magnitude still unconfirmed.** Everything is inside **2024–26 — one bull era, no bear market.** The n=1
   confidence gap is about **data (a 2010–2023 bear-inclusive book)**, not about fitting; refitting does not
   close it.

---

## 6. Recommendation & next step

The regime-sizing re-evaluation changes the recommendation from "deploy #1" to a data decision.

**The single highest-leverage next move is acquiring the 2010–2023 NQ box data**, because that one gap is the
binding constraint on *three* threads at once: (a) confirm-or-kill the refitted regime overlay's magnitude,
(b) give the entire strategy its first **bear-market test** (all our validation is one bull run), and (c)
unblock **silver** (frozen for the same missing-history reason). We already have the in-house Databento
pipeline that produced gold's 16-year frame; if it can produce 2010–23 NQ box levels the same way, it unlocks
all three. Modeling harder on a one-era book only yields more well-caveated candidates against the same wall.

- **If the 2010–23 data is reachable:** run the bear-inclusive re-evaluation — properly confirm/kill the
  refitted regime overlay and stress the whole book through a downturn.
- **If not:** shelve regime sizing as a documented refitted candidate and pivot to **#3 intra-candle entries**
  — deployable today, serves the "increase entries" goal, and (unlike regime sizing) it is *not*
  champion-fragile.

#2 (exogenous VIX/breadth fusion) remains blocked on external data.

---

**Topic status: fundamental analysis CLOSED.** Regime sizing = **refitted candidate, gated on 2010–23 data.**
Reproduce: `regime_recheck.py` (old-ramp flip) · `regime_refit_oos.py` (refit OOS test), on the server.
