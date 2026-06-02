---
name: remote-training-master
description: Master spec for the remote GPU training workflow — local source-of-truth, server-only compute, rsync sync, detached jobs, live log streaming. Covers architecture, the approach analysis, every toolkit script, the GPU (gfx1031) setup, security, and troubleshooting.
type: master
---

# Remote Training Workflow — Master Specification

How we train models on the remote AMD server while keeping **all data, code, results,
and documentation local and version-controlled**. The server is treated as
**ephemeral compute only**. This document is the single source of truth for the
`subprojects/meta-prophet/server/` toolkit.

> Status: connection, key auth, GPU, and the full sync→train→log→results loop are all
> **verified working** (see §8). The end-to-end smoke test (`smoke_test.py`) trained a
> model on the GPU and returned results to local.

---

## 1. The server (verified facts)

| Property | Value |
|---|---|
| Host (off-LAN) | `78.89.209.212:33362` (KW public IP). LAN-private `192.168.50.62` not reachable off-LAN. |
| User | `dev` (uid 1000) — **not root, no passwordless sudo** → userland only |
| CPU | AMD Ryzen 9 9950X — **32 threads** |
| RAM | 128 GiB (~123 GiB free) — the old 14 GB local OOM is gone |
| GPU | **AMD Radeon RX 6700 XT** = `gfx1031` |
| ROCm | system 7.1.0; venv torch is `2.5.1+rocm6.2` (wheel bundles its own runtime) |
| Disk | 776 GB free |
| Scratch | `/home/dev/Mulham/meta-prophet/` (we created it; `Mulham` pre-existed) |
| Reusable venv | `/home/dev/Mulham/.venv` — already has `torch/torchvision/torchaudio 2.5.1+rocm6.2` + `pytorch-triton-rocm` |
| Caveats | **no `tmux`**, shared box (20 Docker containers running) |

### GPU is forced ON (`gfx1031` override)
`gfx1031` is **not** in ROCm's official support list, so PyTorch must be told to use
the supported `gfx1030` codepath:

```
export HSA_OVERRIDE_GFX_VERSION=10.3.0
```

With that, `torch.cuda.is_available()` → `True`, device = "AMD Radeon RX 6700 XT", and
real GPU matmul/training works. A harmless `hipBLASLt … unsupported architecture`
warning appears and auto-falls back to `hipblas` — expected, not an error. Every
toolkit script that runs Python exports this override automatically.

---

## 2. Architecture — "thin remote compute"

```
   LOCAL (source of truth, git)                REMOTE (ephemeral compute)
   /mnt/data/projects/trading                  /home/dev/Mulham/meta-prophet
   ├── data, code, notes, results              ├── data/   (synced CSVs, resident)
   │                                           ├── code/   (synced training scripts)
   │      ── push.sh (rsync up) ─────────▶      ├── runs/<id>/  (models, metrics, preds)
   │                                           └── logs/<id>.log
   │      ◀──── pull.sh (rsync down) ──         (GPU: gfx1031 + HSA override)
   │      ◀──── follow.sh (live tail) ──        (jobs: setsid+nohup, disconnect-proof)
   └── server_runs/<id>/  (mirrored back; documented & analysed locally)
```

