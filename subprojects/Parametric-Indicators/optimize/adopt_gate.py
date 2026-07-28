"""Issue #14 — the adopt gate for the 143-indicator library.

**Nothing from `#12`'s indicator library may become a champion contributor until it clears this.** The
reason is the multiple-comparisons trap: search 125+ candidate indicators against one price series and
*something* will look good on the training window purely by chance. The gate is designed so that a
lucky in-sample winner cannot pass.

Four numbers, and a candidate must beat all of them:

  baseline   the deployed champion, indicator layer frozen, scored on the 2026 holdout.
  treatment  re-optimize with the whole library searchable — but on **2025 only** (`--train-window
             2025`, so 2026 is never seen) — then score the best-on-train on 2026.
  dumb       the identical search, identical budget, with the real indicators replaced by PLACEBOS
             whose votes are pseudo-random. This measures how much "edge" the search procedure
             manufactures from noise. Treatment must beat it, not just beat zero.
  noise      take the treatment winner and SHUFFLE its indicators' per-bar votes. If the OOS edge
             survives a shuffle, it never came from the indicators.

Plus a power statement: `n` OOS trades and the minimum detectable effect. A null at low power is not
evidence of absence (`feedback_power_analysis_mandatory`), and a positive without the dumb + noise
controls is not evidence of presence (`feedback_dumb_control_and_noise`).

Subcommands:
  baseline   score the champion on the holdout
  evaluate   score an arbitrary params JSON on train / holdout
  noise      the vote-shuffle control for a given params JSON
  power      n + minimum detectable effect from a trade ledger
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from optimize import core, data as data_mod, timeframes as TF
from optimize.l2.payload import l1_default_params

_METRICS = ("pnl", "max_dd", "n_taken", "win", "pf", "exposure")


def _summary(m):
    out = {}
    for k in _METRICS:
        v = m.get(k)
        if isinstance(v, (int, float, np.floating)):
            out[k] = round(float(v), 4)
    return out


def _score(df_dec, df1, box, vf, n_split, params, bar_td, window):
    core._clear_caches()
    return core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                 dict(params, window=window), bar_td)


def _load(tf, instrument):
    return data_mod.load_inputs(tf, instrument)


def _both_windows(tf, instrument, params, label, log):
    df_dec, df1, box, vf, n_split = _load(tf, instrument)
    bar_td = TF.get(tf).bar_td
    tr = _score(df_dec, df1, box, vf, n_split, params, bar_td, "2025")
    oos = _score(df_dec, df1, box, vf, n_split, params, bar_td, "2026")
    log(f"  {label:22s} TRAIN(2025) P/L ${float(tr['pnl']):>10,.0f} DD ${float(tr['max_dd']):>8,.0f} "
        f"n={int(tr['n_taken']):>4d}  |  HOLDOUT(2026) P/L ${float(oos['pnl']):>10,.0f} "
        f"DD ${float(oos['max_dd']):>8,.0f} n={int(oos['n_taken']):>4d}")
    return {"label": label, "train_2025": _summary(tr), "holdout_2026": _summary(oos),
            "oos_trades": [float(t.get("pnl", 0.0)) for t in (oos.get("trades") or [])]}


# --------------------------------------------------------------------------------------------------
def power_from_trades(pnls, alpha=0.05, power=0.80):
    """Minimum detectable effect for a one-sample t-test on per-trade P/L.

    The question the gate must answer is not "did the treatment win?" but "could this design have
    DETECTED a win of the size we care about?" With n trades of standard deviation s, the smallest
    mean per-trade edge detectable at (alpha, power) is  (z_a + z_b) * s / sqrt(n).
    """
    from scipy import stats
    x = np.asarray([p for p in pnls if np.isfinite(p)], float)
    n = int(x.size)
    if n < 2:
        return {"n": n, "mean": None, "sd": None, "mde_per_trade": None, "mde_total": None,
                "note": "too few trades for a power statement"}
    s = float(x.std(ddof=1))
    za = float(stats.norm.ppf(1 - alpha / 2.0))
    zb = float(stats.norm.ppf(power))
    mde = (za + zb) * s / np.sqrt(n)
    t = float(x.mean() / (s / np.sqrt(n))) if s > 0 else float("nan")
    return {"n": n, "mean_per_trade": round(float(x.mean()), 2), "sd_per_trade": round(s, 2),
            "t_stat": round(t, 3), "p_two_sided": round(float(2 * (1 - stats.t.cdf(abs(t), n - 1))), 5),
            "mde_per_trade": round(float(mde), 2), "mde_total": round(float(mde * n), 0),
            "alpha": alpha, "power": power}


def install_vote_scrambler(seed: int, log):
    """PLACEBO MODE — destroy the indicators' information while keeping everything else identical.

    Each indicator's per-bar vote array is **circularly shifted** by a deterministic offset derived
    from (indicator key, its params, seed). A circular shift is chosen over a full shuffle on purpose:
    it preserves the vote's marginal distribution *and* its autocorrelation — how often it fires and
    how long it stays on — while destroying its alignment with price. So the control differs from the
    treatment in exactly one respect: whether the votes carry information. Search space, dimension
    count, trial budget, sampler and seeds are untouched.

    ⚠️ CACHE POISONING is the hazard here. `core._cached_votes` writes computed votes to the shared
    on-disk `vote_cache`, whose key does NOT know about scrambling — a placebo vote could be served to
    a REAL run later. So this also repoints the disk cache at a throwaway directory and clears the
    in-process memo. Never run placebo mode without it.
    """
    import tempfile
    import numpy as _np
    from indicators import runner
    from optimize import vote_cache

    scratch = tempfile.mkdtemp(prefix="adoptgate_placebo_votecache_")
    vote_cache.set_cache_dir(scratch)
    core._clear_caches()
    log(f"[gate] PLACEBO: vote cache isolated at {scratch} (a scrambled vote must never reach the real cache)")

    orig = runner._ind_vote
    stats = {"calls": 0}

    def scrambled(ind, ctx, bdir, src=None):
        v = _np.asarray(orig(ind, ctx, bdir, src))
        n = v.shape[0]
        if n < 2:
            return v
        key = (ind.key, tuple(sorted(ind.config.params.items())), seed)
        off = int(_np.abs(hash(key))) % n
        stats["calls"] += 1
        return _np.roll(v, off)

    runner._ind_vote = scrambled
    return stats


def cmd_search(args, log):
    """Run the optimization — treatment (real votes) or control (placebos) — on the TRAIN window only."""
    import time
    import optuna
    from optimize import optimizer as _opt
    stats = None
    if args.mode == "control":
        stats = install_vote_scrambler(args.seed, log)
    # A 47k-trial run at Optuna's INFO level writes ~50 MB of per-trial spam, which buries the two
    # lines that matter and makes the log useless to poll. Quiet it, and emit our own heartbeat instead
    # (`feedback_never_wait_blindly`: a long run must be observable, not a black box).
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    t_start = time.time()
    state = {"best": None}

    def heartbeat(study, trial):
        n = trial.number + 1
        if trial.values and (state["best"] is None or trial.values[0] > state["best"]):
            state["best"] = trial.values[0]
        if n % max(1, args.progress_every) == 0:
            el = time.time() - t_start
            rate = n / el if el > 0 else 0
            eta = (args.trials - n) / rate / 60 if rate > 0 else float("nan")
            log(f"[gate] {args.mode} {n:,}/{args.trials:,} trials "
                f"({rate*60:.0f}/min, ETA {eta:.0f} min) best-on-train ${state['best'] or 0:,.0f}")

    _opt.PROGRESS_CALLBACK = heartbeat
    log(f"[gate] {args.mode.upper()} search: tf={args.tf} trials={args.trials} "
        f"max_enabled={args.max_enabled} train_window={args.train_window} prefix={args.study_prefix}")
    res = _opt.run(args.tf, n_trials=args.trials, ind_1min=True, study_prefix=args.study_prefix,
                   max_enabled=args.max_enabled, train_window=args.train_window,
                   instrument=args.instrument, warm_start=not args.no_warm_start)
    if stats is not None:
        log(f"[gate] PLACEBO: scrambled {stats['calls']:,} vote computations")
        assert stats["calls"] > 0, "placebo mode scrambled NOTHING — the control is vacuous"
    return res


def _score_scrambled(tf, instrument, params, seed):
    """Score `params` on the 2026 holdout with every indicator vote circularly shifted by `seed`."""
    from indicators import runner
    import numpy as _np
    orig = runner._ind_vote
    try:
        def scrambled(ind, ctx, bdir, src=None):
            v = _np.asarray(orig(ind, ctx, bdir, src))
            n = v.shape[0]
            if n < 2:
                return v
            off = int(_np.abs(hash((ind.key, tuple(sorted(ind.config.params.items())), seed)))) % n
            return _np.roll(v, off)
        runner._ind_vote = scrambled
        df_dec, df1, box, vf, n_split = _load(tf, instrument)
        m = _score(df_dec, df1, box, vf, n_split, params, TF.get(tf).bar_td, "2026")
        return float(m["pnl"]), int(m["n_taken"])
    finally:
        runner._ind_vote = orig
        core._clear_caches()


def cmd_noise(args, log):
    """NOISE CHECK as a permutation test, not a single shuffle.

    A single scramble tells you almost nothing — one draw from a distribution you have not seen. This
    re-scores the winner `--perms` times with a different circular shift each time, which builds the
    null distribution of "what this exact configuration earns on the holdout when its indicators carry
    no information". The empirical p-value is the fraction of that null which matches or beats the real
    result.

    ⚠️ The vote cache is isolated first: a scrambled vote array written to the shared cache would be
    served to a real run later.
    """
    import tempfile
    from optimize import vote_cache
    scratch = tempfile.mkdtemp(prefix="adoptgate_noise_votecache_")
    vote_cache.set_cache_dir(scratch)
    core._clear_caches()
    log(f"[gate] NOISE: vote cache isolated at {scratch}")

    params = json.loads(Path(args.params).read_text())
    if "params" in params:                       # accept an `extract` output directly
        params = params["params"]
    params.setdefault("ind_1min", True)
    keys = [s["key"] for s in params.get("indicators", []) if s.get("enabled")]

    df_dec, df1, box, vf, n_split = _load(args.tf, args.instrument)
    real = _score(df_dec, df1, box, vf, n_split, params, TF.get(args.tf).bar_td, "2026")
    real_pnl = float(real["pnl"])
    log(f"[gate] winner indicators {keys}: REAL holdout P/L ${real_pnl:,.0f} (n={int(real['n_taken'])})")

    null = []
    for i in range(args.perms):
        pnl, n = _score_scrambled(args.tf, args.instrument, params, seed=100_000 + i)
        null.append(pnl)
        if (i + 1) % max(1, args.perms // 10) == 0:
            log(f"[gate] noise {i+1}/{args.perms} … null mean ${np.mean(null):,.0f}")
    null = np.asarray(null, float)
    ge = int((null >= real_pnl).sum())
    p = (ge + 1) / (len(null) + 1)               # add-one: an empirical p can never be exactly 0
    log(f"[gate] NULL n={len(null)}  mean ${null.mean():,.0f}  sd ${null.std(ddof=1):,.0f}  "
        f"p95 ${np.quantile(null, 0.95):,.0f}  max ${null.max():,.0f}")
    log(f"[gate] p = {p:.4f}  ({ge}/{len(null)} scrambles matched or beat the real result)")
    verdict = ("the edge SURVIVES scrambling ⇒ it does not come from the indicators"
               if p > 0.05 else "the edge VANISHES under scrambling ⇒ consistent with a real signal")
    log(f"[gate] {verdict}")
    return {"indicators": keys, "real_holdout_pnl": round(real_pnl, 2),
            "null_n": len(null), "null_mean": round(float(null.mean()), 2),
            "null_sd": round(float(null.std(ddof=1)), 2),
            "null_p95": round(float(np.quantile(null, 0.95)), 2),
            "null_max": round(float(null.max()), 2),
            "p_value": round(float(p), 5), "verdict": verdict}


def _pnl_by_entry(m):
    """{entry bar index -> P/L} for one scored run. The entry BAR is the pairing key: two strategies
    that take the same trade on the same bar contribute an exactly-zero difference.

    `backtest_metrics` trades carry `entry_idx` (an index into the scored window), not `entry_time` —
    the first version of this keyed on the latter, every lookup returned None, all 81 trades collapsed
    into a single bucket, and the paired test silently degenerated to n=1. Missing keys now raise
    instead of quietly producing a confident wrong answer.
    """
    out = {}
    for t in (m.get("trades") or []):
        if "entry_idx" not in t:
            raise KeyError(f"trade record has no 'entry_idx' — cannot pair. keys={sorted(t)}")
        k = int(t["entry_idx"])
        out[k] = out.get(k, 0.0) + float(t.get("pnl", 0.0))
    return out


def paired_stats(a_map, b_map, alpha=0.05, power=0.80, n_boot=10000, seed=7):
    """PAIRED comparison of two strategies on the same holdout, matched by entry bar.

    Why this and not two P/L totals: an unpaired test carries the full per-trade volatility of BOTH
    strategies (±$2,218 on NQ 4h), so it can only see an improvement of ~91% of the entire holdout
    profit. But two variants of the same box strategy take mostly the SAME trades — and every shared
    trade contributes a difference of exactly zero, carrying no variance at all. The signal lives
    entirely in the bars where they disagree, and pairing is what isolates it.

    Returns the difference series' t-test, a bootstrap CI on the TOTAL difference, and the paired MDE
    next to the unpaired one so the gain in power is visible rather than asserted.
    """
    from scipy import stats
    keys = sorted(set(a_map) | set(b_map))
    d = np.array([a_map.get(k, 0.0) - b_map.get(k, 0.0) for k in keys], float)
    n = int(d.size)
    if n < 2:
        return {"n_pairs": n, "note": "too few pairs"}
    nz = d != 0.0
    sd = float(d.std(ddof=1))
    za, zb = float(stats.norm.ppf(1 - alpha / 2)), float(stats.norm.ppf(power))
    mde = (za + zb) * sd / np.sqrt(n)
    t = float(d.mean() / (sd / np.sqrt(n))) if sd > 0 else float("nan")
    p = float(2 * (1 - stats.t.cdf(abs(t), n - 1))) if np.isfinite(t) else float("nan")

    if sd == 0.0:
        t, p = 0.0, 1.0                          # identical strategies: no difference, not "undefined"

    rng = np.random.default_rng(seed)
    boot = d[rng.integers(0, n, size=(n_boot, n))].sum(axis=1)

    # Apples-to-apples power comparison: the STANDARD ERROR OF THE TOTAL difference under each scheme.
    # (An earlier version compared a paired *total* against an unpaired *mean*, which are not the same
    # quantity and made pairing look 100x worse than it is.)
    #   paired    total = sum of per-bar differences        ⇒ SE = sd_d * sqrt(n_pairs)
    #   unpaired  total = sum(a) - sum(b), independent sets ⇒ SE = sqrt(n_a*var_a + n_b*var_b)
    a = np.array(list(a_map.values()), float)
    b = np.array(list(b_map.values()), float)
    se_paired = sd * np.sqrt(n)
    se_unpaired = (float(np.sqrt(a.size * a.var(ddof=1) + b.size * b.var(ddof=1)))
                   if (a.size > 1 and b.size > 1) else float("nan"))

    return {
        "n_pairs": n, "n_disagreeing_bars": int(nz.sum()),
        "agreement_pct": round(100.0 * (1 - nz.sum() / n), 1),
        "trades_a": int(a.size), "trades_b": int(b.size),
        "total_diff": round(float(d.sum()), 2),
        "mean_diff_per_bar": round(float(d.mean()), 2),
        "sd_diff": round(sd, 2),
        "t_stat": round(float(t), 3), "p_two_sided": round(float(p), 5),
        "boot_ci95_total": [round(float(np.quantile(boot, 0.025)), 0),
                            round(float(np.quantile(boot, 0.975)), 0)],
        "se_total_paired": round(float(se_paired), 0),
        "se_total_unpaired": round(float(se_unpaired), 0) if np.isfinite(se_unpaired) else None,
        "mde_total_paired": round(float((za + zb) * se_paired), 0),
        "mde_total_unpaired": (round(float((za + zb) * se_unpaired), 0)
                               if np.isfinite(se_unpaired) else None),
        "power_gain_x": (round(float(se_unpaired / se_paired), 2)
                         if np.isfinite(se_unpaired) and se_paired > 0 else None),
    }


def cmd_paired(args, log):
    """Paired holdout comparison. Two flavours, both reported:

      A  treatment winner  vs  the deployed baseline champion — the issue's question.
      B  the treatment winner with its indicators ON vs the SAME parameters with them OFF — an
         ABLATION. Everything but the indicator layer is held fixed, so the pairing is near-total and
         it answers the narrower, sharper question: did the INDICATORS contribute anything?
    """
    cand = json.loads(Path(args.params).read_text())
    if "params" in cand:
        cand = cand["params"]
    cand.setdefault("ind_1min", True)
    keys = [s["key"] for s in cand.get("indicators", []) if s.get("enabled")]

    base = dict(l1_default_params(args.tf))
    base["ind_1min"] = True

    df_dec, df1, box, vf, n_split = _load(args.tf, args.instrument)
    bar_td = TF.get(args.tf).bar_td

    m_cand = _score(df_dec, df1, box, vf, n_split, cand, bar_td, "2026")
    m_base = _score(df_dec, df1, box, vf, n_split, base, bar_td, "2026")

    off = dict(cand)
    off["indicators"] = [dict(s, enabled=False) for s in cand.get("indicators", [])]
    m_off = _score(df_dec, df1, box, vf, n_split, off, bar_td, "2026")

    log(f"[gate] candidate indicators {keys}")
    log(f"[gate]   candidate  HOLDOUT P/L ${float(m_cand['pnl']):>10,.0f}  n={int(m_cand['n_taken']):>4d}")
    log(f"[gate]   baseline   HOLDOUT P/L ${float(m_base['pnl']):>10,.0f}  n={int(m_base['n_taken']):>4d}")
    log(f"[gate]   same-but-indicators-OFF ${float(m_off['pnl']):>10,.0f}  n={int(m_off['n_taken']):>4d}")

    out = {"indicators": keys}
    for tag, other in (("A_vs_baseline", m_base), ("B_ablation_indicators_off", m_off)):
        st = paired_stats(_pnl_by_entry(m_cand), _pnl_by_entry(other))
        out[tag] = st
        log(f"[gate] {tag}: {st['n_pairs']} paired bars, {st['agreement_pct']}% identical  "
            f"total diff ${st['total_diff']:,.0f}  95% CI [{st['boot_ci95_total'][0]:,.0f}, "
            f"{st['boot_ci95_total'][1]:,.0f}]  p={st['p_two_sided']:.4f}")
        log(f"[gate]   SE(total) paired ${st['se_total_paired']:,.0f} vs unpaired "
            f"${st['se_total_unpaired']:,.0f}  ⇒ pairing is {st['power_gain_x']}× more sensitive "
            f"(detectable: ${st['mde_total_paired']:,.0f} paired vs ${st['mde_total_unpaired']:,.0f})")
    return out


def cmd_verdict(args, log):
    """Assemble every artifact and apply the adopt rule — including the distinction that matters most.

    ADOPT requires ALL of:
      1. treatment beats the baseline on the holdout;
      2. treatment beats the DUMB CONTROL's holdout — beating zero is not enough when an identical
         search over placebo votes also produces a positive number;
      3. the noise permutation test rejects (p <= 0.05) — the edge must vanish when the winner's own
         votes are scrambled;
      4. the paired 95% CI on the difference excludes zero.

    Anything else is DEFAULT-OFF. But a rejection is reported as one of two DIFFERENT things, because
    they have opposite implications for what to do next:
      NO EFFECT           the effect is measurable and it is not there.
      CANNOT TELL         |effect| < the minimum detectable effect. The design could not have seen a
                          real improvement of this size, so the null is uninformative
                          (`feedback_power_analysis_mandatory`).
    """
    def _read(p):
        return json.loads(Path(p).read_text()) if p and Path(p).exists() else None

    base = _read(args.baseline)
    treat = _read(args.treatment)
    ctrl = _read(args.control)
    noise = _read(args.noise_json)
    paired = _read(args.paired_json)

    v = {"criteria": {}, "inputs_present": {
        "baseline": base is not None, "treatment": treat is not None,
        "control": ctrl is not None, "noise": noise is not None, "paired": paired is not None}}

    b_oos = float(base["holdout_2026"]["pnl"]) if base else None
    t_sel = (treat or {}).get("selected") or {}
    t_oos = float(t_sel["holdout_2026"]["pnl"]) if t_sel else None
    c_sel = (ctrl or {}).get("selected") or {}
    c_oos = float(c_sel["holdout_2026"]["pnl"]) if c_sel else None

    log("[gate] ── ADOPT GATE VERDICT ──")
    if b_oos is not None:
        log(f"  baseline  holdout P/L ${b_oos:>11,.0f}")
    if t_oos is not None:
        log(f"  treatment holdout P/L ${t_oos:>11,.0f}   indicators {t_sel.get('enabled_indicators')}")
    if c_oos is not None:
        log(f"  CONTROL   holdout P/L ${c_oos:>11,.0f}   (placebo votes — the score a search "
            f"manufactures from noise)   indicators {c_sel.get('enabled_indicators')}")

    if b_oos is not None and t_oos is not None:
        v["criteria"]["1_beats_baseline"] = bool(t_oos > b_oos)
        log(f"  1. beats baseline?      {'YES' if t_oos > b_oos else 'NO'}  "
            f"(Δ ${t_oos - b_oos:+,.0f})")
    if c_oos is not None and t_oos is not None:
        v["criteria"]["2_beats_dumb_control"] = bool(t_oos > c_oos)
        log(f"  2. beats dumb control?  {'YES' if t_oos > c_oos else 'NO'}  "
            f"(Δ ${t_oos - c_oos:+,.0f})")
    if noise:
        ok = float(noise["p_value"]) <= 0.05
        v["criteria"]["3_noise_test_rejects"] = bool(ok)
        log(f"  3. survives noise test? {'YES' if ok else 'NO'}  (permutation p={noise['p_value']}, "
            f"null mean ${noise['null_mean']:,.0f})")
    if paired:
        st = paired.get("A_vs_baseline") or {}
        lo, hi = st.get("boot_ci95_total", [None, None])
        ok = bool(lo is not None and (lo > 0 or hi < 0))
        v["criteria"]["4_paired_ci_excludes_zero"] = ok
        log(f"  4. paired CI excludes 0?{'YES' if ok else ' NO'}  "
            f"(Δ ${st.get('total_diff', 0):,.0f}, 95% CI [{lo:,.0f}, {hi:,.0f}], p={st.get('p_two_sided')})")
        v["mde_total_paired"] = st.get("mde_total_paired")
        v["observed_effect"] = st.get("total_diff")

    passed = all(v["criteria"].values()) and len(v["criteria"]) == 4
    v["adopt"] = bool(passed)
    if passed:
        v["verdict"] = "ADOPT"
    else:
        eff, mde = v.get("observed_effect"), v.get("mde_total_paired")
        underpowered = (eff is not None and mde is not None and abs(eff) < mde)
        v["verdict"] = "DEFAULT-OFF — CANNOT TELL (underpowered)" if underpowered else "DEFAULT-OFF — NO EFFECT"
        v["underpowered"] = bool(underpowered)
    log(f"  ⇒ {v['verdict']}")
    if v.get("underpowered"):
        log(f"     |observed ${abs(v['observed_effect']):,.0f}| < minimum detectable "
            f"${v['mde_total_paired']:,.0f} ⇒ this design could NOT have seen an improvement of this "
            f"size. The null says nothing about the indicators.")
    return v


def params_from_trial(t):
    """Rebuild the engine params dict from a stored trial — from RECORDED values, never re-derived.

    `enabled_specs`, `k_rule`, `cap_mode` and `cap_1min` are read from user_attrs because the optimizer
    resolves them (a pinned `--force-eod` never appears in `trial.params` at all, and re-deriving it
    reads as OFF — which silently strips the end-of-day close off the champion).
    """
    p = t.params
    ua = t.user_attrs
    return {
        "sl_soft": float(p["sl_soft"]),
        "sl_hard": float(p["sl_soft"]) + float(p["sl_hard_delta"]),
        "tp": float(p["tp"]),
        "gate_pct": float(p["gate_pct"]),
        "dd_limit": float(p["dd_limit"]),
        "cooldown": int(p["cooldown"]),
        "flip": bool(p["flip"]),
        "k": int(ua["k_rule"]),
        "indicators": list(ua["enabled_specs"]),
        "cap_mode": ua.get("cap_mode", "none"),
        "cap_1min": int(ua.get("cap_1min", 0) or 0),
        "ind_1min": True,
    }


def cmd_extract(args, log):
    """Take the search's feasible Pareto front and score every member on train + HOLDOUT.

    The gate's rule is best-ON-TRAIN, then read its holdout number — picking the best *holdout* member
    would be selecting on the test set, which is the exact trap this whole exercise exists to avoid. So
    the front is ranked by the TRAIN objective and `selected` is its top member; the rest are reported
    only so the spread is visible.

    ⚠️ `--scramble-seed` is REQUIRED when extracting a CONTROL study, and it must be the seed that
    study was searched with. The dumb control asks "what does this search procedure score when the
    indicators carry no information?" — that is a statement about the whole pipeline under the null, so
    the holdout must be scored with the SAME placebo votes the search trained on. Scoring a control
    winner with real votes silently answers a different question (what an arbitrarily-chosen real
    configuration earns) and the resulting number is not a null at all.
    """
    import optuna
    if args.scramble_seed is not None:
        install_vote_scrambler(args.scramble_seed, log)
        log(f"[gate] extracting under PLACEBO votes (seed {args.scramble_seed}) — this is a CONTROL study")
    storage = _storage()
    study = optuna.load_study(study_name=args.study, storage=storage)

    def feasible(t):
        return all(v <= 0 for v in t.user_attrs.get("constraint", [1.0]))

    front = [t for t in study.best_trials if feasible(t) and "enabled_specs" in t.user_attrs]
    front.sort(key=lambda t: t.values[0], reverse=True)          # rank by TRAIN median fold P/L
    log(f"[gate] study {args.study}: {len(study.trials):,} trials, feasible front {len(front)}")
    if not front:
        log("[gate] !! no feasible front member carries `enabled_specs` — nothing to evaluate")
        return {"study": args.study, "front": 0, "members": []}

    rows = []
    for i, t in enumerate(front[: args.top]):
        prm = params_from_trial(t)
        keys = [s["key"] for s in prm["indicators"]]
        row = _both_windows(args.tf, args.instrument, prm, f"front[{i}] {keys}", log)
        row["trial_number"] = t.number
        row["train_objective"] = float(t.values[0])
        row["enabled_indicators"] = keys
        row["params"] = prm
        row["power_oos"] = power_from_trades(row.pop("oos_trades"))
        rows.append(row)
    return {"study": args.study, "front": len(front), "selected": rows[0], "members": rows}


def _storage():
    import os
    url = os.environ.get("WSH_STORAGE_URL")
    if not url:
        raise SystemExit("WSH_STORAGE_URL not set — source the server's pg.env first")
    return url


def cmd_baseline(args, log):
    params = l1_default_params(args.tf)
    params["ind_1min"] = True
    enabled = [s["key"] for s in (params.get("indicators") or []) if s.get("enabled")]
    log(f"[gate] BASELINE = deployed {args.tf} champion, indicator layer FROZEN: {enabled} (k={params.get('k')})")
    row = _both_windows(args.tf, args.instrument, params, "baseline champion", log)
    row["enabled_indicators"] = enabled
    row["k"] = params.get("k")
    row["power_oos"] = power_from_trades(row.pop("oos_trades"))
    log(f"  power(OOS): n={row['power_oos']['n']} trades, per-trade sd "
        f"${row['power_oos']['sd_per_trade']:,.0f} ⇒ minimum detectable edge "
        f"${row['power_oos']['mde_per_trade']:,.0f}/trade (${row['power_oos']['mde_total']:,.0f} total) "
        f"at alpha=0.05, power=0.80")
    return row


def cmd_evaluate(args, log):
    params = json.loads(Path(args.params).read_text())
    params.setdefault("ind_1min", True)
    row = _both_windows(args.tf, args.instrument, params, Path(args.params).stem, log)
    row["power_oos"] = power_from_trades(row.pop("oos_trades"))
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["baseline", "evaluate", "search", "extract", "noise", "paired", "verdict"])
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--params", default=None, help="params JSON (for `evaluate`)")
    ap.add_argument("--mode", default="treatment", choices=["treatment", "control"],
                    help="`search` only. control ⇒ indicator votes are circularly shifted (placebo).")
    ap.add_argument("--trials", type=int, default=47100)
    ap.add_argument("--max-enabled", type=int, default=3)
    ap.add_argument("--train-window", default="2025", choices=["full", "2025"])
    ap.add_argument("--study-prefix", default="adopt14")
    ap.add_argument("--no-warm-start", action="store_true")
    ap.add_argument("--seed", type=int, default=20260728, help="placebo shift seed")
    ap.add_argument("--progress-every", type=int, default=2000, help="heartbeat interval (trials)")
    ap.add_argument("--study", default=None, help="study name (for `extract`)")
    ap.add_argument("--top", type=int, default=5, help="front members to score (`extract`)")
    ap.add_argument("--perms", type=int, default=200, help="permutations for the noise check")
    ap.add_argument("--scramble-seed", type=int, default=None,
                    help="REQUIRED when extracting a CONTROL study: the seed it was searched\n                         with, so the holdout is scored under the SAME placebo votes.")
    ap.add_argument("--baseline", default=None, help="baseline JSON (verdict)")
    ap.add_argument("--treatment", default=None, help="treatment extract JSON (verdict)")
    ap.add_argument("--control", default=None, help="control extract JSON (verdict)")
    ap.add_argument("--noise-json", default=None, help="noise JSON (verdict)")
    ap.add_argument("--paired-json", default=None, help="paired JSON (verdict)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    def log(m):
        print(m, flush=True)

    res = {"baseline": cmd_baseline, "evaluate": cmd_evaluate, "search": cmd_search,
           "extract": cmd_extract, "noise": cmd_noise,
           "paired": cmd_paired, "verdict": cmd_verdict}[args.cmd](args, log)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(res, indent=2))
        log(f"[gate] WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
