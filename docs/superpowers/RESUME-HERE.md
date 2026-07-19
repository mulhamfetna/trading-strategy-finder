# ▶️ RESUME POINTER — updated 2026-07-14

> **📌 For the full current state across ALL workstreams, read
> [`MASTER-STATUS-2026-07-14.md`](MASTER-STATUS-2026-07-14.md) first — it supersedes this file's
> workstream summaries.** This pointer is kept for the server/infra details and the standing rules.
>
> **Latest state:** FA closed (priced in), stop-loss closed (dead at 1s), #4 done, **#5 answered**
> (session = risk-not-edge), silver + Asia-cell frozen, **#7 research done — D1 (fit per-trade P&L) is the
> queued next step, but the user is about to narrow the #7 research with new information.**

**Read this first when picking the workstream back up.**

---

## WHERE WE ARE: both big questions are SETTLED. Nothing is half-finished.

### 1. Fundamental analysis — **PRICED IN**, and this time it is earned

The verdict I retracted on 07-13 for having 12% power came back at **882 releases / 99% power**.
Direction **−0.004**, magnitude **−0.018**, persistence **48.2%**, shape **p=0.880**. All four null, at
full power. **Same sentence as before; completely different standing.**

The "magnitude survivor" is dead: it was **2025 being the luckiest of 17 years** (+0.281 vs a 17-year mean
of **+0.027**). The decisive split — **2010–2023: r = −0.006 at 100% power. 2024–2026: r = +0.111 at 26%
power.** The effect exists *only* where we were blind.

### 2. The dynamic stop-loss — **DEAD**, now confirmed at 1-SECOND resolution (Task #11)

**The sweeps are REAL. 94% of our 235 stop-outs are swept, median just ONE SECOND beyond the stop.** The
resolution complaint was completely correct: 1-minute bars cannot see them.

**And it changes nothing.** The best rule you could actually trade earns **+$80 per trade against a
±$1,600 per-trade swing (p = 0.452)** — indistinguishable from zero, exactly as a martingale predicts.
Two-thirds of even that is just *"the stop is too tight"* (a dumb 40→120 widened stop captures it with no
1-second data at all). **Seeing the sweep more clearly does not make it profitable to sit through.**

📄 **[`06-VERDICT-at-full-power.md`](06-VERDICT-at-full-power.md)** — the full write-up of both.
📊 Raw output: [`results/`](results/) — `17y_direction.txt`, `17y_pattern.txt`,
`17y_magnitude_by_year.txt`, `stop_1s.txt`.

---

## ✅ CLOSED 2026-07-14 PM

- **#4 — `veto_mask` rename** (`a1017a2`). Engine param → `veto_vote_mask`; it does NOT block (`entry_gate`
  is the sole blocking array; the veto is folded in upstream). Docstring documents the trap. Golden 6/6
  byte-identical, integration test passes. `runner.veto_mask` (the correctly-named METHOD) untouched.
- **D3 — silver** (`880679e`). Pre-registered test (`study_silver.py`); **no long silver history exists**,
  so a powered test is impossible. Passed 3/3 pre-declared criteria but the raw headline died under the
  17-year surprise ruler and the survivor is a suppressor-prone partial at 12% power in the fluke window.
  → **Not dropped, not confirmed: FROZEN forward test.** Re-run once ~6-12 mo of new silver data exist.
  Full writeup: report 06 Part 12.

## ➡️ WHAT TO DO NEXT (in order)

| # | Task | Why |
|---|---|---|
| **5** | **Trading-session windows** (Asia / London / NY, overlaps, gaps) | The 09:30 NY open contaminated the news study. Session structure is currently **invisible** to the system. |
| **7** | **Fit our own probability distribution** | **Now better motivated than ever:** the per-trade spread on a stop-out is **80 points**. That fat tail is precisely what defeated every edge we measured — a +4 pt/trade effect needs ~3,220 samples to see. Correct tail probabilities feed **stop placement and sizing** directly. |

---

## 🔒 ISOLATION — this workstream is PINNED, do not mix it with other agents' work

