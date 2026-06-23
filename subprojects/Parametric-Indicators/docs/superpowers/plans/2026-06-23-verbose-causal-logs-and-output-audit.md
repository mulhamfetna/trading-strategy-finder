# Verbose Causal Logs + Output-Calculation Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the per-candle causal log fully verbose — every `LogRow` field populated, serialized, shown on the dashboard, and exported to CSV — and make every displayed box derive from the log (single source of truth), correcting any miscalculated box.

**Architecture:** The causal log (one `LogRow` per decision bar, from `logbook.run_causal`) becomes the single source of truth. L1's engine result is enriched to surface per-bar indicator votes and breaker-skipped would-be P/L; `run_causal` populates the 4 deferred fields; serialization + CSV emit all 23 fields; the dashboard renders them all; and the legacy engine-derived summary path is converted to log-first (or retired). Numbers that change under correct log-derivation are re-locked in the parity anchors + golden baseline.

**Tech Stack:** Python 3 (numpy, pandas, dataclasses), stdlib `http.server` backend, vanilla-JS dashboard (`frontend/dashboard.html`), pytest.

## Global Constraints

- **Log = single source of truth.** Every displayed box on every endpoint derives from the per-candle log via `aggregate.*`. No box reads `l1.ledger`/`l2.ledger` directly for display.
- **Corrected numbers win + re-lock.** A box whose corrected log-derived value differs from today's locked number → update parity anchors (`optimize/l2/test_parity_anchor.py`, `optimize/l2/test_aggregate.py`) AND golden (`perf/golden/*.json` via `perf/capture_golden.py`); document before→after.
- **No entry/exit logic change.** Section 1 only *records* what the engine already decides. Existing populated fields keep identical values.
- **Parity gates that must stay green (or be deliberately re-locked):** `python3 perf/check_golden.py`, `python3 optimize/test_fast_parity.py 4h`, `pytest optimize/l2/test_parity_anchor.py optimize/l2/test_aggregate.py`.
- **Per-decision-bar granularity:** the log has ~2,119 rows for 4h (not per-minute) — per-bar `indicators` detail is cheap.
- **Bundles deferred:** update `shareable/*` in a follow-up after main lands (Task 9 notes it; don't block).

---

## File Structure

- `optimize/l2/l1_runner.py` — **modify**: add `votes_by_bar` + `skipped_would_be` to `L1Result` and populate them in `run_l1`.
- `optimize/l2/logbook.py` — **modify**: populate `text, indicators, veto_flip, would_be_pnl` per row in `run_causal`; add a small `_vote_chips`/`_row_text` helper.
- `optimize/l2/payload.py` — **modify**: `_serialize_log_row` emits all 23 fields; convert `build_combined_payload` to log-first (or retire with Task 6's finding).
- `optimize/l2/aggregate.py` — **modify**: `_CSV_COLS` + `log_to_csv` emit all 23 columns incl. JSON `indicators`.
- `frontend/dashboard.html` — **modify**: wide all-column per-candle log table + vote chips + horizontal scroll; ledger gains entry/exit price.
- `optimize/l2/test_logbook.py`, `optimize/l2/test_payload.py`, `optimize/l2/test_aggregate.py`, `optimize/l2/test_l2_server.py` — **modify/add**: assertions for populated fields + 23-column CSV.
- `docs/LOG_FIELDS.md` (or similar) — **create**: the lost-info diff report vs tag `approved-4h-indicators-backtester`.

---

## Task 1: Surface per-bar votes + skipped would-be P/L on L1Result

**Files:**
- Modify: `optimize/l2/l1_runner.py` (`L1Result` dataclass ~line 91-112; `run_l1` ~line 146-177)
- Test: `optimize/l2/test_logbook.py` (new test function)

**Interfaces:**
- Produces: `L1Result.votes_by_bar: list[list[dict]]` — length `n`; `votes_by_bar[i]` = `[{"key": str, "vote": "long"|"short"|"veto"|"none", "active": bool}, ...]` for every enabled indicator at bar `i`. `L1Result.skipped_would_be: dict[int, float]` — `{bar_idx: would_be_pnl}` for breaker-skipped candidate bars.
- Consumed by: Task 2 (`run_causal`).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_logbook.py
def test_l1result_exposes_votes_and_skipped_would_be():
    import sys; from pathlib import Path
    _PI = Path(__file__).resolve().parents[2]
    if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
    from optimize.l2 import payload
    l1 = payload.run_l1_cached("4h", use_disk=False)
    n = len(l1.df_dec)
    assert hasattr(l1, "votes_by_bar") and len(l1.votes_by_bar) == n
    # at least one bar carries a vote with the expected shape
    nonempty = [v for v in l1.votes_by_bar if v]
    assert nonempty, "no per-bar votes recorded"
    chip = nonempty[0][0]
    assert set(chip) == {"key", "vote", "active"} and chip["vote"] in ("long", "short", "veto", "none")
    assert isinstance(l1.skipped_would_be, dict)
```

- [ ] **Step 2: Run it — expect FAIL** (`AttributeError: 'L1Result' object has no attribute 'votes_by_bar'`)

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_l1result_exposes_votes_and_skipped_would_be -v`

- [ ] **Step 3: Add the two fields to the `L1Result` dataclass**

In `optimize/l2/l1_runner.py`, after `n_locks: int = 0` (~line 112):

```python
    votes_by_bar: list = field(default_factory=list)   # per-bar [{key,vote,active}] for every enabled indicator
    skipped_would_be: dict = field(default_factory=dict)  # {bar_idx: would_be_pnl} for breaker-skipped candidates
```

(Ensure `from dataclasses import field` is imported — it already is if other fields use `field`.)

- [ ] **Step 4: Build `votes_by_bar` from the already-computed `votes` in `run_l1`**

`run_l1` already computes `votes = runner.compute_votes(df_dec, box, inds, src=src)` (line 146) and discards it. Read lines 140-177 to confirm `inds` (the indicator objects) and `n` are in scope. After `cause = attribute(...)` (~line 163), add a helper-built per-bar list. Add this module-level helper near the top of `l1_runner.py`:

```python
def _votes_by_bar(votes: dict, inds, n: int) -> list:
    """Per-bar [{key,vote,active}] for every enabled indicator. votes[id(ind)] is a per-bar int array
    (+1 long / -1 short / 0 none; veto-mode indicators encode veto as their own convention — map below)."""
    out = [[] for _ in range(n)]
    enabled = [ind for ind in inds if ind.config.enabled]
    for ind in enabled:
        arr = votes.get(id(ind))
        if arr is None:
            continue
        a = list(arr)
        mode = ind.config.mode
        for i in range(min(n, len(a))):
            v = int(a[i])
            if mode == "veto":
                vote = "veto" if v != 0 else "none"
            else:
                vote = "long" if v > 0 else ("short" if v < 0 else "none")
            out[i].append({"key": ind.key, "vote": vote, "active": v != 0})
    return out
```

> NOTE for implementer: confirm the vote-int convention by reading `indicators/runner.py::_ind_vote` and the existing chip-building in `strategy.py` (search `ind-chips`/`vote`). Mirror whatever sign/veto convention they use so chips match the rich L1 view exactly. Adjust the mapping above if the convention differs.

- [ ] **Step 5: Build `skipped_would_be` from the pre-breaker candidates**

`run_l1` builds `cand` (pre-breaker candidate trades) then `taken, _skipped, _locks = apply_breaker(cand, ...)`. Each candidate dict has `entry_idx` and `pnl`. Bars where `cause[idx] == "would_enter"` are breaker-skipped. Build the map:

```python
    skipped_would_be = {int(t["entry_idx"]): float(t["pnl"]) for t in cand
                        if int(t["entry_idx"]) < len(cause) and cause[int(t["entry_idx"])] == "would_enter"}
```

> NOTE: confirm `cand` carries `pnl` and `entry_idx` (read `apply_breaker` + the candidate build ~lines 150-161). If `pnl` isn't on the pre-breaker candidate, compute it the same way the ledger does, or have `apply_breaker` return the skipped dicts. Do NOT change `taken`/breaker behaviour — read-only extraction.

- [ ] **Step 6: Pass both into the `L1Result(...)` constructor** (~line 174-177)

```python
                    n_candidates=len(cand), n_skipped_breaker=_skipped, n_locks=_locks,
                    votes_by_bar=_votes_by_bar(votes, inds, n), skipped_would_be=skipped_would_be)
```

- [ ] **Step 7: Run the test — expect PASS**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_l1result_exposes_votes_and_skipped_would_be -v`

- [ ] **Step 8: Guard parity — L1Result is pickled to the disk cache; bump the cache version**

In `optimize/l2/payload.py`, bump `_L1_CACHE_VER` (e.g. `"v2-vf_seed"` → `"v3-votes"`) so old-schema pickles aren't loaded with the new fields defaulted.

- [ ] **Step 9: Run golden + parity — must still MATCH (read-only additions)**

Run: `python3 perf/check_golden.py 4h && python3 -m pytest optimize/l2/test_parity_anchor.py -q`
Expected: golden ✅ ALL MATCH; anchors pass.

- [ ] **Step 10: Commit**

```bash
git add optimize/l2/l1_runner.py optimize/l2/payload.py optimize/l2/test_logbook.py
git commit -m "feat(l1): surface per-bar votes + breaker-skipped would-be P/L on L1Result"
```

---

## Task 2: Populate the 4 deferred fields in run_causal

**Files:**
- Modify: `optimize/l2/logbook.py` (`run_causal` loop ~line 142-189; add helpers)
- Test: `optimize/l2/test_logbook.py`

**Interfaces:**
- Consumes: `L1Result.votes_by_bar`, `L1Result.skipped_would_be` (Task 1).
- Produces: `LogRow` rows where `text, indicators, veto_flip, would_be_pnl` are populated.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_logbook.py
def test_run_causal_populates_deferred_fields():
    import sys; from pathlib import Path
    _PI = Path(__file__).resolve().parents[2]
    if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
    from optimize.l2 import payload, logbook
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    rows = res.log
    assert any(r.indicators for r in rows), "no row carries indicator votes"
    assert all(isinstance(r.text, str) and r.text for r in rows), "text not populated on every row"
    assert any(r.would_be_pnl is not None for r in rows if r.event_type == "SKIP") or \
           not any(r.event_type == "SKIP" for r in rows), "SKIP rows missing would_be_pnl"
    # veto_flip true only where the entered direction reverses the box signal
    for r in rows:
        if r.decision == "entry" and r.box_dir and r.direction:
            assert r.veto_flip == (r.direction != r.box_dir)
```

- [ ] **Step 2: Run it — expect FAIL** (`AssertionError: no row carries indicator votes`)

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_run_causal_populates_deferred_fields -v`

- [ ] **Step 3: Add row-text + veto-flip helpers to `logbook.py`** (module level)

```python
def _row_text(r_layer, decision, reason, direction, box_dir, exit_reason, pnl) -> str:
    if decision == "entry":
        flip = " (reversed)" if (box_dir and direction and direction != box_dir) else ""
        return f"{r_layer} ENTER {direction}{flip} → {exit_reason} {pnl:+.0f}"
    return f"no-entry: {reason}"

def _veto_flip(direction, box_dir) -> bool:
    return bool(direction and box_dir and direction != box_dir)
```

- [ ] **Step 4: Populate the fields at each `LogRow(...)` construction site**

In `run_causal`, read `l1.votes_by_bar` / `l1.skipped_would_be` into locals before the loop:

```python
    votes_by_bar = getattr(l1, "votes_by_bar", None) or [[] for _ in range(n)]
    skipped_wb = getattr(l1, "skipped_would_be", {}) or {}
```

Then on the **L1 entry** row (line 148) add:
```python
                              veto_flip=_veto_flip(t1["direction"], box_dir),
                              indicators=votes_by_bar[i],
                              text=_row_text("L1","entry","entered",t1["direction"],box_dir,t1["exit_reason"],float(t1["pnl"])),
```
On the **L2 entry** row (line 154) add the same three with `t2` and `"L2"`.
On the **nonentry** row (line 170) add:
```python
                              indicators=votes_by_bar[i],
                              would_be_pnl=skipped_wb.get(i),
                              text=_row_text(owner,"nonentry",reason,None,box_dir,None,0.0),
```

> NOTE: keep all existing kwargs unchanged — only ADD these. The numeric fields (pnl/equity/dd) and the equity-booking loop at lines 173-189 are untouched.

- [ ] **Step 5: Run the test — expect PASS**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_run_causal_populates_deferred_fields -v`

- [ ] **Step 6: Golden + parity unchanged**

Run: `python3 perf/check_golden.py 4h && python3 -m pytest optimize/l2/test_parity_anchor.py optimize/l2/test_aggregate.py -q`
Expected: golden ✅ ALL MATCH; anchors pass (no numeric field changed).

- [ ] **Step 7: Commit**

```bash
git add optimize/l2/logbook.py optimize/l2/test_logbook.py
git commit -m "feat(log): populate text/indicators/veto_flip/would_be_pnl in run_causal"
```

---

## Task 3: Serialize all 23 fields to the frontend

**Files:**
- Modify: `optimize/l2/payload.py` (`_serialize_log_row` ~line 432-438)
- Test: `optimize/l2/test_payload.py`

**Interfaces:**
- Produces: the `D.log[]` rows the dashboard reads now carry all 23 keys (adds `entry_price, exit_price, text, veto_flip, would_be_pnl, indicators`).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_payload.py
def test_serialize_log_row_has_all_fields():
    import sys; from pathlib import Path
    _PI = Path(__file__).resolve().parents[2]
    if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
    from optimize.l2 import payload, logbook
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    row = payload._serialize_log_row(res.log[0])
    for k in ("i","time","layer","decision","reason","box_cause","event_type","direction","box_dir",
              "entry_price","exit_time","exit_price","exit_reason","pnl","equity","dd","in_position",
              "position_owner","l2_reason","text","veto_flip","would_be_pnl","indicators"):
        assert k in row, f"missing {k}"
```

- [ ] **Step 2: Run it — expect FAIL** (`missing entry_price`)

Run: `python3 -m pytest optimize/l2/test_payload.py::test_serialize_log_row_has_all_fields -v`

- [ ] **Step 3: Extend `_serialize_log_row`**

```python
def _serialize_log_row(r) -> dict:
    """Full per-candle log row for the dashboard table + CSV (all LogRow fields)."""
    return {"i": r.i, "time": r.time, "layer": r.layer, "decision": r.decision, "reason": r.reason,
            "box_cause": r.box_cause, "event_type": r.event_type, "direction": r.direction,
            "box_dir": r.box_dir, "entry_price": r.entry_price, "exit_time": r.exit_time,
            "exit_price": r.exit_price, "exit_reason": r.exit_reason, "pnl": round(r.pnl, 2),
            "equity": r.equity, "dd": r.dd, "in_position": r.in_position,
            "position_owner": r.position_owner, "l2_reason": r.l2_reason,
            "text": r.text, "veto_flip": r.veto_flip, "would_be_pnl": r.would_be_pnl,
            "indicators": r.indicators}
```

- [ ] **Step 4: Run the test — expect PASS**

Run: `python3 -m pytest optimize/l2/test_payload.py::test_serialize_log_row_has_all_fields -v`

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_payload.py
git commit -m "feat(payload): serialize all 23 log-row fields to the frontend"
```

---

## Task 4: CSV export — all 23 columns incl. JSON indicators

**Files:**
- Modify: `optimize/l2/aggregate.py` (`_CSV_COLS` ~line 214; `log_to_csv` ~line 219-)
- Test: `optimize/l2/test_aggregate.py`

**Interfaces:**
- Produces: `log_to_csv(log)` emits a header with all 23 columns; `indicators` is JSON-encoded.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_aggregate.py
def test_csv_has_all_columns_and_json_indicators():
    import json as _json, sys; from pathlib import Path
    _PI = Path(__file__).resolve().parents[2]
    if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
    from optimize.l2 import payload, logbook, aggregate
    res = logbook.run_causal(payload.l1_default_params("4h"), payload.l2_default_params(), "4h")
    log = [payload._serialize_log_row(r) for r in res.log]
    csv = aggregate.log_to_csv(log)
    header = [c for c in csv.split("\n") if not c.startswith("#")][0].split(",")
    for col in ("entry_price","exit_price","text","veto_flip","would_be_pnl","indicators"):
        assert col in header, f"CSV missing {col}"
    # an indicators cell parses back as JSON list
    import csv as _csv, io
    rows = list(_csv.DictReader(io.StringIO("\n".join(l for l in csv.split("\n") if not l.startswith("#")))))
    ind_cells = [r["indicators"] for r in rows if r["indicators"]]
    assert ind_cells and isinstance(_json.loads(ind_cells[0]), list)
```

- [ ] **Step 2: Run it — expect FAIL** (`CSV missing text`)

Run: `python3 -m pytest optimize/l2/test_aggregate.py::test_csv_has_all_columns_and_json_indicators -v`

- [ ] **Step 3: Extend `_CSV_COLS` and JSON-encode `indicators` in `log_to_csv`**

Read `aggregate.py:214-222`. Set the column list to the full 23 (keep `datetime` if currently derived), appending the new ones, with `indicators` last:

```python
_CSV_COLS = ["i", "time", "datetime", "layer", "decision", "reason", "box_cause", "event_type",
             "direction", "box_dir", "veto_flip", "entry_price", "exit_time", "exit_price",
             "exit_reason", "would_be_pnl", "pnl", "equity", "dd", "in_position", "position_owner",
             "l2_reason", "text", "indicators"]
```

In `log_to_csv`, when writing each cell, JSON-encode the `indicators` value:

```python
import json
# inside the row-building loop, for the indicators column:
val = row.get(col)
if col == "indicators":
    val = json.dumps(val or [])
```

> NOTE: read the existing `log_to_csv` cell-writing loop and follow its exact escaping/quoting (it likely uses `csv.writer`, which will quote the JSON cell automatically). Keep the provenance `#`-comment header untouched.

- [ ] **Step 4: Run the test — expect PASS**

Run: `python3 -m pytest optimize/l2/test_aggregate.py::test_csv_has_all_columns_and_json_indicators -v`

- [ ] **Step 5: Update the existing CSV-shape assertion in `test_l2_server.py`**

Read `optimize/l2/test_l2_server.py` (the `causal_log.csv` test ~line 57). Update its expected column set to the 23-column header. Run: `python3 -m pytest optimize/l2/test_l2_server.py -q` → PASS.

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/aggregate.py optimize/l2/test_aggregate.py optimize/l2/test_l2_server.py
git commit -m "feat(csv): export all 23 log columns incl. JSON-encoded per-bar indicators"
```

---

## Task 5: Dashboard — wide all-column log + vote chips + ledger prices

**Files:**
- Modify: `frontend/dashboard.html` (`renderView`: `lcols` ~line 366-373, `cols` ledger ~line 354-363; add a `.logwrap{overflow-x:auto}` style)
- Test: manual (Playwright) — see Step 5

**Interfaces:**
- Consumes: the full serialized rows from Task 3.

- [ ] **Step 1: Widen the per-candle log column list**

Replace the `lcols` array (~line 367) with all columns; render `indicators` as chips. Example:

```javascript
const lcols=[['i','#','l'],['time','time','l'],['layer','src','l'],['decision','decision','l'],
  ['reason','reason','l'],['box_cause','box cause','l'],['event_type','event','l'],
  ['direction','dir','l'],['box_dir','box dir','l'],['veto_flip','flip','l'],
  ['entry_price','entry $','r'],['exit_time','exit','l'],['exit_price','exit $','r'],
  ['exit_reason','exit reason','l'],['would_be_pnl','would-be','r'],['pnl','P/L','r'],
  ['equity','equity','r'],['dd','dd','r'],['in_position','pos','l'],
  ['position_owner','owner','l'],['l2_reason','l2 reason','l'],['indicators','indicators','l']];
```

In the row-cell builder, special-case `time`/`exit_time` (format via `DB.dt`), numeric `r` cells (round/locale), `veto_flip`/`in_position` (render `⇄`/`✓` or blank), and `indicators` (chips):

```javascript
if(c[0]==='indicators') return `<td class="l"><span class="ind-chips">`+
  (Array.isArray(v)?v:[]).map(x=>`<span class="chip ${x.vote} ${x.active?'':'off'}" title="${x.key}:${x.vote}">${x.key}:${(x.vote||'')[0]||''}</span>`).join('')+`</span></td>`;
```

> NOTE: reuse the EXACT chip markup already used in the event log (search `ind-chips` in `renderView` ~line 344) so styling is consistent.

- [ ] **Step 2: Wrap the log table for horizontal scroll**

Add `.logwrap{overflow-x:auto;}` to the `<style>` block and ensure the per-candle log `<table id="logtbl">` is inside a `<div class="logwrap">` (add the wrapper in the HTML if not present).

- [ ] **Step 3: Add entry/exit price to the trade ledger**

Extend the ledger `cols` (~line 354) with `['entry_price','entry $','r']` and `['exit_price','exit $','r']`, formatting numeric cells with locale rounding.

- [ ] **Step 4: Syntax-check the inline script**

Run:
```bash
python3 -c "import re;h=open('frontend/dashboard.html').read();b=max(re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',h,re.S),key=len);open('/tmp/d.js','w').write(b)"
node --check /tmp/d.js
```
Expected: no syntax error.

- [ ] **Step 5: Manual verify (Playwright, system Chrome)**

Start `python3 server.py --port 8290`, drive it headless (executablePath `/usr/bin/google-chrome-stable`), click `#run`, switch each view tab, and assert `#logtbl` has the new columns and `.ind-chips` rows render; the ledger shows `entry $`/`exit $`. Screenshot for the record.

- [ ] **Step 6: Commit**

```bash
git add -f frontend/dashboard.html
git commit -m "feat(dashboard): wide all-column per-candle log + vote chips + ledger fill prices"
```

---

## Task 6: Audit — make build_combined_payload log-first (or retire)

**Files:**
- Investigate then Modify: `optimize/l2/payload.py` (`build_combined_payload` ~line 367-407), `server.py` (`/api/combined_backtest` ~line 253-258), possibly delete `frontend/combined.html`
- Test: `optimize/l2/test_l2_server.py`

- [ ] **Step 1: Determine reachability**

Run:
```bash
grep -rn "combined_backtest\|combined.html" frontend/ server.py
ls frontend/combined.html 2>/dev/null && echo "combined.html present" || echo "absent"
```
Decide: is `/api/combined_backtest` reached by any live frontend? (The unified dashboard uses `/api/causal_backtest`.) Record the finding in the commit message.

- [ ] **Step 2a (if DEAD): retire it**

Delete the `build_combined_payload` function, the `/api/combined_backtest` route block in `server.py`, and `frontend/combined.html` (delete tracked HTML with `git rm`). Keep `metrics.score`/`metrics.combined`/`_l1_full_summary` only if still referenced by tests; otherwise move them under a clearly-named test-helper.

- [ ] **Step 2b (if LIVE): convert to log-first**

Rewrite `build_combined_payload` to build the same response shape but source `meta.summary` from the log: call `_run_causal_memo(l1p, l2p, tf)` then `aggregate.boxes_for_layer(res,"L1",bar_secs)`, `aggregate.boxes_for_layer(res,"L2",bar_secs)`, `aggregate.combined_boxes(res,bar_secs)`. Map those into the `summary.l1/l2/combined` keys the endpoint promised. Demote `_l1_full_summary`/`metrics.score`/`metrics.combined` to test-oracle-only (leave them importable for parity tests; remove from the display path).

- [ ] **Step 3: Test the endpoint still serves a valid payload (or is gone)**

If retired: add/keep a test asserting `/api/combined_backtest` returns 404 (or remove its test). If converted: assert `out["meta"]["summary"]["combined"]["pnl"]` equals the log-derived `combined_boxes` pnl.

Run: `python3 -m pytest optimize/l2/test_l2_server.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add optimize/l2/payload.py server.py optimize/l2/test_l2_server.py
git commit -m "refactor(audit): make every displayed box log-first (combined endpoint <retired|converted>)"
```

---

## Task 7: Per-box correctness pass + re-lock

**Files:**
- Investigate: `optimize/l2/aggregate.py` (`_financials`, `boxes_for_layer`, `combined_boxes`)
- Modify (only if a box is wrong): the offending function
- Modify (if any number changes): `optimize/l2/test_parity_anchor.py`, `optimize/l2/test_aggregate.py`, `perf/golden/*.json`

- [ ] **Step 1: Audit each box against the log**

For `pnl, pnl_2025/2026, max_dd, win, pf, payoff, exposure, n_taken, n_candidates, n_locks` and the streak/total boxes, confirm each is computed from the log entries (not an engine shortcut) and is arithmetically correct (e.g. combined `max_dd` = merged-equity underwater, not a sum; `pf`/`payoff` guards). Write a short scratch script that recomputes each from `res.log` and diffs against the box value; record any mismatch.

- [ ] **Step 2: Fix any miscalculated box**

If a box is wrong, correct its function in `aggregate.py`. Add a regression test in `test_aggregate.py` asserting the corrected formula from the log.

- [ ] **Step 3: Re-lock changed numbers**

For each box whose corrected value differs from the locked anchor: update `test_parity_anchor.py` + `test_aggregate.py` to the corrected value, and regenerate golden:
```bash
python3 perf/capture_golden.py 4h 2h 1h 15m 5m 2m
```
Document each before→after in the report (Task 8).

- [ ] **Step 4: Full gate**

Run: `python3 perf/check_golden.py && python3 optimize/test_fast_parity.py 4h && python3 -m pytest optimize/l2/ -q`
Expected: all green (golden re-captured if Step 3 changed numbers).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/aggregate.py optimize/l2/test_aggregate.py optimize/l2/test_parity_anchor.py perf/golden
git commit -m "fix(audit): correct <box> log-derivation + re-lock anchors/golden (before→after in report)"
```

---

## Task 8: Lost-info diff report

**Files:**
- Create: `docs/LOG_FIELDS.md`

- [ ] **Step 1: Diff the tag vs now**

```bash
git show approved-4h-indicators-backtester:subprojects/Parametric-Indicators/optimize/l2/aggregate.py | grep -n "_CSV_COLS" -A4
```
Compare the tag's CSV columns + dashboard `lcols` + `_serialize_log_row` fields against current.

- [ ] **Step 2: Write the report**

Create `docs/LOG_FIELDS.md`: the full 23-field table (meaning + populated-since), a "restored vs added" section (what the tag exposed vs what was dropped vs newly added), the CSV column order, and any box re-locked in Task 7 with before→after + justification. Use embedded Mermaid for the log→serialize→CSV/dashboard flow (per project convention: Mermaid, never ASCII art).

- [ ] **Step 3: Commit**

```bash
git add docs/LOG_FIELDS.md
git commit -m "docs: LOG_FIELDS.md — full log field reference + lost-info diff vs approved tag"
```

---

## Task 9: Follow-up note — bundles

**Files:**
- Modify: the report or a tracking note

- [ ] **Step 1:** Note in `docs/LOG_FIELDS.md` that `shareable/server_agent_kit` and `shareable/two_layer_causal_backtester` carry their own `logbook.py`/`aggregate.py`/`payload.py`/`dashboard.html` copies and need the same verbose-log treatment in a follow-up; not done here to keep the main change reviewable. (No code change.)

---

## Self-Review

- **Spec coverage:** Section 1 (log enrichment) → Tasks 1-2. Section 2 (serialize + CSV) → Tasks 3-4. Section 3 (dashboard) → Task 5. Section 4 (audit + re-lock + diff report) → Tasks 6-8. Bundles deferred → Task 9. ✓ All spec sections mapped.
- **Type consistency:** `votes_by_bar: list[list[dict{key,vote,active}]]` and `skipped_would_be: dict[int,float]` defined in Task 1, consumed in Task 2; `_serialize_log_row` keys (Task 3) match the CSV `_CSV_COLS` (Task 4) and the dashboard `lcols` (Task 5). ✓
- **Placeholder scan:** the two engine-coupled steps (votes convention, candidate `pnl`) carry explicit "read these lines + confirm convention" NOTEs rather than fabricated certainty — intentional, since the exact int/veto convention must mirror existing code; all other steps have concrete code. ✓
- **Numbers-may-change** is isolated to Task 7 with explicit re-lock + documentation, honoring the locked decision.
