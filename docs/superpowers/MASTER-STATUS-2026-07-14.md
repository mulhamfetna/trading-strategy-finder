# MASTER STATUS — 2026-07-14 · all workstreams, one page in, full detail below

**The single reference for everything in flight on the `fundamental-analysis` branch: every workstream,
every experiment, every research pass, every discovery, and every open thread — as of the end of
2026-07-14. Read this to know where we stand before the next pivot.**

Branch: `fundamental-analysis` (pinned worktree, **not** merged, isolated from the parallel `dev` agents) ·
Author: Claude (Opus 4.8) · Reviewer: Mulham Fetna · **$0 spent** · production untouched (golden 6/6).

> **🔄 NEW DIRECTION (2026-07-14 PM) — the news workstream is RE-OPENED, narrowed + expanded.** Scope cut
> to **NQ + GC only** (drop the other 7 from future dev). Goal moves from *prediction* (answered: news is
> priced in) to *DECISION*: close / enter / **assist (scale-in after a loss)** on news, and **content →
> repeatable pattern → rule**. Plan: [`plans/2026-07-14-fa-v2-nq-gc-decisions.md`](plans/2026-07-14-fa-v2-nq-gc-decisions.md).
> ⚠️ the "assist" idea is a martingale — tested, not assumed. GC has only 2025-2026 data (fluke-window,
> like silver). **#7 (distribution) continues in parallel — the fat tail is exactly what the assist idea
> multiplies.**

---

## PART 0 — THE GREAT PICTURE

