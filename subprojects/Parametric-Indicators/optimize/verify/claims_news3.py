"""WS-NEWS3 claims (#124, #125) — every number published by the P1 ride-through study.

Protocol: #118. Same rules as claims_news2: value_fn reads the COMMITTED artefact; V1/V2/V3 must be
able to fail for DIFFERENT reasons; every claim declares its blind spot; `expect` is never adjusted
to match output.
"""
from __future__ import annotations


from pathlib import Path

import numpy as np
import pandas as pd

from harness import Check, Claim, register

FUND = Path(__file__).resolve().parents[1] / "fundamentals"

PRIMARY = dict(lead_min=5, stop_pct=0.20, direction="long")   # pre-registered on #125 BEFORE RTY ran


def _events(inst: str, subset: str = "RELEASES", title: str | None = None) -> pd.Series:
    d = pd.read_csv(FUND / f"p1_events_{inst}.csv")
    d = d[(d["set"] == subset) & (d.lead_min == PRIMARY["lead_min"])
          & (d.stop_pct == PRIMARY["stop_pct"]) & (d.direction == PRIMARY["direction"])]
    if title:
        d = d[d.title == title]
    return d.pnl_usd.astype(float)


def _tstat(x: pd.Series) -> tuple[float, float]:
    n = len(x)
    se = x.std(ddof=1) / np.sqrt(n)
    return float(x.mean() / se), float(se)


# ---------------------------------------------------------------------------------------------
# CLAIM — the announcement premium, confirmed on the pre-registered holdout instrument
# ---------------------------------------------------------------------------------------------
def _prem_v1() -> tuple[bool, str]:
    """V1 — RE-DERIVATION, different artefact: the cell AGGREGATE file (written by a separate code
    path in the run) must carry the same mean as the per-event file the ledger reads."""
    agg = pd.read_csv(FUND / "p1_ride_RTY.csv")
    a = agg[(agg["set"] == "RELEASES") & (agg.lead_min == 5) & (agg.stop_pct == 0.20)
            & (agg.direction == "long")].gross_mean.iloc[0]
    e = _events("RTY").mean()
    return abs(a - e) < 0.01, f"aggregate {a:.2f} vs per-event {e:.2f}"


def _prem_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT SOURCE: NQ and ES are different price files. If the premium were an artefact
    of the RTY frame it would not appear there; NQ's CI must exclude 0 and ES's mean must be > 0."""
    outs = {}
    for inst in ("NQ", "ES"):
        x = _events(inst)
        t, se = _tstat(x)
        outs[inst] = (float(x.mean()), t)
    ok = outs["NQ"][1] > 1.96 and outs["ES"][0] > 0
    return ok, f"NQ mean {outs['NQ'][0]:+.2f} (t={outs['NQ'][1]:.2f}), ES mean {outs['ES'][0]:+.2f}"


def _prem_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: 'the pipeline pays long wherever it is pointed' must be FALSE.
    The identical test on RTY CONTROL windows must NOT reject (one-sided p > 0.05), and CL —
    where no equity premium exists — must NOT show an effect like RTY's."""
    from scipy import stats
    ctl = _events("RTY", subset="CONTROL")
    t_c = stats.ttest_1samp(ctl, 0.0)
    p1_c = t_c.pvalue / 2 if t_c.statistic > 0 else 1 - t_c.pvalue / 2
    cl = _events("CL")
    ok = p1_c > 0.05 and cl.mean() < _events("RTY").mean() / 2
    return ok, f"RTY control mean {ctl.mean():+.2f} (1-sided p={p1_c:.3f}), CL mean {cl.mean():+.2f}"


