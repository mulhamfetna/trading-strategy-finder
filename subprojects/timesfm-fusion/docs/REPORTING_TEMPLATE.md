# Reporting system — the standard we run EVERY experiment through

This is the repeatable "reporting system" (per user request 2026-07-15): every candidate — a new model,
a new data source, a new signal — goes through the **same five staged docs + a verdict**, then we
proceed to the next. It exists because it already caught a seductive n=1 artifact (TimesFM) before it
shipped. Copy this structure into a per-candidate folder: `docs/<candidate>/{PRIOR_ART,REPRO,DUMB_CONTROL,ROBUSTNESS}.md`.

## The five stages (do them in order; stop early on a NO-GO)

1. **PRIOR_ART.md — deep-research first** (mandatory, per SOP).
   What is it, license/access (can we use it legally/commercially?), how it produces the signal, published
   evidence for/against, known pitfalls. End with a **go/no-go to *test*** (not to deploy).

2. **REPRO.md — establish the baseline.**
   If someone claims a number, reproduce it *to the dollar* from their artifacts before believing it. If
   there's no prior claim, establish the honest baseline on our own data. Prove causality (no look-ahead).

3. **DUMB_CONTROL.md — beat the stupidest alternative.**
   Compare the fancy thing against the cheapest sensible proxy (ATR/realized-vol for a vol signal; a
   constant/random/last-value for a forecast; a coin-flip for a direction call). **Steelman the dumb
   control** (give it its best hyperparameter, in-sample). If the fancy thing doesn't clearly win, stop.

4. **ROBUSTNESS.md — break the n=1.**
   Multi-regime (multiple years incl. a bear if data allows), purged/combinatorial cross-validation,
   block-bootstrap (P(helps)), and a **random control** (does a random action of the same size do as
   well?). Report per-sub-period. State confounds honestly. A single-window win is *not* a result.

5. **VERDICT** (in ROBUSTNESS.md or a VERDICT.md): **GO / NO-GO**, the mechanism, salvage options.

## Non-negotiable rules (from feedback memory)
- **Never a positive result without** a dumb control **and** a noise/power check.
- **Never a negative result without** a power analysis (could we even have detected the effect?).
- **Implement the criterion you actually wrote** — don't quietly swap "≠ zero" for "is negative".
- **Compute on the server**, never the local box, unless explicitly authorized.
- **Verify, don't trust** — reproduce numbers; check the fast tells (e.g. gated-DD == ungated-DD).

## Also update, per experiment
- `EXPERIMENTS_LOG.md` — one row in the timeline table + any banked discovery.
- The relevant memory (`project_*`) — verdict + the one-line reason.

## Fast tells worth checking every time
- vol/risk filter: is **gated max-DD actually lower than ungated**? If equal, it isn't touching the risk.
- "edge" concentrated in **a handful of tail trades** → fragile; quantify how few.
- stateful gates/estimators: is the state a **single instance** across the series (not re-created per item)?
- caches keyed on params-not-data: **clear them** after any data/period change.
