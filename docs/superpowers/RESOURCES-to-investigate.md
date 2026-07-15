# RESOURCES TO INVESTIGATE — external data / signal sources

**Supplied by the user 2026-07-15 for deep investigation as potential data/signal sources for the FA-v2
(NQ + GC news → decision) workstream. Task #16.** Do not treat any of these as adopted yet — each needs a
real assessment of what it provides, cost, historical depth, and how (or whether) we can pull it
programmatically.

---

## The list

| # | URL | What it appears to be | The questions to answer |
|---|---|---|---|
| 1 | https://www.barchart.com/ | Market data — futures, options, equities, technicals, economic calendar | Does it give **historical intraday** futures data (NQ/GC) and a **historical economic calendar with release times**? Free tier limits? API? |
| 2 | https://en.macromicro.me/ | Macro-economic charts / indicators / dashboards | **Point-in-time** macro series? Anything FRED/ALFRED doesn't have? Export/API? |
| 3 | https://www.koyfin.com/ | Financial analytics dashboards (Bloomberg-lite) | Historical macro + market data depth; API vs UI-only; cost |
| 4 | https://companiesmarketcap.com/ | Market-cap rankings | Likely low relevance to NQ/GC futures news — confirm and probably drop |
| 5 | https://etfdb.com/ | ETF database / screener | Relevant only if we use ETF proxies (SPY/GLD) for longer history — worth checking GLD/QQQ history |
| 6 | https://seekingalpha.com/ | Analysis / news / sentiment | **News sentiment / event coverage** — could feed "content of the news"; is there structured/historical access or is it article-only? |
| 7 | https://stockanalysis.com/ | Stock fundamentals / data | Mostly equities fundamentals — relevance to NQ/GC macro news is limited; confirm |
| 8 | https://finviz.com/ | Screener / heatmap / news feed | News feed + a macro calendar; scrape-friendly? historical? |
| 9 | https://x.com/antpalkin/status/2072774690834153532 | X/Twitter thread | Review for method/ideas — summarize the claim, check if it's testable on our data, flag if folklore |
| 10 | https://x.com/ruujss/status/2074503360208884204 | X/Twitter thread | Same — summarize, assess, do NOT adopt untested |

---

## What "deeply investigate" means here (the assessment criteria)

For each source, the deliverable answers:

1. **What signal/data does it actually provide** that is relevant to NQ/GC and to news-content decisions?
2. **Free vs paid**, and the free-tier limits.
3. **Historical depth** — critically, does it offer **point-in-time / first-print** macro data (like
   ALFRED) or a **historical intraday economic calendar with exact release timestamps**? That is the
   scarce, valuable thing (it is what let us do the 17-year NQ study). UI-only sites that can't be pulled
   programmatically are low value for a systematic pipeline.
4. **Programmatic access** — official API, documented endpoints, or scrape-only (and terms-of-service).
5. **Verdict:** genuinely useful data source / idea worth testing / UI-convenience-only / drop.

## Discipline (do NOT skip)

- The two X threads are **claims, not evidence.** Summarize and test on our own data before believing —
  the same standard that killed the session-timing folklore and the London GMM edge. A viral trading
  thread is exactly the kind of thing that looks great and dies with a 1-bar entry delay.
- Prefer sources offering **historical, point-in-time, programmatically-pullable** data. Our whole
  advantage came from ALFRED first-print vintages + a 17-year tape; a pretty dashboard we can't query adds
  little to a systematic study.
- Watch for **survivorship / hindsight** in any "here's the pattern" content from social media.

**Recommended handling:** fold this into the FA-v2 research sequence — after the current news-decision
research pass lands, run a targeted assessment (likely a short web-research pass over these specific
sources) and produce a real-vs-useful table, then pull whatever passes into the data layer.
