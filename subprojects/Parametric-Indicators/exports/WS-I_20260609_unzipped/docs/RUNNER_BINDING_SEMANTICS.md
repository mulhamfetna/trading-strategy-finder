---
name: ws-i-runner-binding-semantics
description: WS-I open design question — how the indicator confirmation layer (votes + K-rule + retrace-fill) binds to the live engine run. Enumerates the genuinely ambiguous semantic forks the spec never settled, with recommended defaults, for the I.5 team-leader sign-off. Professional version + plain-language ("baby") version.
type: decision-request
status: awaiting-approval (I.5)
created: 2026-06-04
workstream: WS-I
---

# Runner-Binding Semantics — open decisions for I.5

**Context.** Everything up to here is built and parity-locked: the indicator math, the votes, the
K-rule aggregator, the SMC structures, the `wait_bars` debounce, the retrace-fill **resolver**, and
the engine **`entry_resolver` hook** (default off ⇒ verified-engine parity intact, 60 tests green).

The **last** piece — "binding" — is the glue in `runner.py` that, for each box signal, decides
*which indicators confirm/veto, when, and at what price the trade fills*, then calls the engine.
Writing it forces several decisions the frozen spec never pinned down. They're judgment calls that
change real behaviour, so I'm bringing them to you instead of guessing. Each has a **recommended
default** chosen to be unambiguous, causal, and parity-safe.

---

## PROFESSIONAL VERSION

### Q1 — K larger than the number of confirm-capable indicators
`K` = "need ≥ K confirming indicators." If the user enables **fewer** confirm-capable indicators
(mode ∈ {confirm, both}) than `K`, the K-rule can never be met → **zero trades**, silently.
- **Options:** (a) raise `ParamError` to the UI; (b) silently cap `K` at the count; (c) waive.
- **Recommended:** **(a) raise `ParamError`** — "K=3 but only 2 confirm-capable indicators enabled."
  No silent fallback (matches the project rule). The dashboard bounds the K slider to `[1, N_confirm]`.
> aproved on recommedend
### Q2 — Veto-only setups (zero confirm-capable indicators enabled)
If the user enables **only veto-mode** indicators (0 confirm-capable), should a confirm still be
required? With `K≥1` and 0 confirmers, every entry is blocked — almost certainly not intended (they
just wanted to *filter* the box with vetoes).
- **Options:** (a) waive the confirm requirement when `N_confirm_active == 0` (box trades unless
  vetoed); (b) keep `K` (blocks everything).
- **Recommended:** **(a) waive.** `K` only governs confirm-capable indicators; with none enabled the
  box + vol-gate + veto filters decide. (Combined with Q1: the confirm requirement is
  `min(K, N_confirm_active)`, and `K > N_confirm_active` with `N_confirm_active > 0` is the Q1 error.)
> aproved on recommmedned

### Q3 — When is each indicator's *direction* read: frozen at the signal bar, or re-read during the pullback?
With retrace, an entry can wait several 1-min bars for price to pull back. During that wait an
indicator's reading *could* change (e.g., RSI crosses 50). Do we (a) **freeze** each indicator's
directional reading + veto at the **signal bar** (`idx-1`) and only let the **price-level touch** be
path-dependent, or (b) **re-evaluate** readings live on every pullback bar?
- **Recommended:** **(a) freeze at the signal bar.** Deterministic, causal, matches the box (which is
  also read at `idx-1`), and far simpler to log/reproduce. Only the *price reaching each level* is
  path-dependent. (b) is more "realistic" but path-dependent, harder to verify, and needs intrabar
  indicator recompute.
> switch to b -> re-evaluate readings live on every pullback bar

### Q4 — Can a veto appear *during* the armed/pullback window and abort the entry?
Follows from Q3. If readings are frozen (Q3a), a veto can only exist **at the signal bar** (blocks
the entry outright); it cannot newly appear mid-pullback.
- **Recommended:** **veto frozen at the signal bar** (consistent with Q3a). A later "live abort"
  veto is deferred unless you want true intrabar re-evaluation.
