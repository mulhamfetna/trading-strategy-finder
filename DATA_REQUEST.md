# DATA REQUEST — what to download, and exactly why

**Date:** 2026-07-13 · For: Mulham · From: the fundamental-analysis workstream
**Purpose:** unblock the one thing that is holding the entire news workstream hostage — **sample size.**

---

## THE ONE-LINE ANSWER

> **NQ 1-minute bars, 2010 → present. That alone unblocks everything.**
>
> **Then: SI, CL, GC.** Then, if easy: **seconds data — but ONLY in ±30-minute windows around the 1,208
> release timestamps I have generated for you.** Not continuous. Continuous seconds would be ~20 GB per
> instrument and 99.9% of it is useless to us.

---

## WHY — the arithmetic that makes this the top priority

| | |
|---|---|
| Releases needed for **80% statistical power** | **647** |
| Releases we have **now** | **117** |
| **Statistical power we currently have** | **12%** |
| **Releases that 2010 → present would give us** | **1,208** |
| **That is** | **1.9× the required sample** |

**Everything I concluded about news this week rested on 52–117 events. At 12% power, "we found nothing"
means almost nothing.** Even if news moves the market exactly as we hope, our test would have **missed it
88 times out of 100.** That is why the "scheduled macro is priced in" verdict had to be **retracted**.

**This download is the difference between a shrug and an answer.**

---

# 1 — TIMEFRAME: **1-MINUTE ONLY**

## ✅ Download: **1-minute bars, continuous, 2010 → present**

## ❌ Do NOT download: 4h, 1h, 15m, 5m, 2m, daily

**Reason:** every coarser timeframe is **derivable from 1-minute by aggregation — exactly and
losslessly.** I can build 4h/1h/15m/5m/2m from 1-minute bars myself.

**You cannot go the other way.** And downloading 4h separately only creates a risk that it *disagrees*
with what I aggregate — which would be a silent, poisonous inconsistency.

**1-minute is the base unit. Everything else is a computation.**

---

# 2 — INSTRUMENTS: priority-ordered

**Important context:** the 9-market robustness test found your markets are only **~3.2 independent bets**.
NQ / ES / RTY / YM are **0.95 correlated with each other** — they are four names for one position. So
downloading all nine gives far less new information than it looks like.

| Priority | Market | Why we want it |
|---|---|---|
| **1 · ESSENTIAL** | **NQ** | Everything is built on it. Nothing runs without this. |
| **2 · HIGH** | **SI** (silver) | **The pre-registered open question.** p = 0.007 — the strongest of all 36 cells we tested — and it **STRENGTHENED out-of-sample** (−0.140 → −0.500). It is the *only* result that behaved unlike everything else, and we cannot test it properly on 57 events. |
| **3 · HIGH** | **CL** (crude) + **GC** (gold) | **Falsification columns.** Different asset blocs. If our signal pushes *every* market the same way, we have built an **alarm detector**, not a news reader. These are how we find that out. |
| **4 · USEFUL** | **HG** (copper) | "Dr. Copper" — tracks economic growth. A strong jobs number **should** lift copper. If our signal says it falls, something is wrong with the signal. |
| **5 · LOW VALUE** | ES · RTY · YM · NG | **0.91–0.98 correlated with NQ.** Almost zero new information. Take them only if they're free. |

**Minimum viable: NQ.**
**Strongly recommended: NQ + SI + CL + GC.**

---

# 3 — SECONDS DATA: **yes, but windows only**

## The reason it matters (this is a real, open question)

On **2025-03-07**, the 08:30 payrolls bar did this:

| | |
|---|---|
| Open | 20107.50 |
| **Low** | **20061.50** ← fell 46 points |
| **High** | **20249.00** ← then rocketed 141 points |
| Close | 20218.25 |

**It went both ways inside the same sixty seconds.**

> **A 1-minute OHLC candle tells you open/high/low/close — and NOTHING about the ORDER those happened in.**
>
> So at the release minute, **1-minute data is provably too coarse to trade direction.** This may be the
> actual reason our "trade the reaction" study found nothing — **a data-resolution artifact, not market
> efficiency.** We cannot currently tell those two apart, and that is unacceptable.

## The scope — and why continuous seconds is the wrong ask

| Scope | Bars | Size (per instrument) | Verdict |
|---|---|---|---|
| Seconds, **continuous 2010–2026** | ~342,000,000 | **~20 GB** | ❌ **NO.** 99.9% of it is useless to us |
| **Seconds, ±30 min around each release ONLY** | **~4,500,000** | **~270 MB** | ✅ **YES** |

**I have generated the exact timestamp list for you:**

### 📎 `DATA_REQUEST_release_timestamps_2010_2026.csv` — **1,208 rows**

```
Date,event,agency
2010-01-08 08:30:00,nonfarm_payrolls,BLS
2010-01-14 08:30:00,retail_sales,Census
...
```

**Ask the provider for: 1-second (or tick) bars from `Date − 30 min` to `Date + 30 min`, for each of
those 1,208 timestamps.** That's a 60-minute window per event.

