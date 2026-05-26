# Stage 1.1 — notes & decisions

Companion to `proposal.md`. The proposal is the long-form analysis; this file is the **decision page**. Mark each item below with your notes, blockers, or approval. I'll re-read this file when you say "ok done".

---

## Headline

The change is a **one-cell flip in the windowing truth table**:

| anchor.signal | scanned candle state | stage1.0 action | stage1.1 action |
|---|---|---|---|
| `long`  | `long`  | discard, re-anchor | **EMIT (long→long), re-anchor**  |
| `short` | `short` | discard, re-anchor | **EMIT (short→short), re-anchor** |

Everything else is preserved. New rule is a **strict superset** of the old (every reverse window is also a next window). Means we can keep both subprojects in the tree without contradiction.

### Your notes on the headline

>>>

<<<

---

## Proposed restructure (quick view)

```
subprojects/signals/
├── generate_stage1.py                    ← unchanged Stage 1 producer
├── signals_*.csv                         ← unchanged Stage 1 outputs
├── stage1.0-reverse-signals/             ← rename of current stage2/
└── stage1.1-next-signal/                 ← NEW clone with rule patched
```

Stage 1 itself is **not** cloned — both variants read the same `signals_full.csv` etc.

### Your notes on the restructure

>>>

<<<

---

## Key call-outs to weigh in on

### 1. Naming feels slightly off

"Stage 1.1" labels the variant as a Stage-1 change, but the rule that's changing lives in the windowing layer (current `stage2/`). Stage 1 itself is unchanged.

Options:
- Keep your naming as-is (`stage1.0-reverse-signals`, `stage1.1-next-signal`) — clear story, slightly misnamed.
- Rename to reflect the actual layer (`windows-1.0-reverse`, `windows-1.1-next` or similar).
- [x] Drop the version numbers entirely (`reverse_signals/`, `next_signals/`).

>>>

<<<

### 2. Schema invariant changes

`first_signal != last_signal` was always true in stage1.0. In stage1.1 it's no longer true (same-direction windows have `first_signal == last_signal`). No code outside the subproject is known to depend on this — but if any analysis assumed "endpoints are always opposite", it would silently drift.

>>> fix it accoridng to each project

<<<

### 3. By-direction split goes from 2 files to 4

stage1.0 emits two split files:
- `long_to_short_*.csv`
- `short_to_long_*.csv`

stage1.1 needs four:
- `long_to_long_*.csv`
- `long_to_short_*.csv`
- `short_to_long_*.csv`
- `short_to_short_*.csv`

>>> aproved

<<<

### 4. Expected row count (educated guess)

stage1.0 full preset = 372 windows. stage1.1 will be **≥ 372**, likely materially more, because every same-direction sequence that stage1.0 swallowed now emits one or more windows. Exact count is unknown until the generator runs.

>>> aproved

<<<

---

## Open questions from the proposal (Q1–Q8) — answer here or in `proposal.md`

If you'd rather have all answers in one file, use these blocks; I'll merge.

### Q1 — Nest under `signals/` or lift to a peer dir?

>>> all under signals with clear naming system

<<<

### Q2 — Python slug for the dotted name (`stage1_0_reverse_signals` vs `reverse_signals` vs other)

>>> reverse singalnes snd net signals 

<<<

### Q3 — Confirm rename-only of existing `stage2/` (no content edits, 36 tests pass untouched)

>>> aproved

<<<

### Q4 — Keep stage1.1's 21-column schema + direction-aware tp/sl?

>>> sure

<<<

### Q5 — Output filename for stage1.1 (`next_signals_{preset}.csv` recommended)

>>> aproved

<<<

### Q6 — Confirm 4-way direction split naming for stage1.1

>>> aproved

<<<

### Q7 — Stage 1.1 dashboard: own clone / shared with picker / no dashboard yet

>>> own clone

<<<

### Q8 — Anything else to add or veto before move-plan

>>> nop

<<<

---

## Approval

Mark one when ready:

- [ ] Approved — execute the proposal as written.
- [x] Approved with the changes I noted above.
- [ ] Not yet — see notes; iterate.

>>>

<<<
