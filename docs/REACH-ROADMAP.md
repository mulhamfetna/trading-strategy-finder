# REACH-ROADMAP — native SEO + GEO reach for the rung-4 record

**Filed 2026-08-31 (owner: "document those four tiers properly and let's do tier one today").**
Goal: maximum durable reach for this work — for the owner's profile as a data-science researcher, both
inside quantitative trading and in data science generally — at **minimal time and zero money**, and
**without touching the system's logic in any way**. Everything here is metadata, documents, and where the
existing documents get seen.

## The story we broadcast (fixed — every artifact tells the same one)

Not the P&L. The **method**: a public research codebase where every published number is a machine-verified
claim with three verifications and a declared blind spot; where negative results are power-tested and
published (0/225 opening-range cells survive realistic costs over 16 years); where every study is
pre-registered before it runs; and where the live track record is **out-of-sample by construction** — the
parameter set and trading universe were hash-frozen under a signed protocol (2026-08-31) before any of the
data they will be judged on existed. That story has almost no competitors; a P&L story has a million.

**Calibration rule:** the public claim today is "the rung-4 machinery is complete and the record clock has
started" — the frozen-replay record itself has zero windows until the next box drop. Never overclaim.

## Standing rules (inherit from the repo's law — restated here because outreach is where they bite)

1. **No logic changes.** This roadmap may touch README/docs/metadata/releases only.
2. **Nothing leaves our own repo without the owner's explicit go in that message.** Pushing to our own
   remote, editing our own repo's GitHub metadata, and cutting our own releases are normal workflow;
   external submissions (list PRs, preprint servers, journals, forum posts) are publishing — each waits
   for its own explicit "publish".
3. Public text says the engine runs on **"your own data"** naturally, as a design property. No inventory
   of sources, no boundary lines — it is simply how the system works.
4. **Every number quoted anywhere must be a ledger claim** (`optimize/verify/run.py`). If it isn't in the
   ledger, it doesn't go in an abstract, a README headline, or a post.
5. The external live system is a separate project and never appears in this material.

## Tier 1 — the repo as the search-and-AI surface (≈ hours; DO TODAY)

The repo is the canonical URL for everything else; GitHub is among the most heavily crawled and
AI-retrieved sources on the web. Make the repo answer the questions searchers and AI engines actually ask.

| # | Item | Detail |
|---|------|--------|
| 1.1 | **README: quotable, falsifiable headline numbers** | A "findings you can quote" section under FAQ-shaped headings, each line a ledger-bound number with its claim ID — the format generative engines lift verbatim. Fix stale counts (ledger 71→79). Add the rung-4 / frozen-replay story with the calibration rule above. |
| 1.2 | **`llms.txt`** | The emerging convention for AI crawlers: a root file naming what this repo is, the headline findings, and the canonical docs (POSITIONING, LIVE-PROTOCOL, the ledger) with stable links. |
| 1.3 | **GitHub metadata** | Topics extended toward what people search (`reproducibility`, `pre-registration`, `walk-forward-analysis`, `optuna`, …), homepage → the concept DOI, description kept aligned. |
| 1.4 | **Citation metadata check** | `CITATION.cff` / `.zenodo.json` already carry ORCID + concept DOI; extend keywords to match the topics. Google Scholar attribution flows from these automatically. |
| 1.5 | **Zenodo version release (executes #201)** | Tag + Release **v5.7.0** carrying POSITIONING.md, RUNG4-ROADMAP.md, the signed LIVE-PROTOCOL, and this roadmap → Zenodo mints the version DOI (Scholar-indexed, AI-crawled, free citability). Version DOI appended to CITATION.cff once minted. |

**Acceptance:** README/llms.txt merged to dev and released to main; topics live; v5.7.0 DOI resolves.

## Tier 2 — the citable paper layer (≈ days; the researcher-profile multiplier)

Papers are what Scholar, other researchers, and generative engines cite. Two artifacts, both free:

| # | Item | Detail |
|---|------|--------|
| 2.1 | **Preprint** | SSRN (frictionless) and/or arXiv q-fin.TR (needs endorsement). Candidate A — the powered null: *"Opening-range breakout does not survive realistic costs: a pre-registered 225-cell, 16-year study"* (reaches the trading field; nulls are rare and citable). Candidate B — the methodology: *"A machine-verified claims ledger for trading-system research"* (reaches general data science / reproducibility). Recommendation: A first (concrete, complete, already ledger-bound), B second. |
| 2.2 | **JOSS submission** | Journal of Open Source Software: free, peer-reviewed, built for research software, yields a real journal paper on Scholar. The repo already meets the substance bar (CI, tests green without data, AGPL, DOI, docs); needs a `paper.md` + reviewer-oriented install/usage pass. The "clone it and link your own data" design is exactly the reusability story JOSS wants. |

**Acceptance:** drafts written locally as `.md`, reviewed by the owner, submitted only on explicit go.

## Tier 3 — owned channels and communities (≈ hours of drafting; go-gated per item)

| # | Item | Detail |
|---|------|--------|
| 3.1 | **Blog post on the owner's domain** | One post on my-blog around the null result + the method (owned-domain SEO; the canonical narrative URL that social posts point at). |
| 3.2 | **Curated-list PRs** | One-line PR to `awesome-quant` (and similar): these pages carry enormous PageRank and sit in every model's training data; a single accepted line outperforms months of posting. Prepared text lives in this doc's companion issue; submission is go-gated. |
| 3.3 | **Community posts** | Hacker News ("Show HN" / the ORB null), r/algotrading, X, Bluesky — drafts as local files; the threads themselves get crawled into search and training corpora. Post on explicit go, owner's accounts. |

**Acceptance:** every draft exists as a committed/local file before anything is posted; each posting has
its own owner go recorded in the tracking issue.

## Tier 4 — deferred (cost exceeds return at current resources; revisit only on owner request)

YouTube/video content · conference talks and meetups · a dedicated docs website · paid promotion of any
kind · a Wikipedia presence (fails notability today; a JOSS paper + citations may change that later).
None of these are scheduled; none block anything above.

## Sequence and ownership

Tier 1 today (this session) → Tier 2 drafting next (2.1-A, then 2.2, then 2.1-B) → Tier 3 drafts alongside
Tier 2, released in one coordinated wave (blog post first, community posts point at it). Board and per-tier
issues track every step as comments, per the repo's documentation law.