> same as Q3 -> veto is live follwing the pullback and not frozen at any point 

### Q5 — Division of labour: gate vs. resolver (no double-counting)
Two mechanisms now exist: the per-bar **composite gate** (`build_gate`) and the **retrace-fill
resolver**. They must not both enforce the confirm-count.
- **Recommended:** **gate = vol-gate ∧ (no active veto at the signal bar)**; **resolver = confirm
  count + retrace levels + timing**. The gate decides *eligibility*; the resolver decides *if/when/at
  what price* the K-th confirm completes and the trade fills. Clean separation, single source of truth
  for the K-rule (the resolver).
> needs further explinations with intective demos and charts for real case studies 

### Q6 — Per-indicator `wait_bars` + `retrace` combine as AND
Decision #5 said an indicator counts as a confirm once **both** its retrace and wait are satisfied.
- **Recommended (mechanical):** an indicator's confirm is live when **(reading favorable, frozen at
  signal bar)** AND **(`wait_bars` debounce satisfied on the decision-TF reading up to the signal
  bar)** AND **(price has touched its retrace level within the window)**. The K-th such indicator's
  level is the fill price (already-built resolver). `retrace=0` ⇒ level = signal close ⇒ touched
  immediately; `wait_bars=0` ⇒ no debounce ⇒ parity.
> aproved unless it intersect with another aproved point

### Parity / safety implications
- All defaults preserve the **all-off ⇒ exact box parity** lock (no enabled indicator ⇒ gate =
  vol-gate, resolver unused).
- All are **causal** (signal-bar-frozen readings; only price-touch is intrabar).
- Q1's error path upholds **no-silent-fallback**.

### What I need from you
Approve Q1–Q6 as recommended, or mark the ones to change. On approval I implement the binding in
`runner.py` (TDD) and the engine layer of I.3 is fully closed.

---

## BABY VERSION (plain language)

Think of the box as the **driver** who wants to make a turn (the trade). The indicators are
**passengers** who say **"yes, go"** (confirm) or **"no, stop"** (veto). We agreed: the car only goes
if **nobody says stop** and **at least `K` passengers say go**. The retrace rule adds: *don't go the
instant the light turns — wait for the price to dip a little first, and you get in at that better
price.* Six small "what if" questions fall out of that, and I want your call:

1. **What if you ask for 3 "go" votes but only 2 passengers can vote "go"?** The car would *never*
   move and you'd see nothing. → **I'll show you an error** ("you asked for 3 but only have 2"),
   not silently do nothing.

2. **What if every passenger you turned on is a "no" voter (nobody can say "go")?** Requiring a "go"
   would freeze the car forever. → **I'll treat it as "go unless someone says stop"** — the vetoes
   just filter the box.

3. **A passenger said "go" at the corner, but while we wait for the price dip they change their
   mind — do we still count their old "go"?** → **I'll lock everyone's vote at the moment of the
   signal** and only wait on the *price* dipping. Simpler and you can always reproduce why a trade
   happened. (We can make votes "live" later if you want.)

