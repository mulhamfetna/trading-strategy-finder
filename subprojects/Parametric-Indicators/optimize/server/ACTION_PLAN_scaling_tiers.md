# Action Plan — Optimizer Scaling Tiers 1–4 (implement local → deploy server)

**Date:** 2026-06-12 · branch `dev` · derives from `optimize/server/REPORT_system_scaling_study.md` §6
**Status:** PLAN — not started. Approval-gated per tier. **Strategy: finish ALL local implementation first
(parity-locked, backward-compatible), then ONE deployment pass to the server.**
**Blocker on the deploy half:** SSH to the AMD box is currently failing — see
`optimize/server/INCIDENT_ssh_connection_reset.md`. **Local implementation does not need the server**, so
it proceeds regardless; deployment waits for SSH restoration.

> Companion docs: `REPORT_system_scaling_study.md` (the study + roadmap), `INCIDENT_wsh4_sqlite_contention.md`
> (the original failure), `MIGRATION_per_tf_db.md` (Tier 0.3, already done local), `INCIDENT_ssh_connection_reset.md`
> (current deploy blocker).

---

## 0. Governing principles (every tier)

1. **Local-first, deploy-once.** Implement + verify Tiers 1–4 locally; deploy in a single rollout when SSH is back.
2. **Parity-locked.** Every change keeps the engine byte-identical: `optimize/test_parity.py`
   (`$7,735/$3,670/n=66`) + full `pytest` green. Storage/infra changes must not touch trade math.
3. **Backward-compatible + reversible.** Like Tier 0.3: new paths fall back to the old behaviour with a
   loud warning; one rollback commit per tier.
4. **Approval-gated.** Present each tier, get the go, implement, report. No silent scope creep.
5. **Centralize before swapping.** The storage URL is hard-coded in 3 places
   (`optimizer.py:67`, `report_wsi.py:34,76`, `remote_wsi.sh`); centralize it FIRST so SQLite↔Postgres is one switch.

---

## 1. Status recap (where Tier 0 left us)

| Tier | Item | State |
|------|------|-------|
| 0.1 | `catch=StorageInternalError` | ✅ local (`93a9244`) |
| 0.2 | WAL + 60 s `busy_timeout` | ✅ local (`93a9244`) |
| 0.3 | per-TF DB files `wsh_<tf>.db` (lock split ~6×, backward-compat) | ✅ local (`813f9f5`) |
| — | **deployed to server?** | ❌ **no** — held until in-flight results pulled (now clean → deploy pending) |

So the deploy pass must carry **Tier 0 + the new Axis-A/B engine speedups** *and* whatever of Tiers 1–4 we finish.

---

## 2. PHASE L — local implementation (no server needed)

### Tier 1 — Right-size the backend (PostgreSQL) · RISK: MED · ~1–2 d
**1.2 first — centralize the storage URL.**
- [ ] **L1.1** Add `optimize/storage.py` (or a config read): `storage_url(tf)` returns
      `os.environ.get("WSH_STORAGE_URL")` if set, else the per-TF sqlite path (`sqlite:///…/wsh_<tf>.db`).
      One source of truth.
- [ ] **L1.2** Refactor `optimizer.py`, `report_wsi.py`, and the `remote_wsi.sh` `create_study`/`counts`/`pull`
      one-liners to call it. **No behaviour change when the env var is unset** (still per-TF sqlite).
- [ ] **L1.3** Add `engine_kwargs={"pool_size":32,"max_overflow":8}` only on the Postgres branch.
- [ ] **L1.4** Tests: env-unset → identical sqlite path (parity unchanged); env-set to a throwaway
      `sqlite:////tmp/x.db` → study created there. Document the Postgres URL form in the docstring.

**Acceptance L1:** `pytest` green; `test_parity` unchanged; with `WSH_STORAGE_URL` unset the system is
byte-identical to today. (The actual Postgres *server* is provisioned in Phase D.)

### Tier 2 — Resilience & self-healing · RISK: MED · ~1 d
- [ ] **L2.1** Worker **watchdog/respawn** in the launcher: wrap the worker loop so a worker that dies before
      its study hits the **target trial count** is respawned; log every respawn (ref §8.3 of the study).
- [ ] **L2.2** **Target-based idempotent runs:** a run means "reach N **total** trials for this study," not
      "add N." Compute remaining = `max(0, target − completed)` per worker so top-ups are exact + re-runnable.
- [ ] **L2.3** `bash -n remote_wsi.sh` + a dry-run of the launcher spec (echo the planned worker map).

**Acceptance L2:** simulated worker kill (local, tiny study) → final trial count unchanged after respawn.

### Tier 3 — Observability · RISK: LOW · ~1 d
- [ ] **L3.1** `status`/`counts` report **COMPLETE / RUNNING / FAIL** per study + trials/min (ref §8.4).
- [ ] **L3.2** Structured run log (one JSON line per poll: ts, per-TF counts, worker count, fail rate) + a
      threshold alert hook (reuse the Telegram watcher already in the toolkit).
