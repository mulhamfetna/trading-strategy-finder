# GC-02 — the walk-forward forward-validation scripts (issue #4)

Recovered on **2026-07-30** from `~/Mulham/fa-m1/` on the server, where they had survived only as
**untracked** files. The report they produced —
[`docs/superpowers/GC-02-inverse-macro-forward-validation.md`](../../docs/superpowers/GC-02-inverse-macro-forward-validation.md)
— was committed on 2026-07-22; **the code that produced it was not**, so the headline result was not
reproducible from the repository.

Same failure mode as the `wshgap` re-optimization (see
[`optimize/reports/gap_fills/reopt_wshgap/README.md`](../gap_fills/reopt_wshgap/README.md)): the
conclusion is in git, the evidence is on a box nobody is reading.

## The two scripts, and why both are kept

| file | what it is |
|---|---|
| `walk_forward_gc.py` | **v1 — LOOK-AHEAD, retained as the counter-example.** Measured the +5-minute move from the bar *before* the print (`paths_for` anchor = `close[t0−1]`), so it captured the release-instant jump you cannot trade. Produced a spectacular and **false** +$131/trade "tradeable" result. |
| `walk_forward_gc2.py` | **v2 — CAUSAL, the one the report uses.** Enters at the **close of the release-minute bar** (the number is already public) and holds to +5 minutes. Reports both rows, so the gap between them *is* the un-tradeable jump. |
| `gc_run.txt` | run log |

v1 is kept deliberately. The difference between the two files is the entire lesson of GC-02: the same
walk-forward, differing only in **where the entry anchor sits relative to the information**, moves the
answer from *"+$106.80 per trade"* to *"−$2.28 per trade"*.

## The result they produced

Gold, 766 walk-forward trades, sign fitted only on prior releases:

| move measured | mean | t-stat | $/trade |
|---|---|---|---|
| FULL (from pre-print bar — **look-ahead**) | +1.068 pts | **+4.26** | +$106.80 |
| CAUSAL (enter at release-bar close — **tradeable**) | −0.023 pts | −0.17 | **−$2.28** |

The fitted sign was negative in **95%** of trades, so the inverse relationship is real and stable out of
sample. **The entire edge is the sub-second release jump.** An NQ control fitted a negative sign in only
0.5% of trades and produced a null causal move, so the phenomenon is gold-specific.

## ⚠️ To re-run these

Both scripts hardcode `ROOT = ".../.worktrees/fundamental/..."`, the worktree they were written in.
Point that at the current checkout before running. They need the extended 16-year gold frame
(`extended_data.load_1m_extended("GC")`, 2010-06-06 → 2026-07-17, 5.66M bars) and the release calendar
(1,208 events, 2010 → 2026-12-09), both of which are server-side.
