# Intra-Candle Entry for Vetoed Signals — Progress & Decisions Worksheet

> 🟡 **BRAINSTORMING IN PROGRESS.** This is a *fill-in worksheet*, not a spec. Read each decision, tick an option
> (or write your own in the NOTES line), and hand it back — then I turn it into a formal spec → plan → build.
> Every decision has a 👶 **baby version** (plain language, no jargon).

---

## 0. The idea, in one baby paragraph 👶

Right now, when the strategy sees a trade setup ("box signal") but one of its indicator "judges" says **"no, don't
take it"** (a **veto**), the trade is **thrown away forever**. Your idea: instead of throwing it away, **keep it on
a sticky note** and **keep watching for the next few hours (inside that same 4-hour candle)**. The moment the
judges change their mind and say "ok, now it's fine," **jump in mid-candle** instead of waiting for the next
4-hour boundary. So vetoed setups get a **second chance** to become trades, entered *inside* the candle.

---

## 1. How it works today vs. the change

**Today:** a signal is checked **once**, at the 4-hour candle's close. Vetoed → dropped → gone.

**Proposed:** a vetoed signal is checked **again and again** on every 1-minute bar inside the candle, and enters
the first time it fully qualifies.

```mermaid
flowchart TD
  A["4h box signal fires (long/short)"] --> B{"indicators veto it?"}
  B -->|"no"| C["enter normally (today's behaviour)"]
  B -->|"yes — VETOED"] --> D["👉 NEW: keep it ARMED on a sticky note"]
  D --> E["walk each 1-min bar inside the candle"]
  E --> F{"full gate open?<br/>(no veto AND ≥K confirms)"}
  F -->|"no"| G{"window used up?<br/>(N bars, or new signal supersedes)"}
  G -->|"no"| E
  G -->|"yes"| H["EXPIRE — never entered"]
  F -->|"yes"| I["ENTER mid-candle at this 1-min bar"]
  classDef new fill:#e7f3ff,stroke:#3366cc;
  class D,E,F,I new;
```

**Good news (feasibility):** the engine **already** computes every indicator on the 1-minute timeline — it just
*samples* the result once per 4-hour bar today. And the exact engine **already has an "arm a signal and walk the
1-min bars to find a fill" mechanism** (the retrace/wait `entry_resolver`). This feature largely **reuses** both,
so it's well within reach.

---

## 2. Already settled ✅ (you decided these)

| # | Decision | Your answer |
|---|---|---|
| **D0** | **On/off control (disableable)** | ✅ **Disableable via a dashboard checkbox placed directly *under the time-cap* control**; **default OFF**. Off ⇒ byte-identical champion (golden-safe). Also a plain engine/param flag so the optimizer can toggle it. |
| **D1** | **What triggers entry** for an armed vetoed signal | ✅ **Full gate**: enter at the first 1-min bar where **no indicator vetoes AND ≥K confirms** — the exact champion gate, just checked intra-candle. |
| **D2** | **How long it waits** | ✅ **Tunable max-wait `N` 1-min bars** (also ends early if a new box signal supersedes it). `N` will be optimizer-searchable later. |

---

## 2.5 Prior-art research — what the evidence says (deep-research pass, 2026-07-03) 🔬

106 agents, 23 sources, 88 claims, 20 confirmed / 5 refuted. **The rigorous evidence is mixed-to-cautionary, and
some of it is on our exact instrument (MNQ/NQ):**

👶 **Baby version:** other people have tried "wait, then jump in" entries. The careful studies say: **naive
"wait for a pullback then enter" often backfires** (on micro-Nasdaq it was a disaster — you wait, the move leaves
without you, 19% win rate). A plain **delay** even wrecked a good signal. BUT the versions that **worked** waited
for **several conditions to line up at once** (exactly our "no veto AND enough confirms" rule), and **re-taking
signals you first rejected** *can* help — mostly by making your losers smaller. Bloggers' rosy "confirmation =
higher win rate" claims mostly **failed fact-checking.**

| Evidence | Verdict for us |
|---|---|
| Pullback/retest entry on **MNQ**: 80.7% stop-out, **19.3% win rate** | ❌ **Don't add a pullback wait** (→ D4 = enter immediately) |
| A **one-bar delay** flipped a good signal from +profit to −loss; intrabar-expansion signals die if you wait | ⚠️ **The delay itself is the risk** → prefer **short** wait windows, measure the decay (→ D7 = sweep N) |
| Validated winners used **multi-condition armed entry** (≥3 conditions) | ✅ Our **full gate** (`¬veto ∧ ≥K confirms`) is the *good* flavor (→ D1 confirmed) |
| Re-admitting rejected signals: win 51.4%→54.5%, PnL 2×, mainly **smaller losers**; scales with move size | ✅ Cautious support for the whole idea — **watch loss size, not just win rate** |
| Blog claims "confirmation greatly improves win rate / 62%-2.8R" | ❌ **Refuted** — ignore |

**Bottom line:** worth a **measured test with tempered expectations** — enter immediately (no pullback), keep the
wait **short**, and **prove it clears the 57.5% breakeven** before trusting it. This is exactly why we test on the
champion first.

---

## 3. Decisions I still need from you 📝 (now evidence-informed)

### D3 — When the gate opens but we're already in a trade 🟥 (the big one)
👶 **Baby version:** we can only hold **one** trade at a time. Your vetoed signal might get its green light *while
another trade is still running*. We can't take two at once — so do we **wait our turn**, or **give up**?