- [ ] **L3.3** **Pre-flight contention smoke test:** a short high-concurrency probe (N workers × few trials)
      that asserts **zero** `database is locked` deaths — run before any multi-hour sweep, complements the
      parity gate. This is the explicit Tier-0 acceptance turned into a reusable command.

**Acceptance L3:** an injected FAIL is surfaced by `status` within ~60 s; the smoke test passes on per-TF sqlite.

### Tier 4 — Data layer for expansion · RISK: LOW–MED · ~2–3 d
- [ ] **L4.1** CSV→**Parquet** loader path (opt-in): read Parquet if present else CSV; a one-shot converter
      script. Keeps the in-RAM numpy path; faster load, smaller files. Parity must hold (same float64).
- [ ] **L4.2** **Dataset registry:** every run records path + content hash + provenance (reuse
      `optimize/DATA_PROVENANCE.md` conventions) for reproducibility across instruments × windows.
- [ ] **L4.3** **Capacity formula** documented where `WORKERS` is defined: `workers ≈ cores−2` for sqlite;
      Postgres lifts the cap. Encode as a comment + a derived default.

**Acceptance L4:** Parquet vs CSV load produces byte-identical arrays (hash check); registry entry written per run.

> **Tier 5 (multi-node orchestration)** stays **deferred** — out of scope until we exceed one box.

---

## 3. PHASE D — deployment pass (needs SSH restored)

Run **once**, after the local tiers are green and committed. Order matters.

- [ ] **D0** Pre-req: SSH to the AMD box works again (see `INCIDENT_ssh_connection_reset.md`); confirm with
      `remote_wsi.sh status` (read-only) — server idle, results already pulled.
- [ ] **D1** `remote_wsi.sh push` — rsync the optimized `Parametric-Indicators` (Tier 0 hardening + per-TF DB
      + centralized URL + watchdog + observability + Axis-A/B engine speedups). *(studies/results rsync-excluded.)*
- [ ] **D2** `remote_wsi.sh parity` — **server-side byte-identical check** on the new code before anything runs.
- [ ] **D3 (Tier 1 infra)** Provision **PostgreSQL** on the server (containerized, localhost-only, per §8.2):
      `docker run … postgres:16`; set `WSH_STORAGE_URL=postgresql://…`. Optional: `optuna.copy_study` the
      existing sqlite history, or start a fresh study prefix on PG and keep sqlite read-only.
- [ ] **D4** **Contention smoke test** (Tier 3.3) on the server at full worker count → **zero** lock deaths.
      This is the hard gate before committing to a multi-hour sweep.
- [ ] **D5** Launch the sweep with the watchdog + target-based semantics (trials/TF to be confirmed with the
      user — last target was 5,000/TF; the under-sampled 4h/1h need topping to target).
- [ ] **D6** `remote_wsi.sh status`/`counts` watch + Telegram alerts; `pull` results when targets are hit.

**Acceptance D:** full 6-TF sweep reaches target on every study, **no worker attrition**, no lock errors —
i.e. the original incident cannot recur.

---

## 4. Rollback map

| Undo | How |
|------|-----|
| any local tier | `git revert <tier_commit>` (each tier = 1 commit; env-unset path keeps old behaviour) |
| Postgres on server | unset `WSH_STORAGE_URL` → falls back to per-TF sqlite; `docker rm -f wsh-pg` |
| whole deploy | re-`push` the prior commit; server scratch is isolated (`/home/dev/Mulham/wsg-i`) |
| nuke optimizer changes | `git reset --hard 93a9244` (Tier-0 snapshot) — keeps Tier 0, drops 1–4 |

Nothing here touches the strategy/trade math (parity-locked), so worst case is an infra revert, not a results change.

---

## 5. Sequencing & approval gates

```
PHASE L (local, no server)            PHASE D (server, needs SSH)
  L1 Postgres URL central  [gate] ─┐
  L2 watchdog/respawn      [gate]  ├─► (all green, committed) ─► D1 push ─► D2 parity ─► D3 PG ─► D4 smoke ─► D5 run ─► D6 pull
  L3 observability         [gate]  │
  L4 data layer            [gate] ─┘
```
- Implement L1→L4 in order, **one approval + one commit + one UPDATE doc per tier** (same ritual as Axis B).
- Deployment (Phase D) is a **single gated pass** once SSH is back and the local tiers are merged.
- Sweep parameters (trials/TF, which TFs) confirmed with the user at D5.

---

## 6. Open decisions for you
1. **Start Phase L now** (SSH is down anyway) — begin with **Tier 1 (centralize URL + Postgres-ready)**? Recommended.
2. **Postgres history:** migrate the existing `wsh.db` trials into PG (`optuna.copy_study`), or start a fresh
   PG study prefix and keep sqlite read-only for the old fronts? (Lower-risk: fresh prefix.)
3. **Scope:** do all of Tiers 1–4, or stop after Tier 1+2 (the must-do resilience) and defer 3–4?
