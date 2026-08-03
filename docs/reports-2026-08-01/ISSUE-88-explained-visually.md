---
name: issue-88-explained-visually
description: The MAP-Elites archive problem explained in plain words and pictures — why 1,494 shelves and 400 items means "keep the first" instead of "keep the best", and how binning fixes it.
type: explainer
date: 2026-08-02
issue: 88
---

# #88 — the display cabinet with too many shelves

*Plain-language, picture-first. Arabic mirror: `ISSUE-88-explained-visually.ar.md`*

---

## 1. What MAP-Elites is trying to do

Imagine a **display cabinet**. Every shelf is reserved for one *kind* of strategy.

A shelf is chosen by two things:

- **how risky** the strategy is (its worst drawdown), and
- **how many indicators** it uses.

The rule is simple: **each shelf holds the single best strategy of that kind.**

```mermaid
flowchart LR
    T["a new strategy<br/>is tested"] --> W{"which shelf<br/>does it belong on?"}
    W --> S["shelf =<br/>(risk level, how many indicators)"]
    S --> C{"is that shelf<br/>empty?"}
    C -->|"EMPTY"| P1["put it on the shelf<br/><i>anything is accepted</i>"]
    C -->|"OCCUPIED"| C2{"is the newcomer<br/>BETTER?"}
    C2 -->|"yes"| P2["replace the old one<br/><b>this is the point of the method</b>"]
    C2 -->|"no"| P3["throw the newcomer away"]
    style P1 fill:#e67e22,color:#fff
    style P2 fill:#27ae60,color:#fff
```

**The green box is the whole idea.** It is where "the best" gets chosen. The orange box is just filling
an empty space — no choosing happens there.

---

## 2. The problem, in one picture

The cabinet has **9 risk rows**. The number of *columns* is the number of indicators a strategy can use.

When this was designed there were **18 indicators**, so ~19 columns:

| | 0 ind | 1 | 2 | 3 | … | 18 |
|---|---|---|---|---|---|---|
| **risk 0** | 🟩 | 🟩 | 🟩 | 🟩 | … | 🟩 |
| **risk 1** | 🟩 | 🟩 | 🟩 | 🟩 | … | 🟩 |
| … | … | … | … | … | … | … |

**171 shelves. 400 strategies get tested.** Every shelf gets visited about **2–3 times**, so the
"is the newcomer better?" question actually gets asked.

Today there are **165 indicators**, so **166 columns**:

| | 0 ind | 1 | 2 | … | 82 | … | 165 |
|---|---|---|---|---|---|---|---|
| **risk 0** | ⬜ | ⬜ | ⬜ | … | 🟩 | … | ⬜ |
| **risk 1** | ⬜ | ⬜ | ⬜ | … | 🟩 | … | ⬜ |
| … | … | … | … | … | … | … | … |

**1,494 shelves. Still 400 strategies.**

```mermaid
xychart-beta
    title "How many times each shelf gets visited"
    x-axis ["designed (18 ind)", "today (165 ind)", "after the fix"]
    y-axis "visits per shelf" 0 --> 6
    bar [2.3, 0.27, 4.9]
```

---

## 3. Why that breaks the method

With **less than one visit per shelf**, almost every shelf is filled by **the first strategy that
happens to land on it** — and nothing ever comes back to challenge it.

```mermaid
flowchart TD
    A["1,494 shelves<br/>400 strategies"] --> B["most shelves:<br/><b>never visited at all</b>"]
    A --> C["nearly all the rest:<br/><b>visited exactly once</b>"]
    C --> D["the shelf was empty<br/>⇒ accept whatever arrived"]
    D --> E["<b>'keep the BEST'<br/>became<br/>'keep the FIRST'</b>"]
    style B fill:#95a5a6,color:#fff
    style E fill:#c0392b,color:#fff
```

**This is the damage:** the cabinet still *looks* full and well-organised. It is still presented as
*"the best low-risk strategy, the best few-indicator strategy…"*. But nothing was ever compared to
anything. It became **a collection of first arrivals wearing the label of a collection of champions.**

---

## 4. Why so many columns are useless anyway

Look at what the columns actually distinguish.

**The strategies you actually deploy use 3 to 10 indicators.**

```mermaid
flowchart LR
    subgraph useful["columns that matter"]
    A["3 ind"] --- B["5 ind"] --- C["7 ind"] --- D["10 ind"]
    end
    subgraph waste["columns that are their own shelf for no reason"]
    E["61 ind"] --- F["62 ind"] --- G["63 ind"] --- H["…"]
    end
    style useful fill:#27ae60,color:#fff
    style waste fill:#95a5a6,color:#fff
```

**Is a 61-indicator strategy a meaningfully different *kind* of thing from a 62-indicator one?** No. But
the cabinet gives each its own shelf, and each shelf steals visits from the ones that matter.

---

## 5. The fix — group the columns

Instead of one column per exact count, use **groups**, fine where it matters and coarse where it does
not:

| group | 0 | 1–2 | 3–4 | 5–7 | 8–10 | 11–15 | 16–25 | 26–50 | 51+ |
|---|---|---|---|---|---|---|---|---|---|
| **why** | none | very few | **champion zone** | **champion zone** | **champion zone** | many | lots | very many | crowd |