register(Claim(
    id="P1-RIDE-PREMIUM-RTY-CONFIRMED",
    issue="#125",
    statement="The announcement-window LONG premium replicated on the pre-registered holdout: RTY "
              "(never loaded before the test was filed), long, enter 5 min before the release, "
              "0.20% stop, exit release+15m: +$69.54/event gross (95% CI [+27.21, +111.86], "
              "t = 3.22, one-sided p = 0.0007, n = 418), net +$57.04 at realistic costs; the same "
              "windows on clean control days pay ≈ $0.",
    source="optimize/fundamentals/p1_events_RTY.csv",
    value_fn=lambda: round(float(_events("RTY").mean()), 2),
    expect=69.54, tol=0.01,
    blind_spot="Shares the TV calendar and the control-draw code with every other cell — a defect "
               "in either affects all instruments identically and no check here can see it. Also "
               "cannot see era concentration (2016-19 is ~0); that caveat lives in the report, "
               "pinned by P1-CPI-ENGINE's V-checks only indirectly.",
    checks=[Check("V1", "aggregate file carries the same mean", _prem_v1),
            Check("V2", "premium present on independent NQ/ES price files", _prem_v2),
            Check("V3", "absent on RTY controls and on CL", _prem_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — the pre-release drift predicts NOTHING (goal row 4), adequately powered
# ---------------------------------------------------------------------------------------------
def _drift_counts() -> tuple[int, int, list]:
    n_groups, n_beat, rows = 0, 0, []
    for inst in ("NQ", "ES", "GC", "CL", "RTY"):
        d = pd.read_csv(FUND / f"p1_drift_{inst}.csv")
        rel = d[(d["set"] == "RELEASES") & (d.n > 0)]
        n_groups += len(rel)
        n_beat += int(rel.beats_break_even.sum() + rel.beats_half.sum())
        rows.append((inst, rel[rel.group == "ALL"].iloc[0]))
    return n_groups, n_beat, rows


def _drift_v1() -> tuple[bool, str]:
    """V1 — internal consistency: every accuracy must sit inside its own Wilson interval and the
    interval half-width must shrink like 1/sqrt(n) (a wrong-n or wrong-k row breaks this)."""
    bad = 0
    for inst in ("NQ", "ES", "GC", "CL", "RTY"):
        d = pd.read_csv(FUND / f"p1_drift_{inst}.csv")
        for _, r in d[d.n > 0].iterrows():
            if not (r.ci_lo - 1e-9 <= r.accuracy <= r.ci_hi + 1e-9):
                bad += 1
            if r.n > 100 and (r.ci_hi - r.ci_lo) > 4.0 / np.sqrt(r.n):
                bad += 1
    return bad == 0, f"{bad} inconsistent rows"


def _drift_v2() -> tuple[bool, str]:
    """V2 — the release-day 'signal' must equal its own control: if drift accuracy on release days
    materially exceeded the matched no-news control, the null would be wrong."""
    gaps = []
    for inst in ("NQ", "ES", "GC", "CL", "RTY"):
        d = pd.read_csv(FUND / f"p1_drift_{inst}.csv")
        a = d[(d["set"] == "RELEASES") & (d.group == "ALL")].accuracy.iloc[0]
        c = d[(d["set"] == "CONTROL") & (d.group == "ALL")].accuracy.iloc[0]
        gaps.append(a - c)
    return max(map(abs, gaps)) < 0.06, f"release-minus-control accuracy gaps {[round(g,3) for g in gaps]}"


def _drift_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: 'the test was too weak to reject the break-even' must be FALSE — every
    ALL-group upper bound must sit BELOW 0.71, i.e. the test could and did exclude tradeability."""
    his = []
    for inst in ("NQ", "ES", "GC", "CL", "RTY"):
        d = pd.read_csv(FUND / f"p1_drift_{inst}.csv")
        his.append(float(d[(d["set"] == "RELEASES") & (d.group == "ALL")].ci_hi.iloc[0]))
    return max(his) < 0.71, f"ALL-group CI upper bounds {[round(h,3) for h in his]} (break-even 0.71)"


register(Claim(
    id="P1-DRIFT-DEAD",
    issue="#125",
    statement="The pre-release price pattern (release−60m → release−1m drift) predicts the release "
              "move's direction on NO instrument: accuracies 0.48–0.51, every 95% upper bound below "
              "the 0.71 break-even; 0 of the release groups beat even 0.5. FOMC leans inverse "
              "(0.39 [0.29, 0.50]).",
    source="optimize/fundamentals/p1_drift_NQ.csv (+ES,GC,CL,RTY)",
    value_fn=lambda: _drift_counts()[1],
    expect=0, tol=0,
    blind_spot="Only the 60-minute lookback and sign-vs-sign form were tested; a nonlinear or "
               "other-horizon drift signal is invisible to this claim.",
    checks=[Check("V1", "accuracy/CI internal consistency", _drift_v1),
            Check("V2", "release accuracy equals its own control", _drift_v2),
            Check("V3", "the test was capable of rejecting 0.71 (all upper bounds below it)", _drift_v3)]))


# ---------------------------------------------------------------------------------------------
# CLAIM — CPI is the engine of the premium
# ---------------------------------------------------------------------------------------------
def _cpi_v1() -> tuple[bool, str]:
    """V1 — different statistic path: the t-test on the same rows must reject at 20-way Bonferroni
    (5 series x 4 instruments were looked at), not just 'CI excludes 0'."""
    from scipy import stats
    x = _events("NQ", title="Inflation Rate MoM")
    t = stats.ttest_1samp(x, 0.0)
    return bool(t.statistic > 0 and t.pvalue < 0.05 / 20), f"t={t.statistic:.2f}, p={t.pvalue:.2e}, n={len(x)}"


def _cpi_v2() -> tuple[bool, str]:
    """V2 — INDEPENDENT price files: the CPI-day premium must also be positive with CI excluding 0
    on RTY AND on GC (gold is outside the equity family — same macro event, different asset)."""
    outs = {}
    for inst in ("RTY", "GC"):
        x = _events(inst, title="Inflation Rate MoM")
        t, se = _tstat(x)
        outs[inst] = (float(x.mean()), t)
    ok = all(v[1] > 1.96 for v in outs.values())
    return ok, ", ".join(f"{k} {v[0]:+.2f} (t={v[1]:.2f})" for k, v in outs.items())


def _cpi_v3() -> tuple[bool, str]:
    """V3 — FALSIFICATION: 'any 8:30 release in the same era shows this' must be FALSE — Retail
    Sales MoM (same clock minute, same years, same instruments) must NOT show a positive premium."""
    x = _events("NQ", title="Retail Sales MoM")
    t, se = _tstat(x)
    return bool(x.mean() < 0 or t < 1.96), f"Retail Sales NQ mean {x.mean():+.2f} (t={t:.2f})"


register(Claim(
    id="P1-CPI-ENGINE",
    issue="#125",
    statement="CPI (Inflation Rate MoM) is the engine of the announcement premium: NQ long through "
              "CPI releases earns +$424.22/event (95% CI [+168.97, +679.48], n = 116) at the primary "
              "cell, replicated on RTY (+$262.40) and GC (+$258.73), while Retail Sales at the same "
              "clock minute earns −$79.20. Era-concentrated: strongest 2022+, alive through 2026.",
    source="optimize/fundamentals/p1_events_NQ.csv",
    value_fn=lambda: round(float(_events("NQ", title="Inflation Rate MoM").mean()), 2),
    expect=424.22, tol=0.01,
    blind_spot="n = 116 CPI events over 10.5y; the per-year signal is noisy (2023 was negative) and "
               "nothing here can distinguish 'permanent premium' from 'inflation-era regime that "
               "ends'. The claim pins the sample mean, not the future.",
    checks=[Check("V1", "significant at 20-way Bonferroni by t-test", _cpi_v1),
            Check("V2", "replicates on RTY and on GC (non-equity)", _cpi_v2),
            Check("V3", "Retail Sales at the same clock minute shows NO premium", _cpi_v3)]))