Other agents are working in parallel on `dev` in **separate worktrees**. Keep out of their way:

- **Local:** work in **`/mnt/data/projects/trading`**, which `git worktree list` shows is itself a
  worktree pinned to branch **`fundamental-analysis`**. Others hold `.worktrees/timecap-eod` (on `dev`),
  `.worktrees/phase1-core-engine`, `.worktrees/live-dashboard`.
- **NEVER** switch branches in this directory. **NEVER** merge into or push to `dev`.
- **Server:** `/home/dev/Mulham/fa-m1` is this workstream's section. It is **not a git repo** — a plain
  rsync'd file tree — so there is no branch to contaminate there.

**Server environment that actually works** (this cost real time to rediscover):

```bash
ssh amd-trading
source /home/dev/Mulham/.venv/bin/activate
cd /home/dev/Mulham/fa-m1/Parametric-Indicators

# ENGINE studies (champions, trades, stop-loss) — the engine's own 2025-2026 price data:
export WSH_DATA_BASE=/home/dev/Mulham/wsg-h  WSG_DATA_ROOT=/home/dev/Mulham/wsg-h/data

# FUNDAMENTALS studies (17-year frame + ALFRED) — a different base:
export WSH_DATA_BASE=/home/dev/Mulham  WSG_DATA_ROOT=/home/dev/Mulham/data
export FRED_API_KEY=$(cat ~/.config/fred/api_key)     # installed, mode 600, OUTSIDE the repo
```

---

## 🧰 WHAT GOT BUILT/FIXED THIS SESSION (all committed, all verified)

| | |
|---|---|
| **`study_stop_1s.py`** | Task #11. Sweep classification + the tradeable delay rule + **the dumb-control** + **a bootstrap significance test**. |
| **`extended_data.load_1s_windows()`** | Many windows, **ONE pass** over the 7.3 GB / 142M-row file. **Byte-seeks** straight to the data (ISO timestamps sort lexicographically), skipping ~88% of the file. 235 windows in **7 seconds**. |
| **`alfred.py`** | `SeriesNotInAlfred` for HTTP 400 (permanent, don't retry) · retry+backoff on 429/5xx · **re-raise** rather than swallow. |
| **`study_surprise.py`** | Counts **expected drops** vs **TRANSIENT failures** separately, and **REFUSES to write the cache** if any transient survived — a cached hole would be permanent and invisible. Cache is keyed on a **calendar fingerprint**. |
| **`watchdog.py`** | **Self-match guard.** `pgrep -f <pattern>` used to match the watchdog's own command line, so it could **never report death**. |

---

## ⚠️ STANDING RULES (every one of these was learned by getting it wrong)

- **Never run compute on the local box** (12c/14GB) without explicit permission. **Server for everything.**
- **Never wait blindly.** `python3 -u` + a live log + the **watchdog**. Poll short; report state each time.
- **Never report a negative result without a power analysis** — computed against a **pre-declared**
  minimum effect (`MEI = 0.15`), **never** the observed one. Power against the observed effect is
  circular and makes every true negative print as *"underpowered."*
- **Never report a POSITIVE result without asking what the noise looks like.** A +$18,685 headline was
  +$80/trade against a ±$1,600 spread. **Always run the dumb control** — two-thirds of that "edge" was
  just a wider stop.
- **Never hand-type a number into a report.** Paste it from the run. *(I nearly broke this — I began
  reconstructing a 17-row table from memory. That is fabrication.)*
- **Write the kill criterion down BEFORE the run** — and then **implement the criterion you actually
  wrote.** My first pass coded "is the total negative?" when I had declared "is it *indistinguishable
  from zero*?", and it would have retracted a correct report on pure noise.
- **The 17-year frame is STUDY-ONLY.** The engine must never load it — it would change `n_split` and the
  volatility gate, and therefore **every champion**.

**Production is untouched throughout:** `news_veto` + `track_excursions` default **OFF**, golden 6/6
byte-identical, **$0 spent on data.**
