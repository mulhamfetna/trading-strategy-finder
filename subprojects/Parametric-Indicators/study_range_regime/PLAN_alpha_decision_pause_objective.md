# α — decision-pause objective + escalating ladder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use `- [ ]`.

**Goal:** Swap the optimizer's 3rd objective (win-rate → minimize the recurring decision-pause) on the
wsh4-era space, and drive it as a user-gated fastest→slowest ladder to find the shortest pause at ≥95% of the
champion's P/L.

**Architecture:** Default-off flags on `optimizer.py` (`--objective`, `--exclude-indicators`,
`--only-indicators`) reading the S0 `max_no_entry_days_decision` key already in `backtest_metrics`. A
`run_alpha_ladder.py` defines the 3 tiers, runs Tier 1 locally + reports, and emits the server commands for
Tiers 2–3 (user-gated). No engine logic change → golden 6/6 holds.

**Tech Stack:** existing `optimize/optimizer.py` (Optuna NSGA-III), `optimize/no_entry.py` (S0), pytest.
**Working dir:** `/mnt/data/projects/trading/subprojects/Parametric-Indicators/`. Commits SKIPPED (commit only
when asked). Spec: `study_range_regime/SPEC_alpha_decision_pause_objective.md`.

---

## Task α.1 — `--objective` swap (win-rate ↔ min decision-pause)
**Files:** Modify `optimize/optimizer.py`, Create `optimize/test_alpha_objective.py`

- [ ] **Step 1: failing test** (`test_alpha_objective.py`)
```python
import warnings; warnings.filterwarnings("ignore")
import inspect
from optimize import optimizer as O

def test_run_has_objective_param():
    assert "objective" in inspect.signature(O.run).parameters
    # default must be the win-rate path (byte-identical to today)
    assert inspect.signature(O.run).parameters["objective"].default == "winrate"
```
- [ ] **Step 2: run → fail** `python3 -m pytest optimize/test_alpha_objective.py -q`.
- [ ] **Step 3: implement** — thread `objective` into `run()` + the closure. In the `def run(...)` signature
      (line 267) add `objective: str = "winrate", exclude_inds: tuple = (), only_inds: tuple = ()`. Replace the
      objective tail (lines 320–329) with:
```python
        full_pnl = float(full["pnl"]); full_dd = float(full["max_dd"])
        dec_pause = float(full.get("max_no_entry_days_decision", full.get("max_no_entry_days", 0.0)))
        trial.set_user_attr("worst_dd", worst_dd)
        trial.set_user_attr("median_pnl", r["median_pnl"])
        trial.set_user_attr("median_win", med_win)
        trial.set_user_attr("full_pnl", full_pnl)
        trial.set_user_attr("full_dd", full_dd)
        trial.set_user_attr("decision_pause_days", dec_pause)
        trial.set_user_attr("constraint", [float(full_dd - DD_PNL_CAP * full_pnl)])
        # 3 objectives, all maximised. Default 3rd = win-rate; objective='decision_pause' swaps it to
        # -decision_pause (maximising the negative ⇒ minimising the recurring no-entry pause). directions unchanged.
        third = (-dec_pause) if objective == "decision_pause" else med_win
        return r["median_pnl"], -worst_dd, third
```
- [ ] **Step 4: run → pass.**

## Task α.2 — indicator scope (`--exclude-indicators` / `--only-indicators`)
**Files:** Modify `optimize/optimizer.py`, `optimize/test_alpha_objective.py`

