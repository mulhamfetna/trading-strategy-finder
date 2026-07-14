# ⏸️ RESUME POINTER — paused 2026-07-14

**Read this first when picking the workstream back up.**

---

## WHERE WE LANDED

**The fundamental-analysis question is SETTLED.** The verdict I retracted on 07-13 for having 12% power
came back at **871 releases / 99% power** and is now **earned**: scheduled US macro news is **priced in**.
Direction −0.004, magnitude −0.018, persistence 48.2%, shape p=0.880. **All four null, at full power.**

**The "magnitude" survivor is dead** — it was **2025 being the luckiest of 17 years** (+0.281 vs a
17-year mean of +0.027).

📄 **[`06-VERDICT-at-full-power.md`](06-VERDICT-at-full-power.md)** — the full write-up. Reports 00 and 01
have been updated to point at it.

---

## 🔴 THREE THINGS ARE UNFINISHED — in priority order

### 1. ALFRED fetch errors are silently shrinking the sample ⚠️ **FIX THIS FIRST**

The pattern re-run hit **44 fetch errors by release 500** (the direction run had only 5). Each error does
a bare `continue` — **it silently drops that release from the sample.** Visible causes: HTTP **400 Bad
Request** and **502 Bad Gateway**. Only the first 5 errors are ever printed, so 39 were invisible.

**Why this is dangerous, and why I stopped the run:** that run was about to **write the degraded sample
into the new cache**, where every future run would hit it. **A transient network blip would have been
baked in permanently.** I killed it before it wrote. **The `.sig` file does not exist, so the cache is
NOT poisoned** — verify that before doing anything else:

```bash
ssh amd-trading 'ls optimize/fundamentals/surprises_cache.*'   # .csv only = safe. .sig present = suspect.
```

**The fix, in `optimize/fundamentals/alfred.py`:**
- Add **retry with backoff** on 502/429/timeout (transient — these should never cost us a release).
- **Classify 400 Bad Request separately.** It is *not* transient. It most likely means we asked for a
  vintage **before that series existed** (e.g. PPIFIS early years) — which is a legitimate, expected
  drop, not a failure. **Count the two kinds separately and report them.**
- **Refuse to write the cache** if the transient-error rate exceeds a threshold. A degraded cache that
  silently persists is exactly the failure class this workstream keeps getting bitten by.

### 2. The per-year table in report 06, Part 5 is a placeholder

`06-VERDICT-at-full-power.md` Part 5 has a **⏸️ PENDING** block instead of the 17 per-year correlations.

**I started reconstructing those numbers from memory while drafting, caught it, and removed them.** They
must be pasted **verbatim from the run** — do not hand-type them:

```bash
python3 -u optimize/fundamentals/study_magnitude_17y.py | tee results/17y_magnitude_by_year.txt
```

The **aggregates** in that section (9 pos / 8 neg, mean +0.027, sd 0.144, 2025 = +0.281) **are** from the
run and are safe to cite.

### 3. `results/17y_pattern.txt` still carries the INVERTED power label

The committed artifact says `power = 8% (underpowered — cannot tell)` — the **opposite** of the truth. It
was produced **before** the `MEI = 0.15` fix. The **correlations are right; the labels are backwards.**
Re-running `study_pattern.py --extended` regenerates it correctly (**REAL NEGATIVE, power 99%**). That
re-run is what got interrupted by problem #1.

---

## ✅ WHAT IS ALREADY DONE AND SAFE

| | |
|---|---|
| FRED API key **installed on the server** | `~/.config/fred/api_key`, mode 600, **outside the repo** |
| **Cache fix** (`study_surprise.py`) | Cache is now keyed on a **calendar fingerprint**, not a date-span comparison that could never pass. Before this, **945 ALFRED calls re-ran on every single invocation** (~17 min) while the log printed `rebuilding` as if normal. **A cache that never hits is not a cache.** |
| Reports 00 / 01 updated | Both now point to 06. Report 01 Part 5 is marked **self-retracted**. |
| Production | **Untouched.** `news_veto` + `track_excursions` default **OFF**. Golden 6/6. **$0 spent.** |

---

## ➡️ THEN: THE REAL NEXT TASK — #11

**The highest-stakes open item in the whole project.**

The **dynamic stop-loss verdict** (report 04: "post-stop price is a fair martingale, no rule can beat it")
was measured **on 1-minute bars**. We now know — from 1-second data — that the 08:30 head-fake which stops
you out **can last two seconds**:

```
08:30:01   -46 pts   <- THE LOW. This is what stops out a long.
08:30:03   +51 pts   <- already right, and stays right
08:30:10  +141 pts   <- THE HIGH
```

**A 1-minute OHLC candle records both extremes and cannot tell you the order.** So the martingale result
**may be a resolution artifact**, not a fact about the market.

**Kill criterion — declared IN ADVANCE (do not move it after seeing the data):**

> **If sweeps are rare (< 15% of stop-outs), OR if the post-sweep path is ALSO a martingale — the original
> verdict STANDS and the dynamic stop-loss stays dead.**

1-second data: `/home/dev/Mulham/data_2010_1s/NQ_Continuous_Data/NQ_1s.csv` (7.8 GB — chunked reads).

---

## 🔒 STANDING RULES (learned the hard way, do not relax)

- **Never run compute on the local box** (12c/14GB) without explicit permission. **Server for everything.**
- **Never wait blindly.** Every long run gets `python3 -u` + a live log + the **watchdog**
  (`optimize/fundamentals/watchdog.py`). Poll short; report state each time.
- **Never report a negative result without a power analysis.** Power is computed against a
  **pre-declared** minimum effect (`MEI = 0.15`), **never** the observed one — that is circular and it
  makes every true negative print as "underpowered."
- **Never hand-type a number into a report.** Paste it from the run. *(I nearly broke this today.)*
- **The 17-year frame is STUDY-ONLY.** The engine must never load it — it would change `n_split` and the
  volatility gate, and therefore **every champion**.