**Principles**
- **Local is canonical.** Data, code, results, docs live and are versioned locally.
- **Server holds nothing precious.** Scratch is reproducible from local at any time.
- **Only training runs remotely.** Preprocessing, analysis, plotting, reporting = local.
- **Code is edited locally**, synced read-only to the server, executed there.
- **Data is resident**: synced once, reused across runs (don't re-copy big CSVs).

---

## 3. Was this the most effective approach? (analysis)

The proposed design (local data + remote training + rsync both ways + local docs) is
the **correct standard pattern** for a shared/untrusted remote box. Four refinements
were applied to make it robust; all are now implemented:

| Proposed | Issue | Implemented refinement |
|---|---|---|
| "transfer logs every iteration" | per-iteration rsync is chatty/racy | **one long-lived follower** (`follow.sh`: `tail -f --pid` over ssh, `tee` to local) + a structured `metrics.jsonl` per run |
| (implicit) run over ssh | SSH drop kills the job | **`setsid`+`nohup`** detachment (`train.sh`); a dropped follower never stops training |
| password in `.env` | plaintext credential, re-read every call | **dedicated SSH key** (`~/.ssh/amd_trading`), `SERVER_DATA.env` git-ignored |
| re-sync/rebuild each run | wasteful on big CSVs / venv | **resident data + reusable venv**; per-run `runs/<id>` scoping; thread caps for the shared box |

Net verdict: **yes, the approach is sound** — with continuous streaming (not
per-iteration push), detached jobs, key auth, and resident env/data it is both
effective and safe on a shared machine.

---

## 4. Toolkit (`subprojects/meta-prophet/server/`)

| File | Purpose |
|---|---|
| `server.env` | All connection + path + GPU + thread config. **No secrets** (key auth). |
| `lib.sh` | Shared `srv()` (ssh), `push()/pull()` (rsync), logging. Sourced by every script. |
| `setup_remote.sh` | Idempotent: make scratch dirs, **verify GPU**, optionally `--deps` install darts/etc. |
| `push.sh` | `push.sh {data|code|path} <src> [dst]` — rsync local→remote. |
| `train.sh` | `train.sh <run_id> <script.py> [args]` — launch **detached** GPU job; logs→`logs/<id>.log`, outputs→`runs/<id>/`; saves PID. |
| `follow.sh` | `follow.sh <run_id>` — live-stream the remote log to terminal **and** mirror to `server_runs/logs/`. Exits when the job's PID dies. |
| `status.sh` | `status.sh [run_id]` — host/GPU load; per-run alive/dead + last log lines + outputs. |
| `stop.sh` | `stop.sh <run_id>` — graceful TERM then KILL. |
| `pull.sh` | `pull.sh <run_id>` (or `--all`) — rsync run outputs + log back to `server_runs/`. |
| `gpu.sh` | quick `rocm-smi` snapshot. |
| `smoke_test.py` | tiny GPU training job used to validate the loop. |

`server_runs/` (local mirror of results/logs) is git-ignored — outputs are regenerable;
only scripts + docs are tracked, consistent with the rest of the project.

---

## 5. Standard workflow (per experiment)

```bash
cd subprojects/meta-prophet/server

# 0. one-time per session: verify env + GPU (and install deps the first time)
./setup_remote.sh            # or: ./setup_remote.sh --deps

# 1. sync inputs (data resident — only when it changes) and the training code
./push.sh data ../../../data/full_data/NQ_4h.csv     # example; reused across runs
./push.sh code ../scripts/                            # the model scripts

# 2. launch a detached GPU run (returns immediately, survives disconnect)
./train.sh darts_nbeats_plain 09_darts_rnn.py --model nbeats --regressors none

# 3. watch it live (Ctrl-C detaches; the job keeps running)
./follow.sh darts_nbeats_plain
#   ... or check asynchronously:
./status.sh darts_nbeats_plain

# 4. bring results home and analyse/plot/report LOCALLY
./pull.sh darts_nbeats_plain
```

**Contract for training scripts:** accept `--out <dir>` and write all artifacts there
(model, `metrics.jsonl`, predictions, a `result.json` summary), and print one progress
line per epoch/step to stdout (it becomes the streamed log). `smoke_test.py` is the
reference implementation.

---

## 6. Security

- **Key auth only** for automation: `~/.ssh/amd_trading` (ed25519, no passphrase),
  installed in the server's `authorized_keys`. SSH alias `amd-trading` in `~/.ssh/config`.
- **`SERVER_DATA.env` is git-ignored** and untracked — the plaintext password never
  enters version control and is no longer needed once the key is installed.
- `server.env` is safe to commit (no secrets).
- Optional hardening (not done, would need sudo): disable password auth server-side.

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `cuda.is_available()` False | `HSA_OVERRIDE_GFX_VERSION=10.3.0` not exported (scripts do this automatically). |
| `hipBLASLt … unsupported architecture` warning | benign — falls back to hipblas on gfx1031. Ignore. |
| GPU "low-power state" in rocm-smi | idle; wakes on first real op. |
| job dies on disconnect | use `train.sh` (setsid+nohup), never a bare `ssh … python`. |
| `Permission denied (publickey)` | key not installed / wrong path — re-run the key install, check `IdentityFile`. |
| private IP unreachable | off-LAN — use the public `78.89.209.212` (already in `server.env`). |
| OOM | shouldn't happen (123 GB), but lower `THREADS` / batch size; we're on a shared box. |
| need `darts` etc. | `./setup_remote.sh --deps` (installs into the reusable venv). |

---

## 8. Verification log (this setup)

- SSH key auth: `KEY_AUTH_OK`, password-free. ✓
- GPU: forced gfx1031 → `cuda.is_available: True`, RX 6700 XT, 4000×4000 matmul 0.21 s. ✓
- End-to-end smoke (`smoke_dryrun`): detached launch (PID), live log stream + local
  mirror, GPU training (loss 12.6→0.03 learning y=3x+2), `result.json` pulled to
  `server_runs/smoke_dryrun/`. ✓

---

## 9. Next

The forced-GPU path is proven, so the long-paused work is unblocked:
- **EXP-D** — Darts NBEATS / TFT / RNN (plain + regressors) on GPU.
- **EXP-E** — fold those into the 12-entry price leaderboard.
Sync the existing `scripts/09_darts_*.py`, `./setup_remote.sh --deps`, then `train.sh`
each model and `pull.sh` the results for local analysis.
