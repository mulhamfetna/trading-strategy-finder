# Multi-timeframe layer fusion (primary + secondary) — design

**Date:** 2026-06-30
**Status:** approved (design) — pending implementation plan
**Related:** `optimize/l2/logbook.py` (`run_causal`), `optimize/l2/engine.py` (`run_l2`, `l1_priority`,
force-close, `l2_gate_components`), `optimize/l2/payload.py` (`build_view_payload`, `run_l1_cached`,
`_run_causal_memo`, profiles), `optimize/l2/dataset.py`, `server.py` (`/api/causal_backtest`,
`/api/combined_config`), `frontend/dashboard.html` (L2 settings group, `run()`), `optimize/instruments.py`,
`optimize/timeframes.py` (`TF`).

## 1. Goal

Trade **two timeframes of the same instrument at once**, each with its **own profile**, where one timeframe is
**primary** and the other is **secondary**. Concretely: run **1h as primary**; on the bars where the primary
produces **no entry** (and is flat), let the **4h secondary** take the trade per its own profile. Net effect:
"I'm on both 1h and 4h signals, 1h has priority, 4h fills the gaps."

This is **not** today's L2 (which manages L1's *dropped* veto/vol-gate signals on the **same** frame). It is a
new, **opt-in** capability: the second layer becomes an **independent strategy on its own timeframe**, fused
with the primary under primary-priority arbitration.

## 2. Decisions (locked in brainstorming)

| # | Decision | Choice |
|---|---|---|
| 1 | Per-layer **stock**? | **No** — same instrument both layers. Per-layer applies to **timeframe** only. |
| 2 | Conflict when secondary holds and primary fires | **Primary preempts** — force-close the secondary, primary takes over (reuse existing `l1_priority + force-close`). |
| 3 | What makes the secondary fire | **Its own full profile** on its own timeframe's box signal (vol-gate / indicator confirm-veto / breaker / flip / cap), gated to "primary is flat". |
| 4 | Relationship to today's L2 | **Additive new mode.** Default stays `residual (same frame)` → golden untouched; new `independent timeframe` mode is opt-in. |
| 5 | Position model | **Single shared position, 1 contract**, owner-arbitrated (primary or secondary, never both at once). "On both" = *eligible* on both; primary wins. **Not** two simultaneous positions. |

## 3. Semantics

- **Primary layer (L1):** the instrument's box strategy on the **primary timeframe** (the main timeframe
  selector), running its full profile. Behaves exactly as L1 does today.
- **Secondary layer (L2), `independent timeframe` mode:** the *same instrument's* box strategy on the
  **secondary timeframe**, running its own full profile. It is **eligible to enter only on master-grid bars
  where the primary holds no position** (primary flat = not in a trade and not entering this bar).
- **Arbitration (single position, primary priority):**
  - Primary flat + secondary signal passes its profile ⇒ **secondary enters** (owner = L2).
  - Primary signal fires while flat ⇒ **primary enters** (owner = L1).
  - Primary signal fires while **secondary holds** ⇒ **force-close secondary at that bar**, primary enters
    (owner flips L2→L1). This is the existing oracle behavior.
  - Secondary signal fires while **primary holds** ⇒ **ignored** (primary keeps the position).
- **Exits:** each layer's trade exits on its **own** profile's SL/TP/cap/breaker rules, except the
  force-close above.

## 4. Master grid & alignment

- The two layers decide on different bar cadences (e.g. 1h vs 4h). Arbitration and the per-candle log run on a
  **master grid = the finer of the two timeframes**.
- The coarser layer's decisions are **aligned onto the master grid** at the master bar whose timestamp matches
  the coarser bar's decision close (a 4h decision lands on the corresponding 1h boundary; it persists/holds per
  its own trade until its own exit).
- Rationale: the finer grid can represent both layers' decision instants without loss; the engine already
  computes decisions on the 1-minute frame and projects to timeframe bars, so both layers share a common
  absolute (epoch) time axis to align on.
- **Edge case (secondary finer than primary):** the UI does not constrain which timeframe is primary vs
  secondary, so the master grid is always computed as the finer of the two — the design is symmetric in
  cadence; "primary/secondary" governs *priority*, not *which is finer*.

## 5. Engine design

- **New fusion entry point** (e.g. `engine.run_dual_tf(primary, secondary)` or `run_l2(..., mode=)`), so that
  **`run_l2`'s existing residual path is byte-for-byte unchanged** for the default mode.
