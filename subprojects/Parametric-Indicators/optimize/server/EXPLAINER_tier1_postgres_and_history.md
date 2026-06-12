# Explainer (baby + professional) — Tier 1 (Postgres + storage URL) and what to do with the old trial history

**Date:** 2026-06-12 · purpose: explain decisions **#2** (start Tier 1) and **#3** (migrate history vs fresh start)
from `ACTION_PLAN_scaling_tiers.md` §6, in plain language, so you can choose with full understanding.
**Nothing here changes any code — it's an explainer.**

---

## Part A — Decision #2: "start Tier 1 (centralize the storage URL + make it Postgres-ready)"

### A.1 First, what is "the storage" and why did it break?

When the optimizer runs, it tries thousands of parameter combinations ("trials"). For **each** trial it
writes down: *what knobs it set* and *what score it got*. All ~30 parallel workers need to share this
notebook so they don't repeat each other and so the search can resume. That shared notebook is a
**database**, and today it is a **SQLite file** on disk (`wsh_<tf>.db`).

> **Baby.** Picture 30 people filling one shared notebook with their results. SQLite's rule is: **only one
> pen exists.** To write, you must hold the pen. With 30 people grabbing for one pen, most are waiting. If
> someone waits too long, they get frustrated and **walk out** (the worker process dies — that was the
> `database is locked` incident). That's why the 4h and 1h studies finished short.

