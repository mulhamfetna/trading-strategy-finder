"""Read a study's results from the optimizer store for the Reporting panel (#43).

Multi-objective values are [median-fold P/L, -worst-DD, win%]. Feasibility (DD ≤ cap·P/L) is decided by
the optimizer's own constraints_func, whose values Optuna persists in trial system-attrs — we read those
rather than re-deriving the cap (avoids a silent-default mismatch if a run used a custom --dd-pnl-cap).
"""
from __future__ import annotations


def _load(name: str):
    import optuna
    from optimize import storage as S
    url = S.storage_url(None)
    return optuna.load_study(
        study_name=name,
        storage=optuna.storages.RDBStorage(url=url, engine_kwargs=S.engine_kwargs(url)),
    )


def _feasible(trial):
    """True/False from the optimizer's stored constraint values (feasible ⇔ all ≤ 0); None if unknown."""
    for k, v in trial.system_attrs.items():
        if "constraint" in k.lower() and isinstance(v, (list, tuple)) and v:
            return all(c <= 0 for c in v)
    return None


def study_summary(name: str, top: int = 12) -> dict:
    import optuna
    try:
        st = _load(name)
    except Exception as e:
        return {"ok": False, "name": name, "detail": str(e)[:200]}
    complete = [t for t in st.trials if t.state == optuna.trial.TrialState.COMPLETE and t.values]
    pruned = sum(1 for t in st.trials if t.state == optuna.trial.TrialState.PRUNED)
    rows = []
    for t in complete:
        v = t.values
        rows.append({
            "trial": t.number,
            "pnl": round(v[0], 1),
            "dd": round(-v[1], 1) if len(v) > 1 else None,
            "win": round(v[2], 2) if len(v) > 2 else None,
            "feasible": _feasible(t),
        })
    rows.sort(key=lambda r: (r["pnl"] if r["pnl"] is not None else -1e18), reverse=True)
    feas = [r for r in rows if r["feasible"]]
    return {
        "ok": True, "name": name,
        "total": len(st.trials), "complete": len(complete), "pruned": pruned,
        "feasible_count": len(feas),
        "best_pnl": rows[0] if rows else None,
        "best_feasible": feas[0] if feas else None,
        "top": rows[:top],
    }
