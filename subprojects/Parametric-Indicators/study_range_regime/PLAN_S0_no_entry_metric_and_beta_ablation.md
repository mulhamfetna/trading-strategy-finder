# S0 (no-entry metric) + β (indicator ablation) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) or
> superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a warmup-attributed no-entry-streak metric to the engine (S0), then an isolated tool (β) that
exhaustively backtests all 2⁸ subsets of the wsh4 1-min 4h champion's 8 indicators and reports which can be
dropped — with PnL/DD/decision-pause/data-footprint per subset.

**Architecture:** S0 = a pure helper (`optimize/no_entry.py`) + additive keys in `backtest_metrics`. β =
`optimize/ablate_indicators.py` reusing the golden engine path + `two_stage._Ctx` loader, parallel over 256
subsets. No engine logic change (only additive metric output) → golden byte-identical.

**Tech Stack:** Python, numpy, multiprocessing, the existing `optimize/{core,fast_engine,folds,two_stage}.py`
+ `indicators/library.py`. Spec: `study_range_regime/SPEC_S0_no_entry_metric_and_beta_ablation.md`.

**Working dir (all paths):** `/mnt/data/projects/trading/subprojects/Parametric-Indicators/`. Commits are
SKIPPED per the standing "commit only when asked" rule — implement + test only.

---

## Key facts (from code exploration)
- `backtest_metrics(df_dec, df1, box, vf, n_split, params, bar_td, sig_int)` returns a dict; `trades=taken`
  where each `taken` item is `{"pnl","eq","dd","year"}` (core.py:144) built from `cand` (fast_backtest) whose
  items carry `entry_idx` (fast_engine.py:143). → add `entry_idx` to the `taken` dict.
- Indicators: `library.from_specs(specs)` → instances; each has `.warmup_bars()` (in **1-min candles when
  ind_1min**, else decision bars) and `.enabled`. `library.REGISTRY` has 18 keys.
- TF: `bar_td` is a `pd.Timedelta`; minutes = `bar_td.total_seconds()/60` (4h → 240), hours = `/3600`.
- Champion source: `optimize/results/wsh4_champions_full.json["4h"]` → `{box, indicators[…enabled…]}`,
  8 enabled: bollinger, cci, keltner, mfi, obv, order_block, sma_trend, structure_trend. Golden full P/L
  **$142,203**.

---

## File structure
| File | Responsibility |
|---|---|
| `optimize/no_entry.py` | **NEW** pure helper: `no_entry_metrics(entry_indices, n_bars, warmup_decision_bars, bar_hours)` → metric dict |
| `optimize/core.py` | **MODIFY** `backtest_metrics`: add `entry_idx` to taken; compute warmup; call helper; merge additive keys |
| `optimize/ablate_indicators.py` | **NEW** β: load champion, enumerate 256 subsets, parallel backtest, rank, write report |
| `optimize/test_no_entry_metric.py` | **NEW** S0 unit lock |
| `optimize/test_ablate.py` | **NEW** β unit lock |
| `optimize/results/ablation_wsi1m_4h.json` | β output (raw 256 rows) |
| `study_range_regime/REPORT_indicator_ablation_wsi1m_4h.md` | β output (ranked report, Mermaid) |

---

## Task S0.1 — pure no-entry helper
**Files:** Create `optimize/no_entry.py`, `optimize/test_no_entry_metric.py`

