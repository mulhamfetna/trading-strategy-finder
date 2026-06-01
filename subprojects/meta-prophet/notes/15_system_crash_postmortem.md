# System Crash Post-Mortem — 2026-06-01

> The machine froze and rebooted during Phase D (Darts) of the meta-prophet expansion.
> This documents the root cause, the evidence, what survived, and how to prevent a repeat.

## Verdict

**Out-of-memory (OOM) exhaustion → kernel thrash → reboot.** The machine has **14 GB RAM and ZERO swap**. I launched two PyTorch/Darts training batches *concurrently* in the background, on top of the still-running backend, frontend, and two `tail -f` watchers from earlier in the session. Two simultaneous deep-learning training processes (NBEATS + TFT) plus their dataloader workers exceeded physical RAM, and with no swap to absorb the spike the kernel had nowhere to fall back to. The system went unresponsive and rebooted.

This was **my operational error**, not a code bug and not a data problem.

## Evidence

| Fact | Value |
|---|---|
| `uptime` after recovery | `up 8 min` — confirms a recent hard reboot |
| Total RAM | 14 GiB |
| **Swap** | **0 B** ← the critical aggravating factor |
| CPU cores | 12 |
| Last output written before crash | `outputs/09_darts_rnn_plain.csv` @ 15:05 |
| Concurrent heavy jobs at crash time | batch 1 (RNN-reg → NBEATS-plain → NBEATS-reg) **and** batch 2 (TFT-plain → TFT-reg) launched back-to-back, so an NBEATS train and a TFT train were running at the same time |
| Also still running | uvicorn `--reload` (backend), vite (frontend), 2× `tail -f`, VS Code + Pylance |
| Survivors after reboot | only OS services + VS Code (the editor); all my session processes were killed |

## Why it ran out of memory

1. **Two torch trainings at once.** I launched batch 1 and batch 2 as separate background workers without waiting for batch 1 to finish. So at peak, an NBEATS model and a TFT model were training simultaneously — roughly double the memory footprint I'd budgeted for.
2. **PyTorch CPU oversubscription.** With `accelerator='cpu'`, PyTorch defaults to using all 12 cores for intra-op parallelism, and Lightning spawns additional dataloader workers. Two trainings × 12-thread pools = heavy CPU + memory contention.
3. **Walk-forward retrains a fresh model every 20–40 bars.** Each script fits ~15–29 separate models in a loop. PyTorch/Lightning does not always release all memory between fits promptly, so the resident set can climb across the loop rather than staying flat.
4. **No swap = no shock absorber.** On a machine with swap, a transient over-allocation pages out and slows down. With 0 B swap, the kernel's only options are OOM-kill or freeze. Under sustained allocation it thrashed the page cache and became unresponsive before it could cleanly kill a single process.
5. **Leftover services.** The backend (uvicorn `--reload` watches the filesystem), frontend (vite), and two `tail -f` processes were never stopped after the earlier "run servers" task. They didn't cause the crash but reduced the headroom.

## What did NOT cause it

- **Not the data.** `NQ_4h.csv` is intact and correct (verified in `09_neuralprophet_root_cause_report.md`).
- **Not a code bug.** The `10_darts_rnn_regressors.py` ValueError (RNNModel needs `future_covariates`, not `past_covariates`) is a real but *separate* bug — it would have failed fast and cheaply, not crashed the box.
- **Not Darts/torch instability per se.** A single Darts training at a time runs fine (we proved `09_darts_rnn_plain` completed successfully).

## Data-loss assessment

**No analytical work was lost.** All committed/written artifacts survived on disk:
- Outputs through `09_darts_rnn_plain.csv` are intact (naive, prophet, arima, sarimax×2, statsforecast, darts-rnn-plain = 7 of 12 models done).
- All notes, scripts, plots, and the expansion plan are on disk.
- Only the 5 in-flight/queued Darts runs (RNN-reg, NBEATS×2, TFT×2) were lost and must be re-run.

## Corrective actions (before resuming Phase D)

1. **Run Darts jobs strictly one at a time**, foreground, never two batches concurrently.
2. **Cap PyTorch threads**: set `torch.set_num_threads(2)` and Lightning `num_workers=0` in `_darts_runner.py` to bound CPU/memory.
3. **Stop the leftover servers** (uvicorn, vite, tail watchers) before any heavy compute — they're not needed for the meta-prophet study.
4. **Add a memory guard**: check `free -h` before launching each Darts model; skip/defer if available < 4 GB.
5. **Fix the RNN-regressors bug**: Darts `RNNModel` supports only `future_covariates`, not `past_covariates`. The regressor variants for RNN must pass covariates as future (they're bar-open-known, so that's actually correct semantically).
6. **Consider adding swap** (a one-line `fallocate`+`swapon` of even 8 GB) so a future spike degrades to slowness instead of a reboot — but that's the user's call (system-level change, outside the subproject).

## Resume plan

Phase D is **7/12 complete**. To finish safely:
- Fix `_darts_runner.py` (thread caps + RNN future-covariates).
- Re-run the 5 remaining Darts entries **sequentially, foreground, one at a time**, checking memory between each.
- Then proceed to Phase E (final 12-entry leaderboard + report) as planned.