- Steps:
  1. Run **primary** as a standalone L1 via `run_l1_cached(primary_tf, params=primary_profile, instrument)`.
  2. Run **secondary** as a standalone L1 via `run_l1_cached(secondary_tf, params=secondary_profile,
     instrument)` → its candidate entries/exits on the secondary grid.
  3. Build the **master grid** (finer tf's decision dates). Project both layers' positions onto it by epoch
     time. Walk the grid applying the §3 arbitration; emit `LogRow`s with `position_owner` ∈ {L1, L2} exactly
     as `run_causal` does today.
- **Reuse:** `position_owner`, the per-layer equity/drawdown write-back, and `force-close` logic already exist
  in `run_causal`/`engine.run_l2`; the new path differs only in that the **secondary's candidate set comes from
  its own timeframe's box signals**, not from `l1.dropped_signals`.

## 6. Backend / API

- `run_causal(l1_params, l2_params, tf, instrument, *, l2_mode="residual", l2_tf=None)`:
  - `l2_mode="residual"` (default) ⇒ current behavior, unchanged, `l2_tf` ignored.
  - `l2_mode="independent"` ⇒ new fusion; `l2_tf` is the secondary timeframe (defaults to `tf` if omitted,
    which degenerates to "two same-tf strategies, primary priority").
- `build_view_payload(..., l2_mode=, l2_tf=)` threads both through; memo keys include `(l2_mode, l2_tf)`.
- `/api/causal_backtest` body gains `l2_mode` and `l2_tf`. **Omitting them ⇒ byte-identical to today.** Bad
  `l2_tf` (not in `_TF_SET`) ⇒ HTTP 400, consistent with the existing instrument/tf validation.
- **View tabs:** `l1` = primary alone · `l2` = the secondary's standalone run (for inspection) · `combined` =
  the fused result.

## 7. Dashboard UI

- **Timeframe is per-layer:** the **primary timeframe** selector lives in the **L1 settings pane**
  ("Timeframe (primary)"); the **secondary timeframe** lives in the **L2 settings pane** ("Timeframe
  (secondary)"), shown only in `independent` mode (in residual mode L2 inherits L1's frame).
- The **L2 settings group** gains a **Mode** selector: `Residual (same frame)` (default) | `Independent timeframe`.
- The top **Market group** keeps only the **stock** (shared by both layers, per decision #1) — the timeframe is
  no longer global.
- **Default page state:** the dashboard opens in the measured baseline — instrument **ES**, **primary 1h**
  (L1 = the 1h champion), **L2 mode = independent**, **secondary 4h** (L2 = the 4h champion). In independent
  mode the L2 layer auto-loads the **secondary timeframe's champion** (`loadL2Secondary`), so a fresh load +
  Run reproduces the ES 1h+4h fusion (**$71,800** combined, 264 trades) with **zero manual changes**.
  Switching the instrument to NQ gives the NQ 1h+4h fusion ($173,789). Switching L2 mode to residual restores
  the same-frame L2 default.
- `run()` threads `l2_mode` + `l2_tf` into the L2/combined requests. Default mode sends nothing new.

## 8. Profiles

- No schema change. The secondary uses any L2 profile (full layer params), including the ES champions added to
  `profiles/l2_profiles.json`. The primary uses any L1 profile. Each layer is independently selectable.

## 9. Safety & testing

- **Golden:** default mode (`residual`) is byte-identical ⇒ `perf/check_golden.py` 6-TF unchanged.
- **New-mode tests:**
  - secondary disabled (or no secondary signals) ⇒ combined == primary-alone.
  - L2 tab (secondary standalone) == a direct `run_l1_cached(secondary_tf, secondary_profile)` run.
  - preemption: a constructed case where primary fires during a secondary trade force-closes it at the right
    bar with the right P/L.
  - master-grid alignment: a coarse-secondary decision lands on the correct fine-primary bar by epoch time.
- **UI:** Playwright covers the Mode selector, the revealed L2-timeframe dropdown, and a 1h+4h fused run.

## 10. Out of scope (YAGNI)

- Per-layer **instrument** (cross-stock fusion) — explicitly deferred (decision #1).
- More than two layers.
- Two simultaneous positions / multi-contract portfolios (decision #5).
- Optimizing the secondary timeframe jointly with the primary — this spec is the **backtester/dashboard**
  capability; a joint multi-tf optimizer is a separate future effort.