**9 columns instead of 166.**

```mermaid
flowchart TD
    B["<b>BEFORE</b><br/>9 risk rows × 166 columns<br/><b>= 1,494 shelves</b><br/>400 visitors<br/><b>0.27 visits each</b>"] --> R["group the columns:<br/>fine at 3–10 where champions live,<br/>coarse above"]
    R --> A["<b>AFTER</b><br/>9 risk rows × 9 columns<br/><b>= 81 shelves</b><br/>400 visitors<br/><b>4.9 visits each</b>"]
    style B fill:#c0392b,color:#fff
    style A fill:#27ae60,color:#fff
```

With ~5 visits per shelf, the **"is the newcomer better?"** question gets asked again and again — which
is the entire reason the method exists.

---

## 6. It must not break again next time the library grows

The library went **15 → 18 → 143 → 165**. That growth is what broke this in the first place.

```mermaid
flowchart LR
    O["<b>OLD</b><br/>columns = number of indicators"] --> OG["library grows"] --> OB["shelves grow with it<br/><b>breaks silently</b>"]
    N["<b>NEW</b><br/>columns = fixed groups<br/>(…, 26–50, 51+)"] --> NG["library grows"] --> NB["shelves stay at 9<br/><b>nothing changes</b>"]
    style OB fill:#c0392b,color:#fff
    style NB fill:#27ae60,color:#fff
```

The last group is **"51 or more"**, a catch-all. Whether the library holds 165 indicators or 500, the
cabinet still has 9 columns.

---

## 7. How I will prove it worked — not just argue it

Counting shelves is arithmetic. **The real test is whether choosing actually happens.**

So the archive will count two different events:

```mermaid
flowchart LR
    E1["<b>first-fill</b><br/>shelf was empty,<br/>anything accepted"] --> M1["no choosing happened"]
    E2["<b>improvement</b><br/>shelf was occupied,<br/>newcomer was BETTER"] --> M2["<b>choosing happened</b>"]
    style E1 fill:#e67e22,color:#fff
    style E2 fill:#27ae60,color:#fff
```

| | before the fix | after the fix — the prediction |
|---|---|---|
| first-fills | almost everything | far fewer |
| **improvements** | **almost none** | **a healthy share** |

**If the improvement count does not rise, the fix did not work** — and I will report that instead of
pointing at the shelf arithmetic and declaring victory. This is written down before the run, so it
cannot be reinterpreted afterwards.

---

## 8. What this does *not* claim

```mermaid
flowchart TD
    F["#88 fixes the archive shape"] --> Y["✅ the method can choose again"]
    F --> N1["❌ does NOT make past MAP-Elites results valid<br/><i>those came from the broken version</i>"]
    F --> N2["❌ does NOT claim MAP-Elites beats the normal search"]
    N1 --> S["that is <b>#90</b> — re-validation"]
    style Y fill:#27ae60,color:#fff
    style N1 fill:#95a5a6,color:#fff
    style N2 fill:#95a5a6,color:#fff
```

Every MAP-Elites result accepted before this was produced by the version that kept first arrivals. Those
results are **not wrong — they are unvalidated**, which is a different and more awkward status, and it
is tracked separately.

---

## 9. The whole thing in one line

> **A cabinet with more shelves than items stops being a collection of the best and becomes a collection
> of the first — while looking exactly the same from the outside.**

---

## 10. What happened when it was measured (2026-08-03)

**The test in §7 was the wrong test, and it took two failures to see it.**

| round | what was counted | result |
|---|---|---|
| 1 | improvements ≥ 2× | **failed** — 1 of 8 seeds |
| 2 | improvements ≥ 2×, 10× the budget | **failed, and inverted** — the broken cabinet scored **2.5× MORE** |
| 3 | **how good the strategies on the shelves actually are** | **passed — 8 of 8** |

Why round 2 inverted, in one line:

> **A cabinet of junk is easy to improve on. A cabinet of genuinely good items is hard to improve on.**

So counting improvements *rewards* the broken cabinet. The counter went up as the thing got worse — not
a weak measurement, a wrong one.

### The number that settles it

The run is *handed* a strategy before it starts — the current champion, worth **$23,328**.

| | best strategy found in the part of the cabinet that matters |
|---|---|
| **broken cabinet** | **exactly the champion it started with, in 5 of 8 runs** |
| **fixed cabinet** | beat it in **8 of 8**, by **+23%** |

> **The broken cabinet spent 4,000 tries and handed back the strategy it was given** — while looking
> busy the whole time: 260 shelves filled, 299 "improvements" logged.

### Two corrections to this page

- **"4.9 visits per shelf" was optimistic.** It assumed every try reaches a shelf. **68% never do** —
  they lose money, barely trade, or drop too hard. The real figure is **1.46**. Still above the 1.0 that
  matters (the old cabinet achieved **0.08**), but the honest number is lower than the one drawn above.
- **§7's promise was kept, twice.** The criterion failed and was reported as failed both times. The
  third criterion was written down and committed *before* its run, so it could not be chosen for
  passing.

Full detail: `../reports-2026-08-03/ISSUE-88-FINAL-round3.md`