**If tick data is available at similar cost, take TICK over seconds** — ticks give true order-of-events,
which is precisely what we're missing.

**If seconds are hard to get: skip it.** It is a *nice-to-have* that unlocks Task #6. **The 1-minute
history is the thing that actually matters, and it is not optional.**

---

# 4 — 🚨 CRITICAL DATA-QUALITY REQUIREMENTS

**Get these wrong and the whole download is worthless. Please pass them to the provider verbatim.**

## 4.1 — TIMEZONE: **US Eastern wall-clock**

Our existing files are **US Eastern**, and I *proved* it rather than assumed it: mean volume peaks at
**09:30** and **15:59–16:00** (the US cash equity open and close), and the session starts at **18:00**
(the CME Globex reopen).

**New data MUST match.** If it arrives in UTC or Chicago time, every release timestamp is off by hours
and every result is garbage — **silently**, because it will still *run*.

**Ask explicitly: "what timezone are the timestamps in?"**

## 4.2 — CONTINUOUS-CONTRACT ROLL: **must match our existing files**

Futures contracts expire. A "continuous" series stitches them together — and **how** it stitches matters
enormously.

- Our current files are named `*_Continuous_Data`.
- **A roll gap looks exactly like a huge price move.** If the new data uses a different roll method
  (back-adjusted vs. non-adjusted, volume-roll vs. calendar-roll), the seam between old and new data will
  contain **fake moves**, and I will measure them as real.

**Ask: "back-adjusted or not? What is the roll rule?" — and tell me the answer.** If you know how the
existing files were built, tell me that too.

## 4.3 — ⚠️ **OVERLAP IS MANDATORY** ⚠️

**Do NOT download only 2010–2023.**

**Download 2010 → present, INCLUDING 2024, 2025 and 2026 — the years we already have.**

**Why this is non-negotiable:** I will compare the new data against our existing files **bar-for-bar, on
the overlapping years.** If they disagree — different prices, different volumes, different roll — then
**the new data is a different animal and I must NOT staple it onto the old.**

**This overlap check is the single most important safeguard in the whole request.** Without it, I could
silently join two incompatible datasets and every result afterwards would be quietly wrong.

## 4.4 — SCHEMA

Match our existing files exactly:

```
datetime,open,high,low,close,volume
2025-01-01 18:00:00,21269.0,21282.75,21253.5,21261.25,393
```

- `datetime` — no timezone suffix, US Eastern wall-clock
- OHLC — floats
- `volume` — integer
- **One row per minute.** Missing minutes (no trades) may be omitted — just tell me which convention.

## 4.5 — GAPS

Tell me about any known gaps (exchange outages, data-vendor holes). **A silent gap is worse than a
documented one** — I can handle a hole I know about; I cannot handle one I don't.

---

# 5 — STORAGE (so you can size the download)

| Item | Bars | CSV size |
|---|---|---|
| **NQ 1-min, 2010–2026** | ~5.9 million | **~350 MB** |
| NQ + SI + CL + GC (4 markets) | ~24 million | **~1.4 GB** |
| All 9 markets | ~53 million | **~3 GB** |
| Seconds, ±30 min windows, 1 market | ~4.5 million | **~270 MB** |

**All of this is comfortably manageable.** The AMD server has **123 GB RAM** and the studies read data in
windows, not all at once. **Storage is not the constraint — sample size is.**

---

# 6 — WHAT I WILL DO WITH IT (in order)

1. **Validate the overlap first.** Compare 2024–2026 bar-for-bar against our existing files. **If they
   disagree, I stop and tell you** — I will not staple incompatible data together.
2. **Rebuild the calendar to 2010** → ~1,208 events.
3. **Re-run every study at real statistical power**, reporting power alongside every result:
   - The magnitude signal (currently **+0.19, p=0.027, n=117** — *promising, not proven*)
   - The direction signal (currently *dead* — but on 28 out-of-sample events, which proves little)
   - The veto null test
   - The pattern / shape / persistence studies
4. **Test SILVER** on its pre-registered protocol.
5. **If seconds arrive:** resolve Task #6 — is 1-minute too coarse to trade the release?

**And then we will finally have an ANSWER instead of a shrug.**

---

# 7 — THE CHECKLIST (hand this to the provider)

- [ ] **1-minute bars** (NOT 4h/1h/etc — I derive those)
- [ ] **2010-01-01 → present**
- [ ] **Including 2024–2026** ← **MANDATORY, for the overlap validation**
- [ ] **NQ** (essential) · **SI** · **CL** · **GC** (recommended) · others if free
- [ ] **US Eastern wall-clock timestamps** — confirm explicitly
- [ ] **Continuous contract** — tell me the roll rule and whether it's back-adjusted
- [ ] Schema: `datetime,open,high,low,close,volume`
- [ ] Document any gaps
- [ ] *(Optional)* **Seconds or tick data, ±30 min around the 1,208 timestamps in
      `DATA_REQUEST_release_timestamps_2010_2026.csv`** — **NOT continuous**
