# WS-EARN Stage 1 — TradingView verification worksheet (criterion C4, issue #110)

**What you are checking:** that the timestamp in our table is the moment the market actually
reacted, to within ±1 minute. Our timestamps come from SEC EDGAR — the second the SEC accepted
the company's Form 8-K earnings filing. That is *documentary*, not derived from price.

**Why your check matters:** EDGAR records when the FILING was accepted, not when the press
release crossed the wire. For Apple the two coincide. For others the filing can lag the release
by minutes. Your eyes on the chart are the only fully independent test of the minute we have —
no free data vendor publishes announcement times at all (Nasdaq's own API returns
`time-not-supplied`).

**Pass mark, pre-registered before collection:** ≥ 34 of 36 within ±1 minute.

## How to check one row

1. Open TradingView, symbol **NQ1!** (Nasdaq-100 futures — it trades after the 16:00 close, so
   it covers after-market earnings; QQQ regular-hours data does not).
2. Set the interval to **1 minute**.
3. Jump to the date and time in the row.
4. You are looking for a **sudden volume and range expansion** at that minute or the one after.
5. Write what you see in the verdict column.

⚠️ **Do not adjust our timestamp to match the spike.** If they disagree, record the disagreement.
Moving the timestamp to fit the price would make the later analysis circular — we would be
'discovering' a spike exactly where we had defined it to be.

⚠️ Rows marked **OUTLIER** sit far from that company's usual release time. Being an outlier does
not make a row wrong — a company can genuinely release off-schedule — but they are the rows most
worth your attention.

ℹ️ Rows marked `outside_span` are after 2026-05-19, where our local price file ends. **TradingView
still has that data**, so you can check them normally; they simply are not usable for analysis yet.

| # | ticker | date | time (ET) | session | flag | NQ bar | verdict (✓ / ✗ / note) |
|---|--------|------|-----------|---------|------|--------|------------------------|
| 1 | **NVDA** | 2024-02-21 | **16:22:09** | AMC |  | bar_present |  |
| 2 | **NVDA** | 2025-05-28 | **16:21:30** | AMC |  | bar_present |  |
| 3 | **NVDA** | 2026-05-20 | **16:21:19** | AMC |  | outside_span |  |
| 4 | **GOOGL** | 2024-01-30 | **16:01:26** | AMC |  | bar_present |  |
| 5 | **GOOGL** | 2025-04-24 | **16:01:26** | AMC |  | bar_present |  |
| 6 | **GOOGL** | 2026-07-22 | **16:01:36** | AMC |  | outside_span |  |
| 7 | **AAPL** | 2024-02-01 | **16:30:30** | AMC |  | bar_present |  |
| 8 | **AAPL** | 2025-05-01 | **16:30:21** | AMC |  | bar_present |  |
| 9 | **AAPL** | 2026-07-30 | **16:30:28** | AMC |  | outside_span |  |
| 10 | **MSFT** | 2024-01-30 | **16:03:17** | AMC |  | bar_present |  |
| 11 | **MSFT** | 2025-04-30 | **16:06:03** | AMC |  | bar_present |  |
| 12 | **MSFT** | 2026-07-29 | **16:04:53** | AMC |  | outside_span |  |
| 13 | **AMZN** | 2024-02-01 | **16:06:02** | AMC |  | bar_present |  |
| 14 | **AMZN** | 2025-05-01 | **16:15:00** | AMC |  | bar_present |  |
| 15 | **AMZN** | 2026-07-30 | **16:06:23** | AMC |  | outside_span |  |
| 16 | **AVGO** | 2024-03-07 | **16:18:09** | AMC |  | bar_present |  |
| 17 | **AVGO** | 2025-06-05 | **16:27:02** | AMC |  | bar_present |  |
| 18 | **AVGO** | 2026-06-03 | **16:21:35** | AMC |  | outside_span |  |
| 19 | **META** | 2024-02-01 | **16:10:29** | AMC |  | bar_present |  |
| 20 | **META** | 2025-04-30 | **16:16:00** | AMC |  | bar_present |  |
| 21 | **META** | 2026-07-29 | **16:03:23** | AMC |  | outside_span |  |
| 22 | **TSLA** | 2024-01-24 | **17:24:27** | AMC | ⚠️ OUTLIER | in_span_no_bar |  |
| 23 | **TSLA** | 2025-04-22 | **16:10:12** | AMC |  | bar_present |  |
| 24 | **TSLA** | 2026-07-22 | **16:35:52** | AMC |  | outside_span |  |
| 25 | **MU** | 2024-03-20 | **16:00:45** | AMC |  | bar_present |  |
| 26 | **MU** | 2025-06-25 | **16:03:10** | AMC |  | bar_present |  |
| 27 | **MU** | 2026-06-24 | **16:02:01** | AMC |  | outside_span |  |
| 28 | **WMT** | 2024-02-20 | **06:59:55** | BMO |  | bar_present |  |
| 29 | **WMT** | 2025-05-15 | **06:58:44** | BMO |  | bar_present |  |
| 30 | **WMT** | 2026-05-21 | **06:59:53** | BMO |  | outside_span |  |
| 31 | **AMD** | 2024-01-30 | **16:16:19** | AMC |  | bar_present |  |
| 32 | **AMD** | 2025-05-06 | **16:16:45** | AMC |  | bar_present |  |
| 33 | **AMD** | 2026-05-05 | **16:16:06** | AMC |  | bar_present |  |
| 34 | **ASML** | 2024-01-24 | **06:01:45** | BMO |  | bar_present |  |
| 35 | **ASML** | 2025-04-16 | **06:02:40** | BMO |  | bar_present |  |
| 36 | **ASML** | 2026-07-15 | **06:05:47** | BMO |  | outside_span |  |

**Total rows to check: 36.** Pass mark ≥ 34 within ±1 minute.

---

## Supplementary — the time-of-day outliers (NOT part of the pre-registered 36)

These sit far from their company's usual release time, so they are the most informative rows in
the whole table. They are listed **separately on purpose**: criterion C4 was pre-registered at
36 rows with a pass mark of 34, and quietly enlarging the sample after the fact would change the
denominator of a test that was fixed in advance. Check them because they are interesting — the
result does not count toward C4 either way.

| ticker | date | time (ET) | minutes from that company's median | note |
|--------|------|-----------|-----------------------------------|------|
| **TSLA** | 2024-01-24 | **17:24:27** | 74 | falls inside the 17:00-17:59 CME halt — no NQ bar exists |
| **ASML** | 2024-10-15 | **11:34:59** | 332 | only intraday event in the entire table |
| **META** | 2025-01-29 | **16:47:14** | 39 |  |

## If a row fails

Note the time you actually see the spike. A *consistent* per-company offset is criterion C5 —
it becomes a recorded correction. A *random* disagreement means the source is unreliable for
that company and it gets excluded, with the exclusion recorded.
