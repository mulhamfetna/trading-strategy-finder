# Gold (GC) + Silver (SI) Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Onboard COMEX Gold (GC) and Silver (SI) end-to-end — placed data, −1-workday-shifted boxes, generated
signals, selectable+backtestable in the dashboard, wired into the optimizer — stopping before any server-side
optimization campaign.

**Architecture:** Additive-only. Copy the two instruments' candles + boxes into the `ALL_STOCKS` tree the
registry already anchors on; an isolated COMEX script shifts boxes −1 business day and re-runs the frozen Stage 1
/ Stage 2 signal engine; two registry entries (`all-stocks-signals/instruments.py` + `optimize/instruments.py`)
make GC/SI resolve their data, appear in the dashboard dropdown, and optimize — all instrument-aware plumbing
already exists (built for ES). NQ/ES stay byte-identical.

**Tech Stack:** Python 3.14, pandas, Optuna (optimizer), pytest. Repo:
`subprojects/Parametric-Indicators` (also uses sibling `subprojects/all-stocks-signals` + `subprojects/signals`
+ repo-root `ALL_STOCKS/` data tree and `src/data/loader.py`).

## Global Constraints

- **Golden gate:** `python3 perf/check_golden.py` MUST print 6/6 byte-identical after every task that touches
  shared code. A mismatch is a HARD STOP — NQ must never change.
- **Contract economics (exact):** GC `point_value = 100.0`, SI `point_value = 5000.0`.
- **Tokens:** `GC`, `SI` (uppercase, match data folders). No display-name layer.
- **Box the backtester reads:** the **SHIFTED** box (`shifted_boxes/{GC,SI}_full_data_shifted.csv`) — spec D3.
- **Shift rule:** `new_Date = old_Date − pandas.offsets.BDay(1)`; 3 loud asserts (no weekend, no collision, all
  moved back).
- **Timeframes:** `1m 2m 5m 15m 1h 2h 4h`. **Presets:** `full 2025 2026`. **Decision TF for smoke/backtest:** `4h`.
- **No local heavy compute:** the optimizer smoke test is 1 trial / 2 folds ONLY. Real campaigns are GATED — do
  not launch them in this plan.
- **Never stage sensitive files:** `keypass.txt`, `login.txt`, `kw-full.ovpn`, `SERVER_DETIALS.md`.
- **Paths:** run all commands from `subprojects/Parametric-Indicators/` unless a path says otherwise. The repo
  root (`…/trading`) is `../..` from there; the `ALL_STOCKS` tree and the two source zips live at the repo root.

---

### Task 1: Place COMEX candles + raw boxes into the ALL_STOCKS tree

**Files:**
- Create (data): `ALL_STOCKS/CANDLES/COMEX/GC_Continuous_Data/GC_<TF>.csv` (7 files) + `SI_Continuous_Data/SI_<TF>.csv` (7)
- Create (data): `ALL_STOCKS/BOXS/COMEX/GC/GC_full_data.csv` + `ALL_STOCKS/BOXS/COMEX/SI/SI_full_data.csv`
- Test: `subprojects/all-stocks-signals/tests/test_comex_data_placed.py`

**Interfaces:**
- Produces: the on-disk data files at the exact paths `all-stocks-signals/instruments.py` will point at in Task 3.

- [ ] **Step 1: Write the failing test**

```python
# subprojects/all-stocks-signals/tests/test_comex_data_placed.py
import os
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
_ALL = os.path.join(_ROOT, 'ALL_STOCKS')
TFS = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']


def test_candles_present_and_shaped():
    for tok in ('GC', 'SI'):
        for tf in TFS:
            p = os.path.join(_ALL, 'CANDLES', 'COMEX', f'{tok}_Continuous_Data', f'{tok}_{tf}.csv')
            assert os.path.exists(p), f'missing {p}'
            df = pd.read_csv(p, nrows=5)
            assert list(df.columns) == ['datetime', 'open', 'high', 'low', 'close', 'volume'], f'{p} cols'


def test_boxes_present_and_shaped():
    nq_box = os.path.join(_ALL, 'BOXS', 'CME', 'NQ', 'NQ_full_data.csv')
    nq_cols = list(pd.read_csv(nq_box, nrows=1).columns)
    for tok in ('GC', 'SI'):
        p = os.path.join(_ALL, 'BOXS', 'COMEX', tok, f'{tok}_full_data.csv')
        assert os.path.exists(p), f'missing {p}'
        assert list(pd.read_csv(p, nrows=1).columns) == nq_cols, f'{p} must match NQ box columns'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/all-stocks-signals && python3 -m pytest tests/test_comex_data_placed.py -q`
