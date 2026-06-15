# Pending Questions — decisions awaiting the user (2026-06-15)

Every open decision in one place. Each entry has: **the question**, **options** (what each means + trade-off),
a **baby paragraph** (plain language), and **my recommendation**. Nothing here is acted on until you answer.

---

## Q1 — Split long/short SL/TP: evaluate it now, or leave for wsh5?
**Context:** original task point 5 ("shorts have their own SL/TP, longs have their own"). The engine already
*supports* split SL/TP (E1, golden-safe), but no study has *swept* it — the `{shared | split}` arm was deferred
to the next optimizer run (`wsh5`).

**Options:**
- **(a) Sweep split now** — run a standalone grid: does giving longs vs shorts different SL/TP beat the shared
  champion OOS? Pro: answers point 5 directly, on current data. Con: another multi-fold study (a few hours of
  build + run); risks selection bias on few short trades.
- **(b) Leave for wsh5** — let the full optimizer search the split space jointly with gate+indicators when we
  next re-optimize. Pro: cleanest, joint, no double-counting. Con: point 5 stays "enabled but unproven" until
  that run happens.

**Baby paragraph:** right now the system uses the *same* stop-loss/take-profit numbers whether it's buying or
selling. You asked whether buys and sells should get their *own* numbers. The machine can already do this — we
just haven't tested whether it actually helps. We can either test it on its own now, or fold it into the big
re-optimization later.

**My recommendation:** **(b)** — split is most meaningfully tested *jointly* in `wsh5`; a standalone sweep on
~150 trades risks an overfit answer.

---

## Q2 — Build the retrospective regime chart (regime_charts.py)?
**Context:** the action plan listed a visual "ribbon" (bands, new-highs/lows, regime over 2024–26) as deliverable
S2. The registry **tables** now cover the data; only the picture is missing.

**Options:**
- **(a) Build it** — a static chart (matplotlib) showing the price with the bands, NEW_HIGH/NEW_LOW markers, and
  the trend ribbon. Pro: fast to eyeball whether the regime labels make sense. Con: insight-only, not tradeable.
- **(b) Skip it** — the CSV/markdown tables are enough; spend effort elsewhere.

**Baby paragraph:** we have all the numbers in tables. This question is just: do you also want a *drawing* of them
(price chart with the highs/lows and trend colours marked) so you can glance at it instead of reading rows?

**My recommendation:** **(a)** if you like to verify by eye; otherwise **(b)**. Low stakes either way.

---

## Q3 — Phase E2: wire split SL/TP through the fast engine + optimizer?
**Context:** to let a future `wsh5` run actually *search* the split long/short space, the split fields must be
threaded through `fast_engine`, `optimize/core`, and the optimizer's search space, plus a fast-vs-exact parity
test (T4). This is engine plumbing, not a study.

**Options:**
- **(a) Do E2 now** — so wsh5 is ready to search split bounds the moment we launch it. Pro: unblocks Q1(b).
  Con: touches the hot path; needs the golden + parity gate re-run.
- **(b) Defer until we commit to a wsh5 run** — don't touch the engine until the re-optimization is actually
  scheduled.

**Baby paragraph:** the "fast" version of the backtester (used by the optimizer to try thousands of settings)
doesn't yet know about separate buy/sell stops. Before the optimizer can *search* for good split values, we'd
teach it. We can do that prep now, or wait until we're sure we're doing the big re-optimization.

**My recommendation:** **(b)** — pair E2 with the decision to actually run `wsh5`; doing it earlier is idle risk
on the hot path.

---

## Q4 — Commit & push the current work?
**Context:** uncommitted now = the price-range registry (`range_registry.py` + CSVs + `REGISTRY_TABLES.md`),
`DELIVERY_AUDIT.md`, the structure detectors (`smc.py` +4 functions + tests), `structure_tables.py` + outputs,
and all the docs (`PROGRESS_PIN`, `DEFINITION_BOOK`, `PLAN_structure_tables`, this file). Also 9 earlier `dev`
commits are unpushed.

**Options:**
- **(a) Commit + push everything** — snapshot all of it to `origin/dev`.
- **(b) Commit locally only** — record it but don't push.
- **(c) Hold** — keep working uncommitted.

**Baby paragraph:** none of today's work is "saved" into git yet (your rule: I only commit when you say so). Do
you want me to save it, save-and-upload it, or keep going without saving?

**My recommendation:** **(a)** — this is a clean, self-contained, fully-tested deliverable; a good save point.
I'll never stage the repo-root secrets or the pre-existing modified files.

---

## Q5 — (NEW, from your LOW_TREND question) Change the registry trend basis?
**Context:** the registry showed **0 LOW_TREND** because its `NEW_LOW`/`LOW_TREND` is anchored on the *cumulative
all-time* low (set in Jan-2024, never broken in an up-only market) — **0 NEW_LOW events**. A *relative* lower-low
(a pullback below the previous swing low) is a different thing — the structure tables show **153 of those**
(swing_l=3). So "trend" can be defined two ways.

**Options:**
- **(a) Keep cumulative-extreme basis** — `HIGH_TREND/LOW_TREND` only flip on all-time-territory breaks. Pro:
  matches "are we hitting genuinely new price territory?"; LOW_TREND being absent is the *correct* read of a
  2024–26 uptrend. Con: feels empty (almost always HIGH_TREND).
- **(b) Add a relative/structure basis** — drive trend off the LL/HL/HH/LH structure labels (HH+HL = high-trend,
  LH+LL = low-trend), so pullbacks and local down-legs *do* register LOW_TREND. Pro: more responsive, matches the
  ICT meaning of trend; Con: noisier, era-dependent, and it's a *different* definition than the registry's.
- **(c) Keep both, side by side** — registry keeps cumulative trend; structure tables already carry the relative
  one. Document that they answer different questions.

**Baby paragraph:** you noticed there was never a "low trend" in the price-range tables. That's because those
tables only call it a low trend when price makes a brand-new *all-time* low — and in a market that only went up
for 2.5 years, that never happened. But "lower lows" during normal dips *do* exist — they're in the new
structure tables. So the question is whether you want the price-range tables to react to those everyday dips too,
or to keep meaning strictly "new record low."

**My recommendation:** **(c)** — keep the two definitions distinct (cumulative = "new record territory";
structure = "everyday up/down legs"). They're both useful and answer different questions; merging them loses
information. If you want one headline trend for trading, use the **structure** one.

---

## Q6 — Structure-task follow-ups (documented, not built)
**Context:** task B built the LL/HL/HH/LH tables + IFVG + breaker + CISD detectors. Still open from your concept
dump: **OB/breaker entry placement** (immediate / middle / top of zone / wait-for-confirmation), **retrace
tuning** (price-distance vs time-bars), and **wiring these detectors into the optimizer** as searchable inputs.

**Options:**
- **(a) Plan the next pass now** — design how entry-placement + confirmation (FVG/CISD) become real entry rules.
- **(b) Park it** — tables/detectors are delivered; revisit when you want to act on them in the engine.

**Baby paragraph:** we now *detect* order blocks, breakers, inverse-FVGs and delivery shifts, and we *label* the
swing highs/lows. The next step would be turning those into actual entry decisions (where exactly to buy/sell,
and what confirms the trade). Do you want to plan that now, or stop at detection for now?

**My recommendation:** **(b)** for now — lock the definitions/tables first; design entries as a focused follow-up
once you've reviewed the tables.