**Professional.** SQLite serializes writes behind a single file-level lock. Under ~30 concurrent Optuna
workers, lock-wait exceeded the timeout → `database is locked` → (pre-Tier-0) the worker crashed. Tier 0
softened this (don't crash, wait longer, one notebook per timeframe). Tier 1 **removes the single-pen rule
entirely.**

### A.2 What PostgreSQL is, and why it fixes it

**PostgreSQL ("Postgres")** is not a file — it's a small **database *server*** (a running program) that
manages the data for you. Its key trick is **MVCC** (multi-version concurrency control): **many writers can
write at the same time** without blocking each other.

> **Baby.** Instead of one shared notebook with one pen, Postgres is an **office with a clerk and many
> windows**. All 30 people walk up to their own window and hand in their results **at the same time**; the
> clerk files them all. Nobody waits for a pen, nobody walks out. Same results, no traffic jam.

**Professional.** Postgres is a **first-class Optuna backend** — Optuna already supports it; you don't
rewrite anything in the search/sampler logic. You only change **where** the trials are stored. MVCC means
the exact failure (write-lock contention) **cannot happen** by design.

### A.3 What "centralize the storage URL" means (and why it comes first)

The "storage URL" is just the **address of the notebook**, a short string like
`sqlite:///optimize/studies/wsh_4h.db`. Right now that address is **typed into three different files**:

```
optimizer.py        (the worker that WRITES trials)
report_wsi.py       (the reader that BUILDS reports)
remote_wsi.sh       (the launcher + counts + pull on the server)
```

If you change the database, you must edit **all three** and keep them identical, or things silently read
the wrong place.

> **Baby.** The notebook's address is written on **three separate sticky notes**. If you move the notebook
> and forget one sticky note, that person keeps walking to the empty old spot. "Centralizing" = write the
> address **once on a whiteboard** that all three read. Then moving the notebook = change **one** word on
> the whiteboard.

**Professional.** We add one helper (e.g. `storage_url(tf)`) that returns
`os.environ["WSH_STORAGE_URL"]` **if set**, otherwise the current per-TF SQLite path. All three callers use
it. Switching SQLite → Postgres becomes a **single environment variable**, not a 3-file edit. This is
**1.2 before 1.1** on purpose: centralize the address first, *then* the swap is trivial and low-risk.

### A.4 What actually changes vs what stays exactly the same

| Stays identical (guaranteed) | Changes |
|------------------------------|---------|
| All trade math / engine / indicators (parity-locked) | Where trials are stored (a file → a server) |
| The search algorithm (NSGA-III), objectives, constraints | The "address" lives in one place, not three |
| Behaviour when `WSH_STORAGE_URL` is **unset** (still per-TF SQLite) | A new opt-in Postgres path when the env var **is** set |

> **The safety guarantee:** with the env var **unset**, the system is **byte-identical to today** — same
> SQLite files, same parity (`$7,735 / $3,670 / n=66`), same tests. Postgres is **opt-in**. So Tier 1's
> local half is almost zero-risk: we add a switch and prove "switch off = nothing changed."

### A.5 Why do Tier 1 locally now, while SSH is down?

Tier 1's **code** (the helper + the 3 refactors + tests) needs **no server** — it's pure local Python/bash.
Only the actual Postgres *server* gets stood up later (Phase D, on the box). So we lose no time: implement
and prove the switch locally now; flip it on during the deploy once SSH is back.

---

## Part B — Decision #3: what to do with the ~25,000 trials already done

When we move the notebook to Postgres, the old SQLite notebooks still hold **all the work already done** —
roughly **25,000 completed trials** across the 6 timeframes, including the winning Pareto fronts and the
champion parameter sets. Two honest choices:

### Option A — **Migrate** the history into Postgres (`optuna.copy_study`)

Copy each old SQLite study into the new Postgres DB, then keep going there.

> **Baby.** Photocopy every page of the old notebooks into the new office's filing cabinet, then keep
> adding new pages there. Nothing is lost; the search **continues from where it stopped**.

| 👍 Pros | 👎 Cons |
|---------|---------|
| **Continuous history** — one DB has all old + new trials | A **migration step** that must be done carefully |
| The search **keeps its head start**: NSGA-III evolves from the 25k existing trials instead of restarting from random | Study names + objective directions + constraints must match **exactly** or the copy is rejected/subtly wrong |
| **Top-ups continue**: 4h (≈2,146) and 1h (≈2,653) resume *toward* 5,000 instead of starting over | Bigger cutover surface = more to verify during the risky moment |
| Analysis/reporting sees everything in one place | If a copy is imperfect, it could blur the clean record |

**When A is right:** you care about **continuing** the under-sampled 4h/1h (and keeping the evolutionary
momentum of the search).

### Option B — **Fresh start** on Postgres, keep SQLite read-only

Start a brand-new study prefix on Postgres (e.g. `wsh5_<tf>`); leave the old SQLite files as a frozen,
read-only record of past results.

> **Baby.** Leave the old notebooks on the shelf exactly as they are (you can still read them), and start
> **fresh notebooks** in the new office. Cleanest possible move — you can't accidentally smudge the old
> ones.

| 👍 Pros | 👎 Cons |
|---------|---------|
| **Lowest risk** — no migration code, **impossible** to corrupt old data | New studies start at **zero trials** — the search restarts from random |
| Clean separation; old fronts stay exactly as pulled (immutable) | The 4h/1h **can't "continue"** — you'd re-sweep them from scratch |
| Simplest cutover (just point at the new empty DB) | Results split across **two stores** (old SQLite + new PG) → cross-comparison needs care |

**When B is right:** you value a **clean, risk-free cutover** and are fine re-running searches fresh (or the
old champions are already "good enough" and you only want the *infrastructure* fixed).

### B.1 A sensible middle path (recommended default)

- **Migrate only the studies you actually want to continue** (the under-sampled **4h** and **1h**) via
  `copy_study`, and **start the rest fresh** (or leave the already-at-target 5m/2h/15m/2m on read-only SQLite
  as the record). This gets the continuation where it matters while keeping the migration tiny and low-risk.
- If even that feels risky: **Option B (fresh prefix) is the safe default** — we lose the head start but
  gain a bulletproof cutover, and we can always `copy_study` later once the Postgres path is proven.

> **My recommendation:** **start with Option B (fresh `wsh5` prefix on Postgres)** to make the
> infrastructure cutover bulletproof, **then** optionally `copy_study` the 4h/1h history in as a *second,
> separately-verified* step. That way the risky infra change and the fiddly data migration never happen at
> the same moment — each is provable on its own. (You decide; this is your call.)

### B.2 What this decision does NOT affect
- It does **not** change any trade math, champion validity, or the dashboard — those are independent.
- The **already-pulled results** (`WS-I_RESULTS.md`, Pareto CSVs/PNGs, champion recipes) are safe either way;
  they're files on disk, not in the optimizer DB.

---

## Part C — So, concretely, what I'd do on your "go"

1. **Tier 1 local (Decision #2):** add the `storage_url()` helper, refactor the 3 callers, add tests proving
   *env-unset = identical*, document the Postgres URL form. One commit + one UPDATE doc. **Risk: low.**
2. **History (Decision #3):** I'll wire the Postgres path to honour whichever you pick — **(B) fresh prefix**
   (default, safest) or **(A) copy_study** the 4h/1h. The actual Postgres server + copy happen in Phase D on
   the box (after SSH is back), each gated and verified.

**Your two answers needed:**
- **#2** — green-light Tier 1 local implementation now? (recommended: yes; it's low-risk and needs no server)
- **#3** — **B (fresh, safest)**, **A (migrate everything)**, or **middle (migrate only 4h/1h)**?
