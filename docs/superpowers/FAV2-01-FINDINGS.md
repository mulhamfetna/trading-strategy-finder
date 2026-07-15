# FA-v2 · FINDINGS — news × NQ + GC (running log)

**The on-data findings of the re-opened, narrowed news workstream (NQ + GC only; prediction → decision).
Plan: [`plans/2026-07-14-fa-v2-nq-gc-decisions.md`](plans/2026-07-14-fa-v2-nq-gc-decisions.md). This file
grows as A1 → A2 → B1/B2/B3 complete.**

Branch `fundamental-analysis` · $0 · production untouched. Raw output under `results/`.

---

## A1 — DOES GOLD REACT TO US MACRO? (foundational measurement) ✅

**Question:** before any GC news study, does gold even respond to scheduled US macro releases, how
strongly vs NQ, and is there a directional tilt? Both measured on the same 2025–2026 window (wsg-i) for a
fair head-to-head. Raw: [`results/news_reaction_nq_gc.txt`](results/news_reaction_nq_gc.txt).

### Result: YES — gold reacts strongly, ~84% as much as Nasdaq

| Offset from 08:30 | NQ | GC |
|---|---|---|
| −1 min (08:29) | 1.36× | 1.03× |
| **0 min (08:30)** | **8.57×** | **7.22×** |
| +1 min (08:31) | 2.95× | 2.85× |
| +3 min (08:33) | 2.58× | 2.27× |

**GC spikes 7.22× a normal minute at the release** (NQ 8.57× on the same window; GC/NQ = 0.84). The shape
is identical to NQ's: dead quiet before, explosive at the print, decaying over the next few minutes.
**Gold is a legitimate news instrument — this validates studying it.** (This is a measurement; the spike
is real regardless of sample size, exactly like NQ's 8.3× calendar self-validation.)

### The interesting bit — the two markets weight the announcements differently

Which announcement moves each market most (|move| × normal at the release minute):

| Event | NQ | GC |
|---|---|---|
| **CPI** | **18.5×** (NQ's biggest) | 11.3× |
| **Nonfarm payrolls** | 11.0× | **14.3×** (GC's biggest) |
| PPI | 9.9× | 5.6× |
| PCE | 4.1× | 3.7× |
| Retail sales | 3.4× | 3.9× |
| GDP | 2.4× | 3.6× |

> **🍼 In plain words** — **Nasdaq reacts most to inflation (CPI); gold reacts most to jobs (NFP).** That
> fits the economics: equities care about the *inflation → Fed → discount-rate* channel, while gold cares
> about the *jobs → real interest rates / dollar* channel. So the two are **genuinely different news
> instruments**, not the same bet — which is the whole reason the user added gold. This is directly useful
> for the per-event-type work (A2): the event that matters most differs by market.
>
> **⚠️ Caveat:** these per-event numbers are **n = 10–18 each** (2025–2026), so the *exact ordering* is
> suggestive, not settled. The robust reads are: (1) both react strongly; (2) CPI and NFP dominate for
> both; (3) the NQ-favors-CPI / GC-favors-NFP split is real-looking and economically sensible but wants
> more data to confirm.

### The directional tilt — a trap flagged, not chased

| Market | Mean signed return at release | % up | bootstrap p |
|---|---|---|---|
| NQ | +6.89 bp | 60.0% | **0.020** |
| GC | +4.87 bp | 53.8% | 0.110 |

The NQ "+6.89 bp, p=0.020" looks like a directional tilt. **It is almost certainly not a news signal, and
here is why I'm not chasing it:**
- It is **unconditional** (releases tend to be followed by an up-move) — a *different* thing from our
  17-year finding that the *surprise* doesn't predict direction (−0.004). The 17-year null stands.
- It is **2025–2026 only, n=85, in the fluke window** — and 2025–2026 was a **bull market**. "Prices tend
  to be higher a minute after 08:30" over a rising 18 months is mostly just the market's overall drift
  sampled at release minutes, not a news effect.
- GC shows no such tilt (p=0.110), as expected for a non-trending safe-haven over the same window.

**Verdict A1:** ✅ Gold reacts strongly to US macro (7.2×), with a sensible instrument-specific event
weighting (NQ↔CPI, GC↔NFP). The **direction** remains undecided/frozen (the |move| is real; the sign is
fluke-window noise). GC directional work needs **long GC history** — the silver bottleneck.

### → Next
- **A2** — per-event-type PATH patterns on NQ (17y, powered) and GC (2025–2026, frozen): does CPI produce
  a repeatable *shape* we can save as a rule? (The user's "content → pattern → rule.")
- **B1/B2/B3** — news-conditional trade decisions (close / enter / **assist**), gated by the incoming
  research pass on gold reaction, news position-management, and the scale-in/martingale evidence.
