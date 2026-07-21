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
> thing kept killing every apparent edge: **a huge per-trade loss tail** — a swing that makes an $80/trade
> "edge" statistically invisible. (⚠️ that swing was quoted as ±$1,600 throughout; on the corrected ledger
> the real per-trade worst case is **$3,029** — see [`BUG-01`](BUG-01-sizing-studies-ran-the-wrong-strategy.md).) So the current workstream (**#7**) is aimed squarely at that
> tail: characterize it properly so future stop and sizing decisions rest on real probabilities. We just
> finished the research phase for it. **You are about to narrow that research with new information.**

| Workstream | State | The one-line verdict |
|---|---|---|
| **Fundamental analysis** (news) | ✅ **CLOSED** | Scheduled US macro is **priced in** — earned at 882 releases / 99% power |
| **Dynamic stop-loss** (#3, #11) | ✅ **CLOSED** | Dead. A martingale even at 1-second resolution; 94% of stop-outs are 2-second sweeps but chasing them doesn't pay |
| **`veto_mask` trap** (#4) | ✅ **DONE** | Renamed + documented; only `entry_gate` blocks; golden 6/6 byte-identical |
| **Session windows** (#5) | ✅ **CLOSED 07-20** | Real in the tape & in our *risk*, not a tradeable *entry* edge. The one frozen exception (Asia/22:00) tested OOS cross-instrument → **FLUKE** (0/3 indices replicate). [`SESSION-04`](SESSION-04-asia-cell-oos-verdict.md) |
| **Silver** (D3) | ❄️ **FROZEN** | Passed a pre-registered test but unconfirmable now — frozen forward test |
| **Own distribution** (#7) | ✅ **RE-EARNED 07-20** | Trade P&L **bounded at −151.4/+125.6** (EVT ξ<0), **3.89% gap THROUGH the stop**; raw returns fat (α≈3); **vol-scaled stop REJECTED** — the fixed stop-out rate is regime-FLAT (55/56/57%) while a σ-stop would swing (69/56/46%). The old "[−40,+60]" headline was CIRCULAR (BUG-01). [`DIST-00`](DIST-00-WORKSTREAM-REPORT.md) |
| **News v2 → decisions** (NQ+GC) | ✅ **ANSWERED** | Gold reacts (NFP>CPI); close/enter negligible/no-edge; **assist REJECTED** (belief backwards); content→pattern = **volatility not direction**. [`FAV2-00`](FAV2-00-WORKSTREAM-REPORT.md) |
| **Fat-tail-aware sizing** (#17) | ✅ **RE-EARNED 07-20** | **~0.6–1.2% (quarter-half Kelly), edge-champs only, hard cap** — triangulated 3 ways, now on the REAL champion ledger after BUG-01. ⚠️ CI floor **0.0%** (cannot exclude zero edge); real per-trade tail **$3,029** not $1,600; **5m f\*=0.0%** (no size). **Z3 vol-targeting REJECTED** (halves flip). [`SIZE-00`](SIZE-00-WORKSTREAM-REPORT.md) · [`BUG-01`](BUG-01-sizing-studies-ran-the-wrong-strategy.md) |
| **GC replication** (2026-07-19) | ✅ **COMPLETE** | The verdict **REPLICATES on gold** (all 4 tests null, n=866/99% power) ⇒ no longer an NQ quirk. ⭐ Plus a discovery the battery MISSED: gold moves **INVERSE** to macro surprises (Spearman −0.193, negative 15/16 yrs) — Pearson was blind to it. Real residual at **T+1s = +\$49.90 (t=3.40)** but killed by slippage. [`GC-01`](GC-01-REPLICATION-verdict.md) |
| **Gap-aware fills** (GAP-01/02) | ✅ **SHIPPED 07-20** | Engine now fills a gapped SL/TP at the bar OPEN, not the line (symmetric, `gap_fills` default True, parity 11/11, old golden preserved). Across all **54 champions** P&L is NEUTRAL (**−0.2%**) but **drawdown +9.8%** (NG +148%, GC better on both) — the old model understated **RISK**, not profit. [`GAP-01`](GAP-01-how-the-engine-fills-a-gapped-stop.md) · [`GAP-02`](GAP-02-champion-before-after.md) |

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

**D1 (DIST-02) — ⚠️ FIRST VERSION WAS CIRCULAR; corrected 2026-07-20.** The original text below claimed
the P&L is "bounded [−40,+60] on every TF, 0 of 7,356 trades lose more than the stop." **Those bounds were
the study's own hardcoded defaults** — it never ran the champions at all (see
[`BUG-01`](BUG-01-sizing-studies-ran-the-wrong-strategy.md)). It measured its inputs and reported them as
a discovery.

**The corrected result — the conclusion HOLDS, the magnitudes do not:**

| | Circular version | **Real champion ledger** |
|---|---|---|
| P&L bounds | [−40, +60] | **[−151.4, +125.6]** |
| trades losing MORE than the stop | 0 of 7,356 (0%) | **371 of 9,537 (3.89%)** — the gap/slippage tail |
| worst loss | −40 pts (−$800) | **−151 pts (−$3,029)** |
| EVT shape ξ (80/90/95% thresholds) | — | **−0.366 / −1.555 / −1.978 — all ξ<0 ⇒ BOUNDED** |
| Gaussian check | — | too optimistic at the 1% and 0.5% quantiles |

So the loss tail **is** truncated by the stop — now demonstrated independently by the EVT fit (ξ<0)
rather than asserted from a hardcoded bound — but **3.89% of trades gap straight through it**, and the
real per-trade worst case is **$3,029, nearly double the $1,600 quoted throughout the older reports.**
The qualitative conclusion (the stop truncates the fat-tailed return process, so keep-the-stop and
never-assist are both right) survives. The genuine fat tail lives in **raw returns** → EVT moves there.

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
- **The "priced in" verdict REPLICATES on gold** (2026-07-19) — all four pre-registered tests null on GC at n=866/99% power. It is no longer an NQ-specific result.
- ⭐ **Gold moves INVERSE to macro surprises** — Spearman −0.193 (p<1e-5), negative in **15 of 16 years**, significant in both halves, NULL on the NQ control. Economically textbook (strong data → higher real yields → gold down). A real, durable fact about gold; **not** an entry signal.
- **A macro release prices over ~10–30 seconds, not instantly** — 59.9% done at +1s, 87% by +10s, 95% by +30s. The residual at +1s is statistically real (+$49.90, t=3.40) and economically un-capturable (dies at 5 ticks of slippage).

**Things that DIED under scrutiny:**
- The magnitude "survivor" (+0.187 → −0.018 at full power).
- The 2025 "hawkish-Fed" direction story (−0.43 → −0.004).
- The dynamic stop-loss (dead on 1-min AND 1-second).
- A broad session entry edge (3/5 sessions flip sign).
- Session folklore: the 2–3am equity-premium trade, the post-lunch effect, the London-session GMM edge (flipped with a 1-bar delay).

**FROZEN (pre-registered, unconfirmable now — re-test on future/long data, build nothing):**
- **Silver** (D3): gold-controlled partial −0.258, 4/4 quarters, but raw died under the better ruler; 1-of-36, fluke window.
- **The 22:00/Asia entry cell** (S3): +$364/trade stable both halves, but 1-of-6, n=89, fluke window.

**METHOD lessons banked (they generalize beyond this project):**
- **On fat-tailed instruments, always report RANK correlation alongside Pearson.** The pre-registered
  battery used Pearson and was blind to one of the strongest, most persistent macro reactions in the
  book — it reported "gold: nothing here" about an effect that is significant in 15 of 16 years.
- **Measure at the resolution of the DECISION.** A 1-minute study concluded "100% priced inside the
  release minute" because its "T+0" was the minute's *close* — 60 seconds late. At 1-second resolution
  only 59.9% is done at +1s. A coarse study answers a different question than the one you asked, and it
  does not warn you.

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

## PART 4 — OPEN THREADS & WHAT'S QUEUED  *(refreshed 2026-07-20)*

Everything the workstream set out to answer is **answered**. What remains is follow-through and a handful
of genuinely-blocked threads. Ranked by value.

### A — actionable now (no blocker)
| Item | Why it's worth doing | Cost |
|---|---|---|
| **Champion RE-OPTIMIZATION under gap-aware fills** | The champions were all tuned when gaps were free; per-slot rankings moved ±28% (GAP-02), so the *selection* was made on a distorted scoreboard. NG especially. | server campaign |
| **Re-cut the risk budget** | Drawdown was ~10% optimistic overall, +148% on NG. The sizing rec (Z2/Z4) rests on drawdown, so it should be re-derived on honest DD. | small |
| **Forward-validate gold's inverse macro reaction** | The Spearman −0.193 finding (GC-01) is post-hoc; it deserves a pre-registered forward test on new releases. | small |

### B — blocked on data
| Item | Blocker |
|---|---|
| **Silver forward test** (`study_silver.py`) | SI long history did NOT land with GC — **confirmed absent on the server 2026-07-20**. Same in-house Databento pipeline as GC would unblock it. |
| ~~Asia/22:00 session cell re-test~~ | ✅ **CLOSED 07-20 — FLUKE.** Cross-instrument OOS: 0 of 3 independent equity indices replicate; 22:00 is *below* average on ES/YM/RTY (OOS pool ≈ −$38/trade). [`SESSION-04`](SESSION-04-asia-cell-oos-verdict.md) |

### C — closed / moot / not-ours
| Item | Status |
|---|---|
| #7 D1–D4, Z1–Z4 sizing | ✅ done, re-earned on the real ledger after BUG-01 |
| Z3 vol-targeting OOS on GC | ❌ **moot** — Z3 died on its own temporal split, so there is nothing to OOS-test |
| `test_intracandle_parity` (#15) | pre-existing, another workstream's (default-OFF feature); golden passes |
| The 17 l2 test failures | **stale, not regressions** — the 4h default was deliberately unlocked 07-11 (TESTS-01); handed to the l2/dev owner |

**Nothing is mid-run; the tree is committed and consistent.** The single highest-value next step is the
champion re-optimization under honest fills — it is the only thing that turns the corrected engine into
deployable numbers.

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