- [ ] **A — Keep waiting until flat** *(my recommendation)* — stay on the sticky note; if the light is green but
  we're busy, skip and keep checking; enter the first bar that's green **and** we're free (within the N-bar window).
  → most rescued trades.
- [ ] **B — Give up if blocked** — if the first green light happens while we're busy, throw the signal away. →
  simplest, fewer/earlier trades only.
- [ ] **C — Flip/replace the open trade** — close the running trade and take the vetoed one instead. → aggressive,
  changes existing trades' behaviour (riskier, more entangled).

**❓ Also tell me what "in a trade" should mean:** (i) any prior normal trade, (ii) another armed vetoed trade,
(iii) both.

> **📝 YOUR DECISION (A/B/C):** `__________`   **"in a trade" = (i/ii/iii):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D4 — The entry price on the qualifying bar
👶 **Baby version:** once the light turns green on a 1-minute bar, do we buy **right there** at that bar's price,
or do we still wait for a small pullback first (the existing "retrace" feature)?

- [ ] **A — Enter immediately** at the qualifying 1-min bar's close *(my recommendation — **now evidence-backed**:
  pullback/retest entries were catastrophic on MNQ (19% win). Matches the champion's retrace=0 and is simplest)*.
- [ ] **B — Apply retrace on top** — after the gate opens, still wait for the configured pullback before filling
  (stacks the two features; only matters if retrace > 0).

> **📝 YOUR DECISION (A/B):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D5 — Which dropped signals get this second chance (scope)
👶 **Baby version:** signals get dropped for **two** different reasons — an indicator **veto**, or the **volatility
gate**. You said "vetoed." Should this apply *only* to veto-dropped signals, or also to volatility-gate-dropped
ones?

- [ ] **A — Vetoed only** *(my recommendation — matches what you said; the volatility gate is a per-candle
  "market too calm/wild" filter that doesn't change inside the candle, so re-checking it wouldn't help)*.
- [ ] **B — Vetoed + volatility-gated** — also rescue vol-gated signals (bigger pool, but the vol gate is basically
  fixed for the candle, so this mostly wouldn't fire — lower value).

> **📝 YOUR DECISION (A/B):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D6 — Direction of the rescued trade
👶 **Baby version:** the original signal said long or short. When we finally enter, do we take **that same
direction**, or could it flip?

- [ ] **A — Keep the original box direction** *(my recommendation — you said "keep the signal")*.
- [ ] **B — Allow it to flip** if the intra-candle indicators point the other way (more complex; overlaps the
  existing flip feature).

> **📝 YOUR DECISION (A/B):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D7 — Default wait window `N` for the first champion study
👶 **Baby version:** before we let the optimizer tune `N`, we test on the current champion with a fixed value.
How long a default? (240 one-minute bars = one full 4-hour candle.)

- [ ] **A — Don't pick one; SWEEP `N ∈ {30, 60, 120, 240}`** in the champion study *(my **updated** recommendation
  — the evidence shows a delay can let the move exhaust, so short N may win; the sweep shows the decay curve
  directly rather than guessing)*.
- [ ] **B — 240 (one full 4h candle)**   · [ ] **C — 60 (first hour)**   · [ ] **D — other:** `______`

> **📝 YOUR DECISION (A/B/C/D):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D8 — How many signals can be "armed" at once
👶 **Baby version:** if a *second* box signal fires while the first is still waiting on its sticky note, do we
track both, or does the new one replace the old?

- [ ] **A — One at a time; newest replaces** *(my recommendation — matches D2's "superseded" rule and the existing
  engine behaviour)*.
- [ ] **B — Allow a queue of several armed signals** (more complex; rarely needed).

> **📝 YOUR DECISION (A/B):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

### D9 — Roll-out scope (this is a *plan* decision, not a mechanic)
👶 **Baby version:** we do this in two steps: **(1)** measure the effect on the **current champion** first, then
**(2)** let the **optimizer** use it and re-tune. Step 1 is easy (the exact engine already has the arming
machinery). Step 2 has a **caveat**: the fast optimizer engine currently enters only at 4-hour boundaries for
speed, so teaching it intra-candle entries is **more work** and may be slower.

- [ ] **A — Champion study first, decide on the optimizer after seeing results** *(my strong recommendation —
  cheap, and it tells us if the idea is even worth the heavier optimizer work)*.
- [ ] **B — Build both up front** (optimizer included) before seeing champion results (more work, higher risk).

> **📝 YOUR DECISION (A/B):** `__________`
> **📝 NOTES:** `______________________________________________________________`

---

## 4. What happens after you fill this in

1. I turn your answers into a **formal design spec** (`docs/superpowers/specs/…-intracandle-veto-entry-design.md`),
   you review it.
2. Then a **step-by-step implementation plan** (TDD, off the golden path, golden 6/6 must stay green).
3. Then build **Phase 1**: measure the effect on the current champion ($142,203 / 214 — and the $153,321 wsh6cold
   champion) with the feature toggled on, default-off so nothing changes until enabled.
4. Report the effect → then decide on **Phase 2** (optimizer), per D9.

## 5. The guarantees that hold no matter what you choose
- **Causal — no look-ahead:** each 1-min re-check uses only bars up to that minute.
- **Default OFF ⇒ byte-identical champion:** the golden parity gate (6 timeframes) must stay green.
- **Additive & off the production path** until you approve promoting it.

---

*Hand this back with the 📝 lines filled (even just the letters, e.g. "D3=A(i), D4=A, D5=A, D6=A, D7=A, D8=A,
D9=A") and I'll write the spec.*