Expected: FAIL (files missing).

- [ ] **Step 3: Place the data (unzip the two source zips into the tree)**

Run from the repo root (`…/trading`):

```bash
cd /mnt/data/projects/trading
# candles: the zip's internal tree is COMEX/GC_Continuous_Data/... → lands exactly under CANDLES/COMEX
unzip -oq silver-gold-candles.zip -d ALL_STOCKS/CANDLES
# boxes: zip has GC/GC_full_data.csv + SI/SI_full_data.csv → place each under BOXS/COMEX/<TOK>/
mkdir -p ALL_STOCKS/BOXS/COMEX/GC ALL_STOCKS/BOXS/COMEX/SI /tmp/gs_levels
unzip -oq silver-gold-levels.zip -d /tmp/gs_levels
cp /tmp/gs_levels/GC/GC_full_data.csv ALL_STOCKS/BOXS/COMEX/GC/GC_full_data.csv
cp /tmp/gs_levels/SI/SI_full_data.csv ALL_STOCKS/BOXS/COMEX/SI/SI_full_data.csv
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd subprojects/all-stocks-signals && python3 -m pytest tests/test_comex_data_placed.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit** (data may be gitignored — the test is the tracked artifact)

```bash
cd /mnt/data/projects/trading/subprojects/all-stocks-signals
git add tests/test_comex_data_placed.py
git add -f ../../ALL_STOCKS/BOXS/COMEX 2>/dev/null || true   # boxes are small; force only if ignored + desired
git commit -m "feat(data): place COMEX GC+SI candles + raw boxes; presence/shape test"
```

---

### Task 2: Isolated COMEX box-shift + signal generation

**Files:**
- Create: `subprojects/all-stocks-signals/isolated_comex_box_shift.py` (adapted from `isolated_etf_box_shift.py`)
- Create: `subprojects/all-stocks-signals/shifted_boxes/{GC,SI}_full_data_shifted.csv` (output)
- Create: `subprojects/all-stocks-signals/output_shifted/{GC,SI}/...` + `{GC,SI}_SIGNALS_DELIVERY/` (output)
- Test: `subprojects/all-stocks-signals/tests/test_comex_shift.py`

**Interfaces:**
- Consumes: raw boxes from Task 1; the frozen engine at `subprojects/signals/generate_stage1.py`
  (`_emit_rows`, `_OUT_COLS`) + `subprojects/signals/stage1_0_reverse_signals/generate_stage2.py` (`generate`);
  `src.data.loader.load_data`.
- Produces: `shift_box(token, comex_cfg) -> pd.DataFrame` (indexed by shifted Date), the shifted-box CSVs, and
  the delivery bundles. `COMEX` dict of `{token: {candle_dir, prefix, box}}`.

- [ ] **Step 1: Write the failing test** (shift bijection is the risky logic — unit-test it directly)

```python
# subprojects/all-stocks-signals/tests/test_comex_shift.py
import importlib.util
import os
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(_HERE, '..', 'isolated_comex_box_shift.py')


def _load():
    spec = importlib.util.spec_from_file_location('comex_shift', _MOD)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_comex_registry_has_gc_si():
    m = _load()
    assert set(m.COMEX) == {'GC', 'SI'}


