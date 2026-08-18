# System analysis — do we need an ORM, and is the Postgres/SQLite split still right?

**Date:** 2026-07-29 · Questions raised after the "the studies are gone" error, which was caused by
me searching one backend while the data sat in the other.

---

## Answers up front

| question | answer |
|---|---|
| Do we have an ORM? | **Yes, indirectly.** Optuna is built on SQLAlchemy 2.0.49, already installed. |
| Should we add our own ORM? | **No.** It would wrap a schema we don't own and solve nothing we have. |
| Is the SQLite default still efficient? | **Yes — for how we run today (one study at a time) it is strictly better than Postgres.** |
| Should we move to an enterprise DB / load balancer? | **No.** There is no concurrent request load to balance. It would add failure modes and zero throughput. |
| Is anything actually wrong? | **Yes — one thing: which backend is in use is invisible.** That is what bit us, and it is cheap to fix. |

---

## 1. Do we have an ORM, and would one help?

### What is actually there

**We do not have our own database.** We have exactly one relational store, and it belongs to Optuna —
its trial history. Optuna talks to it through **SQLAlchemy**, which is an ORM plus a SQL toolkit. So an
ORM is already in the stack, already a dependency, and already mapping every table we have.

Our own code touches SQL directly in **six** places, and all of them are tiny metadata reads:

| file | what it does |
|---|---|
| `optimize/optimizer.py:125` | "does this study already exist in this file?" |
| `optimize/report_wsi.py:53` | list study names |
| `optimize/trial_count.py:39` | count trials |
| `optimize/migrate_to_pg.py:34` | one-off SQLite → Postgres migration |
| `optimize/contention_smoke.py:55` | a deliberate lock-contention test |
| `optimize/optimizer.py:682` | study bookkeeping |

Every one is a one-line `SELECT`. There is no schema of ours to map, no relationships, no business
objects. **The heavy data — 486,969 price bars — never goes near a database.** It lives in CSV files and
is loaded into pandas/numpy arrays. An ORM has nothing to offer numpy.

### Why adding one would be a net negative

1. **It would map somebody else's schema.** `studies` and `trials` are Optuna's *internal* tables. Writing
   our own model classes over them means we own a copy of a schema we don't control, which breaks
   silently the first time Optuna changes it.
2. **We would have two mappings of the same tables** — Optuna's and ours — that can disagree.
3. **It replaces `SELECT study_name FROM studies` with a session lifecycle, a model class and a migration
   story.** That is more code and more failure modes to express less.
4. **It buys none of the usual ORM wins.** No complex joins, no schema evolution of ours, no
   multi-database portability we need.

### ⚠️ The real (smaller) issue those six call sites do have

They hardcode Optuna's internal table names. **That is genuine coupling to a private schema** — an
Optuna upgrade could break them with no warning.

The obvious fix, "use Optuna's public API instead", is **not available**: `get_all_study_summaries()` is
known to hang on this project once there are ~100+ studies, which is precisely why raw SQL was used.

**So the recommendation is not an ORM — it is containment:** move those `SELECT`s into `optimize/storage.py`
so there is *one* place that knows Optuna's table names, with a comment recording that we bypass the
public API deliberately because it hangs. That is a ~30-line change that removes a real risk. An ORM is a
large change that removes none.

---

## 2. Is the SQLite/Postgres arrangement still right?

### First, a correction of framing

**SQLite is not a "fallback" from Postgres — it is the default, and Postgres is the opt-in.**

```
storage_url()  =  os.environ["WSH_STORAGE_URL"]        if set   →  Postgres
                  else  f"sqlite:///{per_tf_db_path}"           →  SQLite   ← default
```

Nothing in the campaign scripts sets `WSH_STORAGE_URL`, so **every study we have run recently is
SQLite**. (That is exactly why I looked in Postgres, found nothing, and wrongly announced the July
studies were lost.)

### Why the design looks the way it does — both parts were earned

**The per-timeframe SQLite split** came from a real incident (`INCIDENT_wsh4_sqlite_contention.md`,
2026-06-11): ~30 worker processes hammering **one shared** `wsh.db`. SQLite serialises writes behind a
single database-level lock; lock-wait blew past the 5-second timeout, `study.optimize()` was called
without `catch=`, and **workers died mid-run**. Two timeframes finished under-sampled (4h reached 2,146
trials of 5,000; 1h reached 2,653). Splitting into `wsh_<tf>[_<INST>].db` turned one lock into six.

**Postgres** was added for the same pressure, and needed its own tuning:

> Optuna issues **~70 commits per trial** (one per searched parameter, plus user attributes and the
> trial create/complete). With `synchronous_commit=on`, profiling showed `psycopg2 commit` was
> **55% of total runtime**. Setting it off measured **1.68× solo**, 1.14× at 20 workers.

That is the honest cost of Postgres for this workload: a chatty, tiny-transaction write pattern that
network round-trips punish.

### What our workload actually is *today*

| | then (June) | now |
|---|---|---|
| concurrent workers | **~30** | **1** |
| studies at a time | 6 in parallel | **1, sequential** |
| server load | saturated | **1.16 on 32 cores**; optimizer at 74% of *one* core |

The current campaign runs `for INST; do for TF; do … done; done` — **one study, one process, one
writer**. Under that shape **SQLite's single-writer limitation cannot bind**, and Postgres's advantage
(true concurrent writers) has nothing to do. Meanwhile Postgres would add a container dependency, a
network hop, and 70 round-trips per trial.

**Verdict: for today's workload SQLite is not merely adequate, it is the faster and simpler choice.**

### Would a bigger database or a load balancer help?

**No — and the load-balancer idea is a category error worth naming.** A load balancer spreads *many
independent network requests* across *several servers*. We have one batch process writing to a local
store. There are no requests to spread. It would introduce new failure modes and improve nothing.

Likewise "enterprise database": our store holds trial metadata measured in tens of megabytes, written
by one process. The bottleneck in this system has never been the database — it is **indicator
computation**, which is why the win that mattered this month was making `dfa` 1,396× faster, not
changing storage engines.

### ⚠️ Where the real cost is

Not performance — **ambiguity**. Two backends exist, nothing announces which is live, and the study
files are named identically in both. That is precisely how I came to tell you twice that finished work
had been lost.

**Recommended (small, safe):**

1. **Print the active backend and file at study start** — one line: `storage: sqlite:///…/wsh_4h.db`.
2. **Add a `find_study` locator that searches BOTH backends** and reports where each match lives, so
   "does this study exist?" can never again be answered from one half of the system.
3. **Keep both backends.** The parallel-worker case is real and will return; Postgres is correct for it,
   already tuned, and documented.

**Not recommended:** migrating, consolidating, or removing either backend. The system is stable, the
design was earned by a real incident, and changing it risks more than it returns — exactly your instinct.

---

## 3. Summary

| | |
|---|---|
| ORM | already present via Optuna/SQLAlchemy. **Do not add our own.** Instead centralise the 6 raw `SELECT`s in `storage.py`. |
| storage backend | SQLite default is **correct for sequential campaigns**; Postgres is correct for many-worker sweeps and is already tuned. **Keep both.** |
| scaling up | not justified — the bottleneck is indicator compute, not I/O. |
| the actual defect | **backend invisibility.** Fix with a startup line and a both-backend locator. |