4. **Can a passenger yell "stop!" *after* we've started waiting for the dip?** → With votes locked
   (#3), **no** — a "stop" only counts at the signal moment. (Changeable if you want live aborts.)

5. **Two different referees are in the car (the gate and the fill-resolver) — who counts the
   votes?** → **The gate only checks "no stops + good volatility"; the fill-resolver counts the
   "go" votes and picks the entry price.** One counter, no double-counting.

6. **Each passenger can ask to "wait N bars" AND "wait for an X dip" — do both have to happen?** →
   **Yes, both** before that passenger's "go" counts; the trade fills at the dip-price of whichever
   "go" completes the `K`-th vote. (Set both to 0 ⇒ behaves exactly like today.)

**Bottom line:** none of these change anything when indicators are off — the car drives exactly as it
does today. They only matter once you switch indicators on, and they're about avoiding "the car
silently never moves" surprises. Tell me "approved" or point at the numbers you'd do differently.

---

# DEEP ANALYSIS — round 2 (after your inline decisions, 2026-06-04)

Your calls: **Q1 ✅ recommended · Q2 ✅ recommended · Q3 → switch to (b) LIVE re-eval · Q4 → veto
LIVE (never frozen) · Q5 → needs worked examples/charts · Q6 ✅ "unless it intersects another
approved point" (it does — see §A).** The Q3/Q4 switch is the big one and ripples through the design.
Studying it surfaced **one genuine architectural fork I cannot resolve without you (§B)** plus a Q6
reconciliation (§A). §D is the Q5 walkthrough you asked for.

## §A — Q6 now intersects Q3/Q4 (resolved)
Q6's wording said "reading favorable, **frozen at signal bar**." You moved Q3/Q4 to **live**, so that
clause is overridden. **Updated Q6:** an indicator's confirm is live when **(reading favorable —
evaluated LIVE, §B granularity)** AND **(`wait_bars` satisfied)** AND **(price has touched its retrace
level)**; its veto is live likewise. `retrace=0`/`wait=0` ⇒ parity unchanged. No other approved point
conflicts. ✅

## §B — The fork your Q3/Q4 forces: *on what clock is "live" evaluated?*
This is the crux. **Indicators are computed on the decision timeframe (e.g. 4h); the pullback/retrace
is a 1-minute price event** (WS-H rule: decisions on the TF, fills/exits on 1-min). "Re-evaluate the
reading on every pullback bar" is ambiguous because the pullback bars are **1-minute**, but a 4h RSI/
EMA/ADX has **no new value until the 4h bar closes**. Two coherent meanings:

- **B1 — Live at each *closed decision bar* while the entry is armed (recommended).** The signal arms
  an entry; we wait for the retrace level on 1-min *within* the current 4h window using the latest
  *closed* 4h reading. If the level isn't hit by the time the next 4h bar closes and the box still
  holds (no new signal), the entry stays armed and **the indicators are re-read on that new closed 4h
  bar** — a flipped reading drops that confirm; a fresh veto aborts. Fully **causal** (only closed
  bars), deterministic, reproducible. "Live" = updates every decision bar the wait spans.
- **B2 — Live intrabar on every 1-minute bar.** Recompute the indicators on the *forming* 4h bar (or
  on the 1-min series) at each minute. Problems: (1) a partial-4h-bar RSI/ADX is **ill-defined** and
  changes minute-to-minute on incomplete data; (2) it effectively redefines the indicators onto a
  different clock than the box reads them on; (3) heavy recompute. It is *more* "live" but **noisy and
  architecturally inconsistent** with "indicators live on the decision TF."

**Why this matters:** in the *common* case — a retrace that fills **within the same 4h window** —
B1 and B2 differ only in whether the indicator value can wiggle intrabar. B1 holds the just-closed
reading for the duration of that window (the only causally-clean 4h value available); B2 lets it
wiggle on partial data. They diverge meaningfully only when an entry stays armed **across** decision
bars, where **both** re-read — B1 at the clean close, B2 also intrabar.

