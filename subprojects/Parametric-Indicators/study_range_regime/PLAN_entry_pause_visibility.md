# Entry-Pause Visibility — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use `- [ ]`.

**Goal:** Make *why the system isn't entering* visible everywhere — dashboard logs every prevented entry with
its reason (incl. the currently-missing confirm<K), 4 new dashboard cards quantify the no-entry decomposition,
and the all-stocks delivery gains a holds_dropped column + a per-signal pause sidecar.

**Architecture:** A pure `pause_streaks.py` helper computes per-bar cause + longest runs from arrays.
`strategy.build_payload` calls it (additive — no change to trades/PnL ⇒ golden 6/6) to fill 4 summary fields
and emit confirm<K NOENTRY events. Frontend renders them. all-stocks adds a column + sidecar.

**Tech Stack:** numpy, the existing `strategy.py`/`indicators/runner.py`, vanilla-HTML frontend, pandas (all-stocks).
**Working dir:** `/mnt/data/projects/trading/subprojects/Parametric-Indicators/` (parts 1+3) and
`/mnt/data/projects/trading/subprojects/all-stocks-signals/` (part 2). Commits only when the user asks.

## Key facts (from code)
- `strategy.build_payload` has: `sig_arr = decision_signals(d4, box)` (±1/0), `gate` (vol-only mask `vfw≤gthr`),
  `veto_mask` (from `runner.build_layer`), `_votes` (computed once), `inds`, `ind_src`, `k_rule`, `gthr`.
  It does NOT keep a confirm mask — recompute via `runner.confirm_mask(d4, box, inds, k_rule, src=ind_src, votes=_votes)`.
- `blocked` entries `{entry_idx, signal_idx, direction, reason∈{veto,vol_gate}}` already become `NOENTRY`
  events (strategy.py ~377-395). **confirm<K candidates are dropped WITHOUT a NOENTRY event** — this plan adds them.
- `taken` recs carry `entry_time`/`exit_time` (epoch secs). `summary` built at strategy.py ~448.

---

## Task 1 — pure streak/attribution helper
**Files:** Create `optimize/pause_streaks.py`, `optimize/test_pause_streaks.py`

- [ ] **Step 1: failing test**
```python
import numpy as np
from optimize.pause_streaks import longest_run, pause_metrics

def test_longest_run():
    assert longest_run(np.array([0,1,1,0,1,1,1,0], dtype=bool)) == 3
    assert longest_run(np.array([0,0,0], dtype=bool)) == 0
    assert longest_run(np.array([1,1], dtype=bool)) == 2

def test_pause_metrics_decomposition():
    sig   = np.array([0, 1, 0, 0, 1, 1, 0], dtype=int)   # candidates at idx 1,4,5
    volg  = np.array([1, 0, 1, 1, 1, 1, 1], dtype=bool)  # idx1 vol-gated
    veto  = np.array([0, 0, 0, 0, 1, 0, 0], dtype=bool)  # idx4 vetoed
    conf  = np.array([1, 1, 1, 1, 1, 0, 1], dtype=bool)  # idx5 confirm<K (conf False)
    m = pause_metrics(sig, volg, veto, conf, bar_seconds=4*3600,
                      trade_spans=[(0,6)])               # one trade idx0->6 (6 bars)
    assert m["box_silence"]["bars"] == 2                 # idx2,3 run (idx6 is len-1 trailing single)
    assert m["gate_noentry"]["bars"] == 1                # idx1
    assert m["indicator_noentry"]["bars"] == 2           # idx4 (veto) + idx5 (confirm) consecutive
    assert m["position_hold"]["bars"] == 6
    assert "days" in m["box_silence"]
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** `optimize/pause_streaks.py`:
```python
"""Pure no-entry attribution + longest-run helpers (visibility). No engine/data deps."""
from __future__ import annotations
import numpy as np


def longest_run(mask) -> int:
    """Length of the longest run of True in a boolean array."""
    best = cur = 0
    for v in np.asarray(mask, dtype=bool):
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    return int(best)


def per_bar_cause(sig, vol_gate, veto, confirm):
    """Attribute each decision bar (priority): no_signal → vol_gated → vetoed → confirm<K → would_enter.
    Returns 4 boolean masks (box_silence, gate_block, indic_block, would_enter)."""
    sig = np.asarray(sig); cand = sig != 0
    vol_gate = np.asarray(vol_gate, dtype=bool); veto = np.asarray(veto, dtype=bool)
    confirm = np.asarray(confirm, dtype=bool)
    box_silence = ~cand
    gate_block = cand & ~vol_gate
    indic_block = cand & vol_gate & (veto | ~confirm)
    would_enter = cand & vol_gate & ~veto & confirm
    return box_silence, gate_block, indic_block, would_enter