> **🍼 In one paragraph** — Over this session we asked three big questions and answered them honestly: does
> scheduled news move our market predictably (**no** — priced in, proven at full power), can we improve the
> stop-loss (**no** — it's a fair game even at 1-second resolution), and does trading-session structure
> give us an edge (**no entry edge**, but a real *risk* pattern worth using for sizing). Along the way one
> thing kept killing every apparent edge: **a huge, fat per-trade loss tail** — an ±$1,600 swing that makes
> an $80/trade "edge" statistically invisible. So the current workstream (**#7**) is aimed squarely at that
> tail: characterize it properly so future stop and sizing decisions rest on real probabilities. We just
> finished the research phase for it. **You are about to narrow that research with new information.**

| Workstream | State | The one-line verdict |
|---|---|---|
| **Fundamental analysis** (news) | ✅ **CLOSED** | Scheduled US macro is **priced in** — earned at 882 releases / 99% power |
| **Dynamic stop-loss** (#3, #11) | ✅ **CLOSED** | Dead. A martingale even at 1-second resolution; 94% of stop-outs are 2-second sweeps but chasing them doesn't pay |
| **`veto_mask` trap** (#4) | ✅ **DONE** | Renamed + documented; only `entry_gate` blocks; golden 6/6 byte-identical |
| **Session windows** (#5) | ✅ **ANSWERED** | Real in the tape & in our *risk*, not a tradeable *entry* edge |
| **Silver** (D3) | ❄️ **FROZEN** | Passed a pre-registered test but unconfirmable now — frozen forward test |
| **Own distribution** (#7) | ✅ **COMPLETE** | Trade P&L truncated (stop works); raw returns fat (α≈3); **vol-scaled stop REJECTED** (gambler's ruin) → keep fixed stop. Open: fat-tail-aware *sizing*. [`DIST-00`](DIST-00-WORKSTREAM-REPORT.md) |
| **News v2 → decisions** (NQ+GC) | ✅ **ANSWERED** | Gold reacts (NFP>CPI); close/enter negligible/no-edge; **assist REJECTED** (belief backwards); content→pattern = **volatility not direction**. [`FAV2-00`](FAV2-00-WORKSTREAM-REPORT.md) |
| **Fat-tail-aware sizing** (#17) | 🔬 **IN PROGRESS** | Research done (fractional Kelly recipe). Z1: full Kelly = 2.5% (CI [0.3%,4.4%]), 5m/2m≈0 → size small (~quarter-Kelly). Next: Z2 tail haircut, Z3 vol-target, Z4 PnL:DD |

---

## PART 1 — WORKSTREAM DETAIL

### 1. Fundamental analysis — CLOSED (priced in, earned)

**The arc:** retracted on 07-13 for 12% power → re-earned on **17 years / n=882 / ~100% power.**

| Route | Full-power result |
|---|---|
| Direction | **−0.004** (sign-hit 49.3%) — coin flip |
| Magnitude | **−0.018** — the "survivor" died; it was 2025 being the luckiest of 17 years (17-yr mean +0.027) |
| Persistence | 48.2% — coin flip |
| Shape | p = 0.880 — the surprise doesn't pick the path shape |

**Key discovery:** the improved 17-year surprise ruler corrected the whole thing — the same mechanism that
turned magnitude +0.187 into −0.018. **Reports 00–06.** The retraction was the mechanism *working*: it
predicted "get more data and it resolves," and it did.

### 2. Dynamic stop-loss — CLOSED (dead, confirmed at 1-second)

Report 04 said post-stop price is a fair martingale on 1-min bars. **Task #11 re-tested at 1-second:**
**94% of stop-outs are real 2-second sweeps** (the resolution complaint was correct!) — and the best
tradeable delay rule still earns only **+$80/trade against a ±$1,600 swing (p=0.452)**, two-thirds of which
is just "the stop is too tight." Verdict stands. **Report 06 Part 9.**

### 3. The `veto_mask` trap — DONE (#4)

The engine parameter named `veto_mask` **did not block anything** — `entry_gate` is the sole blocking
array; the veto is folded in upstream. Renamed → `veto_vote_mask`, documented the real blocking logic,
golden 6/6 byte-identical. **`ENGINEERING-NOTE-what-blocks-an-entry.md`.**

### 4. Session windows — ANSWERED (#5)

Research-first separated real from folklore, then two on-data tests:

- **S1** (17y NQ): the U-shape is real (open/lunch **1.94×**, matches literature); RTH is 2–4× louder than
  overnight; **the London–NY "overlap" is a non-event for NQ (1.00×)** — FX folklore, not index fact.
- **S3** (642 champion trades): our **RISK** inherits the session shape (**stop-out 55.6% RTH-morning vs
  15.7% Asia**, mechanistic) but our **EDGE does not** (RTH-vs-overnight p=0.147; 3/5 sessions flip sign
  across halves; only the 22:00/Asia cell holds — a silver-style frozen 1-of-6).

**Two deliverables banked:** the confound-control per-minute multipliers (S1) and the session-dependent
stop-out rate → session-aware stop sizing (S3). **No entry filter built. SESSION-00 (consolidated) + 01–03.**

### 5. Own distribution — RESEARCH DONE + D1 DONE (#7)

The verified recipe (**DIST-01**): GARCH-filter, fit the rare-large-loss tail on residuals via **EVT
(peaks-over-threshold + Generalized Pareto)**, asymmetric tails, **McNeil–Frey** conditional; all sources
are daily/hourly so re-estimate on our data.

**D1 (DIST-02) — a plan-correcting discovery:** the champion's **per-trade P&L is TRUNCATED, not
fat-tailed.** Bounded [−40,+60] on every TF; **0 of 7,356 trades** lose more than the stop; **excess
kurtosis −1.82** (negative = *light* tails); **bimodal** (~40% win@+60 / ~37% lose@−40). The "±$1,600 fat
tail" is really a **bimodal win/lose spread** (~$960) — a near-binary payoff, not a heavy tail. **The stop
truncates the fat-tailed return process** — which is *why* keep-the-stop (04/06) and never-assist (B3) are
both right. The genuine fat tail lives in **raw returns** (gap/slippage that could blow *through* the stop
live) → EVT moves there.

**D2 (DIST-03) — the raw-return tail, confirmed and quantified:** excess kurtosis **+98.6** (vs D1's
−1.82), tail index **α ≈ 3** (the inverse-cubic law, heavier than daily), loss/gain ~symmetric intraday.
🔴 **Counterintuitive:** the tail is *heavier* **overnight** (α≈2.5) than **RTH** (α≈3.4–4.9) — thin
liquidity → rare but proportionally violent gaps. So **two risks point at opposite sessions**: everyday
stop-out rate worst in RTH (S3), catastrophic tail-shape worst overnight (D2). (α is scale-free *shape*;
the absolute per-session magnitude comes from D3.)

**D3 (DIST-04) — the conditional tail, the actionable payoff:** McNeil–Frey (EWMA vol filter → GPD on
residuals). De-clustering cuts the tail but not all (kurtosis +98.6→+54.6, ξ=+0.32; deep tail ~3× a
Gaussian). **The 40-pt stop's safety is regime-conditional:** 99.9% 1-min move = 2.6pt (quiet) → 90pt (very
loud) → 164pt (extreme) — a single minute can blow *through* the stop when loud. **Resolves the D2
paradox:** RTH has higher *absolute* blow-through (19.7% of bars vs overnight 3.3%) — scale beats shape.
**Deliverable = a VOL-SCALED (constant-σ) stop/size**, not a fixed 40 pts. **Next: D4** (build + test the
vol-scaled stop on the champion ledgers; golden gate protects production).

---

### 6. News v2 → trading DECISIONS, NQ + GC — IN PROGRESS (re-opened 2026-07-15)

Narrowed scope (NQ+GC), goal moved from *prediction* → *decision*. Plan:
[`plans/2026-07-14-fa-v2-nq-gc-decisions.md`](plans/2026-07-14-fa-v2-nq-gc-decisions.md); running findings:
[`FAV2-01-FINDINGS.md`](FAV2-01-FINDINGS.md); decision research:
[`FAV2-02-RESEARCH-decisions-real-vs-dangerous.md`](FAV2-02-RESEARCH-decisions-real-vs-dangerous.md).

- **A1** ✅ — **gold reacts strongly** to US macro (7.2× a normal minute, vs NQ 8.6×), same spike shape,
  but weights events differently: **NQ↔CPI (18.5×), GC↔NFP (14.3×)** — economically sensible (different
  channels). Directional tilt is fluke-window noise, not chased. Gold is a real, *different* news instrument.
- **Decision research** ✅ — asymmetric verdict: **close-on-news** has a real mechanism (contested net of
  cost); **enter-on-news** has no edge for NQ/GC; **the "assist" (scale-in after a loss) is condemned by
  convergent, uncontested ruin mathematics** — no evidence price recovers after a news loss; test the narrow
  recovery-edge question only, default reject.
- **B1** ✅ — close-on-news **sound but negligible**: champions open across a release only ~1% of the time.
- **B3** ✅ — **the ASSIST is REJECTED** (17y, L=20/40/80): no recovery edge (p≈0.7), the "skyrocket" rate
  *falls* with loss size (61%→45%→22% — the belief is backwards), tail −$3k to −$9k at double size. Do NOT
  build — averaging-down-into-ruin, confirmed on our own data.
- **A2** ✅ — content→pattern→rule = a **VOLATILITY rule, not directional**: repeatable per-event spike-decay
  (NFP 13.6×, CPI 12.3×), but direction is a coin flip at full power (Bonferroni). Feeds #7 + session sizing.
- **Consolidated:** [`FAV2-00-WORKSTREAM-REPORT.md`](FAV2-00-WORKSTREAM-REPORT.md). **News is a VOLATILITY
  event, not direction or recovery.** B2 deprioritized; GC directional/per-event frozen (long GC history
  needed); task #16 (data sources) open. **→ Next: #7 · D1** (fit per-trade P&L — the fat tail that killed
  the assist and every edge).
- ⏳ **Task #16** — assess user-supplied external data sources (barchart, macromicro, koyfin, finviz, +2 X
  threads) for pullable point-in-time/historical data vs UI-only.

---

## PART 2 — EVERY DISCOVERY, IN ONE LIST

**Findings that STAND (measurements / robust):**
- Scheduled US macro is priced in — direction, magnitude, persistence, shape all null at ~100% power.
- The dynamic stop-loss is a martingale — even at 1-second resolution.
- 94% of stop-outs are genuine ~2-second liquidity sweeps (1-min bars really are too coarse to see them).
- The calendar self-validates: an 8.3× volatility spike lands on the exact 08:30 ET minute.
- **Timezone triple-confirmed US Eastern** — news and candles share the timezone; no mismatch (the hazard raised and disproved).
- The intraday U-shape is real on our tape (open/lunch 1.94×); the London–NY overlap is a non-event for NQ.
- Our champion's stop-out RATE is strongly session-dependent (56%→16%) — a mechanistic consequence of the volatility shape.
- Only `entry_gate` blocks an entry; "veto" params are non-blocking hints.

**Things that DIED under scrutiny:**
- The magnitude "survivor" (+0.187 → −0.018 at full power).
- The 2025 "hawkish-Fed" direction story (−0.43 → −0.004).
- The dynamic stop-loss (dead on 1-min AND 1-second).
- A broad session entry edge (3/5 sessions flip sign).
- Session folklore: the 2–3am equity-premium trade, the post-lunch effect, the London-session GMM edge (flipped with a 1-bar delay).

**FROZEN (pre-registered, unconfirmable now — re-test on future/long data, build nothing):**
- **Silver** (D3): gold-controlled partial −0.258, 4/4 quarters, but raw died under the better ruler; 1-of-36, fluke window.
- **The 22:00/Asia entry cell** (S3): +$364/trade stable both halves, but 1-of-6, n=89, fluke window.

**The THROUGH-LINE that motivates #7:** every apparent edge in this project — news, stop-loss, session —
was killed by the **fat per-trade loss tail** (an ~80-point / ±$1,600 per-trade swing). An $80/trade
effect needs ~3,200 trades to confirm against that tail. **#7 exists to characterize that tail.**

---

## PART 3 — THE DISCIPLINE (why these answers are trustworthy)

Every conclusion this session was gated by rules that are now standing law, each learned by getting it
wrong at least once:

| Rule | Learned from |
|---|---|
| No **negative** result without a **power analysis** | The 12%-power retraction |
| No **positive** result without a **dumb control** + a **noise check** | The $18,685 stop-loss "edge" that was $80/trade |
| **Pre-register** the criterion — and **implement the one you wrote** | Two verdicts that tested a different contrast than declared |
| Research **first**, on-data **second** | The deep-research-first rule (#5, #7) |
| **Never hand-type** a number — paste from the run | Nearly reconstructing a 17-row table from memory |
| Every long run gets a **watchdog** + live log; never wait blind | The empty-log silent failure |

**Self-corrections caught this session:** a healthy run killed over a misread error count; a results file
with inverted power labels; a cache that never hit; a sweep detector that was true-by-construction; two
verdicts testing the wrong contrast; a timezone guard with the wrong landmark. All caught, all fixed, all
documented.

---

## PART 4 — OPEN THREADS & WHAT'S QUEUED

| Item | Status |
|---|---|
| **#7 · D1** — fit the champion's per-trade P&L as a mixture | **queued (recommended next)** |
| #7 · D2 — tail index of NQ 1-min per session | after D1 |
| #7 · D3 — McNeil–Frey conditional (GARCH→GPD) tail | after D2 |
| #7 · D4 — decisions (stop/sizing); **sizing half needs its own research pass** | gated |
| **Silver** — re-run `study_silver.py` on future data | frozen |
| **Asia cell** — re-test on future/long data | frozen |
| **Task #15** — `test_intracandle_parity` fails 3/4 on server (pre-existing, separate default-OFF workstream; golden passes) | flagged, not this workstream |

**⏳ Awaiting your input:** you said you'll feed new information to **narrow the #7 research.** This document
is the clean baseline for that. Nothing is mid-run; the tree is committed and consistent.

---

## PART 5 — INFRASTRUCTURE & REPRODUCE

**Server layout (each study has its own data base):**
- FA / 17-year studies: `WSH_DATA_BASE=/home/dev/Mulham`
- Engine studies (champion trades): `WSH_DATA_BASE=/home/dev/Mulham/wsg-h`
- Multi-market (SI/GC/…): `WSH_DATA_BASE=/home/dev/Mulham/wsg-i/ALL_STOCKS`
- FRED key: `~/.config/fred/api_key` (mode 600, outside the repo)

**Key tools built this session:** `study_stop_1s.py`, `study_session_shape.py`, `study_session_edge.py`,
`study_silver.py`, `verify_timezone.py`, `watchdog.py`, `extended_data.load_1s_windows` (one-pass 7.3 GB
reader). **The 17-year frame is STUDY-ONLY** — the engine must never load it.

**Reading guide:** `00-INDEX.md` → this file → the workstream you care about (06 news · 04+06 stop-loss ·
SESSION-00 sessions · DIST-01 distribution). Resume pointer: `RESUME-HERE.md`.
