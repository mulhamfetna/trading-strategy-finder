# Issue #6 — Turn on the automatic code checker (CI) · **CLOSED**

**Date closed:** 2026-07-29 · **Status:** done and verified

---

## 1. What this was about, in plain language

Every time we change the code, we want a robot to check it before the change is allowed into the
"final, verified" copy of the project. That robot is called **CI** (continuous integration). It runs
three checks:

1. **Does the code still parse?** (no broken typing, no half-finished edits)
2. **Does the engine still load?** (nothing renamed or deleted that something else needed)
3. **Do the fast/accelerated calculations still give exactly the same answers as the slow, trusted
   originals?** (185 checks — this is the one that catches silent maths damage)

## 2. What was actually wrong

The robot **was already running** — it had been switched on and was passing on every recent change.

But **nothing forced anyone to listen to it.** The robot could shout "this is broken!" and the change
could still be merged into `main` — the branch our own rules describe as *"final, verified versions
only."* The check existed; the enforcement did not.

An earlier note of mine said the setting read `required_status_checks: none`. That was slightly wrong:
the setting was **missing entirely**. Same practical effect.

## 3. What changed

All three checks are now **required**. A red robot blocks the merge. Verified by reading the setting
back from GitHub afterwards rather than trusting that the write worked:

```json
{ "strict": true,
  "contexts": [ "Byte-compile the engine tree (syntax)",
                "Import smoke-test the core engine (imports / interfaces)",
                "Accelerator parity (data-free)" ],
  "pr_reviews": 0, "enforce_admins": false, "force_push": false }
```

**Deliberately left alone:**

| setting | left as | why |
|---|---|---|
| `enforce_admins` | **off** | you keep an emergency override. Turning it on would lock you out of your own project in a crisis. |
| approvals required | **0** | changes still go through a pull request, but a solo maintainer shouldn't have to formally approve their own work. |
| force-push / delete branch | **blocked** | unchanged, already correct. |

## 4. ⚠️ What green CI does NOT mean

**It does not mean "verified."** The robot never sees the price data — that lives only on the server and
is deliberately kept out of the code repository. So CI cannot run:

- the **golden gate** (the trade-by-trade fingerprint check across 6 timeframes),
- the real-data speed/accuracy sweep across 486,969 bars,
- the 2-second-per-indicator budget scan.

Those still run on the server before anything reaches `main`. **Green CI means "nothing is obviously
broken", not "this is correct."**

## 5. What went well / what went wrong

- **Went well:** the fix was one setting; the risky parts (locking yourself out, removing the
  pull-request rule) were consciously *not* touched; the result was read back from the source of truth
  instead of assumed.
- **Went wrong:** this sat open for a week labelled "blocked" when the blocker (a missing permission)
  had already been resolved — **the label outlived the problem.** Same lesson as #2: a status written
  once and never re-checked becomes misinformation.