**My recommendation: B1.** It delivers your intent ("readings & vetoes are live, not frozen forever
at the signal") while staying causal and consistent with the TF/1-min split.

> **DECIDED 2026-06-04: B1** — live re-evaluation per *closed decision bar* while armed; the retrace
> level is tracked on 1-min within each window. All runner-binding semantics are now settled.

## §C — Engine-scope impact of going live (vs the frozen model)
Frozen (my old rec) needed only the **within-window** `entry_resolver` hook already built. **Live
(B1)** additionally requires the engine to **carry an armed-but-unfilled setup across decision bars**
and, on each new bar while armed: (1) re-read indicator votes, (2) re-check veto (abort if vetoed),
(3) re-test the K-rule, (4) keep scanning 1-min for the retrace level, (5) abandon on a new box
signal (supersede). This is a **larger, still parity-safe** engine change (all-off ⇒ no arming ⇒
identity). I'll TDD it with an explicit "armed across N bars, veto appears on bar N → abort" case.

## §D — Q5 worked through (the demos you asked for)
**Setup (all examples):** 4h TF, box signals **LONG** at signal-bar close **S = 20 000**. Enabled:
`RSI` (confirm, retrace 0), `EMA` (confirm, retrace = 20 pts → level 19 980), `ADX` (veto, thr 25).
**K = 2.** Gate = vol-calm ∧ no-veto; Resolver = counts confirms + sets fill price.

**Case 1 — normal fill (the K-th confirm's level).**
```
4h window after the signal (price path on 1-min):
 S=20000 ┤●RSI confirm (level 20000, touched at t0)         gate: vol OK, ADX=30 (no veto) → ELIGIBLE
         │＼                                                 resolver: confirm #1 = RSI @ t0
 19990   ┤  ＼____                                           waiting for 2nd confirm…
 19980   ┤       ＼●EMA confirm (level 19980 touched, t47)   confirm #2 = EMA @ t47  → K=2 MET
         │         ▲ FILL @ 19980, time t47  (K-th = 2nd confirm's level)
```
Gate said "allowed"; the **resolver** picked *when* (t47) and *price* (19 980). One counter.

**Case 2 — veto blocks at the gate (no entry at all).**
```
ADX = 18 (< 25) at the signal bar  →  veto active  →  gate = ELIGIBLE? NO.
Resolver never runs. No arming, no fill. (Under your Q4-live, a veto can also appear LATER and abort
an already-armed entry — see Case 4.)
```

**Case 3 — partial confirm, never fills → superseded.**
```
 S=20000 ┤●RSI confirm (#1)            price never dips to 19 980 before the next box signal
 19992   ┤＼__/＼__/                    confirm count stuck at 1 < K=2
         │  (next 4h bar emits a NEW long signal) → old armed entry SUPERSEDED, logged "unfilled"
```

**Case 4 — LIVE abort (this is what Q3/Q4 buys you; needs §B).**
```
bar n   (signal): RSI bull, EMA bull, ADX 30 → armed, waiting for 19 980
bar n+1 (closed, box holds): re-read → ADX drops to 17  →  VETO now active  →  ABORT armed entry
                              (frozen model would have ignored this and still filled — your call fixes that)
```

**Why gate vs resolver are split:** the **gate** answers *"is this signal allowed to participate at
all?"* (volatility OK, not vetoed) — a fast per-bar boolean. The **resolver** answers *"given it's
allowed, do ≥ K confirms actually line up as price pulls back, and at what price?"* — the path/price
logic. If both counted confirms we'd double-count and the fill price would be ambiguous. Splitting
them = **one source of truth for the K-rule (resolver)**, gate stays a cheap eligibility filter.

## §E — Updated decisions
| Q | Decision |
|---|---|
| Q1 | ✅ raise `ParamError` when `K > N_confirm_active` |
| Q2 | ✅ waive confirm requirement when `N_confirm_active == 0` |
| Q3 | **LIVE** re-evaluation — **B1 (per closed decision bar) recommended; B2 (intrabar) open — need your pick** |
| Q4 | **LIVE veto** — aborts an armed entry the moment a veto appears (same clock as Q3) |
| Q5 | Split kept: gate = eligibility (vol ∧ no-veto), resolver = K-count + fill price (see §D) |
| Q6 | ✅ with §A fix — readings/vetoes are **live**, not frozen; `wait`+`retrace` still AND |

**Single open item:** **§B — B1 vs B2** (the clock for "live"). Pick B1 (recommended) or B2 and I
implement the live binding in `runner.py` + the across-bars engine arming (§C), TDD, parity-locked.