- [ ] **Step 1: failing test**
```python
def test_suggest_indicators_scope():
    from optimize import optimizer as O
    import optuna
    st = optuna.create_study(sampler=optuna.samplers.RandomSampler())
    t = st.ask()
    specs = O._suggest_indicators(t, exclude=("ifvg", "breaker", "cisd"),
                                  only=("cci", "order_block", "structure_trend"))
    on_possible = {s["key"] for s in specs if s.get("_searched")}
    assert on_possible == {"cci", "order_block", "structure_trend"}        # only these are searched
    assert all(s["enabled"] is False for s in specs if s["key"] in ("ifvg", "breaker", "cisd"))
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** — replace `_suggest_indicators` (lines 56–65) with a scoped version:
```python
def _suggest_indicators(trial, exclude=(), only=()):
    """Search en_<key> + params for each registered indicator, EXCEPT keys in `exclude` or (when `only` is
    non-empty) keys not in `only` — those are forced OFF with default params and NOT suggested (fewer dims).
    Mode = the schema default. `_searched` marks which keys actually entered the search (test hook)."""
    specs = []
    for key in library.REGISTRY:
        meta = library.SCHEMA[key]
        searched = (key not in exclude) and (not only or key in only)
        if not searched:
            params = {p["name"]: p["default"] for p in meta["params"]}
            specs.append({"key": key, "enabled": False, "mode": meta["mode"], "params": params, "_searched": False})
            continue
        enabled = trial.suggest_categorical(f"en_{key}", [False, True])
        params = {p["name"]: _suggest_param(trial, f"{key}_{p['name']}", p) for p in meta["params"]}
        specs.append({"key": key, "enabled": enabled, "mode": meta["mode"], "params": params, "_searched": True})
    return specs
```
      Then strip the `_searched` helper key before the spec is used by the engine: in `objective()` where
      `specs = _suggest_indicators(trial)` (line ~302) change to
      `specs = [{k: v for k, v in s.items() if k != "_searched"} for s in _suggest_indicators(trial, exclude_inds, only_inds)]`.
- [ ] **Step 4: run → pass.**

## Task α.3 — golden guard (objective default unchanged)
**Files:** none (verification)
- [ ] **Step 1:** `python3 perf/check_golden.py` → Expected **ALL 6 MATCH** (default `objective="winrate"`,
      no scope ⇒ the search is byte-identical; the dashboard path is untouched regardless).
- [ ] **Step 2:** quick parity of the search tail — `python3 -c "from optimize import optimizer as O; import inspect; print('winrate' in inspect.getsource(O.run))"` → True.

## Task α.4 — warm-start the lean champion (extra seed)
**Files:** Modify `optimize/optimizer.py`

- [ ] **Step 1:** In `warm_start_seeds` (after the wsh5 split block), append the lean champion when present:
```python
    lean_f = _RESULTS_DIR / "wsh_lean_4h_champion.json"
    if lean_f.exists():
        try:
            c = json.loads(lean_f.read_text()).get(tf_name)
            if c:
                seeds.append(_native_seed(c["box"], c.get("indicators", {}), split_sltp, b))
        except Exception:
            pass
```
- [ ] **Step 2: verify** `python3 -c "from optimize import optimizer as O; import json; b=json.load(open('optimize/sl_tp_bounds.json'))['4h']; print(len(O.warm_start_seeds('4h', False, b)))"` → ≥ 2 (wsh4 + lean).

## Task α.5 — CLI flags + thread into run()
**Files:** Modify `optimize/optimizer.py`

- [ ] **Step 1:** add args in `main()` (after `--sampler`, line ~432):
```python
    ap.add_argument("--objective", default="winrate", choices=["winrate", "decision_pause"],
                    help="3rd objective: winrate* (unchanged) or decision_pause (minimise the recurring no-entry pause)")
    ap.add_argument("--exclude-indicators", default="", help="comma keys forced OFF (e.g. ifvg,breaker,cisd = wsh4-era)")
    ap.add_argument("--only-indicators", default="", help="comma keys; ONLY these are searched (others forced off)")