def test_shift_is_clean_backward_bijection():
    m = _load()
    for tok in ('GC', 'SI'):
        box = m.shift_box(tok)                       # runs the shift + asserts internally
        d = pd.to_datetime(box['Date'])
        assert d.dt.dayofweek.max() <= 4             # no weekend
        assert not d.duplicated().any()              # no collision
        raw = pd.to_datetime(pd.read_csv(m.COMEX[tok]['box'])['Date']).dt.normalize()
        assert (d.min() < raw.min()) or (d.max() < raw.max())   # moved backward
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/all-stocks-signals && python3 -m pytest tests/test_comex_shift.py -q`
Expected: FAIL (module `isolated_comex_box_shift.py` does not exist).

- [ ] **Step 3: Create the isolated COMEX script**

Adapt `isolated_etf_box_shift.py` verbatim except the instrument table and labels. Full file:

```python
# subprojects/all-stocks-signals/isolated_comex_box_shift.py
"""ISOLATED COMEX box-shift + re-export (GC & SI ONLY).

Self-contained on purpose: never references NQ/ES/ETF, never imports the shared driver/registry. Reuses ONLY the
FROZEN Stage 1 / Stage 2 engine (read-only, by file path) so the signal methodology is identical to the approved
pipeline. Shifts each box Date back one BUSINESS day, re-generates signals for 7 TF x 3 presets, validates, and
packages <TOKEN>_SIGNALS_DELIVERY/. Mirrors isolated_etf_box_shift.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_SIGNALS_ROOT = os.path.abspath(os.path.join(_HERE, '..', 'signals'))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_ALL = os.path.join(_REPO_ROOT, 'ALL_STOCKS')
sys.path.insert(0, _REPO_ROOT)
from src.data.loader import load_data  # noqa: E402

TIMEFRAMES = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']
PRESETS = ['full', '2025', '2026']

# --- the TWO COMEX instruments only (hardcoded; NQ/ES/ETF deliberately absent) ---
COMEX = {
    'GC': dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'COMEX', 'GC_Continuous_Data'),
               prefix='GC', box=os.path.join(_ALL, 'BOXS', 'COMEX', 'GC', 'GC_full_data.csv')),
    'SI': dict(candle_dir=os.path.join(_ALL, 'CANDLES', 'COMEX', 'SI_Continuous_Data'),
               prefix='SI', box=os.path.join(_ALL, 'BOXS', 'COMEX', 'SI', 'SI_full_data.csv')),
}

_SHIFTED_DIR = os.path.join(_HERE, 'shifted_boxes')
_OUT_ROOT = os.path.join(_HERE, 'output_shifted')


def _load_frozen(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SIGNALS_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g1 = _load_frozen('comex_stage1', 'generate_stage1.py')
g2 = _load_frozen('comex_stage2', os.path.join('stage1_0_reverse_signals', 'generate_stage2.py'))


def shift_box(token: str) -> pd.DataFrame:
    box = pd.read_csv(COMEX[token]['box'])
    old = pd.to_datetime(box['Date']).dt.normalize()
    new = old - pd.offsets.BDay(1)
    assert new.dt.dayofweek.max() <= 4, f"{token}: shift produced a weekend date"
    assert not new.duplicated().any(), f"{token}: shift produced duplicate dates (collision)"
    assert (new < old).all(), f"{token}: some dates not moved backward"
    box = box.copy()
    box['Date'] = new
    os.makedirs(_SHIFTED_DIR, exist_ok=True)
    out = os.path.join(_SHIFTED_DIR, f'{token}_full_data_shifted.csv')
    box.to_csv(out, index=False)
    print(f"  [{token}] shifted box -> {os.path.relpath(out, _REPO_ROOT)}  "
          f"(Date {new.min().date()} .. {new.max().date()})")
    return box.set_index('Date', drop=False)


def stage1_for_preset(candles_csv: str, box_idx: pd.DataFrame, preset: str) -> pd.DataFrame:
    candles = load_data(candles_csv)
    if preset != 'full':
        candles = candles[candles['Date'].dt.year == int(preset)].reset_index(drop=True)
    rows = list(g1._emit_rows(candles, box_idx))
    return pd.DataFrame(rows, columns=g1._OUT_COLS).sort_values(
        by=['datetime', 'box_upper', 'box_lower'],
        ascending=[True, False, False], kind='mergesort', na_position='last',
    ).reset_index(drop=True)


def generate(token: str, box_idx: pd.DataFrame) -> list:
    cfg = COMEX[token]
    summary = []
    for tf in TIMEFRAMES:
        candles_csv = os.path.join(cfg['candle_dir'], f"{cfg['prefix']}_{tf}.csv")
        if not os.path.exists(candles_csv):
            print(f"  SKIP {token} {tf}: missing {candles_csv}", file=sys.stderr); continue
        tf_dir = os.path.join(_OUT_ROOT, token, tf)
        nh_dir = os.path.join(tf_dir, 'no_holds')
        bd_dir = os.path.join(tf_dir, 'by_direction')
        os.makedirs(nh_dir, exist_ok=True); os.makedirs(bd_dir, exist_ok=True)
        for preset in PRESETS:
            s1 = stage1_for_preset(candles_csv, box_idx, preset)
            s1.to_csv(os.path.join(tf_dir, f'signals_{token}_{tf}_{preset}.csv'), index=False)
            nh = s1[s1['signal'].isin(['long', 'short'])].reset_index(drop=True)
            nh.to_csv(os.path.join(nh_dir, f'signals_{token}_{tf}_{preset}_no_holds.csv'), index=False)
            rev = g2.generate(s1)
            rev.to_csv(os.path.join(tf_dir, f'reverse_signals_{token}_{tf}_{preset}.csv'), index=False)
            rev[rev['first_signal'] == 'long'].reset_index(drop=True).to_csv(
                os.path.join(bd_dir, f'long_to_short_{token}_{tf}_{preset}.csv'), index=False)
            rev[rev['first_signal'] == 'short'].reset_index(drop=True).to_csv(
                os.path.join(bd_dir, f'short_to_long_{token}_{tf}_{preset}.csv'), index=False)
            d = s1['signal'].value_counts().to_dict()
            summary.append(dict(instrument=token, timeframe=f'{token}_{tf}', preset=preset,
                                signal_rows=len(s1), long=int(d.get('long', 0)),
                                short=int(d.get('short', 0)), hold=int(d.get('hold', 0)),
                                no_hold_rows=len(nh), reverse_windows=len(rev)))
            print(f"  {token:4s} {tf:4s} {preset:5s}: signals={len(s1):>8,}  "
                  f"L/S/H={d.get('long',0)}/{d.get('short',0)}/{d.get('hold',0)}  "
                  f"no_holds={len(nh):>6,}  reverse={len(rev):>4,}")
    os.makedirs(os.path.join(_OUT_ROOT, token), exist_ok=True)
    pd.DataFrame(summary).to_csv(os.path.join(_OUT_ROOT, token, 'SUMMARY.csv'), index=False)
    return summary


def validate(token: str, box_idx: pd.DataFrame) -> list:
    box_dates = set(box_idx['Date'].dt.date.astype(str))
    errs = []
    for tf in TIMEFRAMES:
        base = os.path.join(_OUT_ROOT, token, tf)
        for p in PRESETS:
            a = pd.read_csv(os.path.join(base, f'signals_{token}_{tf}_{p}.csv'))
            nh = pd.read_csv(os.path.join(base, 'no_holds', f'signals_{token}_{tf}_{p}_no_holds.csv'))
            rev = pd.read_csv(os.path.join(base, f'reverse_signals_{token}_{tf}_{p}.csv'))
            l2s = pd.read_csv(os.path.join(base, 'by_direction', f'long_to_short_{token}_{tf}_{p}.csv'))
            s2l = pd.read_csv(os.path.join(base, 'by_direction', f'short_to_long_{token}_{tf}_{p}.csv'))
            vc = a['signal'].value_counts(); tag = f"{token} {tf} {p}"
            if vc.get('long', 0) + vc.get('short', 0) + vc.get('hold', 0) != len(a): errs.append(f"{tag}: counts")
            if len(nh) != vc.get('long', 0) + vc.get('short', 0): errs.append(f"{tag}: no_hold")
            if (nh['signal'] == 'hold').any(): errs.append(f"{tag}: hold in no_holds")
            if len(l2s) + len(s2l) != len(rev): errs.append(f"{tag}: partition")
            ids = a['box_id'].dropna().astype(str)
            if len(ids):
                bad = set(ids.str.rsplit('_', n=1).str[-1].unique()) - box_dates
                if bad: errs.append(f"{tag}: box_id outside SHIFTED index e.g. {list(bad)[:3]}")
            if len(rev) > len(nh): errs.append(f"{tag}: reverse>no_hold")
    return errs


def package(token: str) -> None:
    src = os.path.join(_OUT_ROOT, token)
    dst = os.path.join(_REPO_ROOT, f'{token}_SIGNALS_DELIVERY')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    n = 0
    for tf in TIMEFRAMES:
        tf_dir = os.path.join(src, tf)
        for p in PRESETS:
            name = f'{token}_{tf}_{p}.csv'
            for s, d in [
                (f'signals_{token}_{tf}_{p}.csv', os.path.join('1_all_signals', name)),
                (os.path.join('no_holds', f'signals_{token}_{tf}_{p}_no_holds.csv'), os.path.join('2_holds_dropped', name)),
                (f'reverse_signals_{token}_{tf}_{p}.csv', os.path.join('3_reverse_signals', name)),
                (os.path.join('by_direction', f'long_to_short_{token}_{tf}_{p}.csv'), os.path.join('4_reverse_by_direction', 'long_to_short', name)),
                (os.path.join('by_direction', f'short_to_long_{token}_{tf}_{p}.csv'), os.path.join('4_reverse_by_direction', 'short_to_long', name)),
            ]:
                sp = os.path.join(tf_dir, s); dp = os.path.join(dst, d)
                os.makedirs(os.path.dirname(dp), exist_ok=True); shutil.copy2(sp, dp); n += 1
    shutil.copy2(os.path.join(src, 'SUMMARY.csv'), os.path.join(dst, 'SUMMARY.csv'))
    with open(os.path.join(dst, 'README.md'), 'w') as f:
        f.write(f"# {token} Signals — Delivery Bundle (BOX-SHIFTED -1 business day)\n\n"
                f"COMEX {token} regenerated with the box Date shifted back one business day (weekends skipped) "
                f"by the ISOLATED script isolated_comex_box_shift.py. NQ/ES/ETF unaffected. "
                f"Timeframes {' '.join(TIMEFRAMES)}; presets {' '.join(PRESETS)}. "
                f"Shifted box: shifted_boxes/{token}_full_data_shifted.csv.\n")
    archive = shutil.make_archive(dst, 'zip', root_dir=_REPO_ROOT, base_dir=f'{token}_SIGNALS_DELIVERY')
    print(f"  [{token}] packaged {n} CSVs -> {os.path.basename(dst)}  + {os.path.basename(archive)}")


def main() -> int:
    ap = argparse.ArgumentParser(description='ISOLATED COMEX box-shift + re-export (GC/SI only)')
    ap.add_argument('--instruments', nargs='+', default=list(COMEX.keys()), choices=list(COMEX.keys()))
    ap.add_argument('--no-package', action='store_true', help='generate + validate only (no bundle)')
    args = ap.parse_args()
    assert all(t in COMEX for t in args.instruments), "this script handles COMEX GC/SI ONLY"
    print(f"ISOLATED COMEX box-shift (-1 business day) for: {', '.join(args.instruments)}")
    print("NQ / ES / ETFs are NOT touched by this script.\n")
    all_errs = []
    for tok in args.instruments:
        box_idx = shift_box(tok)
        generate(tok, box_idx)
        errs = validate(tok, box_idx)
        all_errs += errs
        print(f"  [{tok}] validation: {'OK' if not errs else errs}")
        if not args.no_package and not errs:
            package(tok)
    if all_errs:
        print("VALIDATION FAILED:", all_errs, file=sys.stderr); return 1
    print("\nDONE (COMEX GC/SI).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run the shift unit test to verify it passes**

Run: `cd subprojects/all-stocks-signals && python3 -m pytest tests/test_comex_shift.py -q`
Expected: PASS (3 passed) — the shift is a clean backward bijection for GC and SI.

- [ ] **Step 5: Run the full generation + validation + packaging**

Run: `cd subprojects/all-stocks-signals && python3 isolated_comex_box_shift.py`
Expected: per-TF/preset signal-count lines for GC then SI, each `validation: OK`, and
`packaged … -> GC_SIGNALS_DELIVERY + GC_SIGNALS_DELIVERY.zip` (same for SI), ending `DONE (COMEX GC/SI).`
If any `validation:` line lists errors → STOP and debug before committing (do NOT package a failing bundle).

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/all-stocks-signals
git add isolated_comex_box_shift.py tests/test_comex_shift.py
git add -f shifted_boxes/GC_full_data_shifted.csv shifted_boxes/SI_full_data_shifted.csv
git commit -m "feat(signals): isolated COMEX GC+SI box-shift (-1 BDay) + Stage1/Stage2 signal gen (validated)"
```

---

### Task 3: Register GC/SI in both registries (backtester + dashboard)

**Files:**
- Modify: `subprojects/all-stocks-signals/instruments.py` (add GC/SI to `REGISTRY`, box → shifted)
- Modify: `subprojects/Parametric-Indicators/optimize/instruments.py` (`TOKENS`, `POINT_VALUE`)
- Test: `subprojects/Parametric-Indicators/optimize/test_instruments_comex.py`

**Interfaces:**
- Consumes: shifted boxes + candle files from Tasks 1–2.
- Produces: `instruments.TOKENS == ("NQ","ES","GC","SI")`; `point_value("GC")==100.0`, `point_value("SI")==5000.0`;
  `resolve_paths("GC","4h")` → the GC 4h candle, GC 1m candle, and GC **shifted** box.

- [ ] **Step 1: Write the failing test**

```python
# subprojects/Parametric-Indicators/optimize/test_instruments_comex.py
import os
from optimize import instruments as inst


def test_tokens_include_comex():
    assert inst.TOKENS == ("NQ", "ES", "GC", "SI")


def test_point_values():
    assert inst.point_value("GC") == 100.0
    assert inst.point_value("SI") == 5000.0


def test_resolve_paths_use_shifted_box():
    for tok in ("GC", "SI"):
        dec, minute, box = inst.resolve_paths(tok, "4h")
        assert dec.endswith(f"{tok}_4h.csv") and os.path.exists(dec)
        assert minute.endswith(f"{tok}_1m.csv") and os.path.exists(minute)
        assert box.endswith(f"{tok}_full_data_shifted.csv"), f"{tok} backtester must read the SHIFTED box"
        assert os.path.exists(box)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd subprojects/Parametric-Indicators && python3 -m pytest optimize/test_instruments_comex.py -q`
Expected: FAIL (`TOKENS` is `("NQ","ES")`; unknown GC/SI).

- [ ] **Step 3a: Add GC/SI to the all-stocks registry, box pointing at the SHIFTED file**

In `subprojects/all-stocks-signals/instruments.py`, after the `_box(...)` helper add a shifted-box helper and the
two entries. Insert this helper just below the existing `def _box(*parts): ...`:

```python
def _shifted_box(token: str) -> str:
    # COMEX GC/SI backtester reads the -1-workday-shifted box (spec D3) written by isolated_comex_box_shift.py
    return os.path.join(os.path.dirname(__file__), 'shifted_boxes', f'{token}_full_data_shifted.csv')
```

Then add these two entries inside the `REGISTRY = { ... }` dict (e.g. right after the `ES` entry):

```python
    'GC': Instrument(
        token='GC',
        candle_dir=_cdir('COMEX', 'GC_Continuous_Data'), candle_prefix='GC',
        box_csv=_shifted_box('GC')),
    'SI': Instrument(
        token='SI',
        candle_dir=_cdir('COMEX', 'SI_Continuous_Data'), candle_prefix='SI',
        box_csv=_shifted_box('SI')),
```

- [ ] **Step 3b: Add GC/SI to the engine-facing instruments facade**

In `subprojects/Parametric-Indicators/optimize/instruments.py`, change the two constants:

```python
TOKENS: tuple[str, ...] = ("NQ", "ES", "GC", "SI")
POINT_VALUE: dict[str, float] = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd subprojects/Parametric-Indicators && python3 -m pytest optimize/test_instruments_comex.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Verify a scaled-permissive backtest resolves + golden stays green**

Run (backtester resolves GC/SI data and produces finite trades/PnL with the auto default):

```bash
cd subprojects/Parametric-Indicators
python3 -c "
from optimize import data, instruments
from optimize.l2 import payload
for tok in ('GC','SI'):
    df_dec, df1, box, vf, n = data.load_inputs('4h', tok)
    d = payload.instrument_l1_default(tok, '4h')
    print(tok, 'bars', len(df_dec), 'box_rows', len(box), 'default_keys', sorted(d)[:4])
    assert len(df_dec) > 100 and len(box) > 100
print('OK resolve')
"
python3 perf/check_golden.py
```
Expected: prints `GC …`, `SI …`, `OK resolve`; then `check_golden.py` = **6/6 byte-identical**. If golden is not
6/6 → HARD STOP.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading
git -C subprojects/all-stocks-signals add instruments.py
git -C subprojects/Parametric-Indicators add optimize/instruments.py optimize/test_instruments_comex.py
git -C subprojects/Parametric-Indicators commit -m "feat(instrument): register GC+SI (pv 100/5000, shifted box); golden 6/6"
git -C subprojects/all-stocks-signals commit -m "feat(registry): add COMEX GC+SI (backtester reads shifted box)"
```

---

### Task 4: Optimizer smoke test (gc1 / si1) + GATE

**Files:**
- Create: `subprojects/Parametric-Indicators/docs/GOLDSILVER_ONBOARDING_STATUS.md` (status + gate note)
- (No engine changes — the optimizer already threads `instrument`, scales bounds via `_bounds_for`, uses
  `point_value`.)

**Interfaces:**
- Consumes: registered GC/SI from Task 3.
- Produces: two Optuna studies `gc1_4h` / `si1_4h` each with ≥1 completed trial; a status doc naming the gate.

- [ ] **Step 1: Run the 1-trial local smoke test for GC**

Run (tiny: 1 trial, 2 folds — proves wiring only, NOT a campaign):

```bash
cd subprojects/Parametric-Indicators
python3 optimize/optimizer.py 4h --trials 1 --folds 2 --study-prefix gc1 --instrument GC
```
Expected: `[4h] loading inputs (GC, pv=100) ...`, a decision-bars line, one trial runs, exits 0 with a summary
dict (`n_trials` ≥ 1). Any traceback → STOP and debug (do not proceed to the gate).

- [ ] **Step 2: Run the 1-trial local smoke test for SI**

Run:

```bash
cd subprojects/Parametric-Indicators
python3 optimize/optimizer.py 4h --trials 1 --folds 2 --study-prefix si1 --instrument SI
```
Expected: `[4h] loading inputs (SI, pv=5000) ...`, one trial completes, exit 0.

- [ ] **Step 3: Write the status / gate doc**

```markdown
# Gold (GC) + Silver (SI) Onboarding — Status

**Date:** 2026-07-04  ·  **Branch:** stocks-drop-down-backtester-optimizer

## Done (prep, local only)
- Data placed under ALL_STOCKS/{CANDLES,BOXS}/COMEX for GC + SI (7 TF each + boxes).
- Boxes shifted -1 workday (isolated_comex_box_shift.py) → shifted_boxes/{GC,SI}_full_data_shifted.csv.
- Signals generated + validated + packaged: {GC,SI}_SIGNALS_DELIVERY.
- Registered GC (pv 100) + SI (pv 5000) in both registries; backtester reads the SHIFTED box (spec D3).
- Dashboard dropdown lists GC/SI; scaled-permissive default backtests both.
- Golden 6/6 byte-identical (NQ untouched).
- Optimizer wiring proven: gc1_4h + si1_4h studies each ran a 1-trial local smoke test.

## GATE — awaiting explicit user go before server compute
Real per-instrument campaigns are NOT started. Proposed when approved:
- Run on the AMD server (never local). Prefixes gc1 / si1 (or a fresh pair per run).
- Suggest `--auto-trials` (budget ∝ search dimensions) on 4h first, then other TFs.
- After each: extract champion → wsh4_champions_full_{GC,SI}.json → verify dashboard default → 2026 OOS.
```

- [ ] **Step 4: Golden re-check + commit**

```bash
cd subprojects/Parametric-Indicators
python3 perf/check_golden.py     # expect 6/6
git add docs/GOLDSILVER_ONBOARDING_STATUS.md
git commit -m "docs(onboarding): GC+SI prep complete (signals+registry+optimizer smoke); GATE before server campaigns"
```

- [ ] **Step 5: STOP — report to user and wait**

Report: prep done, golden 6/6, both smoke tests green, and ask for explicit go (+ trial budget) before any
server-side optimization. Do not launch campaigns in this plan.

---

## Self-Review

**Spec coverage:** D1 placement → Task 1. D2 shift → Task 2. D3 shifted-box-in-backtester → Task 3 (test asserts
it). D4 tokens → Task 3. D5 signal gen/validate/package → Task 2. D6 optimizer prefixes + smoke → Task 4. D7 gate
→ Task 4 Steps 3+5. Testing/safety (golden, invariants, resolve smoke, sensitive files) → Tasks 2–4. All covered.

**Placeholder scan:** none — every code/command step is concrete.

**Type consistency:** `COMEX` dict shape (`candle_dir/prefix/box`) consistent across Task 2 + its test; `shift_box`
signature matches its test; `resolve_paths` return `(dec, minute, box)` matches Task 3 test; `TOKENS` tuple order
`("NQ","ES","GC","SI")` consistent between Task 3 impl + test.

**Box-column check (D1 test):** verified — NQ and GC/SI `_full_data.csv` both carry the same 53 columns
(including `Date`, `Scraped_At`, `dOpen`… through the W/M target columns), so `test_boxes_present_and_shaped`'s
exact-equality assertion holds as written. No relaxation needed.

---

## REVISION 2 (2026-07-04) — user-expanded scope: shift ES too + save a reusable pipeline

The user amended scope after approving the design:
1. **Shift ES as well** (not just GC/SI). ES currently reads its **raw** box; re-point it to a **shifted** box so
   ALL non-NQ instruments are consistently −1-workday-shifted. **NQ stays raw** (frozen golden anchor — never
   shifted). Shift set = **{ES, GC, SI}**.
2. **Save a reusable onboarding pipeline** any future stock follows, with a built-in **STEP 0 human-gate**: before
   onboarding a new stock, confirm with the user "same pipeline or a modified one?" then follow the chosen path.

### Deltas to the tasks above

- **Generalize, don't hardcode.** Instead of the GC/SI-only `isolated_comex_box_shift.py`, build a config-driven
  `subprojects/all-stocks-signals/onboard_stock.py` that takes an **instrument spec** and does shift → generate →
  validate → package for ANY token. The GC/SI-only script in Task 2 above is superseded by this generalized one;
  its `shift_box`/`generate`/`validate`/`package` bodies are reused verbatim (only the instrument table becomes a
  parameter). Drive it from a small `ONBOARD` dict covering `ES`, `GC`, `SI`.
- **Task 1 (data placement):** ES candles + raw box are ALREADY on disk (`ALL_STOCKS/CANDLES/CME/ES_Continuous_Data`,
  `ALL_STOCKS/BOXS/CME/ES/ES_full_data.csv`). Only GC/SI need placing. ES just needs shifting + re-wiring.
- **Task 3 (registration) additions:**
  - `optimize/instruments.py` `TOKENS = ("NQ","ES","GC","SI")`, add GC/SI point values (ES already 50.0).
  - **Update the existing** `optimize/test_instruments.py::test_tokens_and_point_values` (currently asserts
    `("NQ","ES")`) → `("NQ","ES","GC","SI")` + GC 100 / SI 5000. (This is the ONLY pre-existing test the change
    breaks; verified all other ES tests check candle medians/structure, unaffected by a box shift.)
  - In `all-stocks-signals/instruments.py`, **re-point ES's `box_csv`** from `_box('CME','ES','ES_full_data.csv')`
    to `_shifted_box('ES')` (same shifted-box helper GC/SI use).
  - **Rename the stale ES champion:** `optimize/results/wsh4_champions_full_ES.json` →
    `wsh4_champions_full_ES.stale-rawbox.json` (keep for history) so `instrument_l1_default("ES")` falls back to
    the scaled-permissive default until ES is re-optimized on the shifted box. Add a one-line note in the status
    doc that ES's Jun-30 pareto set (`*_wsi_pareto_ES.*`) is now raw-box history, pending re-opt.
- **New Task 5 — reusable pipeline SOP.** Create `subprojects/all-stocks-signals/NEW_STOCK_ONBOARDING_SOP.md`
  documenting the exact repeatable steps (place data → `onboard_stock.py` shift+signals → register in both
  registries → golden 6/6 → optimizer smoke → GATE server campaigns), led by:
  > **STEP 0 (human-gate):** When a new stock arrives, confirm with the user: *use this same pipeline, or a
  > modified one?* Do not run until they choose. Default map: box shift = −1 workday; point-value must be
  > confirmed per contract (full vs micro); NQ is never shifted.
- **Task 4 (smoke) additions:** also run an ES 1-trial smoke on the shifted box (`--study-prefix es_shift1
  --instrument ES`) to prove the re-wire; status doc lists ES re-opt among the gated campaigns.

### Revised safety notes
- Golden stays NQ-only 6/6 (NQ untouched) — unchanged gate.
- Shifting ES changes ES backtest/optimization results (expected). No ES exact-number test breaks; the stale
  champion is retired to fallback (documented), not silently served on mismatched data.
