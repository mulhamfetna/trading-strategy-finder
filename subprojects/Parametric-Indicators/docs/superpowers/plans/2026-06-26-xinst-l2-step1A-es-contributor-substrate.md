# Cross-Instrument L2 — Step 1·Part A: ES Contributor Substrate (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, fully-tested `optimize/l2/contributors/` module that loads ES candles + boxes, aligns ES to NQ decision bars causally, computes ES net state {long/short/hold} two ways (delivered touch + recomputed BoxLookup traversal), runs the existing 18-indicator committee on ES bars oriented to NQ's box direction, and emits ES confirm/veto masks for both signal encodings (directional stance+mode and the full 6-cell truth table). **Nothing is wired into `engine.run_l2`/`l2_gate_components` — that is Part B.**

**Architecture:** A small package of single-responsibility pure functions: `registry` (the `Contributor` abstraction over the `instruments.py` no-mix contract), `loader` (ES inputs), `align` (causal NQ-decision-bar alignment), `state` (touch + traversal net state), `votes` (ES committee + the two signal-voter mask builders). Every function maximally reuses the existing NQ machinery — `runner.market_context`, `runner._vote_from_1min`, `votes.stance_directions`, `library.from_specs`, `box_lookup.BoxLookup`, `optimize.signals.decision_signals` — so orientation/warm-up/collapse semantics are byte-identical to NQ's. The module produces masks shaped exactly like `engine.l2_gate_components`'s `(vol_gate, veto, confirm)` so Part B can AND/pool them with zero new conventions.

**Tech Stack:** Python 3, numpy, pandas (no new dependencies). pytest for tests. Follow the existing repo file/test patterns (`from optimize.l2 import ...`, `sys.path` insert to the subproject root).

## Global Constraints