```
- [ ] **Step 2:** thread them through the `run(...)` call (line ~445):
```python
    _excl = tuple(x for x in a.exclude_indicators.split(",") if x)
    _only = tuple(x for x in a.only_indicators.split(",") if x)
    run(a.timeframe, n_trials=n_trials, folds=a.folds, min_trades=a.min_trades,
        ind_1min=a.ind_1min, study_prefix=a.study_prefix, split_sltp=a.split_sltp,
        warm_start=not a.no_warm_start, sampler=a.sampler,
        objective=a.objective, exclude_inds=_excl, only_inds=_only)
```
- [ ] **Step 3:** add `pause {ua.get('decision_pause_days',0):.1f}d` to the per-front print line (line ~395) so
      the front shows the pause column. Run `python3 -m optimize.optimizer 4h --plan --objective decision_pause`
      → Expected: plan prints, no error.

## Task α.6 — ladder runner + per-tier report
**Files:** Create `optimize/run_alpha_ladder.py`

- [ ] **Step 1: implement** the 3-tier runner. Tier 1 runs `optimizer.run` locally; Tiers 2–3 print the server
      command (user-gated). After a tier, write a report sorted by decision-pause.
```python
"""α ladder — user-gated, fastest→slowest. Tier 1 (lean-3, local) runs here; Tiers 2-3 emit the server
command to launch on the AMD box. Each tier writes REPORT_alpha_<tier>_decision_pause.md sorted by pause."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent; _PI = _HERE.parent
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
from optimize import optimizer as O
import optuna

LEAN = ("cci", "order_block", "structure_trend")
WSH4_MED = 33587.0; FLOOR = 0.95 * WSH4_MED      # highlight band (−5%)
TIERS = {
    "1": dict(prefix="wsh7a", only=LEAN, exclude=(), where="local",
              desc="lean-3 fixed ON, continuous knobs only (~7 dims)"),
    "2": dict(prefix="wsh7b", only=(), exclude=("ifvg", "breaker", "cisd"), where="server",
              desc="wsh4-era 15-indicator space"),
    "3": dict(prefix="wsh7c", only=(), exclude=("ifvg", "breaker", "cisd"), where="server",
              desc="wsh4-era 15-indicator space, bigger budget + lean seed"),
}

def _report(prefix, tf, path):
    st = optuna.load_study(study_name=f"{prefix}_{tf}", storage=O.study_storage.storage_url(O._db_for(tf, f"{prefix}_{tf}")))
    rows = []
    for t in st.trials:
        ua = t.user_attrs
        if t.values is None or any(v > 0 for v in ua.get("constraint", [1.0])):  # feasible only
            continue
        rows.append((ua.get("decision_pause_days", 9e9), ua.get("median_pnl", 0.0),
                     ua.get("full_pnl", 0.0), ua.get("full_dd", 0.0), ua.get("median_win", 0.0)))
    rows.sort(key=lambda r: (r[0], -r[1]))     # shortest pause, then best P/L
    L = [f"# α tier {prefix} — decision-pause front ({tf})\n",
         f"Feasible trials sorted by decision-pause. Highlight = shortest pause with median P/L ≥ ${FLOOR:,.0f}.\n",
         "| decision-pause d | median P/L | full P/L | full DD | win% |", "|--:|--:|--:|--:|--:|"]
    star = next((r for r in rows if r[1] >= FLOOR), None)
    for r in rows[:40]:
        mark = " ⭐" if r is star else ""
        L.append(f"| {r[0]:.1f}{mark} | ${r[1]:,.0f} | ${r[2]:,.0f} | ${r[3]:,.0f} | {r[4]:.1f} |")
    if star:
        L.append(f"\n**Shortest pause @ ≥95% P/L: {star[0]:.1f}d, median ${star[1]:,.0f}** (champion baseline 11.5d / $33,587).")
    Path(path).write_text("\n".join(L) + "\n"); return star

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=list(TIERS), required=True)
    ap.add_argument("--tf", default="4h"); ap.add_argument("--trials", type=int, default=800)
    a = ap.parse_args(); cfg = TIERS[a.tier]
    if cfg["where"] == "server":
        excl = ",".join(cfg["exclude"])
        print(f"TIER {a.tier} runs on the SERVER. Launch (after your go):")
        print(f"  WSH_PREFIX={cfg['prefix']} WSH_OBJECTIVE=decision_pause WSH_EXCLUDE={excl} "
              f"bash optimize/server/remote_wsi.sh run")
        return 0
    print(f"TIER {a.tier} ({cfg['desc']}) — running locally, prefix {cfg['prefix']} …")
    O.run(a.tf, n_trials=a.trials, ind_1min=True, study_prefix=cfg["prefix"], objective="decision_pause",
          only_inds=cfg["only"], exclude_inds=cfg["exclude"], warm_start=True)
    rep = _PI / "study_range_regime" / f"REPORT_alpha_tier{a.tier}_decision_pause.md"
    star = _report(cfg["prefix"], a.tf, rep)
    print(f"TIER {a.tier} DONE → {rep}. "
          + (f"shortest@95%P/L = {star[0]:.1f}d" if star else "no point ≥95% P/L")
          + ". PAUSED — review, then say 'go' for the next tier.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```
- [ ] **Step 2: verify import + server-tier dry print** `python3 -m optimize.run_alpha_ladder --tier 2`
      → prints the `WSH_OBJECTIVE=decision_pause WSH_EXCLUDE=ifvg,breaker,cisd …` server command, exits 0.

## Task α.7 — `remote_wsi.sh` env (server tiers, additive default-off)
**Files:** Modify `optimize/server/remote_wsi.sh`
- [ ] **Step 1:** mirror the `WSH_SAMPLER` pattern — add near it:
```bash
OBJ_ARG="${WSH_OBJECTIVE:+--objective ${WSH_OBJECTIVE}}"
EXCL_ARG="${WSH_EXCLUDE:+--exclude-indicators ${WSH_EXCLUDE}}"
```
      and append `$OBJ_ARG $EXCL_ARG` to the worker `IND_ARGS` line. Unset ⇒ unchanged.
- [ ] **Step 2:** `bash -n optimize/server/remote_wsi.sh` → OK. `python3 perf/check_golden.py` → 6/6 (additive).

## Task α.8 — run Tier 1 locally + report (acceptance)
**Files:** none (run)
- [ ] **Step 1 (background, ~30–60 min):** `python3 -m optimize.run_alpha_ladder --tier 1 --trials 800`
      Expected: writes `study_range_regime/REPORT_alpha_tier1_decision_pause.md`; prints the shortest pause
      found vs the champion's 11.5d. **PAUSE** — report to the user, wait for "go" before Tier 2.

## Task FINAL — doc + tracker
- [ ] Update `study_range_regime/NEXT_OPTIMIZER_NOTES.md` + `SYSTEM_UPDATES_MEGADOC.md` with α + the wsh7a/b/c
      ladder + the Tier-1 result. (No commit unless asked.)

---

## Self-review
- **Spec coverage:** D1 swap → α.1; D2 soft/no-threshold → α.1 (`-dec_pause`, no constraint added); D3 −5%
  highlight → α.6 `_report` star; D4 ladder + user-gated → α.6 (Tier 1 local, Tiers 2-3 print command, PAUSE);
  D5 wsh4-era exclude → α.2/α.5; D6 prefixes + warm-start → α.4/α.6. Golden-safe → α.3/α.7. Tests → α.1/α.2.
- **Placeholders:** none — all steps have runnable code/commands.
- **Type consistency:** `run(..., objective, exclude_inds, only_inds)`; `_suggest_indicators(trial, exclude, only)`
  with `_searched` stripped before engine use; `decision_pause_days` user_attr written in α.1 and read in α.6;
  env names `WSH_OBJECTIVE`/`WSH_EXCLUDE` consistent α.6↔α.7.