def _dur(bars, bar_seconds):
    secs = bars * bar_seconds
    h = int(secs // 3600); d = round(secs / 86400.0, 2)
    return {"bars": int(bars), "seconds": int(secs), "hours": h, "days": d}


def pause_metrics(sig, vol_gate, veto, confirm, bar_seconds, trade_spans=None):
    """The 4 visibility metrics. trade_spans = list of (entry_idx, exit_idx) for position-hold."""
    box_silence, gate_block, indic_block, _ = per_bar_cause(sig, vol_gate, veto, confirm)
    hold_bars = max((b - a for a, b in (trade_spans or [])), default=0)
    return {"box_silence": _dur(longest_run(box_silence), bar_seconds),
            "gate_noentry": _dur(longest_run(gate_block), bar_seconds),
            "indicator_noentry": _dur(longest_run(indic_block), bar_seconds),
            "position_hold": _dur(hold_bars, bar_seconds)}
```
- [ ] **Step 4: run → pass.**

## Task 2 — wire into `strategy.build_payload` (additive; golden-safe)
**Files:** Modify `strategy.py`

- [ ] **Step 1:** just before the `summary = dict(...)` (strategy.py ~448), compute the metrics + confirm mask:
```python
    # --- entry-pause visibility (additive; does NOT touch trades/equity/PnL) ---
    from optimize import pause_streaks
    _cmask = None
    if specs and any(i.config.enabled for i in inds):
        import numpy as _np
        _cmask = _np.asarray(runner.confirm_mask(d4, box, inds, k_rule, src=ind_src, votes=_votes), dtype=bool)
    _n = len(d4)
    _sig = np.asarray([0 if s is None else (1 if s == "long" else -1 if s == "short" else int(bool(s))) for s in sig_arr][:_n]) \
        if sig_arr.dtype == object else np.asarray(sig_arr[:_n])
    _volg = (np.asarray(gate, dtype=bool)[:_n] if gate is not None else np.ones(_n, dtype=bool))
    _veto = (np.asarray(veto_mask, dtype=bool)[:_n] if veto_mask is not None else np.zeros(_n, dtype=bool))
    _conf = (_cmask[:_n] if _cmask is not None else np.ones(_n, dtype=bool))
    _dates = d4["Date"].astype("int64") // 10**9                 # epoch secs
    _bar_secs = int(np.median(np.diff(_dates.values))) if _n > 1 else 14400
    _spans = [(int(t["entry_idx"]), int(t.get("exit_idx", t["entry_idx"])))
              for t in cand if "entry_idx" in t]
    _pm = pause_streaks.pause_metrics(_sig, _volg, _veto, _conf, _bar_secs, trade_spans=_spans)
```
      NOTE: confirm the trade dict key for the exit bar index. If `cand` items lack `exit_idx`, derive span
      bars from `(exit_time-entry_time)/_bar_secs`: replace `_spans` with
      `_spans=[(0, max(1, round((_ts(t['exit_time'])-_ts(t['entry_time']))/_bar_secs))) for t in cand]`
      (only the *difference* matters for position_hold).
- [ ] **Step 2:** add the 4 metrics to the `summary` dict (after `noentry_streak_start=...`):
```python
                   box_silence=_pm["box_silence"], position_hold=_pm["position_hold"],
                   gate_noentry=_pm["gate_noentry"], indicator_noentry=_pm["indicator_noentry"])
```
- [ ] **Step 3:** emit the missing **confirm<K NOENTRY events** + a `reason` field on all three. After the
      existing `for b in blocked:` loop (~395), add:
```python
    # confirm<K NOENTRY events (the engine's blocked_log only carries veto/vol_gate) — additive, logs only.
    if _cmask is not None and gthr is not None:
        import numpy as _np
        _cand = _sig != 0
        cblk = _np.flatnonzero(_cand & _volg & ~_veto & ~_conf)
        for i in cblk:
            events.append({"time": _ts(d4["Date"].iloc[int(i)]), "type": "NOENTRY", "reason": "confirm<K",
                           "text": f"ENTRY NOT TAKEN — {'long' if _sig[i]>0 else 'short'} blocked: "
                                   f"fewer than K={k_rule} confirmers"})
```
      And tag the existing two: in the `for b in blocked:` loop set `ev["reason"] = "vetoed" if b["reason"]=="veto" else "vol_gated"`.
- [ ] **Step 4: golden** `python3 perf/check_golden.py` → 6/6 MATCH (trades/PnL untouched; only summary keys +
      NOENTRY events added). If `sig_arr` dtype handling trips parity, it won't — these are post-trade additive.
- [ ] **Step 5: champion sanity** — run the wsh4 champion via the dashboard path and print
      `payload["meta"]["summary"]["box_silence"/"gate_noentry"/"indicator_noentry"/"position_hold"]`; expect
      box_silence to dominate (consistent with diagnose_pause).

## Task 3 — frontend: reason-tagged log + 4 cards
**Files:** Modify `frontend/index.html`

- [ ] **Step 1:** the event log already renders `NOENTRY` (and now confirm<K) events. Add a CSS color for
      `.row.NOENTRY` (muted/orange) so prevented entries are visually distinct, and show the `reason` if present.
      In the event-log builder (the `D.events.map` block) the text already carries the reason; just ensure
      `NOENTRY` rows get the class (they do via `e.type`). Add `.row.NOENTRY .b{color:var(--orange)}` to CSS.
- [ ] **Step 2:** add 4 cards to the `#cards` render string (after the no-entry-streak card), each value =
      `${m.bars} candles · ${fmtDur(m.bars*barMin)}` where `barMin` = the run's bar minutes (derive from
      summary or default 240 for 4h). Use the helper:
```javascript
    + card(S.box_silence ? `${S.box_silence.bars}c · ${S.box_silence.days}d` : '—', 'longest box-silence (no box signal)')
    + card(S.position_hold ? `${S.position_hold.bars}c · ${S.position_hold.days}d` : '—', 'longest position hold (trade open)')
    + card(S.gate_noentry ? `${S.gate_noentry.bars}c · ${S.gate_noentry.days}d` : '—', 'longest gate non-entry (vol-gate blocked)')
    + card(S.indicator_noentry ? `${S.indicator_noentry.bars}c · ${S.indicator_noentry.days}d` : '—', 'longest indicator non-entry (gate-approved, indicators blocked)')
```
      (Each card's label IS its description, per the user's "both each with its description".)
- [ ] **Step 3: verify** — restart server (`fuser -k 8200/tcp; python3 server.py --port 8200 &`), run the
      champion in the browser (or curl `/api/backtest` with the champion preset), confirm the 4 cards populate
      + NOENTRY confirm<K events appear. (Reuse the e2e Playwright pattern in `tests/e2e_dashboard_inputs.py`
      for an automated check if desired.)

## Task 4 — all-stocks: holds_dropped column + pause sidecar + re-anchor parity
**Files:** Modify `subprojects/all-stocks-signals/` (the stage-2 generator + `package_delivery.py`)

- [ ] **Step 1:** locate where `2_holds_dropped` rows are produced (holds removed from `1_all_signals`). Add a
      **`holds_dropped`** integer column = count of consecutive `hold` rows in `1_all_signals` immediately
      before each kept `long`/`short` row. (Compute from the all-signals sequence: running count of holds since
      the last non-hold, attached to the next signal row.)
- [ ] **Step 2:** compute per `instrument×tf×preset`: `longest_box_pause_bars` = max consecutive `hold` run in
      `1_all_signals`; `reverse_longest_pause_bars` = max `holds_between` in `3_reverse_signals`. Convert to
      time via the TF bar duration.
- [ ] **Step 3:** write `PAUSE_SUMMARY.json` (+ a readable `.md`) per signal set, collated into each delivery
      bundle root:
```json
{"instrument":"…","tf":"…","preset":"…","holds_dropped_total":N,
 "longest_box_pause":{"bars":N,"hours":H,"days":D},
 "reverse":{"longest_pause":{"bars":N,"hours":H,"days":D}}}
```
- [ ] **Step 4: re-anchor parity** — the new `holds_dropped` column changes the `2_holds_dropped` schema, so
      the NQ byte-parity baseline (#200) no longer matches. Re-run the NQ generation, confirm the ONLY diff is
      the additive column (+ sidecar), update/re-freeze the parity anchor, and note it in the all-stocks docs.
- [ ] **Step 5: structural validation** — regenerate one instrument bundle (e.g. ES) and assert: the
      `holds_dropped` column present + non-negative + sums to (rows in all_signals − rows in holds_dropped);
      `PAUSE_SUMMARY.json` present with the 3 figures.

## Task FINAL — doc
- [ ] Write `study_range_regime/UPDATE_entry_pause_visibility.md` (verbose, Mermaid: the no-entry decomposition
      flowing to the 4 cards + the log + the all-stocks sidecar). Update `SYSTEM_UPDATES_MEGADOC.md`.

---

## Self-review
- **Spec coverage:** D1 reason-tagged log → Task 2 step 3 (confirm<K added; veto/vol_gate already logged + now
  tagged); D2 box-silence + position-hold cards → Task 3 step 2 (+ gate/indicator); D3 sidecar → Task 4 step 3;
  D4 additive/golden → Task 2 step 4; D5 parity re-anchor → Task 4 step 4. 4 streaks → Task 1/2. All covered.
- **Placeholders:** none (code in every step; the one runtime check — trade exit-idx key — has an explicit
  fallback in Task 2 step 1).
- **Type consistency:** `pause_metrics`/`per_bar_cause`/`longest_run` signatures match Task 1↔2; summary keys
  `box_silence/position_hold/gate_noentry/indicator_noentry` identical in Task 2 (backend) and Task 3 (frontend);
  each metric is `{bars,seconds,hours,days}` used consistently.