- [ ] **Step 1: failing test** (`test_no_entry_metric.py`)
```python
from optimize.no_entry import no_entry_metrics

def test_basic_gap_and_decision_split():
    # entries at bars 0, 10, 50, 55 over 100 bars; warmup boundary at 12 decision bars; 4h ⇒ 6 bars/day
    m = no_entry_metrics([0, 10, 50, 55], n_bars=100, warmup_decision_bars=12, bar_hours=4.0)
    # gaps between consecutive entries: 10, 40, 5 ; leading gap (0-0)=0
    assert m["max_no_entry_bars"] == 40
    assert round(m["max_no_entry_days"], 2) == round(40 * 4 / 24, 2)
    # decision gaps START at/after bar 12 ⇒ the 10→50 gap (starts at 10 < 12? start=10 -> excluded) ; the 50->55 (start 50) =5
    # the 10->50 gap starts at bar 10 (<12) so it straddles warmup ⇒ excluded; decision max = 5
    assert m["max_no_entry_bars_decision"] == 5
    assert m["longest_gap_source"] == "warmup" if 40 <= 12 else "decision"   # overall max 40 starts at bar10<12 ⇒ source warmup? see rule
    assert m["first_entry_bar"] == 0

def test_no_trades():
    m = no_entry_metrics([], n_bars=100, warmup_decision_bars=5, bar_hours=4.0)
    assert m["max_no_entry_bars"] == 0 and m["max_no_entry_bars_decision"] == 0
    assert m["first_entry_bar"] is None

def test_trailing_excluded_from_decision():
    m = no_entry_metrics([20, 30], n_bars=100, warmup_decision_bars=0, bar_hours=4.0)
    # trailing gap 30->99 = 69 reported but NOT in decision max (decision max = gap 20->30 = 10)
    assert m["trailing_no_entry_bars"] == 69
    assert m["max_no_entry_bars_decision"] == 10
```
- [ ] **Step 2: run → fail** `python3 -m pytest optimize/test_no_entry_metric.py -q` → ImportError.
- [ ] **Step 3: implement** (`no_entry.py`). **Rules:** a "gap" is the bar-distance between consecutive
      entries; the leading gap is `first_entry − 0`. A gap is **decision-phase** iff its START index `≥
      warmup_decision_bars` (so any gap straddling/within warmup is excluded — warmup is the one-time startup
      we don't optimize). The trailing gap (last entry → `n_bars−1`) is reported but excluded from decision.
      `longest_gap_source` = `"warmup"` if the overall-longest gap starts before `warmup_decision_bars`, else
      `"decision"`.
```python
"""Pure no-entry-streak metric with warmup-vs-decision attribution (S0). No engine/data deps."""
from __future__ import annotations
import math


def no_entry_metrics(entry_indices, n_bars, warmup_decision_bars=0, bar_hours=4.0) -> dict:
    days = lambda bars: round(bars * bar_hours / 24.0, 3)
    idx = sorted(int(i) for i in entry_indices)
    out = {"first_entry_bar": (idx[0] if idx else None),
           "warmup_decision_bars": int(warmup_decision_bars),
           "warmup_days": days(warmup_decision_bars)}
    if not idx:
        out.update(max_no_entry_bars=0, max_no_entry_days=0.0,
                   max_no_entry_bars_decision=0, max_no_entry_days_decision=0.0,
                   trailing_no_entry_bars=0, trailing_no_entry_days=0.0, longest_gap_source="none")
        return out
    # gaps between consecutive entries (+ leading gap from bar 0); each is (start_idx, length)
    gaps = [(0, idx[0])]
    for a, b in zip(idx, idx[1:]):
        gaps.append((a, b - a))
    trailing = (idx[-1], (n_bars - 1) - idx[-1])     # reported, excluded from decision
    inter = gaps                                     # leading + between-entry gaps
    max_bars = max((g[1] for g in inter), default=0)
    longest = max(inter, key=lambda g: g[1]) if inter else (0, 0)
    decision = [g for g in inter if g[0] >= warmup_decision_bars]
    max_dec = max((g[1] for g in decision), default=0)
    out.update(
        max_no_entry_bars=int(max_bars), max_no_entry_days=days(max_bars),
        max_no_entry_bars_decision=int(max_dec), max_no_entry_days_decision=days(max_dec),
        trailing_no_entry_bars=int(trailing[1]), trailing_no_entry_days=days(trailing[1]),
        longest_gap_source=("warmup" if longest[0] < warmup_decision_bars else "decision"))
    return out
```
- [ ] **Step 4: run → pass.** (Fix the test's `longest_gap_source` assertion to the rule: overall max gap
      (40) starts at bar 10 < 12 ⇒ `"warmup"`.) Re-run → PASS.

## Task S0.2 — wire into `backtest_metrics` (additive; golden-safe)
**Files:** Modify `optimize/core.py`

- [ ] **Step 1:** In the `taken.append({...})` (core.py:144), add the entry index:
```python
        taken.append({"pnl": pnl, "eq": eq, "dd": dd,
                      "year": pd.Timestamp(t["exit_time"]).year, "entry_idx": int(t["entry_idx"])})
```
- [ ] **Step 2:** Just before the `return dict(...)` (core.py:160), compute the metric. Add:
```python
    # S0: warmup-attributed no-entry-streak (additive — never changes existing values).
    from optimize.no_entry import no_entry_metrics
    from indicators import library as _lib
    _specs = [s for s in params.get("indicators", []) if s.get("enabled")]
    _warm_native = 0
    try:
        _warm_native = max((i.warmup_bars() for i in _lib.from_specs(_specs)), default=0)
    except Exception:
        _warm_native = 0
    _bar_min = bar_td.total_seconds() / 60.0
    # ind_1min ⇒ warmup is in 1-MIN candles → convert to decision bars; else already decision bars.
    _warm_dec = math.ceil(_warm_native / _bar_min) if params.get("ind_1min") else int(_warm_native)
    _ne = no_entry_metrics([t["entry_idx"] for t in taken], n_bars=len(df_dec),
                           warmup_decision_bars=_warm_dec, bar_hours=bar_td.total_seconds() / 3600.0)
    _ne["data_footprint_candles"] = int(_warm_native)         # issue 3: live-trader history buffer
    _ne["warmup_frame"] = "1min" if params.get("ind_1min") else "decision"
```
      Add `import math` at the top of `core.py` if absent. Then merge into the return dict by adding
      `**_ne` as the last argument of `return dict(... , trades=taken, **_ne)`.
- [ ] **Step 3: golden check** `python3 perf/check_golden.py` → Expected: **ALL 6 MATCH** (additive keys
      don't touch pnl/dd/n/indicators).
- [ ] **Step 4: sanity on the champion** — run the champion 4h full backtest and print the new keys:
```bash
python3 -c "
import warnings; warnings.filterwarnings('ignore')
from optimize import two_stage as TS
ctx = TS._Ctx('4h', split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=True)
m = ctx.evaluate(ctx.build_params(ctx.champ_en, ctx.champ_flip, ctx.champ_cont))
" 2>/dev/null
```
      Expected: runs without error. (The metric is exercised end-to-end in β.) NOTE: `_Ctx.evaluate`
      returns a trimmed dict; to see the raw keys, β calls `backtest_metrics` directly (Task β.2).

## Task β.1 — champion loader + 256-subset enumeration + param builder
**Files:** Create `optimize/ablate_indicators.py`, `optimize/test_ablate.py`

- [ ] **Step 1: failing test** (`test_ablate.py`)
```python
import warnings; warnings.filterwarnings("ignore")
from optimize import ablate_indicators as AB

def test_enumerate_256():
    champ = AB.load_champion("4h")
    subs = AB.subsets(champ["enabled_keys"])
    assert len(champ["enabled_keys"]) == 8
    assert len(subs) == 256
    assert frozenset() in subs and frozenset(champ["enabled_keys"]) in subs   # all-off and all-on present
    assert len(set(subs)) == 256                                              # distinct

def test_build_params_masks_enabled():
    champ = AB.load_champion("4h")
    keep = frozenset(list(champ["enabled_keys"])[:3])
    p = AB.build_params(champ, keep)
    on = {s["key"] for s in p["indicators"] if s["enabled"]}
    assert on == set(keep)                          # only the kept subset is enabled
    assert p["ind_1min"] is True and p["sl_soft"] == champ["box"]["sl_soft"]
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** the loader + enumeration + param builder in `ablate_indicators.py`:
```python
"""β — exhaustive indicator ablation of the wsh4 1-min 4h champion. All 2^8 subsets, full-period, parallel.
Reuses the golden engine path (backtest_metrics) + the two_stage._Ctx loader. Reports which indicators drop."""
from __future__ import annotations
import json, itertools, sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from indicators import library

_CHAMPS = _HERE / "results" / "wsh4_champions_full.json"


def load_champion(tf: str = "4h") -> dict:
    c = json.loads(_CHAMPS.read_text())[tf]
    enabled = [s["key"] for s in c["indicators"] if s.get("enabled")]
    params_by_key = {s["key"]: s.get("params", {}) for s in c["indicators"]}
    modes = {s["key"]: s.get("mode", library.SCHEMA[s["key"]]["mode"]) for s in c["indicators"]}
    return {"tf": tf, "box": c["box"], "enabled_keys": enabled,
            "params_by_key": params_by_key, "modes": modes, "indicators_raw": c["indicators"]}


def subsets(enabled_keys) -> list:
    keys = list(enabled_keys)
    out = []
    for r in range(len(keys) + 1):
        for combo in itertools.combinations(keys, r):
            out.append(frozenset(combo))
    return out


def build_params(champ: dict, keep: frozenset) -> dict:
    box = champ["box"]
    specs = [{"key": k, "enabled": (k in keep), "mode": champ["modes"].get(k, library.SCHEMA[k]["mode"]),
              "params": dict(champ["params_by_key"].get(k, {}))} for k in champ["enabled_keys"]]
    return dict(sl_soft=box["sl_soft"], sl_hard=box["sl_hard"], tp=box["tp"], gate_pct=box["gate_pct"],
                dd_limit=box["dd_limit"], cooldown=int(box["cooldown"]), flip=bool(box["flip"]),
                window="full", indicators=specs, k=int(box["k"]), ind_1min=True)
```
- [ ] **Step 4: run → pass. (β.1)**

## Task β.2 — per-subset evaluation + parallel runner
**Files:** Modify `optimize/ablate_indicators.py`, `optimize/test_ablate.py`

- [ ] **Step 1: failing test** (stub eval returns the new keys)
```python
def test_eval_row_shape(monkeypatch):
    champ = AB.load_champion("4h")
    # monkeypatch the engine eval to a stub so the test is fast + offline
    monkeypatch.setattr(AB, "_evaluate_full", lambda params: {
        "pnl": 100.0, "max_dd": 10.0, "win": 70.0, "pf": 1.5, "n_taken": 5,
        "max_no_entry_days_decision": 2.0, "max_no_entry_days": 2.0, "longest_gap_source": "decision",
        "warmup_days": 0.1, "data_footprint_candles": 346})
    row = AB.eval_subset(champ, frozenset(list(champ["enabled_keys"])[:2]))
    assert row["n_indicators"] == 2 and set(row["kept"]) <= set(champ["enabled_keys"])
    assert {"pnl","max_dd","win","decision_pause_days","data_footprint_candles","kept"} <= set(row)
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** `_evaluate_full` (loads context once per worker) + `eval_subset` + `run_all`:
```python
import os
from concurrent.futures import ProcessPoolExecutor

_CTX = None   # per-process loaded-once engine context

def _ctx(tf):
    global _CTX
    if _CTX is None:
        from optimize import two_stage as TS
        _CTX = TS._Ctx(tf, split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=False)
    return _CTX

def _evaluate_full(params: dict) -> dict:
    """Full-period backtest via the golden engine path; returns backtest_metrics dict (+ S0 keys)."""
    from optimize.core import backtest_metrics
    c = _ctx(params["_tf"])
    p = {k: v for k, v in params.items() if k != "_tf"}
    return backtest_metrics(c.df_dec, c.df1, c.box, c.vf, c.n_split, dict(p, window="full"),
                            c.tf.bar_td, sig_int=c.sig_int)

def eval_subset(champ: dict, keep: frozenset) -> dict:
    params = build_params(champ, keep); params["_tf"] = champ["tf"]
    m = _evaluate_full(params)
    return {"kept": sorted(keep), "n_indicators": len(keep), "dropped": sorted(set(champ["enabled_keys"]) - keep),
            "pnl": m.get("pnl", 0.0), "max_dd": m.get("max_dd", 0.0), "win": m.get("win", 0.0),
            "pf": m.get("pf"), "n_taken": m.get("n_taken", 0),
            "decision_pause_days": m.get("max_no_entry_days_decision", 0.0),
            "overall_pause_days": m.get("max_no_entry_days", 0.0),
            "pause_source": m.get("longest_gap_source", "?"),
            "warmup_days": m.get("warmup_days", 0.0),
            "data_footprint_candles": m.get("data_footprint_candles", 0)}

def _eval_one(args):
    champ, keep = args
    return eval_subset(champ, keep)

def run_all(tf: str = "4h", workers: int = 10) -> list:
    champ = load_champion(tf)
    subs = subsets(champ["enabled_keys"])
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row in ex.map(_eval_one, [(champ, s) for s in subs]):
            rows.append(row)
    return rows
```
- [ ] **Step 4: run → pass. (β.2)**

## Task β.3 — ranking + report writers
**Files:** Modify `optimize/ablate_indicators.py`, `optimize/test_ablate.py`

- [ ] **Step 1: failing test**
```python
def test_rank_and_marginal():
    base = {"kept": ["a","b"], "n_indicators": 2, "dropped": [], "pnl": 100.0, "max_dd": 10.0,
            "win": 70.0, "pf": 1.5, "n_taken": 5, "decision_pause_days": 2.0, "overall_pause_days": 2.0,
            "pause_source": "decision", "warmup_days": 0.1, "data_footprint_candles": 300}
    drop_one = dict(base, kept=["a"], n_indicators=1, dropped=["b"], pnl=98.0)
    ranked = AB.rank([base, drop_one], baseline_pnl=100.0, drop_bonus=5000.0)
    assert ranked[0]["kept"] == ["a"]                     # 98 + 5000*1 > 100 + 0 ⇒ dropping 1 wins
    assert ranked[0]["delta_pnl_pct"] == -2.0
    marg = AB.marginal_impact([base, drop_one], ["a","b"])
    assert "b" in marg
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** `rank`, `marginal_impact`, `write_json`, `write_report`:
```python
DROP_BONUS = 5000.0   # $ credited per indicator dropped, for the ranking score (documented, tunable)

def rank(rows, baseline_pnl, drop_bonus=DROP_BONUS):
    for r in rows:
        r["delta_pnl_pct"] = round(100.0 * (r["pnl"] - baseline_pnl) / baseline_pnl, 2) if baseline_pnl else 0.0
        r["score"] = r["pnl"] + drop_bonus * len(r["dropped"])
    return sorted(rows, key=lambda r: r["score"], reverse=True)

def marginal_impact(rows, keys):
    """Mean pnl WITH vs WITHOUT each indicator across all subsets → avg ΔPnL of removing it."""
    out = {}
    for k in keys:
        with_k = [r["pnl"] for r in rows if k in r["kept"]]
        without_k = [r["pnl"] for r in rows if k not in r["kept"]]
        out[k] = {"avg_pnl_with": round(sum(with_k)/len(with_k), 0) if with_k else 0.0,
                  "avg_pnl_without": round(sum(without_k)/len(without_k), 0) if without_k else 0.0}
        out[k]["avg_drop_cost"] = round(out[k]["avg_pnl_with"] - out[k]["avg_pnl_without"], 0)
    return out

def write_json(rows, path):
    Path(path).write_text(json.dumps(rows, indent=2)); return path

def write_report(ranked, marg, champ, baseline, path, top=40):
    L = []
    L.append("# Indicator ablation — wsh4 1-min 4h champion\n")
    L.append(f"Baseline (all {len(champ['enabled_keys'])} on) = **${baseline:,.0f}** P/L. "
             f"All {len(ranked)} subsets backtested full-period (ind_1min). Ranked by "
             f"score = PnL + ${DROP_BONUS:,.0f}/indicator-dropped (no hard filter — pick by eye).\n")
    L.append("| rank | kept | #drop | PnL | ΔPnL% | maxDD | win% | decision-pause d | source | footprint(1m) |")
    L.append("|--:|---|--:|--:|--:|--:|--:|--:|---|--:|")
    for i, r in enumerate(ranked[:top], 1):
        L.append(f"| {i} | {','.join(r['kept']) or '(none)'} | {len(r['dropped'])} | ${r['pnl']:,.0f} | "
                 f"{r['delta_pnl_pct']:+.1f} | ${r['max_dd']:,.0f} | {r['win']:.1f} | "
                 f"{r['decision_pause_days']:.1f} | {r['pause_source']} | {r['data_footprint_candles']} |")
    L.append(f"\n_… {max(0,len(ranked)-top)} more rows in the JSON._\n")
    L.append("## Per-indicator marginal impact (avg ΔPnL when removed)\n")
    L.append("| indicator | avg PnL with | avg PnL without | avg drop cost |\n|---|--:|--:|--:|")
    for k, v in sorted(marg.items(), key=lambda kv: kv[1]["avg_drop_cost"]):
        L.append(f"| {k} | ${v['avg_pnl_with']:,.0f} | ${v['avg_pnl_without']:,.0f} | ${v['avg_drop_cost']:,.0f} |")
    Path(path).write_text("\n".join(L) + "\n"); return path
```
- [ ] **Step 4: run → pass. (β.3)**

## Task β.4 — `main()` + full run (acceptance smoke)
**Files:** Modify `optimize/ablate_indicators.py`

- [ ] **Step 1:** add `main()`:
```python
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="β indicator ablation")
    ap.add_argument("--tf", default="4h"); ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--drop-bonus", type=float, default=DROP_BONUS); ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    champ = load_champion(a.tf)
    rows = run_all(a.tf, workers=a.workers)
    baseline = next(r["pnl"] for r in rows if len(r["kept"]) == len(champ["enabled_keys"]))
    assert abs(baseline - 142203) < 50, f"baseline {baseline} != golden 142,203 — loader/params wrong"
    ranked = rank(rows, baseline, a.drop_bonus)
    marg = marginal_impact(rows, champ["enabled_keys"])
    write_json(rows, _HERE / "results" / f"ablation_wsi1m_{a.tf}.json")
    write_report(ranked, marg, champ, baseline,
                 _PI / "study_range_regime" / f"REPORT_indicator_ablation_wsi1m_{a.tf}.md", top=a.top)
    print(f"ablation done: {len(rows)} subsets; baseline ${baseline:,.0f}; report written")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```
- [ ] **Step 2: full run (acceptance smoke, ~6–10 min, run in background):**
      `python3 -m optimize.ablate_indicators --tf 4h --workers 10`
      Expected: prints `baseline $142,203` (assert passes), writes the JSON + report. If the baseline assert
      fails, STOP — the champion loader/params don't reproduce golden (fix before trusting any row).
- [ ] **Step 3:** open `study_range_regime/REPORT_indicator_ablation_wsi1m_4h.md`; confirm it ranks subsets,
      shows ΔPnL%/decision-pause/footprint, and the per-indicator marginal table. Sanity: the all-on row's
      decision-pause should reveal whether the ~14-day pause is `decision` or `warmup` sourced.

## Task FINAL — doc + tracker
**Files:** Create `study_range_regime/UPDATE_S0_beta_no_entry_and_ablation.md`; update megadoc
- [ ] Write a verbose Mermaid doc (metric definition incl. warmup/decision attribution, the ablation
      method, the headline finding: which indicators are droppable + pause source). Update
      `SYSTEM_UPDATES_MEGADOC.md` index. (No commit unless asked.)

---

## Self-review
- **Spec coverage:** S0 metric+attribution → S0.1/S0.2; warmup-vs-decision (D6) → no_entry.py rule + ind_1min
  conversion in core; 256 subsets (D7) → β.1; full-period (D4) → β.2 `_evaluate_full`; ranked report no-filter
  (D5) → β.3 `rank`/`write_report`; data-footprint (issue 3) → `data_footprint_candles`; golden-safe → S0.2
  step 3; baseline $142,203 anchor → β.4 assert. All covered.
- **Placeholders:** none — every step has runnable code/commands.
- **Type consistency:** `no_entry_metrics(entry_indices, n_bars, warmup_decision_bars, bar_hours)` keys used
  identically in core.py merge and β `eval_subset`; `load_champion`→`subsets`→`build_params`→`eval_subset`→
  `rank`/`marginal_impact`→`write_*` signatures consistent across β tasks.