(Copied verbatim from the spec — `docs/superpowers/specs/2026-06-26-cross-instrument-l2-state-feature-layer-design.md`. Every task's requirements implicitly include this section.)

- **Scope: L2 only; L1 untouched.** This plan adds *new* code under `optimize/l2/contributors/` and **does not modify** `engine.py`, `l1_runner.py`, `runner.py`, `library.py`, `base.py`, `votes.py`, `payload.py`, or any engine path. (Spec Decision 1.)
- **Contributors-OFF ⇒ byte-identical ⇒ golden 6/6.** "With ALL contributors disabled, the system is byte-identical to today's L2. The golden gate must still pass 6/6 (`perf/check_golden.py`). The entire contributor block is purely additive." Because Part A adds *no code path to the engine*, the golden gate is **trivially unaffected**; each mask builder is independently verified to be identity-when-disabled. (Spec §8.1, Decision 13.)
- **Causality / no look-ahead by construction.** "Alignment is causal by construction — we only ever index a bar whose close `≤` the NQ decision bar's close (last-closed). No contributor cell can encode future information." A dedicated look-ahead guard test enforces this. (Spec §8.2.)
- **Collapse to one net state per decision bar**, mirroring L1's collapse-to-one-entry-per-candle; long wins ties (matches `optimize.signals.decision_signals`). (Spec §4.2.)
- **State source is optimizer-chosen between two definitions:** (a) delivered Stage-1 touch signal, (b) recomputed BoxLookup traversal at L1 parity. Both are implemented; the two can diverge materially and that is intentional. (Spec §4.2, Decision 8.)
- **Both signal encodings implemented and searchable:** (i) directional stance+mode reusing `votes.stance_directions`; (ii) full 6-cell truth table. (Spec §5a, Decision 9.)
- **Full 18-indicator registry on the contributor's bars**, every vote **oriented to NQ's `box_dir`** so `+1` always means "agrees with the NQ entry direction." (Spec §5b, Decision 10.)
- **Registry-driven, generic over contributors; never hard-code ES into shared logic.** Contributors are declared via `subprojects/all-stocks-signals/instruments.py` (the no-mix contract). (Spec §3, Decision 5/6.)
- **Follow existing code patterns** — same import bootstrap, same docstring density, same numpy/pandas idioms as `l1_runner.py` / `runner.py`.

**Verified facts (measured against real data on 2026-06-26, used by the tests below):**
- ES 4h and NQ 4h grids are **byte-identical: 2,119 bars, 2,119/2,119 coincident timestamps** ⇒ `align_decbars` returns the identity index for ES.
- Delivered touch == `decision_signals(es_df_dec, es_box)` **exactly: 0/2,119 mismatches** (counts long=425, short=382, hold=1312).
- Traversal is materially sparser (long=53, short=38, hold=2028) ⇒ confirms the intentional touch-vs-traversal divergence (Spec §12).
- Canonical traversal tick threshold = **0.75** (every BoxLookup construction in the repo uses `tick_threshold=0.75`).

---

## File Structure

All new files; no existing file is modified.

| File | Responsibility |
|---|---|
| `optimize/l2/contributors/__init__.py` | Package marker (empty). |
| `optimize/l2/contributors/registry.py` | `Contributor` dataclass + `CONTRIBUTORS`/`get_contributor` lookup, built from the `instruments.py` no-mix registry. Resolves candle/box/delivery paths. Never names ES in logic — ES is one registry entry. |
| `optimize/l2/contributors/loader.py` | `load_contributor_inputs(token, tf)` → `ContributorInputs` (df_dec, df1, box, delivery, tick_threshold). Mirrors `optimize/data.load_inputs` + `load_box` for an arbitrary instrument. |
| `optimize/l2/contributors/align.py` | `align_decbars(nq_dec_dates, es_dec_dates, bar_td)` (causal last-closed index) + `gather_to_nq(es_series, j_es, fill)`. The single alignment chokepoint for Part A. |
| `optimize/l2/contributors/state.py` | `touch_state(df_dec, delivery)` + `traversal_state(df_dec, box_csv, tick_threshold)` → per-contributor-bar net state int8 {+1/-1/0}. |
| `optimize/l2/contributors/votes.py` | ES committee (`committee_votes`, `committee_veto_mask`, `committee_confirm_count`, `committee_confirm_mask`) + the two signal-voter encoders (`signal_stance`, `signal_truthtable`). |
| `optimize/l2/contributors/test_contrib_registry.py` | Task 1 tests. |
| `optimize/l2/contributors/test_contrib_loader.py` | Task 2 tests. |
| `optimize/l2/contributors/test_contrib_align.py` | Task 3 tests (incl. look-ahead guard). |
| `optimize/l2/contributors/test_contrib_state.py` | Task 4 tests (touch vs traversal). |
| `optimize/l2/contributors/test_contrib_committee.py` | Task 5 tests (committee orientation + identity). |
| `optimize/l2/contributors/test_contrib_signal.py` | Task 6 tests (stance+mode, 6-cell, Part-B compatibility/identity). |

Tests live **inside the package** as flat `test_contrib_*.py` files (pytest discovers them recursively), matching the project's flat `optimize/l2/test_*.py` convention. Each test/source file bootstraps `sys.path` with the subproject root via `parents[3]` (file is at `optimize/l2/contributors/<file>.py`).

**All pytest commands run from the subproject root:** `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.

---

### Task 1: Contributor registry

**Files:**
- Create: `optimize/l2/contributors/__init__.py`
- Create: `optimize/l2/contributors/registry.py`
- Test: `optimize/l2/contributors/test_contrib_registry.py`

**Interfaces:**
- Consumes: `subprojects/all-stocks-signals/instruments.py` (`REGISTRY: dict[str, Instrument]`; each `Instrument` has `.token`, `.candle_dir`, `.candle_prefix`, `.box_csv`, `.delivery_name()`).
- Produces:
  - `@dataclass(frozen=True) Contributor` with fields `token: str`, `candle_dir: str`, `candle_prefix: str`, `box_csv: str`, `delivery_dir: str`, `align: str`, `tick_threshold: float = 0.75`; methods `candle_csv(tf: str) -> str`, `delivery_csv(tf: str, preset: str = "full") -> str`.
  - `CONTRIBUTORS: dict[str, Contributor]` (contains `"ES"`).
  - `get_contributor(token: str) -> Contributor` (raises `KeyError` on unknown token).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_registry.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2.contributors import registry


def test_es_contributor_paths_resolve_from_instruments_registry():
    c = registry.get_contributor("ES")
    assert c.token == "ES"
    assert c.align == "identity"                       # ES = exact grid (Spec §3.2)
    assert c.tick_threshold == 0.75
    assert c.candle_csv("4h").endswith("ES_Continuous_Data/ES_4h.csv")
    assert c.candle_csv("1m").endswith("ES_Continuous_Data/ES_1m.csv")
    assert c.box_csv.endswith("BOXS/CME/ES/ES_full_data.csv")
    assert c.delivery_csv("4h", "full").endswith("ES_SIGNALS_DELIVERY/2_holds_dropped/ES_4h_full.csv")
    # every resolved path must actually exist on disk (no typo'd path silently accepted)
    for p in (c.candle_csv("4h"), c.candle_csv("1m"), c.box_csv, c.delivery_csv("4h", "full")):
        assert Path(p).exists(), p


def test_unknown_contributor_raises():
    with pytest.raises(KeyError):
        registry.get_contributor("DOGE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.contributors'`.

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/contributors/__init__.py
```
(empty file)

```python
# optimize/l2/contributors/registry.py
"""Cross-instrument L2 contributor registry — the standard for adding QQQ/SQQQ (Spec §3).

A `Contributor` is a declarative bundle (token + candle/box/delivery sources + alignment kind) built
from `subprojects/all-stocks-signals/instruments.py` (the no-mix contract — the single place instrument
identity lives). Generic over instruments: nothing here special-cases ES beyond the one registry entry.
Part A registers ES (align='identity', exact grid). ETFs (align='as_of') are a later registry entry +
adapter — ZERO gate-logic change (Spec §3.3)."""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

# The parent trading repo root (override for the server migration via WSH_DATA_BASE; mirrors
# optimize/data._BASE). The instruments registry + delivery bundles live under it.
_TRADING = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_INST_PATH = _TRADING / "subprojects" / "all-stocks-signals" / "instruments.py"


def _load_instruments():
    """Load the no-mix instrument registry by file path (avoids polluting sys.path with the generic
    top-level module name 'instruments')."""
    spec = importlib.util.spec_from_file_location("ass_instruments", _INST_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_instruments = _load_instruments()


@dataclass(frozen=True)
class Contributor:
    """One external contributor's data identity + how it aligns onto NQ's decision grid."""
    token: str          # instrument identifier (e.g. "ES")
    candle_dir: str     # dir holding <prefix>_<TF>.csv
    candle_prefix: str  # filename prefix (e.g. "ES")
    box_csv: str        # the unified per-instrument box file (_full_data.csv)
    delivery_dir: str   # <TOKEN>_SIGNALS_DELIVERY/2_holds_dropped (the delivered Stage-1 touch signal)
    align: str          # "identity" (exact grid, ES) | "as_of" (ETF) — Part A uses identity only
    tick_threshold: float = 0.75   # BoxLookup traversal tick band (repo-canonical 0.75)

    def candle_csv(self, tf: str) -> str:
        return os.path.join(self.candle_dir, f"{self.candle_prefix}_{tf}.csv")

    def delivery_csv(self, tf: str, preset: str = "full") -> str:
        return os.path.join(self.delivery_dir, f"{self.token}_{tf}_{preset}.csv")


def _from_instrument(token: str, align: str) -> Contributor:
    inst = _instruments.REGISTRY[token]
    delivery_dir = str(_TRADING / inst.delivery_name() / "2_holds_dropped")
    return Contributor(token=inst.token, candle_dir=inst.candle_dir,
                       candle_prefix=inst.candle_prefix, box_csv=inst.box_csv,
                       delivery_dir=delivery_dir, align=align)


# Part A: ES only. NQ is the host (contributor #0, identity decision grid) and needs no load here.
CONTRIBUTORS: dict[str, Contributor] = {
    "ES": _from_instrument("ES", align="identity"),
}


def get_contributor(token: str) -> Contributor:
    if token not in CONTRIBUTORS:
        raise KeyError(f"unknown contributor {token!r}; known: {sorted(CONTRIBUTORS)}")
    return CONTRIBUTORS[token]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_registry.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/contributors/__init__.py optimize/l2/contributors/registry.py optimize/l2/contributors/test_contrib_registry.py
git commit -m "feat(l2-contrib): Contributor registry over instruments.py no-mix contract (ES entry)"
```

---

### Task 2: Contributor input loader

**Files:**
- Create: `optimize/l2/contributors/loader.py`
- Test: `optimize/l2/contributors/test_contrib_loader.py`

**Interfaces:**
- Consumes: `registry.get_contributor(token) -> Contributor`; `loader.load_data(path)` (repo root `loader.py`, maps `datetime`→`Date`, parses dates).
- Produces:
  - `@dataclass ContributorInputs` with fields `token: str`, `df_dec: pd.DataFrame`, `df1: pd.DataFrame`, `box: pd.DataFrame`, `delivery: pd.DataFrame`, `tick_threshold: float`.
  - `load_contributor_box(box_csv: str) -> pd.DataFrame` (normalized `Date` index, dedup on `Date`).
  - `load_delivery_signal(delivery_csv: str) -> pd.DataFrame` (parsed `datetime` column).
  - `load_contributor_inputs(token: str, tf: str = "4h") -> ContributorInputs`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_loader.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pandas as pd
from optimize.l2.contributors import loader


def test_load_es_inputs_shapes_and_columns():
    es = loader.load_contributor_inputs("ES", "4h")
    assert es.token == "ES"
    assert es.tick_threshold == 0.75
    # decision frame: OHLCV with a parsed Date column, ~2119 bars (measured)
    for col in ("Date", "Open", "High", "Low", "Close", "Volume"):
        assert col in es.df_dec.columns
    assert pd.api.types.is_datetime64_any_dtype(es.df_dec["Date"])
    assert len(es.df_dec) > 2000
    assert es.df_dec["Date"].is_monotonic_increasing
    # 1-minute frame is much larger and also datetime-parsed
    assert len(es.df1) > len(es.df_dec) * 50
    assert pd.api.types.is_datetime64_any_dtype(es.df1["Date"])
    # box frame: normalized Date index (midnight), no duplicate dates
    assert es.box.index.name == "Date"
    assert (es.box.index == es.box.index.normalize()).all()
    assert not es.box.index.duplicated().any()
    # delivery: only long/short rows (2_holds_dropped), datetime parsed
    assert set(es.delivery["signal"].unique()) <= {"long", "short"}
    assert pd.api.types.is_datetime64_any_dtype(es.delivery["datetime"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.contributors.loader'`.

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/contributors/loader.py
"""Load an arbitrary contributor's inputs (candles + boxes + delivered touch signal).

Mirrors optimize/data.load_inputs + load_box for a registry-declared instrument. Pure data loading —
no alignment, no state, no votes (those are align.py / state.py / votes.py)."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from loader import load_data                                      # noqa: E402
from optimize.l2.contributors.registry import get_contributor    # noqa: E402


def load_contributor_box(box_csv: str) -> pd.DataFrame:
    """Load a contributor's unified box frame, normalized Date index (same shape as optimize/data.load_box
    and box_lookup expectations)."""
    c = pd.read_csv(box_csv)
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    return c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def load_delivery_signal(delivery_csv: str) -> pd.DataFrame:
    """Load the delivered Stage-1 touch signal stream (2_holds_dropped: only long/short rows, one per
    (candle × box)). Columns: datetime, open, high, low, close, volume, signal, box_id, box_upper,
    box_lower (per ES_SIGNALS_DELIVERY/README.md)."""
    d = pd.read_csv(delivery_csv)
    d["datetime"] = pd.to_datetime(d["datetime"])
    return d


@dataclass
class ContributorInputs:
    token: str
    df_dec: pd.DataFrame    # decision-TF OHLCV (Date/Open/High/Low/Close/Volume)
    df1: pd.DataFrame       # 1-minute OHLCV (shared exit resolution analogue)
    box: pd.DataFrame       # unified box frame (normalized Date index)
    delivery: pd.DataFrame  # delivered touch signal stream
    tick_threshold: float


def load_contributor_inputs(token: str, tf: str = "4h") -> ContributorInputs:
    """Return the full input bundle for a contributor + timeframe (preset 'full')."""
    c = get_contributor(token)
    df_dec = load_data(c.candle_csv(tf)).sort_values("Date").reset_index(drop=True)
    df1 = load_data(c.candle_csv("1m")).sort_values("Date").reset_index(drop=True)
    box = load_contributor_box(c.box_csv)
    delivery = load_delivery_signal(c.delivery_csv(tf, "full"))
    return ContributorInputs(token=c.token, df_dec=df_dec, df1=df1, box=box,
                             delivery=delivery, tick_threshold=c.tick_threshold)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_loader.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/contributors/loader.py optimize/l2/contributors/test_contrib_loader.py
git commit -m "feat(l2-contrib): load ES candles/boxes/delivery via the contributor registry"
```

---

### Task 3: Causal NQ-decision-bar alignment + look-ahead guard

**Files:**
- Create: `optimize/l2/contributors/align.py`
- Test: `optimize/l2/contributors/test_contrib_align.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure numpy/pandas). For real use, `nq_dec_dates` = `l1.df_dec["Date"].to_numpy()`, `es_dec_dates` = `ContributorInputs.df_dec["Date"].to_numpy()`, `bar_td` = `TF.get(tf).bar_td`.
- Produces:
  - `align_decbars(nq_dec_dates, es_dec_dates, bar_td: pd.Timedelta) -> np.ndarray` (int64, len = #NQ bars; value = index of contributor's last-closed decision bar with start ≤ NQ bar start; `-1` where none). For the ES exact grid this is the coincident bar (identity).
  - `gather_to_nq(es_series: np.ndarray, j_es: np.ndarray, fill=0) -> np.ndarray` (maps a per-contributor-bar series onto NQ decision bars via `j_es`; `j_es < 0` ⇒ `fill`).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_align.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import align, loader

BAR = pd.Timedelta(hours=4)


def _dts(*iso):
    return np.array(list(iso), dtype="datetime64[ns]")


def test_identity_grid_maps_each_nq_bar_to_coincident_es_bar():
    grid = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00")
    j = align.align_decbars(grid, grid, BAR)
    assert list(j) == [0, 1, 2]                        # exact grid ⇒ identity (Spec §3.2/§4.1)


def test_last_closed_when_contributor_is_sparser():
    nq = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    es = _dts("2025-01-01T18:00", "2025-01-02T06:00")   # ES missing the two middle bars
    j = align.align_decbars(nq, es, BAR)
    # bar0 -> es0; bars1,2 -> still es0 (last-closed ≤ their start); bar3 -> es1
    assert list(j) == [0, 0, 0, 1]


def test_minus_one_before_first_contributor_bar():
    nq = _dts("2025-01-01T10:00", "2025-01-01T18:00")
    es = _dts("2025-01-01T18:00")
    j = align.align_decbars(nq, es, BAR)
    assert list(j) == [-1, 0]                           # no ES bar available for the 10:00 NQ bar yet


def test_lookahead_guard_shifting_es_future_does_not_change_earlier_alignment():
    """Shift a LATER ES bar further into the future; every NQ bar at/before the unshifted bars keeps its
    alignment index. If alignment leaked the future, an earlier index would change. (Spec §8.2/§8.3.3.)"""
    nq = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    es = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    j_before = align.align_decbars(nq, es, BAR)
    es_shift = es.copy()
    es_shift[3] = np.datetime64("2025-06-01T06:00")    # push the last ES bar months into the future
    j_after = align.align_decbars(nq, es_shift, BAR)
    # the first 3 NQ bars are unaffected; only bar3 (which used es3) loses it -> last-closed es2
    assert list(j_before[:3]) == list(j_after[:3])
    assert j_after[3] == 2                              # bar3 falls back to es2, never sees the future bar


def test_lookahead_guard_on_real_es_grid():
    """Real ES/NQ 4h grids are identical (measured 2119/2119). Shifting the entire tail of ES into the
    future must not change alignment for any NQ bar before the shift point."""
    es = loader.load_contributor_inputs("ES", "4h")
    nq_dates = es.df_dec["Date"].to_numpy()            # ES==NQ grid; reuse ES dates as the NQ grid
    es_dates = es.df_dec["Date"].to_numpy()
    j0 = align.align_decbars(nq_dates, es_dates, BAR)
    cut = len(es_dates) - 100
    es_shift = es_dates.copy()
    es_shift[cut:] = es_shift[cut:] + np.timedelta64(365, "D")
    j1 = align.align_decbars(nq_dates, es_shift, BAR)
    assert np.array_equal(j0[:cut], j1[:cut])          # earlier bars untouched by future shift


def test_gather_to_nq_uses_fill_for_missing():
    es_series = np.array([10, 20, 30], dtype=np.int8)
    j = np.array([-1, 0, 0, 2], dtype=np.int64)
    out = align.gather_to_nq(es_series, j, fill=0)
    assert list(out) == [0, 10, 10, 30]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_align.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.contributors.align'`.

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/contributors/align.py
"""Causal alignment of a contributor's decision bars onto NQ's decision grid (Spec §4.1).

The single Part-A alignment chokepoint. For each NQ decision bar we take the contributor's LAST-CLOSED
decision bar — causal, no look-ahead by construction. A contributor bar 'closes' at start+bar_td and is
available to NQ bar i (which closes at nq_start_i + bar_td) iff es_start_j + bar_td ≤ nq_start_i + bar_td,
i.e. es_start_j ≤ nq_start_i (the bar_td offsets cancel for same-width grids). For the ES exact grid this
is the coincident bar (identity). ETFs (later) layer an as-of + one-business-day box-shift adapter on top;
the causal 'start ≤ start' rule is unchanged."""
from __future__ import annotations

import numpy as np
import pandas as pd


def align_decbars(nq_dec_dates, es_dec_dates, bar_td: pd.Timedelta) -> np.ndarray:
    """Index, per NQ decision bar, of the contributor's last-closed decision bar (start ≤ NQ start);
    -1 where no contributor bar exists yet. `bar_td` is accepted for interface symmetry with
    runner._decbar_1min_index and to document the close-offset cancellation; it must be > 0."""
    assert bar_td > pd.Timedelta(0), "bar_td must be positive"
    nq = np.asarray(nq_dec_dates, dtype="datetime64[ns]")
    es = np.asarray(es_dec_dates, dtype="datetime64[ns]")
    # last contributor bar whose START ≤ this NQ bar's START — searchsorted only ever looks backward,
    # so future contributor bars cannot influence an earlier NQ bar's index (look-ahead safe).
    j = np.searchsorted(es, nq, side="right") - 1
    return j.astype(np.int64)


def gather_to_nq(es_series: np.ndarray, j_es: np.ndarray, fill=0) -> np.ndarray:
    """Map a per-contributor-bar series onto NQ decision bars via the alignment index j_es.
    j_es < 0 (no contributor bar yet) ⇒ `fill`."""
    es_series = np.asarray(es_series)
    out = np.full(len(j_es), fill, dtype=es_series.dtype)
    ok = np.asarray(j_es) >= 0
    out[ok] = es_series[np.asarray(j_es)[ok]]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_align.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/contributors/align.py optimize/l2/contributors/test_contrib_align.py
git commit -m "feat(l2-contrib): causal last-closed NQ-decbar alignment + look-ahead guard"
```

---

### Task 4: ES net state — touch (delivered) and traversal (BoxLookup)

**Files:**
- Create: `optimize/l2/contributors/state.py`
- Test: `optimize/l2/contributors/test_contrib_state.py`

**Interfaces:**
- Consumes: `loader.load_contributor_inputs` (`df_dec`, `delivery`, `box` location via `registry.get_contributor("ES").box_csv`); `box_lookup.BoxLookup(unified_path, tick_threshold)` with `.reset_state()` and `.get_signal(close, ts) -> 'long'|'short'|'hold'|None`; `optimize.signals.decision_signals` + `optimize.fast_engine.signals_to_int` (for the real-data parity anchor only).
- Produces:
  - `touch_state(df_dec: pd.DataFrame, delivery: pd.DataFrame) -> np.ndarray` (int8 per decision bar, +1 long / -1 short / 0 hold; long wins ties).
  - `traversal_state(df_dec: pd.DataFrame, box_csv: str, tick_threshold: float) -> np.ndarray` (int8 per decision bar; None→0).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_state.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import state, loader, registry
from optimize import signals as _signals
from optimize.fast_engine import signals_to_int


def test_touch_state_collapses_to_net_long_wins_ties():
    # 3 decision bars; delivery (2_holds_dropped) carries only long/short rows, possibly multiple per bar
    df_dec = pd.DataFrame({"Date": pd.to_datetime(
        ["2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00"])})
    delivery = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-01T18:00", "2025-01-01T18:00",   # bar0: a short box AND a long box -> long wins ties
            "2025-01-01T22:00",                        # bar1: only short -> short
            # bar2: no delivered row -> hold
        ]),
        "signal": ["short", "long", "short"],
    })
    st = state.touch_state(df_dec, delivery)
    assert list(st) == [1, -1, 0]


def test_traversal_state_fires_long_on_below_inside_above():
    # one weekly level box (W-RL via WRLU/WRLD); close path below -> inside -> above must fire 'long'.
    box = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02"]),
        "WRLU": [110.0], "WRLD": [100.0],
    }).set_index("Date", drop=False)
    box_csv = str(Path(_PI) / "optimize" / "l2" / "contributors" / "_tmp_box_state.csv")
    box.reset_index(drop=True).to_csv(box_csv, index=False)
    # decision bars all map to box-date 2025-01-02 (hour < 18 ⇒ same day)
    df_dec = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02T02:00", "2025-01-02T06:00", "2025-01-02T10:00"]),
        "Close": [90.0,   # below (close < lower - tick)
                  105.0,  # inside
                  120.0], # above -> traversal fires LONG
    })
    st = state.traversal_state(df_dec, box_csv, tick_threshold=0.75)
    Path(box_csv).unlink()
    assert st[0] == 0 and st[1] == 0 and st[2] == 1     # only the through-traversal bar fires long


def test_touch_vs_traversal_diverge_on_real_es():
    es = loader.load_contributor_inputs("ES", "4h")
    box_csv = registry.get_contributor("ES").box_csv
    touch = state.touch_state(es.df_dec, es.delivery)
    trav = state.traversal_state(es.df_dec, box_csv, es.tick_threshold)
    assert len(touch) == len(trav) == len(es.df_dec)
    # touch is much denser than traversal (measured: ~807 vs ~91 directional bars) — Spec §12 divergence
    assert int((touch != 0).sum()) > int((trav != 0).sum()) * 3


def test_touch_state_equals_decision_signals_recompute_on_real_es():
    """The delivered touch signal == optimize.signals.decision_signals(es) byte-for-byte (measured
    0/2119 mismatches). This anchors source (a) 'delivered' to the L1 Stage-1 rule (Spec §4.2)."""
    es = loader.load_contributor_inputs("ES", "4h")
    touch = state.touch_state(es.df_dec, es.delivery)
    recompute = signals_to_int(_signals.decision_signals(es.df_dec, es.box))
    assert np.array_equal(touch, recompute)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.contributors.state'`.

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/contributors/state.py
"""Contributor net state {+1 long / -1 short / 0 hold} per decision bar — BOTH definitions (Spec §4.2).

(a) touch_state     — read the DELIVERED Stage-1 touch signal (ES_SIGNALS_DELIVERY/2_holds_dropped) and
                      collapse the per-(candle × box) rows to one net state per bar (long wins ties).
                      Verified equal to optimize.signals.decision_signals(es) byte-for-byte.
(b) traversal_state — recompute via box_lookup.BoxLookup (L1-parity traversal: below→inside→above = long,
                      above→inside→below = short). Stateful ⇒ feed bars in chronological order.

The two can diverge materially; letting the optimizer pick is intentional (Spec §12)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from box_lookup import BoxLookup                                  # noqa: E402

_SIG2INT = {"long": 1, "short": -1, "hold": 0}


def touch_state(df_dec: pd.DataFrame, delivery: pd.DataFrame) -> np.ndarray:
    """Net per-decision-bar touch state from the delivered Stage-1 signal. The delivery (2_holds_dropped)
    carries only long/short rows; a bar is long if ANY of its delivered rows is long, short if any is
    short, LONG WINS TIES (mirrors decision_signals + L1's collapse-to-one-entry-per-candle). Bars with no
    delivered row are hold (0)."""
    dates = pd.DatetimeIndex(df_dec["Date"])
    longs = pd.DatetimeIndex(delivery.loc[delivery["signal"] == "long", "datetime"].unique())
    shorts = pd.DatetimeIndex(delivery.loc[delivery["signal"] == "short", "datetime"].unique())
    out = np.zeros(len(dates), dtype=np.int8)
    out[dates.isin(shorts)] = -1
    out[dates.isin(longs)] = 1            # long assigned last ⇒ long wins ties
    return out


def traversal_state(df_dec: pd.DataFrame, box_csv: str, tick_threshold: float) -> np.ndarray:
    """Net per-decision-bar traversal state via BoxLookup (L1 parity). Stateful: ONE BoxLookup, reset,
    fed bars in chronological order. get_signal returns long/short/hold/None; None (no active box row) ⇒
    hold (0)."""
    bl = BoxLookup(unified_path=box_csv, tick_threshold=tick_threshold)
    bl.reset_state()
    dates = df_dec["Date"].to_numpy()
    closes = df_dec["Close"].to_numpy(float)
    out = np.zeros(len(df_dec), dtype=np.int8)
    for i in range(len(df_dec)):
        sig = bl.get_signal(float(closes[i]), pd.Timestamp(dates[i]))
        out[i] = _SIG2INT.get(sig, 0)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_state.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/contributors/state.py optimize/l2/contributors/test_contrib_state.py
git commit -m "feat(l2-contrib): ES net state — delivered touch + BoxLookup traversal (collapsed)"
```

---

### Task 5: ES indicator committee on ES bars, oriented to NQ box_dir

**Files:**
- Create: `optimize/l2/contributors/votes.py`
- Test: `optimize/l2/contributors/test_contrib_committee.py`

**Interfaces:**
- Consumes: `indicators.library.from_specs(specs) -> list[Indicator]`; `indicators.runner.market_context(df) -> MarketContext`; `indicators.runner._vote_from_1min(ind, ctx, j_idx, box_dir) -> int8[]` (computes the indicator's directions on `ctx`, samples at `j_idx`, orients against `box_dir`, applies warm-up — the EXACT NQ orientation machinery, here with the ES decision frame playing the role of the source frame and `j_es` the sampling index); `indicators.base.{CONFIRM, VETO}`; `align.align_decbars`.
- Produces (all aligned to NQ decision bars; `n` = #NQ bars):
  - `committee_votes(es_df_dec, j_es, nq_box_dir, specs) -> tuple[dict, list]` → `({id(ind): int8 vote[]}, inds)`; votes are `+1` CONFIRM (ES agrees with NQ box dir) / `-1` VETO / `0` neutral, per NQ bar, for ENABLED indicators only.
  - `committee_veto_mask(votes, inds, n) -> np.ndarray[bool]` (any-OR veto, entry-bar-aligned `out[idx]=veto@idx-1`, idx0=False; identity all-False when no enabled veto-capable indicator). Mirrors `runner.veto_mask`.
  - `committee_confirm_count(votes, inds, n) -> np.ndarray[int64]` (per-SIGNAL-bar count of CONFIRM votes among enabled confirm-capable indicators; UNshifted — Part B pools/aligns it).
  - `committee_confirm_mask(votes, inds, k, n) -> np.ndarray[bool]` (`≥K_eff` gate, entry-bar-aligned `out[idx]=count@idx-1≥K_eff`, idx0=True; identity all-True when 0 confirmers). Mirrors `runner.confirm_mask`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_committee.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import votes
from indicators.base import CONFIRM


def _rising_es(n=60):
    """A monotonically rising ES decision frame ⇒ EMA(fast)>EMA(slow), stance = +1 (bullish) on warm bars."""
    dates = pd.date_range("2025-01-01T18:00", periods=n, freq="4h")
    close = np.linspace(100.0, 200.0, n)
    return pd.DataFrame({"Date": dates, "Open": close, "High": close + 1,
                         "Low": close - 1, "Close": close, "Volume": np.ones(n)})


def test_es_long_committee_vote_confirms_only_nq_long():
    """ES is bullish (rising). With box_dir = +1 (NQ-long) the ES EMA-trend confirms; with box_dir = -1
    (NQ-short) it must NOT confirm. Orientation: +1 always means 'agrees with NQ' (Spec §5b)."""
    es = _rising_es(60)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)                # identity grid
    specs = [{"key": "ema_trend", "enabled": True, "mode": "confirm",
              "params": {"fast": 3, "slow": 8}}]
    nq_long = np.ones(n, dtype=np.int8)
    nq_short = -np.ones(n, dtype=np.int8)
    v_long, inds = votes.committee_votes(es.df_dec if hasattr(es, "df_dec") else es, j_es, nq_long, specs)
    v_short, _ = votes.committee_votes(es, j_es, nq_short, specs)
    ind_id = next(iter(v_long))
    warm = 8                                            # slow EMA warm-up
    assert (v_long[ind_id][warm:] == CONFIRM).all()    # ES-long confirms NQ-long
    assert not (v_short[ind_id][warm:] == CONFIRM).any()  # ES-long never confirms NQ-short


def test_committee_masks_are_identity_when_no_specs_enabled():
    es = _rising_es(20)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)
    v, inds = votes.committee_votes(es, j_es, np.ones(n, dtype=np.int8), specs=[])
    assert v == {}
    veto = votes.committee_veto_mask(v, inds, n)
    confirm = votes.committee_confirm_mask(v, inds, k=1, n=n)
    assert not veto.any()                              # no veto ⇒ all-False identity
    assert confirm.all()                               # no confirmer ⇒ all-True identity (Spec §8.1)


def test_committee_confirm_mask_threshold_and_alignment():
    es = _rising_es(40)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)
    specs = [{"key": "ema_trend", "enabled": True, "mode": "confirm", "params": {"fast": 3, "slow": 8}}]
    nq_long = np.ones(n, dtype=np.int8)
    v, inds = votes.committee_votes(es, j_es, nq_long, specs)
    confirm = votes.committee_confirm_mask(v, inds, k=1, n=n)
    assert confirm.dtype == bool and len(confirm) == n
    assert confirm[0]                                  # idx0 is identity-True (entry-bar alignment)
    assert confirm[-1]                                 # late warm bars confirm ⇒ gate open
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_committee.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.l2.contributors.votes'`.

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/l2/contributors/votes.py
"""Contributor voter channels for L2 (Spec §5) — all aligned to NQ decision bars, oriented to NQ box_dir.

§5b — indicator committee: the FULL 18-indicator registry computed on the CONTRIBUTOR's own bars via the
instrument-agnostic MarketContext, sampled at the aligned contributor bar per NQ decision bar, and oriented
to NQ's box_dir (reusing runner._vote_from_1min verbatim — the ES decision frame plays the source-frame
role, j_es the sampling index). A +1 always means 'agrees with the NQ entry direction'.

§5a — composite signal voter (state → vote), BOTH encodings searchable:
  signal_stance       (i)  directional stance + mode (reuses votes.stance_directions)
  signal_truthtable   (ii) full 6-cell (NQ-long,NQ-short) × (ES-long,ES-short,ES-hold) truth table

The committee mask builders MIRROR runner.veto_mask/confirm_mask EXACTLY (same any-OR veto, same ≥K_eff
confirm, same entry-bar shift out[1:]=raw[:-1]) so Part B can AND/pool them with NQ's masks with zero new
conventions. All builders are identity-when-disabled (veto all-False, confirm all-True / no contribution)
— the unit-level guarantee behind the contributors-OFF byte-parity invariant (Spec §8.1)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from indicators import library, runner                           # noqa: E402
from indicators import votes as ind_votes                        # noqa: E402
from indicators.base import CONFIRM, VETO, HOLD, BOTH            # noqa: E402

_DIR_STR = {1: "long", -1: "short"}
_ST_STR = {1: "long", -1: "short", 0: "hold"}


# ---- §5b indicator committee -----------------------------------------------------------------------

def committee_votes(es_df_dec: pd.DataFrame, j_es, nq_box_dir, specs):
    """Run the committee on the contributor's decision bars, oriented to NQ box_dir. Returns
    ({id(ind): int8 vote[] of len(j_es)}, inds) for ENABLED indicators (votes ∈ {+1 CONFIRM, -1 VETO, 0})."""
    es_ctx = runner.market_context(es_df_dec)
    inds = library.from_specs([s for s in specs if s.get("enabled")])
    bd = np.asarray(nq_box_dir, dtype=np.int8)
    j = np.asarray(j_es, dtype=np.int64)
    votes_d = {id(ind): runner._vote_from_1min(ind, es_ctx, j, bd)
               for ind in inds if ind.config.enabled}
    return votes_d, inds


def committee_veto_mask(votes_d: dict, inds, n: int) -> np.ndarray:
    """Any-OR veto among enabled veto-capable indicators, entry-bar-aligned (out[idx]=veto@idx-1; idx0=
    False). No veto-capable enabled indicator ⇒ all-False identity. Mirrors runner.veto_mask."""
    out = np.zeros(n, dtype=bool)
    vetoers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("veto", "both")]
    if not vetoers:
        return out
    raw = np.zeros(n, dtype=bool)
    for ind in vetoers:
        raw |= (votes_d[id(ind)][:n] == VETO)
    out[1:] = raw[:-1]
    return out


def committee_confirm_count(votes_d: dict, inds, n: int) -> np.ndarray:
    """Per-SIGNAL-bar count of CONFIRM votes among enabled confirm-capable indicators (UNshifted; Part B
    pools/aligns it for the MERGED/OR topologies)."""
    confirmers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    cc = np.zeros(n, dtype=np.int64)
    for ind in confirmers:
        cc += (votes_d[id(ind)][:n] == CONFIRM).astype(np.int64)
    return cc


def committee_confirm_mask(votes_d: dict, inds, k: int, n: int) -> np.ndarray:
    """≥K_eff confirm gate, entry-bar-aligned (out[idx]=count@idx-1≥K_eff; idx0=True). K_eff=min(k,
    #confirmers); 0 confirmers ⇒ all-True identity. Mirrors runner.confirm_mask."""
    out = np.ones(n, dtype=bool)
    confirmers = [ind for ind in inds if ind.config.enabled and ind.config.mode in ("confirm", "both")]
    k_eff = min(int(k), len(confirmers))
    if k_eff <= 0:
        return out
    cc = committee_confirm_count(votes_d, inds, n)
    ok = cc >= k_eff
    out[1:] = ok[:-1]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_committee.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/contributors/votes.py optimize/l2/contributors/test_contrib_committee.py
git commit -m "feat(l2-contrib): ES 18-indicator committee oriented to NQ box_dir + runner-parity masks"
```

---

### Task 6: Composite signal voter — both encodings + Part-B compatibility

**Files:**
- Modify: `optimize/l2/contributors/votes.py` (append the two signal encoders)
- Test: `optimize/l2/contributors/test_contrib_signal.py`

**Interfaces:**
- Consumes: `indicators.votes.stance_directions(stance) -> (cdir, vdir)`; `indicators.base.{HOLD, BOTH}`; the aligned ES net state from Task 4 (`align.gather_to_nq(touch_state(...)/traversal_state(...), j_es)`); the NQ box dir array (`l1.sig_int` in real use).
- Produces (both return aligned `(confirm_vote, veto)` bool arrays; `n` = #NQ bars; entry-bar-aligned `out[idx]=verdict@idx-1`; identity = confirm_vote all-False, veto all-False — so a disabled/ignored voter contributes nothing to either channel):
  - `signal_stance(nq_box_dir, nq_es_state, mode: str) -> tuple[np.ndarray, np.ndarray]` (encoding i; `mode ∈ {"confirm","veto","both"}`; confirm channel fires where the ES stance agrees with NQ box dir, veto where it opposes).
  - `signal_truthtable(nq_box_dir, nq_es_state, table: dict) -> tuple[np.ndarray, np.ndarray]` (encoding ii; `table` keyed by `(nq_dir_str, es_state_str)` ∈ `{"long","short"}×{"long","short","hold"}` → `"confirm"|"veto"|"ignore"`; missing cells & HOLD box bars default to ignore).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/contributors/test_contrib_signal.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.l2.contributors import votes


def test_signal_stance_confirm_mode_agrees_with_box():
    # bars: box dir and ES state per signal bar; verdicts appear at the NEXT bar (entry-bar alignment).
    nq_box = np.array([1, -1, 1, 0], dtype=np.int8)    # long, short, long, hold
    es_st = np.array([1,  1, -1, 1], dtype=np.int8)    # ES: long, long, short, long
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="confirm")
    # signal-bar would_confirm = ES agrees with box: bar0 long==long True; bar1 short vs ES-long False;
    # bar2 long vs ES-short False; bar3 box hold ⇒ False. Shift to entry bar (out[idx]=@idx-1), idx0=False.
    assert list(cvote) == [False, True, False, False]
    assert not veto.any()                              # confirm-only mode ⇒ no veto channel (identity)


def test_signal_stance_both_mode_vetoes_opposition():
    nq_box = np.array([1, 1], dtype=np.int8)
    es_st = np.array([-1, -1], dtype=np.int8)          # ES opposes the long box
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="both")
    assert list(veto) == [False, True]                 # opposition vetoes (shifted to entry bar)
    assert not cvote.any()


def test_signal_stance_veto_mode_has_no_confirm_channel():
    nq_box = np.array([1, 1], dtype=np.int8)
    es_st = np.array([1, 1], dtype=np.int8)            # ES agrees, but mode=veto ⇒ no confirm emitted
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="veto")
    assert not cvote.any()                             # confirm channel identity-off
    assert not veto.any()                              # agreement never vetoes


def test_signal_truthtable_six_cells():
    # asymmetric example (Spec §5a-ii): "ES-hold vetoes NQ-short but is ignored for NQ-long"
    table = {
        ("long", "long"): "confirm", ("long", "short"): "veto",  ("long", "hold"): "ignore",
        ("short", "long"): "veto",   ("short", "short"): "confirm", ("short", "hold"): "veto",
    }
    # signal bars cover all 6 directional cells (+ a HOLD box bar that must be ignored)
    nq_box = np.array([1,  1,  1, -1, -1, -1, 0], dtype=np.int8)
    es_st = np.array([1, -1,  0,  1, -1,  0, 1], dtype=np.int8)
    cvote, veto = votes.signal_truthtable(nq_box, es_st, table)
    # per signal bar verdicts: confirm, veto, ignore, veto, confirm, veto, (box hold) ignore
    # shifted to entry bar (out[idx]=@idx-1; idx0 identity)
    assert list(cvote) == [False, True, False, False, False, True, False]
    assert list(veto) == [False, False, True, False, True, False, True]


def test_truthtable_missing_cell_and_hold_box_default_ignore():
    nq_box = np.array([0, 1], dtype=np.int8)           # bar0 HOLD box; bar1 long with empty table
    es_st = np.array([1, 1], dtype=np.int8)
    cvote, veto = votes.signal_truthtable(nq_box, es_st, table={})
    assert not cvote.any() and not veto.any()          # nothing specified ⇒ pure identity


def test_signal_masks_compatible_with_l2_gate_shape_and_off_is_identity():
    """Part-B compatibility: ES masks are bool, length n, and an all-ignore ES voter leaves
    vol_gate & ~veto & confirm BYTE-IDENTICAL — the contributors-OFF parity invariant (Spec §8.1)."""
    n = 10
    rng = np.random.default_rng(0)
    nq_box = rng.choice([-1, 0, 1], size=n).astype(np.int8)
    es_st = np.zeros(n, dtype=np.int8)                 # all hold ⇒ no agreement/opposition
    cvote, veto = votes.signal_stance(nq_box, es_st, mode="both")
    assert cvote.dtype == bool and veto.dtype == bool and len(cvote) == len(veto) == n
    # emulate the engine gate; ES OFF must not change it
    vol_gate = rng.random(n) > 0.3
    nq_veto = rng.random(n) > 0.7
    nq_confirm = rng.random(n) > 0.2
    base = vol_gate & ~nq_veto & nq_confirm
    with_es = vol_gate & ~(nq_veto | veto) & nq_confirm  # OR ES veto into NQ veto (a MERGED topology)
    assert np.array_equal(base, with_es)               # ES all-hold ⇒ veto all-False ⇒ no change
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest optimize/l2/contributors/test_contrib_signal.py -v`
Expected: FAIL with `AttributeError: module 'optimize.l2.contributors.votes' has no attribute 'signal_stance'`.

- [ ] **Step 3: Write minimal implementation**

Append to `optimize/l2/contributors/votes.py`:

```python
# ---- §5a composite signal voter — both encodings ---------------------------------------------------

def _shift_to_entry(craw: np.ndarray, vraw: np.ndarray):
    """Align per-signal-bar verdicts to the entry bar (out[idx]=verdict@idx-1; idx0 identity-off) — the
    same shift runner.veto_mask/confirm_mask use. Returns (confirm_vote, veto) bool arrays."""
    n = len(craw)
    cvote = np.zeros(n, dtype=bool)
    veto = np.zeros(n, dtype=bool)
    cvote[1:] = craw[:-1]
    veto[1:] = vraw[:-1]
    return cvote, veto


def signal_stance(nq_box_dir, nq_es_state, mode: str):
    """Encoding (i): directional stance + mode (Spec §5a-i). The ES net state is a stance (+1/-1/0);
    orient to NQ box_dir via votes.stance_directions (cdir=state, vdir=-state). mode ∈ {confirm,veto,both}
    selects channels. Returns (confirm_vote, veto) bool arrays, entry-bar-aligned, identity-when-off."""
    bd = np.asarray(nq_box_dir, dtype=np.int8)
    st = np.asarray(nq_es_state, dtype=np.int8)
    cdir, vdir = ind_votes.stance_directions(st)
    has = bd != HOLD
    would_confirm = ((cdir == bd) | (cdir == BOTH)) & has
    would_veto = ((vdir == bd) | (vdir == BOTH)) & has
    n = len(bd)
    craw = would_confirm if mode in ("confirm", "both") else np.zeros(n, dtype=bool)
    vraw = would_veto if mode in ("veto", "both") else np.zeros(n, dtype=bool)
    return _shift_to_entry(craw, vraw)


def signal_truthtable(nq_box_dir, nq_es_state, table: dict):
    """Encoding (ii): full 6-cell truth table (Spec §5a-ii). For each NQ decision bar with a directional
    box, look up table[(nq_dir, es_state)] ∈ {confirm,veto,ignore} and emit poolable confirm_vote + veto
    bool arrays, entry-bar-aligned. HOLD box bars and unspecified cells default to ignore. Cells:
    (long|short) × (long|short|hold) = 6."""
    bd = np.asarray(nq_box_dir, dtype=np.int8)
    st = np.asarray(nq_es_state, dtype=np.int8)
    n = len(bd)
    craw = np.zeros(n, dtype=bool)
    vraw = np.zeros(n, dtype=bool)
    for i in range(n):
        if bd[i] == 0:                                 # no NQ box direction ⇒ nothing to confirm/veto
            continue
        action = table.get((_DIR_STR[int(bd[i])], _ST_STR[int(st[i])]), "ignore")
        if action == "confirm":
            craw[i] = True
        elif action == "veto":
            vraw[i] = True
    return _shift_to_entry(craw, vraw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest optimize/l2/contributors/test_contrib_signal.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the whole contributors suite + a golden-safety smoke**

Run: `python -m pytest optimize/l2/contributors/ -v`
Expected: PASS (all tasks' tests green — 22 passed).

Run (proves Part A added no engine path / golden trivially intact): `python -m pytest optimize/l2/test_engine.py -q`
Expected: PASS (existing L2 engine tests unchanged — contributors are not imported by the engine).

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/contributors/votes.py optimize/l2/contributors/test_contrib_signal.py
git commit -m "feat(l2-contrib): composite signal voter — stance+mode + 6-cell truth table (Part-B-ready masks)"
```

---

## Definition of done for Part A

- [ ] `optimize/l2/contributors/` exists with: `registry.py`, `loader.py`, `align.py`, `state.py`, `votes.py` (+ `__init__.py`).
- [ ] ES candles (4h + 1m), boxes, and the delivered touch signal load through the **registry** (no hard-coded ES paths in logic; ES is one `instruments.py`-derived entry).
- [ ] `align_decbars` is **causal/last-closed**, returns the **identity index** on the ES exact grid, and **passes the look-ahead guard** (synthetic + real-ES tail-shift).
- [ ] ES net state computed **both** ways: `touch_state` (== `decision_signals(es)` byte-for-byte) and `traversal_state` (BoxLookup, L1 parity), demonstrably divergent.
- [ ] The **full 18-indicator committee** runs on ES bars via `committee_votes`, every vote **oriented to NQ box_dir** (`ES-long confirms only NQ-long`), with `runner`-parity veto/confirm masks.
- [ ] **Both signal encodings** emit entry-bar-aligned `(confirm_vote, veto)` masks: `signal_stance` (stance+mode) and `signal_truthtable` (6-cell).
- [ ] Every mask builder is **identity-when-disabled** (veto all-False, confirm all-True / no contribution), so a contributors-OFF combine is byte-identical — the unit-level basis for the golden 6/6 invariant.
- [ ] Nothing in `engine.py` / `l1_runner.py` / `runner.py` / `library.py` / `payload.py` is modified; `python -m pytest optimize/l2/contributors/ optimize/l2/test_engine.py` is green.

## Next (not in this plan)

- **Part B — gate-topology wiring (Spec §6):** consume these masks inside `engine.l2_gate_components` / a new combiner module under the optimizer-chosen topology (MERGED | SEPARATE-AND | OR-confirm-boost), per-contributor identity-when-OFF; add the contributors-OFF byte-parity test + golden 6/6 (`perf/check_golden.py`) and the ES-ON pinned anchor (Spec §8.3).
- **Part C — dashboard (Spec §10 step 2):** expose every contributor knob (enable, state-source, encoding, committee toggles/params, topology) in `frontend/l2.html` for manual verification before any optimization.
